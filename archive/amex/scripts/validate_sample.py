"""
Phase 1 후속: 50k stratified 샘플(data/processed/train_sample_50k.parquet)에
대해 결측치/스키마 검증을 수행하고, 원본(data/raw/train_data.parquet) 대비
- 50%+ 결측 컬럼 패턴
- 13개월 풀 관측 비율
이 샘플링으로 왜곡되지 않았는지 비교한다. pandas 전체 로드 없이 DuckDB로만 처리.
"""
import json
import duckdb

RAW_DATA = "data/raw/train_data.parquet"
SAMPLE_DATA = "data/processed/train_sample_50k.parquet"

con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")


def describe_schema(path):
    rows = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()
    return [(r[0], r[1]) for r in rows]  # (column_name, column_type)


def basic_counts(path):
    total_rows, n_customers = con.execute(
        f"SELECT count(*), count(distinct customer_ID) FROM read_parquet('{path}')"
    ).fetchone()
    return total_rows, n_customers


def null_fraction_by_column(path, feature_cols):
    total_rows = con.execute(f"SELECT count(*) FROM read_parquet('{path}')").fetchone()[0]
    exprs = ", ".join(f'count("{c}") AS nn_{i}' for i, c in enumerate(feature_cols))
    row = con.execute(f"SELECT {exprs} FROM read_parquet('{path}')").fetchone()
    result = {}
    for i, c in enumerate(feature_cols):
        non_null = row[i]
        result[c] = 1 - non_null / total_rows
    return result


def observation_month_distribution(path):
    rows = con.execute(f"""
        WITH per_customer AS (
            SELECT customer_ID, count(*) AS n_months
            FROM read_parquet('{path}')
            GROUP BY customer_ID
        )
        SELECT n_months, count(*) AS n_customers
        FROM per_customer
        GROUP BY n_months
        ORDER BY n_months DESC
    """).fetchall()
    return rows  # list of (n_months, n_customers)


# --- schema ---
raw_schema = describe_schema(RAW_DATA)
sample_schema = describe_schema(SAMPLE_DATA)
# sample intentionally drops __index_level_0__ (pandas index leftover, see
# docs/decisions_pending_review.md) so raw has exactly one extra column.
raw_schema_minus_index = [c for c in raw_schema if c[0] != "__index_level_0__"]
schema_match = raw_schema_minus_index == sample_schema
print(f"schema identical excluding __index_level_0__ (raw vs sample): {schema_match}")
print(f"raw columns: {len(raw_schema)}, sample columns: {len(sample_schema)}")
if not schema_match:
    print("DIFF:", set(raw_schema_minus_index) ^ set(sample_schema))

key_cols = {"customer_ID", "S_2", "target", "__index_level_0__"}
feature_cols = [c for c, _ in sample_schema if c not in key_cols]
print(f"feature columns (excl. keys): {len(feature_cols)}")

# --- basic counts ---
raw_rows, raw_customers = basic_counts(RAW_DATA)
sample_rows, sample_customers = basic_counts(SAMPLE_DATA)
print(f"raw: {raw_rows} rows, {raw_customers} customers")
print(f"sample: {sample_rows} rows, {sample_customers} customers")

# --- missingness ---
raw_null = null_fraction_by_column(RAW_DATA, feature_cols)
sample_null = null_fraction_by_column(SAMPLE_DATA, feature_cols)

raw_high_missing = {c for c, f in raw_null.items() if f >= 0.5}
sample_high_missing = {c for c, f in sample_null.items() if f >= 0.5}

print(f"raw >=50% missing columns: {len(raw_high_missing)}")
print(f"sample >=50% missing columns: {len(sample_high_missing)}")
print(f"overlap: {len(raw_high_missing & sample_high_missing)}")
print(f"raw-only: {sorted(raw_high_missing - sample_high_missing)}")
print(f"sample-only: {sorted(sample_high_missing - raw_high_missing)}")

# --- observation months ---
raw_dist = observation_month_distribution(RAW_DATA)
sample_dist = observation_month_distribution(SAMPLE_DATA)

raw_full = sum(n for m, n in raw_dist if m == 13)
sample_full = sum(n for m, n in sample_dist if m == 13)
print(f"raw full-13-month ratio: {raw_full}/{raw_customers} = {raw_full/raw_customers:.4f}")
print(f"sample full-13-month ratio: {sample_full}/{sample_customers} = {sample_full/sample_customers:.4f}")

# --- dump full results to json for report writing ---
out = {
    "schema_match": schema_match,
    "raw_columns": len(raw_schema),
    "sample_columns": len(sample_schema),
    "feature_col_count": len(feature_cols),
    "raw_rows": raw_rows,
    "raw_customers": raw_customers,
    "sample_rows": sample_rows,
    "sample_customers": sample_customers,
    "raw_high_missing_count": len(raw_high_missing),
    "sample_high_missing_count": len(sample_high_missing),
    "high_missing_overlap": len(raw_high_missing & sample_high_missing),
    "raw_only_high_missing": sorted(raw_high_missing - sample_high_missing),
    "sample_only_high_missing": sorted(sample_high_missing - raw_high_missing),
    "raw_high_missing_cols": sorted(raw_high_missing),
    "sample_high_missing_cols": sorted(sample_high_missing),
    "raw_obs_dist": raw_dist,
    "sample_obs_dist": sample_dist,
    "raw_full13_ratio": raw_full / raw_customers,
    "sample_full13_ratio": sample_full / sample_customers,
}
with open("data/processed/validation_result.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("wrote data/processed/validation_result.json")
