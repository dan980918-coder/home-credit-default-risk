"""
01_data_audit.py
Loan Approval Risk Scoring (연체 위험 기반 대출 승인 기준 설계) - v2 재분석
1단계: 원데이터 점검

실행: python3 v2/scripts/01_data_audit.py
출력: v2/docs/audit_results.json (중간 결과), v2/docs/figures/*.png
주의: 모델링/상관/그룹별 연체율 계산 없음. TARGET은 분포만 확인.
"""
import json
import os
import duckdb
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
FIG_DIR = os.path.join(ROOT, "v2", "docs", "figures")
OUT_JSON = os.path.join(ROOT, "v2", "docs", "audit_results.json")

os.makedirs(FIG_DIR, exist_ok=True)

# 한글 폰트 설정
for font_name in ["AppleGothic", "NanumGothic", "Nanum Gothic"]:
    if any(f.name == font_name for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = font_name
        break
plt.rcParams["axes.unicode_minus"] = False

FILES = {
    "application_train": "application_train.csv",
    "application_test": "application_test.csv",
    "bureau": "bureau.csv",
    "bureau_balance": "bureau_balance.csv",
    "previous_application": "previous_application.csv",
    "POS_CASH_balance": "POS_CASH_balance.csv",
    "installments_payments": "installments_payments.csv",
    "credit_card_balance": "credit_card_balance.csv",
}

con = duckdb.connect()
results = {}

# ---------------------------------------------------------------
# 1-1. 파일 기본 정보
# ---------------------------------------------------------------
print("=== 1-1. 파일 기본 정보 ===")
file_info = {}
for name, fname in FILES.items():
    path = os.path.join(RAW, fname)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    try:
        nrows = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{path}')").fetchone()[0]
        ncols = len(con.execute(f"SELECT * FROM read_csv_auto('{path}') LIMIT 0").description)
        read_error = None
    except Exception as e:
        nrows, ncols = None, None
        read_error = str(e)
    file_info[name] = {
        "file": fname,
        "size_mb": round(size_mb, 1),
        "n_rows": nrows,
        "n_cols": ncols,
        "encoding": "utf-8 (가정, 오류 없음)" if read_error is None else "확인 필요",
        "read_error": read_error,
    }
    print(name, file_info[name])
results["file_info"] = file_info

# 분석 단위(grain) - 컬럼 설명/Kaggle 문서 근거로 수동 기록
grain = {
    "application_train": "대출 신청 1건 = 신청자 1명 (SK_ID_CURR 1개당 1행)",
    "application_test": "대출 신청 1건 = 신청자 1명 (TARGET 없음, 예측 대상)",
    "bureau": "신청자(SK_ID_CURR)가 타 금융기관에 보유한 과거/현재 신용 1건 (SK_ID_BUREAU 1개당 1행)",
    "bureau_balance": "bureau의 각 신용(SK_ID_BUREAU)에 대한 월별(MONTHS_BALANCE) 상태 스냅샷 1행",
    "previous_application": "신청자(SK_ID_CURR)의 과거 Home Credit 대출 신청 1건 (SK_ID_PREV 1개당 1행)",
    "POS_CASH_balance": "previous_application(SK_ID_PREV)의 POS/현금대출에 대한 월별 상태 스냅샷 1행",
    "installments_payments": "previous_application(SK_ID_PREV)의 분할상환 회차(또는 실제 납부)별 1행",
    "credit_card_balance": "previous_application(SK_ID_PREV)의 신용카드 대출에 대한 월별 잔액 스냅샷 1행",
}
results["grain"] = grain

# ---------------------------------------------------------------
# 1-2. 키와 테이블 연결
# ---------------------------------------------------------------
print("\n=== 1-2. 키 유일성 ===")
key_checks = {}


def path_of(name):
    return os.path.join(RAW, FILES[name])


# SK_ID_CURR 중복 (application_train/test)
for name in ["application_train", "application_test"]:
    p = path_of(name)
    total = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p}')").fetchone()[0]
    distinct = con.execute(f"SELECT COUNT(DISTINCT SK_ID_CURR) FROM read_csv_auto('{p}')").fetchone()[0]
    key_checks[name] = {"key": "SK_ID_CURR", "total_rows": total, "distinct_keys": distinct, "duplicated": total != distinct}

# SK_ID_BUREAU 중복 (bureau)
p = path_of("bureau")
total = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p}')").fetchone()[0]
distinct = con.execute(f"SELECT COUNT(DISTINCT SK_ID_BUREAU) FROM read_csv_auto('{p}')").fetchone()[0]
key_checks["bureau"] = {"key": "SK_ID_BUREAU", "total_rows": total, "distinct_keys": distinct, "duplicated": total != distinct}

# SK_ID_PREV 중복 (previous_application)
p = path_of("previous_application")
total = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p}')").fetchone()[0]
distinct = con.execute(f"SELECT COUNT(DISTINCT SK_ID_PREV) FROM read_csv_auto('{p}')").fetchone()[0]
key_checks["previous_application"] = {"key": "SK_ID_PREV", "total_rows": total, "distinct_keys": distinct, "duplicated": total != distinct}

print(key_checks)
results["key_checks"] = key_checks

# train/test SK_ID_CURR 겹침
p_train = path_of("application_train")
p_test = path_of("application_test")
overlap = con.execute(
    f"""
    SELECT COUNT(*) FROM
    (SELECT SK_ID_CURR FROM read_csv_auto('{p_train}')) a
    INNER JOIN (SELECT SK_ID_CURR FROM read_csv_auto('{p_test}')) b
    ON a.SK_ID_CURR = b.SK_ID_CURR
    """
).fetchone()[0]
results["train_test_overlap"] = overlap
print(f"\ntrain/test SK_ID_CURR 겹침: {overlap}건")

# 고아 레코드 (양방향) - 연결 구조: application -> bureau -> bureau_balance
#                                   application -> previous_application -> (POS_CASH, installments, credit_card)
print("\n=== 1-2. 고아 레코드 ===")
orphan_results = {}


def orphan_check(child_name, child_key, parent_name, parent_key):
    pc = path_of(child_name)
    pp = path_of(parent_name)
    child_total = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{pc}')").fetchone()[0]
    orphan_child = con.execute(
        f"""
        SELECT COUNT(*) FROM read_csv_auto('{pc}') c
        WHERE c.{child_key} NOT IN (SELECT {parent_key} FROM read_csv_auto('{pp}'))
        """
    ).fetchone()[0]
    parent_total = con.execute(f"SELECT COUNT(DISTINCT {parent_key}) FROM read_csv_auto('{pp}')").fetchone()[0]
    parent_unmatched = con.execute(
        f"""
        SELECT COUNT(*) FROM (SELECT DISTINCT {parent_key} FROM read_csv_auto('{pp}')) p
        WHERE p.{parent_key} NOT IN (SELECT DISTINCT {child_key} FROM read_csv_auto('{pc}'))
        """
    ).fetchone()[0]
    return {
        "child_total_rows": child_total,
        "child_orphan_rows": orphan_child,
        "child_orphan_pct": round(orphan_child / child_total * 100, 3) if child_total else None,
        "parent_total_distinct_keys": parent_total,
        "parent_unmatched_keys": parent_unmatched,
        "parent_unmatched_pct": round(parent_unmatched / parent_total * 100, 3) if parent_total else None,
    }


orphan_results["bureau_to_application"] = orphan_check("bureau", "SK_ID_CURR", "application_train", "SK_ID_CURR")
orphan_results["bureau_balance_to_bureau"] = orphan_check("bureau_balance", "SK_ID_BUREAU", "bureau", "SK_ID_BUREAU")
orphan_results["previous_application_to_application"] = orphan_check(
    "previous_application", "SK_ID_CURR", "application_train", "SK_ID_CURR"
)
orphan_results["POS_CASH_to_previous_application"] = orphan_check(
    "POS_CASH_balance", "SK_ID_PREV", "previous_application", "SK_ID_PREV"
)
orphan_results["installments_to_previous_application"] = orphan_check(
    "installments_payments", "SK_ID_PREV", "previous_application", "SK_ID_PREV"
)
orphan_results["credit_card_to_previous_application"] = orphan_check(
    "credit_card_balance", "SK_ID_PREV", "previous_application", "SK_ID_PREV"
)
print(json.dumps(orphan_results, indent=2, ensure_ascii=False))
results["orphan_results"] = orphan_results

# 참고: bureau/previous_application -> application 은 train+test 합쳐야 완전함.
# application_train 기준으로만 확인했으므로, test 포함 버전도 별도 계산.
p_bureau = path_of("bureau")
combined_ids_query = f"""
    SELECT COUNT(*) FROM read_csv_auto('{p_bureau}') c
    WHERE c.SK_ID_CURR NOT IN (
        SELECT SK_ID_CURR FROM read_csv_auto('{p_train}')
        UNION
        SELECT SK_ID_CURR FROM read_csv_auto('{p_test}')
    )
"""
bureau_orphan_combined = con.execute(combined_ids_query).fetchone()[0]
bureau_total = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p_bureau}')").fetchone()[0]
results["bureau_orphan_vs_train_plus_test"] = {
    "orphan_rows": bureau_orphan_combined,
    "total_rows": bureau_total,
    "orphan_pct": round(bureau_orphan_combined / bureau_total * 100, 4),
}
print("bureau orphan vs (train+test):", results["bureau_orphan_vs_train_plus_test"])

p_prev = path_of("previous_application")
prev_orphan_combined = con.execute(
    f"""
    SELECT COUNT(*) FROM read_csv_auto('{p_prev}') c
    WHERE c.SK_ID_CURR NOT IN (
        SELECT SK_ID_CURR FROM read_csv_auto('{p_train}')
        UNION
        SELECT SK_ID_CURR FROM read_csv_auto('{p_test}')
    )
    """
).fetchone()[0]
prev_total = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p_prev}')").fetchone()[0]
results["previous_application_orphan_vs_train_plus_test"] = {
    "orphan_rows": prev_orphan_combined,
    "total_rows": prev_total,
    "orphan_pct": round(prev_orphan_combined / prev_total * 100, 4),
}
print("previous_application orphan vs (train+test):", results["previous_application_orphan_vs_train_plus_test"])

# ---------------------------------------------------------------
# 1-3. 이력 보유 현황 (application_train 기준)
# ---------------------------------------------------------------
print("\n=== 1-3. 이력 보유 현황 ===")
n_train = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p_train}')").fetchone()[0]

history = {}


def history_coverage(child_name, child_key="SK_ID_CURR", via_prev=False):
    pc = path_of(child_name)
    if not via_prev:
        n_with = con.execute(
            f"""
            SELECT COUNT(DISTINCT t.SK_ID_CURR) FROM read_csv_auto('{p_train}') t
            WHERE t.SK_ID_CURR IN (SELECT DISTINCT SK_ID_CURR FROM read_csv_auto('{pc}'))
            """
        ).fetchone()[0]
    else:
        # child linked via SK_ID_PREV -> previous_application -> SK_ID_CURR
        n_with = con.execute(
            f"""
            SELECT COUNT(DISTINCT t.SK_ID_CURR) FROM read_csv_auto('{p_train}') t
            WHERE t.SK_ID_CURR IN (
                SELECT DISTINCT pa.SK_ID_CURR FROM read_csv_auto('{pc}') c
                JOIN read_csv_auto('{p_prev}') pa ON c.SK_ID_PREV = pa.SK_ID_PREV
            )
            """
        ).fetchone()[0]
    return {"n_with_history": n_with, "pct_with_history": round(n_with / n_train * 100, 2)}


history["bureau"] = history_coverage("bureau")
history["previous_application"] = history_coverage("previous_application")
history["installments_payments"] = history_coverage("installments_payments", via_prev=True)
history["credit_card_balance"] = history_coverage("credit_card_balance", via_prev=True)
history["POS_CASH_balance"] = history_coverage("POS_CASH_balance", via_prev=True)

# 어떤 이력도 없는 신청자
n_no_history = con.execute(
    f"""
    SELECT COUNT(*) FROM read_csv_auto('{p_train}') t
    WHERE t.SK_ID_CURR NOT IN (SELECT DISTINCT SK_ID_CURR FROM read_csv_auto('{path_of("bureau")}'))
      AND t.SK_ID_CURR NOT IN (SELECT DISTINCT SK_ID_CURR FROM read_csv_auto('{p_prev}'))
    """
).fetchone()[0]
history["no_history_at_all"] = {"n": n_no_history, "pct": round(n_no_history / n_train * 100, 2)}
history["n_train_total"] = n_train

print(json.dumps(history, indent=2, ensure_ascii=False))
results["history"] = history

# ---------------------------------------------------------------
# 1-4. TARGET 확인 (분포만)
# ---------------------------------------------------------------
print("\n=== 1-4. TARGET 분포 ===")
target_dist = con.execute(
    f"""
    SELECT TARGET, COUNT(*) as cnt
    FROM read_csv_auto('{p_train}')
    GROUP BY TARGET
    ORDER BY TARGET
    """
).fetchdf()
target_dist["pct"] = (target_dist["cnt"] / target_dist["cnt"].sum() * 100).round(3)
print(target_dist)
results["target_distribution"] = target_dist.to_dict(orient="records")

# test에 TARGET 컬럼 존재 여부
test_cols = con.execute(f"SELECT * FROM read_csv_auto('{p_test}') LIMIT 0").description
test_colnames = [c[0] for c in test_cols]
results["test_has_target_column"] = "TARGET" in test_colnames

# TARGET 정의 원문 인용 (컬럼 설명 파일에서)
desc_path = os.path.join(RAW, "HomeCredit_columns_description.csv")
desc_df = pd.read_csv(desc_path, encoding="cp1252", index_col=0)
target_row = desc_df[(desc_df["Row"] == "TARGET")]
results["target_definition_raw"] = target_row.to_dict(orient="records")
print("TARGET 정의:", results["target_definition_raw"])

# 시각화: TARGET 분포
fig, ax = plt.subplots(figsize=(5, 4))
ax.bar(target_dist["TARGET"].astype(str), target_dist["cnt"], color=["#4C72B0", "#DD8452"])
for i, row in target_dist.iterrows():
    ax.text(i, row["cnt"], f"{row['cnt']:,}\n({row['pct']}%)", ha="center", va="bottom")
ax.set_xlabel("TARGET (0=정상상환, 1=연체)")
ax.set_ylabel("건수")
ax.set_title("application_train TARGET 분포")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "target_distribution.png"), dpi=120)
plt.close()

# ---------------------------------------------------------------
# 1-5. 데이터 품질
# ---------------------------------------------------------------
print("\n=== 1-5. 데이터 품질: 결측률 ===")

missing_summary = {}
missing_bucket_summary = {}

for name in FILES:
    p = path_of(name)
    cols = [c[0] for c in con.execute(f"SELECT * FROM read_csv_auto('{p}') LIMIT 0").description]
    total_rows = file_info[name]["n_rows"]
    # 결측률을 DuckDB로 한번에 계산
    select_parts = ", ".join([f"SUM(CASE WHEN \"{c}\" IS NULL THEN 1 ELSE 0 END) AS \"{c}\"" for c in cols])
    null_counts = con.execute(f"SELECT {select_parts} FROM read_csv_auto('{p}')").fetchdf().iloc[0]
    miss_pct = (null_counts / total_rows * 100).round(3)
    missing_summary[name] = miss_pct.to_dict()

    bucket = {"0%": 0, "0~10%": 0, "10~50%": 0, "50%+": 0}
    for v in miss_pct:
        if v == 0:
            bucket["0%"] += 1
        elif v <= 10:
            bucket["0~10%"] += 1
        elif v <= 50:
            bucket["10~50%"] += 1
        else:
            bucket["50%+"] += 1
    missing_bucket_summary[name] = bucket

print(json.dumps(missing_bucket_summary, indent=2, ensure_ascii=False))
results["missing_bucket_summary"] = missing_bucket_summary
results["missing_summary"] = missing_summary

# 결측률 분포 시각화 (application_train)
fig, ax = plt.subplots(figsize=(6, 4))
vals = list(missing_bucket_summary["application_train"].values())
labels = list(missing_bucket_summary["application_train"].keys())
ax.bar(labels, vals, color="#55A868")
for i, v in enumerate(vals):
    ax.text(i, v, str(v), ha="center", va="bottom")
ax.set_xlabel("결측률 구간")
ax.set_ylabel("컬럼 수")
ax.set_title("application_train 컬럼별 결측률 분포")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "missing_rate_distribution.png"), dpi=120)
plt.close()

# 상수/준상수 컬럼, 중복 행
print("\n=== 1-5. 상수/준상수 컬럼, 중복 행 ===")
constant_cols = {}
duplicate_rows = {}
for name in FILES:
    p = path_of(name)
    total_rows = file_info[name]["n_rows"]
    cols = [c[0] for c in con.execute(f"SELECT * FROM read_csv_auto('{p}') LIMIT 0").description]
    const_list = []
    for c in cols:
        top_pct = con.execute(
            f"""
            SELECT COUNT(*) * 1.0 / {total_rows} as pct
            FROM read_csv_auto('{p}')
            GROUP BY "{c}"
            ORDER BY COUNT(*) DESC
            LIMIT 1
            """
        ).fetchone()[0]
        if top_pct >= 0.999:
            const_list.append({"col": c, "top_value_pct": round(top_pct * 100, 3)})
    constant_cols[name] = const_list

    col_list = ", ".join(f'"{c}"' for c in cols)
    dup_count = con.execute(
        f"""
        SELECT COALESCE(SUM(cnt - 1), 0) FROM (
            SELECT COUNT(*) as cnt FROM read_csv_auto('{p}') GROUP BY {col_list}
        ) WHERE cnt > 1
        """
    ).fetchone()[0]
    duplicate_rows[name] = dup_count or 0

print("상수/준상수 컬럼:", json.dumps(constant_cols, indent=2, ensure_ascii=False))
print("중복 행:", duplicate_rows)
results["constant_cols"] = constant_cols
results["duplicate_rows"] = duplicate_rows

# 이상값: DAYS_ 컬럼
print("\n=== 1-5. DAYS_ 컬럼 이상값 ===")
days_anomalies = {}
for name in FILES:
    p = path_of(name)
    cols = [c[0] for c in con.execute(f"SELECT * FROM read_csv_auto('{p}') LIMIT 0").description]
    days_cols = [c for c in cols if c.startswith("DAYS_")]
    for c in days_cols:
        stats = con.execute(
            f"""
            SELECT MIN("{c}") as min_v, MAX("{c}") as max_v,
                   SUM(CASE WHEN "{c}" > 0 THEN 1 ELSE 0 END) as n_positive,
                   SUM(CASE WHEN "{c}" = 365243 THEN 1 ELSE 0 END) as n_365243
            FROM read_csv_auto('{p}')
            """
        ).fetchdf().iloc[0]
        days_anomalies[f"{name}.{c}"] = {
            "min": stats["min_v"], "max": stats["max_v"],
            "n_positive": int(stats["n_positive"]), "n_365243": int(stats["n_365243"]),
        }
print(json.dumps(days_anomalies, indent=2, ensure_ascii=False, default=str))
results["days_anomalies"] = days_anomalies

# 범주형 특수값 (XNA, XAP, Unknown)
print("\n=== 1-5. 범주형 특수값 ===")
special_cat_values = {}
SPECIAL_VALUES = ["XNA", "XAP", "Unknown", "Unknown type of loan"]
for name in FILES:
    p = path_of(name)
    schema = con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{p}')").fetchdf()
    str_cols = schema[schema["column_type"].isin(["VARCHAR"])]["column_name"].tolist()
    for c in str_cols:
        for sv in SPECIAL_VALUES:
            try:
                cnt = con.execute(
                    f"SELECT COUNT(*) FROM read_csv_auto('{p}') WHERE \"{c}\" = ?", [sv]
                ).fetchone()[0]
            except Exception:
                cnt = 0
            if cnt > 0:
                special_cat_values[f"{name}.{c}.{sv}"] = cnt
print(json.dumps(special_cat_values, indent=2, ensure_ascii=False))
results["special_cat_values"] = special_cat_values

# 금액 컬럼 음수/극단값 (AMT_ 컬럼)
print("\n=== 1-5. AMT_ 컬럼 이상값 ===")
amt_anomalies = {}
for name in FILES:
    p = path_of(name)
    cols = [c[0] for c in con.execute(f"SELECT * FROM read_csv_auto('{p}') LIMIT 0").description]
    amt_cols = [c for c in cols if c.startswith("AMT_")]
    for c in amt_cols:
        try:
            stats = con.execute(
                f"""
                SELECT MIN("{c}") as min_v, MAX("{c}") as max_v,
                       SUM(CASE WHEN "{c}" < 0 THEN 1 ELSE 0 END) as n_negative,
                       QUANTILE_CONT("{c}", 0.999) as p999
                FROM read_csv_auto('{p}')
                """
            ).fetchdf().iloc[0]
            amt_anomalies[f"{name}.{c}"] = {
                "min": stats["min_v"], "max": stats["max_v"],
                "n_negative": int(stats["n_negative"]), "p99.9": stats["p999"],
            }
        except Exception as e:
            amt_anomalies[f"{name}.{c}"] = {"error": str(e)}
print(json.dumps(amt_anomalies, indent=2, ensure_ascii=False, default=str))
results["amt_anomalies"] = amt_anomalies

# CODE_GENDER 등 범주형 극소수 범주
gender_check = con.execute(
    f"SELECT CODE_GENDER, COUNT(*) as cnt FROM read_csv_auto('{p_train}') GROUP BY CODE_GENDER ORDER BY cnt DESC"
).fetchdf()
results["gender_check"] = gender_check.to_dict(orient="records")
print("CODE_GENDER:", gender_check)

# ---------------------------------------------------------------
# 1-6. 시간 정보와 누수 위험
# ---------------------------------------------------------------
print("\n=== 1-6. 시간 정보 ===")
# 절대 날짜 컬럼 존재 여부 확인 (스키마 기반)
schema_train = con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{p_train}')").fetchdf()
date_like_cols = schema_train[schema_train["column_type"].isin(["DATE", "TIMESTAMP"])]
results["absolute_date_columns"] = date_like_cols.to_dict(orient="records")
print("절대 날짜형 컬럼:", date_like_cols)

# 신청 이후 정보 의심: MONTHS_BALANCE > 0 (POS_CASH, credit_card, bureau_balance)
leakage_candidates = {}
for name in ["POS_CASH_balance", "credit_card_balance", "bureau_balance"]:
    p = path_of(name)
    cnt = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p}') WHERE MONTHS_BALANCE > 0").fetchone()[0]
    total = file_info[name]["n_rows"]
    leakage_candidates[name] = {"col": "MONTHS_BALANCE", "n_future": cnt, "pct_future": round(cnt / total * 100, 4)}

# previous_application의 DAYS_ 컬럼 중 양수(미래) 값
p_prev_path = path_of("previous_application")
prev_cols = [c[0] for c in con.execute(f"SELECT * FROM read_csv_auto('{p_prev_path}') LIMIT 0").description]
for c in [c for c in prev_cols if c.startswith("DAYS_")]:
    cnt = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p_prev_path}') WHERE \"{c}\" > 0 AND \"{c}\" != 365243").fetchone()[0]
    leakage_candidates[f"previous_application.{c}"] = {"col": c, "n_future_excl_365243": cnt}

print(json.dumps(leakage_candidates, indent=2, ensure_ascii=False))
results["leakage_candidates"] = leakage_candidates

# 저장
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)

print(f"\n완료. 결과 저장: {OUT_JSON}")
con.close()
