"""
02_variable_catalog.py
Loan Approval Risk Scoring - v2 재분석
2단계: 변수 파악 (업무 의미별 분류, 분포 요약)

실행: python3 v2/scripts/02_variable_catalog.py
출력: v2/docs/catalog_results.json
주의: TARGET과의 관계는 계산하지 않음. 각 변수의 분포만 요약.
"""
import json
import os
import duckdb
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
OUT_JSON = os.path.join(ROOT, "v2", "docs", "catalog_results.json")

con = duckdb.connect()
p_train = os.path.join(RAW, "application_train.csv")

desc_path = os.path.join(RAW, "HomeCredit_columns_description.csv")
desc_df = pd.read_csv(desc_path, encoding="cp1252", index_col=0)
desc_map = {}
for _, r in desc_df[desc_df["Table"] == "application_{train|test}.csv"].iterrows():
    desc_map[r["Row"]] = r["Description"]

# ---------------------------------------------------------------
# 2-1. application_train 변수 카탈로그: 업무 의미별 분류
# ---------------------------------------------------------------
CATEGORY_MAP = {
    "SK_ID_CURR": "식별자",
    "TARGET": "타겟",
    "NAME_CONTRACT_TYPE": "대출 조건",
    "AMT_CREDIT": "대출 조건",
    "AMT_ANNUITY": "대출 조건",
    "AMT_GOODS_PRICE": "대출 조건",
    "WEEKDAY_APPR_PROCESS_START": "신청 시점",
    "HOUR_APPR_PROCESS_START": "신청 시점",
    "CODE_GENDER": "인적 사항",
    "CNT_CHILDREN": "가족",
    "CNT_FAM_MEMBERS": "가족",
    "NAME_FAMILY_STATUS": "가족",
    "NAME_TYPE_SUITE": "가족",
    "AMT_INCOME_TOTAL": "소득·재산",
    "FLAG_OWN_CAR": "소득·재산",
    "FLAG_OWN_REALTY": "소득·재산",
    "OWN_CAR_AGE": "소득·재산",
    "NAME_INCOME_TYPE": "고용·직업",
    "NAME_EDUCATION_TYPE": "고용·직업",
    "OCCUPATION_TYPE": "고용·직업",
    "ORGANIZATION_TYPE": "고용·직업",
    "DAYS_EMPLOYED": "고용·직업",
    "DAYS_BIRTH": "인적 사항",
    "DAYS_REGISTRATION": "인적 사항",
    "DAYS_ID_PUBLISH": "인적 사항",
    "DAYS_LAST_PHONE_CHANGE": "연락처·서류 제출 여부",
    "NAME_HOUSING_TYPE": "거주지·지역",
    "REGION_POPULATION_RELATIVE": "거주지·지역",
    "REGION_RATING_CLIENT": "거주지·지역",
    "REGION_RATING_CLIENT_W_CITY": "거주지·지역",
    "REG_REGION_NOT_LIVE_REGION": "거주지·지역",
    "REG_REGION_NOT_WORK_REGION": "거주지·지역",
    "LIVE_REGION_NOT_WORK_REGION": "거주지·지역",
    "REG_CITY_NOT_LIVE_CITY": "거주지·지역",
    "REG_CITY_NOT_WORK_CITY": "거주지·지역",
    "LIVE_CITY_NOT_WORK_CITY": "거주지·지역",
    "EXT_SOURCE_1": "외부 신용점수",
    "EXT_SOURCE_2": "외부 신용점수",
    "EXT_SOURCE_3": "외부 신용점수",
    "OBS_30_CNT_SOCIAL_CIRCLE": "주변인 연체 관측",
    "DEF_30_CNT_SOCIAL_CIRCLE": "주변인 연체 관측",
    "OBS_60_CNT_SOCIAL_CIRCLE": "주변인 연체 관측",
    "DEF_60_CNT_SOCIAL_CIRCLE": "주변인 연체 관측",
    "FLAG_MOBIL": "연락처·서류 제출 여부",
    "FLAG_EMP_PHONE": "연락처·서류 제출 여부",
    "FLAG_WORK_PHONE": "연락처·서류 제출 여부",
    "FLAG_CONT_MOBILE": "연락처·서류 제출 여부",
    "FLAG_PHONE": "연락처·서류 제출 여부",
    "FLAG_EMAIL": "연락처·서류 제출 여부",
}
for i in range(2, 22):
    CATEGORY_MAP[f"FLAG_DOCUMENT_{i}"] = "연락처·서류 제출 여부"
for suffix in ["AMT_REQ_CREDIT_BUREAU_HOUR", "AMT_REQ_CREDIT_BUREAU_DAY", "AMT_REQ_CREDIT_BUREAU_WEEK",
               "AMT_REQ_CREDIT_BUREAU_MON", "AMT_REQ_CREDIT_BUREAU_QRT", "AMT_REQ_CREDIT_BUREAU_YEAR"]:
    CATEGORY_MAP[suffix] = "신용조회 이력"

all_cols = [c[0] for c in con.execute(f"SELECT * FROM read_csv_auto('{p_train}') LIMIT 0").description]
for c in all_cols:
    if c in CATEGORY_MAP:
        continue
    if any(c.endswith(suf) for suf in ["_AVG", "_MODE", "_MEDI"]) or c in (
        "FONDKAPREMONT_MODE", "HOUSETYPE_MODE", "TOTALAREA_MODE", "WALLSMATERIAL_MODE", "EMERGENCYSTATE_MODE"
    ):
        CATEGORY_MAP[c] = "주택 건물 정보"
    else:
        CATEGORY_MAP[c] = "기타"

n_train = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p_train}')").fetchone()[0]
schema = con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{p_train}')").fetchdf()
dtype_map = dict(zip(schema["column_name"], schema["column_type"]))

catalog = []
for c in all_cols:
    dtype = dtype_map[c]
    n_null = con.execute(f"SELECT SUM(CASE WHEN \"{c}\" IS NULL THEN 1 ELSE 0 END) FROM read_csv_auto('{p_train}')").fetchone()[0]
    n_unique = con.execute(f"SELECT COUNT(DISTINCT \"{c}\") FROM read_csv_auto('{p_train}')").fetchone()[0]
    entry = {
        "column": c,
        "category": CATEGORY_MAP.get(c, "기타"),
        "description_en": desc_map.get(c, ""),
        "dtype": dtype,
        "missing_pct": round(n_null / n_train * 100, 3),
        "n_unique": n_unique,
    }
    if dtype in ("BIGINT", "DOUBLE", "INTEGER", "HUGEINT"):
        stats = con.execute(
            f"SELECT MIN(\"{c}\"), MEDIAN(\"{c}\"), MAX(\"{c}\") FROM read_csv_auto('{p_train}')"
        ).fetchone()
        entry["min"] = stats[0]
        entry["median"] = stats[1]
        entry["max"] = stats[2]
    else:
        top = con.execute(
            f"""
            SELECT "{c}", COUNT(*) as cnt FROM read_csv_auto('{p_train}')
            GROUP BY "{c}" ORDER BY cnt DESC LIMIT 5
            """
        ).fetchdf()
        entry["top_categories"] = top.to_dict(orient="records")
    catalog.append(entry)

print(f"카탈로그 변수 수: {len(catalog)}")

# 분류별 개수
from collections import Counter
cat_counts = Counter(c["category"] for c in catalog)
print(json.dumps(dict(cat_counts), ensure_ascii=False, indent=2))

# ---------------------------------------------------------------
# 2-2. 하위 테이블 요약
# ---------------------------------------------------------------
sub_tables = {
    "bureau": "bureau.csv",
    "bureau_balance": "bureau_balance.csv",
    "previous_application": "previous_application.csv",
    "POS_CASH_balance": "POS_CASH_balance.csv",
    "installments_payments": "installments_payments.csv",
    "credit_card_balance": "credit_card_balance.csv",
}

sub_summary = {}
p_prev = os.path.join(RAW, "previous_application.csv")

for name, fname in sub_tables.items():
    p = os.path.join(RAW, fname)
    cols = [c[0] for c in con.execute(f"SELECT * FROM read_csv_auto('{p}') LIMIT 0").description]
    n_rows = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p}')").fetchone()[0]

    if name == "bureau":
        key = "SK_ID_CURR"
    else:
        key = "SK_ID_PREV" if "SK_ID_PREV" in cols else "SK_ID_BUREAU"

    if name == "bureau_balance":
        per_entity = con.execute(
            f"SELECT COUNT(*) * 1.0 / COUNT(DISTINCT SK_ID_BUREAU) FROM read_csv_auto('{p}')"
        ).fetchone()[0]
        max_per_entity = con.execute(
            f"SELECT MAX(cnt) FROM (SELECT COUNT(*) as cnt FROM read_csv_auto('{p}') GROUP BY SK_ID_BUREAU)"
        ).fetchone()[0]
        median_per_entity = con.execute(
            f"SELECT MEDIAN(cnt) FROM (SELECT COUNT(*) as cnt FROM read_csv_auto('{p}') GROUP BY SK_ID_BUREAU)"
        ).fetchone()[0]
    elif name == "bureau":
        per_entity = con.execute(
            f"SELECT COUNT(*) * 1.0 / COUNT(DISTINCT SK_ID_CURR) FROM read_csv_auto('{p}')"
        ).fetchone()[0]
        max_per_entity = con.execute(
            f"SELECT MAX(cnt) FROM (SELECT COUNT(*) as cnt FROM read_csv_auto('{p}') GROUP BY SK_ID_CURR)"
        ).fetchone()[0]
        median_per_entity = con.execute(
            f"SELECT MEDIAN(cnt) FROM (SELECT COUNT(*) as cnt FROM read_csv_auto('{p}') GROUP BY SK_ID_CURR)"
        ).fetchone()[0]
    else:
        # per applicant (SK_ID_CURR) via previous_application join, and also per SK_ID_PREV
        per_entity = con.execute(
            f"SELECT COUNT(*) * 1.0 / COUNT(DISTINCT SK_ID_PREV) FROM read_csv_auto('{p}')"
        ).fetchone()[0]
        max_per_entity = con.execute(
            f"SELECT MAX(cnt) FROM (SELECT COUNT(*) as cnt FROM read_csv_auto('{p}') GROUP BY SK_ID_PREV)"
        ).fetchone()[0]
        median_per_entity = con.execute(
            f"SELECT MEDIAN(cnt) FROM (SELECT COUNT(*) as cnt FROM read_csv_auto('{p}') GROUP BY SK_ID_PREV)"
        ).fetchone()[0]

    sub_summary[name] = {
        "n_rows": n_rows,
        "n_cols": len(cols),
        "columns": cols,
        "avg_rows_per_entity": round(per_entity, 2),
        "median_rows_per_entity": median_per_entity,
        "max_rows_per_entity": max_per_entity,
    }

print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "columns"} for k, v in sub_summary.items()}, indent=2, ensure_ascii=False))

results = {
    "catalog": catalog,
    "category_counts": dict(cat_counts),
    "sub_table_summary": sub_summary,
}

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)

print(f"완료. 결과 저장: {OUT_JSON}")
con.close()
