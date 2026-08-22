"""
Phase 2 EDA: 카테고리별 대표 변수(target과의 Pearson 상관 절대값 상위 3개,
카테고리 5개 x 3 = 15개) 분포를 target 0/1로 나눠 boxplot으로 시각화.
주의: 이 선정은 EDA 패턴 탐색용이며 최종 모델 feature 선택이 아님
(docs/phase2_eda.md §4 참고). 15개만 다루므로 DuckDB로 해당 컬럼만
pandas DataFrame으로 가져와도 메모리 문제 없음.
"""
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

SAMPLE_DATA = "data/processed/train_sample_50k.parquet"
OUT_PATH = "reports/figures/phase2_representative_distributions.png"

# category -> [(column, corr_with_target)], from phase2_feature_screening.py top-3
REPRESENTATIVE = {
    "B (Balance)": [("B_18", -0.484), ("B_9", +0.484), ("B_2", -0.480)],
    "D (Delinquency)": [("D_48", +0.545), ("D_61", +0.480), ("D_44", +0.468)],
    "P (Payment)": [("P_2", -0.610), ("P_4", +0.238), ("P_3", -0.237)],
    "R (Risk)": [("R_1", +0.360), ("R_3", +0.291), ("R_27", -0.274)],
    "S (Spend)": [("S_7", +0.328), ("S_3", +0.317), ("S_25", -0.245)],
}
ALL_COLS = [c for cols in REPRESENTATIVE.values() for c, _ in cols]

con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")

col_list = ", ".join(f'"{c}"' for c in ALL_COLS)
df = con.execute(f"SELECT {col_list}, target FROM read_parquet('{SAMPLE_DATA}')").fetchdf()
print(f"pulled {len(df)} rows x {len(df.columns)} cols for plotting")

fig, axes = plt.subplots(5, 3, figsize=(12, 16))
for row, (cat, cols) in enumerate(REPRESENTATIVE.items()):
    for col_idx, (col, corr) in enumerate(cols):
        ax = axes[row, col_idx]
        data0 = df.loc[df["target"] == 0, col].dropna()
        data1 = df.loc[df["target"] == 1, col].dropna()
        ax.boxplot([data0, data1], tick_labels=["target=0", "target=1"], showfliers=False,
                   patch_artist=True,
                   boxprops=dict(facecolor="#4C72B0" if col_idx == 0 else "#dd8452"))
        ax.set_title(f"{col} (corr={corr:+.3f})", fontsize=10)
        if col_idx == 0:
            ax.set_ylabel(cat, fontsize=10)

fig.suptitle("카테고리별 대표 변수 15개 — target 0/1 분포 비교\n(EDA 패턴 탐색용 선정, 최종 모델 feature 선택 아님)",
             fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(OUT_PATH, dpi=150)
print(f"saved {OUT_PATH}")

# duplicate-suspect check: do any of the 15 representative columns overlap
# with the D_49/D_132/D_106, D_134~D_138 duplicate-suspect group from §2?
duplicate_suspects = {"D_49", "D_132", "D_106", "D_134", "D_135", "D_136", "D_137", "D_138"}
overlap = duplicate_suspects & set(ALL_COLS)
print(f"overlap with duplicate-suspect columns: {overlap if overlap else 'none'}")
