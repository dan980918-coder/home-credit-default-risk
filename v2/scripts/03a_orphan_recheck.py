"""
03a_orphan_recheck.py
Loan Approval Risk Scoring - v2 재분석
1단계 보고서 오류 확인: 고아 레코드 비율의 분모 방향을 양방향으로 재계산한다.

실행: python3 -I v2/scripts/03a_orphan_recheck.py
출력: v2/docs/orphan_recheck_results.json
"""
import json
import os
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
OUT_JSON = os.path.join(ROOT, "v2", "docs", "orphan_recheck_results.json")

con = duckdb.connect()


def p(name):
    return os.path.join(RAW, name)


p_train = p("application_train.csv")
p_test = p("application_test.csv")
p_bureau = p("bureau.csv")
p_bureau_balance = p("bureau_balance.csv")
p_prev = p("previous_application.csv")
p_pos = p("POS_CASH_balance.csv")
p_inst = p("installments_payments.csv")
p_cc = p("credit_card_balance.csv")

results = {}

# -----------------------------------------------------------------
# 1. bureau <-> bureau_balance (양방향)
# -----------------------------------------------------------------
bureau_total = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p_bureau}')").fetchone()[0]
bureau_without_balance = con.execute(
    f"""
    SELECT COUNT(*) FROM read_csv_auto('{p_bureau}') b
    WHERE b.SK_ID_BUREAU NOT IN (SELECT DISTINCT SK_ID_BUREAU FROM read_csv_auto('{p_bureau_balance}'))
    """
).fetchone()[0]

bb_total = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p_bureau_balance}')").fetchone()[0]
bb_true_orphan = con.execute(
    f"""
    SELECT COUNT(*) FROM read_csv_auto('{p_bureau_balance}') bb
    WHERE bb.SK_ID_BUREAU NOT IN (SELECT DISTINCT SK_ID_BUREAU FROM read_csv_auto('{p_bureau}'))
    """
).fetchone()[0]

results["bureau_bureau_balance"] = {
    "a_bureau_rows_without_any_balance_record": {
        "numerator": bureau_without_balance,
        "denominator": bureau_total,
        "pct": round(bureau_without_balance / bureau_total * 100, 3),
        "meaning": "bureau 신용 중 bureau_balance에 월별 기록이 전혀 없는 신용의 비율 (데이터 오류 아님 - 월별 상태를 제공하지 않는 신용 유형이 있을 수 있음)",
    },
    "b_bureau_balance_rows_truly_orphan": {
        "numerator": bb_true_orphan,
        "denominator": bb_total,
        "pct": round(bb_true_orphan / bb_total * 100, 3),
        "meaning": "bureau_balance 행 중 bureau에 SK_ID_BUREAU가 아예 없는 '진짜 고아' 비율 (참조 무결성 문제 여부)",
    },
}
print("bureau<->bureau_balance:", json.dumps(results["bureau_bureau_balance"], indent=2, ensure_ascii=False))

# -----------------------------------------------------------------
# 2. previous_application <-> credit_card_balance (양방향 + 상품종류별)
# -----------------------------------------------------------------
prev_total = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p_prev}')").fetchone()[0]
prev_without_cc = con.execute(
    f"""
    SELECT COUNT(*) FROM read_csv_auto('{p_prev}') pa
    WHERE pa.SK_ID_PREV NOT IN (SELECT DISTINCT SK_ID_PREV FROM read_csv_auto('{p_cc}'))
    """
).fetchone()[0]

by_contract_type = con.execute(
    f"""
    SELECT pa.NAME_CONTRACT_TYPE,
           COUNT(*) as total,
           SUM(CASE WHEN pa.SK_ID_PREV NOT IN (SELECT DISTINCT SK_ID_PREV FROM read_csv_auto('{p_cc}')) THEN 1 ELSE 0 END) as without_cc
    FROM read_csv_auto('{p_prev}') pa
    GROUP BY pa.NAME_CONTRACT_TYPE
    ORDER BY total DESC
    """
).fetchdf()
by_contract_type["pct_without_cc"] = (by_contract_type["without_cc"] / by_contract_type["total"] * 100).round(3)

cc_total = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p_cc}')").fetchone()[0]
cc_true_orphan = con.execute(
    f"""
    SELECT COUNT(*) FROM read_csv_auto('{p_cc}') cc
    WHERE cc.SK_ID_PREV NOT IN (SELECT DISTINCT SK_ID_PREV FROM read_csv_auto('{p_prev}'))
    """
).fetchone()[0]

cc_sk_id_curr_in_app = con.execute(
    f"""
    SELECT COUNT(*) FROM read_csv_auto('{p_cc}') cc
    WHERE cc.SK_ID_CURR IN (
        SELECT SK_ID_CURR FROM read_csv_auto('{p_train}')
        UNION
        SELECT SK_ID_CURR FROM read_csv_auto('{p_test}')
    )
    """
).fetchone()[0]

results["previous_application_credit_card_balance"] = {
    "a_prev_rows_without_any_cc_record": {
        "numerator": prev_without_cc,
        "denominator": prev_total,
        "pct": round(prev_without_cc / prev_total * 100, 3),
        "meaning": "previous_application 행 중 카드 잔액 기록이 없는 비율 (신용카드가 아닌 상품이면 당연히 없음)",
    },
    "a_by_contract_type": by_contract_type.to_dict(orient="records"),
    "b_cc_rows_truly_orphan": {
        "numerator": cc_true_orphan,
        "denominator": cc_total,
        "pct": round(cc_true_orphan / cc_total * 100, 3),
        "meaning": "credit_card_balance 행 중 previous_application에 SK_ID_PREV가 아예 없는 '진짜 고아' 비율",
    },
    "c_cc_sk_id_curr_in_application": {
        "numerator": cc_sk_id_curr_in_app,
        "denominator": cc_total,
        "pct": round(cc_sk_id_curr_in_app / cc_total * 100, 3),
        "meaning": "credit_card_balance의 SK_ID_CURR가 application_train/test에 존재하는 비율 (신청자 연결 가능 여부)",
    },
}
print("previous_application<->credit_card_balance:", json.dumps(results["previous_application_credit_card_balance"], indent=2, ensure_ascii=False, default=str))

# -----------------------------------------------------------------
# 3. previous_application <-> POS_CASH_balance / installments_payments (동일 방식)
# -----------------------------------------------------------------
for name, path in [("POS_CASH_balance", p_pos), ("installments_payments", p_inst)]:
    without_child = con.execute(
        f"""
        SELECT COUNT(*) FROM read_csv_auto('{p_prev}') pa
        WHERE pa.SK_ID_PREV NOT IN (SELECT DISTINCT SK_ID_PREV FROM read_csv_auto('{path}'))
        """
    ).fetchone()[0]
    child_total = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{path}')").fetchone()[0]
    child_true_orphan = con.execute(
        f"""
        SELECT COUNT(*) FROM read_csv_auto('{path}') c
        WHERE c.SK_ID_PREV NOT IN (SELECT DISTINCT SK_ID_PREV FROM read_csv_auto('{p_prev}'))
        """
    ).fetchone()[0]
    child_sk_id_curr_in_app = con.execute(
        f"""
        SELECT COUNT(*) FROM read_csv_auto('{path}') c
        WHERE c.SK_ID_CURR IN (
            SELECT SK_ID_CURR FROM read_csv_auto('{p_train}')
            UNION
            SELECT SK_ID_CURR FROM read_csv_auto('{p_test}')
        )
        """
    ).fetchone()[0]
    results[f"previous_application_{name}"] = {
        "a_prev_rows_without_any_child_record": {
            "numerator": without_child,
            "denominator": prev_total,
            "pct": round(without_child / prev_total * 100, 3),
        },
        "b_child_rows_truly_orphan": {
            "numerator": child_true_orphan,
            "denominator": child_total,
            "pct": round(child_true_orphan / child_total * 100, 3),
        },
        "c_child_sk_id_curr_in_application": {
            "numerator": child_sk_id_curr_in_app,
            "denominator": child_total,
            "pct": round(child_sk_id_curr_in_app / child_total * 100, 3),
        },
    }
    print(f"previous_application<->{name}:", json.dumps(results[f"previous_application_{name}"], indent=2, ensure_ascii=False, default=str))

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)

print(f"\n완료: {OUT_JSON}")
con.close()
