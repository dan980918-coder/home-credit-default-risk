# 검증 체크리스트

연체 위험 기반 대출 승인 기준 설계 (Loan Approval Risk Scoring) — v2 재분석 1~4단계 직접 검증용

> "실제값", "통과", "메모" 칸은 비워 두었다. 직접 계산·대조한 뒤 채운다. 추적용 신청자 3명과 이력 없는 신청자 1명은 아래 "추적용 신청자" 절에 고정돼 있다(seed=20251017).

## 추적용 신청자 (C절에서 사용)

| SK_ID_CURR | TARGET | previous_application 건수 | installments_payments 건수 |
|---|---|---|---|
| 264637 | 0 | 5 | 24 |
| 315017 | 0 | 5 | 16 |
| 447195 | 0 | 3 | 11 |

이력 없는 신청자(11번 항목용): **SK_ID_CURR = 409473** (TARGET=1)

원본 행 내보내기: `v2/verification/exports/applicant_<ID>_{installments_payments,previous_application,application_row}.csv` (재생성: `python3 -I v2/verification/select_and_export_tracer_applicants.py`)

---

| # | 확인 항목 | 직접 해볼 것(구체적 명령·방법) | 기대값(근거) | 실제값 | 통과 | 메모 |
|---|---|---|---|---|---|---|
| **A. 원천 데이터** |||||||
| 1 | 테이블 행 수 | DuckDB CLI 실행 후: `SELECT COUNT(*) FROM read_csv_auto('data/raw/application_train.csv');` 를 8개 테이블(application_train/test, bureau, bureau_balance, previous_application, POS_CASH_balance, installments_payments, credit_card_balance) 각각에 대해 실행 | application_train 307,511 / application_test 48,744 / bureau 1,716,428 / bureau_balance 27,299,925 / previous_application 1,670,214 / POS_CASH_balance 10,001,358 / installments_payments 13,605,401 / credit_card_balance 3,840,312 (출처: `01_data_audit.md` §1-1) | | | |
| 2 | 기저 연체율 | `SELECT AVG(TARGET) FROM read_csv_auto('data/raw/application_train.csv');` | 0.08073 (8.073%) (출처: `01_data_audit.md` §4) | | | |
| 3 | 특수값 | `SELECT COUNT(*) FROM read_csv_auto('data/raw/application_train.csv') WHERE DAYS_EMPLOYED = 365243;` | 55,374건 (출처: `01_data_audit.md` §5-4) | | | |
| 4 | 고아 비율 | `SELECT COUNT(*) FROM read_csv_auto('data/raw/bureau_balance.csv') bb WHERE bb.SK_ID_BUREAU NOT IN (SELECT SK_ID_BUREAU FROM read_csv_auto('data/raw/bureau.csv'));` 을 전체 행수(27,299,925)로 나눈다 | 3,120,184건 / 27,299,925건 = 11.43% (출처: `01_data_audit.md` "수정 기록"절, `orphan_recheck_results.json`) | | | |
| **B. 분할** |||||||
| 5 | 분할 겹침 | `v2/data/splits/{train,valid,holdout}_ids.csv`를 각각 읽어 SK_ID_CURR 집합의 교집합이 비어 있는지 확인(예: pandas `set(a) & set(b)`) | 세 집합 모두 교집합 0건 (출처: `03_split.py` 44~46행의 assert) | | | |
| 6 | 분할 크기와 연체율 | `train_ids.csv`/`valid_ids.csv`의 행 수와 TARGET 평균을 직접 계산 | 학습 184,506명(8.073%) / 검증 61,502명(8.073%) / 최종평가 61,503명(미저장) (출처: `split_summary.json`) | | | |
| 7 | 최종평가 미사용 | `v2/scripts/01~05` 전체에서 `holdout` 또는 `holdout_ids.csv`라는 문자열을 검색: `grep -rn "holdout" v2/scripts/01_data_audit.py v2/scripts/02_variable_catalog.py v2/scripts/03_split.py v2/scripts/04_build_hypothesis_features.py v2/scripts/05_test_signal_hypotheses.py` | 03_split.py에서 holdout을 "생성"하는 코드만 있고, 04/05번 스크립트에는 holdout_ids.csv를 "읽는" 코드가 전혀 없어야 함 | | | |
| **C. 변수 (신청자 추적)** |||||||
| 8 | 분할상환 지연 비율 (H1 핵심 변수) | `applicant_264637_installments_payments.csv`를 열어 `DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT`인 행 수를 직접 세고 전체 행 수로 나눈다. 315017, 447195도 동일하게 | 264637: late_payment_ratio ≈ 0.0417(24행 중 1행 지연) / 315017: ≈ 0.0625(16행 중 1행) / 447195: 0.0(11행 중 0행) (출처: `hypothesis_features.parquet`, 06_h2_followup 작업 시 재확인 가능) | | | |
| 9 | 과거 신청 거절 비율 (H3 핵심 변수) | `applicant_<ID>_previous_application.csv`에서 `NAME_CONTRACT_STATUS='Refused'`인 행 수를 세고 전체 행 수로 나눈다 | 264637: 0/5=0.0 / 315017: 1/5=0.2 / 447195: 0/3=0.0 | | | |
| 10 | 대출금÷물건가격(H5), 재직기간(H4) | `applicant_<ID>_application_row.csv`에서 `AMT_CREDIT÷AMT_GOODS_PRICE`를 계산하고, `DAYS_EMPLOYED`가 365243이면 NULL 처리 후 `-DAYS_EMPLOYED`로 재직일수 계산 | 264637: credit_to_goods=1,078,200÷900,000=1.198, employment_days=1,183일 / 315017: 315,000÷315,000=1.0, 560일 / 447195: 545,040÷450,000=1.2112, 2,832일 (세 명 모두 365243 아님 — 365243인 경우 NULL+unemployed_flag=1 처리 규칙은 `04_build_hypothesis_features.py` 81~82행 참고) | | | |
| 11 | 이력 없는 신청자 | `hypothesis_features.parquet`(또는 재계산)에서 SK_ID_CURR=409473의 `late_payment_ratio`, `reject_ratio`, `n_installment_records`, `n_prev_records` 값이 0이 아니라 **NULL(NaN)**인지 확인 | 전부 NULL(NaN) — 0이면 불일치 (출처: `03_features.md` "NULL로 둔다" 원칙) | | | |
| **D. 가설 검증 계산** |||||||
| 12 | IV 재계산 | `v2/verification/bins_employment_days.csv`를 스프레드시트로 열어, 구간별 WoE=ln(정상비중÷연체비중), IV=Σ(정상비중−연체비중)×WoE를 계산(각 칸의 n_good/n_bad에 0.5를 더하고, 분모는 전체 n_good/n_bad에 "구간수×0.5"를 더함 — 예: 정상비중 = (n_good+0.5)÷(전체n_good+구간수×0.5)) | H4 핵심변수(employment_days) IV = 0.1130(중간) (출처: `04_signal_hypotheses.md` 판정요약표) | | | |
| 13 | Wilson 신뢰구간 | `bins_employment_days.csv`에서 가장 위험한 구간(bin1: n=15,134, n_bad=1,764)에 대해 Wilson 공식으로 직접 계산: p=n_bad/n, z=1.96, 중심=(p+z²/2n)/(1+z²/n), 반폭=z×sqrt(p(1-p)/n+z²/4n²)/(1+z²/n) | bin1 연체율 95% CI ≈ [11.154%, 12.177%] (출처: `bins_employment_days.csv`의 보고서값 컬럼, `05_test_signal_hypotheses.py` 105~112행 `wilson_ci()`) | | | |
| 14 | 최소 구간 크기 | `hypothesis_results.json`의 5개 핵심변수(late_payment_ratio, annuity_to_income, reject_ratio, employment_days, credit_to_goods) 각각의 `bins` 배열에서 `pct_of_total` 값이 모두 5.0 이상인지 확인(결측 구간 제외하지 않고 전부) | 모든 구간 pct_of_total ≥ 5.0 이어야 함(구간화 규칙, `05_test_signal_hypotheses.py` 141~160행의 병합 로직) | | | |
| **E. 원칙 준수** |||||||
| 15 | 제외 변수 | `v2/docs/03_features.md`와 `v2/docs/feature_build_log.json`의 `excluded_always`에 `CODE_GENDER`, `OBS_30_CNT_SOCIAL_CIRCLE`, `DEF_30_CNT_SOCIAL_CIRCLE`, `OBS_60_CNT_SOCIAL_CIRCLE`, `DEF_60_CNT_SOCIAL_CIRCLE` 5개가 들어 있는지, `hypothesis_features.parquet`의 컬럼 목록에 이 5개가 없는지 확인. 시간창 계산은 `04_build_hypothesis_features.py`의 128행(`DAYS_CREDIT >= -365`), 147~148행(`DAYS_INSTALMENT >= -365`) 등에서 `>=` 비교가 0 이하(음수 또는 0) 값만 포함하는 조건인지 코드로 직접 확인 | `feature_build_log.json`의 `excluded_always`에 5개 전부 명시, parquet 컬럼에 없음. 시간창 조건은 전부 `-365` 이상 즉 과거~최근 365일(0 이하)만 포함 | | | |
| **F. 4단계 최종평가** |||||||
| 16 | 승인율 80% 연체율 | `v2/data/predictions/test_scores.parquet`을 CSV로 내보낸 뒤(`python3 -c "import pandas as pd; pd.read_parquet('v2/data/predictions/test_scores.parquet').to_csv('test_scores.csv', index=False)"`), 스프레드시트에서 `new_score` 기준 상위 80%(하위 20% 거절)를 승인으로 두고, 그 승인군의 TARGET 평균을 계산 | 4.610% (출처: `07_final_evaluation.md` §2-1, `final_evaluation_results.json`의 `h6.table`에서 `approval_rate=0.8`) | | | |
| 17 | 스왑셋 네 그룹 | 같은 CSV에서 `champion_score` 상위 80% 임계값과 `new_score` 상위 80% 임계값을 각각 구하고, 각 신청자가 (현행승인/거절) × (새점수승인/거절) 중 어디에 속하는지 세어 네 그룹 인원을 센다 | 둘다승인 45,369명 / 둘다거절 8,468명 / swap-out(현행승인·새점수거절) 3,833명 / swap-in(현행거절·새점수승인) 3,833명 (출처: `07_final_evaluation.md` §2-3) | | | |
| 18 | 이익 지수 재계산 | 같은 CSV에서 r=20%, LGD=60% 조합의 승인율 80% 지점 이익을 직접 계산: 이익=Σ(승인&TARGET=0) 0.2×AMT_CREDIT − Σ(승인&TARGET=1) 0.6×AMT_CREDIT. 이를 "전원승인 이익"(모든 행 기준 같은 공식)으로 나누고 100을 곱해 지수로 환산. champion_score와 new_score 각각 계산 | champion 이익지수 ≈ 94.49 / new_score 이익지수 ≈ 96.43 (주의: 이 수치는 `07_final_evaluation.md`의 H7 표에 있는 "이익 최대 지점"의 지수가 아니라 — 그 표는 각 모델의 최적 승인율(각각 96%/95%)에서의 값이다 — 승인율을 80%로 고정했을 때의 값이므로 별도로 계산된 참고값이다) | | | |
| 19 | 점수표 확인 | (스코어카드가 최종 선택된 경우만 해당) `06_scorecard_points.md`의 배점표로 신청자 1명(예: SK_ID_CURR=264637)의 점수를 직접 합산해 문서의 계산 예시(최종 점수 543.56)와 대조 | 543.56점 (출처: `06_scorecard_points.md` "신청자 1명 점수 계산 예시"). **참고**: 4단계 선택 규칙 적용 결과 최종 모델은 스코어카드가 아니라 **LightGBM**이었다(`06_modeling.md` §8) — 이 항목은 스코어카드 후보 자체의 점수표 정합성만 검증하는 것이며, 최종평가에 쓰인 모델과는 별개다. | | | |
| 20 | 최종평가 미사용 확인 | `grep -n "holdout" v2/scripts/07_models.py` 실행 | `07_models.py`에서 `holdout`이 나오는 줄은 전부 주석/문구(예: "holdout_ids.csv는 이 스크립트에서 전혀 읽지 않는다")뿐이어야 하며, `pd.read_csv`나 `open(...)`처럼 `holdout_ids.csv` 파일을 실제로 여는 코드는 **없어야** 한다. `holdout_ids.csv`를 실제로 읽는 코드는 `08_final_evaluation.py`에만 있어야 정상 | | | |
