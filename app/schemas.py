"""요청/응답 pydantic 스키마. docs/phase5_api_spec.md 기준."""
from typing import Literal, Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class ModelInfoResponse(BaseModel):
    model_name: str
    model_version: str
    trained_at: str
    training_data: str
    validated_auc: float
    validation_scheme: str
    feature_count: int
    shap_explanation: bool = True
    predict_lookup_enabled: bool
    endpoint_guide: dict[str, str] = Field(default_factory=lambda: {
        "/predict": "기존 학습 데이터(application_train/test)에 있던 고객을 SK_ID_CURR으로 조회해 예측 — 사전계산된 feature 사용, 빠름",
        "/predict/live": "신규 고객(학습 데이터에 없는 고객)을 위한 실시간 집계 데모 — 원본 필드를 입력받아 그 자리에서 Lean(A) feature를 계산 후 예측",
    })


class PredictRequest(BaseModel):
    sk_id_curr: int


class Factor(BaseModel):
    feature: str
    feature_value: Optional[Any] = None
    shap_value: float
    direction: Literal["increases_risk", "decreases_risk"]


class PredictResponse(BaseModel):
    sk_id_curr: Optional[int] = None
    default_probability: float
    risk_class: Literal["high", "low"]
    threshold: float
    top_factors: list[Factor]
    data_source: Literal["precomputed", "live"]
    has_bureau_record: Optional[bool] = None
    has_previous_application: Optional[bool] = None
    model_version: str


class InstallmentRecord(BaseModel):
    model_config = ConfigDict(extra="allow")


class CreditCardRecord(BaseModel):
    model_config = ConfigDict(extra="allow")


class PosCashRecord(BaseModel):
    model_config = ConfigDict(extra="allow")


class BureauRecord(BaseModel):
    model_config = ConfigDict(extra="allow")


class PreviousApplicationRecord(BaseModel):
    model_config = ConfigDict(extra="allow")
    installments: list[InstallmentRecord] = Field(default_factory=list)
    credit_card_records: list[CreditCardRecord] = Field(default_factory=list)
    pos_cash_records: list[PosCashRecord] = Field(default_factory=list)


class ApplicationFields(BaseModel):
    model_config = ConfigDict(extra="allow")


class LivePredictRequest(BaseModel):
    application: ApplicationFields
    bureau_records: list[BureauRecord] = Field(default_factory=list)
    previous_application_records: list[PreviousApplicationRecord] = Field(default_factory=list)
