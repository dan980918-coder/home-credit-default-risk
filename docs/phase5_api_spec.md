# Phase 5: API 스펙 설계

> ✅ **승인 및 구현 완료.** 아래는 구현 착수 전 설계 단계에서 작성한 스펙 원본(의사결정 기록 보존 목적)이며, 실제 구현/테스트 결과는 [phase5_serving.md](phase5_serving.md) 참고.

모델: Lean(A) + LightGBM, 전체 `application_train`(100%)으로 재학습.
결정 사항(사용자 확정) 반영: A(사전계산 조회) + C(실시간 집계 데모) 병행, SHAP 상위 3~5개 기본 포함, held-out 성능 주의문구 명시.

## 엔드포인트 목록

| 메서드/경로 | 용도 |
|---|---|
| `GET /health` | 헬스체크 |
| `GET /model/info` | 모델 메타데이터 (버전, 검증 AUC, 주의문구 등) |
| `POST /predict` | **A안**: SK_ID_CURR으로 사전계산된 feature 조회 후 예측 |
| `POST /predict/live` | **C안**: 원본 필드(application + 선택적 bureau/previous_application 이력)를 받아 그 자리에서 Lean(A) feature를 집계 후 예측 (신규 고객 데모용) |

---

## 1. `GET /health`

```json
// 200 응답
{ "status": "ok" }
```

## 2. `GET /model/info`

```json
// 200 응답
{
  "model_name": "lean_a_lightgbm",
  "model_version": "v1",
  "trained_at": "2026-08-22",
  "training_data": "application_train.csv 전체(307,511건) + bureau/previous_application 파생 feature(Lean(A), 163개)",
  "validated_auc": 0.7825,
  "validation_scheme": "80/20 stratified split (Phase 4, random_state=42) 기준 — 서빙 모델(전체 데이터로 재학습)의 held-out 성능은 별도로 측정되지 않음",
  "feature_count": 163,
  "shap_explanation": true
}
```

`validation_scheme` 필드에 명시적으로 주의문구를 포함(요청하신 "AUC 0.7825는 80/20 기준, 재학습 모델 자체 성능은 미측정" 문구를 API 응답에도 노출) — README에도 동일 문구 기재 예정.

---

## 3. `POST /predict` (A안: SK_ID_CURR 조회)

### 요청
```json
{
  "sk_id_curr": 100001
}
```

### 응답 (200)
```json
{
  "sk_id_curr": 100001,
  "default_probability": 0.0823,
  "risk_class": "low",
  "threshold": 0.5,
  "top_factors": [
    { "feature": "EXT_SOURCE_2", "feature_value": 0.65, "shap_value": -0.31, "direction": "decreases_risk" },
    { "feature": "EXT_SOURCE_3", "feature_value": 0.58, "shap_value": -0.22, "direction": "decreases_risk" },
    { "feature": "bureau_debt_credit_ratio", "feature_value": 0.71, "shap_value": 0.14, "direction": "increases_risk" },
    { "feature": "inst_late_frac_mean", "feature_value": 0.02, "shap_value": -0.05, "direction": "decreases_risk" }
  ],
  "data_source": "precomputed",
  "model_version": "v1"
}
```

- `sk_id_curr`가 사전계산 테이블(train+test 통합, TARGET 제외)에 없으면 **404** (`{"detail": "SK_ID_CURR not found"}`)
- `top_factors`는 개수를 3~5개로(기본 5개, `top_n` 쿼리 파라미터로 3~5 조정 가능하게 할지는 구현 시 결정 — 기본값 5 제안)
- `risk_class`: `threshold`(기본 0.5, Phase 4에서 쓴 것과 동일) 기준 `"high"`/`"low"`

---

## 4. `POST /predict/live` (C안: 실시간 집계 데모)

새 신청자를 가정 — application 원본 필드(있는 만큼만) + 선택적으로 bureau/previous_application 이력을 받아 `build_features_leanA.py`와 동일한 DuckDB 집계 로직을 그 자리에서 재사용해 Lean(A) feature를 만든 뒤 예측.

### 요청

```json
{
  "application": {
    "CODE_GENDER": "F",
    "FLAG_OWN_CAR": "N",
    "FLAG_OWN_REALTY": "Y",
    "AMT_INCOME_TOTAL": 180000,
    "AMT_CREDIT": 450000,
    "AMT_ANNUITY": 22000,
    "AMT_GOODS_PRICE": 450000,
    "NAME_EDUCATION_TYPE": "Higher education",
    "DAYS_BIRTH": -12000,
    "DAYS_EMPLOYED": -1500,
    "EXT_SOURCE_1": 0.55,
    "EXT_SOURCE_2": 0.62,
    "EXT_SOURCE_3": 0.48
    // ... application 원본 컬럼 중 있는 값만 (나머지는 자동으로 NULL 처리)
  },
  "bureau_records": [
    {
      "CREDIT_ACTIVE": "Active",
      "DAYS_CREDIT": -500,
      "AMT_CREDIT_SUM": 100000,
      "AMT_CREDIT_SUM_DEBT": 40000,
      "CREDIT_TYPE": "Consumer credit"
      // ... bureau.csv 컬럼 중 있는 값만
    }
  ],
  "previous_application_records": [
    {
      "NAME_CONTRACT_STATUS": "Approved",
      "AMT_CREDIT": 200000,
      "AMT_APPLICATION": 200000,
      "DAYS_DECISION": -400,
      "installments": [
        { "AMT_INSTALMENT": 5000, "AMT_PAYMENT": 5000, "DAYS_INSTALMENT": -350, "DAYS_ENTRY_PAYMENT": -352 }
      ]
      // credit_card_records / pos_cash_records도 같은 방식으로 선택적 포함 가능
    }
  ]
}
```

- `application`만 필수, `bureau_records`/`previous_application_records`는 **생략 가능**(생략 시 `has_bureau_record`/`has_previous_application` = False로 자동 처리 — 실제 신규 고객 시나리오와 일치)
- `application` 안의 필드도 전부 optional — 넘기지 않은 필드는 NULL로 집계(Lean(A) 파이프라인이 이미 NULL을 정상 처리하도록 설계돼 있음)
- 컬럼명은 원본 CSV 컬럼명 그대로 사용(별도 매핑 불필요, 문서화 부담 감소)

### 응답 (200)

`/predict`와 동일한 형태 + `data_source: "live"` + 어떤 블록이 실제로 채워졌는지 표시:

```json
{
  "sk_id_curr": null,
  "default_probability": 0.1543,
  "risk_class": "low",
  "threshold": 0.5,
  "top_factors": [ /* 동일 형태 */ ],
  "data_source": "live",
  "has_bureau_record": true,
  "has_previous_application": true,
  "model_version": "v1"
}
```

- 입력 검증 실패(예: `application` 자체가 없음) 시 **422**

---

## 5. 공통 사항

- **top_factors 방향(`direction`) 정의**: SHAP value > 0 → `"increases_risk"`, < 0 → `"decreases_risk"` (모델이 TARGET=1을 양성 클래스로 학습했으므로 SHAP 양수 = 연체 확률↑ 방향)
- **에러 응답 형식**: FastAPI 기본 `{"detail": "..."}` 형식 그대로 사용
- **인증**: 이번 Phase 5 범위에서는 미포함(포트폴리오 데모 목적, 필요시 이후 추가)

---

(위 질문은 설계 단계 원본 그대로 보존 — 사용자가 승인해 이 스펙대로 구현 완료됨. 실제 구현/테스트 결과는 [phase5_serving.md](phase5_serving.md) 참고.)
