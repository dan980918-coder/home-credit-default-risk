"""
POST /predict/live 용: 요청 페이로드(application + 선택적 bureau/previous_application
이력)를 원본 CSV와 동일한 스키마의 in-memory DataFrame으로 변환하고, DuckDB에
등록한 뒤 scripts/_lean_a_features.py의 SQL을 그대로 재사용해 배치 파이프라인
(build_features_leanA.py)과 동일한 로직으로 1명분 Lean(A) feature row를 만든다.

합성 키: 실시간 신청자는 실제 SK_ID_CURR/SK_ID_PREV/SK_ID_BUREAU가 없으므로
요청 내에서만 유효한 음수 합성 ID를 부여해 그룹핑/조인이 올바르게 되도록 한다.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import duckdb
import pandas as pd

from _lean_a_features import (
    bb_agg_sql, bureau_agg_sql, ccb_agg_sql, pos_agg_sql, inst_agg_sql,
    prev_agg_sql, final_join_sql,
)

RAW = "data/raw"
SYNTHETIC_SK_ID_CURR = -1

NUMERIC_TYPES = {"BIGINT", "DOUBLE", "FLOAT", "INTEGER", "SMALLINT", "TINYINT", "HUGEINT", "DECIMAL"}

_schema_cache: dict[str, list[tuple[str, str]]] = {}


def _get_csv_schema(con: duckdb.DuckDBPyConnection, csv_name: str) -> list[tuple[str, str]]:
    if csv_name not in _schema_cache:
        rows = con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{RAW}/{csv_name}.csv')").fetchall()
        _schema_cache[csv_name] = [(r[0], r[1]) for r in rows]
    return _schema_cache[csv_name]


def _is_numeric_dtype(dtype: str) -> bool:
    return any(dtype.upper().startswith(t) for t in NUMERIC_TYPES)


def _coerce(value, dtype: str):
    if value is None:
        return None
    if _is_numeric_dtype(dtype):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return str(value)


def _empty_typed_df(schema: list[tuple[str, str]]) -> pd.DataFrame:
    """0행이라도 DuckDB가 컬럼 타입을 정확히 알아야(빈 numeric 컬럼에 avg()를
    쓰는 등) 쿼리 플래닝이 실패하지 않으므로, dtype을 명시적으로 지정."""
    cols = {}
    for col, dtype in schema:
        cols[col] = pd.Series(dtype="float64" if _is_numeric_dtype(dtype) else "object")
    return pd.DataFrame(cols)


def _cast_df_to_schema(df: pd.DataFrame, schema: list[tuple[str, str]]) -> pd.DataFrame:
    for col, dtype in schema:
        if col in df.columns:
            df[col] = df[col].astype("float64" if _is_numeric_dtype(dtype) else "object")
    return df


def _records_to_df(con, csv_name: str, records: list[dict], overrides: dict) -> pd.DataFrame:
    """records(list of raw-column dicts)를 csv_name의 원본 스키마와 동일한 컬럼
    구성의 DataFrame으로 변환. overrides에 지정된 컬럼은 요청값 대신 합성 ID로 덮어씀
    (overrides[col]가 리스트면 레코드별로, 아니면 전체 동일값). 값이 전부 None인
    numeric 컬럼도 pandas가 object로 추론하지 않도록 dtype을 명시적으로 맞춘다."""
    schema = _get_csv_schema(con, csv_name)
    if not records:
        return _empty_typed_df(schema)
    rows = []
    for i, rec in enumerate(records):
        row = {}
        for col, dtype in schema:
            if col in overrides:
                ov = overrides[col]
                row[col] = ov[i] if isinstance(ov, list) else ov
            else:
                row[col] = _coerce(rec.get(col), dtype)
        rows.append(row)
    return _cast_df_to_schema(pd.DataFrame(rows), schema)


def build_live_feature_row(payload: dict) -> pd.DataFrame:
    """payload: {"application": {...}, "bureau_records": [...], "previous_application_records": [...]}
    -> Lean(A) feature 1행 DataFrame (SK_ID_CURR, has_bureau_record, has_previous_application 포함)"""
    con = duckdb.connect()

    application = payload.get("application") or {}
    bureau_records = payload.get("bureau_records") or []
    prev_records = payload.get("previous_application_records") or []

    # ---------- application: 1행, SK_ID_CURR 합성 + DAYS_EMPLOYED anomaly 처리 ----------
    app_schema = _get_csv_schema(con, "application_test")  # TARGET 없는 스키마가 입력에 맞음
    app_row = {col: _coerce(application.get(col), dtype) for col, dtype in app_schema}
    app_row["SK_ID_CURR"] = SYNTHETIC_SK_ID_CURR
    raw_days_employed = app_row.get("DAYS_EMPLOYED")
    is_anomaly = raw_days_employed == 365243
    app_row["DAYS_EMPLOYED_ANOMALY"] = bool(is_anomaly)
    if is_anomaly:
        app_row["DAYS_EMPLOYED"] = None
    app_df = _cast_df_to_schema(pd.DataFrame([app_row]), app_schema + [("DAYS_EMPLOYED_ANOMALY", "BOOLEAN")])
    con.register("application_live", app_df)

    # ---------- bureau: SK_ID_CURR/SK_ID_BUREAU 합성. bureau_balance는 스펙상 미지원(빈 테이블) ----------
    bureau_sk_id_bureau = [-(i + 1) for i in range(len(bureau_records))]
    bureau_df = _records_to_df(
        con, "bureau", bureau_records,
        overrides={"SK_ID_CURR": SYNTHETIC_SK_ID_CURR, "SK_ID_BUREAU": bureau_sk_id_bureau},
    )
    con.register("bureau_live", bureau_df)

    bb_schema = _get_csv_schema(con, "bureau_balance")
    bb_df = _empty_typed_df(bb_schema)
    con.register("bureau_balance_live", bb_df)

    # ---------- previous_application + 중첩된 installments/credit_card/pos_cash ----------
    prev_sk_id_prev = [-(i + 1) for i in range(len(prev_records))]
    prev_df = _records_to_df(
        con, "previous_application", prev_records,
        overrides={"SK_ID_CURR": SYNTHETIC_SK_ID_CURR, "SK_ID_PREV": prev_sk_id_prev},
    )
    con.register("previous_application_live", prev_df)

    inst_flat, ccb_flat, pos_flat = [], [], []
    inst_sk_id_prev, ccb_sk_id_prev, pos_sk_id_prev = [], [], []
    for prev_id, rec in zip(prev_sk_id_prev, prev_records):
        for inst in rec.get("installments") or []:
            inst_flat.append(inst)
            inst_sk_id_prev.append(prev_id)
        for ccb in rec.get("credit_card_records") or []:
            ccb_flat.append(ccb)
            ccb_sk_id_prev.append(prev_id)
        for pos in rec.get("pos_cash_records") or []:
            pos_flat.append(pos)
            pos_sk_id_prev.append(prev_id)

    ccb_df = _records_to_df(con, "credit_card_balance", ccb_flat,
                             overrides={"SK_ID_PREV": ccb_sk_id_prev})
    pos_df = _records_to_df(con, "POS_CASH_balance", pos_flat,
                             overrides={"SK_ID_PREV": pos_sk_id_prev})
    inst_df = _records_to_df(con, "installments_payments", inst_flat,
                              overrides={"SK_ID_PREV": inst_sk_id_prev})
    con.register("ccb_live", ccb_df)
    con.register("pos_live", pos_df)
    con.register("inst_live", inst_df)

    # ---------- 배치 파이프라인과 동일한 SQL 재사용 ----------
    bb_agg = bb_agg_sql("bureau_balance_live")
    bureau_agg = bureau_agg_sql("bureau_live", f"({bb_agg})")
    ccb_agg = ccb_agg_sql("ccb_live")
    pos_agg = pos_agg_sql("pos_live")
    inst_agg = inst_agg_sql("inst_live")
    prev_agg = prev_agg_sql("previous_application_live", f"({ccb_agg})", f"({pos_agg})", f"({inst_agg})")
    final_sql = final_join_sql("application_live", f"({bureau_agg})", f"({prev_agg})")

    result = con.execute(final_sql).fetchdf()
    con.close()
    return result
