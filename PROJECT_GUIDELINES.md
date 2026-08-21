# PROJECT_GUIDELINES.md

## 1. 프로젝트명
카드사 채무불이행(연체) 예측 — American Express Default Prediction 데이터 기반

## 2. 목적
삼성카드 데이터분석 직무(신용관리 영역) 지원을 위한 포트폴리오 프로젝트.
실제 신용카드사(American Express)의 익명화된 고객 결제 데이터를 기반으로,
카드 대금 연체(채무불이행) 가능성을 예측하는 모델을 구축한다.

## 3. 데이터
- 출처: Kaggle "American Express - Default Prediction" (2022, CC0 Public Domain)
- 원본: train_data.parquet(고객 190개 집계 feature × 13개월 시계열), train_labels.csv(정답 라벨)
- 압축본 사용: 커뮤니티 제공 Parquet 압축 버전(원본 16GB → 수GB대)
- 용량 문제로 customer_id 일부 샘플링 후 로컬 반입 예정 — 샘플링 방식/규모는 Phase 1에서 결정

## 4. 운영 원칙 (CRM 프로젝트 workflow 이식)
- **임의 확정 금지**: 데이터 프로파일링 전에는 주제·가설·전처리 방향·모델 종류 등을 임의로 확정하지 않는다.
- **중요 결정은 후보 제시 후 사용자가 선택**: 여러 선택지와 장단점을 제시하고, 최종 선택은 사용자가 한다.
- **Phase 단위 진행**: Phase마다 작업을 끊고, 매 Phase 종료 시 커밋/push하며 중간 결과·diff를 사용자에게 검토받는다. 사용자 검토 없이 다음 Phase로 넘어가지 않는다.
- **판단 필요 이슈 처리 방식**: 구조적 중단 조건이 아닌 전처리/정제성 이슈는 즉시 멈추지 않고 합리적 기본값으로 처리한 뒤 `docs/decisions_pending_review.md`에 계속 기록하고, 나중에 한 번에 몰아서 검토한다. 단, 이후 단계 성립 여부에 직결되는 중대한 결정은 즉시 확인받는다.
- **데이터 누수 방지**: 예측 시점(카드 대금 청구 시점) 이후에 발생하는 정보는 feature에서 제외한다.
- **공개 범위**: 원본 대용량 데이터·고객별 원본 ID는 GitHub에 공개하지 않는다. 코드/집계결과/모델평가/문서만 공개한다.

## 5. 기술 스택 (예정)
Python, Pandas/Polars, DuckDB 또는 Parquet 직접 처리, scikit-learn/XGBoost/LightGBM,
SHAP, FastAPI(서빙), Docker(패키징), pytest

## 6. Phase 로드맵 (초안 — Phase 1 진행 후 조정)
- Phase 1: 원본 데이터 검증 및 적합성 확인, customer_id 샘플링 전략 결정
- Phase 2: EDA (분포, 결측치 패턴, 클래스 불균형 확인)
- Phase 3: Feature Engineering (시계열 집계, 도메인 기반 파생변수)
- Phase 4: 모델링 및 비교 (여러 모델 + SHAP 해석)
- Phase 5: FastAPI 서빙 + Docker 패키징
- Phase 6: Render 1차 배포 → AWS(ECS Fargate 또는 App Runner) 최종 배포
- Phase 7: 모니터링 대시보드 (예측 분포·드리프트 추적)
- Phase 8: 문서화 및 GitHub 포트폴리오 정리

## 7. 현재 상태
Phase 1 시작 전 — 원본 데이터(`data/raw/train_data.parquet`, `data/raw/train_labels.csv`) 반입 완료, 검증/샘플링 전략 결정 대기 중
