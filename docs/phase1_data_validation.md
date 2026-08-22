# Phase 1: 데이터 검증 결과 (Home Credit Default Risk)

검증 환경: 재부팅 관계없이 여유 메모리 63~212MB대(타이트), DuckDB로 CSV 직접 스캔(pandas 전체 로드 없음)
스크립트: [`scripts/phase1_validate_tables.py`](../scripts/phase1_validate_tables.py)

## 1. 테이블별 로드 확인

| 테이블 | 행 수 | 컬럼 수 | dtype 구성 |
|---|---|---|---|
| application_train | 307,511 | 122 | BIGINT 41 / VARCHAR 15 / DOUBLE 65 / BOOLEAN 1 |
| application_test | 48,744 | 121 (TARGET 없음) | BIGINT 40 / VARCHAR 15 / DOUBLE 65 / BOOLEAN 1 |
| bureau | 1,716,428 | 17 | BIGINT 6 / VARCHAR 3 / DOUBLE 8 |
| bureau_balance | 27,299,925 | 3 | BIGINT 2 / VARCHAR 1 |
| previous_application | 1,670,214 | 37 | BIGINT 6 / VARCHAR 16 / DOUBLE 15 |
| credit_card_balance | 3,840,312 | 23 | BIGINT 7 / DOUBLE 15 / VARCHAR 1 |
| POS_CASH_balance | 10,001,358 | 8 | BIGINT 5 / DOUBLE 2 / VARCHAR 1 |
| installments_payments | 13,605,401 | 8 | BIGINT 3 / DOUBLE 5 |

8개 테이블 전부 정상 로드, 손상 없음. `bureau_balance`(2,730만행), `installments_payments`(1,360만행)가 규모가 큰 테이블.

## 2. application_train SK_ID_CURR 고유 개수

- 총 행 수 307,511 = 고유 SK_ID_CURR 307,511 → **완전 일치, 중복 없음**
- train/test 간 SK_ID_CURR 겹침: **0건** (정상 — 두 세트가 배타적으로 분리됨)

## 3. 조인 무결성 (고아 레코드 확인)

`NOT IN` 서브쿼리의 NULL 함정(NULL이 하나라도 있으면 `NOT IN` 결과가 전부 UNKNOWN 처리되는 SQL 3치 논리 이슈)을 의심해 `LEFT JOIN` 방식으로 교차 검증했고, 두 방식 결과가 동일함을 확인(부모 키에 NULL 없음도 확인). **아래 수치는 실제 데이터 특성**, 쿼리 버그 아님.

| 자식 테이블 | 기준 키 | 부모 테이블 | 고아 행 수 | 비율 |
|---|---|---|---|---|
| bureau | SK_ID_CURR | application_train∪test | 0 | 0% |
| previous_application | SK_ID_CURR | application_train∪test | 0 | 0% |
| **bureau_balance** | SK_ID_BUREAU | bureau | **3,120,184 / 27,299,925** | **11.4%** |
| **credit_card_balance** | SK_ID_PREV | previous_application | **1,082,816 / 3,840,312** | **28.2%** |
| POS_CASH_balance | SK_ID_PREV | previous_application | 340,561 / 10,001,358 | 3.4% |
| installments_payments | SK_ID_PREV | previous_application | 1,250,826 / 13,605,401 | 9.2% |

**해석**:
- SK_ID_CURR 레벨(최상위, application ↔ bureau/previous_application)은 완전히 깨끗함 — 고아 0건
- SK_ID_BUREAU/SK_ID_PREV 레벨(2차 상세 이력 테이블)에서는 상당한 비율의 고아 레코드 발생, 특히 credit_card_balance가 28.2%로 가장 큼
- 이 데이터셋은 공개적으로도 잘 알려진 특성으로, `bureau_balance`/`credit_card_balance`/`POS_CASH_balance`/`installments_payments`가 원본 시스템에서 `bureau.csv`/`previous_application.csv`보다 더 넓은 ID 범위로 별도 추출되어, 일부 SK_ID_BUREAU/SK_ID_PREV가 상위 테이블에 존재하지 않는 것으로 보임(Kaggle 데이터 자체의 알려진 특성으로 보이나, 100% 확정은 아니므로 참고로만 기재)
- **실무적 영향**: 이 고아 레코드들은 SK_ID_CURR(최종 예측 대상 고객)로 연결할 방법이 없으므로, 최종 feature 테이블 구축 시 자연스럽게 제외됨(안전) — 조인 시 INNER/LEFT 여부만 명확히 하면 되고, 데이터 파이프라인이 깨지는 문제는 아님

## 4. 대용량 테이블 로드 시 메모리 실측

| 시점 | 값 |
|---|---|
| 실행 시작 시점 여유 | 63MB (매우 타이트) |
| **peak python RSS** | **307MB** |
| 실행 중 시스템 unused 최저치 | 75MB |
| 실행 후 시스템 unused | 212MB |
| swap 사용량 변화 | 없음 (0 → 0) |

2,730만 행(bureau_balance), 1,360만 행(installments_payments) 등 대용량 CSV를 포함해 8개 테이블 전체 스키마 확인 + 행 수 카운트 + 6개 조인 무결성 체크(LEFT JOIN 포함)를 전부 처리했는데도 peak RSS 307MB로 매우 안정적. DuckDB의 스트리밍 실행 덕분에 CSV 크기(최대 690MB)와 무관하게 메모리 사용이 낮게 유지됨.

## 5. 라이선스 확인 (Kaggle Competition Rules)

**AMEX(CC0)와 달리 제한적 라이선스** — 별도 보고 참고. PROJECT_GUIDELINES.md §3에 반영 완료.

## 다음: 조인/집계 계획 (후보만 제시, 미착수)

별도로 후보안 제시함 — 사용자 결정 대기.
