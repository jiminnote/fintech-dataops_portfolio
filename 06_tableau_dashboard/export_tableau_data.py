"""
Tableau용 CSV 데이터 내보내기
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DuckDB에 적재된 데이터를 Tableau에서 바로 사용할 수 있는 형태로 내보냅니다.
- daily_kpi.csv: 일간 KPI 요약
- retention_cohort.csv: 코호트 리텐션 (히트맵용)
- funnel_data.csv: 퍼널 전환 데이터
- transaction_summary.csv: 거래 분석 요약
"""

from pathlib import Path

import duckdb
import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
EXPORT_DIR = Path(__file__).parent / "exports"
DB_PATH = DATA_DIR / "quickpay.duckdb"


def export_daily_kpi(con: duckdb.DuckDBPyConnection):
    """일간 KPI 마트 데이터 내보내기"""
    query = """
    WITH daily_users AS (
        SELECT
            CAST(event_timestamp AS DATE) AS dt,
            COUNT(DISTINCT user_id) AS dau,
            COUNT(DISTINCT CASE WHEN platform = 'ios' THEN user_id END) AS dau_ios,
            COUNT(DISTINCT CASE WHEN platform = 'android' THEN user_id END) AS dau_android,
            COUNT(DISTINCT CASE WHEN platform = 'web' THEN user_id END) AS dau_web
        FROM events
        WHERE event_name = 'auth_login_completed'
        GROUP BY 1
    ),
    daily_txn AS (
        SELECT
            CAST(created_at AS DATE) AS dt,
            COUNT(*) AS total_txns,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed_txns,
            SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) AS gmv,
            SUM(CASE WHEN status = 'completed' AND transaction_type = 'transfer' THEN amount ELSE 0 END) AS transfer_gmv,
            SUM(CASE WHEN status = 'completed' AND transaction_type = 'qr_payment' THEN amount ELSE 0 END) AS qr_gmv,
            SUM(CASE WHEN status = 'completed' THEN fee ELSE 0 END) AS fee_revenue,
            COUNT(CASE WHEN transaction_type = 'transfer' AND status = 'completed' THEN 1 END) AS transfer_count,
            COUNT(CASE WHEN transaction_type = 'qr_payment' AND status = 'completed' THEN 1 END) AS qr_count,
            ROUND(COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*), 2) AS success_rate
        FROM transactions
        GROUP BY 1
    )
    SELECT
        du.dt AS date,
        DAYNAME(du.dt) AS day_name,
        du.dau,
        du.dau_ios,
        du.dau_android,
        du.dau_web,
        COALESCE(dt.total_txns, 0) AS total_transactions,
        COALESCE(dt.completed_txns, 0) AS completed_transactions,
        COALESCE(dt.gmv, 0) AS gmv,
        COALESCE(dt.transfer_gmv, 0) AS transfer_gmv,
        COALESCE(dt.qr_gmv, 0) AS qr_payment_gmv,
        COALESCE(dt.fee_revenue, 0) AS fee_revenue,
        COALESCE(dt.transfer_count, 0) AS transfer_count,
        COALESCE(dt.qr_count, 0) AS qr_payment_count,
        COALESCE(dt.success_rate, 0) AS success_rate,
        ROUND(COALESCE(dt.gmv, 0) * 1.0 / NULLIF(du.dau, 0), 0) AS gmv_per_dau
    FROM daily_users du
    LEFT JOIN daily_txn dt ON du.dt = dt.dt
    ORDER BY du.dt
    """
    df = con.execute(query).fetchdf()
    df.to_csv(EXPORT_DIR / "daily_kpi.csv", index=False)
    print(f"   ✅ daily_kpi.csv: {len(df)}행")
    return df


def export_retention_cohort(con: duckdb.DuckDBPyConnection):
    """코호트 리텐션 데이터 내보내기 (히트맵용)"""
    query = """
    WITH user_signup AS (
        SELECT user_id, CAST(signup_date AS DATE) AS signup_date,
               DATE_TRUNC('week', CAST(signup_date AS DATE))::DATE AS cohort_week
        FROM users
    ),
    user_activity AS (
        SELECT DISTINCT user_id, CAST(event_timestamp AS DATE) AS activity_date
        FROM events WHERE event_name = 'auth_login_completed'
    ),
    cohort_daily AS (
        SELECT
            us.cohort_week,
            ua.activity_date - us.signup_date AS day_n,
            COUNT(DISTINCT ua.user_id) AS active_users
        FROM user_signup us
        INNER JOIN user_activity ua ON us.user_id = ua.user_id
        WHERE ua.activity_date - us.signup_date BETWEEN 0 AND 30
        GROUP BY 1, 2
    ),
    cohort_sizes AS (
        SELECT cohort_week, COUNT(DISTINCT user_id) AS cohort_size
        FROM user_signup GROUP BY 1
    )
    SELECT
        cd.cohort_week,
        cd.day_n,
        cd.active_users,
        cs.cohort_size,
        ROUND(cd.active_users * 100.0 / cs.cohort_size, 2) AS retention_rate
    FROM cohort_daily cd
    JOIN cohort_sizes cs ON cd.cohort_week = cs.cohort_week
    ORDER BY cd.cohort_week, cd.day_n
    """
    df = con.execute(query).fetchdf()
    df.to_csv(EXPORT_DIR / "retention_cohort.csv", index=False)
    print(f"   ✅ retention_cohort.csv: {len(df)}행")
    return df


def export_funnel_data(con: duckdb.DuckDBPyConnection):
    """퍼널 전환 데이터 내보내기"""
    query = """
    WITH user_funnel AS (
        SELECT
            user_id,
            MAX(CASE WHEN event_name = 'auth_signup_started' THEN 1 ELSE 0 END) AS step1,
            MAX(CASE WHEN event_name = 'auth_signup_submitted' THEN 1 ELSE 0 END) AS step2,
            MAX(CASE WHEN event_name = 'auth_signup_completed' THEN 1 ELSE 0 END) AS step3,
            MAX(CASE WHEN event_name = 'auth_identity_verified' THEN 1 ELSE 0 END) AS step4,
            MAX(CASE WHEN event_name = 'payment_transfer_started' THEN 1 ELSE 0 END) AS step5,
            MAX(CASE WHEN event_name = 'payment_transfer_completed' THEN 1 ELSE 0 END) AS step6
        FROM events
        WHERE event_name IN (
            'auth_signup_started', 'auth_signup_submitted', 'auth_signup_completed',
            'auth_identity_verified', 'payment_transfer_started', 'payment_transfer_completed'
        )
        GROUP BY 1
    ),
    totals AS (
        SELECT SUM(step1) AS s1, SUM(step2) AS s2, SUM(step3) AS s3,
               SUM(step4) AS s4, SUM(step5) AS s5, SUM(step6) AS s6
        FROM user_funnel
    )
    SELECT 1 AS step_order, 'Step 1: 가입 시작' AS step_name, s1 AS users,
           100.0 AS pct_from_start, 100.0 AS pct_from_prev FROM totals
    UNION ALL
    SELECT 2, 'Step 2: 정보 제출', s2, ROUND(s2*100.0/s1,1), ROUND(s2*100.0/s1,1) FROM totals
    UNION ALL
    SELECT 3, 'Step 3: 가입 완료', s3, ROUND(s3*100.0/s1,1), ROUND(s3*100.0/s2,1) FROM totals
    UNION ALL
    SELECT 4, 'Step 4: 본인인증', s4, ROUND(s4*100.0/s1,1), ROUND(s4*100.0/s3,1) FROM totals
    UNION ALL
    SELECT 5, 'Step 5: 첫 송금 시도', s5, ROUND(s5*100.0/s1,1), ROUND(s5*100.0/s4,1) FROM totals
    UNION ALL
    SELECT 6, 'Step 6: 첫 송금 완료', s6, ROUND(s6*100.0/s1,1), ROUND(s6*100.0/s5,1) FROM totals
    ORDER BY step_order
    """
    df = con.execute(query).fetchdf()
    df.to_csv(EXPORT_DIR / "funnel_data.csv", index=False)
    print(f"   ✅ funnel_data.csv: {len(df)}행")
    return df


def export_transaction_summary(con: duckdb.DuckDBPyConnection):
    """거래 분석 요약 데이터 내보내기"""
    query = """
    SELECT
        DATE_TRUNC('month', CAST(created_at AS TIMESTAMP))::DATE AS month,
        transaction_type,
        status,
        bank_name,
        merchant_category,
        EXTRACT(HOUR FROM CAST(created_at AS TIMESTAMP)) AS hour,
        EXTRACT(DOW FROM CAST(created_at AS TIMESTAMP)) AS day_of_week,
        COUNT(*) AS txn_count,
        SUM(amount) AS total_amount,
        SUM(fee) AS total_fee,
        AVG(amount) AS avg_amount,
        COUNT(DISTINCT user_id) AS unique_users
    FROM transactions
    GROUP BY 1, 2, 3, 4, 5, 6, 7
    ORDER BY 1, 2
    """
    df = con.execute(query).fetchdf()
    df.to_csv(EXPORT_DIR / "transaction_summary.csv", index=False)
    print(f"   ✅ transaction_summary.csv: {len(df)}행")
    return df


def main():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("📊 Tableau용 CSV 데이터 내보내기 시작...")
    print(f"   DB: {DB_PATH}")
    print(f"   출력: {EXPORT_DIR}/\n")
    
    con = duckdb.connect(str(DB_PATH), read_only=True)
    
    export_daily_kpi(con)
    export_retention_cohort(con)
    export_funnel_data(con)
    export_transaction_summary(con)
    
    con.close()
    
    print("\n✅ Tableau용 데이터 내보내기 완료!")
    print("📌 다음 단계: Tableau Public Desktop에서 CSV를 열어 대시보드를 만드세요.")
    print("   → 상세 가이드: 06_tableau_dashboard/dashboard_design.md")


if __name__ == "__main__":
    main()
