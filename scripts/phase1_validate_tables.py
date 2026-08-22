"""
Phase 1: 8개 Home Credit 테이블 로드 확인 + SK_ID_CURR 조인 무결성 검증.
pandas 전체 로드 없이 DuckDB로 CSV를 직접 스캔.
"""
import json
import duckdb

RAW = "data/raw"
TABLES = {
    "application_train": f"{RAW}/application_train.csv",
    "application_test": f"{RAW}/application_test.csv",
    "bureau": f"{RAW}/bureau.csv",
    "bureau_balance": f"{RAW}/bureau_balance.csv",
    "previous_application": f"{RAW}/previous_application.csv",
    "credit_card_balance": f"{RAW}/credit_card_balance.csv",
    "POS_CASH_balance": f"{RAW}/POS_CASH_balance.csv",
    "installments_payments": f"{RAW}/installments_payments.csv",
}

con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory='data/tmp_duckdb'")
con.execute("SET preserve_insertion_order=false")

results = {}

print("=" * 70)
print("1) 테이블별 로드 확인 (스키마 / 행·컬럼 수)")
print("=" * 70)
for name, path in TABLES.items():
    schema = con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{path}')").fetchall()
    n_rows = con.execute(f"SELECT count(*) FROM read_csv_auto('{path}')").fetchone()[0]
    ncols = len(schema)
    dtype_summary = {}
    for row in schema:
        dtype_summary[row[1]] = dtype_summary.get(row[1], 0) + 1
    print(f"\n[{name}] rows={n_rows:,}  cols={ncols}  dtypes={dtype_summary}")
    results[name] = {"rows": n_rows, "cols": ncols, "dtypes": dtype_summary,
                      "columns": [(r[0], r[1]) for r in schema]}

print("\n" + "=" * 70)
print("2) application_train SK_ID_CURR 고유 개수 확인 (기대: 307,511)")
print("=" * 70)
n_total, n_distinct = con.execute(f"""
    SELECT count(*), count(distinct SK_ID_CURR)
    FROM read_csv_auto('{TABLES["application_train"]}')
""").fetchone()
print(f"total rows={n_total:,}  distinct SK_ID_CURR={n_distinct:,}  "
      f"일치={n_distinct == 307511}")
results["application_train_check"] = {"total_rows": n_total, "distinct_sk_id_curr": n_distinct,
                                        "matches_307511": n_distinct == 307511}

# train/test SK_ID_CURR 겹침 확인
overlap = con.execute(f"""
    SELECT count(*) FROM (
        SELECT SK_ID_CURR FROM read_csv_auto('{TABLES["application_train"]}')
        INTERSECT
        SELECT SK_ID_CURR FROM read_csv_auto('{TABLES["application_test"]}')
    )
""").fetchone()[0]
print(f"train/test SK_ID_CURR 겹침: {overlap}건 (0이어야 정상)")
results["train_test_overlap"] = overlap

print("\n" + "=" * 70)
print("3) 조인 무결성: 고아 레코드(고객 마스터에 없는 SK_ID_CURR/SK_ID_PREV/SK_ID_BUREAU) 확인")
print("=" * 70)


def orphan_check(child_name, child_path, child_key, parent_desc, parent_sql):
    orphans = con.execute(f"""
        SELECT count(*) FROM read_csv_auto('{child_path}') c
        WHERE c.{child_key} NOT IN ({parent_sql})
    """).fetchone()[0]
    total = con.execute(f"SELECT count(*) FROM read_csv_auto('{child_path}')").fetchone()[0]
    print(f"[{child_name}] {child_key} not in {parent_desc}: {orphans:,} / {total:,} rows")
    return orphans


all_curr = f"""
    SELECT SK_ID_CURR FROM read_csv_auto('{TABLES["application_train"]}')
    UNION
    SELECT SK_ID_CURR FROM read_csv_auto('{TABLES["application_test"]}')
"""
orphans_bureau = orphan_check("bureau", TABLES["bureau"], "SK_ID_CURR",
                               "application_train∪test.SK_ID_CURR", all_curr)
orphans_prev = orphan_check("previous_application", TABLES["previous_application"], "SK_ID_CURR",
                             "application_train∪test.SK_ID_CURR", all_curr)

bureau_ids = f"SELECT SK_ID_BUREAU FROM read_csv_auto('{TABLES['bureau']}')"
orphans_bb = orphan_check("bureau_balance", TABLES["bureau_balance"], "SK_ID_BUREAU",
                           "bureau.SK_ID_BUREAU", bureau_ids)

prev_ids = f"SELECT SK_ID_PREV FROM read_csv_auto('{TABLES['previous_application']}')"
orphans_ccb = orphan_check("credit_card_balance", TABLES["credit_card_balance"], "SK_ID_PREV",
                            "previous_application.SK_ID_PREV", prev_ids)
orphans_pos = orphan_check("POS_CASH_balance", TABLES["POS_CASH_balance"], "SK_ID_PREV",
                            "previous_application.SK_ID_PREV", prev_ids)
orphans_inst = orphan_check("installments_payments", TABLES["installments_payments"], "SK_ID_PREV",
                             "previous_application.SK_ID_PREV", prev_ids)

results["orphans"] = {
    "bureau_vs_app": orphans_bureau,
    "previous_application_vs_app": orphans_prev,
    "bureau_balance_vs_bureau": orphans_bb,
    "credit_card_balance_vs_prev": orphans_ccb,
    "POS_CASH_balance_vs_prev": orphans_pos,
    "installments_payments_vs_prev": orphans_inst,
}

with open("data/processed/phase1_validation_result.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)
print("\nwrote data/processed/phase1_validation_result.json")
