# 모델링 (4단계 2절)

연체 위험 기반 대출 승인 기준 설계 (Loan Approval Risk Scoring) — v2 재분석

재현 코드: [`v2/scripts/07_models.py`](../scripts/07_models.py) · 원본 수치: [`modeling_results.json`](modeling_results.json) · 점수표: [`06_scorecard_points.md`](06_scorecard_points.md)

> **학습 세트(60%, 184,506명)로 학습하고, 검증 세트(20%, 61,502명)로 모델·설정을 선택했다.** 최종평가(holdout) 세트는 이 스크립트에서 전혀 읽지 않았다. 선택 규칙은 작업 시작 전에 고정했고 결과를 보고 바꾸지 않았다.

---

## 1. 변수 세트

| 세트 | 변수 수 | 구성 |
|---|---|---|
| 기본 세트(나이 제외) | 36개 | H1~H5 핵심·보조 변수 27개(H2 포함) + EXT_SOURCE_1/2/3 + 결측플래그 3개 + AMT_CREDIT/AMT_ANNUITY/AMT_GOODS_PRICE |
| 기본 세트(나이 포함) | 37개 | 위 + age_years |
| 참고용 전체 세트 | 133개 | 기본 세트(나이 포함) + application 잔여 96개 컬럼(제외 변수 제외) |

## 2. 변수 선택 결과

**1단계: 학습 세트 IV≥0.02 필터** — 37개 중 26개 통과, 11개 제거:

| 제거된 변수 | 이유(학습세트 IV) |
|---|---|
| EXT_SOURCE_1_MISSING | 0.0049 |
| EXT_SOURCE_2_MISSING | 0.0000 |
| EXT_SOURCE_3_MISSING | 0.0070 |
| NAME_CONTRACT_TYPE | 0.0134 |
| annuity_to_income | 0.0060 (H2 핵심변수, 3단계 기각과 일관) |
| bureau_balance_delinquent_month_ratio | 0.0130 |
| bureau_currently_overdue_flag | 0.0138 |
| cc_dpd_month_ratio | 0.0060 |
| credit_to_income | 0.0094 |
| recent_1yr_apply_count | 0.0191 |
| total_credit_bureau_inquiries | 0.0173 |

**2단계: WOE 상관 |r|>0.7 필터** — IV 통과 26개 중 2개 추가 제거:

| 제거 | 유지 | 상관계수 | 제거쪽 IV | 유지쪽 IV |
|---|---|---|---|---|
| underpay_ratio | late_payment_ratio | 0.845 | 0.0504 | 0.0645 |
| avg_delay_days | late_payment_ratio | 0.794 | 0.0458 | 0.0645 |

**최종 변수 수**: 나이 포함 24개, 나이 제외 23개. EXT_SOURCE 결측 플래그 3개가 전부 IV 필터에서 탈락했다는 점은, 이 데이터에서는 "외부점수가 없다는 사실 자체"보다 "점수 수치 자체"가 신호로서 훨씬 중요함을 뜻한다.

---

## 3. 현행 기준(Champion) — 대용 지표임을 명시

> 아래 "Champion"은 **실제 회사의 기존 심사 점수가 아니라, 외부 점수(EXT_SOURCE_1/2/3)만 쓰는 심사를 가정한 대용 기준**이다.

* 입력: EXT_SOURCE_1/2/3 + 결측 플래그 3개(6개 변수)
* 결측 처리: 학습 세트 중앙값 대체(EXT_SOURCE_1=0.5060, EXT_SOURCE_2=0.5658, EXT_SOURCE_3=0.5352 — 정확한 값은 `modeling_results.json`의 `champion.medians` 참고)
* 모델: 로지스틱 회귀(기본 설정)
* 검증 AUC = **0.7225**, KS = 0.3309, Gini = 0.4450

---

## 4. 새 점수 후보 1: 로지스틱 회귀 스코어카드

* 3단계 IV 엔진과 동일한 알고리즘(분위수 최대 10구간 + 5%/양쪽클래스 병합, 범주형 1% 미만 "기타")으로 학습 세트 기준 구간을 만들고 WOE로 변환했다.
* C(L2 정규화 강도) 그리드 서치 — 나이 포함 버전:

| C | 검증 AUC |
|---|---|
| 0.01 | 0.75307 |
| 0.1 | 0.75329 |
| **1** | **0.75330** (선택) |

나이 제외 버전도 동일하게 C=1이 최적(검증 AUC 0.75321).

* **스코어카드(나이 포함) 검증 AUC = 0.7533, KS = 0.3811, Gini = 0.5066**
* 점수표 전문과 신청자 1명 계산 예시는 [`06_scorecard_points.md`](06_scorecard_points.md) 참고.

---

## 5. 새 점수 후보 2: LightGBM

* 입력: 기본 세트 원값(WOE 변환 없음), 범주형 변수 없음(NAME_CONTRACT_TYPE은 IV 필터에서 이미 제거됨)
* 그리드: num_leaves{15,31,63} × learning_rate{0.03,0.05} × min_child_samples{50,200} = 12개 조합, 검증 세트로 early stopping(50라운드)
* 클래스 가중치 미사용(순위 평가 목적)

**그리드 서치 결과(나이 포함, 12개 조합 중 발췌)**:

| num_leaves | learning_rate | min_child_samples | best_iteration | 검증 AUC |
|---|---|---|---|---|
| 31 | 0.05 | 200 | 298 | **0.76992** (최적) |
| 31 | 0.03 | 200 | 604 | 0.76989 |
| 15 | 0.05 | 200 | 610 | 0.76972 |
| 63 | 0.03 | 200 | 391 | 0.76975 |
| (나머지 8개 조합) | | | | 0.767~0.769 |

전체 12개 조합 상세는 `modeling_results.json`의 `lightgbm_with_age.grid_results` 참고.

* **LightGBM(나이 포함) 검증 AUC = 0.7699, KS = 0.4067, Gini = 0.5398** (최적 조합: num_leaves=31, learning_rate=0.05, min_child_samples=200)
* 나이 제외 버전 최적: num_leaves=15, learning_rate=0.03, min_child_samples=200, 검증 AUC = 0.7680, KS=0.4074, Gini=0.5359

---

## 6. 참고용 전체 세트 (LightGBM 1회, 참고용)

133개 변수(기본세트+나이+application 잔여 96컬럼) 전체를 LightGBM(num_leaves=31, learning_rate=0.05, min_child_samples=100, early stopping)으로 1회 학습한 결과:

**검증 AUC = 0.7747, KS = 0.4115, Gini = 0.5494**

기본 세트(나이 포함) LightGBM(AUC 0.7699) 대비 **+0.0048**(AUC 기준) 높다 — "설명 가능한 24개 변수로 구성하기 위해 포기한 성능"이 AUC 기준 약 0.5%p 수준임을 숫자로 남긴다. 이 모델은 최종 후보가 아니며 어떤 선택에도 쓰이지 않았다.

---

## 7. 검증 세트 성능 요약표

| 모델 | 변수 수 | 검증 AUC | 검증 KS | 검증 Gini |
|---|---|---|---|---|
| Champion(외부점수 대용) | 6 | 0.7225 | 0.3309 | 0.4450 |
| 스코어카드(나이 포함) | 24 | 0.7533 | 0.3811 | 0.5066 |
| 스코어카드(나이 제외) | 23 | 0.7532 | 0.3820 | 0.5064 |
| **LightGBM(나이 포함)** | 24 | **0.7699** | 0.4067 | 0.5398 |
| LightGBM(나이 제외) | 23 | 0.7680 | 0.4074 | 0.5359 |
| 참고용 전체 세트(LightGBM) | 133 | 0.7747 | 0.4115 | 0.5494 |

---

## 8. 선택 규칙 적용 과정

**1) 모델 선택** (LightGBM AUC − 스코어카드 AUC ≥ 0.01 이면 LightGBM, 아니면 스코어카드):
`0.7699 - 0.7533 = 0.0166 ≥ 0.01` → **LightGBM 선택**

**2) 나이 판정** (선택된 모델에서 나이를 뺐을 때 AUC 하락이 0.005 미만이면 나이 제외 버전이 최종):
LightGBM 나이 포함 AUC 0.7699 → 나이 제외 AUC 0.7680, 하락폭 `0.0699 - 0.7680 = 0.0020` (0.2%p) `< 0.005` → **나이 제외 버전이 최종**

**최종 선택 모델: LightGBM(나이 제외, 23개 변수), 검증 AUC = 0.7680**

---

## 9. 변수 기여도 (SHAP 상위 15개, 최종 선택 모델 기준)

| 순위 | 변수 | 평균 |SHAP| 절댓값 |
|---|---|---|
| 1 | EXT_SOURCE_2 | 0.3368 |
| 2 | EXT_SOURCE_3 | 0.2835 |
| 3 | EXT_SOURCE_1 | 0.1870 |
| 4 | credit_to_annuity | 0.1426 |
| 5 | employment_days | 0.1384 |
| 6 | recent_1yr_late_ratio | 0.1128 |
| 7 | credit_to_goods | 0.1051 |
| 8 | AMT_ANNUITY | 0.0949 |
| 9 | late_payment_ratio | 0.0816 |
| 10 | AMT_GOODS_PRICE | 0.0810 |
| 11 | debt_to_income | 0.0786 |
| 12 | card_utilization | 0.0677 |
| 13 | bureau_max_overdue_amt | 0.0616 |
| 14 | reject_ratio | 0.0515 |
| 15 | phone_change_days | 0.0451 |

외부 신용점수 3개가 SHAP 기여도 1~3위를 모두 차지해, 참고 변수로만 다뤘던 EXT_SOURCE가 실제로는 가장 강력한 예측 변수임이 재확인됐다(3단계에서도 IV 기준 참고 변수 중 압도적 1위였음). 3단계에서 검증한 H1(late_payment_ratio, 9위)·H3(reject_ratio, 14위)·H4(employment_days, 5위)의 핵심 변수가 모두 상위 15위 안에 들어, 3단계 가설 채택 결과가 실제 예측 기여도로도 뒷받침됐다. 반면 H5의 핵심 변수(credit_to_goods, 7위)보다 "방향 반대" 발견으로 주목했던 보조 변수(credit_to_annuity)가 더 높은 순위(4위)를 차지한 점도 3단계 발견과 일관된다.

---

## 10. 건너뛴 항목

* 스코어카드·LightGBM 모두 선택 규칙에 따라 자동 결정됐으므로, 추가적인 수동 임계값 조정은 하지 않았다.
* 참고용 전체 세트는 1회만 학습(그리드서치 생략) — 지시사항대로 "포기한 성능"을 숫자로 남기는 용도로만 썼다.
