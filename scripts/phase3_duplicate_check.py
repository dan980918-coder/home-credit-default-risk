"""
Phase 3: Phase 2에서 결측률이 비슷해 "중복 의심"으로 표시했던
D_49/D_132/D_106, D_134~D_138의 실제 값 상관관계와 결측 패턴 겹침을 확인.
결론: 값 상관은 낮음(중복 아님) / 결측 패턴은 거의 완전히 겹침(block-missing).
"""
import duckdb
import pandas as pd

SAMPLE_DATA = "data/processed/train_sample_50k.parquet"
COLS = ["D_49", "D_132", "D_106", "D_134", "D_135", "D_136", "D_137", "D_138"]

con = duckdb.connect()
con.execute("SET memory_limit='512MB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")

col_list = ", ".join(f'"{c}"' for c in COLS)
df = con.execute(f"SELECT {col_list} FROM read_parquet('{SAMPLE_DATA}')").fetchdf()

print("non-null row counts:")
print(df.notna().sum().to_string())

print("\npairwise Pearson correlation (value level):")
print(df.corr(min_periods=30).round(3).to_string())

group_b = ["D_134", "D_135", "D_136", "D_137", "D_138"]
same_pattern = df[group_b].isna().apply(lambda row: row.nunique() == 1, axis=1).mean()
print(f"\nD_134~D_138 결측 패턴 완전 일치 비율: {same_pattern:.4%}")

for a, b in [("D_49", "D_132"), ("D_49", "D_106")]:
    both = (df[a].isna() & df[b].isna()).sum()
    either = (df[a].isna() | df[b].isna()).sum()
    print(f"{a} vs {b} 결측 Jaccard 겹침: {both/either:.4%}")
