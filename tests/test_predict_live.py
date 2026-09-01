"""POST /predict/live 입력 검증 테스트.

값 자체가 없는 필드(결측)는 그대로 None 처리되지만, 값은 왔는데 스키마 타입과
맞지 않는 값(예: numeric 컬럼에 문자열)은 조용히 None으로 넘기지 않고 422로
명확히 거부해야 한다 — app/feature_live.py의 FeatureTypeError 참고.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID_APPLICATION = {
    "CODE_GENDER": "F",
    "FLAG_OWN_CAR": "N",
    "FLAG_OWN_REALTY": "Y",
    "AMT_INCOME_TOTAL": 180000,
    "AMT_CREDIT": 450000,
    "AMT_ANNUITY": 22000,
    "NAME_EDUCATION_TYPE": "Higher education",
    "DAYS_BIRTH": -12000,
    "DAYS_EMPLOYED": -1500,
    "EXT_SOURCE_2": 0.62,
}


def test_predict_live_valid_application_returns_200():
    response = client.post("/predict/live", json={"application": VALID_APPLICATION})
    assert response.status_code == 200
    body = response.json()
    assert body["data_source"] == "live"
    assert body["has_bureau_record"] is False
    assert body["has_previous_application"] is False
    assert 0.0 <= body["default_probability"] <= 1.0


def test_predict_live_invalid_numeric_type_returns_422():
    bad_application = {**VALID_APPLICATION, "AMT_INCOME_TOTAL": "abc"}
    response = client.post("/predict/live", json={"application": bad_application})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(
        "AMT_INCOME_TOTAL" in err["loc"] and err["input"] == "abc"
        for err in detail
    )
