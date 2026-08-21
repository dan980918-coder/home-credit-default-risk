# Phase 1: 데이터 검증 결과

검증 환경: MacBook Air, 8-core CPU, 물리 메모리 8GB (검증 시작 시점 여유 메모리 ~468MB)
사용 도구: DuckDB 1.5.5 (parquet 직접 쿼리, 메모리 비적재), pandas 2.2.3 + pyarrow 19.0.0 (전체 로드 테스트용)

## 1. 원본 데이터셋 여부 확인
- `customer_ID` 고유 개수: **458,913명**
- Kaggle "American Express - Default Prediction" 공식 train set의 고유 고객 수(458,913명)와 **정확히 일치**
- → `data/raw/train_data.parquet`(3.2GB)는 샘플링되지 않은 **전체 압축본**임을 확인

## 2. 로드 확인 / 행렬 크기
- 전체 행 수: 5,531,451
- 컬럼 수: 192 (원본 190개 + `target` 컬럼 병합 + `__index_level_0__` 인덱스 잔재 1개)
  - `__index_level_0__`는 pandas가 parquet 저장 시 남긴 구 인덱스 컬럼으로, feature도 target도 아니므로 로드 시 drop 필요 (→ `docs/decisions_pending_review.md` 기록)
- row group 수: 1 (파일 전체가 단일 row group — 컬럼 단위 스캔에는 문제 없으나 병렬 row-group 분산 읽기는 불가)
- 파일 손상 없음, pyarrow/duckdb/pandas 모두 정상 파싱 확인

## 3. 라벨 매칭
- `train_labels.csv`: 458,913행, 고유 customer_ID 458,913개 (1:1)
- data ↔ labels 간 customer_ID 불일치: **0건** (양방향)
- parquet에 이미 병합되어 있는 `target` 컬럼 값과 `train_labels.csv`의 target 값 불일치: **0건**
  → `train_labels.csv`는 검증용으로만 쓰고, 실제로는 parquet 내장 `target`을 단일 소스로 사용하면 됨

## 4. 시계열 분포
- 관측 기간: 2017-03-01 ~ 2018-03-31 (고유 날짜 396개, 월 단위 스냅샷)
- 고객당 관측 개월 수 분포:

| 개월 수 | 고객 수 | 비율 |
|---|---|---|
| 13 (풀) | 386,034 | 84.1% |
| 12 | 10,623 | 2.3% |
| 1~11 (부분) | 62,256 | 13.6% |

- 대다수(84%)는 13개월 풀 데이터 보유, 나머지는 중도 가입/이탈 등으로 관측 개월 수가 짧음 → Feature Engineering 시 고객별 관측 개월 수 자체를 feature로 활용하거나 최소 개월 수 기준 필터링 여부를 Phase 3에서 검토 필요

## 5. 클래스 불균형
| target | 고객 수 | 비율 |
|---|---|---|
| 0 (정상) | 340,085 | 74.11% |
| 1 (연체/채무불이행) | 118,828 | 25.89% |

- 약 2.9:1 — 중간 수준 불균형 (극단적 fraud-level 불균형은 아님). 클래스 가중치 조정 또는 threshold 튜닝으로 대응 가능한 수준.

## 6. 결측치 패턴
- 전체 188개 feature 컬럼 중:
  - 결측치 0%: 73개 컬럼
  - 결측치 ≥50%: 30개 컬럼 (최대 99.93%, `D_87`)
- 결측치가 극단적으로 높은 컬럼들은 "결측 자체가 정보"(예: 특정 상품 미보유)일 가능성이 있어 단순 삭제보다 결측 여부를 별도 feature로 만드는 방안을 Phase 3에서 검토

## 7. 로드/처리 속도 실측
| 작업 | 도구 | 소요 시간 | 비고 |
|---|---|---|---|
| customer_ID 고유값 카운트 | DuckDB (parquet 직접 쿼리) | 0.25s | 메모리 비적재 |
| 라벨 매칭 검증 (조인 포함) | DuckDB | 0.71s | 메모리 비적재 |
| 시계열 분포 집계 | DuckDB | 0.86s | 메모리 비적재 |
| 188개 컬럼 결측치 스캔 | DuckDB | 6.62s | 메모리 비적재 |
| **전체 데이터 pandas 로드** | pandas.read_parquet | **31.2s** | DataFrame 메모리 5.73GB |
| 고객별 최근 1개월 추출 (groupby+tail) | pandas | 5.91s | 로드 후 추가 연산 |

- pandas 전체 로드 시 프로세스 peak memory footprint: **약 9.65GB** (`/usr/bin/time -l` 측정, macOS 메모리 압축 포함 기준)
  - 검증 시작 시점 물리 메모리 여유가 468MB뿐이었던 것을 감안하면, 이 머신(8GB RAM)에서 pandas로 전체 데이터를 통째로 로드하는 것은 **실측상 체감될 정도로 느리고(31초, DuckDB 대비 40배+) 메모리 여유가 거의 없는 위험한 작업**임을 확인
  - swap-to-disk 발생은 없었으나(macOS 메모리 압축이 흡수), 다른 앱이 더 메모리를 쓰고 있었거나 Phase 3~4에서 feature engineering으로 컬럼이 늘어나는 시점에는 OOM 가능성이 높음

## 결론
1. 원본 데이터는 **샘플링되지 않은 전체 official train set**이 맞음
2. 데이터 품질(라벨 매칭, 스키마)은 문제 없음
3. **pandas 기반 전체 로드는 이 머신에서 실질적으로 위험/비효율** → customer_id 샘플링이 필요하다고 판단
4. DuckDB는 전체 데이터에 대해서도 빠르고 메모리 안전 → EDA/집계 단계에서는 계속 활용 가능하나, Phase 4 이후 scikit-learn/LightGBM/SHAP 등은 결국 in-memory 배열이 필요하므로 샘플링이 실질적으로 요구됨

## 8. 5만 명 stratified 샘플 검증

검증 환경: 재부팅 직후, 검증 시작 시점 여유 메모리 65MB (스크립트: [`scripts/validate_sample.py`](../scripts/validate_sample.py))
샘플 생성: [`scripts/build_sample.py`](../scripts/build_sample.py), target 비율 유지 stratified 5만 명
대상: `data/processed/train_sample_50k.parquet` (602,293행, 50,000명) vs `data/raw/train_data.parquet` (5,531,451행, 458,913명)

**참고**: 최초 생성본은 스키마 검증 과정에서 `__index_level_0__`(pandas 인덱스 잔재, §2/`decisions_pending_review.md` 참고)가 그대로 남아있는 것이 발견되어, `build_sample.py`에 `EXCLUDE (__index_level_0__)`를 추가해 샘플을 재생성했다. 아래 수치는 재생성 후 최종본 기준.

### 8.1 스키마
- 원본 192개(feature 188 + `customer_ID` + `S_2` + `target` + `__index_level_0__`) 중 `__index_level_0__`를 제외한 191개 컬럼이 샘플과 **완전 일치**
- 컬럼 순서/타입 포함 dtype 캐스팅 등 부작용 없음 확인

### 8.2 결측치 패턴 (50%+ 결측 컬럼)
| | 원본 | 샘플 |
|---|---|---|
| 188개 feature 중 결측 ≥50% 컬럼 수 | 30 | 30 |
| 두 집합 간 불일치 | — | **0개** (완전 동일한 30개 컬럼) |

→ 5만 명 샘플링으로 결측 패턴이 **전혀 왜곡되지 않음**. stratified sampling이 target 분포뿐 아니라 feature-level 결측 구조도 원본과 동일하게 보존함을 확인.

### 8.3 시계열 관측 비율 (13개월 풀 관측)
| | 원본 | 샘플 | 차이 |
|---|---|---|---|
| 풀(13개월) 관측 비율 | 84.12% (386,034/458,913) | 84.05% (42,023/50,000) | 0.07%p |

→ 원본과 사실상 동일한 수준으로 유지됨 (0.07%p는 5만 명 규모의 표본추출 변동 범위 내).

### 8.4 실행 리소스 (재부팅 후 여유 메모리 65~123MB 조건)
| 작업 | 프로세스 peak RSS | swap |
|---|---|---|
| 5만 명 샘플 생성 (build_sample.py, 최초) | ~825MB | 0 (swapins/swapouts) |
| 5만 명 샘플 재생성 (`__index_level_0__` 제외 반영 후) | ~993MB | 0 (swapins/swapouts) |
| 결측치/스키마/관측비율 검증 (validate_sample.py) | ~367~598MB | 0 (swapins/swapouts) |

→ 원본 3.2GB parquet에 대한 전체 컬럼 스캔(결측치 188개 컬럼 + 고객별 관측월 집계)까지 포함했지만 모두 `memory_limit=1GB` 안에서 처리되어 디스크 spill(`data/tmp_duckdb/`) 없이 완료. 여유 메모리가 65~123MB인 상황에서도 안전하게 실행 가능함을 재확인.

## 결론 (샘플 검증 추가)
5. 5만 명 stratified 샘플은 원본의 **결측 구조(30개 고결측 컬럼 100% 일치)**, **시계열 관측 비율(84.12% vs 84.05%)**, **클래스 비율(25.89% vs 25.89%)**을 모두 왜곡 없이 보존함 → Phase 2(EDA)부터는 `data/processed/train_sample_50k.parquet` 기준으로 안전하게 진행 가능
6. 스키마 검증 과정에서 `__index_level_0__` 잔재 컬럼이 샘플에도 그대로 복사돼 있던 것을 발견해 `build_sample.py`를 수정하고 샘플을 재생성함 (target 중복 이슈는 `docs/decisions_pending_review.md`에 보류 상태로 유지)
