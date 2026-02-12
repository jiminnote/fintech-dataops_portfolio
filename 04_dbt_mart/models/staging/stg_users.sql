/*
  stg_users — 사용자 데이터 스테이징
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*/

WITH source AS (
    SELECT * FROM {{ source('raw', 'users') }}
)

SELECT
    user_id,
    device_id,
    platform,
    device_model,
    CAST(signup_date AS DATE) AS signup_date,
    DATE_TRUNC('week', CAST(signup_date AS DATE))::DATE AS signup_week,
    DATE_TRUNC('month', CAST(signup_date AS DATE))::DATE AS signup_month,
    signup_method,
    
    -- 가입 경과일 (현재 기준)
    CURRENT_DATE - CAST(signup_date AS DATE) AS days_since_signup

FROM source
WHERE user_id NOT LIKE 'usr_test%'
