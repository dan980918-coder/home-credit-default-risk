"""
06_h2_followup.py
Loan Approval Risk Scoring - v2 재분석
4단계 1절: H2(상환부담) 기각 원인 탐색. "기존 심사가 이미 부담이 큰 신청자를
걸러냈다"는 가설을 정황 증거로만 살펴본다 (단정하지 않음). 학습 세트만 사용.

실행: python3 -I v2/scripts/06_h2_followup.py
출력: v2/docs/h2_followup_results.json, v2/docs/figures/h2_*.png
"""
import json
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FEAT_PATH = os.path.join(ROOT, "v2", "data", "features", "hypothesis_features.parquet")
SPLIT_DIR = os.path.join(ROOT, "v2", "data", "splits")
DOCS_DIR = os.path.join(ROOT, "v2", "docs")
FIG_DIR = os.path.join(DOCS_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

for font_name in ["AppleGothic", "NanumGothic", "Nanum Gothic"]:
    if any(f.name == font_name for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = font_name
        break
plt.rcParams["axes.unicode_minus"] = False

features = pd.read_parquet(FEAT_PATH)
train_ids = pd.read_csv(os.path.join(SPLIT_DIR, "train_ids.csv"))
df = train_ids.merge(features, on="SK_ID_CURR", how="left")
n_train = len(df)
print(f"학습 세트: {n_train:,}명")

results = {}

# -----------------------------------------------------------------
# 1. annuity_to_income 분포 상한
# -----------------------------------------------------------------
x = df["annuity_to_income"].dropna()
percentiles = [50, 90, 95, 99, 99.9]
pct_values = {f"p{p}": round(float(np.percentile(x, p)), 4) for p in percentiles}
pct_values["max"] = round(float(x.max()), 4)
pct_values["n_valid"] = int(len(x))
results["annuity_to_income_distribution"] = pct_values
print("annuity_to_income 분포:", json.dumps(pct_values, ensure_ascii=False, indent=2))

# 특정 값 근처 급격한 절단/몰림 확인: 소수점 반올림 단위로 몰림 빈도 집계
rounded = (x * 100).round().astype(int)  # 0.01 단위
top_spikes = rounded.value_counts().head(10)
results["annuity_to_income_spikes_pct_of_n"] = {
    str(k / 100): round(v / len(x) * 100, 3) for k, v in top_spikes.items()
}
print("몰림 상위 10 (값/100 단위):", results["annuity_to_income_spikes_pct_of_n"])

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
axes[0].hist(x, bins=100, color="#4C72B0")
for p in [90, 95, 99]:
    v = np.percentile(x, p)
    axes[0].axvline(v, color="red", linestyle="--", linewidth=0.8)
    axes[0].text(v, axes[0].get_ylim()[1] * 0.9, f"p{p}", rotation=90, fontsize=8, color="red")
axes[0].set_title("annuity_to_income 전체 분포")
axes[0].set_xlabel("AMT_ANNUITY / AMT_INCOME_TOTAL")
axes[0].set_ylabel("신청자 수")

axes[1].hist(x[x <= np.percentile(x, 99.5)], bins=100, color="#55A868")
axes[1].set_title("annuity_to_income 분포 (상위 0.5% 제외, 확대)")
axes[1].set_xlabel("AMT_ANNUITY / AMT_INCOME_TOTAL")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "h2_annuity_to_income_distribution.png"), dpi=130)
plt.close()
print("그림 저장: h2_annuity_to_income_distribution.png")

# -----------------------------------------------------------------
# 2. credit_to_annuity 구간별 외부 신용점수 평균의 평균
# -----------------------------------------------------------------
cta = df["credit_to_annuity"]
valid = cta.notna() & df["ext_source_mean"].notna()
d2 = df[valid].copy()
d2["cta_decile"] = pd.qcut(d2["credit_to_annuity"], q=10, duplicates="drop")
decile_summary = d2.groupby("cta_decile", observed=True).agg(
    n=("SK_ID_CURR", "count"),
    credit_to_annuity_mean=("credit_to_annuity", "mean"),
    ext_source_mean_avg=("ext_source_mean", "mean"),
    bad_rate=("TARGET", "mean"),
).reset_index()
decile_summary["cta_decile"] = decile_summary["cta_decile"].astype(str)
decile_summary["bad_rate_pct"] = (decile_summary["bad_rate"] * 100).round(3)
decile_summary["ext_source_mean_avg"] = decile_summary["ext_source_mean_avg"].round(4)
decile_summary["credit_to_annuity_mean"] = decile_summary["credit_to_annuity_mean"].round(3)
results["credit_to_annuity_decile_vs_extsource"] = decile_summary.to_dict(orient="records")
print("\ncredit_to_annuity 구간별 외부점수 평균:")
print(decile_summary[["cta_decile", "n", "credit_to_annuity_mean", "ext_source_mean_avg", "bad_rate_pct"]])

corr_cta_ext = d2["credit_to_annuity"].corr(d2["ext_source_mean"])
results["corr_credit_to_annuity_vs_ext_source_mean"] = round(float(corr_cta_ext), 4)
print(f"\ncredit_to_annuity와 ext_source_mean의 상관계수: {corr_cta_ext:.4f}")

fig, ax1 = plt.subplots(figsize=(9, 5))
x_pos = range(len(decile_summary))
ax1.bar(x_pos, decile_summary["ext_source_mean_avg"], color="#8172B2", alpha=0.7, label="외부신용점수 평균(좌축)")
ax1.set_ylabel("EXT_SOURCE 평균의 평균")
ax1.set_xticks(x_pos)
ax1.set_xticklabels([f"D{i+1}" for i in x_pos])
ax1.set_xlabel("credit_to_annuity 10분위 (D1=짧은 할부 ~ D10=긴 할부)")
ax2 = ax1.twinx()
ax2.plot(x_pos, decile_summary["bad_rate_pct"], color="#C44E52", marker="o", label="연체율(우축)")
ax2.set_ylabel("연체율(%)")
fig.legend(loc="upper center", bbox_to_anchor=(0.5, 1.02), ncol=2, fontsize=9)
plt.title("credit_to_annuity 분위별 외부신용점수와 연체율", pad=30)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "h2_credit_to_annuity_vs_extsource.png"), dpi=130)
plt.close()
print("그림 저장: h2_credit_to_annuity_vs_extsource.png")

# -----------------------------------------------------------------
# 3. 외부 신용점수 5분위 안에서 credit_to_annuity 방향 확인
# -----------------------------------------------------------------
d3 = df[df["ext_source_mean"].notna() & df["credit_to_annuity"].notna()].copy()
d3["ext_quintile"] = pd.qcut(d3["ext_source_mean"], q=5, labels=[f"Q{i+1}(낮음)" if i == 0 else (f"Q{i+1}(높음)" if i == 4 else f"Q{i+1}") for i in range(5)])

within_quintile = []
for q, grp in d3.groupby("ext_quintile", observed=True):
    grp = grp.copy()
    try:
        grp["cta_bin"] = pd.qcut(grp["credit_to_annuity"], q=5, duplicates="drop")
    except Exception:
        within_quintile.append({"ext_quintile": str(q), "n": len(grp), "spearman_rho": None, "note": "분위 생성 실패"})
        continue
    bin_stats = grp.groupby("cta_bin", observed=True)["TARGET"].agg(["count", "mean"]).reset_index()
    bin_stats["order"] = range(len(bin_stats))
    if len(bin_stats) >= 2:
        from scipy import stats as spstats
        rho, pval = spstats.spearmanr(bin_stats["order"], bin_stats["mean"])
    else:
        rho, pval = np.nan, np.nan
    within_quintile.append({
        "ext_quintile": str(q), "n": len(grp),
        "spearman_rho": None if pd.isna(rho) else round(float(rho), 4),
        "bad_rate_by_cta_bin_pct": [round(v * 100, 3) for v in bin_stats["mean"]],
    })

results["within_ext_source_quintile_credit_to_annuity_direction"] = within_quintile
print("\n외부점수 5분위 내 credit_to_annuity 방향(Spearman rho):")
for r in within_quintile:
    print(f"  {r['ext_quintile']}: n={r['n']}, rho={r['spearman_rho']}")

fig, ax = plt.subplots(figsize=(9, 5))
for r in within_quintile:
    if r.get("bad_rate_by_cta_bin_pct"):
        ax.plot(range(1, len(r["bad_rate_by_cta_bin_pct"]) + 1), r["bad_rate_by_cta_bin_pct"],
                marker="o", label=r["ext_quintile"])
ax.set_xlabel("credit_to_annuity 5분위 (낮음→높음)")
ax.set_ylabel("연체율(%)")
ax.set_title("외부신용점수 5분위 안에서 credit_to_annuity별 연체율")
ax.legend(title="외부점수 분위", fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "h2_within_extsource_quintile.png"), dpi=130)
plt.close()
print("그림 저장: h2_within_extsource_quintile.png")

with open(os.path.join(DOCS_DIR, "h2_followup_results.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)

print(f"\n완료: {os.path.join(DOCS_DIR, 'h2_followup_results.json')}")
