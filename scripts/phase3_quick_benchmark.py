"""
Phase 3: baseline A(최근 1개월 스냅샷) vs main B(mean/std/last/delta 파생)를
LightGBM 기본 하이퍼파라미터 + 5-fold CV로 빠르게 비교. 본격 튜닝은 Phase 4.
"""
import time
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import StratifiedKFold, cross_val_score

A_PATH = "data/processed/train_features_baseline_A.parquet"
B_PATH = "data/processed/train_features_main_B.parquet"
CATEGORICAL = ["D_63", "D_64"]  # A: 원본 이름, B: *_last로 처리


def prep_A():
    df = pd.read_parquet(A_PATH)
    y = df["target"]
    X = df.drop(columns=["customer_ID", "target"])
    for c in CATEGORICAL:
        X[c] = X[c].astype("category")
    return X, y


def prep_B():
    df = pd.read_parquet(B_PATH)
    y = df["target"]
    X = df.drop(columns=["customer_ID", "target"])
    for c in ["D_63_last", "D_64_last"]:
        X[c] = X[c].astype("category")
    return X, y


def run_cv(X, y, label):
    t0 = time.time()
    clf = lgb.LGBMClassifier(random_state=42, verbosity=-1)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(clf, X, y, cv=cv, scoring="roc_auc", n_jobs=1)
    elapsed = time.time() - t0
    print(f"[{label}] shape={X.shape}  AUC per fold={[round(s,4) for s in scores]}")
    print(f"[{label}] mean AUC={scores.mean():.4f}  std={scores.std():.4f}  elapsed={elapsed:.1f}s")
    return scores


X_a, y_a = prep_A()
scores_a = run_cv(X_a, y_a, "A (baseline, 최근 1개월)")

X_b, y_b = prep_B()
scores_b = run_cv(X_b, y_b, "B (main, mean/std/last/delta)")

print(f"\n차이 (B - A): {scores_b.mean() - scores_a.mean():+.4f}")
