"""
Phase 7 전용: 모니터링 대시보드의 배치별 AUC가 신뢰할 수 있으려면 모델이
한 번도 보지 못한 데이터로 평가해야 한다. 서빙 모델(Phase 5)은 전체
application_train 100%로 재학습돼 있어 그걸 그대로 쓰면 in-sample
평가가 되어 AUC가 부풀려짐(실측: 0.80~0.86 vs Phase 4 held-out 0.7825).

그래서 Phase 4와 동일한 레시피(train_test_split 80/20, random_state=42,
LightGBM n_estimators=200)로 80%만 학습한 모델을 별도로 만들고,
나머지 20%(모델이 전혀 본 적 없는 진짜 held-out)만 모니터링 대시보드의
reference/배치 풀로 사용한다.
"""
import joblib
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split

LEAN_A_PATH = "data/processed/train_features_leanA.parquet"
OUT_MODEL = "models/lean_a_lightgbm_holdout_v1.joblib"
OUT_HOLDOUT_DATA = "data/processed/monitoring_holdout.parquet"
RANDOM_STATE = 42

df = pd.read_parquet(LEAN_A_PATH)
y = df["TARGET"].astype(int)
X = df.drop(columns=["TARGET"])  # SK_ID_CURR은 남겨둠(참고용, 학습에는 안 씀)

cat_cols = [c for c in X.columns if X[c].dtype == object or str(X[c].dtype) == "bool"]
for c in cat_cols:
    X[c] = X[c].astype(str).astype("category")

X_train, X_holdout, y_train, y_holdout = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
)

X_train_fit = X_train.drop(columns=["SK_ID_CURR"])
scale_pos_weight = (len(y_train) - y_train.sum()) / y_train.sum()
print(f"train: {X_train_fit.shape}, holdout(never seen): {X_holdout.shape}")

model = lgb.LGBMClassifier(
    n_estimators=200, scale_pos_weight=scale_pos_weight,
    random_state=RANDOM_STATE, verbosity=-1,
)
model.fit(X_train_fit, y_train, categorical_feature=cat_cols)
joblib.dump(model, OUT_MODEL)
print(f"saved {OUT_MODEL}")

holdout_df = X_holdout.copy()
holdout_df["TARGET"] = y_holdout.values
holdout_df.to_parquet(OUT_HOLDOUT_DATA, index=False)
print(f"saved {OUT_HOLDOUT_DATA} ({len(holdout_df)} rows, 모델이 학습 때 전혀 보지 않은 데이터)")

# sanity check: 이 holdout에 대한 AUC가 Phase 4의 0.7825와 비슷해야 함
from sklearn.metrics import roc_auc_score
proba = model.predict_proba(X_holdout.drop(columns=["SK_ID_CURR"]))[:, 1]
print(f"holdout AUC: {roc_auc_score(y_holdout, proba):.4f} (Phase 4 기준: 0.7825 근방이어야 정상)")
