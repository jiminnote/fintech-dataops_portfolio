/*
  DAU (Daily Active Users) 분석 쿼리
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DuckDB에서 직접 실행 가능
  
  사용법:
    duckdb data/quickpay.duckdb < 05_sql_queries/daily_active_users.sql
*/

-- ① 일간 DAU + 신규/복귀 구분
WITH daily_logins AS (
    SELECT
        CAST(event_timestamp AS DATE) AS login_date,
        user_id,
        platform
    FROM events
    WHERE event_name = 'auth_login_completed'
      AND user_id NOT LIKE 'usr_test%'
    GROUP BY 1, 2, 3
),

user_first_login AS (
    SELECT
        user_id,
        MIN(login_date) AS first_login_date
    FROM daily_logins
    GROUP BY 1
)

SELECT
    dl.login_date,
    COUNT(DISTINCT dl.user_id) AS dau,
    COUNT(DISTINCT CASE WHEN dl.login_date = ufl.first_login_date THEN dl.user_id END) AS new_users,
    COUNT(DISTINCT CASE WHEN dl.login_date > ufl.first_login_date THEN dl.user_id END) AS returning_users,
    COUNT(DISTINCT CASE WHEN dl.platform = 'ios' THEN dl.user_id END) AS dau_ios,
    COUNT(DISTINCT CASE WHEN dl.platform = 'android' THEN dl.user_id END) AS dau_android,
    COUNT(DISTINCT CASE WHEN dl.platform = 'web' THEN dl.user_id END) AS dau_web
FROM daily_logins dl
LEFT JOIN user_first_login ufl ON dl.user_id = ufl.user_id
GROUP BY 1
ORDER BY 1;


-- ② 7일 Rolling WAU
SELECT
    login_date,
    dau,
    SUM(dau) OVER (ORDER BY login_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS wau_7d_sum,
    AVG(dau) OVER (ORDER BY login_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS wau_7d_avg
FROM (
    SELECT
        CAST(event_timestamp AS DATE) AS login_date,
        COUNT(DISTINCT user_id) AS dau
    FROM events
    WHERE event_name = 'auth_login_completed'
    GROUP BY 1
) daily
ORDER BY login_date;


-- ③ DAU/MAU Stickiness Ratio
WITH monthly_active AS (
    SELECT
        DATE_TRUNC('month', CAST(event_timestamp AS DATE)) AS month,
        COUNT(DISTINCT user_id) AS mau
    FROM events
    WHERE event_name = 'auth_login_completed'
    GROUP BY 1
),
daily_active AS (
    SELECT
        CAST(event_timestamp AS DATE) AS dt,
        DATE_TRUNC('month', CAST(event_timestamp AS DATE)) AS month,
        COUNT(DISTINCT user_id) AS dau
    FROM events
    WHERE event_name = 'auth_login_completed'
    GROUP BY 1, 2
)
SELECT
    da.dt,
    da.dau,
    ma.mau,
    ROUND(da.dau * 100.0 / ma.mau, 2) AS stickiness_pct
FROM daily_active da
JOIN monthly_active ma ON da.month = ma.month
ORDER BY da.dt;
