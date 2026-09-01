"""README용 추가 EDA 그래프 5종 생성 (assets/figures/).

phase2_class_imbalance.py / phase2_representative_distributions.py가 이미 다룬 것 외에,
README 보강 요청으로 추가 분석한 항목들:
- CNT_CHILDREN / NAME_FAMILY_STATUS 구간별 TARGET 비율
- EXT_SOURCE_1/2/3 TARGET별 분포 비교
- DEF_30_CNT_SOCIAL_CIRCLE 유무에 따른 TARGET 비율
- DAYS_EMPLOYED 365243 이상치 처리 전/후 분포 비교
"""
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

PATH = "data/raw/application_train.csv"
OUT_DIR = "assets/figures"

con = duckdb.connect()
con.execute("SET memory_limit='1.5GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")

# ---------------------------------------------------------------------------
# 1. CNT_CHILDREN / NAME_FAMILY_STATUS 구간별 TARGET 비율
# ---------------------------------------------------------------------------
children = con.execute(f"""
    SELECT CASE WHEN CNT_CHILDREN >= 3 THEN '3+' ELSE CAST(CNT_CHILDREN AS VARCHAR) END AS grp,
           avg(TARGET) AS target_rate, count(*) AS n
    FROM read_csv_auto('{PATH}')
    GROUP BY grp ORDER BY grp
""").fetchdf()
print("CNT_CHILDREN target rate:\n", children)

family = con.execute(f"""
    SELECT NAME_FAMILY_STATUS AS grp, avg(TARGET) AS target_rate, count(*) AS n
    FROM read_csv_auto('{PATH}')
    GROUP BY grp ORDER BY target_rate DESC
""").fetchdf()
print("NAME_FAMILY_STATUS target rate:\n", family)

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
axes[0].bar(children["grp"], children["target_rate"] * 100, color="#4C72B0")
axes[0].set_title("자녀 수(CNT_CHILDREN)별 TARGET 비율")
axes[0].set_xlabel("자녀 수")
axes[0].set_ylabel("TARGET=1 비율 (%)")
axes[0].axhline(8.07, color="gray", linestyle="--", linewidth=1, label="전체 평균(8.1%)")
axes[0].legend(fontsize=8)

axes[1].barh(family["grp"], family["target_rate"] * 100, color="#DD8452")
axes[1].set_title("가족 상태(NAME_FAMILY_STATUS)별 TARGET 비율")
axes[1].set_xlabel("TARGET=1 비율 (%)")
axes[1].axvline(8.07, color="gray", linestyle="--", linewidth=1)
fig.suptitle("가족 구성별 TARGET(연체) 비율", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(f"{OUT_DIR}/children_family_target_rate.png", dpi=150)
plt.close(fig)
print(f"saved {OUT_DIR}/children_family_target_rate.png")

# ---------------------------------------------------------------------------
# 2. EXT_SOURCE_1/2/3 TARGET별 분포 비교
# ---------------------------------------------------------------------------
ext = con.execute(f"""
    SELECT TARGET, EXT_SOURCE_1, EXT_SOURCE_2, EXT_SOURCE_3
    FROM read_csv_auto('{PATH}')
""").fetchdf()

fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
for i, col in enumerate(["EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3"]):
    d0 = ext.loc[ext["TARGET"] == 0, col].dropna()
    d1 = ext.loc[ext["TARGET"] == 1, col].dropna()
    sns.kdeplot(d0, ax=axes[i], color="#4C72B0", label="TARGET=0", fill=True, alpha=0.3)
    sns.kdeplot(d1, ax=axes[i], color="#C44E52", label="TARGET=1", fill=True, alpha=0.3)
    axes[i].set_title(f"{col}\n(결측 {ext[col].isna().mean():.1%})", fontsize=10)
    axes[i].set_xlabel(col)
    axes[i].legend(fontsize=8)
fig.suptitle("외부 신용점수(EXT_SOURCE_1/2/3) TARGET별 분포 비교", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig(f"{OUT_DIR}/ext_source_distributions.png", dpi=150)
plt.close(fig)
print(f"saved {OUT_DIR}/ext_source_distributions.png")

# ---------------------------------------------------------------------------
# 3. DEF_30_CNT_SOCIAL_CIRCLE 유무에 따른 TARGET 비율
# ---------------------------------------------------------------------------
social = con.execute(f"""
    SELECT CASE WHEN DEF_30_CNT_SOCIAL_CIRCLE > 0 THEN '1건 이상' ELSE '0건' END AS grp,
           avg(TARGET) AS target_rate, count(*) AS n
    FROM read_csv_auto('{PATH}')
    WHERE DEF_30_CNT_SOCIAL_CIRCLE IS NOT NULL
    GROUP BY grp ORDER BY grp
""").fetchdf()
print("DEF_30_CNT_SOCIAL_CIRCLE target rate:\n", social)

fig, ax = plt.subplots(figsize=(5.5, 5))
bars = ax.bar(social["grp"], social["target_rate"] * 100, color=["#4C72B0", "#C44E52"])
for b, (rate, n) in zip(bars, zip(social["target_rate"], social["n"])):
    ax.text(b.get_x() + b.get_width() / 2, rate * 100, f"{rate:.1%}\n(n={n:,})",
            ha="center", va="bottom", fontsize=9)
ax.set_ylim(0, 12.5)
ax.set_title("DEF_30_CNT_SOCIAL_CIRCLE(30일 연체 이력 있는\n지인 수) 유무에 따른 TARGET 비율", fontsize=11)
ax.set_ylabel("TARGET=1 비율 (%)")
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/social_circle_default_target_rate.png", dpi=150)
plt.close(fig)
print(f"saved {OUT_DIR}/social_circle_default_target_rate.png")

# ---------------------------------------------------------------------------
# 4. DAYS_EMPLOYED 365243 이상치 처리 전/후 분포 비교
# ---------------------------------------------------------------------------
emp = con.execute(f"SELECT DAYS_EMPLOYED FROM read_csv_auto('{PATH}')").fetchdf()
before = emp["DAYS_EMPLOYED"]
after = emp.loc[emp["DAYS_EMPLOYED"] != 365243, "DAYS_EMPLOYED"]
anomaly_n = (emp["DAYS_EMPLOYED"] == 365243).sum()

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
axes[0].hist(before, bins=60, color="#C44E52")
axes[0].set_title(f"처리 전 (365243 이상치 {anomaly_n:,}건 포함, 전체 {anomaly_n/len(emp):.1%})")
axes[0].set_xlabel("DAYS_EMPLOYED")

axes[1].hist(after, bins=60, color="#4C72B0")
axes[1].set_title("처리 후 (365243 → NULL 치환, 정상 범위만 표시)")
axes[1].set_xlabel("DAYS_EMPLOYED")

fig.suptitle("DAYS_EMPLOYED 이상치(365243) 처리 전/후 분포", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig(f"{OUT_DIR}/days_employed_anomaly_before_after.png", dpi=150)
plt.close(fig)
print(f"saved {OUT_DIR}/days_employed_anomaly_before_after.png")

# ---------------------------------------------------------------------------
# 5. TARGET 클래스 분포 (reports/figures/phase2_class_imbalance.png과 동일 내용,
#    README 전용 자산 위치인 assets/figures/에도 함께 둠)
# ---------------------------------------------------------------------------
target_counts = con.execute(f"""
    SELECT TARGET, count(*) AS n FROM read_csv_auto('{PATH}') GROUP BY TARGET ORDER BY TARGET
""").fetchall()
counts = {int(t): n for t, n in target_counts}
total = sum(counts.values())

fig, ax = plt.subplots(figsize=(5, 4.5))
labels = ["TARGET=0\n(정상 상환)", "TARGET=1\n(연체)"]
vals = [counts[0], counts[1]]
bars = ax.bar(labels, vals, color=["#4C72B0", "#C44E52"])
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,}\n({v/total:.1%})",
            ha="center", va="bottom", fontsize=9)
ax.set_title(f"클래스 불균형: TARGET 분포 (n={total:,})")
ax.set_ylabel("고객 수")
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/target_distribution.png", dpi=150)
plt.close(fig)
print(f"saved {OUT_DIR}/target_distribution.png")

print("done")
