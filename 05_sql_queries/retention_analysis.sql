/*
  코호트 리텐션 분석
  ━━━━━━━━━━━━━━━━━
  가입 주차별 코호트의 D1, D3, D7, D14, D30 리텐션율 계산
  → Tableau 히트맵 시각화에 사용
*/

-- ① Classic Retention (N-Day)
WITH user_signup AS (
    SELECT
        user_id,
        CAST(signup_date AS DATE) AS signup_date,
        DATE_TRUNC('week', CAST(signup_date AS DATE))::DATE AS cohort_week
    FROM users
),

user_activity AS (
    SELECT DISTINCT
        user_id,
        CAST(event_timestamp AS DATE) AS activity_date
    FROM events
    WHERE event_name = 'auth_login_completed'
),

cohort_activity AS (
    SELECT
        us.user_id,
        us.cohort_week,
        ua.activity_date,
        ua.activity_date - us.signup_date AS days_since_signup
    FROM user_signup us
    INNER JOIN user_activity ua ON us.user_id = ua.user_id
)

SELECT
    cohort_week,
    COUNT(DISTINCT user_id) AS cohort_size,
    
    -- D1 ~ D30 리텐션
    COUNT(DISTINCT CASE WHEN days_since_signup = 1 THEN user_id END) AS d1_users,
    COUNT(DISTINCT CASE WHEN days_since_signup = 3 THEN user_id END) AS d3_users,
    COUNT(DISTINCT CASE WHEN days_since_signup = 7 THEN user_id END) AS d7_users,
    COUNT(DISTINCT CASE WHEN days_since_signup = 14 THEN user_id END) AS d14_users,
    COUNT(DISTINCT CASE WHEN days_since_signup = 30 THEN user_id END) AS d30_users,
    
    ROUND(COUNT(DISTINCT CASE WHEN days_since_signup = 1 THEN user_id END) * 100.0 
          / COUNT(DISTINCT user_id), 2) AS d1_retention,
    ROUND(COUNT(DISTINCT CASE WHEN days_since_signup = 3 THEN user_id END) * 100.0 
          / COUNT(DISTINCT user_id), 2) AS d3_retention,
    ROUND(COUNT(DISTINCT CASE WHEN days_since_signup = 7 THEN user_id END) * 100.0 
          / COUNT(DISTINCT user_id), 2) AS d7_retention,
    ROUND(COUNT(DISTINCT CASE WHEN days_since_signup = 14 THEN user_id END) * 100.0 
          / COUNT(DISTINCT user_id), 2) AS d14_retention,
    ROUND(COUNT(DISTINCT CASE WHEN days_since_signup = 30 THEN user_id END) * 100.0 
          / COUNT(DISTINCT user_id), 2) AS d30_retention

FROM cohort_activity
GROUP BY 1
ORDER BY 1;


-- ② 리텐션 커브 (Tableau용 long format)
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
        COUNT(DISTINCT ua.user_id) AS active_users,
        (SELECT COUNT(DISTINCT user_id) FROM user_signup WHERE cohort_week = us.cohort_week) AS cohort_size
    FROM user_signup us
    INNER JOIN user_activity ua ON us.user_id = ua.user_id
    WHERE ua.activity_date - us.signup_date BETWEEN 0 AND 30
    GROUP BY 1, 2
)
SELECT
    cohort_week,
    day_n,
    active_users,
    cohort_size,
    ROUND(active_users * 100.0 / cohort_size, 2) AS retention_rate
FROM cohort_daily
ORDER BY cohort_week, day_n;
