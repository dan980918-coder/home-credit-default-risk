"""
Phase 5: Home Credit Default Risk 예측 API. 최종 모델: Lean(A) + LightGBM.
스펙: docs/phase5_api_spec.md

/predict      - 기존 학습 데이터(application_train/test)에 있던 고객 조회용 (사전계산 feature)
/predict/live - 신규 고객을 위한 실시간 집계 데모용 (원본 필드 -> 그 자리에서 Lean(A) feature 계산)
"""
from fastapi import FastAPI, HTTPException

from app.schemas import (
    HealthResponse, ModelInfoResponse, PredictRequest, PredictResponse, LivePredictRequest,
)
from app.model import get_bundle
from app.serving_lookup import lookup
from app.feature_live import build_live_feature_row

app = FastAPI(
    title="Home Credit Default Risk API",
    description=(
        "최종 모델: Lean(A) + LightGBM. "
        "/predict는 기존 학습 데이터에 있던 고객 조회용(사전계산 feature), "
        "/predict/live는 신규 고객을 위한 실시간 집계 데모용입니다."
    ),
)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()


@app.get("/model/info", response_model=ModelInfoResponse)
def model_info():
    schema = get_bundle().schema
    return ModelInfoResponse(
        model_name=schema["model_name"],
        model_version=schema["model_version"],
        trained_at=schema["trained_at"],
        training_data=schema["trained_on"],
        validated_auc=schema["validated_auc"],
        validation_scheme=schema["validation_scheme"],
        feature_count=len(schema["feature_columns"]),
    )


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    row = lookup(req.sk_id_curr)
    if row is None:
        raise HTTPException(status_code=404, detail="SK_ID_CURR not found")

    bundle = get_bundle()
    result = bundle.predict_with_explanation(row)
    return PredictResponse(
        sk_id_curr=req.sk_id_curr,
        data_source="precomputed",
        has_bureau_record=bool(row.at[0, "has_bureau_record"]),
        has_previous_application=bool(row.at[0, "has_previous_application"]),
        model_version=bundle.schema["model_version"],
        **result,
    )


@app.post("/predict/live", response_model=PredictResponse)
def predict_live(req: LivePredictRequest):
    payload = req.model_dump()
    row = build_live_feature_row(payload)

    bundle = get_bundle()
    result = bundle.predict_with_explanation(row)
    return PredictResponse(
        sk_id_curr=None,
        data_source="live",
        has_bureau_record=bool(row.at[0, "has_bureau_record"]),
        has_previous_application=bool(row.at[0, "has_previous_application"]),
        model_version=bundle.schema["model_version"],
        **result,
    )
