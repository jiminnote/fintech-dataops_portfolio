/*
  mart_retention — 코호트 리텐션 마트
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Tableau 리텐션 히트맵 대시보드의 데이터 소스
  가입 주차별 코호트의 D1~D30 리텐션율
*/

WITH cohort_base AS (
    SELECT
        signup_week,
        signup_month,
        platform,
        user_id
    FROM {{ ref('stg_users') }}
),

cohort_retention AS (
    SELECT
        uc.signup_week,
        uc.signup_month,
        uc.platform,
        uc.user_id,
        MAX(uc.retained_d1) AS retained_d1,
        MAX(uc.retained_d3) AS retained_d3,
        MAX(uc.retained_d7) AS retained_d7,
        MAX(uc.retained_d14) AS retained_d14,
        MAX(uc.retained_d30) AS retained_d30
    FROM {{ ref('int_user_cohort') }} uc
    GROUP BY 1, 2, 3, 4
)

SELECT
    signup_week,
    signup_month,
    platform,
    
    -- 코호트 크기
    COUNT(DISTINCT user_id) AS cohort_size,
    
    -- 리텐션 인원
    SUM(retained_d1) AS retained_d1_users,
    SUM(retained_d3) AS retained_d3_users,
    SUM(retained_d7) AS retained_d7_users,
    SUM(retained_d14) AS retained_d14_users,
    SUM(retained_d30) AS retained_d30_users,
    
    -- 리텐션율
    ROUND(SUM(retained_d1) * 100.0 / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS retention_d1,
    ROUND(SUM(retained_d3) * 100.0 / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS retention_d3,
    ROUND(SUM(retained_d7) * 100.0 / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS retention_d7,
    ROUND(SUM(retained_d14) * 100.0 / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS retention_d14,
    ROUND(SUM(retained_d30) * 100.0 / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS retention_d30

FROM cohort_retention
GROUP BY 1, 2, 3
ORDER BY signup_week, platform
