"""
select_and_export_tracer_applicants.py
Loan Approval Risk Scoring - v2 검증 키트

학습 세트에서 이력이 풍부한 신청자 3명을 무작위(seed 고정)로 골라,
체크리스트 8~10번 항목 검증에 쓸 원본 테이블 행을 CSV로 내보낸다.

독립성: 이 스크립트는 v2/scripts/의 파이프라인 함수를 import하지 않고,
data/raw/의 원본 CSV에서 직접 다시 읽는다. v2/data/splits/train_ids.csv만
"학습 세트에 속한 신청자"를 가려내는 용도로 참조한다(계산 로직 재사용 아님).

실행: python3 -I v2/verification/select_and_export_tracer_applicants.py
출력:
  v2/verification/tracer_applicants.csv (선정된 3명 + 이력 건수 요약, 커밋함)
  v2/verification/exports/applicant_<ID>_installments_payments.csv (커밋 안 함)
  v2/verification/exports/applicant_<ID>_previous_application.csv (커밋 안 함)
  v2/verification/exports/applicant_<ID>_application_row.csv (커밋 안 함)
"""
import os
import duckdb
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
SPLIT_DIR = os.path.join(ROOT, "v2", "data", "splits")
VERIF_DIR = os.path.join(ROOT, "v2", "verification")
EXPORT_DIR = os.path.join(VERIF_DIR, "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

SEED = 20251017  # 고정 seed

con = duckdb.connect()


def p(name):
    return os.path.join(RAW, name)


train_ids = pd.read_csv(os.path.join(SPLIT_DIR, "train_ids.csv"))

p_train = p("application_train.csv")
p_prev = p("previous_application.csv")
p_inst = p("installments_payments.csv")

# 신청자별 previous_application 건수, installments_payments 건수 (진짜 고아 제외 없이 원본 그대로 카운트 - 검증용은 원본 그대로 보는 것이 목적)
prev_counts = con.execute(
    f"SELECT SK_ID_CURR, COUNT(*) as n_prev FROM read_csv_auto('{p_prev}') GROUP BY SK_ID_CURR"
).fetchdf()
inst_counts = con.execute(
    f"SELECT SK_ID_CURR, COUNT(*) as n_inst FROM read_csv_auto('{p_inst}') GROUP BY SK_ID_CURR"
).fetchdf()

candidates = train_ids.merge(prev_counts, on="SK_ID_CURR", how="inner").merge(inst_counts, on="SK_ID_CURR", how="inner")
# 너무 적지도(검증 의미 없음) 너무 많지도(수기 확인 부담) 않은 범위로 제한
candidates = candidates[(candidates["n_prev"].between(2, 5)) & (candidates["n_inst"].between(10, 30))]
print(f"후보 신청자 수: {len(candidates)}")

chosen = candidates.sample(n=3, random_state=SEED).sort_values("SK_ID_CURR")
print(chosen)

# 요약 저장 (커밋함 - 집계 수치)
chosen.to_csv(os.path.join(VERIF_DIR, "tracer_applicants.csv"), index=False)

# 각 신청자의 원본 행 내보내기 (커밋 안 함, exports/)
for _, row in chosen.iterrows():
    sk_id = int(row["SK_ID_CURR"])

    inst_rows = con.execute(
        f"SELECT * FROM read_csv_auto('{p_inst}') WHERE SK_ID_CURR = {sk_id} ORDER BY DAYS_INSTALMENT, NUM_INSTALMENT_NUMBER"
    ).fetchdf()
    inst_rows.to_csv(os.path.join(EXPORT_DIR, f"applicant_{sk_id}_installments_payments.csv"), index=False)

    prev_rows = con.execute(
        f"SELECT * FROM read_csv_auto('{p_prev}') WHERE SK_ID_CURR = {sk_id} ORDER BY DAYS_DECISION"
    ).fetchdf()
    prev_rows.to_csv(os.path.join(EXPORT_DIR, f"applicant_{sk_id}_previous_application.csv"), index=False)

    app_row = con.execute(
        f"SELECT * FROM read_csv_auto('{p_train}') WHERE SK_ID_CURR = {sk_id}"
    ).fetchdf()
    app_row.to_csv(os.path.join(EXPORT_DIR, f"applicant_{sk_id}_application_row.csv"), index=False)

    print(f"SK_ID_CURR={sk_id}: installments {len(inst_rows)}행, previous_application {len(prev_rows)}행 내보냄")

# 이력이 전혀 없는 신청자 1명도 선정 (체크리스트 11번용)
bureau_ids = con.execute(f"SELECT DISTINCT SK_ID_CURR FROM read_csv_auto('{p('bureau.csv')}')").fetchdf()
no_hist_candidates = train_ids[
    (~train_ids["SK_ID_CURR"].isin(prev_counts["SK_ID_CURR"]))
    & (~train_ids["SK_ID_CURR"].isin(bureau_ids["SK_ID_CURR"]))
]
no_hist_chosen = no_hist_candidates.sample(n=1, random_state=SEED)
no_hist_chosen.to_csv(os.path.join(VERIF_DIR, "tracer_no_history_applicant.csv"), index=False)
print(f"\n이력 없는 신청자(체크리스트 11번): SK_ID_CURR={no_hist_chosen['SK_ID_CURR'].iloc[0]}")

print("\n완료")
