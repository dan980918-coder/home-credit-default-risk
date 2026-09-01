"""
Phase 5: Home Credit Default Risk 예측 API. 최종 모델: Lean(A) + LightGBM.
스펙: docs/phase5_api_spec.md

/predict      - 기존 학습 데이터(application_train/test)에 있던 고객 조회용 (사전계산 feature)
/predict/live - 신규 고객을 위한 실시간 집계 데모용 (원본 필드 -> 그 자리에서 Lean(A) feature 계산)

PUBLIC_DEPLOYMENT 환경변수 (Phase 6): 공개 배포(Render/EC2 등)에서는 반드시
true로 설정 — /predict가 SK_ID_CURR으로 라이선스가 제한적인 Home Credit
데이터셋의 개별 고객 feature 값을 그대로 노출하게 되는 걸 막는다
(docs/phase6_deploy_plan.md 참고). 로컬 개발 시에는 기본값(false)으로
/predict를 그대로 사용 가능.
"""
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.schemas import (
    HealthResponse, ModelInfoResponse, PredictRequest, PredictResponse, LivePredictRequest,
)
from app.model import get_bundle
from app.serving_lookup import lookup
from app.feature_live import build_live_feature_row, FeatureTypeError

PUBLIC_DEPLOYMENT = os.environ.get("PUBLIC_DEPLOYMENT", "false").lower() == "true"

app = FastAPI(
    title="Home Credit Default Risk API",
    description=(
        "최종 모델: Lean(A) + LightGBM. "
        "/predict는 기존 학습 데이터에 있던 고객 조회용(사전계산 feature), "
        "/predict/live는 신규 고객을 위한 실시간 집계 데모용입니다."
        + (" [PUBLIC_DEPLOYMENT 모드: /predict는 비활성화됨]" if PUBLIC_DEPLOYMENT else "")
    ),
)


@app.exception_handler(FeatureTypeError)
def feature_type_error_handler(request: Request, exc: FeatureTypeError):
    """/predict/live에서 값은 왔지만 스키마 타입으로 변환 불가능한 필드가 있을 때
    422로 명확히 거부. 필드 자체가 없는(진짜 결측) 경우는 이 핸들러를 타지 않고
    정상적으로 None 처리된다 — feature_live.FeatureTypeError 참고."""
    loc = ["body", exc.table] + ([str(exc.index)] if exc.index is not None else []) + [exc.field]
    return JSONResponse(
        status_code=422,
        content={"detail": [{
            "loc": loc,
            "msg": f"value is not a valid {exc.expected_dtype.lower()}",
            "type": "type_error",
            "input": None if exc.value is None else str(exc.value),
        }]},
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
        predict_lookup_enabled=not PUBLIC_DEPLOYMENT,
    )


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if PUBLIC_DEPLOYMENT:
        raise HTTPException(status_code=403, detail=(
            "This endpoint is disabled in public deployments (PUBLIC_DEPLOYMENT=true) "
            "to avoid exposing individual records from the license-restricted Home Credit "
            "dataset. Use /predict/live instead, or run locally with PUBLIC_DEPLOYMENT unset."
        ))

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
