"""모델/SHAP explainer 로딩 및 예측+설명 생성. 앱 시작 시 1회 로드해 재사용."""
import json
import joblib
import numpy as np
import pandas as pd
import shap

MODEL_PATH = "models/lean_a_lightgbm_v1.joblib"
SCHEMA_PATH = "models/lean_a_lightgbm_v1_schema.json"

DEFAULT_THRESHOLD = 0.5
DEFAULT_TOP_N = 5


class ModelBundle:
    def __init__(self):
        self.model = joblib.load(MODEL_PATH)
        with open(SCHEMA_PATH) as f:
            self.schema = json.load(f)
        self.feature_columns = self.schema["feature_columns"]
        self.categorical_columns = self.schema["categorical_columns"]
        self.categories = self.schema["categories"]
        self.explainer = shap.TreeExplainer(self.model)

    def prepare_row(self, row: pd.DataFrame) -> pd.DataFrame:
        """임의 소스(사전계산 조회 or 실시간 집계)에서 온 1행을 학습 때와
        동일한 컬럼 순서/타입으로 정렬. 학습 시 못 본 범주값은 NaN 처리."""
        row = row.reindex(columns=self.feature_columns)
        for c in self.categorical_columns:
            row[c] = pd.Categorical(row[c].astype(str), categories=self.categories[c])
        return row

    def predict_with_explanation(self, row: pd.DataFrame, top_n: int = DEFAULT_TOP_N,
                                  threshold: float = DEFAULT_THRESHOLD) -> dict:
        X = self.prepare_row(row)
        proba = float(self.model.predict_proba(X)[0, 1])
        risk_class = "high" if proba >= threshold else "low"

        shap_values = self.explainer.shap_values(X)
        sv = shap_values[1][0] if isinstance(shap_values, list) else shap_values[0]

        order = np.argsort(-np.abs(sv))[:top_n]
        top_factors = []
        for idx in order:
            feature = self.feature_columns[idx]
            value = X.iloc[0, idx]
            if pd.isna(value):
                value = None
            elif isinstance(value, (np.floating, float)):
                value = round(float(value), 4)
            else:
                value = str(value)
            top_factors.append({
                "feature": feature,
                "feature_value": value,
                "shap_value": round(float(sv[idx]), 4),
                "direction": "increases_risk" if sv[idx] > 0 else "decreases_risk",
            })

        return {
            "default_probability": round(proba, 4),
            "risk_class": risk_class,
            "threshold": threshold,
            "top_factors": top_factors,
        }


_bundle: ModelBundle | None = None


def get_bundle() -> ModelBundle:
    global _bundle
    if _bundle is None:
        _bundle = ModelBundle()
    return _bundle
