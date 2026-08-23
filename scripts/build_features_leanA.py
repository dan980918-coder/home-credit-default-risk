"""
Phase 3 (Lean, 옵션 A): 해석 가능성 우선 - 테이블당 핵심 지표만 소수 선별해
SK_ID_CURR 단위 feature 테이블을 만든다.

조인/집계 순서:
  1) bureau_balance -> SK_ID_BUREAU 단위 집계
  2) bureau(+1의 결과) -> SK_ID_CURR 단위 집계
  3) credit_card_balance / POS_CASH_balance / installments_payments
     -> 각각 SK_ID_PREV 단위 집계
  4) previous_application(+3의 결과) -> SK_ID_CURR 단위 집계
  5) application_train/test(전처리 적용) + 2 + 4 최종 join

집계 SQL 자체는 scripts/_lean_a_features.py에 있음 — Phase 5 API의 실시간
집계(/predict/live)도 동일한 함수를 재사용해 배치/실시간 로직이 어긋나지
않도록 함. 전부 DuckDB로 처리(pandas 전체 로드 없음), 중간 결과는 parquet로
저장해 한 번에 처리하는 쿼리의 메모리 사용을 억제한다.
"""
import duckdb
from _preprocessing import clean_application_sql
from _lean_a_features import (
    bb_agg_sql, bureau_agg_sql, ccb_agg_sql, pos_agg_sql, inst_agg_sql,
    prev_agg_sql, final_join_sql,
)

RAW = "data/raw"
OUT = "data/processed"

con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")
con.execute("SET preserve_insertion_order=false")


def run(step, sql):
    print(f"--- {step} ---")
    con.execute(sql)


csv = lambda name: f"read_csv_auto('{RAW}/{name}.csv')"
pq = lambda name: f"read_parquet('{OUT}/{name}.parquet')"

# ---------- 1) bureau_balance -> SK_ID_BUREAU ----------
run("1) bureau_balance -> bb_agg.parquet", f"""
    COPY ({bb_agg_sql(csv('bureau_balance'))}) TO '{OUT}/bb_agg.parquet' (FORMAT PARQUET)
""")

# ---------- 2) bureau(+bb_agg) -> SK_ID_CURR ----------
run("2) bureau -> bureau_agg.parquet (SK_ID_CURR 단위)", f"""
    COPY ({bureau_agg_sql(csv('bureau'), pq('bb_agg'))}) TO '{OUT}/bureau_agg.parquet' (FORMAT PARQUET)
""")

# ---------- 3) credit_card_balance / POS_CASH_balance / installments_payments -> SK_ID_PREV ----------
run("3a) credit_card_balance -> ccb_agg.parquet (SK_ID_PREV 단위)", f"""
    COPY ({ccb_agg_sql(csv('credit_card_balance'))}) TO '{OUT}/ccb_agg.parquet' (FORMAT PARQUET)
""")
run("3b) POS_CASH_balance -> pos_agg.parquet (SK_ID_PREV 단위)", f"""
    COPY ({pos_agg_sql(csv('POS_CASH_balance'))}) TO '{OUT}/pos_agg.parquet' (FORMAT PARQUET)
""")
run("3c) installments_payments -> inst_agg.parquet (SK_ID_PREV 단위)", f"""
    COPY ({inst_agg_sql(csv('installments_payments'))}) TO '{OUT}/inst_agg.parquet' (FORMAT PARQUET)
""")

# ---------- 4) previous_application(+3의 결과) -> SK_ID_CURR ----------
run("4) previous_application -> prev_agg.parquet (SK_ID_CURR 단위)", f"""
    COPY ({prev_agg_sql(csv('previous_application'), pq('ccb_agg'), pq('pos_agg'), pq('inst_agg'))})
    TO '{OUT}/prev_agg.parquet' (FORMAT PARQUET)
""")

# ---------- 5) application_train/test + bureau_agg + prev_agg 최종 join ----------
for split, path in [("train", f"{RAW}/application_train.csv"), ("test", f"{RAW}/application_test.csv")]:
    app_source = f"({clean_application_sql(path)})"
    run(f"5) application_{split} + bureau_agg + prev_agg -> {split}_features_leanA", f"""
        COPY ({final_join_sql(app_source, pq('bureau_agg'), pq('prev_agg'))})
        TO '{OUT}/{split}_features_leanA.parquet' (FORMAT PARQUET)
    """)

print("\n=== 완료: 최종 산출 shape ===")
for split in ["train", "test"]:
    n = con.execute(f"SELECT count(*) FROM read_parquet('{OUT}/{split}_features_leanA.parquet')").fetchone()[0]
    ncols = len(con.execute(f"DESCRIBE SELECT * FROM read_parquet('{OUT}/{split}_features_leanA.parquet')").fetchall())
    print(f"{split}_features_leanA: {n} rows x {ncols} cols")
