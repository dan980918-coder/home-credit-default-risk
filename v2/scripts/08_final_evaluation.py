"""
08_final_evaluation.py
Loan Approval Risk Scoring - v2 재분석
4단계 3절: 최종 평가. 최종평가(holdout) 세트를 이 스크립트에서 처음 연다.
모든 모델·설정은 07_models.py에서 이미 확정됐고, 이 스크립트는 그 결과를
불러와 적용만 한다 - 결과를 보고 모델/변수/설정을 바꾸지 않는다.

산출:
  v2/docs/final_evaluation_results.json
  v2/docs/figures/{tradeoff_champion_vs_challenger,swap_set_80,profit_scenarios}.png
  v2/data/predictions/test_scores.parquet (커밋 안 함)

실행: python3 -I v2/scripts/08_final_evaluation.py
"""
import json
import os
import pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from sklearn.metrics import roc_auc_score

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FEAT_PATH = os.path.join(ROOT, "v2", "data", "features", "hypothesis_features.parquet")
SPLIT_DIR = os.path.join(ROOT, "v2", "data", "splits")
DOCS_DIR = os.path.join(ROOT, "v2", "docs")
FIG_DIR = os.path.join(DOCS_DIR, "figures")
MODEL_DIR = os.path.join(ROOT, "v2", "data", "models")
PRED_DIR = os.path.join(ROOT, "v2", "data", "predictions")
os.makedirs(PRED_DIR, exist_ok=True)

for font_name in ["AppleGothic", "NanumGothic", "Nanum Gothic"]:
    if any(f.name == font_name for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = font_name
        break
plt.rcParams["axes.unicode_minus"] = False

SEED = 42
RNG = np.random.default_rng(SEED)
N_BOOTSTRAP = 1000

# -----------------------------------------------------------------
# 0. 원본 application_train에서 TARGET을 직접 읽어오는 대신,
#    (정확히 최종평가 세트 TARGET이 담긴 유일한 원천인) raw CSV에서 읽는다.
#    주의: 이 파일이 holdout_ids.csv와 병합해 TARGET을 여는 "최초 1회"다.
# -----------------------------------------------------------------
import duckdb
con = duckdb.connect()
p_train_raw = os.path.join(ROOT, "data", "raw", "application_train.csv")
target_lookup = con.execute(f"SELECT SK_ID_CURR, TARGET FROM read_csv_auto('{p_train_raw}')").fetchdf()
con.close()

holdout_ids = pd.read_csv(os.path.join(SPLIT_DIR, "holdout_ids.csv"))  # SK_ID_CURR만 (TARGET 없음 - 의도적)
holdout_ids = holdout_ids.merge(target_lookup, on="SK_ID_CURR", how="left")  # 여기서 "처음" TARGET을 연다
assert holdout_ids["TARGET"].notna().all()

features = pd.read_parquet(FEAT_PATH)
holdout = holdout_ids.merge(features, on="SK_ID_CURR", how="left")
print(f"최종평가 세트: {len(holdout):,}명, 기저 연체율: {holdout['TARGET'].mean()*100:.3f}%")

# EXT_SOURCE 결측 플래그 (07과 동일 로직)
for c in ["EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3"]:
    holdout[f"{c}_MISSING"] = holdout[c].isna().astype(int)

# -----------------------------------------------------------------
# 1. 07_models.py에서 확정된 모델 아티팩트 로드
# -----------------------------------------------------------------
with open(os.path.join(MODEL_DIR, "selection.json"), encoding="utf-8") as f:
    selection = json.load(f)
selected_model_type = selection["selected_model_type"]
final_label = selection["final_label"]
print(f"선택된 모델: {selected_model_type} / {final_label}")

with open(os.path.join(MODEL_DIR, "champion_model.pkl"), "rb") as f:
    champ_art = pickle.load(f)

with open(os.path.join(MODEL_DIR, f"{final_label}_model.pkl"), "rb") as f:
    final_art = pickle.load(f)

with open(os.path.join(DOCS_DIR, "modeling_results.json"), encoding="utf-8") as f:
    modeling_results = json.load(f)

MISSING_LABEL = "(결측)"


# bin 변환 함수 (07_models.py와 동일 알고리즘 재사용 - 스코어카드 적용 시 필요)
def bin_numeric_transform(x, fit_info):
    edges = fit_info["edges"]
    out = pd.Series(MISSING_LABEL, index=x.index, dtype="object")
    valid_mask = x.notna()
    for b, lo, hi in edges:
        if b == edges[-1][0]:
            mask = valid_mask & (x >= lo)
        else:
            mask = valid_mask & (x >= lo) & (x <= hi)
        out.loc[mask] = f"bin{b}"
    if edges:
        first_b, first_lo, _ = edges[0]
        last_b, _, last_hi = edges[-1]
        out.loc[valid_mask & (x < first_lo)] = f"bin{first_b}"
        out.loc[valid_mask & (x > last_hi)] = f"bin{last_b}"
    return out


def bin_categorical_transform(x, fit_info):
    keep = fit_info["keep"]
    valid_mask = x.notna()
    out = pd.Series(MISSING_LABEL, index=x.index, dtype="object")
    mapped = x[valid_mask].astype(str).apply(lambda v: v if v in keep else "기타")
    out.loc[valid_mask] = mapped
    return out


def transform_bins(x, fit_info):
    if fit_info["type"] == "categorical":
        return bin_categorical_transform(x, fit_info)
    return bin_numeric_transform(x, fit_info)


# -----------------------------------------------------------------
# 2. 점수 계산
#    champion_score / new_score = P(정상상환) = 1 - P(bad)  (높을수록 안전, 두 모델 공통 규약)
# -----------------------------------------------------------------
champ_X = holdout[champ_art["cols"]].copy()
for c in ["EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3"]:
    champ_X[c] = champ_X[c].fillna(champ_art["medians"][c])
champ_pbad = champ_art["model"].predict_proba(champ_X)[:, 1]
champ_score = 1 - champ_pbad

if selected_model_type == "scorecard":
    with open(os.path.join(MODEL_DIR, "scorecard_bins.pkl"), "rb") as f:
        sc_bins = pickle.load(f)
    bin_fits = sc_bins["bin_fits"]
    woe_tables = sc_bins["woe_tables"]
    var_list = final_art["var_list"]
    X_new = pd.DataFrame({c: transform_bins(holdout[c], bin_fits[c]).map(woe_tables[c]["woe"].to_dict())
                           for c in var_list}).fillna(0.0)
    new_pbad = final_art["model"].predict_proba(X_new)[:, 1]
    # 새 점수 = 점수표 포인트 합(06_scorecard_points.md와 동일 정의, 높을수록 안전)
    pts = modeling_results["points_table"]
    base_points = pts["base_points"]
    new_score_points = np.full(len(holdout), base_points, dtype=float)
    for c in var_list:
        bins_for_c = transform_bins(holdout[c], bin_fits[c])
        point_map = pts["variables"][c]["bin_points"]
        new_score_points += bins_for_c.map(point_map).fillna(0.0).values
    new_score = new_score_points  # 포인트 스케일 (높을수록 안전)
else:
    cat_vars = final_art["categorical"]
    X_new = holdout[final_art["var_list"]].copy()
    for c in cat_vars:
        X_new[c] = X_new[c].astype(str).where(X_new[c].notna(), np.nan).astype("category")
    new_pbad = final_art["model"].predict_proba(X_new)[:, 1]
    new_score = 1 - new_pbad  # LightGBM은 확률 기반 점수(높을수록 안전)

holdout["champion_score"] = champ_score
holdout["new_score"] = new_score
holdout["champion_pbad"] = champ_pbad
holdout["new_pbad"] = new_pbad

# -----------------------------------------------------------------
# 3-1. 기본 성능: AUC, KS, Gini, 기저 연체율
# -----------------------------------------------------------------
def ks_statistic(y_true, risk_score):
    # risk_score: 클수록 위험(연체 확률)
    df_ = pd.DataFrame({"y": y_true, "s": risk_score}).sort_values("s")
    n_bad = df_["y"].sum()
    n_good = len(df_) - n_bad
    cum_bad = df_["y"].cumsum() / n_bad
    cum_good = (1 - df_["y"]).cumsum() / n_good
    return float((cum_bad - cum_good).abs().max())


y_true = holdout["TARGET"].values
champ_auc = roc_auc_score(y_true, champ_pbad)
champ_ks = ks_statistic(y_true, champ_pbad)
champ_gini = 2 * champ_auc - 1
new_auc = roc_auc_score(y_true, new_pbad)
new_ks = ks_statistic(y_true, new_pbad)
new_gini = 2 * new_auc - 1
base_rate = float(holdout["TARGET"].mean())

print(f"\n[최종평가] Champion: AUC={champ_auc:.4f} KS={champ_ks:.4f} Gini={champ_gini:.4f}")
print(f"[최종평가] 새 점수({final_label}): AUC={new_auc:.4f} KS={new_ks:.4f} Gini={new_gini:.4f}")
print(f"[최종평가] 기저 연체율: {base_rate*100:.3f}%")

results = {
    "selected_model_type": selected_model_type,
    "final_label": final_label,
    "n_holdout": len(holdout),
    "base_rate_pct": round(base_rate * 100, 3),
    "basic_performance": {
        "champion": {"auc": round(float(champ_auc), 5), "ks": round(float(champ_ks), 5), "gini": round(float(champ_gini), 5)},
        "new_score": {"auc": round(float(new_auc), 5), "ks": round(float(new_ks), 5), "gini": round(float(new_gini), 5)},
    },
}


# -----------------------------------------------------------------
# 3-2. H6: 스왑셋 분석
# -----------------------------------------------------------------
def approve_mask(score, approval_rate):
    """score: 높을수록 안전. approval_rate 비율만큼 상위(안전)를 승인."""
    threshold = np.quantile(score, 1 - approval_rate)
    return score >= threshold


def approved_bad_rate(score, target, approval_rate):
    mask = approve_mask(score, approval_rate)
    return float(target[mask].mean()), int(mask.sum())


def scan_approval_rate_for_target_rate(score, target, target_rate, grid=None):
    """new_score 기준으로, 승인군 연체율이 target_rate 이하가 되는 가장 높은 승인율을 찾는다."""
    if grid is None:
        grid = np.arange(0.50, 1.0001, 0.01)
    best_rate = None
    for a in grid:
        rate, _ = approved_bad_rate(score, target, a)
        if rate <= target_rate:
            best_rate = a
    return best_rate


approval_rates = [0.70, 0.80, 0.90]
h6_table = []
for a in approval_rates:
    champ_rate, champ_n = approved_bad_rate(champ_score, holdout["TARGET"].values, a)
    new_rate, new_n = approved_bad_rate(new_score, holdout["TARGET"].values, a)
    diff_pp = (champ_rate - new_rate) * 100
    rel_reduction = (champ_rate - new_rate) / champ_rate * 100 if champ_rate > 0 else np.nan
    h6_table.append({
        "approval_rate": a, "champion_bad_rate_pct": round(champ_rate * 100, 3),
        "new_score_bad_rate_pct": round(new_rate * 100, 3),
        "diff_pp": round(diff_pp, 3), "relative_reduction_pct": round(float(rel_reduction), 2),
    })
print("\nH6 (승인율별 연체율):")
for r in h6_table:
    print(" ", r)

# 같은 연체율에서 승인율 증가
champ_rate_80, _ = approved_bad_rate(champ_score, holdout["TARGET"].values, 0.80)
new_rate_needed = scan_approval_rate_for_target_rate(new_score, holdout["TARGET"].values, champ_rate_80)
approval_rate_increase = (new_rate_needed - 0.80) * 100 if new_rate_needed is not None else None
print(f"\n현행 80% 승인율의 연체율 {champ_rate_80*100:.3f}%와 같거나 낮은 연체율을 새 점수는 {new_rate_needed*100 if new_rate_needed else 'N/A'}% 승인율에서 달성 (증가폭 {approval_rate_increase}%p)")

# 부트스트랩 95% CI (seed 고정, 복원추출 1,000회)
boot_diffs = {a: [] for a in approval_rates}
boot_rate_increase = []
n_h = len(holdout)
target_arr = holdout["TARGET"].values
champ_arr = champ_score.values if hasattr(champ_score, "values") else champ_score
new_arr = new_score.values if hasattr(new_score, "values") else new_score

for i in range(N_BOOTSTRAP):
    idx = RNG.integers(0, n_h, n_h)
    t_b, c_b, n_b = target_arr[idx], champ_arr[idx], new_arr[idx]
    for a in approval_rates:
        cr, _ = approved_bad_rate(c_b, t_b, a)
        nr, _ = approved_bad_rate(n_b, t_b, a)
        boot_diffs[a].append((cr - nr) * 100)
    cr80, _ = approved_bad_rate(c_b, t_b, 0.80)
    nr_needed = scan_approval_rate_for_target_rate(n_b, t_b, cr80)
    if nr_needed is not None:
        boot_rate_increase.append((nr_needed - 0.80) * 100)

for row in h6_table:
    a = row["approval_rate"]
    diffs = np.array(boot_diffs[a])
    row["diff_pp_ci_low"] = round(float(np.percentile(diffs, 2.5)), 3)
    row["diff_pp_ci_high"] = round(float(np.percentile(diffs, 97.5)), 3)

rate_increase_ci = [round(float(np.percentile(boot_rate_increase, 2.5)), 3),
                     round(float(np.percentile(boot_rate_increase, 97.5)), 3)] if boot_rate_increase else [None, None]

print("\nH6 부트스트랩 95% CI 반영:")
for r in h6_table:
    print(" ", r)
print(f"승인율 증가폭 95% CI: {rate_increase_ci}")

# 스왑셋 표 (승인율 80%)
champ_approve_80 = approve_mask(champ_score, 0.80)
new_approve_80 = approve_mask(new_score, 0.80)
swap_groups = {
    "둘다승인": champ_approve_80 & new_approve_80,
    "둘다거절": (~champ_approve_80) & (~new_approve_80),
    "swap_out(현행승인,새점수거절)": champ_approve_80 & (~new_approve_80),
    "swap_in(현행거절,새점수승인)": (~champ_approve_80) & new_approve_80,
}
swap_table = []
for name, mask in swap_groups.items():
    n = int(mask.sum())
    bad_rate = float(holdout["TARGET"].values[mask].mean()) if n > 0 else np.nan
    swap_table.append({"group": name, "n": n, "pct_of_total": round(n / len(holdout) * 100, 2),
                        "bad_rate_pct": round(bad_rate * 100, 3) if n > 0 else None})
print("\n스왑셋(승인율 80%):")
for r in swap_table:
    print(" ", r)

# H6 판정 (사전 고정)
all_ci_positive = all(row["diff_pp_ci_low"] > 0 for row in h6_table)
some_ci_positive = any(row["diff_pp_ci_low"] > 0 for row in h6_table)
if all_ci_positive:
    h6_verdict = "채택"
elif some_ci_positive:
    h6_verdict = "부분 채택"
    h6_verdict_detail = [row["approval_rate"] for row in h6_table if row["diff_pp_ci_low"] > 0]
else:
    h6_verdict = "기각"
    h6_verdict_detail = []
if h6_verdict == "부분 채택":
    h6_verdict_note = f"승인율 {h6_verdict_detail} 지점에서만 신뢰구간 하한>0"
elif h6_verdict == "채택":
    h6_verdict_note = "세 승인율 모두 신뢰구간 하한>0"
else:
    h6_verdict_note = "모든 승인율에서 신뢰구간 하한<=0"
print(f"\nH6 판정: {h6_verdict} ({h6_verdict_note})")

results["h6"] = {
    "table": h6_table,
    "same_bad_rate_approval_increase": {
        "champion_bad_rate_at_80pct_pct": round(champ_rate_80 * 100, 3),
        "new_score_approval_rate_for_same_bad_rate_pct": round(new_rate_needed * 100, 2) if new_rate_needed else None,
        "approval_rate_increase_pp": round(approval_rate_increase, 2) if approval_rate_increase is not None else None,
        "approval_rate_increase_ci": rate_increase_ci,
    },
    "swap_set_80": swap_table,
    "verdict": h6_verdict,
    "verdict_note": h6_verdict_note,
}

# -----------------------------------------------------------------
# 3-3. H7: 수익 기준 최적 지점
# -----------------------------------------------------------------
r_values = [0.10, 0.20, 0.30]
lgd_values = [0.40, 0.60]
approval_grid = np.arange(0.50, 1.0001, 0.01)
amt_credit = holdout["AMT_CREDIT"].values
target_vals = holdout["TARGET"].values


def profit_curve(score, approval_grid, r, lgd):
    profits = []
    for a in approval_grid:
        mask = approve_mask(score, a)
        good_mask = mask & (target_vals == 0)
        bad_mask = mask & (target_vals == 1)
        profit = r * amt_credit[good_mask].sum() - lgd * amt_credit[bad_mask].sum()
        profits.append(profit)
    return np.array(profits)


h7_table = []
for r in r_values:
    for lgd in lgd_values:
        champ_profits = profit_curve(champ_score, approval_grid, r, lgd)
        new_profits = profit_curve(new_score, approval_grid, r, lgd)
        full_approval_profit = (r * amt_credit[target_vals == 0].sum() - lgd * amt_credit[target_vals == 1].sum())
        champ_index = champ_profits / full_approval_profit * 100
        new_index = new_profits / full_approval_profit * 100

        champ_best_i = np.argmax(champ_profits)
        new_best_i = np.argmax(new_profits)
        champ_best_a = float(approval_grid[champ_best_i])
        new_best_a = float(approval_grid[new_best_i])
        champ_best_rate, _ = approved_bad_rate(champ_score, target_vals, champ_best_a)
        new_best_rate, _ = approved_bad_rate(new_score, target_vals, new_best_a)
        breakeven_rate = r / (r + lgd)

        h7_table.append({
            "r": r, "lgd": lgd, "breakeven_bad_rate_pct": round(breakeven_rate * 100, 2),
            "champion_best_approval_rate": round(champ_best_a, 2),
            "champion_best_bad_rate_pct": round(champ_best_rate * 100, 3),
            "champion_profit_index": round(float(champ_index[champ_best_i]), 3),
            "new_score_best_approval_rate": round(new_best_a, 2),
            "new_score_best_bad_rate_pct": round(new_best_rate * 100, 3),
            "new_score_profit_index": round(float(new_index[new_best_i]), 3),
            "profit_index_gain": round(float(new_index[new_best_i] - champ_index[champ_best_i]), 3),
            "new_best_is_interior": bool(0.50 < new_best_a < 1.00),
        })

print("\nH7 (수익 시나리오):")
for r_ in h7_table:
    print(" ", r_)

n_interior = sum(1 for r_ in h7_table if r_["new_best_is_interior"])
h7_verdict = "채택" if n_interior >= 4 else "기각"
print(f"\nH7 판정: {h7_verdict} (내부해 {n_interior}/6)")

results["h7"] = {"table": h7_table, "n_interior_optimum": n_interior, "verdict": h7_verdict}

with open(os.path.join(DOCS_DIR, "final_evaluation_results.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)

# -----------------------------------------------------------------
# 3-4. 그림 3개
# -----------------------------------------------------------------
print("\n그림 생성 중...")

# (1) tradeoff: 승인율 vs 승인군 연체율
fig, ax = plt.subplots(figsize=(8, 6))
grid = np.arange(0.50, 1.0001, 0.01)
champ_curve = [approved_bad_rate(champ_score, target_vals, a)[0] * 100 for a in grid]
new_curve = [approved_bad_rate(new_score, target_vals, a)[0] * 100 for a in grid]
ax.plot(grid * 100, champ_curve, label="현행 기준(외부점수)", color="#4C72B0")
ax.plot(grid * 100, new_curve, label=f"새 점수({final_label})", color="#C44E52")
ax.axhline(base_rate * 100, color="gray", linestyle=":", label=f"전원승인 기저율 {base_rate*100:.2f}%")
for a in approval_rates:
    cr, _ = approved_bad_rate(champ_score, target_vals, a)
    nr, _ = approved_bad_rate(new_score, target_vals, a)
    ax.scatter([a * 100, a * 100], [cr * 100, nr * 100], color=["#4C72B0", "#C44E52"], zorder=5)
    ax.axvline(a * 100, color="lightgray", linestyle="--", linewidth=0.7)
ax.set_xlabel("승인율(%)")
ax.set_ylabel("승인군 연체율(%)")
ax.set_title("현행 기준 vs 새 점수: 승인율-연체율 트레이드오프 (최종평가 세트)")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "tradeoff_champion_vs_challenger.png"), dpi=130)
plt.close()

# (2) 스왑셋 막대그래프
fig, axes = plt.subplots(1, 2, figsize=(11, 5))
names = [r["group"] for r in swap_table]
ns = [r["n"] for r in swap_table]
rates = [r["bad_rate_pct"] for r in swap_table]
axes[0].bar(names, ns, color=["#55A868", "#8172B2", "#C44E52", "#4C72B0"])
axes[0].set_ylabel("인원")
axes[0].set_title("스왑셋 4그룹 인원 (승인율 80%)")
axes[0].tick_params(axis="x", rotation=20)
axes[1].bar(names, rates, color=["#55A868", "#8172B2", "#C44E52", "#4C72B0"])
axes[1].set_ylabel("연체율(%)")
axes[1].set_title("스왑셋 4그룹 연체율 (승인율 80%)")
axes[1].tick_params(axis="x", rotation=20)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "swap_set_80.png"), dpi=130)
plt.close()

# (3) 수익 시나리오
fig, axes = plt.subplots(2, 3, figsize=(16, 9))
idx = 0
for r in r_values:
    for lgd in lgd_values:
        ax = axes.flat[idx]
        champ_profits = profit_curve(champ_score, approval_grid, r, lgd)
        new_profits = profit_curve(new_score, approval_grid, r, lgd)
        full_approval_profit = (r * amt_credit[target_vals == 0].sum() - lgd * amt_credit[target_vals == 1].sum())
        champ_index = champ_profits / full_approval_profit * 100
        new_index = new_profits / full_approval_profit * 100
        ax.plot(approval_grid * 100, new_index, label="새 점수", color="#C44E52")
        ax.plot(approval_grid * 100, champ_index, label="현행", color="#4C72B0", linestyle="--")
        champ_best_i = np.argmax(champ_profits)
        new_best_i = np.argmax(new_profits)
        ax.scatter(approval_grid[champ_best_i] * 100, champ_index[champ_best_i], color="#4C72B0", zorder=5)
        ax.scatter(approval_grid[new_best_i] * 100, new_index[new_best_i], color="#C44E52", zorder=5)
        ax.set_title(f"r={int(r*100)}%, LGD={int(lgd*100)}%")
        ax.set_xlabel("승인율(%)")
        ax.set_ylabel("이익 지수")
        if idx == 0:
            ax.legend(fontsize=8)
        idx += 1
plt.suptitle("수익 시나리오별 이익 지수 곡선 (전원승인=100)")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "profit_scenarios.png"), dpi=130)
plt.close()
print("그림 3개 저장 완료")

# -----------------------------------------------------------------
# 예측 결과 파일 저장 (커밋 안 함)
# -----------------------------------------------------------------
pred_out = holdout[["SK_ID_CURR", "TARGET", "AMT_CREDIT"]].copy()
pred_out["champion_score"] = champ_score
pred_out["new_score"] = new_score
pred_out.to_parquet(os.path.join(PRED_DIR, "test_scores.parquet"), index=False)
print(f"\n예측 결과 저장: {os.path.join(PRED_DIR, 'test_scores.parquet')} ({len(pred_out):,}행)")

print(f"\n완료: {os.path.join(DOCS_DIR, 'final_evaluation_results.json')}")
