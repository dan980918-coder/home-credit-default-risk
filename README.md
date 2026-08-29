# Home Credit Default Risk

대출 신청자의 채무불이행(연체) 가능성을 예측하는 신용평가 모델을 데이터 검증부터 API 서빙, 클라우드 배포, 모니터링까지 엔드투엔드로 구현한 프로젝트입니다. 매 단계마다 후보안 비교·근거 기록·실측 검증을 원칙으로 진행했습니다. 진행 원칙과 로드맵은 [PROJECT_GUIDELINES.md](PROJECT_GUIDELINES.md) 참고.

## 데이터 전환 히스토리 — AMEX → Home Credit

처음엔 American Express Default Prediction(Kaggle, CC0)으로 시작했으나, **해석 가능한 feature 구조가 필요해** 다중 테이블(관계형) 구조를 가진 **Home Credit Default Risk**로 전환했습니다. AMEX 데이터는 단일 파일에 익명화된 190개 집계 feature만 제공해 "왜 이 feature가 중요한가"를 설명하기 어려웠던 반면, Home Credit은 대출 신청서(application) + 신용조회이력(bureau) + 과거 대출이력(previous_application) 등 8개 테이블이 의미가 분명한 컬럼으로 구성돼 있어, feature engineering과 SHAP 해석 모두에서 "왜 위험한가"를 설명하기 훨씬 수월했습니다. 이전 AMEX 진행 내역은 [`archive/amex/`](archive/amex/)에 그대로 보존돼 있습니다(참고용, 현재 파이프라인과는 무관).

## Phase별 요약

| Phase | 내용 | 문서 |
|---|---|---|
| 1. 데이터 검증 | 8개 테이블 스키마·조인 무결성 검증(SK_ID_CURR 레벨은 100% 클린, 하위 이력 테이블은 3~28% 고아 레코드 발견·원인 규명), Kaggle 라이선스 확인(제한적 — 원본 데이터 비공개 유지 결정) | [phase1_data_validation.md](docs/phase1_data_validation.md) |
| 2. EDA | 클래스 불균형(TARGET=1 8.1%), 결측-TARGET 연관성(phi 계수), `DAYS_EMPLOYED=365243` anomaly(전체 18%) 발견 및 처리 | [phase2_eda.md](docs/phase2_eda.md) |
| 3. Feature Engineering | 다중 테이블 집계 — Lean(A, 해석 중심 163컬럼) vs Full(B, 전체 통계량 392컬럼) 두 버전 구축·비교 | [feature_engineering_leanA.md](docs/feature_engineering_leanA.md) · [feature_engineering_fullB.md](docs/feature_engineering_fullB.md) · [phase3_benchmark.md](docs/phase3_benchmark.md) |
| 4. 모델링 & 해석 | App-only/Lean(A)/Full(B) × LogisticRegression/RandomForest/XGBoost/LightGBM 12개 조합 비교, SHAP 분석, 최종 모델 확정 | [phase4_modeling.md](docs/phase4_modeling.md) |
| 5. 서빙 | FastAPI(`/predict`, `/predict/live`) + Docker 패키징(238MB) | [phase5_api_spec.md](docs/phase5_api_spec.md) · [phase5_serving.md](docs/phase5_serving.md) · [phase5_docker.md](docs/phase5_docker.md) |
| 6. 배포 | AWS EC2(t3.micro, 프리티어) 배포, 퍼블릭 엔드포인트 실측 검증 후 인스턴스 stop | [phase6_aws_deploy.md](docs/phase6_aws_deploy.md) |
| 7. 모니터링 | Streamlit 대시보드 — PSI/KS drift 지표, 무작위/synthetic 배치 시뮬레이션, held-out AUC 추적 | [phase7_monitoring.md](docs/phase7_monitoring.md) |

## 최종 모델

**Lean(A) + LightGBM** — 검증 AUC **0.7825** (80/20 stratified split, Phase 4)

- App-only(0.7607) → Lean(A) 신용이력 추가(**0.7825**, +0.02) → Full(B) 전체 통계량(0.7799, 추가 개선 없음)
- SHAP 분석: `EXT_SOURCE_1/2/3`(외부 신용점수)가 최상위 3개 feature. 직접 설계한 `bureau_debt_credit_ratio`, `inst_late_frac_mean`, `ccb_utilization_mean_mean` 등 파생 feature도 상위 20개 중 7개를 차지
- **해석 가능성과 성능을 모두 고려해 Lean(A)를 최종 채택** — Full(B) 대비 컬럼 수 2.4배 적음에도 성능 손실이 없어, 애초 AMEX→Home Credit 전환 이유(해석 가능성)와 성능을 동시에 만족

## 기술 스택

Python · DuckDB(대용량 원본 처리) · pandas/scikit-learn · LightGBM/XGBoost · SHAP(모델 해석) · FastAPI(서빙) · Docker · AWS EC2(배포) · Streamlit(모니터링)

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
| `POST /predict` | **기존 학습 데이터(application_train/test)에 있던 고객 조회용** — SK_ID_CURR으로 사전계산된 feature를 조회해 빠르게 예측. `PUBLIC_DEPLOYMENT=true`(공개 배포 시) 환경변수로 비활성화 가능 |
| `POST /predict/live` | **신규 고객(학습 데이터에 없는 고객)을 위한 실시간 집계 데모용** — 원본 필드(application + 선택적 bureau/previous_application 이력)를 입력받아 그 자리에서 배치 파이프라인과 동일한 로직으로 Lean(A) feature를 계산한 뒤 예측 |

두 엔드포인트로 나뉜 이유: `/predict`는 이미 알고 있는 고객을 빠르게 조회하는 용도이고, `/predict/live`는 실제 서비스에서 마주치는 "한 번도 본 적 없는 신규 신청자"를 심사하는 시나리오를 보여주기 위한 것입니다. `/predict`는 라이선스가 제한적인 원본 데이터의 개별 고객 값을 그대로 노출할 수 있어, 공개 배포 시(Phase 6, AWS EC2) `PUBLIC_DEPLOYMENT=true`로 비활성화했습니다.

### ⚠️ 성능 지표 관련 주의사항

- API가 참조하는 **검증 AUC 0.7825**는 [Phase 4](docs/phase4_modeling.md)의 80/20 stratified split 기준 결과입니다.
- 실제 서빙에 쓰이는 모델(`models/lean_a_lightgbm_v1.joblib`)은 **전체 application_train(100%)으로 재학습**되어 Phase 4 검증 모델과 학습 데이터 양이 다릅니다.
- 따라서 **이 서빙 모델 자체의 held-out 성능은 별도로 측정되지 않았습니다** — 0.7825는 "이 정도 성능을 내는 방법론으로 학습했다"는 근거로 인용하는 것이며, 서빙 모델의 정확한 성능 보증치가 아닙니다.

상세 구현 노트는 [docs/phase5_serving.md](docs/phase5_serving.md) 참고.

## 모니터링 대시보드 실행

```bash
python3 scripts/train_monitoring_model.py   # held-out 모델 학습 (최초 1회)
streamlit run dashboard/monitoring_dashboard.py
```

실제 운영 로그가 없어 `application_train`을 배치로 나눠 "시간에 따라 데이터가 들어온다"를 시뮬레이션합니다. 무작위 배치(정상 상태 대조군)와 의도적 드리프트 주입(synthetic, 라벨 명시) 두 모드를 토글로 제공하고, PSI/KS 기반 drift 지표와 배치별 실제 AUC를 추적합니다. 상세는 [docs/phase7_monitoring.md](docs/phase7_monitoring.md) 참고.

## 데이터 및 라이선스 안내

Kaggle "Home Credit Default Risk"(2018) 데이터를 사용했습니다. 대회 규정(Competition Rules)상 데이터를 "대회 목적 외로 사용하지 말 것", "팀 외부 비공개 공유 금지" 조항이 있어(자세한 확인 경위는 [phase1_data_validation.md](docs/phase1_data_validation.md) 참고), **이 저장소에는 원본 CSV·고객 단위 원본 데이터를 포함하지 않습니다**(`.gitignore`로 `data/` 전체 제외). 공개하는 것은 코드·집계 결과·모델 평가·문서뿐이며, 배포된 API(Phase 6)에서도 개별 고객 데이터를 조회할 수 있는 `/predict`는 비활성화되어 있습니다. 데이터를 직접 사용하려면 [Kaggle 대회 페이지](https://www.kaggle.com/competitions/home-credit-default-risk)에서 규정에 동의한 뒤 내려받아 `data/raw/`에 넣으면 됩니다.
