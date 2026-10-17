"""
07_models.py
Loan Approval Risk Scoring - v2 재분석
4단계 2절: 모델링. 학습 세트로 학습하고 검증 세트로 모델·설정을 선택한다.
최종평가(holdout) 세트는 이 스크립트에서 전혀 읽지 않는다.

산출:
  v2/docs/modeling_results.json   (변수선택/모델별 성능/계수/점수표/SHAP 전체 수치)
  v2/docs/06_scorecard_points.md 작성에 필요한 점수표 데이터
  v2/data/models/ (lightgbm 모델, 스코어카드 파라미터 - 커밋 안 함, 08번 스크립트가 재사용)

실행: python3 -I v2/scripts/07_models.py
"""
import json
import os
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
import lightgbm as lgb
import shap

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FEAT_PATH = os.path.join(ROOT, "v2", "data", "features", "hypothesis_features.parquet")
SPLIT_DIR = os.path.join(ROOT, "v2", "data", "splits")
DOCS_DIR = os.path.join(ROOT, "v2", "docs")
MODEL_DIR = os.path.join(ROOT, "v2", "data", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

SEED = 42
MAX_BINS = 10
MIN_FRAC = 0.05
MISSING_LABEL = "(결측)"
RARE_CAT_THRESHOLD = 0.01

# -----------------------------------------------------------------
# 0. 데이터 로드 — 학습/검증 세트만. holdout_ids.csv는 이 스크립트에서 전혀 읽지 않는다.
# -----------------------------------------------------------------
features = pd.read_parquet(FEAT_PATH)
train_ids = pd.read_csv(os.path.join(SPLIT_DIR, "train_ids.csv"))
valid_ids = pd.read_csv(os.path.join(SPLIT_DIR, "valid_ids.csv"))

train = train_ids.merge(features, on="SK_ID_CURR", how="left")
valid = valid_ids.merge(features, on="SK_ID_CURR", how="left")
print(f"학습 {len(train):,}명 / 검증 {len(valid):,}명")

EXCLUDE_ALWAYS = ["CODE_GENDER", "OBS_30_CNT_SOCIAL_CIRCLE", "DEF_30_CNT_SOCIAL_CIRCLE",
                   "OBS_60_CNT_SOCIAL_CIRCLE", "DEF_60_CNT_SOCIAL_CIRCLE"]
for d in (train, valid):
    for c in EXCLUDE_ALWAYS:
        assert c not in d.columns or d[c].isna().all(), f"제외 변수 {c}가 특징 테이블에 남아있음"

# EXT_SOURCE 결측 플래그 생성
for d in (train, valid):
    for c in ["EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3"]:
        d[f"{c}_MISSING"] = d[c].isna().astype(int)

with open(os.path.join(DOCS_DIR, "feature_build_log.json"), encoding="utf-8") as f:
    build_log = json.load(f)
APPENDIX_VARS = build_log["remainder_appendix_columns"]

# -----------------------------------------------------------------
# 1. 변수 세트 정의
# -----------------------------------------------------------------
HYPOTHESIS_VARS = [
    "late_payment_ratio", "underpay_ratio", "avg_delay_days", "recent_1yr_late_ratio",
    "bureau_currently_overdue_flag", "bureau_max_overdue_amt", "bureau_balance_delinquent_month_ratio",
    "pos_dpd_month_ratio", "cc_dpd_month_ratio",
    "annuity_to_income", "credit_to_income", "active_loan_count", "debt_to_income", "card_utilization",
    "reject_ratio", "recent_1yr_reject_count", "recent_1yr_apply_count", "total_credit_bureau_inquiries",
    "bureau_recent_1yr_new_loans",
    "employment_days", "registration_days", "id_publish_days", "phone_change_days", "unemployed_flag",
    "credit_to_goods", "credit_to_annuity", "NAME_CONTRACT_TYPE",
]
EXT_SOURCE_VARS = ["EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3",
                    "EXT_SOURCE_1_MISSING", "EXT_SOURCE_2_MISSING", "EXT_SOURCE_3_MISSING"]
LOAN_TERM_VARS = ["AMT_CREDIT", "AMT_ANNUITY", "AMT_GOODS_PRICE"]  # NAME_CONTRACT_TYPE은 H5 보조에 이미 포함

BASE_SET_NO_AGE = sorted(set(HYPOTHESIS_VARS + EXT_SOURCE_VARS + LOAN_TERM_VARS))
BASE_SET_WITH_AGE = sorted(set(BASE_SET_NO_AGE + ["age_years"]))
REFERENCE_FULL_SET = sorted(set(BASE_SET_WITH_AGE + APPENDIX_VARS))

print(f"기본 세트(나이 제외): {len(BASE_SET_NO_AGE)}개")
print(f"기본 세트(나이 포함): {len(BASE_SET_WITH_AGE)}개")
print(f"참고용 전체 세트: {len(REFERENCE_FULL_SET)}개")

CATEGORICAL_VARS = set(["NAME_CONTRACT_TYPE"]) | {c for c in APPENDIX_VARS if train[c].dtype == object}
NUMERIC_VARS_IN_REF = [c for c in REFERENCE_FULL_SET if c not in CATEGORICAL_VARS]


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def ks_statistic(y_true, y_score):
    df_ = pd.DataFrame({"y": y_true, "s": y_score}).sort_values("s")
    n_bad = df_["y"].sum()
    n_good = len(df_) - n_bad
    cum_bad = (df_["y"].cumsum()) / n_bad
    cum_good = ((1 - df_["y"]).cumsum()) / n_good
    return float((cum_bad - cum_good).abs().max())


# -----------------------------------------------------------------
# 2. 3단계 IV 엔진 재사용 (binning 로직 동일 알고리즘 재구현)
# -----------------------------------------------------------------
def bin_numeric_fit(x, y, max_bins=MAX_BINS, min_frac=MIN_FRAC):
    """학습 세트로 구간 경계를 "학습"한다. qcut 분위수 + 5%/양쪽클래스 병합 규칙은
    05_test_signal_hypotheses.py의 bin_numeric()과 동일 알고리즘이다."""
    valid_mask = x.notna()
    x_valid = x[valid_mask]
    y_valid = y[valid_mask]
    n_valid = len(x_valid)

    n_unique = x_valid.nunique()
    if n_valid == 0 or n_unique <= 1:
        bin_id = pd.Series(0, index=x_valid.index)
    elif n_unique <= max_bins:
        uniq_vals = sorted(x_valid.unique())
        val_to_code = {v: i for i, v in enumerate(uniq_vals)}
        bin_id = x_valid.map(val_to_code)
    else:
        qcats, edges = pd.qcut(x_valid, q=max_bins, retbins=True, duplicates="drop")
        bin_id = pd.Series(qcats.cat.codes.values, index=x_valid.index)

    if n_valid > 0 and n_unique > 1:
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
            neighbor = bins_sorted[pos - 1] if pos == len(bins_sorted) - 1 else bins_sorted[pos + 1]
            bin_id = bin_id.replace(target_bin, neighbor)
        uniq_sorted = sorted(bin_id.unique())
        relabel = {old: new for new, old in enumerate(uniq_sorted)}
        bin_id = bin_id.map(relabel)

    # 구간 경계(최댓값 기준 오름차순) 저장 — transform 시 이 경계로 신규 데이터를 분류
    edges_list = []
    for b in sorted(bin_id.unique()):
        vals = x_valid[bin_id == b]
        edges_list.append((b, float(vals.min()), float(vals.max())))

    return {"type": "numeric", "edges": edges_list}


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
    # 경계보다 작은 값(학습 세트 최솟값 미만)은 첫 구간에, 큰 값은 마지막 구간에 귀속
    if edges:
        first_b, first_lo, _ = edges[0]
        last_b, _, last_hi = edges[-1]
        out.loc[valid_mask & (x < first_lo)] = f"bin{first_b}"
        out.loc[valid_mask & (x > last_hi)] = f"bin{last_b}"
    return out


def bin_categorical_fit(x, rare_threshold=RARE_CAT_THRESHOLD):
    valid_mask = x.notna()
    x_valid = x[valid_mask].astype(str)
    if len(x_valid) == 0:
        return {"type": "categorical", "keep": set()}
    freq = x_valid.value_counts(normalize=True)
    keep = set(freq[freq >= rare_threshold].index)
    return {"type": "categorical", "keep": keep}


def bin_categorical_transform(x, fit_info):
    keep = fit_info["keep"]
    valid_mask = x.notna()
    out = pd.Series(MISSING_LABEL, index=x.index, dtype="object")
    mapped = x[valid_mask].astype(str).apply(lambda v: v if v in keep else "기타")
    out.loc[valid_mask] = mapped
    return out


def fit_bins(x, y, is_categorical):
    if is_categorical:
        return bin_categorical_fit(x)
    return bin_numeric_fit(x, y)


def transform_bins(x, fit_info):
    if fit_info["type"] == "categorical":
        return bin_categorical_transform(x, fit_info)
    return bin_numeric_transform(x, fit_info)


def compute_woe_map(bin_series, y):
    df_local = pd.DataFrame({"bin": bin_series, "y": y})
    g = df_local.groupby("bin")["y"].agg(["count", "sum"]).rename(columns={"count": "n", "sum": "n_bad"})
    g["n_good"] = g["n"] - g["n_bad"]
    total_bad, total_good, k = g["n_bad"].sum(), g["n_good"].sum(), len(g)
    g["good_dist"] = (g["n_good"] + 0.5) / (total_good + 0.5 * k)
    g["bad_dist"] = (g["n_bad"] + 0.5) / (total_bad + 0.5 * k)
    g["woe"] = np.log(g["good_dist"] / g["bad_dist"])
    g["bad_rate"] = g["n_bad"] / g["n"]
    g["iv_contrib"] = (g["good_dist"] - g["bad_dist"]) * g["woe"]
    return g


print("\n=== 2. 변수별 구간화(학습세트 기준) + WOE 변환 ===")
bin_fits = {}
woe_tables = {}
ivs = {}
for col in BASE_SET_WITH_AGE:
    is_cat = col in CATEGORICAL_VARS
    fit_info = fit_bins(train[col], train["TARGET"], is_cat)
    bin_fits[col] = fit_info
    bins_train = transform_bins(train[col], fit_info)
    woe_table = compute_woe_map(bins_train, train["TARGET"])
    woe_tables[col] = woe_table
    ivs[col] = round(float(woe_table["iv_contrib"].sum()), 5)

iv_summary = pd.Series(ivs).sort_values(ascending=False)
print(iv_summary.to_string())

# -----------------------------------------------------------------
# 3. 변수 선택: IV>=0.02, WOE 상관 |r|>0.7인 쌍은 IV 높은 쪽만
# -----------------------------------------------------------------
print("\n=== 3. 변수 선택 ===")
iv_pass = [c for c in BASE_SET_WITH_AGE if ivs[c] >= 0.02]
print(f"IV>=0.02 통과: {len(iv_pass)}/{len(BASE_SET_WITH_AGE)}개")
removed_by_iv = [c for c in BASE_SET_WITH_AGE if c not in iv_pass]

# WOE 변환된 값으로 상관행렬 계산 (학습 세트)
woe_train_df = pd.DataFrame({c: transform_bins(train[c], bin_fits[c]).map(
    woe_tables[c]["woe"].to_dict()) for c in iv_pass})
corr = woe_train_df.corr().abs()

removed_by_corr = []
cols_remaining = list(iv_pass)
changed = True
while changed:
    changed = False
    corr_sub = woe_train_df[cols_remaining].corr().abs()
    np.fill_diagonal(corr_sub.values, 0)
    max_corr = corr_sub.values.max() if corr_sub.size else 0
    if max_corr > 0.7:
        i, j = np.unravel_index(np.argmax(corr_sub.values), corr_sub.shape)
        c1, c2 = corr_sub.index[i], corr_sub.columns[j]
        drop_col = c1 if ivs[c1] < ivs[c2] else c2
        cols_remaining.remove(drop_col)
        removed_by_corr.append({"dropped": drop_col, "kept": c2 if drop_col == c1 else c1,
                                 "corr": round(float(max_corr), 3),
                                 "dropped_iv": ivs[drop_col], "kept_iv": ivs[c2 if drop_col == c1 else c1]})
        changed = True

final_vars_no_age = [c for c in cols_remaining if c != "age_years"]
final_vars_with_age = list(cols_remaining)
print(f"상관 필터 후 최종(나이 포함): {len(final_vars_with_age)}개, 제거된 쌍: {len(removed_by_corr)}")
print("제거된 변수(상관):", [r["dropped"] for r in removed_by_corr])

variable_selection_log = {
    "base_set_no_age_n": len(BASE_SET_NO_AGE),
    "base_set_with_age_n": len(BASE_SET_WITH_AGE),
    "iv_all": ivs,
    "removed_by_iv_lt_0.02": removed_by_iv,
    "n_after_iv_filter": len(iv_pass),
    "removed_by_correlation": removed_by_corr,
    "final_vars_with_age": final_vars_with_age,
    "final_vars_no_age": final_vars_no_age,
    "n_final_with_age": len(final_vars_with_age),
    "n_final_no_age": len(final_vars_no_age),
}

# -----------------------------------------------------------------
# 4. Champion: EXT_SOURCE_1/2/3 + 결측플래그, 중앙값 대체, 로지스틱회귀
# -----------------------------------------------------------------
print("\n=== 4. Champion(외부점수 대용 기준) ===")
champ_cols = EXT_SOURCE_VARS
champ_train_X = train[champ_cols].copy()
champ_valid_X = valid[champ_cols].copy()
medians = {}
for c in ["EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3"]:
    med = train[c].median()
    medians[c] = float(med)
    champ_train_X[c] = champ_train_X[c].fillna(med)
    champ_valid_X[c] = champ_valid_X[c].fillna(med)

champ_model = LogisticRegression(max_iter=1000, random_state=SEED)
champ_model.fit(champ_train_X, train["TARGET"])
champ_valid_score = champ_model.predict_proba(champ_valid_X)[:, 1]
champ_auc = roc_auc_score(valid["TARGET"], champ_valid_score)
champ_ks = ks_statistic(valid["TARGET"].values, champ_valid_score)
champ_gini = 2 * champ_auc - 1
print(f"Champion 검증 AUC={champ_auc:.4f}, KS={champ_ks:.4f}, Gini={champ_gini:.4f}")


def build_scorecard(var_list, label):
    """지정된 변수 목록으로 WOE 스코어카드(로지스틱회귀)를 학습하고 C를 검증세트 AUC로 선택한다."""
    X_train = pd.DataFrame({c: transform_bins(train[c], bin_fits[c]).map(woe_tables[c]["woe"].to_dict())
                             for c in var_list})
    X_valid = pd.DataFrame({c: transform_bins(valid[c], bin_fits[c]).map(woe_tables[c]["woe"].to_dict())
                             for c in var_list})
    # transform에서 학습세트에 없던 범주가 나오면 NaN -> 0(중립 WOE)으로 대체
    X_train = X_train.fillna(0.0)
    X_valid = X_valid.fillna(0.0)

    best = None
    grid_results = []
    for C in [0.01, 0.1, 1]:
        m = LogisticRegression(penalty="l2", C=C, max_iter=1000, random_state=SEED)
        m.fit(X_train, train["TARGET"])
        vs = m.predict_proba(X_valid)[:, 1]
        auc = roc_auc_score(valid["TARGET"], vs)
        grid_results.append({"C": C, "valid_auc": round(float(auc), 5)})
        if best is None or auc > best["auc"]:
            best = {"C": C, "model": m, "auc": auc}
    vs = best["model"].predict_proba(X_valid)[:, 1]
    ks = ks_statistic(valid["TARGET"].values, vs)
    gini = 2 * best["auc"] - 1
    print(f"[{label}] best C={best['C']}, 검증 AUC={best['auc']:.4f}, KS={ks:.4f}, Gini={gini:.4f}")
    return {
        "label": label, "var_list": var_list, "grid_results": grid_results,
        "best_C": best["C"], "model": best["model"], "valid_auc": float(best["auc"]),
        "valid_ks": ks, "valid_gini": gini,
    }


print("\n=== 5. 스코어카드(로지스틱회귀) 학습 ===")
scorecard_with_age = build_scorecard(final_vars_with_age, "scorecard_with_age")
scorecard_no_age = build_scorecard(final_vars_no_age, "scorecard_no_age")

# -----------------------------------------------------------------
# 6. LightGBM (원값 사용, 검증세트로 early stopping + 소규모 그리드)
# -----------------------------------------------------------------
print("\n=== 6. LightGBM 튜닝 ===")


def build_lightgbm(var_list, label, categorical_vars=None):
    categorical_vars = categorical_vars or []
    X_train = train[var_list].copy()
    X_valid = valid[var_list].copy()
    for c in categorical_vars:
        X_train[c] = X_train[c].astype("category")
        X_valid[c] = pd.Categorical(X_valid[c], categories=X_train[c].cat.categories)

    grid = []
    best = None
    for num_leaves in [15, 31, 63]:
        for lr in [0.03, 0.05]:
            for min_child in [50, 200]:
                model = lgb.LGBMClassifier(
                    num_leaves=num_leaves, learning_rate=lr, min_child_samples=min_child,
                    n_estimators=2000, random_state=SEED, verbosity=-1,
                )
                model.fit(
                    X_train, train["TARGET"],
                    eval_set=[(X_valid, valid["TARGET"])],
                    eval_metric="auc",
                    categorical_feature=categorical_vars if categorical_vars else "auto",
                    callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)],
                )
                vs = model.predict_proba(X_valid)[:, 1]
                auc = roc_auc_score(valid["TARGET"], vs)
                grid.append({"num_leaves": num_leaves, "learning_rate": lr, "min_child_samples": min_child,
                             "best_iteration": model.best_iteration_, "valid_auc": round(float(auc), 5)})
                if best is None or auc > best["auc"]:
                    best = {"params": grid[-1], "model": model, "auc": auc}
    vs = best["model"].predict_proba(X_valid)[:, 1]
    ks = ks_statistic(valid["TARGET"].values, vs)
    gini = 2 * best["auc"] - 1
    print(f"[{label}] best params={best['params']}, 검증 AUC={best['auc']:.4f}, KS={ks:.4f}, Gini={gini:.4f}")
    return {
        "label": label, "var_list": var_list, "grid_results": grid,
        "best_params": best["params"], "model": best["model"], "valid_auc": float(best["auc"]),
        "valid_ks": ks, "valid_gini": gini,
    }


lgbm_cat_vars = [c for c in final_vars_with_age if c in CATEGORICAL_VARS]
lgbm_with_age = build_lightgbm(final_vars_with_age, "lightgbm_with_age", categorical_vars=lgbm_cat_vars)
lgbm_cat_vars_no_age = [c for c in final_vars_no_age if c in CATEGORICAL_VARS]
lgbm_no_age = build_lightgbm(final_vars_no_age, "lightgbm_no_age", categorical_vars=lgbm_cat_vars_no_age)

# -----------------------------------------------------------------
# 7. 참고용 전체 세트: LightGBM 1회만 (검증 AUC만 기록)
# -----------------------------------------------------------------
print("\n=== 7. 참고용 전체 세트 (LightGBM 1회) ===")
ref_cat_vars = [c for c in REFERENCE_FULL_SET if c in CATEGORICAL_VARS]
# 범주형 변수의 object dtype이 bool/None 혼재인 경우 문자열로 통일
for d in (train, valid):
    for c in ref_cat_vars:
        d[c] = d[c].astype(str).where(d[c].notna(), np.nan)

ref_X_train = train[REFERENCE_FULL_SET].copy()
ref_X_valid = valid[REFERENCE_FULL_SET].copy()
for c in ref_cat_vars:
    ref_X_train[c] = ref_X_train[c].astype("category")
    ref_X_valid[c] = pd.Categorical(ref_X_valid[c], categories=ref_X_train[c].cat.categories)

ref_model = lgb.LGBMClassifier(num_leaves=31, learning_rate=0.05, min_child_samples=100,
                                n_estimators=2000, random_state=SEED, verbosity=-1)
ref_model.fit(ref_X_train, train["TARGET"], eval_set=[(ref_X_valid, valid["TARGET"])],
              eval_metric="auc", categorical_feature=ref_cat_vars if ref_cat_vars else "auto",
              callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)])
ref_vs = ref_model.predict_proba(ref_X_valid)[:, 1]
ref_auc = roc_auc_score(valid["TARGET"], ref_vs)
ref_ks = ks_statistic(valid["TARGET"].values, ref_vs)
ref_gini = 2 * ref_auc - 1
print(f"[참고용 전체 세트] 검증 AUC={ref_auc:.4f}, KS={ref_ks:.4f}, Gini={ref_gini:.4f}")

# -----------------------------------------------------------------
# 8. 선택 규칙 적용 (사전 고정)
# -----------------------------------------------------------------
print("\n=== 8. 선택 규칙 적용 ===")
auc_diff = lgbm_with_age["valid_auc"] - scorecard_with_age["valid_auc"]
selected_model_type = "lightgbm" if auc_diff >= 0.01 else "scorecard"
print(f"LightGBM AUC({lgbm_with_age['valid_auc']:.4f}) - 스코어카드 AUC({scorecard_with_age['valid_auc']:.4f}) = {auc_diff:.4f}")
print(f"=> 모델 선택: {selected_model_type}")

if selected_model_type == "lightgbm":
    with_age_result, no_age_result = lgbm_with_age, lgbm_no_age
else:
    with_age_result, no_age_result = scorecard_with_age, scorecard_no_age

age_auc_drop = with_age_result["valid_auc"] - no_age_result["valid_auc"]
age_decision = "나이 제외" if age_auc_drop < 0.005 else "나이 포함"
final_result = no_age_result if age_auc_drop < 0.005 else with_age_result
print(f"나이 유무 AUC 하락: {age_auc_drop:.4f} => {age_decision} 버전을 최종으로 선택")
print(f"최종 모델: {selected_model_type} / {final_result['label']}, 검증 AUC={final_result['valid_auc']:.4f}")

selection_log = {
    "model_selection": {
        "lgbm_with_age_auc": lgbm_with_age["valid_auc"],
        "scorecard_with_age_auc": scorecard_with_age["valid_auc"],
        "auc_diff": round(float(auc_diff), 5),
        "rule": "LightGBM AUC - 스코어카드 AUC >= 0.01 이면 LightGBM, 아니면 스코어카드",
        "selected_model_type": selected_model_type,
    },
    "age_decision": {
        "with_age_auc": with_age_result["valid_auc"],
        "no_age_auc": no_age_result["valid_auc"],
        "auc_drop": round(float(age_auc_drop), 5),
        "rule": "나이를 뺐을 때 AUC 하락이 0.005 미만이면 나이를 뺀 버전이 최종",
        "decision": age_decision,
        "final_label": final_result["label"],
    },
    "reference_full_set": {
        "n_vars": len(REFERENCE_FULL_SET), "valid_auc": round(float(ref_auc), 5),
        "valid_ks": round(float(ref_ks), 5), "valid_gini": round(float(ref_gini), 5),
    },
}

# -----------------------------------------------------------------
# 9. 변수 기여도: 스코어카드면 계수+배점, LightGBM이면 SHAP 상위 15개
# -----------------------------------------------------------------
print("\n=== 9. 변수 기여도 ===")
contribution = {}
if selected_model_type == "scorecard":
    coefs = dict(zip(final_result["var_list"], final_result["model"].coef_[0]))
    contribution["type"] = "logistic_coefficients"
    contribution["coefficients"] = {k: round(float(v), 5) for k, v in coefs.items()}
    contribution["intercept"] = round(float(final_result["model"].intercept_[0]), 5)
else:
    explainer = shap.TreeExplainer(final_result["model"])
    X_for_shap = train[final_result["var_list"]].copy()
    for c in [v for v in final_result["var_list"] if v in CATEGORICAL_VARS]:
        X_for_shap[c] = X_for_shap[c].astype("category")
    shap_values = explainer.shap_values(X_for_shap.sample(n=min(20000, len(X_for_shap)), random_state=SEED))
    if isinstance(shap_values, list):
        shap_values = shap_values[1]
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    shap_rank = sorted(zip(final_result["var_list"], mean_abs_shap), key=lambda t: -t[1])[:15]
    contribution["type"] = "shap_top15"
    contribution["shap_top15"] = [{"variable": v, "mean_abs_shap": round(float(s), 5)} for v, s in shap_rank]

print(json.dumps(contribution, ensure_ascii=False, indent=2)[:2000])

# -----------------------------------------------------------------
# 10. 점수표 변환 (스코어카드가 최종 선택된 경우를 대비해 항상 계산해 둠)
# -----------------------------------------------------------------
print("\n=== 10. 점수표 변환 ===")
PDO = 20
BASE_SCORE = 600
BASE_ODDS_GOOD_TO_BAD = 50  # 정상:연체 = 50:1
FACTOR = PDO / np.log(2)
OFFSET = BASE_SCORE - FACTOR * np.log(BASE_ODDS_GOOD_TO_BAD)

scorecard_final = scorecard_no_age if age_decision == "나이 제외" and selected_model_type == "scorecard" else scorecard_with_age
sc_coefs = dict(zip(scorecard_final["var_list"], scorecard_final["model"].coef_[0]))
sc_intercept = float(scorecard_final["model"].intercept_[0])

# Score = [Offset - Factor*intercept] + sum_i [-Factor * beta_i * woe_i]  (y=TARGET(bad=1) 기준 유도)
base_points = OFFSET - FACTOR * sc_intercept
points_table = {"base_points": round(float(base_points), 2), "factor": round(float(FACTOR), 4),
                 "offset": round(float(OFFSET), 4), "variables": {}}
for var in scorecard_final["var_list"]:
    beta = sc_coefs[var]
    woe_map = woe_tables[var]["woe"].to_dict()
    bin_points = {bin_name: round(float(-FACTOR * beta * woe), 2) for bin_name, woe in woe_map.items()}
    if bin_fits[var]["type"] == "numeric":
        bin_labels = {f"bin{b}": f"[{lo:.4g}, {hi:.4g}]" for b, lo, hi in bin_fits[var]["edges"]}
        bin_labels[MISSING_LABEL] = MISSING_LABEL
    else:
        bin_labels = {k: k for k in bin_points.keys()}
    points_table["variables"][var] = {
        "beta": round(float(beta), 5),
        "bin_points": bin_points,
        "bin_labels": bin_labels,
    }

# -----------------------------------------------------------------
# 저장: 모델 아티팩트 (커밋 안 함 - v2/data/는 gitignore)
# -----------------------------------------------------------------
import pickle

with open(os.path.join(MODEL_DIR, "champion_model.pkl"), "wb") as f:
    pickle.dump({"model": champ_model, "medians": medians, "cols": champ_cols}, f)

with open(os.path.join(MODEL_DIR, "scorecard_bins.pkl"), "wb") as f:
    pickle.dump({"bin_fits": bin_fits, "woe_tables": {k: v for k, v in woe_tables.items()}}, f)

for result in [scorecard_with_age, scorecard_no_age, lgbm_with_age, lgbm_no_age]:
    with open(os.path.join(MODEL_DIR, f"{result['label']}_model.pkl"), "wb") as f:
        pickle.dump({"model": result["model"], "var_list": result["var_list"],
                     "categorical": [c for c in result["var_list"] if c in CATEGORICAL_VARS]}, f)

with open(os.path.join(MODEL_DIR, "selection.json"), "w", encoding="utf-8") as f:
    json.dump({
        "selected_model_type": selected_model_type,
        "age_decision": age_decision,
        "final_label": final_result["label"],
        "final_var_list": final_result["var_list"],
    }, f, ensure_ascii=False, indent=2)

# -----------------------------------------------------------------
# 결과 JSON 저장
# -----------------------------------------------------------------
results = {
    "n_train": len(train), "n_valid": len(valid),
    "variable_selection": variable_selection_log,
    "champion": {"valid_auc": round(float(champ_auc), 5), "valid_ks": round(float(champ_ks), 5),
                 "valid_gini": round(float(champ_gini), 5), "medians": medians,
                 "coefficients": {k: round(float(v), 5) for k, v in zip(champ_cols, champ_model.coef_[0])},
                 "intercept": round(float(champ_model.intercept_[0]), 5),
                 "note": "실제 회사의 기존 심사 점수가 아니라, 외부 점수만 쓰는 심사를 가정한 대용 기준"},
    "scorecard_with_age": {k: v for k, v in scorecard_with_age.items() if k != "model"},
    "scorecard_no_age": {k: v for k, v in scorecard_no_age.items() if k != "model"},
    "lightgbm_with_age": {k: v for k, v in lgbm_with_age.items() if k != "model"},
    "lightgbm_no_age": {k: v for k, v in lgbm_no_age.items() if k != "model"},
    "reference_full_set": selection_log["reference_full_set"],
    "selection": selection_log,
    "contribution": contribution,
    "points_table": points_table,
}
with open(os.path.join(DOCS_DIR, "modeling_results.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)

print(f"\n완료: {os.path.join(DOCS_DIR, 'modeling_results.json')}")
