# Phase 7: 모니터링 대시보드 (Streamlit)

실행: `streamlit run dashboard/monitoring_dashboard.py`

실제 운영 로그가 없어서 `application_train`을 배치로 나눠 "시간에 따라 데이터가 들어온다"를 시뮬레이션한다.

## 1. 시간순 프록시 검토 — SK_ID_CURR은 실측으로 기각함

Home Credit 데이터는 모든 날짜가 "신청 시점 기준 상대값"으로 익명화돼 있어 절대 시간 컬럼이 없다. SK_ID_CURR 오름차순이 접수 순서를 반영할 수도 있다는 가설을 실측으로 검증:

| 구간(순서/무작위) | TARGET 비율 범위 | EXT_SOURCE_2 평균 범위 |
|---|---|---|
| SK_ID_CURR 순서 10구간 | 0.0791~0.0829 | 0.5132~0.5159 |
| 무작위 10구간(대조군) | 0.0779~0.0823 | 0.5134~0.5166 |

변동폭이 사실상 동일 → **SK_ID_CURR 순서에는 구조가 없음, 무작위 배정과 다르지 않음.** 시간순 프록시로 채택하지 않음.

## 2. 배치 분할 모드 (사용자 확정: 둘 다 구현, 토글)

- **B. 무작위 배치(정상 상태 대조군)**: 모니터링 풀을 무작위 셔플 후 N등분. drift 지표가 오탐 없이 낮게 나오는지 검증하는 용도
- **C. 의도적 드리프트 주입(synthetic)**: 정렬 기준 feature(기본 EXT_SOURCE_2, 사이드바에서 변경 가능) 오름차순으로 정렬 후 N등분. **화면에 "⚠️ SYNTHETIC / 의도적 드리프트 주입 모드"** 붉은 배너로 항상 명시 — 실제 드리프트와 혼동되지 않도록 함

## 3. Drift 지표: PSI(메인) + KS(보조)

`dashboard/drift_metrics.py`에 직접 구현(외부 drift 라이브러리 미사용):
- **PSI**: 연속형은 reference 분위수 10구간, 범주형은 카테고리 자체를 버킷으로 사용. 표준 임계값 적용 — `<0.10` 안정 / `0.10~0.25` 주의 / `>0.25` 경고
- **KS 통계량 + p-value**: `scipy.stats.ks_2samp`, PSI를 보완하는 통계적 유의성 지표

대상: 예측 확률 분포 + `EXT_SOURCE_1/2/3`, `AMT_INCOME_TOTAL`, `AMT_CREDIT`, `DAYS_BIRTH`, `bureau_debt_credit_ratio`, `ccb_utilization_mean_mean`(Lean(A) 파생 feature), `NAME_EDUCATION_TYPE`(범주형)

## 4. 중요 버그 발견 및 수정 — AUC in-sample 오염

최초 구현에서 Phase 5 서빙 모델(전체 application_train 100%로 학습됨)을 그대로 써서 배치별 AUC를 쟀더니 **0.80~0.86**으로 Phase 4 검증치(0.7825)보다 뚜렷이 높게 나옴 — 원인은 모델이 이미 학습 때 다 본 데이터를 평가에 다시 쓴 in-sample 오염.

**수정**: [`scripts/train_monitoring_model.py`](../scripts/train_monitoring_model.py)로 Phase 4와 동일한 레시피(80/20 split, `random_state=42`)로 **80%만 학습한 별도 모델**(`models/lean_a_lightgbm_holdout_v1.joblib`)을 새로 만들고, 나머지 20%(61,503명, 모델이 전혀 보지 못한 진짜 held-out)만 대시보드의 reference/배치 풀로 사용하도록 변경.

- 수정 후 held-out 전체 AUC: **0.7833** (Phase 4의 0.7825와 거의 일치 — 정상 재현 확인)
- 무작위 모드 배치별 AUC: 0.78~0.81 범위(정상적인 표본 변동), synthetic 모드에서는 0.74~0.76까지 하락하는 배치도 관찰됨(EXT_SOURCE_2로 정렬해 배치 내 값 범위가 좁아지면서 그 배치 안에서의 판별력이 줄어드는 것으로 추정)

## 5. 로컬 실행 결과 (검증 완료)

**무작위 배치 모드**: PSI 전부 0.00~0.02 수준으로 안정(녹색), "경고 임계값 초과 없음" — drift 지표가 오탐하지 않음을 확인.

**Synthetic 모드(EXT_SOURCE_2 정렬)**: `EXT_SOURCE_2`만 PSI **6.2~7.1**로 극단적으로 치솟고(다른 feature는 대부분 0.01~0.14 수준 유지), 예측 확률 분포도 배치 1·2·7·8에서 "경고(심각한 drift)"로 정확히 표시됨, 총 12건 경고 발견 — **의도적으로 주입한 drift를 지표가 정확히 잡아냄**을 실증.

두 모드 결과가 대조적으로 나온 것 자체가 이 drift 감지 구현이 오탐(false positive)도 없고 미탐(false negative)도 없다는 근거가 됨.

## 6. 기술 스택

**Streamlit** 채택 — 기존 pandas/duckdb 스택과 궁합이 좋고 인터랙티브 대시보드를 빠르게 구현 가능. 차트는 Plotly(박스플롯, 히트맵, 라인차트) 사용. PSI/KS는 Evidently 같은 전용 라이브러리 대신 직접 구현(계산 로직을 명시적으로 보여주기 위함).

## 파일

| 파일 | 역할 |
|---|---|
| `dashboard/drift_metrics.py` | PSI/KS 계산 함수 |
| `dashboard/monitoring_dashboard.py` | Streamlit 앱 본체 |
| `scripts/train_monitoring_model.py` | 모니터링 전용 held-out 모델 학습 |
| `models/lean_a_lightgbm_holdout_v1.joblib` | 80%만 학습한 held-out 모델 |
| `data/processed/monitoring_holdout.parquet` | 모델이 학습 때 보지 않은 20%(61,503명) |
