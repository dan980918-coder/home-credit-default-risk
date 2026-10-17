"""
05_test_signal_hypotheses.py
Loan Approval Risk Scoring - v2 재분석
3단계: 연체 신호 가설(H1~H5) 검증. 학습 세트(60%)만 사용한다.

산출:
  v2/docs/hypothesis_results.json  (변수별 구간, IV, 연체율, 방향, 배수 등 전체 수치)
  v2/docs/figures/iv_by_hypothesis.png
  v2/docs/figures/core_signals.png

실행: python3 -I v2/scripts/05_test_signal_hypotheses.py
"""
import json
import os
import numpy as np
import pandas as pd
from scipy import stats
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

MAX_BINS = 10
MIN_FRAC = 0.05
MISSING_LABEL = "(결측)"
RARE_CAT_THRESHOLD = 0.01

# -----------------------------------------------------------------
# 1. 데이터 로드: 학습 세트(60%)만 사용
# -----------------------------------------------------------------
features = pd.read_parquet(FEAT_PATH)
train_ids = pd.read_csv(os.path.join(SPLIT_DIR, "train_ids.csv"))
df = train_ids.merge(features, on="SK_ID_CURR", how="left")
assert df["TARGET"].notna().all()
n_train = len(df)
base_rate = df["TARGET"].mean()
print(f"학습 세트: {n_train:,}명, 기저 연체율: {base_rate*100:.3f}%")

# -----------------------------------------------------------------
# 2. 변수 정의: 가설별 핵심/보조, 참고, 부록
# -----------------------------------------------------------------
HYPOTHESES = {
    "H1_상환행동": {
        "core": "late_payment_ratio",
        "aux": ["underpay_ratio", "avg_delay_days", "recent_1yr_late_ratio",
                "bureau_currently_overdue_flag", "bureau_max_overdue_amt",
                "bureau_balance_delinquent_month_ratio", "pos_dpd_month_ratio", "cc_dpd_month_ratio"],
        "direction": "high_risky",  # 값이 클수록 위험
        "description": "과거 상환을 늦게/덜 내거나 다른 곳에서 연체 중인 신청자는 위험이 높다",
    },
    "H2_상환부담": {
        "core": "annuity_to_income",
        "aux": ["credit_to_income", "active_loan_count", "debt_to_income", "card_utilization"],
        "direction": "high_risky",
        "description": "소득 대비 상환 부담이나 다른 곳 빚이 큰 신청자는 위험이 높다",
    },
    "H3_자금압박": {
        "core": "reject_ratio",
        "aux": ["recent_1yr_reject_count", "recent_1yr_apply_count", "total_credit_bureau_inquiries",
                "bureau_recent_1yr_new_loans"],
        "direction": "high_risky",
        "description": "최근 거절당했거나 대출을 자주 알아본 신청자는 위험이 높다",
    },
    "H4_생활안정성": {
        "core": "employment_days",
        "aux": ["registration_days", "id_publish_days", "phone_change_days", "unemployed_flag"],
        "direction": "low_risky",  # 값(기간)이 작을수록 위험. unemployed_flag는 1=위험이므로 아래서 개별 처리
        "description": "재직·거주 기간이 짧은 신청자는 위험이 높다",
    },
    "H5_대출조건": {
        "core": "credit_to_goods",
        "aux": ["credit_to_annuity", "NAME_CONTRACT_TYPE"],
        "direction": "high_risky",
        "description": "물건값보다 많이 빌리거나 상환 기간이 긴 대출은 위험이 높다",
    },
}
# 방향이 예외인 보조 변수 개별 지정 (1=위험인 플래그류)
FLAG_HIGH_RISKY = {"bureau_currently_overdue_flag", "unemployed_flag"}

REFERENCE_VARS = ["EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3", "ext_source_mean", "age_years"]

with open(os.path.join(DOCS_DIR, "feature_build_log.json"), encoding="utf-8") as f:
    build_log = json.load(f)
APPENDIX_VARS = build_log["remainder_appendix_columns"]

NUMERIC_DTYPES = ("int64", "float64", "Int64", "Float64", "int32", "float32")


# -----------------------------------------------------------------
# 3. 구간화 + WOE/IV 엔진
# -----------------------------------------------------------------
def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def bin_numeric(x, y, max_bins=MAX_BINS, min_frac=MIN_FRAC):
    """숫자형 변수를 분위수 구간으로 나누고, 5%/양쪽 클래스 존재 조건을 만족할 때까지
    인접 구간을 병합한다. 결측은 별도 구간으로 분리해 반환한다."""
    valid_mask = x.notna()
    x_valid = x[valid_mask]
    y_valid = y[valid_mask]
    n_valid = len(x_valid)

    n_unique = x_valid.nunique()
    if n_valid == 0 or n_unique <= 1:
        bin_id = pd.Series(0, index=x_valid.index)
        edges_desc = {0: f"{x_valid.min() if n_valid else np.nan}"}
    else:
        if n_unique <= max_bins:
            # 저카디널리티 숫자형(예: 0/1 플래그, 소수의 정수값): qcut이 중복 경계를 드롭하며
            # 서로 다른 값을 한 구간에 합쳐버리는 문제를 피하기 위해 값 자체를 구간으로 사용한다.
            uniq_vals = sorted(x_valid.unique())
            val_to_code = {v: i for i, v in enumerate(uniq_vals)}
            bin_id = x_valid.map(val_to_code)
        else:
            try:
                qcats, edges = pd.qcut(x_valid, q=max_bins, retbins=True, duplicates="drop")
                bin_id = pd.Series(qcats.cat.codes.values, index=x_valid.index)
            except Exception:
                bin_id = pd.Series(0, index=x_valid.index)

        # 반복 병합: 구간 비중<5% 또는 한쪽 클래스가 없는 구간을 이웃과 합친다
        for _ in range(max_bins):
            tmp = pd.DataFrame({"bin": bin_id, "y": y_valid})
            stats_df = tmp.groupby("bin")["y"].agg(["count", "sum"]).rename(columns={"count": "n", "sum": "n_bad"})
            stats_df["n_good"] = stats_df["n"] - stats_df["n_bad"]
            stats_df["frac"] = stats_df["n"] / n_valid
            stats_df = stats_df.sort_index()
            bins_sorted = list(stats_df.index)
            if len(bins_sorted) <= 1:
                break
            violating = stats_df[(stats_df["frac"] < min_frac) | (stats_df["n_bad"] == 0) | (stats_df["n_good"] == 0)]
            if violating.empty:
                break
            target_bin = violating.index[0]
            pos = bins_sorted.index(target_bin)
            if pos == len(bins_sorted) - 1:
                neighbor = bins_sorted[pos - 1]
            else:
                neighbor = bins_sorted[pos + 1]
            bin_id = bin_id.replace(target_bin, neighbor)

        # 연속된 정수로 재라벨링(순서 보존)
        uniq_sorted = sorted(bin_id.unique())
        relabel = {old: new for new, old in enumerate(uniq_sorted)}
        bin_id = bin_id.map(relabel)

        # 구간별 값 범위 라벨 생성
        edges_desc = {}
        for b in sorted(bin_id.unique()):
            vals = x_valid[bin_id == b]
            edges_desc[b] = f"[{vals.min():.4g}, {vals.max():.4g}]"

    full_bin = pd.Series(index=x.index, dtype="object")
    full_bin.loc[valid_mask] = bin_id.map(lambda b: f"bin{b}")
    full_bin.loc[~valid_mask] = MISSING_LABEL

    order_map = {f"bin{b}": b for b in edges_desc.keys()}
    labels_desc = {f"bin{b}": desc for b, desc in edges_desc.items()}
    return full_bin, order_map, labels_desc


def bin_categorical(x, rare_threshold=RARE_CAT_THRESHOLD):
    valid_mask = x.notna()
    x_valid = x[valid_mask]
    n_valid = len(x_valid)
    full_bin = pd.Series(index=x.index, dtype="object")
    if n_valid > 0:
        freq = x_valid.value_counts(normalize=True)
        rare = set(freq[freq < rare_threshold].index)
        mapped = x_valid.apply(lambda v: "기타" if v in rare else v)
        full_bin.loc[valid_mask] = mapped
    full_bin.loc[~valid_mask] = MISSING_LABEL
    order_map = None  # 범주형은 자연 순서 없음
    labels_desc = {c: c for c in full_bin.dropna().unique()}
    return full_bin, order_map, labels_desc


def compute_iv_table(bin_series, y, order_map=None):
    df_local = pd.DataFrame({"bin": bin_series, "y": y})
    g = df_local.groupby("bin")["y"].agg(["count", "sum"]).rename(columns={"count": "n", "sum": "n_bad"})
    g["n_good"] = g["n"] - g["n_bad"]
    total_bad = g["n_bad"].sum()
    total_good = g["n_good"].sum()
    k = len(g)
    # WOE/IV: 0 방지를 위해 각 칸(구간의 good/bad 카운트)에 0.5를 더한다
    g["good_dist"] = (g["n_good"] + 0.5) / (total_good + 0.5 * k)
    g["bad_dist"] = (g["n_bad"] + 0.5) / (total_bad + 0.5 * k)
    g["woe"] = np.log(g["good_dist"] / g["bad_dist"])
    g["iv_contrib"] = (g["good_dist"] - g["bad_dist"]) * g["woe"]
    iv_total = g["iv_contrib"].sum()

    g["bad_rate"] = g["n_bad"] / g["n"]
    cis = g.apply(lambda r: wilson_ci(r["n_bad"], r["n"]), axis=1)
    g["ci_low"] = cis.apply(lambda t: t[0])
    g["ci_high"] = cis.apply(lambda t: t[1])

    if order_map is not None:
        g["order"] = g.index.map(lambda b: order_map.get(b, np.nan))
    else:
        g["order"] = np.nan

    return g.reset_index()


def iv_strength(iv):
    if iv < 0.02:
        return "없음"
    elif iv < 0.1:
        return "약함"
    elif iv < 0.3:
        return "중간"
    else:
        return "강함"


def direction_check(g, direction, flag_style=False):
    """결측 구간을 뺀 구간 순서와 연체율의 Spearman 상관, 위험/안전 끝 구간을 계산한다."""
    g_ord = g[g["bin"] != MISSING_LABEL].copy()
    if g_ord["order"].notna().any():
        g_ord = g_ord.sort_values("order")
        if len(g_ord) >= 2:
            rho, pval = stats.spearmanr(g_ord["order"], g_ord["bad_rate"])
        else:
            rho, pval = np.nan, np.nan
        if flag_style:
            # 플래그(0/1)형: order 0=안전측(0), 1=위험측(1)으로 간주
            risky_row = g_ord[g_ord["order"] == g_ord["order"].max()]
            safe_row = g_ord[g_ord["order"] == g_ord["order"].min()]
        elif direction == "high_risky":
            risky_row = g_ord[g_ord["order"] == g_ord["order"].max()]
            safe_row = g_ord[g_ord["order"] == g_ord["order"].min()]
        else:  # low_risky
            risky_row = g_ord[g_ord["order"] == g_ord["order"].min()]
            safe_row = g_ord[g_ord["order"] == g_ord["order"].max()]
    else:
        # 범주형(순서 없음): Spearman 생략, risky/safe는 연체율 최댓값/최솟값으로 대체 서술용
        rho, pval = np.nan, np.nan
        risky_row = g_ord.loc[[g_ord["bad_rate"].idxmax()]] if len(g_ord) else g_ord
        safe_row = g_ord.loc[[g_ord["bad_rate"].idxmin()]] if len(g_ord) else g_ord

    if len(risky_row) == 0 or len(safe_row) == 0:
        return {
            "spearman_rho": rho, "spearman_p": pval,
            "risky_bin": None, "safe_bin": None,
        }

    r = risky_row.iloc[0]
    s = safe_row.iloc[0]
    p1, n1 = r["bad_rate"], r["n"]
    p2, n2 = s["bad_rate"], s["n"]

    if p1 > 0 and p2 > 0 and n1 > 0 and n2 > 0:
        log_rr = np.log(p1 / p2)
        se = np.sqrt((1 - p1) / (p1 * n1) + (1 - p2) / (p2 * n2))
        rr = np.exp(log_rr)
        rr_low = np.exp(log_rr - 1.96 * se)
        rr_high = np.exp(log_rr + 1.96 * se)
    else:
        rr, rr_low, rr_high = np.nan, np.nan, np.nan

    return {
        "spearman_rho": None if pd.isna(rho) else round(float(rho), 4),
        "spearman_p": None if pd.isna(pval) else round(float(pval), 6),
        "risky_bin": {"bin": r["bin"], "n": int(r["n"]), "bad_rate_pct": round(p1 * 100, 3),
                      "ci_low_pct": round(r["ci_low"] * 100, 3), "ci_high_pct": round(r["ci_high"] * 100, 3)},
        "safe_bin": {"bin": s["bin"], "n": int(n2), "bad_rate_pct": round(p2 * 100, 3),
                     "ci_low_pct": round(s["ci_low"] * 100, 3), "ci_high_pct": round(s["ci_high"] * 100, 3)},
        "multiplier": None if pd.isna(rr) else round(float(rr), 3),
        "multiplier_ci_low": None if pd.isna(rr_low) else round(float(rr_low), 3),
        "multiplier_ci_high": None if pd.isna(rr_high) else round(float(rr_high), 3),
    }


def analyze_variable(df, col, direction=None, flag_style=False):
    x = df[col]
    y = df["TARGET"]
    if str(x.dtype) in NUMERIC_DTYPES or pd.api.types.is_numeric_dtype(x):
        bin_series, order_map, labels_desc = bin_numeric(x, y)
    else:
        bin_series, order_map, labels_desc = bin_categorical(x)

    g = compute_iv_table(bin_series, y, order_map)
    iv_total = round(float(g["iv_contrib"].sum()), 5)
    strength = iv_strength(iv_total)

    result = {
        "variable": col,
        "dtype": "numeric" if order_map is not None else "categorical",
        "n_valid": int((~x.isna()).sum()),
        "missing_pct": round(float(x.isna().mean() * 100), 3),
        "iv": iv_total,
        "iv_strength": strength,
        "bins": [],
    }
    for _, row in g.sort_values("order" if order_map is not None else "bad_rate", na_position="last").iterrows():
        label = labels_desc.get(row["bin"], row["bin"]) if row["bin"] != MISSING_LABEL else MISSING_LABEL
        result["bins"].append({
            "bin": row["bin"], "range": label,
            "n": int(row["n"]), "n_bad": int(row["n_bad"]), "n_good": int(row["n_good"]),
            "pct_of_total": round(row["n"] / len(df) * 100, 2),
            "bad_rate_pct": round(row["bad_rate"] * 100, 3),
            "ci_low_pct": round(row["ci_low"] * 100, 3), "ci_high_pct": round(row["ci_high"] * 100, 3),
            "woe": round(row["woe"], 4), "iv_contrib": round(row["iv_contrib"], 5),
        })

    if direction is not None:
        result["direction_check"] = direction_check(g, direction, flag_style=flag_style)
    return result


# -----------------------------------------------------------------
# 4. 가설별 변수 분석 실행
# -----------------------------------------------------------------
all_results = {"base_rate_pct": round(base_rate * 100, 3), "n_train": n_train, "hypotheses": {}}

for h_name, h in HYPOTHESES.items():
    print(f"\n=== {h_name}: {h['description']} ===")
    core_col = h["core"]
    direction = h["direction"]
    core_result = analyze_variable(df, core_col, direction=direction, flag_style=(core_col in FLAG_HIGH_RISKY))
    print(f"  [핵심] {core_col}: IV={core_result['iv']} ({core_result['iv_strength']})")

    aux_results = []
    for aux_col in h["aux"]:
        flag_style = aux_col in FLAG_HIGH_RISKY
        aux_dir = "high_risky" if flag_style else direction
        ar = analyze_variable(df, aux_col, direction=aux_dir, flag_style=flag_style)
        aux_results.append(ar)
        print(f"  [보조] {aux_col}: IV={ar['iv']} ({ar['iv_strength']})")

    # 판정 로직 (사전 고정 기준, 변경 금지)
    dc = core_result.get("direction_check", {})
    iv_ok = core_result["iv"] >= 0.02
    spearman_sign_ok = False
    if dc.get("spearman_rho") is not None:
        expected_sign = 1 if (direction == "high_risky") else -1
        spearman_sign_ok = np.sign(dc["spearman_rho"]) == expected_sign or dc["spearman_rho"] == 0
    risky_gt_safe = False
    ci_low_gt1 = False
    if dc.get("risky_bin") and dc.get("safe_bin"):
        risky_gt_safe = dc["risky_bin"]["bad_rate_pct"] > dc["safe_bin"]["bad_rate_pct"]
        ci_low_gt1 = (dc.get("multiplier_ci_low") is not None) and (dc["multiplier_ci_low"] > 1)

    direction_ok = spearman_sign_ok and risky_gt_safe and ci_low_gt1
    verdict = "채택" if (iv_ok and direction_ok) else "기각"

    all_results["hypotheses"][h_name] = {
        "description": h["description"],
        "direction_expected": direction,
        "core_variable": core_result,
        "aux_variables": aux_results,
        "verdict": verdict,
        "verdict_criteria": {
            "iv_ge_0.02": iv_ok,
            "spearman_sign_matches": spearman_sign_ok,
            "risky_end_gt_safe_end": risky_gt_safe,
            "multiplier_ci_low_gt_1": ci_low_gt1,
        },
    }
    print(f"  => 판정: {verdict} (IV조건={iv_ok}, 방향부호={spearman_sign_ok}, 위험>안전={risky_gt_safe}, 배수CI하한>1={ci_low_gt1})")

# -----------------------------------------------------------------
# 5. 참고 변수 (EXT_SOURCE, 나이) - IV만
# -----------------------------------------------------------------
print("\n=== 참고 변수 ===")
reference_results = []
for col in REFERENCE_VARS:
    r = analyze_variable(df, col, direction=None)
    reference_results.append(r)
    print(f"  {col}: IV={r['iv']} ({r['iv_strength']})")
all_results["reference_variables"] = reference_results

# -----------------------------------------------------------------
# 6. 부록: 나머지 application 컬럼 IV
# -----------------------------------------------------------------
print(f"\n=== 부록 변수 IV 계산 ({len(APPENDIX_VARS)}개) ===")
appendix_results = []
for col in APPENDIX_VARS:
    try:
        r = analyze_variable(df, col, direction=None)
        appendix_results.append({"variable": col, "dtype": r["dtype"], "iv": r["iv"], "iv_strength": r["iv_strength"],
                                  "missing_pct": r["missing_pct"]})
    except Exception as e:
        appendix_results.append({"variable": col, "error": str(e)})
appendix_results_sorted = sorted(appendix_results, key=lambda r: r.get("iv", -1), reverse=True)
all_results["appendix_variables"] = appendix_results_sorted
print(f"부록 상위 5: {[(r['variable'], r.get('iv')) for r in appendix_results_sorted[:5]]}")

# -----------------------------------------------------------------
# 7. 이력 없는 신청자 추가 확인
# -----------------------------------------------------------------
no_hist = df[df["no_history_at_all_flag"] == 1]
has_hist = df[df["no_history_at_all_flag"] == 0]
n_nh, bad_nh = len(no_hist), no_hist["TARGET"].sum()
n_h, bad_h = len(has_hist), has_hist["TARGET"].sum()
ci_nh = wilson_ci(bad_nh, n_nh)
ci_h = wilson_ci(bad_h, n_h)
all_results["no_history_comparison"] = {
    "no_history": {"n": int(n_nh), "n_bad": int(bad_nh), "bad_rate_pct": round(bad_nh / n_nh * 100, 3),
                   "ci_low_pct": round(ci_nh[0] * 100, 3), "ci_high_pct": round(ci_nh[1] * 100, 3)},
    "has_history": {"n": int(n_h), "n_bad": int(bad_h), "bad_rate_pct": round(bad_h / n_h * 100, 3),
                    "ci_low_pct": round(ci_h[0] * 100, 3), "ci_high_pct": round(ci_h[1] * 100, 3)},
}
print(f"\n이력 없음: n={n_nh}, 연체율={bad_nh/n_nh*100:.3f}% / 이력 있음: n={n_h}, 연체율={bad_h/n_h*100:.3f}%")

# -----------------------------------------------------------------
# 8. 보조 변수 중 눈에 띄는 것: IV 상위 5개, 가설 방향과 반대인 변수
# -----------------------------------------------------------------
aux_flat = []
for h_name, h_res in all_results["hypotheses"].items():
    for ar in h_res["aux_variables"]:
        dc = ar.get("direction_check", {})
        expected_sign = 1 if (h_res["direction_expected"] == "high_risky") else -1
        if ar["variable"] in FLAG_HIGH_RISKY:
            expected_sign = 1
        actual_sign = np.sign(dc["spearman_rho"]) if dc.get("spearman_rho") is not None else None
        opposed = (actual_sign is not None) and (actual_sign != 0) and (actual_sign != expected_sign)
        aux_flat.append({
            "hypothesis": h_name, "variable": ar["variable"], "iv": ar["iv"], "iv_strength": ar["iv_strength"],
            "spearman_rho": dc.get("spearman_rho"), "opposed_direction": bool(opposed),
        })
aux_flat_sorted = sorted(aux_flat, key=lambda r: r["iv"], reverse=True)
all_results["aux_variable_summary"] = {
    "top5_by_iv": aux_flat_sorted[:5],
    "opposed_direction": [r for r in aux_flat_sorted if r["opposed_direction"]],
}
print("\n보조 변수 IV 상위 5:", [(r["variable"], r["iv"]) for r in aux_flat_sorted[:5]])
print("방향 반대 보조 변수:", [r["variable"] for r in aux_flat_sorted if r["opposed_direction"]])

# -----------------------------------------------------------------
# 저장
# -----------------------------------------------------------------
with open(os.path.join(DOCS_DIR, "hypothesis_results.json"), "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
print(f"\n결과 저장: {os.path.join(DOCS_DIR, 'hypothesis_results.json')}")

# -----------------------------------------------------------------
# 9. 그림 1: 가설별 IV 막대그래프
# -----------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 7))
y_pos = 0
yticks, ylabels, bars_x, bars_color = [], [], [], []
colors_core = "#C44E52"
colors_aux = "#8C8C8C"

for h_name, h_res in all_results["hypotheses"].items():
    core = h_res["core_variable"]
    yticks.append(y_pos); ylabels.append(f"★{core['variable']} ({h_name})"); bars_x.append(core["iv"]); bars_color.append(colors_core)
    y_pos += 1
    for ar in h_res["aux_variables"]:
        yticks.append(y_pos); ylabels.append(f"  {ar['variable']}"); bars_x.append(ar["iv"]); bars_color.append(colors_aux)
        y_pos += 1
    y_pos += 0.5

ax.barh(yticks, bars_x, color=bars_color, height=0.7)
ax.set_yticks(yticks); ax.set_yticklabels(ylabels, fontsize=8)
ax.invert_yaxis()
for thresh, label in [(0.02, "0.02(약함)"), (0.1, "0.1(중간)"), (0.3, "0.3(강함)")]:
    ax.axvline(thresh, color="gray", linestyle="--", linewidth=0.8)
    ax.text(thresh, -1.5, label, fontsize=7, ha="center", color="gray")
ax.set_xlabel("IV (Information Value)")
ax.set_title("가설별 변수 IV (★=핵심 변수, 회색=보조 변수)")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "iv_by_hypothesis.png"), dpi=130)
plt.close()
print("그림 저장: iv_by_hypothesis.png")

# -----------------------------------------------------------------
# 10. 그림 2: 핵심 변수 5개의 구간별 연체율
# -----------------------------------------------------------------
fig, axes = plt.subplots(5, 1, figsize=(9, 18))
for ax, (h_name, h_res) in zip(axes, all_results["hypotheses"].items()):
    core = h_res["core_variable"]
    bins = core["bins"]
    labels = [b["range"] for b in bins]
    rates = [b["bad_rate_pct"] for b in bins]
    errs_low = [b["bad_rate_pct"] - b["ci_low_pct"] for b in bins]
    errs_high = [b["ci_high_pct"] - b["bad_rate_pct"] for b in bins]
    x = np.arange(len(bins))
    ax.bar(x, rates, yerr=[errs_low, errs_high], capsize=3, color="#4C72B0")
    ax.axhline(all_results["base_rate_pct"], color="red", linestyle="--", linewidth=1, label=f"기저 연체율 {all_results['base_rate_pct']}%")
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=7)
    ax.set_ylabel("연체율(%)")
    ax.set_title(f"{h_name} 핵심변수: {core['variable']} (IV={core['iv']}, {core['iv_strength']})", fontsize=10)
    ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "core_signals.png"), dpi=130)
plt.close()
print("그림 저장: core_signals.png")

print("\n완료")
