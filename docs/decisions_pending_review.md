# 검토 대기 중인 결정 로그

구조적 중단 조건은 아니지만 판단이 필요했던 전처리/정제성 이슈를 합리적 기본값으로 처리하며 여기에 기록한다.
Phase 종료 시점 또는 사용자 요청 시 한 번에 몰아서 검토받는다.

형식: `- [Phase X] 이슈 요약 → 적용한 기본값과 근거`

- [Phase 1, 해결됨] `train_data.parquet`에 pandas 저장 잔재 컬럼 `__index_level_0__` 존재 → `train_sample_50k.parquet` 최초 생성본에도 그대로 남아있던 것을 발견해 `build_sample.py`에 `EXCLUDE (__index_level_0__)` 반영 후 재생성함 (191개 컬럼으로 확정). 원본(`data/raw/train_data.parquet`)에는 여전히 남아있으므로 향후 원본을 직접 로드하는 코드에서는 별도로 drop 필요
- [Phase 1] `train_data.parquet`에 `target` 컬럼이 이미 병합되어 있어 `train_labels.csv`와 값 불일치 0건 확인됨 → 이후 로드는 parquet 내장 target을 단일 소스로 사용, labels.csv는 검증용으로만 보관
- [Phase 1] 50k 샘플 생성 시 `train_sample_50k_labels.parquet`(customer_id+target)을 별도로도 저장함 → `train_sample_50k.parquet`에 이미 target이 포함돼 있어 엄밀히는 중복이지만, 용량이 작고(3.1MB) 라벨만 빠르게 조회할 때 편의성이 있어 일단 유지. 불필요 판단되면 삭제
