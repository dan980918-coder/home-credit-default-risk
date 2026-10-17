"""
Phase 2 EDA: application_train 121개 feature 컬럼(SK_ID_CURR, TARGET 제외)의
결측률을 스캔하고, 50%+ 결측 컬럼에 대해 (결측 여부) x TARGET 카이제곱검정 +
phi 계수로 연관 강도를 확인. AMEX Phase 2와 동일한 방법론.
"""
import json
import duckdb
from scipy.stats import chi2_contingency

PATH = "data/raw/application_train.csv"
KEY_COLS = {"SK_ID_CURR", "TARGET"}

con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")

schema = con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{PATH}')").fetchall()
feature_cols = [row[0] for row in schema if row[0] not in KEY_COLS]
print(f"feature columns: {len(feature_cols)}")

n_total = con.execute(f"SELECT count(*) FROM read_csv_auto('{PATH}')").fetchone()[0]

exprs = ", ".join(f'count("{c}") AS nn_{i}' for i, c in enumerate(feature_cols))
row = con.execute(f"SELECT {exprs} FROM read_csv_auto('{PATH}')").fetchone()
null_frac = {}
for i, c in enumerate(feature_cols):
    null_frac[c] = 1 - row[i] / n_total

high_missing = sorted([c for c, f in null_frac.items() if f >= 0.5], key=lambda c: -null_frac[c])
print(f"\n50%+ 결측 컬럼: {len(high_missing)}개")
for c in high_missing[:10]:
    print(f"  {c}: {null_frac[c]:.1%}")
if len(high_missing) > 10:
    print(f"  ... 외 {len(high_missing)-10}개")

print("\n결측-TARGET 연관성 (phi 계수):")
results = []
for col in high_missing:
    r = con.execute(f"""
        SELECT
            sum(CASE WHEN "{col}" IS NULL AND TARGET = 1 THEN 1 ELSE 0 END) AS null_pos,
            sum(CASE WHEN "{col}" IS NULL AND TARGET = 0 THEN 1 ELSE 0 END) AS null_neg,
            sum(CASE WHEN "{col}" IS NOT NULL AND TARGET = 1 THEN 1 ELSE 0 END) AS nn_pos,
            sum(CASE WHEN "{col}" IS NOT NULL AND TARGET = 0 THEN 1 ELSE 0 END) AS nn_neg
        FROM read_csv_auto('{PATH}')
    """).fetchone()
    null_pos, null_neg, nn_pos, nn_neg = r
    table = [[null_pos, null_neg], [nn_pos, nn_neg]]
    chi2, p, dof, exp = chi2_contingency(table)
    phi = (chi2 / n_total) ** 0.5
    miss_rate_1 = null_pos / (null_pos + nn_pos)
    miss_rate_0 = null_neg / (null_neg + nn_neg)
    results.append({"column": col, "null_frac": null_frac[col], "phi": phi, "p_value": p,
                     "missing_rate_target1": miss_rate_1, "missing_rate_target0": miss_rate_0})

results.sort(key=lambda r: -r["phi"])
print(f"\n{'column':30s} {'null_frac':>10s} {'phi':>8s} {'miss@1':>8s} {'miss@0':>8s}")
for r in results[:20]:
    print(f"{r['column']:30s} {r['null_frac']:10.1%} {r['phi']:8.3f} "
          f"{r['missing_rate_target1']:8.1%} {r['missing_rate_target0']:8.1%}")

notable = [r for r in results if r["phi"] >= 0.05]
print(f"\nphi >= 0.05 (약한~중간 연관, 표본이 커서 임계값을 AMEX보다 낮춤): {len(notable)}개")

with open("data/processed/phase2_missingness_target.json", "w") as f:
    json.dump({"all_null_frac": null_frac, "high_missing_results": results}, f,
               ensure_ascii=False, indent=2)
print("\nwrote data/processed/phase2_missingness_target.json")
