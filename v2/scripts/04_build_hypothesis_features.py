"""
04_build_hypothesis_features.py
Loan Approval Risk Scoring - v2 재분석
3단계: 가설(H1~H5) 검증을 위한 신청자(SK_ID_CURR) 단위 변수 생성.

대상: application_train 307,511명 전체 (분할과 무관하게 변수는 전체에 대해 생성,
TARGET 관련 계산은 05번 스크립트에서 학습 세트로만 제한한다).

연결 경로 원칙: 하위 테이블은 "진짜 고아"(SK_ID_PREV/SK_ID_BUREAU가 상위 키에 없는 행)를
제외한 뒤, 각 테이블이 자체적으로 가진 SK_ID_CURR 기준으로 신청자에 직접 붙인다
(installments_payments/POS_CASH_balance/credit_card_balance는 모두 SK_ID_CURR을
자체 보유하므로 previous_application을 거치지 않고 직접 연결한다). bureau_balance만
SK_ID_CURR이 없어 bureau를 거쳐 연결한다.

이력이 없는 신청자는 NULL로 둔다(0으로 채우지 않는다) - 과거 이력이 '없음'과
'0건/0%로 양호함'은 다른 의미이기 때문이다.

누수 방지: previous_application의 DAYS_LAST_DUE_1ST_VERSION/DAYS_LAST_DUE/
DAYS_TERMINATION은 사용하지 않는다. 시간창 계산은 0 이하 DAYS_* 값만 사용한다
(365243 등 특수값은 사전에 NULL 처리).

실행: python3 -I v2/scripts/04_build_hypothesis_features.py
출력: v2/data/features/hypothesis_features.parquet, v2/docs/feature_build_log.json
"""
import json
import os
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
FEAT_DIR = os.path.join(ROOT, "v2", "data", "features")
os.makedirs(FEAT_DIR, exist_ok=True)
OUT_PARQUET = os.path.join(FEAT_DIR, "hypothesis_features.parquet")
OUT_LOG = os.path.join(ROOT, "v2", "docs", "feature_build_log.json")

con = duckdb.connect()


def p(name):
    return os.path.join(RAW, name)


p_train = p("application_train.csv")
p_bureau = p("bureau.csv")
p_bureau_balance = p("bureau_balance.csv")
p_prev = p("previous_application.csv")
p_pos = p("POS_CASH_balance.csv")
p_inst = p("installments_payments.csv")
p_cc = p("credit_card_balance.csv")

# 전체 application_train 컬럼 확인 (제외 대상 처리를 위해)
all_app_cols = [c[0] for c in con.execute(f"SELECT * FROM read_csv_auto('{p_train}') LIMIT 0").description]

EXCLUDE_ALWAYS = {
    "CODE_GENDER",
    "OBS_30_CNT_SOCIAL_CIRCLE", "DEF_30_CNT_SOCIAL_CIRCLE",
    "OBS_60_CNT_SOCIAL_CIRCLE", "DEF_60_CNT_SOCIAL_CIRCLE",
}
# H1~H5 핵심/보조 변수 생성에 이미 쓰여 raw passthrough에서 제외할 컬럼
USED_IN_DERIVED = {
    "TARGET",
    "AMT_ANNUITY", "AMT_INCOME_TOTAL", "AMT_CREDIT", "AMT_GOODS_PRICE",
    "DAYS_EMPLOYED", "DAYS_REGISTRATION", "DAYS_ID_PUBLISH", "DAYS_LAST_PHONE_CHANGE",
    "DAYS_BIRTH", "NAME_CONTRACT_TYPE",
    "AMT_REQ_CREDIT_BUREAU_HOUR", "AMT_REQ_CREDIT_BUREAU_DAY", "AMT_REQ_CREDIT_BUREAU_WEEK",
    "AMT_REQ_CREDIT_BUREAU_MON", "AMT_REQ_CREDIT_BUREAU_QRT", "AMT_REQ_CREDIT_BUREAU_YEAR",
    "EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3",
}
remainder_cols = [c for c in all_app_cols if c != "SK_ID_CURR"
                  and c not in EXCLUDE_ALWAYS and c not in USED_IN_DERIVED]
print(f"부록(appendix) IV용 잔여 컬럼 수: {len(remainder_cols)}")

remainder_select = ", ".join(f'app."{c}"' for c in remainder_cols)

query = f"""
WITH app_base AS (
    SELECT
        SK_ID_CURR,
        AMT_ANNUITY, AMT_INCOME_TOTAL, AMT_CREDIT, AMT_GOODS_PRICE,
        NAME_CONTRACT_TYPE,
        CASE WHEN DAYS_EMPLOYED = 365243 THEN NULL ELSE -DAYS_EMPLOYED END AS employment_days,
        CASE WHEN DAYS_EMPLOYED = 365243 THEN 1 ELSE 0 END AS unemployed_flag,
        -DAYS_REGISTRATION AS registration_days,
        -DAYS_ID_PUBLISH AS id_publish_days,
        -DAYS_LAST_PHONE_CHANGE AS phone_change_days,
        -DAYS_BIRTH / 365.25 AS age_years,
        EXT_SOURCE_1, EXT_SOURCE_2, EXT_SOURCE_3,
        AMT_REQ_CREDIT_BUREAU_HOUR + AMT_REQ_CREDIT_BUREAU_DAY + AMT_REQ_CREDIT_BUREAU_WEEK
            + AMT_REQ_CREDIT_BUREAU_MON + AMT_REQ_CREDIT_BUREAU_QRT + AMT_REQ_CREDIT_BUREAU_YEAR
            AS total_credit_bureau_inquiries,
        {remainder_select}
    FROM read_csv_auto('{p_train}') app
),

bureau_agg AS (
    SELECT
        SK_ID_CURR,
        COUNT(*) AS n_bureau_records,
        SUM(CASE WHEN CREDIT_ACTIVE = 'Active' THEN 1 ELSE 0 END) AS active_loan_count,
        SUM(CASE WHEN CREDIT_ACTIVE = 'Active' THEN AMT_CREDIT_SUM_DEBT ELSE 0 END) AS active_loan_debt_sum,
        MAX(CASE WHEN CREDIT_DAY_OVERDUE > 0 OR AMT_CREDIT_SUM_OVERDUE > 0 THEN 1 ELSE 0 END) AS bureau_currently_overdue_flag,
        MAX(AMT_CREDIT_MAX_OVERDUE) AS bureau_max_overdue_amt,
        SUM(CASE WHEN DAYS_CREDIT >= -365 THEN 1 ELSE 0 END) AS bureau_recent_1yr_new_loans
    FROM read_csv_auto('{p_bureau}')
    GROUP BY SK_ID_CURR
),

bureau_balance_joined AS (
    -- 진짜 고아(bureau에 SK_ID_BUREAU 없음) 제외 후 bureau를 거쳐 SK_ID_CURR 연결
    SELECT b.SK_ID_CURR, bb.STATUS
    FROM read_csv_auto('{p_bureau_balance}') bb
    INNER JOIN read_csv_auto('{p_bureau}') b ON bb.SK_ID_BUREAU = b.SK_ID_BUREAU
),
bureau_balance_agg AS (
    SELECT
        SK_ID_CURR,
        COUNT(*) AS n_bureau_balance_records,
        AVG(CASE WHEN STATUS IN ('1','2','3','4','5') THEN 1.0 ELSE 0.0 END) AS bureau_balance_delinquent_month_ratio
    FROM bureau_balance_joined
    GROUP BY SK_ID_CURR
),

prev_agg AS (
    SELECT
        SK_ID_CURR,
        COUNT(*) AS n_prev_records,
        AVG(CASE WHEN NAME_CONTRACT_STATUS = 'Refused' THEN 1.0 ELSE 0.0 END) AS reject_ratio,
        SUM(CASE WHEN NAME_CONTRACT_STATUS = 'Refused' AND DAYS_DECISION >= -365 THEN 1 ELSE 0 END) AS recent_1yr_reject_count,
        SUM(CASE WHEN DAYS_DECISION >= -365 THEN 1 ELSE 0 END) AS recent_1yr_apply_count
    FROM read_csv_auto('{p_prev}')
    GROUP BY SK_ID_CURR
),

-- 진짜 고아(previous_application에 SK_ID_PREV 없음) 제외 후 각 테이블의 자체 SK_ID_CURR로 직접 연결
inst_filtered AS (
    SELECT i.*
    FROM read_csv_auto('{p_inst}') i
    WHERE i.SK_ID_PREV IN (SELECT SK_ID_PREV FROM read_csv_auto('{p_prev}'))
),
inst_agg AS (
    SELECT
        SK_ID_CURR,
        COUNT(*) AS n_installment_records,
        AVG(CASE WHEN DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT THEN 1.0 ELSE 0.0 END) AS late_payment_ratio,
        AVG(CASE WHEN AMT_PAYMENT < AMT_INSTALMENT THEN 1.0 ELSE 0.0 END) AS underpay_ratio,
        AVG(CASE WHEN DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT THEN DAYS_ENTRY_PAYMENT - DAYS_INSTALMENT END) AS avg_delay_days,
        SUM(CASE WHEN DAYS_INSTALMENT >= -365 AND DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT THEN 1 ELSE 0 END) * 1.0
            / NULLIF(SUM(CASE WHEN DAYS_INSTALMENT >= -365 THEN 1 ELSE 0 END), 0) AS recent_1yr_late_ratio
    FROM inst_filtered
    GROUP BY SK_ID_CURR
),

pos_filtered AS (
    SELECT c.*
    FROM read_csv_auto('{p_pos}') c
    WHERE c.SK_ID_PREV IN (SELECT SK_ID_PREV FROM read_csv_auto('{p_prev}'))
),
pos_agg AS (
    SELECT
        SK_ID_CURR,
        COUNT(*) AS n_pos_records,
        AVG(CASE WHEN SK_DPD > 0 THEN 1.0 ELSE 0.0 END) AS pos_dpd_month_ratio
    FROM pos_filtered
    GROUP BY SK_ID_CURR
),

cc_filtered AS (
    SELECT c.*
    FROM read_csv_auto('{p_cc}') c
    WHERE c.SK_ID_PREV IN (SELECT SK_ID_PREV FROM read_csv_auto('{p_prev}'))
),
cc_agg AS (
    SELECT
        SK_ID_CURR,
        COUNT(*) AS n_cc_records,
        AVG(CASE WHEN SK_DPD > 0 THEN 1.0 ELSE 0.0 END) AS cc_dpd_month_ratio
    FROM cc_filtered
    GROUP BY SK_ID_CURR
),
cc_latest AS (
    SELECT SK_ID_CURR, SK_ID_PREV, AMT_BALANCE, AMT_CREDIT_LIMIT_ACTUAL,
           ROW_NUMBER() OVER (PARTITION BY SK_ID_PREV ORDER BY MONTHS_BALANCE DESC) AS rn
    FROM cc_filtered
),
cc_util_agg AS (
    SELECT
        SK_ID_CURR,
        SUM(AMT_BALANCE) * 1.0 / NULLIF(SUM(AMT_CREDIT_LIMIT_ACTUAL), 0) AS card_utilization
    FROM cc_latest
    WHERE rn = 1
    GROUP BY SK_ID_CURR
)

SELECT
    a.*,
    a.AMT_ANNUITY / NULLIF(a.AMT_INCOME_TOTAL, 0) AS annuity_to_income,
    a.AMT_CREDIT / NULLIF(a.AMT_INCOME_TOTAL, 0) AS credit_to_income,
    a.AMT_CREDIT / NULLIF(a.AMT_GOODS_PRICE, 0) AS credit_to_goods,
    a.AMT_CREDIT / NULLIF(a.AMT_ANNUITY, 0) AS credit_to_annuity,
    CASE WHEN a.EXT_SOURCE_1 IS NULL AND a.EXT_SOURCE_2 IS NULL AND a.EXT_SOURCE_3 IS NULL THEN NULL
         ELSE (COALESCE(a.EXT_SOURCE_1,0) + COALESCE(a.EXT_SOURCE_2,0) + COALESCE(a.EXT_SOURCE_3,0))
              / (CASE WHEN a.EXT_SOURCE_1 IS NOT NULL THEN 1 ELSE 0 END
                 + CASE WHEN a.EXT_SOURCE_2 IS NOT NULL THEN 1 ELSE 0 END
                 + CASE WHEN a.EXT_SOURCE_3 IS NOT NULL THEN 1 ELSE 0 END)
    END AS ext_source_mean,

    ba.n_bureau_records, ba.active_loan_count,
    ba.active_loan_debt_sum / NULLIF(a.AMT_INCOME_TOTAL, 0) AS debt_to_income,
    ba.bureau_currently_overdue_flag, ba.bureau_max_overdue_amt, ba.bureau_recent_1yr_new_loans,

    bba.n_bureau_balance_records, bba.bureau_balance_delinquent_month_ratio,

    pa.n_prev_records, pa.reject_ratio, pa.recent_1yr_reject_count, pa.recent_1yr_apply_count,

    ia.n_installment_records, ia.late_payment_ratio, ia.underpay_ratio, ia.avg_delay_days, ia.recent_1yr_late_ratio,

    pca.n_pos_records, pca.pos_dpd_month_ratio,

    cca.n_cc_records, cca.cc_dpd_month_ratio, cua.card_utilization,

    -- 이력 보유 플래그 (가설5-3 "이력 없는 신청자" 식별용)
    CASE WHEN ba.n_bureau_records IS NULL AND pa.n_prev_records IS NULL THEN 1 ELSE 0 END AS no_history_at_all_flag

FROM app_base a
LEFT JOIN bureau_agg ba ON a.SK_ID_CURR = ba.SK_ID_CURR
LEFT JOIN bureau_balance_agg bba ON a.SK_ID_CURR = bba.SK_ID_CURR
LEFT JOIN prev_agg pa ON a.SK_ID_CURR = pa.SK_ID_CURR
LEFT JOIN inst_agg ia ON a.SK_ID_CURR = ia.SK_ID_CURR
LEFT JOIN pos_agg pca ON a.SK_ID_CURR = pca.SK_ID_CURR
LEFT JOIN cc_agg cca ON a.SK_ID_CURR = cca.SK_ID_CURR
LEFT JOIN cc_util_agg cua ON a.SK_ID_CURR = cua.SK_ID_CURR
"""

# ORGANIZATION_TYPE / NAME_FAMILY_STATUS 특수값(XNA/Unknown) NULL 처리는 후처리에서 수행
print("특징 테이블 생성 쿼리 실행 중...")
con.execute(f"COPY ({query}) TO '{OUT_PARQUET}' (FORMAT PARQUET)")

n_rows = con.execute(f"SELECT COUNT(*) FROM read_parquet('{OUT_PARQUET}')").fetchone()[0]
n_cols = len(con.execute(f"SELECT * FROM read_parquet('{OUT_PARQUET}') LIMIT 0").description)
print(f"생성 완료: {n_rows:,}행 x {n_cols}열 -> {OUT_PARQUET}")

# XNA/Unknown -> NULL 후처리 (ORGANIZATION_TYPE, NAME_FAMILY_STATUS)
con.execute(f"""
    CREATE OR REPLACE TABLE feat AS
    SELECT * REPLACE (
        CASE WHEN ORGANIZATION_TYPE = 'XNA' THEN NULL ELSE ORGANIZATION_TYPE END AS ORGANIZATION_TYPE,
        CASE WHEN NAME_FAMILY_STATUS = 'Unknown' THEN NULL ELSE NAME_FAMILY_STATUS END AS NAME_FAMILY_STATUS
    )
    FROM read_parquet('{OUT_PARQUET}')
""")
con.execute(f"COPY feat TO '{OUT_PARQUET}' (FORMAT PARQUET)")
print("XNA/Unknown -> NULL 후처리 완료")

log = {
    "n_rows": n_rows,
    "n_cols": n_cols,
    "remainder_appendix_columns": remainder_cols,
    "excluded_always": sorted(EXCLUDE_ALWAYS),
    "used_in_derived_raw_cols": sorted(USED_IN_DERIVED),
    "join_principle": "하위 테이블은 상위 키에 대한 진짜 고아(orphan)를 제외한 뒤 각 테이블이 자체 보유한 SK_ID_CURR로 직접 신청자에 연결한다. bureau_balance만 SK_ID_CURR이 없어 bureau를 거쳐 연결했다.",
    "null_policy": "이력이 없는 신청자는 관련 변수를 NULL로 둔다(0으로 채우지 않음).",
    "leakage_exclusions": ["previous_application.DAYS_LAST_DUE_1ST_VERSION", "previous_application.DAYS_LAST_DUE", "previous_application.DAYS_TERMINATION"],
    "special_value_handling": {
        "DAYS_EMPLOYED=365243": "NULL 처리 + unemployed_flag=1 생성",
        "previous_application.DAYS_*=365243": "시간창(최근 1년) 계산 시 0 이하 값만 사용하므로 자연 배제",
        "ORGANIZATION_TYPE='XNA'": "NULL 처리",
        "NAME_FAMILY_STATUS='Unknown'": "NULL 처리",
    },
}
with open(OUT_LOG, "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)

print(f"로그 저장: {OUT_LOG}")
con.close()
