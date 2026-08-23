# Phase 5: FastAPI 서빙 + Docker 패키징 — 계획 (착수 전, 확인 필요)

최종 확정 모델: **Lean(A) + LightGBM (AUC 0.7825)**. 이 문서는 실제 구현 전 설계 후보를 정리한 것 — PROJECT_GUIDELINES.md §4 원칙에 따라 중요 결정은 후보만 제시하고 착수하지 않음.

## 1. 구현 범위 (제안)

1. 모델 아티팩트 저장 (LightGBM 모델 + 전처리/컬럼 스키마)
2. FastAPI 앱: `/health`, `/predict`, `/model/info` 엔드포인트
3. pydantic 요청/응답 스키마 + 입력 검증
4. pytest로 API 테스트
5. Dockerfile로 패키징
6. (선택) 예측과 함께 로컬 SHAP 설명 반환

## 2. 확인이 필요한 결정 사항

### 2.1 추론 시 feature를 어떻게 확보할지 (가장 중요한 결정)

Lean(A)는 `application` + `bureau`/`previous_application` 집계로 만든 163개 feature라, 실시간 서빙에서 "새 대출 신청자"에 대해 이 feature들을 어떻게 채울지가 핵심 설계 포인트.

| 후보 | 방식 | 장점 | 단점 |
|---|---|---|---|
| **A. SK_ID_CURR 조회형** | `test_features_leanA.parquet`(이미 생성됨)에서 SK_ID_CURR로 미리 계산된 feature를 조회 | 구현 간단, 이미 데이터 있음, 빠름 | "실시간 신규 고객 심사"라는 실제 시나리오와는 거리가 있음(이미 아는 고객만 조회 가능) |
| **B. Raw feature 직접 입력형** | API가 163개 feature 값을 그대로 요청 바디로 받음 | 실시간성 있음, 데이터 소스 의존성 없음 | 클라이언트가 163개 값을 다 채워야 해서 비현실적, "raw 데이터로 채점"이라는 포트폴리오 스토리와 안 맞음 |
| **C. 원본 데이터로 실시간 집계형** | SK_ID_CURR 또는 신규 신청자의 raw 필드 + 관련 bureau/previous_application 레코드를 받아 DuckDB로 그 자리에서 Lean(A) 집계 로직을 실행 | 가장 "실제 서비스"에 가까움, Phase 3 파이프라인 코드를 재사용해 일관성 있음 | 구현 복잡도 가장 높음(API 요청 스펙 설계, 집계 쿼리를 요청 단위로 재사용 가능하게 리팩터링 필요) |

**제안**: **A(SK_ID_CURR 조회형)를 1차로 구현**하고, 포트폴리오 완성도를 위해 여유 있으면 **C를 데모용 보조 엔드포인트**로 추가(예: `/predict/live`에 SK_ID_CURR + 원본 필드 일부를 받아 실제 파이프라인 재사용). B는 권장하지 않음.

### 2.2 서빙용 모델을 어떻게 학습할지

Phase 4에서 쓴 모델은 train의 80%로만 학습(20%는 검증용). 서빙 직전에는 관례적으로 **전체 application_train(100%)으로 재학습**해서 마지막 성능까지 짜내는 게 일반적.

- **제안**: 서빙용 모델은 전체 train으로 재학습, 다만 "검증된 AUC 0.7825"는 80/20 split 결과를 근거로 계속 인용(재학습 모델은 held-out 검증 세트가 없어 AUC를 다시 잴 수 없음 — 이 점을 README/API 문서에 명시)

### 2.3 예측 응답에 SHAP 로컬 설명을 포함할지

- **포함 시 장점**: "왜 이 고객이 고위험으로 분류됐는지" 상위 요인을 응답에 같이 줄 수 있음 — 신용관리 직무 포트폴리오로서 설명가능성(explainability)을 보여주는 강력한 차별점. 단, 요청마다 SHAP 계산이 들어가면 응답 속도가 느려짐(LightGBM TreeExplainer는 빠른 편이라 실사용엔 큰 무리 없을 것으로 예상)
- **제안**: 기본 `/predict` 응답에 상위 5개 SHAP 요인(변수명+기여방향)을 포함

### 2.4 배포 목표 (참고, PROJECT_GUIDELINES 로드맵 §6 그대로)

Phase 5는 FastAPI+Docker까지, 실제 배포(Render→AWS)는 Phase 6에서 별도 진행.

## 3. 다음

위 2.1~2.3 결정해주시면 구현 시작하겠습니다.
