"""Phase 2 EDA: 클래스 불균형(target 0/1) 시각화. 원본 vs 샘플 비교."""
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "AppleGothic"  # macOS 한글 폰트 (글자 깨짐 방지)
plt.rcParams["axes.unicode_minus"] = False

RAW_DATA = "data/raw/train_data.parquet"
SAMPLE_DATA = "data/processed/train_sample_50k.parquet"
OUT_PATH = "reports/figures/phase2_class_imbalance.png"

con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")


def target_counts(path):
    rows = con.execute(f"""
        SELECT target, count(distinct customer_ID) AS n
        FROM read_parquet('{path}')
        GROUP BY target ORDER BY target
    """).fetchall()
    return {int(t): n for t, n in rows}


raw_counts = target_counts(RAW_DATA)
sample_counts = target_counts(SAMPLE_DATA)
print("raw:", raw_counts)
print("sample:", sample_counts)

fig, axes = plt.subplots(1, 2, figsize=(9, 4.5))
labels = ["target=0\n(정상)", "target=1\n(연체)"]
colors = ["#4C72B0", "#C44E52"]

for ax, counts, title in [
    (axes[0], raw_counts, f"원본 (n={sum(counts_ for counts_ in raw_counts.values())})"),
    (axes[1], sample_counts, f"50k 샘플 (n={sum(sample_counts.values())})"),
]:
    vals = [counts[0], counts[1]]
    total = sum(vals)
    bars = ax.bar(labels, vals, color=colors)
    ax.set_title(title)
    ax.set_ylabel("고객 수")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,}\n({v/total:.1%})",
                ha="center", va="bottom", fontsize=9)

fig.suptitle("클래스 불균형: target 분포 (원본 vs 샘플)")
fig.tight_layout()
fig.savefig(OUT_PATH, dpi=150)
print(f"saved {OUT_PATH}")
