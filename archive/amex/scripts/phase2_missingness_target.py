"""
Phase 2 EDA: 결측 자체가 target(연체)과 유의미하게 연관되는지 확인.
50%+ 결측 30개 컬럼 각각에 대해 (해당 컬럼 결측 여부) x (target) 분할표를
DuckDB 집계로 만들고, 카이제곱 검정 + phi 계수(연관 강도)를 계산한다.
"""
import json
import duckdb
from scipy.stats import chi2_contingency

SAMPLE_DATA = "data/processed/train_sample_50k.parquet"

con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")

with open("data/processed/validation_result.json") as f:
    high_missing_cols = json.load(f)["sample_high_missing_cols"]

n_total = con.execute(f"SELECT count(*) FROM read_parquet('{SAMPLE_DATA}')").fetchone()[0]

results = []
for col in high_missing_cols:
    row = con.execute(f"""
        SELECT
            sum(CASE WHEN "{col}" IS NULL AND target = 1 THEN 1 ELSE 0 END) AS null_pos,
            sum(CASE WHEN "{col}" IS NULL AND target = 0 THEN 1 ELSE 0 END) AS null_neg,
            sum(CASE WHEN "{col}" IS NOT NULL AND target = 1 THEN 1 ELSE 0 END) AS notnull_pos,
            sum(CASE WHEN "{col}" IS NOT NULL AND target = 0 THEN 1 ELSE 0 END) AS notnull_neg
        FROM read_parquet('{SAMPLE_DATA}')
    """).fetchone()
    null_pos, null_neg, notnull_pos, notnull_neg = row
    table = [[null_pos, null_neg], [notnull_pos, notnull_neg]]
    chi2, p, dof, expected = chi2_contingency(table)
    n = n_total
    phi = (chi2 / n) ** 0.5  # 2x2 table effect size

    missing_rate_pos = null_pos / (null_pos + notnull_pos)
    missing_rate_neg = null_neg / (null_neg + notnull_neg)

    results.append({
        "column": col,
        "missing_rate_target1": missing_rate_pos,
        "missing_rate_target0": missing_rate_neg,
        "rate_diff": missing_rate_pos - missing_rate_neg,
        "chi2": chi2,
        "p_value": p,
        "phi": phi,
    })

results.sort(key=lambda r: r["phi"], reverse=True)

print(f"{'column':8s} {'miss@1':>8s} {'miss@0':>8s} {'diff':>8s} {'phi':>8s} {'p_value':>12s}")
for r in results:
    print(f"{r['column']:8s} {r['missing_rate_target1']:8.3f} {r['missing_rate_target0']:8.3f} "
          f"{r['rate_diff']:+8.3f} {r['phi']:8.3f} {r['p_value']:12.2e}")

# rule of thumb flag: phi >= 0.1 (small-medium effect) as "notably associated"
notable = [r for r in results if r["phi"] >= 0.1]
print(f"\nphi >= 0.1 (결측 자체가 target과 뚜렷하게 연관): {len(notable)}개")
for r in notable:
    print(f"  {r['column']}: phi={r['phi']:.3f}, missing rate target=1 {r['missing_rate_target1']:.1%} "
          f"vs target=0 {r['missing_rate_target0']:.1%}")

with open("data/processed/phase2_missingness_target.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("\nwrote data/processed/phase2_missingness_target.json")
