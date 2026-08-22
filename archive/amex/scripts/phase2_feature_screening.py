"""
Phase 2 EDA 1단계: 대표 변수 후보 스크리닝.
188개 feature를 pandas로 통째로 로드하지 않고 DuckDB 집계만으로
- 카테고리(D_/S_/P_/B_/R_)별 컬럼 수
- 각 feature의 target과의 Pearson 상관(point-biserial), 결측률
을 계산해 카테고리별 대표 변수 후보(상관 절대값 상위)를 뽑는다.
실제 분포 시각화는 사용자가 후보를 확정한 뒤 별도 스크립트에서 진행.
"""
import json
import re
import duckdb

SAMPLE_DATA = "data/processed/train_sample_50k.parquet"
KEY_COLS = {"customer_ID", "S_2", "target"}
CATEGORY_PREFIX = {"D": "Delinquency", "S": "Spend", "P": "Payment", "B": "Balance", "R": "Risk"}

con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")

schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{SAMPLE_DATA}')").fetchall()
feature_cols = [(row[0], row[1]) for row in schema if row[0] not in KEY_COLS]

# categorize by prefix letter before first underscore
def categorize(col):
    m = re.match(r"^([A-Z]+)_", col)
    return m.group(1) if m else "?"

by_cat = {}
for name, dtype in feature_cols:
    cat = categorize(name)
    by_cat.setdefault(cat, []).append((name, dtype))

print("column count by category:")
for cat, cols in sorted(by_cat.items()):
    label = CATEGORY_PREFIX.get(cat, "unknown")
    print(f"  {cat} ({label}): {len(cols)}")

total_rows = con.execute(f"SELECT count(*) FROM read_parquet('{SAMPLE_DATA}')").fetchone()[0]

# only numeric columns can use CORR(); check types
numeric_types = {"BIGINT", "DOUBLE", "FLOAT", "INTEGER", "SMALLINT", "TINYINT", "HUGEINT", "DECIMAL"}

def is_numeric(dtype):
    return any(dtype.upper().startswith(t) for t in numeric_types)

results = []
skipped_non_numeric = []
for name, dtype in feature_cols:
    if not is_numeric(dtype):
        skipped_non_numeric.append((name, dtype))
        continue
    row = con.execute(f"""
        SELECT
            corr("{name}", target) AS corr_target,
            count("{name}") AS non_null,
            avg(CASE WHEN target = 1 THEN "{name}" END) AS mean_pos,
            avg(CASE WHEN target = 0 THEN "{name}" END) AS mean_neg,
            stddev("{name}") AS sd
        FROM read_parquet('{SAMPLE_DATA}')
    """).fetchone()
    corr_target, non_null, mean_pos, mean_neg, sd = row
    null_frac = 1 - non_null / total_rows
    results.append({
        "column": name,
        "category": categorize(name),
        "dtype": dtype,
        "null_frac": null_frac,
        "corr_target": corr_target,
        "mean_target1": mean_pos,
        "mean_target0": mean_neg,
        "stddev": sd,
    })

print(f"\nnumeric feature columns scored: {len(results)}")
if skipped_non_numeric:
    print(f"non-numeric columns skipped (no CORR): {skipped_non_numeric}")

# rank within category by |corr_target|, excluding null corr (constant/all-null columns)
candidates = {}
for cat in sorted(by_cat.keys()):
    cat_results = [r for r in results if r["category"] == cat and r["corr_target"] is not None]
    cat_results.sort(key=lambda r: abs(r["corr_target"]), reverse=True)
    candidates[cat] = cat_results[:5]

print("\ntop candidates per category (|corr with target| desc, top 5):")
for cat, rows in candidates.items():
    label = CATEGORY_PREFIX.get(cat, "unknown")
    print(f"\n[{cat}] {label}")
    for r in rows:
        print(f"  {r['column']:8s} corr={r['corr_target']:+.4f}  null_frac={r['null_frac']:.3f}  "
              f"mean(target=1)={r['mean_target1']:.3f}  mean(target=0)={r['mean_target0']:.3f}")

with open("data/processed/phase2_feature_screening.json", "w") as f:
    json.dump({
        "by_category_counts": {cat: len(cols) for cat, cols in by_cat.items()},
        "all_results": results,
        "skipped_non_numeric": skipped_non_numeric,
    }, f, ensure_ascii=False, indent=2)
print("\nwrote data/processed/phase2_feature_screening.json")
