"""
Phase 4: 최종 선정 모델(Lean(A) + LightGBM, 3x4 비교에서 AUC 최고) SHAP 분석.
phase4_modeling.py와 동일한 split/하이퍼파라미터로 재학습 후 TreeExplainer 적용.
"""
import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False
from sklearn.model_selection import train_test_split

LEAN_A_PATH = "data/processed/train_features_leanA.parquet"
RANDOM_STATE = 42
SHAP_SAMPLE_SIZE = 5000

df = pd.read_parquet(LEAN_A_PATH)
y = df["TARGET"].astype(int)
X = df.drop(columns=["SK_ID_CURR", "TARGET"])
cat_cols = [c for c in X.columns if X[c].dtype == object or str(X[c].dtype) == "bool"]
for c in cat_cols:
    X[c] = X[c].astype(str).astype("category")

X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
)
scale_pos_weight = (len(y_train) - y_train.sum()) / y_train.sum()

model = lgb.LGBMClassifier(
    n_estimators=200, scale_pos_weight=scale_pos_weight,
    random_state=RANDOM_STATE, verbosity=-1,
)
model.fit(X_train, y_train, categorical_feature=cat_cols)
print("model trained")

X_shap = X_val.sample(n=SHAP_SAMPLE_SIZE, random_state=RANDOM_STATE)
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_shap)
print("shap_values shape:", np.array(shap_values).shape)

# 이진분류 LightGBM sklearn: shap_values가 (n, n_features) 또는 [class0, class1] 리스트일 수 있음
if isinstance(shap_values, list):
    sv = shap_values[1]
else:
    sv = shap_values

mean_abs_shap = pd.Series(np.abs(sv).mean(axis=0), index=X_shap.columns).sort_values(ascending=False)
print("\ntop 20 features by mean |SHAP|:")
print(mean_abs_shap.head(20).to_string())
mean_abs_shap.to_csv("data/processed/phase4_shap_importance.csv")

fig1 = plt.figure(figsize=(9, 8))
shap.summary_plot(sv, X_shap, show=False, max_display=20)
plt.title("SHAP summary (top 20 features)")
plt.tight_layout()
plt.savefig("reports/figures/phase4_shap_summary.png", dpi=150, bbox_inches="tight")
plt.close(fig1)
print("saved reports/figures/phase4_shap_summary.png")

fig2 = plt.figure(figsize=(8, 8))
shap.summary_plot(sv, X_shap, plot_type="bar", show=False, max_display=20)
plt.title("SHAP feature importance (mean |SHAP|, top 20)")
plt.tight_layout()
plt.savefig("reports/figures/phase4_shap_bar.png", dpi=150, bbox_inches="tight")
plt.close(fig2)
print("saved reports/figures/phase4_shap_bar.png")
