# Feature Engineering — Option A (Lean, 해석 중심)

Phase 1 검증 이후 곧바로 진행 (EDA를 위한 별도 Phase 2 문서는 아직 없음 — 필요 시 추후 보강).
집계 방식은 3가지 후보(A 단독 Lean / B 단독 Full / **C: A를 메인 + B를 벤치마크 비교**) 중 C로 진행, 이 문서는 그중 **A(Lean)** 구현.

스크립트: [`scripts/build_features_leanA.py`](../scripts/build_features_leanA.py)

## 조인/집계 순서 (사용자 확정)

```
bureau_balance ──(SK_ID_BUREAU 단위 집계)──▶ bb_agg
bureau + bb_agg ──(SK_ID_CURR 단위 집계)──▶ bureau_agg
credit_card_balance ──(SK_ID_PREV 단위 집계)──▶ ccb_agg  ┐
POS_CASH_balance ──(SK_ID_PREV 단위 집계)──▶ pos_agg      ├─▶ previous_application + 이 3개
installments_payments ──(SK_ID_PREV 단위 집계)──▶ inst_agg ┘   ──(SK_ID_CURR 단위 집계)──▶ prev_agg
application_train/test ──(전처리: DAYS_EMPLOYED anomaly 처리)──▶ application_clean
application_clean + bureau_agg + prev_agg ──(SK_ID_CURR join)──▶ train/test_features_leanA
```

**전처리 (Phase 2 EDA에서 발견 후 반영, 2026-08-22)**: `DAYS_EMPLOYED == 365243`(은퇴자/무직을 나타내는 placeholder, 전체 18%)을 `NULL`로 치환하고 `DAYS_EMPLOYED_ANOMALY` 플래그를 추가 — [`scripts/_preprocessing.py`](../scripts/_preprocessing.py)로 분리해 Option B에서도 동일하게 재사용.

## 선정한 Lean feature 목록 (블록별 핵심 지표만)

### bureau_balance → bureau (SK_ID_BUREAU 단위, 4개)
`bb_n_months`(관측 개월 수), `bb_dpd_ever_frac`(연체 상태였던 개월 비율), `bb_status_last`(최근 상태), `bb_max_dpd_severity`(최대 연체 심각도 0~5)

### bureau(+bb) → SK_ID_CURR (12개)
`bureau_count`, `bureau_active_ratio`, `bureau_days_credit_mean`, `bureau_overdue_ratio`, `bureau_amt_credit_sum_total`, `bureau_amt_credit_sum_debt_total`, `bureau_amt_credit_sum_overdue_total`, `bureau_debt_credit_ratio`(총부채/총신용, 핵심 도메인 지표), `bureau_amt_annuity_mean`, `bureau_credit_type_nunique`, `bureau_bb_dpd_ever_frac_mean`, `bureau_bb_max_dpd_severity_max`

### credit_card_balance / POS_CASH_balance / installments_payments → SK_ID_PREV
- ccb(6개): 개월 수, 잔액 평균, 한도 평균, DPD 최대, DPD 발생 비율, **이용률 평균**(`AMT_BALANCE/AMT_CREDIT_LIMIT_ACTUAL`, 신용평가 핵심 지표)
- pos(5개): 개월 수, 할부 건수 평균, DPD 최대, DPD 발생 비율, 완납 비율
- inst(5개): 납부 건수, 총 납부액, **연체 납부 비율**, 평균 연체일수, **납부비율 평균**(`AMT_PAYMENT/AMT_INSTALMENT`, 과소/과다납부 신호)

### previous_application(+위 3개) → SK_ID_CURR (26개)
자체 지표 10개(신청 건수, 승인/거절 비율, 신청·승인 금액 평균, 연금 평균, 선수금 평균, 최근성, 만기 시점, 평균 상환기간) + 위 3개 블록을 다시 SK_ID_CURR로 평균/최대 집계한 16개

### 최종 결합 (application_train/test 기준)
원본 application 컬럼(122/121개, `DAYS_EMPLOYED` 전처리 반영) + `DAYS_EMPLOYED_ANOMALY`(1개) + `has_bureau_record`/`has_previous_application`(커버리지 플래그 2개) + bureau 블록 12개 + previous_application 블록 26개

## 결과

| | shape |
|---|---|
| `data/processed/train_features_leanA.parquet` | 307,511행 × **163컬럼** |
| `data/processed/test_features_leanA.parquet` | 48,744행 × **162컬럼** (TARGET 없음) |

애초 "+50~90 feature" 예상 범위보다 적은 **+41 feature**(163−122)로 나왔음 — "해석 중심"이라는 목표에 맞춰 테이블당 정말 핵심적인 지표만 선별한 결과. 필요하면 이후 몇 개 더 추가할 수 있음(사용자 확인 필요).

**정합성 체크**:
- `has_bureau_record=True` 비율 85.7%, `has_previous_application=True` 비율 94.6% — 상식적인 범위(모든 고객이 과거 신용/대출 이력이 있는 건 아님)
- `has_bureau_record=False`인데 `bureau_count`가 채워진 행: **0건** (플래그 로직 정합성 확인)
- `ccb_utilization_mean_mean`이 다수 고객에서 NaN — 신용카드 상품을 이용한 적 없는 고객이 많다는 뜻으로 도메인상 자연스러움 (LightGBM 등 트리 모델은 NaN 네이티브 처리)

## 메모리 실측

| | 값 |
|---|---|
| 시작 시점 여유 | 65MB |
| **peak RSS** | **933MB** (DAYS_EMPLOYED 전처리 반영 재빌드 기준) |
| swap | 변화 없음 |

`bureau_balance`(2,730만 행), `installments_payments`(1,360만 행) 등 대용량 테이블을 여러 단계로 나눠(중간 결과 parquet 저장) 처리한 덕분에, 이전 AMEX 프로젝트의 744개 컬럼 집계 사례(1GB 한도에서 OOM 났던 것)와 달리 이번엔 한 번의 OOM 없이 안정적으로 완료됨.

## 다음
- Option B(Full, 전체 통계량) 벤치마크 구현 → A vs B 성능 비교
- Phase 2 EDA는 아직 별도로 안 함 — 필요 시 진행 여부 확인
