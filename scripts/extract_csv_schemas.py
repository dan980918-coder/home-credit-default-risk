"""
Phase 6: /predict/live(app/feature_live.py)가 필요로 하는 건 원본 CSV의
컬럼명·타입 스키마뿐, 실제 행 데이터가 아니다. 배포 환경에 data/raw/ 전체를
둘 필요가 없도록 스키마만 한 번 추출해 models/csv_schemas.json으로 저장한다
(실데이터 0건 — 라이선스/개인정보 우려 없음).
"""
import json
import duckdb

RAW = "data/raw"
OUT_PATH = "models/csv_schemas.json"

# app/feature_live.py가 _get_csv_schema()를 호출하는 테이블 전부
TABLES = [
    "application_test",
    "bureau",
    "bureau_balance",
    "previous_application",
    "credit_card_balance",
    "POS_CASH_balance",
    "installments_payments",
]

con = duckdb.connect()
schemas = {}
for name in TABLES:
    rows = con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{RAW}/{name}.csv')").fetchall()
    schemas[name] = [[r[0], r[1]] for r in rows]
    print(f"{name}: {len(rows)} columns")

with open(OUT_PATH, "w") as f:
    json.dump(schemas, f, ensure_ascii=False, indent=2)
print(f"\nwrote {OUT_PATH}")
