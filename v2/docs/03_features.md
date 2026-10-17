# 가설 검증용 변수 정의 (3단계)

연체 위험 기반 대출 승인 기준 설계 (Loan Approval Risk Scoring) — v2 재분석

재현 코드: [`v2/scripts/04_build_hypothesis_features.py`](../scripts/04_build_hypothesis_features.py) · 산출물: `v2/data/features/hypothesis_features.parquet` (307,511행 x 140열, 데이터 파일은 커밋하지 않음)

> 신청자 1명(SK_ID_CURR) 당 1행. 이력이 없는 신청자는 관련 변수를 **NULL로 둔다**(0으로 채우지 않는다) — "이력 없음"과 "이력은 있는데 0%로 양호함"은 다른 의미이기 때문이다. 결측률은 307,511명 전체 기준이다.

---

## 연결 경로 원칙

[`01_data_audit.md`](01_data_audit.md)의 "수정 기록"·"연결 경로 원칙"에 따라, 하위 테이블은 진짜 고아(상위 키가 없는 행)를 제외한 뒤 **각 테이블이 자체 보유한 SK_ID_CURR**로 신청자에 직접 연결했다. installments_payments/POS_CASH_balance/credit_card_balance는 모두 SK_ID_CURR을 자체 보유하므로 previous_application을 거치지 않았다. bureau_balance만 SK_ID_CURR이 없어 bureau를 거쳐 연결했다.

## 제외·특수값 처리

* **완전 제외** (가설 검증·모델 어디에도 쓰지 않음): `CODE_GENDER`, `OBS_30_CNT_SOCIAL_CIRCLE`, `DEF_30_CNT_SOCIAL_CIRCLE`, `OBS_60_CNT_SOCIAL_CIRCLE`, `DEF_60_CNT_SOCIAL_CIRCLE` — 차별 소지가 있어 실무 심사에서 쓰지 않는 정보.
* **민감 변수 표시만**: `DAYS_BIRTH`(나이, `age_years`로 변환) — IV는 참고용으로만 계산하고 가설 판정에는 쓰지 않는다.
* **누수 방지**: previous_application의 `DAYS_LAST_DUE_1ST_VERSION`/`DAYS_LAST_DUE`/`DAYS_TERMINATION`은 변수 생성에 쓰지 않았다. 시간창(최근 1년 등) 계산은 0 이하 DAYS_* 값만 사용했다.
* **365243 특수값**: `DAYS_EMPLOYED=365243`은 NULL로 바꾸고 `unemployed_flag=1`을 부여했다(미고용/연금수령자로 해석).
* **XNA/Unknown**: `ORGANIZATION_TYPE='XNA'`, `NAME_FAMILY_STATUS='Unknown'`은 NULL로 처리했다.

---

## H1. 상환 행동 변수

| 변수명 | 정의 | 원천 테이블 | 결측률 |
|---|---|---|---|
| **late_payment_ratio** (핵심) | 분할상환 회차 중 실제 납부일(DAYS_ENTRY_PAYMENT)이 예정일(DAYS_INSTALMENT)보다 늦은 회차의 비율 | installments_payments | 5.89% |
| underpay_ratio (보조) | 실제 납부액(AMT_PAYMENT)이 예정액(AMT_INSTALMENT)보다 적은 회차의 비율 | installments_payments | 5.89% |
| avg_delay_days (보조) | 지연된 회차만 대상으로 한 평균 지연일수(납부일−예정일) | installments_payments | 51.17%(지연 회차가 아예 없는 신청자는 NULL) |
| recent_1yr_late_ratio (보조) | 최근 1년(DAYS_INSTALMENT≥-365) 회차 중 지연 비율 | installments_payments | 29.98%(최근 1년 내 회차가 없는 신청자는 NULL) |
| bureau_currently_overdue_flag (보조) | 타 금융기관 신용 중 CREDIT_DAY_OVERDUE>0 또는 AMT_CREDIT_SUM_OVERDUE>0인 기록 보유 여부(1/0) | bureau | 14.32% |
| bureau_max_overdue_amt (보조) | 타 금융기관 신용의 과거 최대 연체금액(AMT_CREDIT_MAX_OVERDUE) 최댓값 | bureau | 40.20% |
| bureau_balance_delinquent_month_ratio (보조) | bureau_balance에서 연체 상태(STATUS 1~5)인 월의 비율 | bureau_balance(→bureau 경유) | 70.01% |
| pos_dpd_month_ratio (보조) | POS/현금대출 월별 기록 중 SK_DPD>0인 월의 비율 | POS_CASH_balance | 6.68% |
| cc_dpd_month_ratio (보조) | 카드 월별 기록 중 SK_DPD>0인 월의 비율 | credit_card_balance | 74.66% |

## H2. 상환 부담 변수

| 변수명 | 정의 | 원천 테이블 | 결측률 |
|---|---|---|---|
| **annuity_to_income** (핵심) | AMT_ANNUITY ÷ AMT_INCOME_TOTAL | application_train | 0.004% |
| credit_to_income (보조) | AMT_CREDIT ÷ AMT_INCOME_TOTAL | application_train | 0.0% |
| active_loan_count (보조) | 타 금융기관 활성 대출 수(CREDIT_ACTIVE='Active') | bureau | 14.32% |
| debt_to_income (보조) | 활성 대출 부채 합(AMT_CREDIT_SUM_DEBT, Active만) ÷ AMT_INCOME_TOTAL | bureau + application_train | 14.96% |
| card_utilization (보조) | 카드별 최근 스냅샷(월 기준 최신) 잔액 합 ÷ 한도 합 | credit_card_balance | 79.96% |

## H3. 자금 압박 변수

| 변수명 | 정의 | 원천 테이블 | 결측률 |
|---|---|---|---|
| **reject_ratio** (핵심) | 과거 자사 신청 중 거절(NAME_CONTRACT_STATUS='Refused') 비율 | previous_application | 5.35% |
| recent_1yr_reject_count (보조) | 최근 1년(DAYS_DECISION≥-365) 거절 건수 | previous_application | 5.35% |
| recent_1yr_apply_count (보조) | 최근 1년 신청 건수 | previous_application | 5.35% |
| total_credit_bureau_inquiries (보조) | AMT_REQ_CREDIT_BUREAU_{HOUR,DAY,WEEK,MON,QRT,YEAR} 합계(서로 겹치지 않는 시간창이므로 합산이 "최근 1년 내외" 총 조회 횟수의 근사치) | application_train | 13.50% |
| bureau_recent_1yr_new_loans (보조) | 최근 1년(DAYS_CREDIT≥-365) 타 금융기관 신규 개설 대출 수 | bureau | 14.32% |

## H4. 생활 안정성 변수

| 변수명 | 정의 | 원천 테이블 | 결측률 |
|---|---|---|---|
| **employment_days** (핵심) | 재직 기간(-DAYS_EMPLOYED), 365243은 NULL + unemployed_flag=1 | application_train | 18.01% |
| registration_days (보조) | 주소 등록 경과일(-DAYS_REGISTRATION) | application_train | 0.0% |
| id_publish_days (보조) | 신분증 발급 경과일(-DAYS_ID_PUBLISH) | application_train | 0.0% |
| phone_change_days (보조) | 전화번호 변경 경과일(-DAYS_LAST_PHONE_CHANGE) | application_train | 0.0% |
| unemployed_flag (보조) | DAYS_EMPLOYED=365243 여부(1/0) — 무직/연금수령자 추정 | application_train | 0.0% |

## H5. 대출 조건 변수

| 변수명 | 정의 | 원천 테이블 | 결측률 |
|---|---|---|---|
| **credit_to_goods** (핵심) | AMT_CREDIT ÷ AMT_GOODS_PRICE | application_train | 0.09%(리볼빙 등 AMT_GOODS_PRICE 없는 상품 포함) |
| credit_to_annuity (보조) | AMT_CREDIT ÷ AMT_ANNUITY (상환 회차 수의 대용) | application_train | 0.004% |
| NAME_CONTRACT_TYPE (보조) | 대출 종류(Cash loans / Revolving loans) | application_train | 0.0% |

## 참고 변수 (가설 판정에 쓰지 않음)

| 변수명 | 정의 | 원천 테이블 | 결측률 |
|---|---|---|---|
| EXT_SOURCE_1 | 외부 신용점수 1 | application_train | 56.38% |
| EXT_SOURCE_2 | 외부 신용점수 2 | application_train | 0.22% |
| EXT_SOURCE_3 | 외부 신용점수 3 | application_train | 19.83% |
| ext_source_mean | EXT_SOURCE_1/2/3 중 결측이 아닌 값들의 평균 | application_train | 0.06%(셋 다 결측인 경우만 NULL) |
| age_years | 나이(-DAYS_BIRTH/365.25) — 민감 변수, IV는 참고용 | application_train | 0.0% |

## 이력 존재 플래그

| 변수명 | 정의 | 결측률 |
|---|---|---|
| no_history_at_all_flag | bureau·previous_application 이력이 모두 없는 신청자(1=이력 전무) | 0.0% (2,470명이 1, 01_data_audit.md 3절과 일치) |
| n_bureau_records / n_bureau_balance_records / n_prev_records / n_installment_records / n_pos_records / n_cc_records | 각 하위 테이블의 신청자별 레코드 수(이력 보유 여부 판정용) | 각 14.32% / 70.01% / 5.35% / 5.89% / 6.68% / 74.66% |

---

## 부록: 나머지 application_train 컬럼 (IV만 일괄 계산)

위 H1~H5 핵심/보조/참고 변수에 쓰이지 않은 application_train의 나머지 96개 컬럼(주택 건물 정보 47개, 문서제출 플래그 27개, 거주지·지역 10개 등)은 원본 그대로 특징 테이블에 포함했고, `v2/docs/04_signal_hypotheses.md`의 부록 표에서 IV만 일괄 계산한다. 전체 목록은 [`feature_build_log.json`](feature_build_log.json)의 `remainder_appendix_columns`에 있다.

---

## 특징 테이블 요약

* 파일: `v2/data/features/hypothesis_features.parquet` (커밋하지 않음, `.gitignore`의 `data/`·`*.parquet` 규칙으로 자동 제외)
* 행: 307,511 (application_train 전체) · 열: 140
* 재현: `python3 -I v2/scripts/04_build_hypothesis_features.py`
