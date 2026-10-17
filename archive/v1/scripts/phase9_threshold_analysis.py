"""
Phase 9: 임계값별 심사 시나리오 분석.

Phase 4/7과 동일한 모델(models/lean_a_lightgbm_holdout_v1.joblib)과 동일한
held-out 데이터(data/processed/monitoring_holdout.parquet, 80/20 stratified
split, random_state=42)를 그대로 사용한다. 이 모델은 학습 때 이 61,503명을
전혀 보지 않았고(Phase 7 참고), held-out AUC가 0.7833으로 Phase 4 검증치
(0.7825)와 근접해 재학습 없이 그대로 임계값 분석에 쓸 수 있다.

임계값(threshold)을 0.1~0.9(0.05 간격)로 바꾸며 승인율/승인군 연체율/
거절군 연체율/Recall/Precision/승인 대출금 중 연체 건 금액 비중을 계산하고,
승인율 90% 유지 / 승인군 연체율 5% 이하 / Recall 70% 이상 3개 운영 시나리오의
임계값을 찾는다.

주의: 손실률(LGD)·금리 등 금융 가정은 넣지 않는다. 금액 지표는 "승인 대출금 중
연체 건 금액 비중"까지만 계산하며, 이는 실제 손실액이 아니다.
"""
import json

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

MODEL_PATH = "models/lean_a_lightgbm_holdout_v1.joblib"
HOLDOUT_PATH = "data/processed/monitoring_holdout.parquet"
OUT_JSON = "data/processed/phase9_threshold_results.json"
OUT_FIG = "assets/figures/threshold_tradeoff.png"

model = joblib.load(MODEL_PATH)
df = pd.read_parquet(HOLDOUT_PATH)
y = df["TARGET"].astype(int)
amt_credit = df["AMT_CREDIT"]
X = df.drop(columns=["TARGET"])
if "SK_ID_CURR" in X.columns:
    X = X.drop(columns=["SK_ID_CURR"])

proba = model.predict_proba(X)[:, 1]
holdout_auc = roc_auc_score(y, proba)
base_rate = y.mean()
print(f"held-out AUC: {holdout_auc:.4f} (Phase 4 기준 0.7825, Phase 7 기준 0.7833)")
print(f"기저 연체율: {base_rate:.4f}")

rows = []
for t in np.arange(0.10, 0.901, 0.05):
    t = round(t, 2)
    pred_reject = proba >= t  # 고위험(연체 예측)으로 판정 -> 거절
    pred_approve = ~pred_reject

    n_total = len(y)
    n_approve = pred_approve.sum()
    approval_rate = n_approve / n_total

    approve_default_rate = y[pred_approve].mean() if n_approve > 0 else np.nan
    n_reject = pred_reject.sum()
    reject_default_rate = y[pred_reject].mean() if n_reject > 0 else np.nan

    tp = ((pred_reject) & (y == 1)).sum()
    fn = ((pred_approve) & (y == 1)).sum()
    fp = ((pred_reject) & (y == 0)).sum()
    recall = tp / (tp + fn) if (tp + fn) > 0 else np.nan
    precision = tp / (tp + fp) if (tp + fp) > 0 else np.nan

    approve_credit_total = amt_credit[pred_approve].sum()
    approve_credit_default = amt_credit[pred_approve & (y == 1)].sum()
    credit_default_share = (
        approve_credit_default / approve_credit_total if approve_credit_total > 0 else np.nan
    )

    rows.append({
        "threshold": t,
        "approval_rate": round(approval_rate, 4),
        "approve_default_rate": round(float(approve_default_rate), 4),
        "reject_default_rate": round(float(reject_default_rate), 4),
        "recall": round(float(recall), 4),
        "precision": round(float(precision), 4),
        "approve_credit_default_share": round(float(credit_default_share), 4),
    })

result_df = pd.DataFrame(rows)
print(result_df.to_string(index=False))

# 운영 시나리오 3개
scenario_90_approval = result_df.iloc[(result_df["approval_rate"] - 0.90).abs().argsort()[:1]]
candidates_5pct = result_df[result_df["approve_default_rate"] <= 0.05]
scenario_5pct_default = (
    candidates_5pct.sort_values("approval_rate", ascending=False).head(1)
    if len(candidates_5pct) > 0 else None
)
candidates_recall70 = result_df[result_df["recall"] >= 0.70]
scenario_recall70 = (
    candidates_recall70.sort_values("approval_rate", ascending=False).head(1)
    if len(candidates_recall70) > 0 else None
)

scenarios = {
    "approval_90pct": scenario_90_approval.to_dict(orient="records")[0],
    "approve_default_5pct_or_less": (
        scenario_5pct_default.to_dict(orient="records")[0] if scenario_5pct_default is not None else None
    ),
    "recall_70pct_or_more": (
        scenario_recall70.to_dict(orient="records")[0] if scenario_recall70 is not None else None
    ),
}
print(json.dumps(scenarios, indent=2, ensure_ascii=False))

with open(OUT_JSON, "w") as f:
    json.dump({
        "holdout_auc": round(float(holdout_auc), 4),
        "base_rate": round(float(base_rate), 4),
        "table": rows,
        "scenarios": scenarios,
    }, f, indent=2, ensure_ascii=False)
print(f"saved {OUT_JSON}")

# 트레이드오프 그림: x=승인율, y=승인군 연체율
fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
ax.plot(result_df["approval_rate"] * 100, result_df["approve_default_rate"] * 100, marker="o", color="#2a5d9f")
ax.axhline(base_rate * 100, color="gray", linestyle="--", linewidth=1, label=f"전체 기저 연체율 {base_rate*100:.1f}%")
ax.set_xlabel("승인율 (%)")
ax.set_ylabel("승인군 연체율 (%)")
ax.set_title("임계값에 따른 승인율-승인군 연체율 트레이드오프")
ax.legend()
ax.invert_xaxis()
fig.tight_layout()
fig.savefig(OUT_FIG)
print(f"saved {OUT_FIG}")
