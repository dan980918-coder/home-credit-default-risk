# PROJECT_GUIDELINES.md

## 1. 프로젝트명
대출 채무불이행(연체) 예측 — Home Credit Default Risk 데이터 기반

## 2. 목적
Home Credit Group의 대출 신청/상환 이력 데이터를 기반으로, 대출 채무불이행
가능성을 예측하는 모델을 구축했다. (2026-08-22: 기존 AMEX 카드 데이터 기반
프로젝트에서 전환 — 해석 가능한 feature 구조가 필요해 다중 테이블(관계형)
구조의 Home Credit 데이터로 변경. 이전 진행 내역은 `archive/amex/`에 보존.)

## 3. 데이터
- 출처: Kaggle "Home Credit Default Risk" (2018)
- 다중 테이블(관계형) 구조 — 단일 파일이 아니라 8개 CSV가 `SK_ID_CURR`(고객·신청 단위 키) 중심으로 연결됨:

  | 테이블 | 내용 | 행 수 | 컬럼 수 | 키 |
  |---|---|---|---|---|
  | `application_train.csv` | 대출 신청 정보 + 정답 라벨(`TARGET`) | 307,511 | 122 | `SK_ID_CURR` (PK) |
  | `application_test.csv` | 대출 신청 정보 (라벨 없음) | 48,744 | 121 | `SK_ID_CURR` (PK) |
  | `bureau.csv` | 타 금융기관에 보고된 과거/현재 신용 이력 | 1,716,428 | 17 | `SK_ID_CURR` → 연결, `SK_ID_BUREAU` (PK) |
  | `bureau_balance.csv` | `bureau`의 월별 잔액 스냅샷 | 27,299,925 | 3 | `SK_ID_BUREAU` → 연결 |
  | `previous_application.csv` | Home Credit 자체 과거 대출 신청 이력 | 1,670,214 | 37 | `SK_ID_CURR` → 연결, `SK_ID_PREV` (PK) |
  | `credit_card_balance.csv` | 과거 Home Credit 신용카드의 월별 잔액 | 3,840,312 | 23 | `SK_ID_PREV` → 연결 |
  | `POS_CASH_balance.csv` | 과거 POS/현금 대출의 월별 상태 | 10,001,358 | 8 | `SK_ID_PREV` → 연결 |
  | `installments_payments.csv` | 과거 대출 상환 이력(예정 대비 실제) | 13,605,401 | 8 | `SK_ID_PREV` → 연결 |

  조인 구조 요약: `application_train/test`(SK_ID_CURR 기준) ← `bureau`(SK_ID_CURR) ← `bureau_balance`(SK_ID_BUREAU) / `application_train/test` ← `previous_application`(SK_ID_CURR, SK_ID_PREV 발급) ← `credit_card_balance`·`POS_CASH_balance`·`installments_payments`(SK_ID_PREV 기준). 즉 SK_ID_CURR이 최상위 키, SK_ID_PREV/SK_ID_BUREAU는 하위 이력 테이블을 연결하는 중간 키.

- `data/raw/`에 8개 CSV를 반입해 Phase 1에서 스키마·용량·조인 무결성을 검증했다.
- 공개 범위: 원본 대용량 데이터·고객별 원본 ID는 GitHub에 공개하지 않았고, 코드/집계결과/모델평가/문서만 공개했다.

## 4. 기술 스택
Python, Pandas, DuckDB(CSV 스트리밍 처리·집계) + Parquet(중간 산출물 저장),
scikit-learn/XGBoost/LightGBM(모델 비교, 최종 채택: LightGBM), SHAP(모델 해석),
FastAPI(API 서빙) + Docker(패키징), AWS EC2(배포), Streamlit(모니터링 대시보드)

## 5. Phase 진행 경과
- Phase 1: 원본 데이터 검증(8개 테이블 스키마/용량/조인 무결성 확인), 라이선스 확인 완료
- Phase 2: EDA 완료 (분포, 결측치 패턴, 클래스 불균형, 테이블 간 관계 확인)
- Phase 3: Feature Engineering 완료 (다중 테이블 집계, 도메인 기반 파생변수 — Lean(A)/Full(B) 두 버전 비교)
- Phase 4: 모델링 및 비교 완료 (LogisticRegression/RandomForest/XGBoost/LightGBM 비교 + SHAP 해석)
- Phase 5: FastAPI 서빙 + Docker 패키징 완료
- Phase 6: AWS EC2 프리티어 배포 완료 (Render 검토 후 AWS EC2로 전환)
- Phase 7: 모니터링 대시보드 구축 완료 (예측 분포·PSI/KS drift 추적)
- Phase 8: 문서화 및 GitHub 공개 전환 완료

## 6. 현재 상태
**Phase 8(문서화 및 GitHub 포트폴리오 정리) 완료 — 전체 로드맵(Phase 1~8) 종료.** 최종 모델 Lean(A) + LightGBM(검증 AUC 0.7825) 확정, EDA/모델링/SHAP/FastAPI 서빙/Docker/AWS EC2 배포/Streamlit 모니터링까지 전 과정 구현·문서화 완료. README.md 최종본 정리, 계획 문서에 실제 구현 결과로 연결되는 교차 참조 추가, `archive/amex/`에 안내 README 추가. **GitHub 저장소를 공개(public)로 전환**(전체 커밋 히스토리에 원본 데이터·자격증명·대용량 파일이 한 번도 포함된 적 없음을 확인 후 진행) — https://github.com/dan980918-coder/home-credit-default-risk . 이전 AMEX 진행 내역은 `archive/amex/`에 보존됨(참고용, 현재 로드맵과 무관).
