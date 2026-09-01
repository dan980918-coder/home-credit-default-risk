"""
Phase 4: App-only / Lean(A) / Full(B) 3개 데이터셋 x 4개 모델(LogisticRegression,
RandomForest, XGBoost, LightGBM) 비교. class_weight/scale_pos_weight로 불균형
처리(TARGET 8.1%), ROC-AUC/Precision/Recall/F1 비교. 결과는 JSON으로 저장해
문서화 스크립트에서 활용.
"""
import json
import time
import duckdb
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score
import xgboost as xgb
from _preprocessing import clean_application_sql
from _train_common import prepare_categorical_columns, train_lightgbm

LEAN_A_PATH = "data/processed/train_features_leanA.parquet"
FULL_B_PATH = "data/processed/train_features_fullB.parquet"
RANDOM_STATE = 42

con = duckdb.connect()
app_only_cols = [r[0] for r in con.execute(
    f"DESCRIBE {clean_application_sql('data/raw/application_train.csv')}"
).fetchall()]


def load(path, restrict_cols=None):
    df = pd.read_parquet(path)
    if restrict_cols is not None:
        df = df[[c for c in restrict_cols if c in df.columns]]
    y = df["TARGET"].astype(int)
    X = df.drop(columns=["SK_ID_CURR", "TARGET"])
    X, cat_cols = prepare_categorical_columns(X)
    return X, y, cat_cols


def evaluate(y_true, y_prob, y_pred):
    return {
        "roc_auc": roc_auc_score(y_true, y_prob),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }


def run_dataset(name, path, restrict_cols=None):
    print(f"\n{'='*70}\n{name}\n{'='*70}")
    X, y, cat_cols = load(path, restrict_cols)
    print(f"shape={X.shape}, categorical cols={len(cat_cols)}")

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
    )
    n_pos = y_train.sum()
    n_neg = len(y_train) - n_pos
    scale_pos_weight = n_neg / n_pos
    print(f"train={X_train.shape}, val={X_val.shape}, scale_pos_weight={scale_pos_weight:.2f}")

    # --- 트리 모델용: category dtype 그대로 (XGBoost/LightGBM 네이티브 지원) ---
    Xt_train, Xt_val = X_train, X_val

    # --- LR/RF용: one-hot 인코딩 (train에 fit, val은 transform만) ---
    numeric_cols = [c for c in X.columns if c not in cat_cols]
    ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    ohe.fit(X_train[cat_cols].astype(str))
    ohe_train = ohe.transform(X_train[cat_cols].astype(str))
    ohe_val = ohe.transform(X_val[cat_cols].astype(str))
    ohe_cols = ohe.get_feature_names_out(cat_cols)

    Xo_train = pd.concat([
        X_train[numeric_cols].reset_index(drop=True).fillna(0),
        pd.DataFrame(ohe_train, columns=ohe_cols),
    ], axis=1)
    Xo_val = pd.concat([
        X_val[numeric_cols].reset_index(drop=True).fillna(0),
        pd.DataFrame(ohe_val, columns=ohe_cols),
    ], axis=1)
    print(f"one-hot shape: train={Xo_train.shape}")

    results = {}

    t0 = time.time()
    lr = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=RANDOM_STATE)
    lr.fit(Xo_train, y_train)
    prob = lr.predict_proba(Xo_val)[:, 1]
    pred = (prob >= 0.5).astype(int)
    results["LogisticRegression"] = {**evaluate(y_val, prob, pred), "elapsed": time.time() - t0}
    print(f"[LogisticRegression] {results['LogisticRegression']}")

    t0 = time.time()
    rf = RandomForestClassifier(n_estimators=100, class_weight="balanced",
                                 n_jobs=-1, random_state=RANDOM_STATE)
    rf.fit(Xo_train, y_train)
    prob = rf.predict_proba(Xo_val)[:, 1]
    pred = (prob >= 0.5).astype(int)
    results["RandomForest"] = {**evaluate(y_val, prob, pred), "elapsed": time.time() - t0}
    print(f"[RandomForest] {results['RandomForest']}")

    t0 = time.time()
    xgb_clf = xgb.XGBClassifier(
        n_estimators=200, tree_method="hist", enable_categorical=True,
        scale_pos_weight=scale_pos_weight, random_state=RANDOM_STATE, eval_metric="auc",
    )
    xgb_clf.fit(Xt_train, y_train)
    prob = xgb_clf.predict_proba(Xt_val)[:, 1]
    pred = (prob >= 0.5).astype(int)
    results["XGBoost"] = {**evaluate(y_val, prob, pred), "elapsed": time.time() - t0}
    print(f"[XGBoost] {results['XGBoost']}")

    t0 = time.time()
    lgbm = train_lightgbm(Xt_train, y_train, scale_pos_weight, random_state=RANDOM_STATE,
                           categorical_feature=cat_cols if cat_cols else "auto")
    prob = lgbm.predict_proba(Xt_val)[:, 1]
    pred = (prob >= 0.5).astype(int)
    results["LightGBM"] = {**evaluate(y_val, prob, pred), "elapsed": time.time() - t0}
    print(f"[LightGBM] {results['LightGBM']}")

    return results


all_results = {}
all_results["App-only"] = run_dataset("App-only (application_train만)", LEAN_A_PATH, app_only_cols)
all_results["Lean(A)"] = run_dataset("Lean(A) (application + 신용이력 요약)", LEAN_A_PATH)
all_results["Full(B)"] = run_dataset("Full(B) (application + 신용이력 전체 통계량)", FULL_B_PATH)

with open("data/processed/phase4_modeling_results.json", "w") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)
print("\nwrote data/processed/phase4_modeling_results.json")

print(f"\n{'='*70}\nSUMMARY (ROC-AUC)\n{'='*70}")
for ds, models in all_results.items():
    for model, m in models.items():
        print(f"{ds:12s} {model:20s} AUC={m['roc_auc']:.4f} P={m['precision']:.4f} "
              f"R={m['recall']:.4f} F1={m['f1']:.4f}")
