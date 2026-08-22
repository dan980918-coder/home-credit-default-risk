"""
Phase 2 EDA: Feature Engineering(Option A, Lean)에서 만든 bureau/previous_application
집계 지표(has_bureau_record, bureau_active_ratio, prev_approved_ratio 등)가
실제로 TARGET과 연관 있는지 확인. 불리언 플래그는 그룹별 TARGET=1 비율로,
연속형은 target과의 Pearson 상관으로 본다.
"""
import duckdb

PATH = "data/processed/train_features_leanA.parquet"
BOOL_COLS = ["has_bureau_record", "has_previous_application"]
NUMERIC_COLS = [
    "bureau_count", "bureau_active_ratio", "bureau_overdue_ratio",
    "bureau_debt_credit_ratio", "bureau_bb_dpd_ever_frac_mean", "bureau_bb_max_dpd_severity_max",
    "prev_count", "prev_approved_ratio", "prev_refused_ratio",
    "ccb_dpd_ever_frac_mean", "ccb_utilization_mean_mean",
    "pos_dpd_ever_frac_mean",
    "inst_late_frac_mean", "inst_late_days_mean_mean", "inst_payment_ratio_mean_mean",
]

con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")

print("=== 불리언 플래그: 그룹별 TARGET=1 비율 ===")
for col in BOOL_COLS:
    rows = con.execute(f"""
        SELECT "{col}", avg(TARGET::DOUBLE) AS target_rate, count(*) AS n
        FROM read_parquet('{PATH}')
        GROUP BY "{col}" ORDER BY "{col}"
    """).fetchall()
    print(f"\n[{col}]")
    for val, rate, n in rows:
        print(f"  {val}: TARGET=1 비율 {rate:.2%}  (n={n:,})")

print("\n=== 연속형 지표: TARGET과의 Pearson 상관 ===")
results = []
for col in NUMERIC_COLS:
    corr, non_null = con.execute(f"""
        SELECT corr("{col}", TARGET), count("{col}")
        FROM read_parquet('{PATH}')
    """).fetchone()
    results.append((col, corr, non_null))

results.sort(key=lambda r: -abs(r[1]) if r[1] is not None else 0)
for col, corr, non_null in results:
    corr_str = f"{corr:+.4f}" if corr is not None else "N/A"
    print(f"  {col:35s} corr={corr_str}  non_null={non_null:,}")
