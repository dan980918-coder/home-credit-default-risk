"""검증 노트북(verification.ipynb)을 생성하는 1회성 스크립트. 노트북 자체는 실행하지 않은 채 커밋한다."""
import os
import nbformat as nbf

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "v2", "verification", "verification.ipynb")

nb = nbf.v4.new_notebook()
cells = []


def md(text):
    cells.append(nbf.v4.new_markdown_cell(text))


def code(text):
    cells.append(nbf.v4.new_code_cell(text))


md("""# 검증 노트북

연체 위험 기반 대출 승인 기준 설계 (Loan Approval Risk Scoring) — v2 1~3단계 직접 검증

**독립성**: 이 노트북은 `v2/scripts/`의 함수를 import하지 않는다. `data/raw/`의 원본 CSV에서 매번 다시 계산한다.
`v2/verification/checklist.md`의 번호와 셀이 1:1로 대응한다. **이 노트북은 실행하지 않은 상태로 커밋됐다 — 출력은 직접 실행해서 확인한다.**""")

code("""import duckdb
import pandas as pd
import numpy as np

RAW = "../../data/raw"  # 저장소 루트 기준 data/raw
con = duckdb.connect()

def p(name):
    return f"{RAW}/{name}"
""")

md("## A. 원천 데이터")

md("""### 1. 테이블 행 수
기대값: application_train 307,511 / application_test 48,744 / bureau 1,716,428 / bureau_balance 27,299,925 /
previous_application 1,670,214 / POS_CASH_balance 10,001,358 / installments_payments 13,605,401 / credit_card_balance 3,840,312
(출처: `v2/docs/01_data_audit.md` §1-1)""")
code("""FILES = ["application_train.csv", "application_test.csv", "bureau.csv", "bureau_balance.csv",
         "previous_application.csv", "POS_CASH_balance.csv", "installments_payments.csv", "credit_card_balance.csv"]
for f in FILES:
    n = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p(f)}')").fetchone()[0]
    print(f, n)
""")

md("""### 2. 기저 연체율
기대값: 8.073% (출처: `01_data_audit.md` §4)""")
code("""rate = con.execute(f"SELECT AVG(TARGET) FROM read_csv_auto('{p('application_train.csv')}')").fetchone()[0]
print(f"{rate*100:.3f}%")
""")

md("""### 3. 특수값(DAYS_EMPLOYED=365243)
기대값: 55,374건 (출처: `01_data_audit.md` §5-4)""")
code("""cnt = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p('application_train.csv')}') WHERE DAYS_EMPLOYED = 365243").fetchone()[0]
print(cnt)
""")

md("""### 4. 고아 비율 (bureau_balance의 진짜 고아)
기대값: 3,120,184 / 27,299,925 = 11.43% (출처: `01_data_audit.md` "수정 기록" 절)""")
code("""orphan = con.execute(f'''
    SELECT COUNT(*) FROM read_csv_auto('{p("bureau_balance.csv")}') bb
    WHERE bb.SK_ID_BUREAU NOT IN (SELECT SK_ID_BUREAU FROM read_csv_auto('{p("bureau.csv")}'))
''').fetchone()[0]
total = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p('bureau_balance.csv')}')").fetchone()[0]
print(orphan, total, round(orphan/total*100, 3), "%")
""")

md("## B. 분할")

md("""### 5. 분할 겹침
기대값: 세 집합 모두 교집합 0건""")
code("""train_ids = pd.read_csv("../data/splits/train_ids.csv")
valid_ids = pd.read_csv("../data/splits/valid_ids.csv")
holdout_ids = pd.read_csv("../data/splits/holdout_ids.csv")

print("train∩valid:", len(set(train_ids.SK_ID_CURR) & set(valid_ids.SK_ID_CURR)))
print("train∩holdout:", len(set(train_ids.SK_ID_CURR) & set(holdout_ids.SK_ID_CURR)))
print("valid∩holdout:", len(set(valid_ids.SK_ID_CURR) & set(holdout_ids.SK_ID_CURR)))
""")

md("""### 6. 분할 크기와 연체율
기대값: 학습 184,506명(8.073%) / 검증 61,502명(8.073%) / 최종평가 61,503명(TARGET 미저장)""")
code("""print("train:", len(train_ids), f"{train_ids.TARGET.mean()*100:.3f}%")
print("valid:", len(valid_ids), f"{valid_ids.TARGET.mean()*100:.3f}%")
print("holdout:", len(holdout_ids), "TARGET column exists?", "TARGET" in holdout_ids.columns)
""")

md("""### 7. 최종평가 미사용 확인
04/05번 스크립트에 holdout_ids.csv를 읽는 코드가 없어야 한다. 아래 셀은 쉘 명령이므로 터미널에서 직접 실행해도 된다.""")
code("""import subprocess
result = subprocess.run(
    ["grep", "-rn", "holdout", "../scripts/01_data_audit.py", "../scripts/02_variable_catalog.py",
     "../scripts/03_split.py", "../scripts/04_build_hypothesis_features.py", "../scripts/05_test_signal_hypotheses.py"],
    capture_output=True, text=True
)
print(result.stdout or "(검색 결과 없음 - 03_split.py 외에는 holdout 언급이 전혀 없어야 정상)")
""")

md("## C. 변수 (신청자 추적)")

md("""### 8. 분할상환 지연 비율 (H1 핵심 변수)
exports/applicant_<ID>_installments_payments.csv를 직접 열어 DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT 인 행 비율을 센다.
이 셀은 "내보내기"만 하고, 계산은 스프레드시트에서 직접 한다(지시사항).""")
code("""tracer = pd.read_csv("tracer_applicants.csv")
print(tracer)
# exports/applicant_<ID>_installments_payments.csv 파일을 Numbers/엑셀로 열어
# DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT 인 행 수를 세고 전체 행 수로 나눈다.
""")

md("""### 9. 과거 신청 거절 비율 (H3 핵심 변수)
exports/applicant_<ID>_previous_application.csv에서 NAME_CONTRACT_STATUS='Refused' 비율을 스프레드시트에서 직접 센다.""")
code("""# 내보내기 셀 (계산은 스프레드시트에서)
for sk_id in tracer.SK_ID_CURR:
    df = pd.read_csv(f"exports/applicant_{sk_id}_previous_application.csv")
    print(sk_id, "previous_application 행 수:", len(df), "| NAME_CONTRACT_STATUS 값:", df["NAME_CONTRACT_STATUS"].tolist())
""")

md("""### 10. 대출금÷물건가격(H5), 재직기간(H4)
exports/applicant_<ID>_application_row.csv에서 AMT_CREDIT÷AMT_GOODS_PRICE, -DAYS_EMPLOYED(365243이면 NULL)를 직접 계산.""")
code("""for sk_id in tracer.SK_ID_CURR:
    df = pd.read_csv(f"exports/applicant_{sk_id}_application_row.csv")
    print(sk_id, "AMT_CREDIT=", df["AMT_CREDIT"].iloc[0], "AMT_GOODS_PRICE=", df["AMT_GOODS_PRICE"].iloc[0],
          "DAYS_EMPLOYED=", df["DAYS_EMPLOYED"].iloc[0])
""")

md("""### 11. 이력 없는 신청자
hypothesis_features.parquet에서 SK_ID_CURR=409473의 이력 변수들이 0이 아니라 NULL인지 확인.""")
code("""feat = pd.read_parquet("../data/features/hypothesis_features.parquet")
no_hist_id = pd.read_csv("tracer_no_history_applicant.csv").SK_ID_CURR.iloc[0]
row = feat[feat.SK_ID_CURR == no_hist_id][
    ["SK_ID_CURR", "late_payment_ratio", "reject_ratio", "n_installment_records", "n_prev_records", "no_history_at_all_flag"]
]
print(row)
print("모두 NaN(NULL)이어야 함 (0이면 불일치)")
""")

md("## D. 가설 검증 계산")

md("""### 12. IV 재계산
bins_employment_days.csv를 스프레드시트로 열어 WoE/IV를 직접 계산한다. 아래 셀은 참고용 재현 계산(스프레드시트 계산과 대조).
공식: good_dist=(n_good+0.5)/(total_good+0.5*구간수), bad_dist=(n_bad+0.5)/(total_bad+0.5*구간수),
WoE=ln(good_dist/bad_dist), IV=Σ(good_dist-bad_dist)×WoE""")
code("""bins = pd.read_csv("bins_employment_days.csv")
k = len(bins)
total_good = bins["n_good(정상)"].sum()
total_bad = bins["n_bad(연체)"].sum()
good_dist = (bins["n_good(정상)"] + 0.5) / (total_good + 0.5 * k)
bad_dist = (bins["n_bad(연체)"] + 0.5) / (total_bad + 0.5 * k)
woe = np.log(good_dist / bad_dist)
iv_contrib = (good_dist - bad_dist) * woe
print("IV 합계:", round(iv_contrib.sum(), 4), "(보고서 값: 0.1130)")
""")

md("""### 13. Wilson 신뢰구간
bins_employment_days.csv의 bin1(가장 위험한 구간 중 하나)에 대해 Wilson 공식을 직접 계산.
공식: p=n_bad/n, z=1.96, 중심=(p+z²/2n)/(1+z²/n), 반폭=z·sqrt(p(1-p)/n+z²/4n²)/(1+z²/n)""")
code("""row = bins[bins["bin"] == "bin1"].iloc[0]
n, k_bad = row["n"], row["n_bad(연체)"]
p = k_bad / n
z = 1.96
denom = 1 + z**2 / n
center = (p + z**2 / (2*n)) / denom
half = (z * np.sqrt(p*(1-p)/n + z**2/(4*n**2))) / denom
print(f"연체율={p*100:.3f}%, 95% CI=[{(center-half)*100:.3f}%, {(center+half)*100:.3f}%]")
print(f"보고서 값: {row['bad_rate_pct_보고서값']}% [{row['ci_low_pct_보고서값']}%, {row['ci_high_pct_보고서값']}%]")
""")

md("""### 14. 최소 구간 크기
5개 핵심변수의 모든 구간이 학습 세트의 5% 이상인지 확인.""")
code("""import json
with open("../docs/hypothesis_results.json", encoding="utf-8") as f:
    results = json.load(f)

core_vars = {
    "H1": "late_payment_ratio", "H2": "annuity_to_income", "H3": "reject_ratio",
    "H4": "employment_days", "H5": "credit_to_goods",
}
for h_name, h in results["hypotheses"].items():
    core = h["core_variable"]
    min_pct = min(b["pct_of_total"] for b in core["bins"])
    print(h_name, core["variable"], "최소 구간 비중:", min_pct, "% (5.0 이상이어야 함)")
""")

md("## E. 원칙 준수")

md("""### 15. 제외 변수 및 시간창 조건
CODE_GENDER, SOCIAL_CIRCLE 4개가 feature 컬럼에 없는지, excluded_always 목록에 있는지 확인.""")
code("""with open("../docs/feature_build_log.json", encoding="utf-8") as f:
    log = json.load(f)

print("excluded_always:", log["excluded_always"])

feat_cols = pd.read_parquet("../data/features/hypothesis_features.parquet").columns.tolist()
excluded = {"CODE_GENDER", "OBS_30_CNT_SOCIAL_CIRCLE", "DEF_30_CNT_SOCIAL_CIRCLE",
            "OBS_60_CNT_SOCIAL_CIRCLE", "DEF_60_CNT_SOCIAL_CIRCLE"}
present = excluded & set(feat_cols)
print("feature 테이블에 남아있는 제외 변수(비어 있어야 함):", present)

# 시간창 조건은 04_build_hypothesis_features.py의 소스코드를 직접 열어 확인한다:
# 128행 bureau_recent_1yr_new_loans: DAYS_CREDIT >= -365
# 147~148행 recent_1yr_late_ratio: DAYS_INSTALMENT >= -365
""")

nb["cells"] = cells
with open(OUT, "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print(f"저장: {OUT} ({len(cells)}개 셀)")
