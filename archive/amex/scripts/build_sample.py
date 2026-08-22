"""
Phase 1: RAM 제약(재부팅 직후 여유 89MB) 하에서 pandas 전체 로드 없이
DuckDB의 out-of-core 실행 엔진으로 customer_id 기준 stratified 5만 명
샘플을 만들어 data/processed/train_sample_50k.parquet 으로 저장한다.
"""
import duckdb

RAW_LABELS = "data/raw/train_labels.csv"
RAW_DATA = "data/raw/train_data.parquet"
OUT_DATA = "data/processed/train_sample_50k.parquet"
OUT_LABELS = "data/processed/train_sample_50k_labels.parquet"
SAMPLE_SIZE = 50_000
SEED = 42

con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")

con.execute(f"SELECT setseed({SEED / 2147483647.0})")

con.execute(f"CREATE TABLE labels AS SELECT * FROM read_csv_auto('{RAW_LABELS}')")

con.execute(f"""
    CREATE TABLE sample_ids AS
    WITH ranked AS (
        SELECT
            customer_id, target,
            row_number() OVER (PARTITION BY target ORDER BY random()) AS rn,
            count(*) OVER (PARTITION BY target) AS grp_total,
            count(*) OVER () AS grand_total
        FROM labels
    )
    SELECT customer_id, target
    FROM ranked
    WHERE rn <= round({SAMPLE_SIZE}.0 * grp_total / grand_total)
""")

n_sample, n_pos = con.execute(
    "SELECT count(*), sum(target) FROM sample_ids"
).fetchone()
print(f"stratified sample customers: {n_sample} (target=1: {n_pos}, "
      f"ratio {n_pos/n_sample:.4f})")

con.execute(f"""
    COPY (
        -- __index_level_0__: raw parquet 저장 시 남은 pandas 구 인덱스 잔재, feature/target 아님 (docs/decisions_pending_review.md)
        SELECT * EXCLUDE (__index_level_0__)
        FROM read_parquet('{RAW_DATA}') t
        SEMI JOIN sample_ids s ON t.customer_id = s.customer_id
    ) TO '{OUT_DATA}' (FORMAT PARQUET)
""")

con.execute(f"COPY sample_ids TO '{OUT_LABELS}' (FORMAT PARQUET)")

n_rows = con.execute(f"SELECT count(*) FROM read_parquet('{OUT_DATA}')").fetchone()[0]
n_cust = con.execute(
    f"SELECT count(distinct customer_id) FROM read_parquet('{OUT_DATA}')"
).fetchone()[0]
print(f"output rows: {n_rows}, distinct customers: {n_cust}")
