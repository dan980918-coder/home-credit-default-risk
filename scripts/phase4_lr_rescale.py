"""
Phase 4 후속: LogisticRegression만 StandardScaler 추가해 재검증.
phase4_modeling.py와 동일한 데이터 로드/split/one-hot 로직 재사용,
LR 앞에 StandardScaler만 추가. RF/XGBoost/LightGBM은 트리 기반이라
스케일링 영향이 없어 재실행하지 않음.
"""
import json
import time
import duckdb
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score
from _preprocessing import clean_application_sql
from _train_common import prepare_categorical_columns

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


def run_lr_scaled(name, path, restrict_cols=None):
    print(f"\n{'='*70}\n{name}\n{'='*70}")
    X, y, cat_cols = load(path, restrict_cols)
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
    )

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

    scaler = StandardScaler()
    Xs_train = scaler.fit_transform(Xo_train)
    Xs_val = scaler.transform(Xo_val)

    t0 = time.time()
    lr = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=RANDOM_STATE)
    lr.fit(Xs_train, y_train)
    prob = lr.predict_proba(Xs_val)[:, 1]
    pred = (prob >= 0.5).astype(int)
    result = {**evaluate(y_val, prob, pred), "elapsed": time.time() - t0}
    print(f"[LogisticRegression + StandardScaler] {result}")
    return result


results = {}
results["App-only"] = run_lr_scaled("App-only (application_train만)", LEAN_A_PATH, app_only_cols)
results["Lean(A)"] = run_lr_scaled("Lean(A) (application + 신용이력 요약)", LEAN_A_PATH)
results["Full(B)"] = run_lr_scaled("Full(B) (application + 신용이력 전체 통계량)", FULL_B_PATH)

with open("data/processed/phase4_lr_rescale_results.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("\nwrote data/processed/phase4_lr_rescale_results.json")

print(f"\n{'='*70}\nSUMMARY\n{'='*70}")
for ds, m in results.items():
    print(f"{ds:12s} AUC={m['roc_auc']:.4f} P={m['precision']:.4f} R={m['recall']:.4f} F1={m['f1']:.4f}")
