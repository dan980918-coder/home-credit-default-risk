# PROJECT_GUIDELINES.md

## 1. 프로젝트명
대출 채무불이행(연체) 예측 — Home Credit Default Risk 데이터 기반

## 2. 목적
삼성카드 데이터분석 직무(신용관리 영역) 지원을 위한 포트폴리오 프로젝트.
Home Credit Group의 대출 신청/상환 이력 데이터를 기반으로, 대출 채무불이행
가능성을 예측하는 모델을 구축한다. (2026-08-22: 기존 AMEX 카드 데이터 기반
프로젝트에서 전환 — 해석 가능한 feature 구조가 필요해 다중 테이블(관계형)
구조의 Home Credit 데이터로 변경. 이전 진행 내역은 `archive/amex/`에 보존.)

## 3. 데이터
- 출처: Kaggle "Home Credit Default Risk" (2018)
- **라이선스 확인 완료 (2026-08-22, Phase 1)** — AMEX(CC0)와 달리 **제한적**:
  - Kaggle Data 탭의 License 필드: **"Subject to Competition Rules"** (별도 오픈 라이선스 없음)
  - Competition Rules 원문(발췌): *"After your acceptance of these Rules, you may access and use the Competition Data only for the purposes of the Competition."* — 대회 목적 외 사용을 명시적으로 제한하는 조항
  - *"No private sharing outside teams — Privately sharing code or data outside of teams is not permitted."*
  - **사용자 결정 (2026-08-22)**: 기존 §4 공개 범위 원칙(원본 CSV 비공개, 코드/집계결과/문서만 공개) **그대로 유지**. 근거: (1) 이 데이터로 코드/분석 결과를 공개하는 포트폴리오·블로그 사례가 Kaggle Notebooks 등에 이미 다수 존재해 관행적으로 통용됨, (2) 원본 데이터 자체를 재배포하는 것이 규정상 가장 문제 소지가 큰 행위이므로 이것만 확실히 피하면(=원본 CSV·원본 고객 단위 데이터를 GitHub에 올리지 않음) 실질적 리스크가 낮다고 판단
- 다중 테이블(관계형) 구조 — 단일 파일이 아니라 8개 CSV가 `SK_ID_CURR`(고객·신청 단위 키) 중심으로 연결됨:

  | 테이블 | 내용 | 키 |
  |---|---|---|
  | `application_train.csv` | 대출 신청 정보 + 정답 라벨(`TARGET`) | `SK_ID_CURR` (PK) |
  | `application_test.csv` | 대출 신청 정보 (라벨 없음) | `SK_ID_CURR` (PK) |
  | `bureau.csv` | 타 금융기관에 보고된 과거/현재 신용 이력 | `SK_ID_CURR` → 연결, `SK_ID_BUREAU` (PK) |
  | `bureau_balance.csv` | `bureau`의 월별 잔액 스냅샷 | `SK_ID_BUREAU` → 연결 |
  | `previous_application.csv` | Home Credit 자체 과거 대출 신청 이력 | `SK_ID_CURR` → 연결, `SK_ID_PREV` (PK) |
  | `credit_card_balance.csv` | 과거 Home Credit 신용카드의 월별 잔액 | `SK_ID_PREV` → 연결 |
  | `POS_CASH_balance.csv` | 과거 POS/현금 대출의 월별 상태 | `SK_ID_PREV` → 연결 |
  | `installments_payments.csv` | 과거 대출 상환 이력(예정 대비 실제) | `SK_ID_PREV` → 연결 |

  조인 구조 요약: `application_train/test`(SK_ID_CURR 기준) ← `bureau`(SK_ID_CURR) ← `bureau_balance`(SK_ID_BUREAU) / `application_train/test` ← `previous_application`(SK_ID_CURR, SK_ID_PREV 발급) ← `credit_card_balance`·`POS_CASH_balance`·`installments_payments`(SK_ID_PREV 기준). 즉 SK_ID_CURR이 최상위 키, SK_ID_PREV/SK_ID_BUREAU는 하위 이력 테이블을 연결하는 중간 키.

- `data/raw/`에 8개 CSV 반입 예정 (반입 후 Phase 1에서 스키마·용량·조인 무결성 검증)

## 4. 운영 원칙 (CRM 프로젝트 workflow 이식)
- **임의 확정 금지**: 데이터 프로파일링 전에는 주제·가설·전처리 방향·모델 종류 등을 임의로 확정하지 않는다.
- **중요 결정은 후보 제시 후 사용자가 선택**: 여러 선택지와 장단점을 제시하고, 최종 선택은 사용자가 한다.
- **Phase 단위 진행**: Phase마다 작업을 끊고, 매 Phase 종료 시 커밋/push하며 중간 결과·diff를 사용자에게 검토받는다. 사용자 검토 없이 다음 Phase로 넘어가지 않는다.
- **판단 필요 이슈 처리 방식**: 구조적 중단 조건이 아닌 전처리/정제성 이슈는 즉시 멈추지 않고 합리적 기본값으로 처리한 뒤 `docs/decisions_pending_review.md`에 계속 기록하고, 나중에 한 번에 몰아서 검토한다. 단, 이후 단계 성립 여부에 직결되는 중대한 결정은 즉시 확인받는다.
- **데이터 누수 방지**: 예측 시점(대출 심사 시점) 이후에 발생하는 정보는 feature에서 제외한다.
- **공개 범위**: 원본 대용량 데이터·고객별 원본 ID는 GitHub에 공개하지 않는다. 코드/집계결과/모델평가/문서만 공개한다. (§3의 라이선스 재확인 결과에 따라 추가 제약이 생길 수 있음)

## 5. 기술 스택 (예정)
Python, Pandas/Polars, DuckDB 또는 Parquet 직접 처리, scikit-learn/XGBoost/LightGBM,
SHAP, FastAPI(서빙), Docker(패키징), pytest

## 6. Phase 로드맵 (초안 — Phase 1 진행 후 조정)
- Phase 1: 원본 데이터 검증(8개 테이블 스키마/용량/조인 무결성), 라이선스 확인, 필요시 샘플링 전략 결정
- Phase 2: EDA (분포, 결측치 패턴, 클래스 불균형, 테이블 간 관계 확인)
- Phase 3: Feature Engineering (다중 테이블 집계, 도메인 기반 파생변수)
- Phase 4: 모델링 및 비교 (여러 모델 + SHAP 해석)
- Phase 5: FastAPI 서빙 + Docker 패키징
- Phase 6: Render 1차 배포 → AWS(ECS Fargate 또는 App Runner) 최종 배포
- Phase 7: 모니터링 대시보드 (예측 분포·드리프트 추적)
- Phase 8: 문서화 및 GitHub 포트폴리오 정리

## 7. 현재 상태
Phase 1 시작 전 — 8개 CSV 반입 대기 중. 이전 AMEX 진행 내역은 `archive/amex/`에 보존됨(참고용, 현재 로드맵과 무관).
