"""data/raw/ 8개 CSV의 컬럼별 dtype/결측률/카디널리티/분포 요약을 docs/data_dictionary.md로 생성.

DuckDB로 CSV를 직접 스캔(pandas 전체 로드 없음). SUMMARIZE로 결측률/수치 요약
(min/max/mean/median)을 얻고, 카디널리티는 컬럼별 COUNT(DISTINCT)를 한 쿼리로 묶어
정확히 계산한다. 범주형 컬럼은 컬럼별로 상위 5개 값의
빈도를 별도 조회한다. Kaggle 공식 컬럼 설명 파일(HomeCredit_columns_description.csv)이
data/raw/에 있으면 함께 붙인다.
"""

import duckdb
from pathlib import Path

RAW_DIR = Path("data/raw")
OUT_PATH = Path("docs/data_dictionary.md")
DESC_FILE = RAW_DIR / "HomeCredit_columns_description.csv"

TABLES = [
    "application_train.csv",
    "application_test.csv",
    "bureau.csv",
    "bureau_balance.csv",
    "previous_application.csv",
    "credit_card_balance.csv",
    "POS_CASH_balance.csv",
    "installments_payments.csv",
]

CATEGORICAL_TYPES = {"VARCHAR", "BOOLEAN"}


def load_descriptions():
    """Kaggle's HomeCredit_columns_description.csv is cp1252-encoded, not UTF-8
    (contains e.g. curly quotes), so DuckDB's CSV reader mis-parses it — read with
    pandas + explicit encoding instead."""
    if not DESC_FILE.exists():
        return {}
    import pandas as pd

    df = pd.read_csv(DESC_FILE, encoding="cp1252")
    cols = {c.lower(): c for c in df.columns}
    table_col = cols.get("table")
    row_col = cols.get("row")
    desc_col = cols.get("description")
    if not (table_col and row_col and desc_col):
        return {}
    out = {}
    for _, r in df.iterrows():
        t = str(r[table_col]).strip()
        c = str(r[row_col]).strip()
        d = str(r[desc_col]).strip()
        out[(t, c)] = d
    return out


def lookup_desc(descriptions, table_csv, column):
    if not descriptions:
        return ""
    candidates = [
        table_csv,
        "application_{train|test}.csv",
        table_csv.replace(".csv", ""),
        table_csv.replace("_train", "").replace("_test", ""),
        table_csv.replace("_train.csv", ".csv").replace("_test.csv", ".csv"),
    ]
    for t in candidates:
        d = descriptions.get((t, column))
        if d:
            return d
    return ""


def fmt_num(x, nd=2):
    if x is None:
        return ""
    try:
        return f"{float(x):,.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def escape_md(s):
    if s is None:
        return ""
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


def exact_cardinalities(con, rel, columns):
    """COUNT(DISTINCT col) for every column in a single pass (one query, one scan)."""
    aliases = [f"n_{i}" for i in range(len(columns))]
    selects = ", ".join(
        f'COUNT(DISTINCT "{c.replace(chr(34), chr(34) * 2)}") AS "{a}"'
        for c, a in zip(columns, aliases)
    )
    row = con.execute(f"SELECT {selects} FROM {rel}").fetchone()
    return {c: row[i] for i, c in enumerate(columns)}


def build_table_section(con, table_csv, descriptions):
    path = RAW_DIR / table_csv
    rel = f"read_csv_auto('{path.as_posix()}', sample_size=-1)"

    total_rows = con.execute(f"SELECT COUNT(*) FROM {rel}").fetchone()[0]
    n_cols = con.execute(f"SELECT COUNT(*) FROM (DESCRIBE SELECT * FROM {rel})").fetchone()[0]

    summary = con.execute(f"SUMMARIZE SELECT * FROM {rel}").df()
    cardinalities = exact_cardinalities(con, rel, list(summary["column_name"]))

    cat_rows = []
    num_rows = []

    for _, r in summary.iterrows():
        col = r["column_name"]
        dtype = r["column_type"]
        null_pct = float(r["null_percentage"]) if r["null_percentage"] is not None else 0.0
        cardinality = cardinalities[col]
        desc = escape_md(lookup_desc(descriptions, table_csv, col))

        if dtype in CATEGORICAL_TYPES:
            safe_col = col.replace('"', '""')
            top5 = con.execute(
                f"""
                SELECT "{safe_col}" AS v, COUNT(*) AS cnt
                FROM {rel}
                WHERE "{safe_col}" IS NOT NULL
                GROUP BY "{safe_col}"
                ORDER BY cnt DESC
                LIMIT 5
                """
            ).df()
            parts = []
            for _, tr in top5.iterrows():
                ratio = tr["cnt"] / total_rows * 100 if total_rows else 0
                parts.append(f"{tr['v']} ({ratio:.1f}%)")
            top5_str = "; ".join(parts)
            cat_rows.append(
                f"| `{col}` | {desc} | {dtype} | {null_pct:.2f} | {cardinality} | {top5_str} |"
            )
        else:
            num_rows.append(
                f"| `{col}` | {desc} | {dtype} | {null_pct:.2f} | {cardinality} "
                f"| {fmt_num(r['min'])} | {fmt_num(r['max'])} | {fmt_num(r['avg'])} | {fmt_num(r['q50'])} |"
            )

    lines = [f"## {table_csv}", "", f"행 수: {total_rows:,} / 컬럼 수: {n_cols}", ""]

    if cat_rows:
        lines += [
            "### 범주형 컬럼",
            "",
            "| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | 상위 5개 값 (비율) |",
            "|---|---|---|---|---|---|",
        ] + cat_rows + [""]

    if num_rows:
        lines += [
            "### 수치형 컬럼",
            "",
            "| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | min | max | mean | median |",
            "|---|---|---|---|---|---|---|---|---|",
        ] + num_rows + [""]

    return "\n".join(lines)


def main():
    con = duckdb.connect()
    con.execute("PRAGMA memory_limit='2GB'")
    con.execute("PRAGMA threads=2")

    descriptions = load_descriptions()

    header = [
        "# 데이터 딕셔너리 (data/raw/ 8개 테이블)",
        "",
        "`data/raw/` 원본 CSV를 DuckDB로 직접 스캔해 생성한 컬럼별 통계 요약. "
        "원본 데이터 자체는 GitHub에 포함하지 않으며(§4), 이 문서는 집계 결과만 담는다.",
        "",
        "- 카디널리티는 `COUNT(DISTINCT ...)`로 정확히 계산한 값",
        "- median은 `SUMMARIZE`의 q50(근사 분위수) 값",
        "- 범주형 상위 5개 값 비율은 결측치를 제외한 전체 행 대비 비율",
    ]

    if not DESC_FILE.exists():
        header.append(
            "- ⚠️ `HomeCredit_columns_description.csv`가 `data/raw/`에 없어 '설명' 컬럼은 비어 있음 "
            "(Kaggle에서 내려받아 `data/raw/`에 추가하면 재실행 시 자동 반영됨)"
        )
    header.append("")

    sections = [header_line for header_line in header]
    for t in TABLES:
        print(f"[build_data_dictionary] processing {t} ...")
        sections.append(build_table_section(con, t, descriptions))
        sections.append("")

    OUT_PATH.write_text("\n".join(sections), encoding="utf-8")
    print(f"[build_data_dictionary] wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
