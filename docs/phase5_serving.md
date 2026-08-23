# Phase 5: FastAPI 서빙 — 구현 및 로컬 테스트 결과

스펙: [docs/phase5_api_spec.md](phase5_api_spec.md) (승인됨). 계획: [docs/phase5_serving_plan.md](phase5_serving_plan.md).

## 구현 구성

| 파일 | 역할 |
|---|---|
| `scripts/_lean_a_features.py` | Lean(A) 집계 SQL을 소스 무관 함수로 분리(리팩터링) — 배치 파이프라인과 실시간 API가 동일 로직 공유 |
| `scripts/build_features_leanA.py` | (기존 스크립트를 `_lean_a_features.py` 사용하도록 리팩터링 — **출력이 리팩터링 전과 완전히 동일함을 `pd.testing.assert_frame_equal`로 검증함**) |
| `scripts/train_serving_model.py` | 서빙용 모델 학습(전체 application_train 100%) + `models/`에 저장 |
| `app/feature_live.py` | `/predict/live` 요청 페이로드 → in-memory DataFrame 등록 → `_lean_a_features.py` SQL 재사용 → Lean(A) feature 1행 생성 (합성 SK_ID_CURR/SK_ID_PREV/SK_ID_BUREAU로 그룹핑) |
| `app/model.py` | 모델+SHAP explainer 로딩, 예측+상위 요인 추출 |
| `app/serving_lookup.py` | `/predict`용 train+test 사전계산 feature 조회 |
| `app/schemas.py` | pydantic 요청/응답 스키마 |
| `app/main.py` | FastAPI 앱, 4개 엔드포인트 |

## 리팩터링 안전성 검증

`build_features_leanA.py`를 공유 모듈 사용 방식으로 바꾼 뒤, 리팩터링 전 산출물(`train/test_features_leanA.parquet`)을 백업해두고 재실행 결과와 `pandas.testing.assert_frame_equal`로 비교 — **완전히 동일함(IDENTICAL: True)** 확인. 기존 Phase 2~4 결과(EDA, 벤치마크, SHAP)의 근거가 되는 데이터가 이번 리팩터링으로 바뀌지 않았음을 보장.

## 로컬 uvicorn 테스트 결과

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

| 테스트 | 결과 |
|---|---|
| `GET /health` | 200, `{"status": "ok"}` |
| `GET /model/info` | 200, `trained_at`/`validated_auc`/`validation_scheme`/`endpoint_guide` 정상 반환 |
| `POST /predict` (test set 고객 100001) | 200, `default_probability=0.2078`, `risk_class=low`, SHAP 상위 요인 5개(EXT_SOURCE_1/2/3 등) |
| `POST /predict` (train set 고객 117276) | 200, `default_probability=0.5565`, `risk_class=high` — train/test 양쪽 조회 정상 동작 확인 |
| `POST /predict` (존재하지 않는 SK_ID_CURR) | **404**, `{"detail": "SK_ID_CURR not found"}` |
| `POST /predict/live` (application + bureau 1건 + previous_application 1건(installments 포함)) | 200, `has_bureau_record=true`, `has_previous_application=true` — 실시간 집계가 개별 유닛테스트와 동일하게 동작 |
| `POST /predict/live` (application만, 이력 없음) | 200, `has_bureau_record=false`, `has_previous_application=false` — 신규 고객(이력 없음) 시나리오 정상 처리, `DAYS_EMPLOYED=365243` anomaly도 정상 감지·NULL 처리 |
| `POST /predict/live` (`application` 필드 누락) | **422**, pydantic 검증 오류 정상 반환 |
| `GET /docs`, `GET /openapi.json` | 200, Swagger UI 정상 로드 |

모든 엔드포인트가 스펙대로 동작함을 확인. 발견 후 즉시 고친 버그 1건: `/model/info`의 `trained_at`이 설명 문자열을 앞 10글자 자르는 실수(`"applicatio"`)였음 → `train_serving_model.py`에 실제 날짜 필드(`datetime.date.today().isoformat()`)를 스키마에 추가해 수정.

## 알려진 제약 (다음 단계 후보)

- `/predict/live`는 API 스펙상 `bureau_records`에 `bureau_balance`(월별 상태 이력) 중첩을 지원하지 않음 — `bb_*` 관련 feature는 항상 NULL로 집계됨(스펙 승인 시 의도된 범위)
- `/predict` 조회는 매 요청마다 parquet 전체를 스캔(WHERE 필터) — 현재 규모(30만+행)에서는 충분히 빠르지만, 트래픽이 커지면 인메모리 인덱스나 DB 전환 고려
- Docker 패키징은 아직 미착수 (원래 Phase 5 범위, 별도 진행 필요)
