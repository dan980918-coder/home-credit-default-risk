"""
Lean(A) feature 집계 로직(SQL)을 소스 무관하게 재사용 가능한 함수로 분리.
`source`는 DuckDB가 SELECT 가능한 어떤 것이든 될 수 있음:
  - "read_csv_auto('data/raw/bureau.csv')" (배치 파이프라인, build_features_leanA.py)
  - "bureau_live" 같은 con.register()로 등록한 in-memory DataFrame 이름 (API live 엔드포인트)
동일한 집계 정의를 배치 빌드와 실시간 API가 그대로 공유해 로직 drift를 방지한다.
"""


def bb_agg_sql(bureau_balance_source: str) -> str:
    return f"""
        SELECT
            SK_ID_BUREAU,
            count(*) AS bb_n_months,
            avg(CASE WHEN STATUS IN ('1','2','3','4','5') THEN 1.0 ELSE 0.0 END) AS bb_dpd_ever_frac,
            arg_max(STATUS, MONTHS_BALANCE) AS bb_status_last,
            max(CASE WHEN STATUS IN ('0','1','2','3','4','5') THEN CAST(STATUS AS INTEGER) END) AS bb_max_dpd_severity
        FROM {bureau_balance_source}
        GROUP BY SK_ID_BUREAU
    """


def bureau_agg_sql(bureau_source: str, bb_agg_source: str) -> str:
    return f"""
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
        FROM {bureau_source} b
        LEFT JOIN {bb_agg_source} bb ON b.SK_ID_BUREAU = bb.SK_ID_BUREAU
        GROUP BY b.SK_ID_CURR
    """


def ccb_agg_sql(ccb_source: str) -> str:
    return f"""
        SELECT
            SK_ID_PREV,
            count(*) AS ccb_n_months,
            avg(AMT_BALANCE) AS ccb_amt_balance_mean,
            avg(AMT_CREDIT_LIMIT_ACTUAL) AS ccb_amt_credit_limit_mean,
            max(SK_DPD) AS ccb_dpd_max,
            avg(CASE WHEN SK_DPD > 0 THEN 1.0 ELSE 0.0 END) AS ccb_dpd_ever_frac,
            avg(AMT_BALANCE / NULLIF(AMT_CREDIT_LIMIT_ACTUAL, 0)) AS ccb_utilization_mean
        FROM {ccb_source}
        GROUP BY SK_ID_PREV
    """


def pos_agg_sql(pos_source: str) -> str:
    return f"""
        SELECT
            SK_ID_PREV,
            count(*) AS pos_n_months,
            avg(CNT_INSTALMENT) AS pos_cnt_instalment_mean,
            max(SK_DPD) AS pos_dpd_max,
            avg(CASE WHEN SK_DPD > 0 THEN 1.0 ELSE 0.0 END) AS pos_dpd_ever_frac,
            avg(CASE WHEN NAME_CONTRACT_STATUS = 'Completed' THEN 1.0 ELSE 0.0 END) AS pos_completed_frac
        FROM {pos_source}
        GROUP BY SK_ID_PREV
    """


def inst_agg_sql(inst_source: str) -> str:
    return f"""
        SELECT
            SK_ID_PREV,
            count(*) AS inst_count,
            sum(AMT_INSTALMENT) AS inst_amt_instalment_sum,
            avg(CASE WHEN DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT THEN 1.0 ELSE 0.0 END) AS inst_late_frac,
            avg(GREATEST(DAYS_ENTRY_PAYMENT - DAYS_INSTALMENT, 0)) AS inst_late_days_mean,
            avg(AMT_PAYMENT / NULLIF(AMT_INSTALMENT, 0)) AS inst_payment_ratio_mean
        FROM {inst_source}
        GROUP BY SK_ID_PREV
    """


def prev_agg_sql(prev_source: str, ccb_agg_source: str, pos_agg_source: str, inst_agg_source: str) -> str:
    return f"""
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
        FROM {prev_source} p
        LEFT JOIN {ccb_agg_source} c ON p.SK_ID_PREV = c.SK_ID_PREV
        LEFT JOIN {pos_agg_source} ps ON p.SK_ID_PREV = ps.SK_ID_PREV
        LEFT JOIN {inst_agg_source} i ON p.SK_ID_PREV = i.SK_ID_PREV
        GROUP BY p.SK_ID_CURR
    """


def final_join_sql(application_source: str, bureau_agg_source: str, prev_agg_source: str) -> str:
    return f"""
        SELECT
            a.*,
            COALESCE(ba.bureau_count, 0) > 0 AS has_bureau_record,
            COALESCE(pa.prev_count, 0) > 0 AS has_previous_application,
            ba.* EXCLUDE (SK_ID_CURR),
            pa.* EXCLUDE (SK_ID_CURR)
        FROM {application_source} a
        LEFT JOIN {bureau_agg_source} ba ON a.SK_ID_CURR = ba.SK_ID_CURR
        LEFT JOIN {prev_agg_source} pa ON a.SK_ID_CURR = pa.SK_ID_CURR
    """
