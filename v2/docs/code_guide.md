# 코드 해설서

연체 위험 기반 대출 승인 기준 설계 (Loan Approval Risk Scoring) — v2 재분석

이 문서는 `v2/scripts/01~05`가 무엇을, 왜 그렇게 했는지 설명한다. 검증은 [`v2/verification/`](../verification/)의 체크리스트·노트북으로 한다.

---

## 01_data_audit.py — 원데이터 점검

* **목적**: 8개 원본 CSV의 기본 정보, 키 무결성, 고아 레코드, 이력 보유율, TARGET 분포, 결측·이상값, 시간/누수 위험을 DuckDB로 직접 스캔해 점검한다.
* **입력**: `data/raw/*.csv` (8개 테이블 + 컬럼 설명 파일)
* **출력**: `v2/docs/audit_results.json`, `v2/docs/figures/target_distribution.png`, `v2/docs/figures/missing_rate_distribution.png`

**처리 순서**:
1. (50~71행) 파일별 행/열 수, 크기, 읽기 오류 확인 — `read_csv_auto`로 전체 스캔.
2. (97~131행) `SK_ID_CURR`/`SK_ID_BUREAU`/`SK_ID_PREV` 중복 여부, train/test `SK_ID_CURR` 겹침(0건) 확인.
3. (139~220행) `orphan_check()` 함수로 6개 테이블 쌍의 양방향 고아 비율 계산. 194~220행에서 bureau/previous_application을 train+test 합집합과 비교(둘 다 0건 — 완전 포괄 확인).
4. (231~272행) `history_coverage()` 함수로 application_train 신청자별 하위 테이블 이력 보유율 계산. POS_CASH/installments/credit_card는 `via_prev=True`로 previous_application을 거쳐 연결(1단계 시점 기준, 04번 스크립트에서는 이 경로를 자체 SK_ID_CURR 직접연결로 수정함 — 아래 "주요 판단" 참고).
5. (278~312행) TARGET 분포 집계 + 막대그래프 저장.
6. (322~360행) 전 테이블 컬럼별 결측률을 `SUM(CASE WHEN ... IS NULL)` 한 번의 쿼리로 일괄 계산, 결측률 구간별 컬럼 수 집계.
7. (366~393행) 상수에 가까운 컬럼(최다값 99.9%+) 탐지, 완전 중복 행 수 계산.
8. (403~421행) `DAYS_` 컬럼의 양수/365243 특수값 탐지.
9. (427~442행) 범주형 특수값(XNA/XAP/Unknown) 컬럼별 건수 집계.
10. (447~468행) `AMT_` 컬럼 음수·상위 0.1% 극단값 집계.
11. (482~503행) 절대 날짜형 컬럼 존재 여부(0개 확인), MONTHS_BALANCE>0 행 탐지(신청 이후 정보 혼입 여부).

**핵심 쿼리 발췌** (고아 레코드 양방향 계산, 139~163행):
```python
def orphan_check(child_name, child_key, parent_name, parent_key):
    orphan_child = con.execute(f"""
        SELECT COUNT(*) FROM read_csv_auto('{pc}') c
        WHERE c.{child_key} NOT IN (SELECT {parent_key} FROM read_csv_auto('{pp}'))
    """).fetchone()[0]
    parent_unmatched = con.execute(f"""
        SELECT COUNT(*) FROM (SELECT DISTINCT {parent_key} FROM read_csv_auto('{pp}')) p
        WHERE p.{parent_key} NOT IN (SELECT DISTINCT {child_key} FROM read_csv_auto('{pc}'))
    """).fetchone()[0]
```
자식→부모(진짜 고아)와 부모→자식(미매칭) 두 방향을 분모를 다르게 해서 각각 계산한다 — 이 두 숫자를 하나로 뭉뚱그려 서술한 것이 1단계 최초 버전의 버그였다(아래 "실행 중 발견·수정한 버그" 참고).

**주요 판단**:
* DuckDB `read_csv_auto`로 CSV를 매번 다시 스캔한다(중간 테이블 생성 없이). 707MB짜리 installments_payments도 컬럼이 8개뿐이라 전체 스캔이 감당 가능했다.
* 고아 비율은 "자식 기준"과 "부모 기준"을 분리해서 계산·보고해야 한다는 원칙을 여기서 세웠고, 04번 스크립트의 "연결 경로 원칙"으로 이어졌다.

**실행 중 발견·수정한 버그**:
1. **`GROUP BY ALL` 중복행 오집계**: 완전 중복 행 수를 셀 때 처음에 `SELECT COUNT(*) ... GROUP BY ALL`을 썼는데, SELECT 목록에 집계 컬럼(`COUNT(*)`)만 있고 다른 컬럼이 없어 DuckDB가 "그룹화할 컬럼이 없다"고 판단해 **전체 테이블을 한 그룹으로 묶어버렸다**. 그 결과 거의 모든 행이 "중복"으로 잘못 집계됐다(예: application_train 307,510/307,511건). 증상은 "거의 전수 중복"이라는 비현실적 숫자. 원인은 `GROUP BY ALL`이 SELECT 절의 비집계 컬럼을 기준으로 그룹화하는데 그런 컬럼이 없었던 것. 수정: `GROUP BY "{col1}", "{col2}", ...`로 모든 컬럼을 명시(385~393행). 재계산 결과 8개 테이블 전부 완전 중복 행 **0건**.
2. **(2단계 이후, 1단계 보고서 서술 오류)**: 고아 비율 자체의 계산은 처음부터 맞았지만, 상단 요약 문장에서 "bureau_balance의 54.9%가 고아"처럼 **분모가 속한 테이블 이름을 잘못 적은 채 서술**했다. 실제로는 bureau 테이블의 54.9%가 bureau_balance 기록이 없는 것이었다. 3단계 작업 중 `03a_orphan_recheck.py`로 (a)/(b)/(c) 세 지표를 명칭을 명시해 재계산해 바로잡았다. 상세 원인은 `01_data_audit.md`의 "수정 기록" 절 참고.

---

## 02_variable_catalog.py — 변수 파악

* **목적**: application_train 122개 컬럼을 업무 의미별로 분류하고, 각 변수의 자료형·결측률·분포를 기록한다. 하위 7개 테이블 요약도 함께 만든다.
* **입력**: `data/raw/application_train.csv`, `HomeCredit_columns_description.csv`
* **출력**: `v2/docs/catalog_results.json`

**처리 순서**:
1. (22~26행) 컬럼 설명 파일을 cp1252 인코딩으로 읽어 컬럼명→영문 설명 매핑(`desc_map`) 생성.
2. (31~97행) `CATEGORY_MAP` 딕셔너리로 122개 컬럼을 14개 업무 카테고리에 수동 매핑. AVG/MODE/MEDI 접미사 컬럼은 "주택 건물 정보"로 일괄 분류(92~95행).
3. (103~131행) 컬럼마다 dtype·결측률·고유값 수 계산. 숫자형은 min/median/max(116~122행), 범주형은 상위 5개 범주(123~130행).
4. (155~204행) bureau/bureau_balance/previous_application/POS_CASH/installments/credit_card 6개 테이블의 신청자(또는 상위키)당 평균/중앙값/최대 레코드 수 계산.

**핵심 쿼리 발췌** (컬럼별 분포 요약, 103~130행):
```python
for c in all_cols:
    n_null = con.execute(f'SELECT SUM(CASE WHEN "{c}" IS NULL THEN 1 ELSE 0 END) FROM read_csv_auto(...)').fetchone()[0]
    n_unique = con.execute(f'SELECT COUNT(DISTINCT "{c}") FROM read_csv_auto(...)').fetchone()[0]
    if dtype in ("BIGINT", "DOUBLE", ...):
        stats = con.execute(f'SELECT MIN("{c}"), MEDIAN("{c}"), MAX("{c}") FROM read_csv_auto(...)').fetchone()
```
컬럼마다 쿼리를 따로 날리는 단순한 구조라 122개 컬럼 × 2~3개 쿼리로 다소 느리지만(약 20여 분), 정확성과 코드 가독성을 우선했다.

**주요 판단**: 이 단계에서는 TARGET과의 관계를 전혀 계산하지 않았다(지시사항 준수) — 변수 분포만 파악하고 가설은 3단계에서 세웠다.

**실행 중 발견·수정한 버그**: 없음(이 스크립트 자체에서 발견된 버그는 없다).

---

## 03_split.py — 데이터 분할

* **목적**: application_train 307,511명을 TARGET 기준 층화추출로 학습60%/검증20%/최종평가20%로 나눈다.
* **입력**: `data/raw/application_train.csv`
* **출력**: `v2/data/splits/{train,valid,holdout}_ids.csv`, `v2/docs/split_summary.json`

**처리 순서**:
1. (30행) DuckDB로 SK_ID_CURR, TARGET만 읽는다(가볍게).
2. (36~38행) `train_test_split(stratify=TARGET)`로 1차 분할: train(60%) vs temp(40%).
3. (40~42행) temp를 다시 절반씩 층화분할해 valid(20%)/holdout(20%) 확보.
4. (44~47행) 세 세트가 서로 겹치지 않는지, 합이 전체와 같은지 assert로 검증.
5. (49~52행) train/valid는 SK_ID_CURR+TARGET을 저장하지만, **holdout은 SK_ID_CURR만 저장**(TARGET 저장 안 함) — 이후 단계에서 실수로라도 최종평가 TARGET을 읽을 수 없게 하는 물리적 장치.

**핵심 코드 발췌** (holdout TARGET 의도적 미저장, 49~52행):
```python
train_df[["SK_ID_CURR", "TARGET"]].to_csv(..., index=False)
valid_df[["SK_ID_CURR", "TARGET"]].to_csv(..., index=False)
holdout_df[["SK_ID_CURR"]].to_csv(..., index=False)  # TARGET 컬럼 자체가 파일에 없음
```

**주요 판단**: 날짜 컬럼이 없어 시간순 분할이 불가능하므로 무작위 층화추출을 썼다(`random_state=42`로 고정, 재현 가능). holdout 파일에 TARGET을 아예 쓰지 않은 것은 "실수 방지"를 코드 구조로 강제한 설계 선택이다.

**실행 중 발견·수정한 버그**: 없음.

---

## 04_build_hypothesis_features.py — 가설 검증용 변수 생성

* **목적**: H1~H5 가설 검증에 쓸 신청자(SK_ID_CURR) 단위 변수 테이블을 만든다.
* **입력**: `data/raw/*.csv` (8개 테이블)
* **출력**: `v2/data/features/hypothesis_features.parquet` (307,511행 x 140열, 커밋 안 함), `v2/docs/feature_build_log.json`

**처리 순서**:
1. (52~71행) application_train 컬럼 중 제외 변수(`EXCLUDE_ALWAYS`, 54~58행: CODE_GENDER+SOCIAL_CIRCLE 4개)와 이미 파생변수에 쓰인 원본 컬럼(`USED_IN_DERIVED`, 60~68행)을 뺀 나머지를 "부록 컬럼"으로 분리.
2. (76~92행) `app_base` CTE: DAYS_EMPLOYED=365243 → NULL + unemployed_flag 생성(81~82행), 나머지 DAYS_* 부호 반전, EXT_SOURCE 평균 계산 준비.
3. (95~106행) `bureau_agg`: 활성대출 수, 활성대출 부채합, 현재연체 플래그, 최대연체금액, 최근1년 신규대출 수 — bureau 자체 SK_ID_CURR로 직접 GROUP BY.
4. (108~121행) `bureau_balance_joined`→`bureau_balance_agg`: bureau_balance는 SK_ID_CURR이 없어 bureau와 INNER JOIN으로 연결(진짜 고아 자동 제외)한 뒤 집계.
5. (123~132행) `prev_agg`: 거절 비율, 최근1년 거절/신청 건수 — previous_application 자체 SK_ID_CURR로 직접 집계.
6. (135~151행) `inst_filtered`(진짜 고아 제외, 138행: `WHERE SK_ID_PREV IN (SELECT ... FROM previous_application)`)→`inst_agg`: 지연비율, 과소납부비율, 평균지연일, 최근1년지연비율.
7. (153~192행) POS_CASH/credit_card도 동일하게 진짜 고아 제외 후 자체 SK_ID_CURR로 직접 집계. `cc_latest`(180~183행)는 **윈도우 함수**로 카드별 최신 월을 골라 이용률을 계산.
8. (194~232행) 모든 CTE를 `LEFT JOIN`으로 app_base에 붙이고, 비율형 파생변수(annuity_to_income 등)를 최종 SELECT에서 계산. 222행에서 이력 전무 플래그 생성.
9. (236행) 쿼리 결과를 바로 parquet로 `COPY ... TO ... (FORMAT PARQUET)`.
10. (243~251행) XNA/Unknown 특수값을 NULL로 바꾸는 후처리 쿼리를 별도로 실행(parquet을 다시 읽어 `CREATE OR REPLACE TABLE ... SELECT * REPLACE(...)` 후 재저장).

**핵심 쿼리 발췌** (카드 이용률 - 윈도우 함수로 "최신 월"만 선택, 180~191행):
```sql
cc_latest AS (
    SELECT SK_ID_CURR, SK_ID_PREV, AMT_BALANCE, AMT_CREDIT_LIMIT_ACTUAL,
           ROW_NUMBER() OVER (PARTITION BY SK_ID_PREV ORDER BY MONTHS_BALANCE DESC) AS rn
    FROM cc_filtered
),
cc_util_agg AS (
    SELECT SK_ID_CURR, SUM(AMT_BALANCE) * 1.0 / NULLIF(SUM(AMT_CREDIT_LIMIT_ACTUAL), 0) AS card_utilization
    FROM cc_latest WHERE rn = 1 GROUP BY SK_ID_CURR
)
```
카드별로 가장 최근(MONTHS_BALANCE가 0에 가까운) 스냅샷 한 행만 골라야 "현재 이용률"의 의미가 되므로, `ROW_NUMBER() OVER (PARTITION BY ...)` 윈도우 함수로 카드(SK_ID_PREV)별 최신 행에 순번을 매긴 뒤 `rn=1`만 필터링했다.

**주요 판단**:
* **365243 처리**: DAYS_EMPLOYED=365243은 NULL로 바꾸고 `unemployed_flag=1`을 별도로 만들었다(81~82행) — 특수값을 버리지 않고 "정보"로 남겼다.
* **NULL 유지**: 이력이 없는 신청자는 모든 하위 집계 변수가 LEFT JOIN으로 자동 NULL이 된다(0으로 채우지 않음) — "이력 없음"과 "이력은 있는데 0%"를 구분하기 위해서다.
* **고아 제외 방식**: `WHERE SK_ID_PREV IN (SELECT SK_ID_PREV FROM previous_application)` 형태의 서브쿼리로 진짜 고아만 걸러내고, previous_application을 거치지 않고 각 하위 테이블이 가진 **자체 SK_ID_CURR**로 바로 GROUP BY했다(01단계에서 previous_application 경유로 집계했던 것과 다른 방식 — 1단계 수정 기록에서 확인한 "credit_card_balance의 진짜 고아는 28.2%뿐, previous_application 경유 시 94.4% 유실"이라는 교훈을 반영).

**실행 중 발견·수정한 버그**: 이 스크립트 자체에서 발견된 버그는 없다. (단, 이 스크립트가 반영하는 "연결 경로 원칙"은 01단계의 서술 오류를 바로잡으며 확정한 것이다.)

---

## 05_test_signal_hypotheses.py — 가설 검증 (IV/WoE 엔진)

* **목적**: 학습 세트(60%)에서 H1~H5 핵심/보조 변수, 참고 변수, 부록 변수의 IV를 계산하고, 핵심 변수는 방향성(Spearman)·위험끝/안전끝 배수·95% CI까지 계산해 가설을 채택/기각 판정한다.
* **입력**: `v2/data/features/hypothesis_features.parquet`, `v2/data/splits/train_ids.csv`
* **출력**: `v2/docs/hypothesis_results.json`, `v2/docs/figures/{iv_by_hypothesis,core_signals}.png`

**처리 순서**:
1. (44~50행) parquet 전체를 읽고 train_ids와 inner merge — **학습 세트(184,506명)만** 사용(검증·최종평가 세트는 이 스크립트가 아예 읽지 않는다, 체크리스트 20번 검증 대상).
2. (55~97행) `HYPOTHESES` 딕셔너리로 가설별 핵심/보조 변수와 예상 방향(`high_risky`/`low_risky`)을 코드 상수로 고정.
3. (115~179행) `bin_numeric()`: 분위수 최대 10구간 생성 후, 5% 미만이거나 한쪽 클래스가 없는 구간을 반복적으로 이웃과 병합(141~160행). 저카디널리티(고유값≤10) 변수는 qcut 대신 값 자체를 구간으로 사용(128~133행, 버그 수정 반영).
4. (182~195행) `bin_categorical()`: 1% 미만 범주를 "기타"로 묶음.
5. (198~222행) `compute_iv_table()`: 구간별 good/bad 카운트에 0.5 보정 후 WOE·IV 계산(206~209행), Wilson 95% CI 계산.
6. (236~291행) `direction_check()`: 결측 제외 구간의 순서-연체율 Spearman 상관, 위험/안전 끝 구간의 배수와 로그비율 근사 95% CI(272~279행).
7. (336~370행) 가설별로 핵심+보조 변수 분석 실행 후, 사전 고정 기준(IV≥0.02 and 방향일치)으로 채택/기각 판정.
8. (381~411행) 참고 변수(EXT_SOURCE, 나이), 부록 96개 변수는 IV만 계산.
9. (414~429행) 이력 없는 신청자 vs 있는 신청자 연체율 비교.
10. (432~452행) 보조 변수 IV 상위 5개, 방향 반대 변수 식별.
11. (463~511행) 그림 2개 생성.

**핵심 쿼리·코드 발췌** (WOE/IV 계산, 0.5 보정 포함, 198~210행):
```python
def compute_iv_table(bin_series, y, order_map=None):
    g = df_local.groupby("bin")["y"].agg(["count", "sum"]) ...
    k = len(g)
    g["good_dist"] = (g["n_good"] + 0.5) / (total_good + 0.5 * k)
    g["bad_dist"] = (g["n_bad"] + 0.5) / (total_bad + 0.5 * k)
    g["woe"] = np.log(g["good_dist"] / g["bad_dist"])
    g["iv_contrib"] = (g["good_dist"] - g["bad_dist"]) * g["woe"]
```
구간 수(k)만큼 분자·분모 양쪽에 0.5를 더해 0 나눗셈/log(0)을 막으면서도 전체 분포 합이 1을 유지하도록 했다(Laplace 스무딩).

**주요 판단**:
* 판정 기준(IV≥0.02 AND 방향일치 AND 배수CI하한>1)은 작업 시작 전 고정했고, H2가 기각으로 나와도 기준을 바꾸지 않았다.
* 보조 변수는 공식 판정 없이 "가설 보강/반대" 서술만 한다(지시사항).

**실행 중 발견·수정한 버그**:
**저카디널리티 플래그 변수의 qcut 구간화 오류**: `pd.qcut(x, q=10, duplicates='drop')`을 0/1 플래그류(`unemployed_flag`, `bureau_currently_overdue_flag`)에 적용했더니, 0이 전체의 80%+를 차지해 분위수 경계 대부분이 0에 몰려 `duplicates='drop'`이 중복 경계를 지우면서 **0과 1이 하나의 구간으로 합쳐졌다**(`(-0.001, 1.0]`라는 단일 구간). 증상: `unemployed_flag`의 IV가 0.0으로 나와 "변별력이 전혀 없다"는 잘못된 결과. 원인: qcut이 "값 자체"가 아니라 "분위수 경계"로 구간을 나누는데, 저카디널리티 데이터에는 분위수 경계가 겹쳐서 의도와 다르게 동작. 수정: 고유값 수가 `max_bins`(10) 이하이면 qcut을 쓰지 않고 **값 자체를 구간 코드로 직접 매핑**하도록 분기 추가(127~133행). 재계산 결과 `unemployed_flag` IV는 0.0327로 바뀌었고, 방향도 가설과 반대(미고용/연금수령자 플래그가 오히려 연체율이 낮음)로 드러나 새로운 발견으로 이어졌다.

---

## SQL 하이라이트 후보

README에 쓸 만한 쿼리 2개를 선정했다. 기준: 집계+조건부계산+윈도우함수(또는 CTE 다단 구성)를 함께 쓴 쿼리.

### 후보 1: 카드 최신 스냅샷 이용률 계산 (04_build_hypothesis_features.py, 180~191행)

```sql
cc_latest AS (
    SELECT SK_ID_CURR, SK_ID_PREV, AMT_BALANCE, AMT_CREDIT_LIMIT_ACTUAL,
           ROW_NUMBER() OVER (PARTITION BY SK_ID_PREV ORDER BY MONTHS_BALANCE DESC) AS rn
    FROM cc_filtered
),
cc_util_agg AS (
    SELECT SK_ID_CURR,
           SUM(AMT_BALANCE) * 1.0 / NULLIF(SUM(AMT_CREDIT_LIMIT_ACTUAL), 0) AS card_utilization
    FROM cc_latest
    WHERE rn = 1
    GROUP BY SK_ID_CURR
)
```
**설명**: 신청자가 카드를 여러 장 가진 경우, 카드별(SK_ID_PREV)로 "가장 최근 월" 스냅샷 한 행만 남겨야 "현재 이용률"이라는 의미가 성립한다. `ROW_NUMBER() OVER (PARTITION BY SK_ID_PREV ORDER BY MONTHS_BALANCE DESC)`로 카드마다 독립적으로 최신 순위를 매긴 뒤 `rn=1`만 남기고, 신청자 단위로 재집계(`SUM/SUM`, 산술평균이 아니라 잔액합÷한도합으로 가중 이용률 계산)하는 2단계 CTE 구성이다.

### 후보 2: 신청자 단위 통합 조인 쿼리 (04_build_hypothesis_features.py, 75~232행 전체)

```sql
WITH app_base AS (...),
     bureau_agg AS (...),
     bureau_balance_joined AS (
         SELECT b.SK_ID_CURR, bb.STATUS
         FROM read_csv_auto(bureau_balance) bb
         INNER JOIN read_csv_auto(bureau) b ON bb.SK_ID_BUREAU = b.SK_ID_BUREAU
     ),
     bureau_balance_agg AS (...),
     prev_agg AS (...),
     inst_filtered AS (
         SELECT i.* FROM read_csv_auto(installments) i
         WHERE i.SK_ID_PREV IN (SELECT SK_ID_PREV FROM read_csv_auto(previous_application))
     ),
     inst_agg AS (...), pos_filtered AS (...), pos_agg AS (...),
     cc_filtered AS (...), cc_agg AS (...), cc_latest AS (...), cc_util_agg AS (...)
SELECT a.*, ... (파생 비율 계산) ...
FROM app_base a
LEFT JOIN bureau_agg ba ON ... LEFT JOIN bureau_balance_agg bba ON ...
LEFT JOIN prev_agg pa ON ... LEFT JOIN inst_agg ia ON ...
LEFT JOIN pos_agg pca ON ... LEFT JOIN cc_agg cca ON ... LEFT JOIN cc_util_agg cua ON ...
```
**설명**: 8개 원본 테이블(최대 1,360만 행)을 단 하나의 쿼리로 신청자 단위 140개 컬럼 특징 테이블로 압축한다. CTE 12개를 체이닝해 "진짜 고아 제외 → 자체 SK_ID_CURR 직접 연결 → LEFT JOIN"이라는 연결 경로 원칙을 SQL 구조 자체로 강제했고, 모든 서브 집계가 먼저 신청자 단위로 축소된 뒤 최종 JOIN에서 합쳐지므로 N:M 폭발 없이 단일 패스로 끝난다.
