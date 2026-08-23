# Home Credit Default Risk

대출 채무불이행(연체) 예측 포트폴리오 프로젝트. 진행 원칙과 로드맵은 [PROJECT_GUIDELINES.md](PROJECT_GUIDELINES.md) 참고.

현재 상태: **Phase 5(FastAPI 서빙) 구현 완료**. 최종 모델: **Lean(A) + LightGBM (검증 AUC 0.7825)** — 상세는 [docs/phase4_modeling.md](docs/phase4_modeling.md), 서빙 API 스펙은 [docs/phase5_api_spec.md](docs/phase5_api_spec.md) 참고.

이전에 진행하던 AMEX Default Prediction 기반 버전은 `archive/amex/`에 보존돼 있습니다 (참고용, 현재 로드맵과는 무관).

## API 실행

```bash
pip install -r requirements.txt
python3 scripts/train_serving_model.py   # 서빙용 모델 학습 (최초 1회, models/에 저장)
uvicorn app.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000/docs`로 Swagger UI 확인 가능.

### Docker로 실행

```bash
docker build -t home-credit-api:latest .
docker run -d -p 8000:8000 -v "$(pwd)/data:/app/data:ro" home-credit-api:latest
```

이미지 크기 약 238MB (서빙에 불필요한 scikit-learn/xgboost/matplotlib 등은 제외한 `requirements-serving.txt` 사용). `data/`는 이미지에 포함하지 않고 런타임에 볼륨으로 마운트 — 상세는 [docs/phase5_docker.md](docs/phase5_docker.md) 참고.

### 엔드포인트

| 엔드포인트 | 용도 |
|---|---|
| `GET /health` | 헬스체크 |
| `GET /model/info` | 모델 메타데이터 (버전, 검증 AUC, 주의문구) |
| `POST /predict` | **기존 학습 데이터(application_train/test)에 있던 고객 조회용** — SK_ID_CURR으로 사전계산된 feature를 조회해 빠르게 예측 |
| `POST /predict/live` | **신규 고객(학습 데이터에 없는 고객)을 위한 실시간 집계 데모용** — 원본 필드(application + 선택적 bureau/previous_application 이력)를 입력받아 그 자리에서 배치 파이프라인과 동일한 로직으로 Lean(A) feature를 계산한 뒤 예측 |

두 엔드포인트로 나뉜 이유: `/predict`는 이미 알고 있는 고객을 빠르게 조회하는 용도이고, `/predict/live`는 실제 서비스에서 마주치는 "한 번도 본 적 없는 신규 신청자"를 심사하는 시나리오를 보여주기 위한 것입니다.

### ⚠️ 성능 지표 관련 주의사항

- API가 참조하는 **검증 AUC 0.7825**는 [Phase 4](docs/phase4_modeling.md)의 80/20 stratified split 기준 결과입니다.
- 실제 서빙에 쓰이는 모델(`models/lean_a_lightgbm_v1.joblib`)은 **전체 application_train(100%)으로 재학습**되어 Phase 4 검증 모델과 학습 데이터 양이 다릅니다.
- 따라서 **이 서빙 모델 자체의 held-out 성능은 별도로 측정되지 않았습니다** — 0.7825는 "이 정도 성능을 내는 방법론으로 학습했다"는 근거로 인용하는 것이며, 서빙 모델의 정확한 성능 보증치가 아닙니다.

상세 구현 노트는 [docs/phase5_serving.md](docs/phase5_serving.md) 참고.
