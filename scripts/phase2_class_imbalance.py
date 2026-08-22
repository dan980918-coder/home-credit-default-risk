"""Phase 2 EDA: TARGET 클래스 불균형 시각화."""
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

OUT_PATH = "reports/figures/phase2_class_imbalance.png"

con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")

rows = con.execute("""
    SELECT TARGET, count(*) AS n
    FROM read_csv_auto('data/raw/application_train.csv')
    GROUP BY TARGET ORDER BY TARGET
""").fetchall()
counts = {int(t): n for t, n in rows}
print("TARGET counts:", counts)
total = sum(counts.values())
print(f"TARGET=0 (정상): {counts[0]:,} ({counts[0]/total:.2%})")
print(f"TARGET=1 (연체): {counts[1]:,} ({counts[1]/total:.2%})")

fig, ax = plt.subplots(figsize=(5, 4.5))
labels = ["TARGET=0\n(정상 상환)", "TARGET=1\n(연체)"]
vals = [counts[0], counts[1]]
colors = ["#4C72B0", "#C44E52"]
bars = ax.bar(labels, vals, color=colors)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,}\n({v/total:.1%})",
            ha="center", va="bottom", fontsize=9)
ax.set_title(f"클래스 불균형: TARGET 분포 (n={total:,})")
ax.set_ylabel("고객 수")
fig.tight_layout()
fig.savefig(OUT_PATH, dpi=150)
print(f"saved {OUT_PATH}")
