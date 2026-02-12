/*
  int_user_cohort — 가입 코호트별 리텐션 분석용 중간 테이블
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  가입 주차 기준으로 코호트를 나누고, N-day 재방문 여부를 플래그 처리
*/

WITH user_base AS (
    SELECT
        user_id,
        signup_date,
        signup_week,
        signup_month,
        platform
    FROM {{ ref('stg_users') }}
),

user_activity AS (
    SELECT DISTINCT
        user_id,
        event_date_kst AS activity_date
    FROM {{ ref('stg_events') }}
    WHERE event_name = 'auth_login_completed'
),

cohort_activity AS (
    SELECT
        ub.user_id,
        ub.signup_date,
        ub.signup_week,
        ub.signup_month,
        ub.platform,
        ua.activity_date,
        ua.activity_date - ub.signup_date AS days_since_signup
    FROM user_base ub
    LEFT JOIN user_activity ua ON ub.user_id = ua.user_id
)

SELECT
    user_id,
    signup_date,
    signup_week,
    signup_month,
    platform,
    activity_date,
    days_since_signup,
    
    -- N-Day 리텐션 플래그
    MAX(CASE WHEN days_since_signup = 1 THEN 1 ELSE 0 END) AS retained_d1,
    MAX(CASE WHEN days_since_signup = 3 THEN 1 ELSE 0 END) AS retained_d3,
    MAX(CASE WHEN days_since_signup = 7 THEN 1 ELSE 0 END) AS retained_d7,
    MAX(CASE WHEN days_since_signup = 14 THEN 1 ELSE 0 END) AS retained_d14,
    MAX(CASE WHEN days_since_signup = 30 THEN 1 ELSE 0 END) AS retained_d30

FROM cohort_activity
GROUP BY 1, 2, 3, 4, 5, 6, 7
