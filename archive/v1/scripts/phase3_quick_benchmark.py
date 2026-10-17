"""
Phase 3 quick 벤치마크: App-only(application_train만) vs Lean(A) vs Full(B)
LightGBM 기본 하이퍼파라미터 + 5-fold CV로 AUC만 빠르게 비교. 본격 튜닝은 Phase 4.
Phase 4 계획에 App-only vs Lean(A) 비교를 넣어달라는 요청에 맞춰 3-way로 확인.
"""
import time
import duckdb
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import StratifiedKFold, cross_val_score
from _preprocessing import clean_application_sql

LEAN_A_PATH = "data/processed/train_features_leanA.parquet"
FULL_B_PATH = "data/processed/train_features_fullB.parquet"

con = duckdb.connect()
app_only_cols = [r[0] for r in con.execute(
    f"DESCRIBE {clean_application_sql('data/raw/application_train.csv')}"
).fetchall()]


def prep(path, restrict_cols=None):
    df = pd.read_parquet(path)
    if restrict_cols is not None:
        df = df[[c for c in restrict_cols if c in df.columns]]
    y = df["TARGET"]
    X = df.drop(columns=["SK_ID_CURR", "TARGET"])
    for c in X.columns:
        if X[c].dtype == object or str(X[c].dtype) == "bool":
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


X_app, y_app = prep(LEAN_A_PATH, restrict_cols=app_only_cols)
scores_app = run_cv(X_app, y_app, "App-only (application_train만)")

X_a, y_a = prep(LEAN_A_PATH)
scores_a = run_cv(X_a, y_a, "Lean(A) (application + 신용이력 요약)")

X_b, y_b = prep(FULL_B_PATH)
scores_b = run_cv(X_b, y_b, "Full(B) (application + 신용이력 전체 통계량)")

print(f"\nApp-only -> Lean(A): {scores_a.mean() - scores_app.mean():+.4f}")
print(f"Lean(A) -> Full(B):  {scores_b.mean() - scores_a.mean():+.4f}")
print(f"App-only -> Full(B): {scores_b.mean() - scores_app.mean():+.4f}")
