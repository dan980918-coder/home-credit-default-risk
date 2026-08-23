"""POST /predict (A안) 용: train+test 사전계산 Lean(A) feature에서 SK_ID_CURR 조회."""
import duckdb
import pandas as pd

TRAIN_PATH = "data/processed/train_features_leanA.parquet"
TEST_PATH = "data/processed/test_features_leanA.parquet"


def lookup(sk_id_curr: int) -> pd.DataFrame | None:
    con = duckdb.connect()
    row = con.execute(f"""
        SELECT * EXCLUDE (TARGET) FROM read_parquet('{TRAIN_PATH}') WHERE SK_ID_CURR = {sk_id_curr}
        UNION ALL
        SELECT * FROM read_parquet('{TEST_PATH}') WHERE SK_ID_CURR = {sk_id_curr}
        LIMIT 1
    """).fetchdf()
    con.close()
    if row.empty:
        return None
    return row
