"""
Phase 5: 서빙용 모델 학습. Phase 4에서 확정한 Lean(A) + LightGBM을
전체 application_train(100%)으로 재학습(Phase 4는 80%만 사용).

주의: 이 모델 자체의 held-out 성능은 별도로 측정하지 않음 — 참고하는 AUC 0.7825는
Phase 4의 80/20 split 결과(docs/phase4_modeling.md)이며, 이 서빙 모델과는
학습 데이터 양이 다름(100% vs 80%). README/API 응답에 이 주의문구를 명시한다.
"""
import json
import datetime
import joblib
import pandas as pd
from _train_common import prepare_categorical_columns, train_lightgbm

LEAN_A_PATH = "data/processed/train_features_leanA.parquet"
MODEL_DIR = "models"
RANDOM_STATE = 42

df = pd.read_parquet(LEAN_A_PATH)
y = df["TARGET"].astype(int)
X = df.drop(columns=["SK_ID_CURR", "TARGET"])

X, cat_cols = prepare_categorical_columns(X)
categories = {c: X[c].cat.categories.tolist() for c in cat_cols}

scale_pos_weight = (len(y) - y.sum()) / y.sum()
print(f"training on full data: {X.shape}, scale_pos_weight={scale_pos_weight:.2f}")

model = train_lightgbm(X, y, scale_pos_weight, random_state=RANDOM_STATE, categorical_feature=cat_cols)
print("model trained on 100% of application_train")

import os
os.makedirs(MODEL_DIR, exist_ok=True)
joblib.dump(model, f"{MODEL_DIR}/lean_a_lightgbm_v1.joblib")

schema = {
    "feature_columns": list(X.columns),
    "categorical_columns": cat_cols,
    "categories": categories,
    "model_name": "lean_a_lightgbm",
    "model_version": "v1",
    "trained_at": datetime.date.today().isoformat(),
    "trained_on": "application_train.csv 전체(307,511건) + bureau/previous_application 파생 feature (Lean(A), 161개 feature)",
    "validated_auc": 0.7825,
    "validation_scheme": (
        "80/20 stratified split (Phase 4, random_state=42) 기준 — "
        "서빙 모델(전체 데이터로 재학습)의 held-out 성능은 별도로 측정되지 않음"
    ),
}
with open(f"{MODEL_DIR}/lean_a_lightgbm_v1_schema.json", "w") as f:
    json.dump(schema, f, ensure_ascii=False, indent=2)

print(f"saved {MODEL_DIR}/lean_a_lightgbm_v1.joblib")
print(f"saved {MODEL_DIR}/lean_a_lightgbm_v1_schema.json")
print(f"feature count: {len(X.columns)}, categorical: {len(cat_cols)}")
