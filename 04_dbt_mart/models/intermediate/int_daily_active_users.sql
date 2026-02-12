/*
  int_daily_active_users — 일간 활성 사용자 집계
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DAU, 신규/복귀 사용자 구분, 플랫폼별 분리
*/

WITH daily_logins AS (
    SELECT
        event_date_kst AS activity_date,
        user_id,
        platform,
        MIN(event_timestamp_kst) AS first_activity_at,
        COUNT(*) AS login_count
    FROM {{ ref('stg_events') }}
    WHERE event_name = 'auth_login_completed'
    GROUP BY 1, 2, 3
),

user_signup AS (
    SELECT
        user_id,
        signup_date
    FROM {{ ref('stg_users') }}
),

enriched AS (
    SELECT
        dl.activity_date,
        dl.user_id,
        dl.platform,
        dl.login_count,
        us.signup_date,
        CASE
            WHEN dl.activity_date = us.signup_date THEN 'new'
            ELSE 'returning'
        END AS user_type
    FROM daily_logins dl
    LEFT JOIN user_signup us ON dl.user_id = us.user_id
)

SELECT
    activity_date,
    user_id,
    platform,
    user_type,
    login_count,
    signup_date
FROM enriched
