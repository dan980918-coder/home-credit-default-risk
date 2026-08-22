# Feature Engineering — Option B (Full, 커뮤니티 표준)

Option A(Lean)와 동일한 조인 순서로, 모든 수치형 컬럼에 mean/max/min/sum을 자동 적용(DuckDB 스키마에서 dtype 자동 판별). 범주형은 Option A와 동일한 최소 처리만 유지(원-핫 미적용) — 순수 원-핫까지 다 하면 유명 공개 커널 기준 수천 컬럼까지 커질 수 있어, "A vs B 성능 비교"라는 목적에는 수치형 통계 확장만으로 충분하다고 판단.

스크립트: [`scripts/build_features_fullB.py`](../scripts/build_features_fullB.py)
전처리: Option A와 동일하게 [`scripts/_preprocessing.py`](../scripts/_preprocessing.py)의 `DAYS_EMPLOYED` anomaly 처리(365243→NULL + `DAYS_EMPLOYED_ANOMALY` 플래그) 적용.

## 결과

| | shape |
|---|---|
| `data/processed/train_features_fullB.parquet` | 307,511행 × **392컬럼** |
| `data/processed/test_features_fullB.parquet` | 48,744행 × 391컬럼 (TARGET 없음) |

Lean(A) 163컬럼 대비 약 2.4배. `DAYS_EMPLOYED=365243` 잔존 0건, `DAYS_EMPLOYED_ANOMALY` 컬럼 존재 확인함.

## 메모리: 두 차례 OOM 발생, 둘 다 안전하게 복구

AMEX Phase 3에서 겪었던 것과 같은 패턴(컬럼 수가 많아지면 단일 GROUP BY 쿼리가 memory_limit을 넘김)이 이번엔 **두 단계**에서 발생함. 둘 다 DuckDB가 설정된 한도 내에서 스스로 멈춘 것으로, 시스템이 실제로 위험했던 적은 없음(unused가 매번 수백MB~1GB대로 회복).

| 단계 | 증상 | 조치 |
|---|---|---|
| 4) previous_application 최종 집계 (209개 집계식) | `memory_limit=1.5GB`에서 1.3GB 지점 OOM | AMEX와 동일하게 블록별(자체 통계/ccb rollup/pos rollup/inst rollup) 분리 집계 후 join으로 재작성 |
| 5) application + bureau_agg_full + prev_agg_full 최종 join (~390컬럼 wide join) | `memory_limit=1.5GB`에서 1.3GB 지점 OOM | `memory_limit=2GB` + `threads=1`로 재시도해 성공 (peak RSS 1,539MB) |

**5단계는 이번 프로젝트에서 처음으로 실제 swap이 유의미하게 발생한 지점**(뒤이은 벤치마크 실행에서 748MB까지 상승, §벤치마크 참고) — 컬럼 수가 늘어날수록 DuckDB의 hash join 빌드 사이드가 커지는 게 근본 원인으로 보임. Phase 4에서 Full(B) 기반 작업을 더 할 경우 이 점을 계속 염두에 둬야 함.

## 다음
- Option A vs Option B 벤치마크 → [`docs/phase3_benchmark.md`](phase3_benchmark.md)
