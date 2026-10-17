"""
Phase 2 EDA: AMT_INCOME_TOTAL / AMT_CREDIT / DAYS_EMPLOYED의 TARGET별 분포 비교.
DAYS_EMPLOYED는 365243이라는 placeholder(무직/은퇴 등 "고용되지 않음" 표시)가
껴있어(전체 18%) 실제 값 분포에서 제외하고 별도로 anomaly 비율을 target별로 비교.
"""
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

PATH = "data/raw/application_train.csv"
OUT_PATH = "reports/figures/phase2_representative_distributions.png"

con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")

df = con.execute(f"""
    SELECT TARGET, AMT_INCOME_TOTAL, AMT_CREDIT,
           CASE WHEN DAYS_EMPLOYED = 365243 THEN NULL ELSE DAYS_EMPLOYED END AS DAYS_EMPLOYED_CLEAN
    FROM read_csv_auto('{PATH}')
""").fetchdf()
print(f"pulled {len(df)} rows")

# DAYS_EMPLOYED anomaly rate by target (참고용, 이미 확인했지만 차트 텍스트에도 반영)
anomaly = con.execute(f"""
    SELECT TARGET, avg(CASE WHEN DAYS_EMPLOYED=365243 THEN 1.0 ELSE 0.0 END)
    FROM read_csv_auto('{PATH}') GROUP BY TARGET ORDER BY TARGET
""").fetchall()
anomaly_map = {int(t): r for t, r in anomaly}
print("DAYS_EMPLOYED anomaly(365243) rate by target:", anomaly_map)

fig, axes = plt.subplots(1, 3, figsize=(13, 5))

specs = [
    ("AMT_INCOME_TOTAL", "연 소득", axes[0]),
    ("AMT_CREDIT", "대출 신청액", axes[1]),
    ("DAYS_EMPLOYED_CLEAN", "재직일수(음수=과거, anomaly 제외)", axes[2]),
]
for col, title, ax in specs:
    d0 = df.loc[df["TARGET"] == 0, col].dropna()
    d1 = df.loc[df["TARGET"] == 1, col].dropna()
    ax.boxplot([d0, d1], tick_labels=["TARGET=0", "TARGET=1"], showfliers=False,
               patch_artist=True, boxprops=dict(facecolor="#4C72B0"))
    ax.set_title(f"{col}\n({title})", fontsize=10)

fig.suptitle("TARGET별 주요 변수 분포 비교 (이상치 제외 boxplot)", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(OUT_PATH, dpi=150)
print(f"saved {OUT_PATH}")
