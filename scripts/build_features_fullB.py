"""
Phase 3 (Full, 옵션 B): 커뮤니티 표준 방식 - 모든 수치형 컬럼에
mean/max/min/sum을 전부 적용해 SK_ID_CURR 단위 feature 테이블을 만든다.
Option A(Lean)와의 성능 비교 벤치마크 목적.

범위 결정: 범주형 컬럼은 Option A와 동일한 최소 처리만 유지(원-핫 전개는
하지 않음) — 순수 범주형 원-핫까지 다 하면 이 데이터셋에서는 수천 컬럼까지
커질 수 있어(유명 공개 커널 기준), 이번 "A vs B 성능 비교"라는 목적에는
수치형 통계 확장만으로 충분하다고 판단.

조인/집계 순서는 Option A와 동일:
  1) bureau_balance -> SK_ID_BUREAU
  2) bureau(+1) -> SK_ID_CURR
  3) credit_card_balance / POS_CASH_balance / installments_payments -> SK_ID_PREV
  4) previous_application(+3) -> SK_ID_CURR
  5) application_train/test(전처리 적용) + 2 + 4 최종 join
"""
import duckdb
from _preprocessing import clean_application_sql

RAW = "data/raw"
OUT = "data/processed"

con = duckdb.connect()
con.execute("SET memory_limit='1.5GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")
con.execute("SET preserve_insertion_order=false")

NUMERIC_TYPES = {"BIGINT", "DOUBLE", "FLOAT", "INTEGER", "SMALLINT", "TINYINT", "HUGEINT", "DECIMAL"}


def numeric_cols_of(path, exclude):
    schema = con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{path}')").fetchall()
    return [r[0] for r in schema
            if r[0] not in exclude and any(r[1].upper().startswith(t) for t in NUMERIC_TYPES)]


def full_stats_exprs(cols):
    exprs = []
    for c in cols:
        exprs.append(f'avg("{c}") AS "{c}_mean"')
        exprs.append(f'max("{c}") AS "{c}_max"')
        exprs.append(f'min("{c}") AS "{c}_min"')
        exprs.append(f'sum("{c}") AS "{c}_sum"')
    return exprs


def run(step, sql):
    print(f"--- {step} ---")
    con.execute(sql)


# ---------- 1) bureau_balance -> SK_ID_BUREAU ----------
bb_numeric = numeric_cols_of(f"{RAW}/bureau_balance.csv", {"SK_ID_BUREAU"})
print("bureau_balance numeric cols:", bb_numeric)
bb_exprs = full_stats_exprs(bb_numeric) + [
    "count(*) AS bb_n_months",
    "avg(CASE WHEN STATUS IN ('1','2','3','4','5') THEN 1.0 ELSE 0.0 END) AS bb_dpd_ever_frac",
    "arg_max(STATUS, MONTHS_BALANCE) AS bb_status_last",
    "max(CASE WHEN STATUS IN ('0','1','2','3','4','5') THEN CAST(STATUS AS INTEGER) END) AS bb_max_dpd_severity",
]
run("1) bureau_balance -> bb_agg_full.parquet", f"""
    COPY (
        SELECT SK_ID_BUREAU, {", ".join(bb_exprs)}
        FROM read_csv_auto('{RAW}/bureau_balance.csv')
        GROUP BY SK_ID_BUREAU
    ) TO '{OUT}/bb_agg_full.parquet' (FORMAT PARQUET)
""")

# ---------- 2) bureau(+bb_agg_full) -> SK_ID_CURR ----------
bureau_numeric = numeric_cols_of(f"{RAW}/bureau.csv", {"SK_ID_CURR", "SK_ID_BUREAU"})
bb_agg_cols = [c for c in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{OUT}/bb_agg_full.parquet')")
               .fetchall() if c[0] != "SK_ID_BUREAU"]
bb_rollup_numeric = [c[0] for c in bb_agg_cols if c[0] != "bb_status_last"]
print("bureau numeric cols:", len(bureau_numeric), " | bb rollup cols:", len(bb_rollup_numeric))

bureau_exprs = (
    full_stats_exprs(bureau_numeric)
    + [f'avg(bb."{c}") AS "bb_{c}_mean"' for c in bb_rollup_numeric]
    + [
        "count(*) AS bureau_count",
        "avg(CASE WHEN b.CREDIT_ACTIVE = 'Active' THEN 1.0 ELSE 0.0 END) AS bureau_active_ratio",
        "count(DISTINCT b.CREDIT_TYPE) AS bureau_credit_type_nunique",
    ]
)
run("2) bureau -> bureau_agg_full.parquet (SK_ID_CURR 단위)", f"""
    COPY (
        SELECT
            b.SK_ID_CURR,
            {", ".join(bureau_exprs)}
        FROM read_csv_auto('{RAW}/bureau.csv') b
        LEFT JOIN read_parquet('{OUT}/bb_agg_full.parquet') bb ON b.SK_ID_BUREAU = bb.SK_ID_BUREAU
        GROUP BY b.SK_ID_CURR
    ) TO '{OUT}/bureau_agg_full.parquet' (FORMAT PARQUET)
""")

# ---------- 3) credit_card_balance / POS_CASH_balance / installments_payments -> SK_ID_PREV ----------
for name, exclude, extra in [
    ("credit_card_balance", {"SK_ID_PREV", "SK_ID_CURR"},
     ["avg(AMT_BALANCE / NULLIF(AMT_CREDIT_LIMIT_ACTUAL, 0)) AS ccb_utilization_mean"]),
    ("POS_CASH_balance", {"SK_ID_PREV", "SK_ID_CURR"}, []),
    ("installments_payments", {"SK_ID_PREV", "SK_ID_CURR"},
     ["avg(CASE WHEN DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT THEN 1.0 ELSE 0.0 END) AS inst_late_frac",
      "avg(AMT_PAYMENT / NULLIF(AMT_INSTALMENT, 0)) AS inst_payment_ratio_mean"]),
]:
    cols = numeric_cols_of(f"{RAW}/{name}.csv", exclude)
    print(f"{name} numeric cols ({len(cols)}):", cols)
    exprs = full_stats_exprs(cols) + [f"count(*) AS {name.lower()}_n_rows"] + extra
    run(f"3) {name} -> {name.lower()}_agg_full.parquet (SK_ID_PREV 단위)", f"""
        COPY (
            SELECT SK_ID_PREV, {", ".join(exprs)}
            FROM read_csv_auto('{RAW}/{name}.csv')
            GROUP BY SK_ID_PREV
        ) TO '{OUT}/{name.lower()}_agg_full.parquet' (FORMAT PARQUET)
    """)

# ---------- 4) previous_application(+3의 결과) -> SK_ID_CURR ----------
prev_numeric = numeric_cols_of(f"{RAW}/previous_application.csv", {"SK_ID_CURR", "SK_ID_PREV"})


def rollup_cols(parquet_path, key="SK_ID_PREV"):
    schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{parquet_path}')").fetchall()
    return [r[0] for r in schema if r[0] != key]


ccb_cols = rollup_cols(f"{OUT}/credit_card_balance_agg_full.parquet")
pos_cols = rollup_cols(f"{OUT}/pos_cash_balance_agg_full.parquet")
inst_cols = rollup_cols(f"{OUT}/installments_payments_agg_full.parquet")
print(f"rollup counts -> ccb:{len(ccb_cols)} pos:{len(pos_cols)} inst:{len(inst_cols)}")

# 209개 집계식을 한 번에 처리하면 memory_limit(1.5GB)에서 OOM남(실측: 1.3GB
# 지점) -> AMEX Phase 3와 동일하게 블록별로 나눠 SK_ID_CURR 단위로 각각 집계
# 후 마지막에 join한다.
own_exprs = full_stats_exprs(prev_numeric) + [
    "count(*) AS prev_count",
    "avg(CASE WHEN NAME_CONTRACT_STATUS = 'Approved' THEN 1.0 ELSE 0.0 END) AS prev_approved_ratio",
    "avg(CASE WHEN NAME_CONTRACT_STATUS = 'Refused' THEN 1.0 ELSE 0.0 END) AS prev_refused_ratio",
]
run(f"4a) previous_application own stats -> prev_own.parquet ({len(own_exprs)}개)", f"""
    COPY (
        SELECT SK_ID_CURR, {", ".join(own_exprs)}
        FROM read_csv_auto('{RAW}/previous_application.csv')
        GROUP BY SK_ID_CURR
    ) TO '{OUT}/prev_own.parquet' (FORMAT PARQUET)
""")

rollup_blocks = [
    ("ccb", f"{OUT}/credit_card_balance_agg_full.parquet", ccb_cols),
    ("pos", f"{OUT}/pos_cash_balance_agg_full.parquet", pos_cols),
    ("inst", f"{OUT}/installments_payments_agg_full.parquet", inst_cols),
]
rollup_paths = []
for prefix, parquet_path, cols in rollup_blocks:
    exprs = [f'avg(r."{c}") AS "{prefix}_{c}_mean"' for c in cols]
    out_path = f"{OUT}/prev_{prefix}_rollup.parquet"
    run(f"4b) previous_application + {prefix} rollup -> {out_path} ({len(exprs)}개)", f"""
        COPY (
            SELECT p.SK_ID_CURR, {", ".join(exprs)}
            FROM read_csv_auto('{RAW}/previous_application.csv') p
            LEFT JOIN read_parquet('{parquet_path}') r ON p.SK_ID_PREV = r.SK_ID_PREV
            GROUP BY p.SK_ID_CURR
        ) TO '{out_path}' (FORMAT PARQUET)
    """)
    rollup_paths.append(out_path)

all_prev_paths = [f"{OUT}/prev_own.parquet"] + rollup_paths
join_sql = f"read_parquet('{all_prev_paths[0]}') b0"
select_cols = ["b0.SK_ID_CURR"] + ["b0.* EXCLUDE (SK_ID_CURR)"]
for i, p in enumerate(all_prev_paths[1:], start=1):
    join_sql += f" JOIN read_parquet('{p}') b{i} USING (SK_ID_CURR)"
    select_cols.append(f"b{i}.* EXCLUDE (SK_ID_CURR)")

run("4c) previous_application 블록 join -> prev_agg_full.parquet", f"""
    COPY (
        SELECT {", ".join(select_cols)}
        FROM {join_sql}
    ) TO '{OUT}/prev_agg_full.parquet' (FORMAT PARQUET)
""")

# ---------- 5) application_train/test(전처리) + bureau_agg_full + prev_agg_full 최종 join ----------
# ~390컬럼 wide join이라 1.5GB에서도 OOM(1.3GB 지점) -> 2GB + threads=1로 재시도해 성공
con.execute("SET memory_limit='2GB'")
con.execute("SET threads=1")
for split, path in [("train", f"{RAW}/application_train.csv"), ("test", f"{RAW}/application_test.csv")]:
    run(f"5) application_{split} + bureau_agg_full + prev_agg_full -> {split}_features_fullB", f"""
        COPY (
            SELECT
                a.*,
                COALESCE(ba.bureau_count, 0) > 0 AS has_bureau_record,
                COALESCE(pa.prev_count, 0) > 0 AS has_previous_application,
                ba.* EXCLUDE (SK_ID_CURR),
                pa.* EXCLUDE (SK_ID_CURR)
            FROM ({clean_application_sql(path)}) a
            LEFT JOIN read_parquet('{OUT}/bureau_agg_full.parquet') ba ON a.SK_ID_CURR = ba.SK_ID_CURR
            LEFT JOIN read_parquet('{OUT}/prev_agg_full.parquet') pa ON a.SK_ID_CURR = pa.SK_ID_CURR
        ) TO '{OUT}/{split}_features_fullB.parquet' (FORMAT PARQUET)
    """)

print("\n=== 완료: 최종 산출 shape ===")
for split in ["train", "test"]:
    n = con.execute(f"SELECT count(*) FROM read_parquet('{OUT}/{split}_features_fullB.parquet')").fetchone()[0]
    ncols = len(con.execute(f"DESCRIBE SELECT * FROM read_parquet('{OUT}/{split}_features_fullB.parquet')").fetchall())
    print(f"{split}_features_fullB: {n} rows x {ncols} cols")
