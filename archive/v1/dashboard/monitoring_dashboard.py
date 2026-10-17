"""
Phase 7: 모니터링 대시보드 (Streamlit).

실제 운영 로그가 없어서 application_train을 배치로 나눠 "시간에 따라
데이터가 들어온다"를 시뮬레이션한다. 두 모드를 토글로 제공:
  - 무작위 배치(정상 상태 대조군): drift 지표가 오탐 없이 안정적으로 나오는지 확인
  - 의도적 드리프트 주입(synthetic): 특정 feature로 정렬해 배치를 나눠
    실제로 분포가 바뀌었을 때 지표가 반응하는지 보여주는 데모용

주의: Home Credit 데이터는 날짜가 전부 "신청 시점 기준 상대값"으로 익명화돼
있어 진짜 시간 컬럼이 없다(SK_ID_CURR 순서도 실측 결과 무작위와 다르지 않음 —
docs/phase7_monitoring.md 참고). 따라서 여기서의 "배치"는 실제 시간 흐름이
아니라 시뮬레이션이라는 점을 항상 명시한다.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from sklearn.metrics import roc_auc_score
import joblib

from drift_metrics import (
    psi_continuous, psi_categorical, ks_test, psi_status,
    PSI_STATUS_COLOR, PSI_STATUS_LABEL_KO, PSI_STABLE, PSI_WARNING,
)
from _train_common import prepare_categorical_columns

DATA_PATH = "data/processed/monitoring_holdout.parquet"
MODEL_PATH = "models/lean_a_lightgbm_holdout_v1.joblib"
RANDOM_STATE = 42
REFERENCE_FRAC = 0.6

MONITORED_FEATURES = [
    ("EXT_SOURCE_1", "continuous"),
    ("EXT_SOURCE_2", "continuous"),
    ("EXT_SOURCE_3", "continuous"),
    ("AMT_INCOME_TOTAL", "continuous"),
    ("AMT_CREDIT", "continuous"),
    ("DAYS_BIRTH", "continuous"),
    ("bureau_debt_credit_ratio", "continuous"),
    ("ccb_utilization_mean_mean", "continuous"),
    ("NAME_EDUCATION_TYPE", "categorical"),
]

st.set_page_config(page_title="Home Credit 모니터링 대시보드 (Phase 7)", layout="wide")


@st.cache_resource
def load_model():
    return joblib.load(MODEL_PATH)


@st.cache_data
def load_data():
    df = pd.read_parquet(DATA_PATH)
    model = load_model()
    X = df.drop(columns=["SK_ID_CURR", "TARGET"]).copy()
    X, _ = prepare_categorical_columns(X)
    df["_pred_proba"] = model.predict_proba(X)[:, 1]
    return df


def make_reference_and_pool(df: pd.DataFrame):
    rng = np.random.RandomState(RANDOM_STATE)
    idx = rng.permutation(len(df))
    n_ref = int(len(df) * REFERENCE_FRAC)
    ref_idx, pool_idx = idx[:n_ref], idx[n_ref:]
    return df.iloc[ref_idx].reset_index(drop=True), df.iloc[pool_idx].reset_index(drop=True)


def split_into_batches(pool: pd.DataFrame, mode: str, n_batches: int, sort_feature: str | None):
    if mode == "synthetic":
        pool = pool.sort_values(sort_feature, na_position="last").reset_index(drop=True)
    else:
        pool = pool.sample(frac=1.0, random_state=RANDOM_STATE).reset_index(drop=True)
    return np.array_split(pool, n_batches)


def compute_batch_metrics(reference: pd.DataFrame, batches: list[pd.DataFrame]):
    rows = []
    for i, batch in enumerate(batches):
        row = {"batch": i + 1, "n": len(batch)}

        ref_p = reference["_pred_proba"].dropna().values
        batch_p = batch["_pred_proba"].dropna().values
        row["pred_proba_psi"] = psi_continuous(ref_p, batch_p)
        ks_stat, ks_p = ks_test(ref_p, batch_p)
        row["pred_proba_ks"] = ks_stat
        row["pred_proba_ks_p"] = ks_p
        row["pred_proba_mean"] = float(np.mean(batch_p))

        if batch["TARGET"].nunique() == 2:
            row["auc"] = roc_auc_score(batch["TARGET"], batch["_pred_proba"])
        else:
            row["auc"] = float("nan")

        for feat, kind in MONITORED_FEATURES:
            ref_vals = reference[feat].dropna().values
            batch_vals = batch[feat].dropna().values
            if kind == "continuous":
                row[f"{feat}__psi"] = psi_continuous(ref_vals, batch_vals)
                ks_s, ks_pv = ks_test(ref_vals, batch_vals)
                row[f"{feat}__ks"] = ks_s
                row[f"{feat}__ks_p"] = ks_pv
            else:
                row[f"{feat}__psi"] = psi_categorical(ref_vals, batch_vals)
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------- UI ----------------
st.title("Home Credit Default Risk — 모니터링 대시보드")
st.caption("Phase 7. 최종 모델: Lean(A) + LightGBM. 실제 운영 로그가 없어 application_train을 배치로 나눠 시뮬레이션합니다.")

with st.sidebar:
    st.header("설정")
    mode_label = st.radio(
        "배치 분할 모드",
        ["무작위 배치 (정상 상태 대조군)", "의도적 드리프트 주입 (synthetic)"],
        index=0,
    )
    mode = "synthetic" if mode_label.startswith("의도적") else "random"
    n_batches = st.slider("배치 개수", min_value=3, max_value=15, value=8)
    sort_feature = None
    if mode == "synthetic":
        sort_feature = st.selectbox(
            "정렬 기준 feature (배치별로 이 값이 점점 커지도록 정렬)",
            ["EXT_SOURCE_2", "EXT_SOURCE_1", "EXT_SOURCE_3", "AMT_INCOME_TOTAL", "AMT_CREDIT", "DAYS_BIRTH"],
            index=0,
        )
    st.markdown("---")
    st.markdown(
        "**PSI 임계값**\n"
        f"- < {PSI_STABLE}: 안정\n"
        f"- {PSI_STABLE}~{PSI_WARNING}: 주의\n"
        f"- > {PSI_WARNING}: 경고(심각한 drift)"
    )

if mode == "synthetic":
    st.error(
        f"⚠️ **SYNTHETIC / 의도적 드리프트 주입 모드** — 배치가 `{sort_feature}` 기준으로 정렬되어 나뉘어 있습니다. "
        "이는 drift 감지 지표가 실제로 작동하는지 보여주기 위해 **인위적으로 구성한 시나리오**이며, "
        "실제 시간 흐름에 따른 드리프트가 아닙니다."
    )
else:
    st.success(
        "✅ **무작위 배치 모드(정상 상태 대조군)** — 배치는 무작위로 나뉘어 있어 실제로는 드리프트가 없어야 합니다. "
        "여기서 PSI/KS가 낮게 나오는 것이 지표가 오탐하지 않는다는 근거가 됩니다."
    )

st.caption(
    "**방법론**: 여기서 쓰는 모델은 Phase 5 서빙 모델(전체 100% 학습)이 아니라, "
    "Phase 4와 동일한 레시피(80/20 split, random_state=42)로 **80%만 학습한 별도 모델**입니다 — "
    "그래야 나머지 20%(61,503명)가 모델이 한 번도 보지 못한 진짜 held-out이 되어 AUC 추적이 의미가 있습니다 "
    "(서빙 모델로 전체 데이터를 평가하면 in-sample이라 AUC가 0.80~0.86으로 부풀려짐을 실제로 확인함). "
    "이 61,503명을 무작위로 reference(60%)와 모니터링 풀(40%)로 나눈 뒤, 모니터링 풀을 위 설정대로 N개 배치로 분할합니다. "
    "Home Credit 데이터는 날짜가 전부 신청 시점 기준 상대값으로 익명화되어 있어 진짜 시간 컬럼이 없고, "
    "SK_ID_CURR 순서도 실측 결과 무작위와 다르지 않아(docs/phase7_monitoring.md) 시간순 프록시로 쓰지 않았습니다."
)

df = load_data()
reference, pool = make_reference_and_pool(df)
batches = split_into_batches(pool, mode, n_batches, sort_feature)
metrics = compute_batch_metrics(reference, batches)

# ---- 1) 예측 확률 분포 변화 ----
st.header("1. 배치별 예측 확률 분포 변화")
col1, col2 = st.columns([2, 1])
with col1:
    fig = go.Figure()
    for i, batch in enumerate(batches):
        fig.add_trace(go.Box(y=batch["_pred_proba"], name=f"배치{i+1}", boxpoints=False))
    fig.add_hline(y=float(reference["_pred_proba"].mean()), line_dash="dash",
                  annotation_text="reference 평균", line_color="gray")
    fig.update_layout(yaxis_title="예측 연체 확률", height=400)
    st.plotly_chart(fig, use_container_width=True)
with col2:
    st.metric("Reference 평균 예측 확률", f"{reference['_pred_proba'].mean():.4f}")
    worst = metrics.loc[metrics["pred_proba_psi"].idxmax()]
    st.metric(f"최대 PSI (배치{int(worst['batch'])})", f"{worst['pred_proba_psi']:.4f}",
               delta=psi_status(worst["pred_proba_psi"]))

pp_table = metrics[["batch", "n", "pred_proba_mean", "pred_proba_psi", "pred_proba_ks", "pred_proba_ks_p"]].copy()
pp_table["status"] = pp_table["pred_proba_psi"].apply(lambda v: PSI_STATUS_LABEL_KO[psi_status(v)])
st.dataframe(
    pp_table.style.apply(
        lambda r: [f"background-color:{PSI_STATUS_COLOR[psi_status(r['pred_proba_psi'])]}33"] * len(r), axis=1
    ),
    use_container_width=True,
)

# ---- 2) feature drift ----
st.header("2. 주요 feature 분포 drift (PSI 히트맵)")
psi_matrix = metrics[["batch"] + [f"{f}__psi" for f, _ in MONITORED_FEATURES]].set_index("batch")
psi_matrix.columns = [f for f, _ in MONITORED_FEATURES]
fig2 = px.imshow(
    psi_matrix.T, aspect="auto", color_continuous_scale="RdYlGn_r",
    zmin=0, zmax=0.4, labels=dict(x="배치", y="feature", color="PSI"),
    text_auto=".2f",
)
fig2.update_layout(height=400)
st.plotly_chart(fig2, use_container_width=True)

# ---- 3) 배치별 실제 AUC ----
st.header("3. 배치별 실제 AUC 추적")
st.caption("이 시뮬레이션은 application_train의 TARGET을 이미 알고 있어 실제 AUC를 바로 계산합니다. "
           "실제 운영에서는 라벨(연체 여부 확정)이 지연 도착해 AUC 추적 자체에 시차가 발생한다는 점에 유의.")
fig3 = go.Figure()
fig3.add_trace(go.Scatter(x=metrics["batch"], y=metrics["auc"], mode="lines+markers", name="배치별 AUC"))
fig3.add_hline(y=0.7825, line_dash="dash", line_color="gray",
               annotation_text="Phase 4 검증 AUC(0.7825, 80/20 split 기준)")
fig3.update_layout(xaxis_title="배치", yaxis_title="AUC", height=350)
st.plotly_chart(fig3, use_container_width=True)

# ---- 4) 경고 ----
st.header("4. Drift 경고")
alerts = []
for _, row in metrics.iterrows():
    if row["pred_proba_psi"] > PSI_WARNING:
        alerts.append(f"배치 {int(row['batch'])}: 예측 확률 분포 PSI={row['pred_proba_psi']:.3f} (경고 임계값 {PSI_WARNING} 초과)")
    for feat, _ in MONITORED_FEATURES:
        v = row[f"{feat}__psi"]
        if v > PSI_WARNING:
            alerts.append(f"배치 {int(row['batch'])}: `{feat}` PSI={v:.3f} (경고 임계값 {PSI_WARNING} 초과)")

if alerts:
    st.warning(f"🚨 총 {len(alerts)}건의 경고 임계값 초과 발견")
    for a in alerts:
        st.markdown(f"- {a}")
else:
    st.info("경고 임계값(PSI > 0.25)을 초과한 배치/feature가 없습니다.")

with st.expander("전체 지표 원본 테이블"):
    st.dataframe(metrics, use_container_width=True)
