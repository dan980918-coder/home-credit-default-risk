# Phase 3 Quick 벤치마크: App-only vs Lean(A) vs Full(B)

LightGBM 기본 하이퍼파라미터(튜닝 없음) + 5-fold CV로 ROC-AUC만 빠르게 비교. 본격 튜닝/평가는 Phase 4.
스크립트: [`scripts/phase3_quick_benchmark.py`](../scripts/phase3_quick_benchmark.py) (메모리 부담 때문에 실제 실행은 App-only+Lean(A) / Full(B)로 나눠서 진행 — 스크립트 자체는 3개를 순서대로 돌리도록 작성됨)

| 구성 | shape | AUC (5-fold 평균) | std | 소요시간 |
|---|---|---|---|---|
| App-only (application_train만) | (307511, 121) | 0.7562 | 0.0041 | 11.9s |
| Lean(A) (application + 신용이력 요약) | (307511, 161) | 0.7764 | 0.0028 | 17.7s |
| Full(B) (application + 신용이력 전체 통계량) | (307511, 390) | 0.7800 | 0.0011 | 47.0s |

**App-only → Lean(A): +0.0202** (뚜렷한 개선)
**Lean(A) → Full(B): +0.0036** (작지만 fold 표준편차보다는 큼)
**App-only → Full(B): +0.0238**

## 해석

- **bureau/previous_application 신용이력 정보를 추가하는 것 자체가 확실히 유의미함** — AMEX Phase 3에서 시계열 파생(baseline A → main B)이 거의 개선이 없었던 것(+0.0003)과 대조적으로, 이번엔 App-only → Lean(A)에서 +0.0202라는 뚜렷한 개선이 나옴. Home Credit 데이터는 신용조회/과거대출 이력이 application 자체 정보보다 예측력이 크게 추가된다는 뜻으로, Phase 2 EDA §4에서 확인한 `ccb_utilization_mean_mean`(corr +0.144) 등 개별 지표 상관과도 일관됨
- **Lean(A) → Full(B)의 개선폭은 작음(+0.0036)** — 컬럼 수는 2.4배(163→392)로 늘었지만 성능 개선은 제한적. "테이블당 핵심 지표 몇 개만 선별"한 Lean 방식이 이미 신호 대부분을 포착했다는 뜻으로 보이며, 이는 애초 프로젝트를 AMEX→Home Credit으로 전환한 이유("해석 가능한 feature 구조가 필요")와도 부합 — **해석하기 쉬운 Lean(A)이 성능 손실을 거의 없이 복잡도만 줄여준다**는 근거가 됨
- 다만 이건 **튜닝 없는 기본 하이퍼파라미터 기준**이라는 점은 AMEX 때와 마찬가지로 유의 — Full(B)은 컬럼이 많아 트리 수/정규화를 더 키우면 격차가 벌어질 수도 있음. Phase 4에서 재검증 필요

## 메모리 실측

| 구성 | peak RSS | 비고 |
|---|---|---|
| App-only + Lean(A) (연속 실행) | 1,478MB | swap 변화 없음 |
| Full(B) 단독 | **1,871MB** | **swap 748MB까지 상승** (이번 프로젝트 최고치) — 여전히 완료는 됐으나 가장 타이트했던 구간 |

## Phase 4 계획 반영 (사용자 요청)

Phase 4 모델링 시 다음 비교를 반드시 포함:
1. **App-only vs Lean(A) 전체(신용이력 포함)** — 이번 quick 벤치마크로 이미 방향성 확인(+0.0202), Phase 4에서 튜닝 후 재확인
2. **Lean(A) vs Full(B)** — 이번엔 +0.0036으로 작았지만 튜닝 후 격차가 벌어지는지 재확인
3. 최종 모델은 위 비교 결과 + SHAP 해석 용이성(프로젝트 목표)을 함께 고려해 Lean(A) 또는 Full(B) 중 선택하거나, 절충안(Full(B)에서 중요도 상위만 추린 버전) 검토
