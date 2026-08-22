"""
Phase 3 (Lean, 옵션 A): 해석 가능성 우선 - 테이블당 핵심 지표만 소수 선별해
SK_ID_CURR 단위 feature 테이블을 만든다.

조인/집계 순서:
  1) bureau_balance -> SK_ID_BUREAU 단위 집계
  2) bureau(+1의 결과) -> SK_ID_CURR 단위 집계
  3) credit_card_balance / POS_CASH_balance / installments_payments
     -> 각각 SK_ID_PREV 단위 집계
  4) previous_application(+3의 결과) -> SK_ID_CURR 단위 집계
  5) application_train/test(전처리 적용) + 2 + 4 최종 join

전부 DuckDB로 처리(pandas 전체 로드 없음), 중간 결과는 parquet로 저장해
한 번에 처리하는 쿼리의 메모리 사용을 억제한다.
"""
import duckdb
from _preprocessing import clean_application_sql

RAW = "data/raw"
OUT = "data/processed"

con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")
con.execute("SET preserve_insertion_order=false")


def run(step, sql):
    print(f"--- {step} ---")
    con.execute(sql)


# ---------- 1) bureau_balance -> SK_ID_BUREAU ----------
run("1) bureau_balance -> bureau_balance_agg.parquet", f"""
    COPY (
        SELECT
            SK_ID_BUREAU,
            count(*) AS bb_n_months,
            avg(CASE WHEN STATUS IN ('1','2','3','4','5') THEN 1.0 ELSE 0.0 END) AS bb_dpd_ever_frac,
            arg_max(STATUS, MONTHS_BALANCE) AS bb_status_last,
            max(CASE WHEN STATUS IN ('0','1','2','3','4','5') THEN CAST(STATUS AS INTEGER) END) AS bb_max_dpd_severity
        FROM read_csv_auto('{RAW}/bureau_balance.csv')
        GROUP BY SK_ID_BUREAU
    ) TO '{OUT}/bb_agg.parquet' (FORMAT PARQUET)
""")

# ---------- 2) bureau(+bb_agg) -> SK_ID_CURR ----------
run("2) bureau -> bureau_agg.parquet (SK_ID_CURR 단위)", f"""
    COPY (
        SELECT
            b.SK_ID_CURR,
            count(*) AS bureau_count,
            avg(CASE WHEN b.CREDIT_ACTIVE = 'Active' THEN 1.0 ELSE 0.0 END) AS bureau_active_ratio,
            avg(b.DAYS_CREDIT) AS bureau_days_credit_mean,
            avg(CASE WHEN b.CREDIT_DAY_OVERDUE > 0 THEN 1.0 ELSE 0.0 END) AS bureau_overdue_ratio,
            sum(b.AMT_CREDIT_SUM) AS bureau_amt_credit_sum_total,
            sum(b.AMT_CREDIT_SUM_DEBT) AS bureau_amt_credit_sum_debt_total,
            sum(b.AMT_CREDIT_SUM_OVERDUE) AS bureau_amt_credit_sum_overdue_total,
            (sum(b.AMT_CREDIT_SUM_DEBT) / NULLIF(sum(b.AMT_CREDIT_SUM), 0)) AS bureau_debt_credit_ratio,
            avg(b.AMT_ANNUITY) AS bureau_amt_annuity_mean,
            count(DISTINCT b.CREDIT_TYPE) AS bureau_credit_type_nunique,
            avg(bb.bb_dpd_ever_frac) AS bureau_bb_dpd_ever_frac_mean,
            max(bb.bb_max_dpd_severity) AS bureau_bb_max_dpd_severity_max
        FROM read_csv_auto('{RAW}/bureau.csv') b
        LEFT JOIN read_parquet('{OUT}/bb_agg.parquet') bb ON b.SK_ID_BUREAU = bb.SK_ID_BUREAU
        GROUP BY b.SK_ID_CURR
    ) TO '{OUT}/bureau_agg.parquet' (FORMAT PARQUET)
""")

# ---------- 3) credit_card_balance / POS_CASH_balance / installments_payments -> SK_ID_PREV ----------
run("3a) credit_card_balance -> ccb_agg.parquet (SK_ID_PREV 단위)", f"""
    COPY (
        SELECT
            SK_ID_PREV,
            count(*) AS ccb_n_months,
            avg(AMT_BALANCE) AS ccb_amt_balance_mean,
            avg(AMT_CREDIT_LIMIT_ACTUAL) AS ccb_amt_credit_limit_mean,
            max(SK_DPD) AS ccb_dpd_max,
            avg(CASE WHEN SK_DPD > 0 THEN 1.0 ELSE 0.0 END) AS ccb_dpd_ever_frac,
            avg(AMT_BALANCE / NULLIF(AMT_CREDIT_LIMIT_ACTUAL, 0)) AS ccb_utilization_mean
        FROM read_csv_auto('{RAW}/credit_card_balance.csv')
        GROUP BY SK_ID_PREV
    ) TO '{OUT}/ccb_agg.parquet' (FORMAT PARQUET)
""")

run("3b) POS_CASH_balance -> pos_agg.parquet (SK_ID_PREV 단위)", f"""
    COPY (
        SELECT
            SK_ID_PREV,
            count(*) AS pos_n_months,
            avg(CNT_INSTALMENT) AS pos_cnt_instalment_mean,
            max(SK_DPD) AS pos_dpd_max,
            avg(CASE WHEN SK_DPD > 0 THEN 1.0 ELSE 0.0 END) AS pos_dpd_ever_frac,
            avg(CASE WHEN NAME_CONTRACT_STATUS = 'Completed' THEN 1.0 ELSE 0.0 END) AS pos_completed_frac
        FROM read_csv_auto('{RAW}/POS_CASH_balance.csv')
        GROUP BY SK_ID_PREV
    ) TO '{OUT}/pos_agg.parquet' (FORMAT PARQUET)
""")

run("3c) installments_payments -> inst_agg.parquet (SK_ID_PREV 단위)", f"""
    COPY (
        SELECT
            SK_ID_PREV,
            count(*) AS inst_count,
            sum(AMT_INSTALMENT) AS inst_amt_instalment_sum,
            avg(CASE WHEN DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT THEN 1.0 ELSE 0.0 END) AS inst_late_frac,
            avg(GREATEST(DAYS_ENTRY_PAYMENT - DAYS_INSTALMENT, 0)) AS inst_late_days_mean,
            avg(AMT_PAYMENT / NULLIF(AMT_INSTALMENT, 0)) AS inst_payment_ratio_mean
        FROM read_csv_auto('{RAW}/installments_payments.csv')
        GROUP BY SK_ID_PREV
    ) TO '{OUT}/inst_agg.parquet' (FORMAT PARQUET)
""")

# ---------- 4) previous_application(+3의 결과) -> SK_ID_CURR ----------
run("4) previous_application -> prev_agg.parquet (SK_ID_CURR 단위)", f"""
    COPY (
        SELECT
            p.SK_ID_CURR,
            count(*) AS prev_count,
            avg(CASE WHEN p.NAME_CONTRACT_STATUS = 'Approved' THEN 1.0 ELSE 0.0 END) AS prev_approved_ratio,
            avg(CASE WHEN p.NAME_CONTRACT_STATUS = 'Refused' THEN 1.0 ELSE 0.0 END) AS prev_refused_ratio,
            avg(p.AMT_CREDIT) AS prev_amt_credit_mean,
            avg(p.AMT_APPLICATION) AS prev_amt_application_mean,
            avg(p.AMT_ANNUITY) AS prev_amt_annuity_mean,
            avg(p.AMT_DOWN_PAYMENT) AS prev_amt_down_payment_mean,
            avg(p.DAYS_DECISION) AS prev_days_decision_mean,
            avg(p.DAYS_LAST_DUE) AS prev_days_last_due_mean,
            avg(p.CNT_PAYMENT) AS prev_cnt_payment_mean,
            avg(c.ccb_n_months) AS ccb_n_months_mean,
            avg(c.ccb_amt_balance_mean) AS ccb_amt_balance_mean_mean,
            avg(c.ccb_amt_credit_limit_mean) AS ccb_amt_credit_limit_mean_mean,
            max(c.ccb_dpd_max) AS ccb_dpd_max_max,
            avg(c.ccb_dpd_ever_frac) AS ccb_dpd_ever_frac_mean,
            avg(c.ccb_utilization_mean) AS ccb_utilization_mean_mean,
            avg(ps.pos_n_months) AS pos_n_months_mean,
            avg(ps.pos_cnt_instalment_mean) AS pos_cnt_instalment_mean_mean,
            max(ps.pos_dpd_max) AS pos_dpd_max_max,
            avg(ps.pos_dpd_ever_frac) AS pos_dpd_ever_frac_mean,
            avg(ps.pos_completed_frac) AS pos_completed_frac_mean,
            avg(i.inst_count) AS inst_count_mean,
            sum(i.inst_amt_instalment_sum) AS inst_amt_instalment_sum_total,
            avg(i.inst_late_frac) AS inst_late_frac_mean,
            avg(i.inst_late_days_mean) AS inst_late_days_mean_mean,
            avg(i.inst_payment_ratio_mean) AS inst_payment_ratio_mean_mean
        FROM read_csv_auto('{RAW}/previous_application.csv') p
        LEFT JOIN read_parquet('{OUT}/ccb_agg.parquet') c ON p.SK_ID_PREV = c.SK_ID_PREV
        LEFT JOIN read_parquet('{OUT}/pos_agg.parquet') ps ON p.SK_ID_PREV = ps.SK_ID_PREV
        LEFT JOIN read_parquet('{OUT}/inst_agg.parquet') i ON p.SK_ID_PREV = i.SK_ID_PREV
        GROUP BY p.SK_ID_CURR
    ) TO '{OUT}/prev_agg.parquet' (FORMAT PARQUET)
""")

# ---------- 5) application_train/test + bureau_agg + prev_agg 최종 join ----------
for split, path in [("train", f"{RAW}/application_train.csv"), ("test", f"{RAW}/application_test.csv")]:
    run(f"5) application_{split} + bureau_agg + prev_agg -> train_features_leanA / test_features_leanA", f"""
        COPY (
            SELECT
                a.*,
                COALESCE(ba.bureau_count, 0) > 0 AS has_bureau_record,
                COALESCE(pa.prev_count, 0) > 0 AS has_previous_application,
                ba.* EXCLUDE (SK_ID_CURR),
                pa.* EXCLUDE (SK_ID_CURR)
            FROM ({clean_application_sql(path)}) a
            LEFT JOIN read_parquet('{OUT}/bureau_agg.parquet') ba ON a.SK_ID_CURR = ba.SK_ID_CURR
            LEFT JOIN read_parquet('{OUT}/prev_agg.parquet') pa ON a.SK_ID_CURR = pa.SK_ID_CURR
        ) TO '{OUT}/{split}_features_leanA.parquet' (FORMAT PARQUET)
    """)

print("\n=== 완료: 최종 산출 shape ===")
for split in ["train", "test"]:
    n = con.execute(f"SELECT count(*) FROM read_parquet('{OUT}/{split}_features_leanA.parquet')").fetchone()[0]
    ncols = len(con.execute(f"DESCRIBE SELECT * FROM read_parquet('{OUT}/{split}_features_leanA.parquet')").fetchall())
    print(f"{split}_features_leanA: {n} rows x {ncols} cols")
