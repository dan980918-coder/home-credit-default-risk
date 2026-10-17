"""
03_split.py
Loan Approval Risk Scoring - v2 재분석
데이터 분할: application_train 307,511명을 TARGET 기준 층화추출로
학습 60% / 검증 20% / 최종평가 20%로 분할한다.

날짜 컬럼이 없어 시간순 분할은 불가능하므로 무작위 층화추출을 쓴다
(random_state=42). 최종평가(test) 세트는 이번 단계에서 TARGET을 열어보지 않는다.

실행: python3 -I v2/scripts/03_split.py
출력:
  v2/data/splits/train_ids.csv (SK_ID_CURR, TARGET)
  v2/data/splits/valid_ids.csv (SK_ID_CURR, TARGET)
  v2/data/splits/holdout_ids.csv (SK_ID_CURR만 - TARGET 미포함, 의도적)
  v2/docs/split_summary.json
"""
import json
import os
import duckdb
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
SPLIT_DIR = os.path.join(ROOT, "v2", "data", "splits")
os.makedirs(SPLIT_DIR, exist_ok=True)

p_train = os.path.join(RAW, "application_train.csv")
con = duckdb.connect()
df = con.execute(f"SELECT SK_ID_CURR, TARGET FROM read_csv_auto('{p_train}')").fetchdf()
con.close()

print(f"전체 신청자: {len(df):,}명, 전체 연체율: {df['TARGET'].mean()*100:.3f}%")

# 1차: train(60%) vs temp(40%), stratify by TARGET
train_df, temp_df = train_test_split(
    df, test_size=0.4, stratify=df["TARGET"], random_state=42
)
# 2차: temp(40%)를 valid(20%)/holdout(20%)로 균등 분할, stratify by TARGET
valid_df, holdout_df = train_test_split(
    temp_df, test_size=0.5, stratify=temp_df["TARGET"], random_state=42
)

assert len(set(train_df["SK_ID_CURR"]) & set(valid_df["SK_ID_CURR"])) == 0
assert len(set(train_df["SK_ID_CURR"]) & set(holdout_df["SK_ID_CURR"])) == 0
assert len(set(valid_df["SK_ID_CURR"]) & set(holdout_df["SK_ID_CURR"])) == 0
assert len(train_df) + len(valid_df) + len(holdout_df) == len(df)

train_df[["SK_ID_CURR", "TARGET"]].to_csv(os.path.join(SPLIT_DIR, "train_ids.csv"), index=False)
valid_df[["SK_ID_CURR", "TARGET"]].to_csv(os.path.join(SPLIT_DIR, "valid_ids.csv"), index=False)
# holdout: TARGET을 의도적으로 저장하지 않음 (이번 단계에서 절대 열어보지 않기 위함)
holdout_df[["SK_ID_CURR"]].to_csv(os.path.join(SPLIT_DIR, "holdout_ids.csv"), index=False)

summary = {
    "total": {"n": len(df), "target_rate_pct": round(df["TARGET"].mean() * 100, 3)},
    "train": {"n": len(train_df), "pct_of_total": round(len(train_df) / len(df) * 100, 2),
              "target_rate_pct": round(train_df["TARGET"].mean() * 100, 3)},
    "valid": {"n": len(valid_df), "pct_of_total": round(len(valid_df) / len(df) * 100, 2),
              "target_rate_pct": round(valid_df["TARGET"].mean() * 100, 3)},
    "holdout": {"n": len(holdout_df), "pct_of_total": round(len(holdout_df) / len(df) * 100, 2),
                "target_rate_pct_NOT_OPENED": "이번 단계에서 열람하지 않음 (holdout_ids.csv에 TARGET 미저장)"},
    "method": "TARGET 기준 층화추출(stratified), random_state=42",
    "note": "application_train에 절대 날짜 컬럼이 없어 시간순(time-based) 분할이 불가능하므로 무작위 층화추출을 사용했다. 최종 평가(holdout) 세트는 이번 단계에서 TARGET을 절대 열어보지 않는다.",
}

with open(os.path.join(ROOT, "v2", "docs", "split_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(json.dumps(summary, ensure_ascii=False, indent=2))
print("완료")
