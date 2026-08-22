"""
raw application_train/test 공통 전처리. Option A(Lean)/B(Full) 양쪽에서 재사용.

DAYS_EMPLOYED == 365243은 "고용되지 않음"(은퇴자 99.98%, 무직 100%)을 나타내는
placeholder로 확인됨(Phase 2 EDA §3) — 실제 재직일수가 아니므로 NaN으로 치환하고,
정보 손실 없이 별도 플래그로 보존한다.
"""


def clean_application_sql(csv_path: str) -> str:
    return f"""
        SELECT
            * EXCLUDE (DAYS_EMPLOYED),
            CASE WHEN DAYS_EMPLOYED = 365243 THEN NULL ELSE DAYS_EMPLOYED END AS DAYS_EMPLOYED,
            (DAYS_EMPLOYED = 365243) AS DAYS_EMPLOYED_ANOMALY
        FROM read_csv_auto('{csv_path}')
    """
