"""
Phase 3: 결정된 두 가지 방식으로 고객 단위 feature 테이블 생성.
  A. baseline: 고객별 최근 1개월 스냅샷 (원본 188 feature 그대로)
  B. 메인: 고객별 mean/std/last/last-first delta 파생 (수치형 186개 x 4)
     + 범주형 2개(D_63, D_64)는 last만
     + 결측 indicator 정리:
       - D_134~D_138 (5개, 100% 동일 결측 패턴) -> 공용 플래그 1개
       - D_49/D_132/D_106 -> phi(Phase 2 §2) 최댓값인 D_49만 유지
모두 DuckDB 집계로 처리 (pandas 전체 로드 없음).
"""
import duckdb

SAMPLE_DATA = "data/processed/train_sample_50k.parquet"
OUT_A = "data/processed/train_features_baseline_A.parquet"
OUT_B = "data/processed/train_features_main_B.parquet"
KEY_COLS = {"customer_ID", "S_2", "target"}
CATEGORICAL_COLS = {"D_63", "D_64"}

con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")

schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{SAMPLE_DATA}')").fetchall()
all_cols = [row[0] for row in schema]
feature_cols = [c for c in all_cols if c not in KEY_COLS]
numeric_cols = [c for c in feature_cols if c not in CATEGORICAL_COLS]

print(f"numeric feature cols: {len(numeric_cols)}, categorical: {len(CATEGORICAL_COLS)}")

# ---------- A. baseline: 최근 1개월 스냅샷 ----------
con.execute(f"""
    COPY (
        SELECT * EXCLUDE (S_2)
        FROM (
            SELECT *, row_number() OVER (PARTITION BY customer_ID ORDER BY S_2 DESC) AS rn
            FROM read_parquet('{SAMPLE_DATA}')
        )
        WHERE rn = 1
    ) TO '{OUT_A}' (FORMAT PARQUET)
""")
n_a, cols_a = con.execute(f"""
    SELECT count(*), count(distinct customer_ID)
    FROM read_parquet('{OUT_A}')
""").fetchone()
ncols_a = len(con.execute(f"DESCRIBE SELECT * FROM read_parquet('{OUT_A}')").fetchall())
print(f"[A] baseline saved: {n_a} rows, {cols_a} customers, {ncols_a} columns")

# ---------- B. mean/std/last/delta + 정리된 missing indicator ----------
# 744개 집계 컬럼을 한 번에 만들면 memory_limit(1GB)을 넘기 쉬워서(실측: 953MB에서
# OOM), 컬럼을 배치로 나눠 각각 customer_ID 단위로 집계한 뒤 마지막에 join한다.
con.execute("SET preserve_insertion_order=false")
con.execute("SET threads=1")

BATCH_SIZE = 40
batches = [numeric_cols[i:i + BATCH_SIZE] for i in range(0, len(numeric_cols), BATCH_SIZE)]
print(f"numeric columns split into {len(batches)} batches of <= {BATCH_SIZE}")

import os
os.makedirs("data/tmp_duckdb/phase3_batches", exist_ok=True)
batch_paths = []
for i, batch in enumerate(batches):
    exprs = []
    for c in batch:
        exprs.append(f'avg("{c}") AS "{c}_mean"')
        exprs.append(f'stddev("{c}") AS "{c}_std"')
        exprs.append(f'arg_max("{c}", S_2) AS "{c}_last"')
        exprs.append(f'(arg_max("{c}", S_2) - arg_min("{c}", S_2)) AS "{c}_delta"')
    path = f"data/tmp_duckdb/phase3_batches/batch_{i}.parquet"
    con.execute(f"""
        COPY (
            SELECT customer_ID, {", ".join(exprs)}
            FROM read_parquet('{SAMPLE_DATA}')
            GROUP BY customer_ID
        ) TO '{path}' (FORMAT PARQUET)
    """)
    batch_paths.append(path)
    print(f"  batch {i+1}/{len(batches)} done ({len(batch)} cols) -> {path}")

# 범주형 last + 정리된 missing indicator + target + n_months_observed
misc_exprs = []
for c in CATEGORICAL_COLS:
    misc_exprs.append(f'arg_max("{c}", S_2) AS "{c}_last"')
misc_exprs.append('(1 - count("D_134") / count(*)::DOUBLE) AS "D_134_138_missing_frac"')
misc_exprs.append('(1 - count("D_49") / count(*)::DOUBLE) AS "D_49_missing_frac"')
misc_exprs.append("max(target) AS target")
misc_exprs.append("count(*) AS n_months_observed")
misc_path = "data/tmp_duckdb/phase3_batches/misc.parquet"
con.execute(f"""
    COPY (
        SELECT customer_ID, {", ".join(misc_exprs)}
        FROM read_parquet('{SAMPLE_DATA}')
        GROUP BY customer_ID
    ) TO '{misc_path}' (FORMAT PARQUET)
""")
batch_paths.append(misc_path)
print(f"  misc batch done -> {misc_path}")

# 모든 배치를 customer_ID로 join (50,000행짜리 join이라 메모리 부담 거의 없음)
join_sql = f"read_parquet('{batch_paths[0]}') b0"
select_cols = ["b0.customer_ID"] + [f"b0.* EXCLUDE (customer_ID)"]
for i, p in enumerate(batch_paths[1:], start=1):
    join_sql += f" JOIN read_parquet('{p}') b{i} USING (customer_ID)"
    select_cols.append(f"b{i}.* EXCLUDE (customer_ID)")

con.execute(f"""
    COPY (
        SELECT {", ".join(select_cols)}
        FROM {join_sql}
    ) TO '{OUT_B}' (FORMAT PARQUET)
""")

n_b, cust_b = con.execute(f"""
    SELECT count(*), count(distinct customer_ID) FROM read_parquet('{OUT_B}')
""").fetchone()
ncols_b = len(con.execute(f"DESCRIBE SELECT * FROM read_parquet('{OUT_B}')").fetchall())
print(f"[B] main features saved: {n_b} rows, {cust_b} customers, {ncols_b} columns")
print(f"    (numeric {len(numeric_cols)} x 4 stats = {len(numeric_cols)*4}, "
      f"+ categorical last {len(CATEGORICAL_COLS)}, + 2 missing_frac, + customer_ID + target + n_months_observed)")
