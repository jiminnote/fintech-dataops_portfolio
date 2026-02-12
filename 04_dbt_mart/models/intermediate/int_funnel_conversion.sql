/*
  int_funnel_conversion — 가입→첫송금 퍼널 전환 분석
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  각 사용자별 퍼널 단계 도달 여부와 전환 시간을 계산
*/

WITH signup_events AS (
    SELECT
        user_id,
        event_date_kst AS event_date,
        event_timestamp_kst AS event_ts,
        event_name
    FROM {{ ref('stg_events') }}
    WHERE event_name IN (
        'auth_signup_started',
        'auth_signup_submitted', 
        'auth_signup_completed',
        'auth_identity_verified',
        'payment_transfer_started',
        'payment_transfer_completed'
    )
),

user_funnel AS (
    SELECT
        user_id,
        
        -- 각 퍼널 단계 최초 도달 시각
        MIN(CASE WHEN event_name = 'auth_signup_started' THEN event_ts END) AS signup_started_at,
        MIN(CASE WHEN event_name = 'auth_signup_submitted' THEN event_ts END) AS signup_submitted_at,
        MIN(CASE WHEN event_name = 'auth_signup_completed' THEN event_ts END) AS signup_completed_at,
        MIN(CASE WHEN event_name = 'auth_identity_verified' THEN event_ts END) AS identity_verified_at,
        MIN(CASE WHEN event_name = 'payment_transfer_started' THEN event_ts END) AS first_transfer_started_at,
        MIN(CASE WHEN event_name = 'payment_transfer_completed' THEN event_ts END) AS first_transfer_completed_at,
        
        -- 퍼널 도달 여부
        COUNT(CASE WHEN event_name = 'auth_signup_started' THEN 1 END) > 0 AS reached_signup_start,
        COUNT(CASE WHEN event_name = 'auth_signup_submitted' THEN 1 END) > 0 AS reached_signup_submit,
        COUNT(CASE WHEN event_name = 'auth_signup_completed' THEN 1 END) > 0 AS reached_signup_complete,
        COUNT(CASE WHEN event_name = 'auth_identity_verified' THEN 1 END) > 0 AS reached_identity_verify,
        COUNT(CASE WHEN event_name = 'payment_transfer_started' THEN 1 END) > 0 AS reached_first_transfer_start,
        COUNT(CASE WHEN event_name = 'payment_transfer_completed' THEN 1 END) > 0 AS reached_first_transfer_complete
        
    FROM signup_events
    GROUP BY 1
)

SELECT
    user_id,
    signup_started_at,
    signup_completed_at,
    identity_verified_at,
    first_transfer_completed_at,
    
    reached_signup_start,
    reached_signup_submit,
    reached_signup_complete,
    reached_identity_verify,
    reached_first_transfer_start,
    reached_first_transfer_complete,
    
    -- 전환 소요 시간 (분)
    CASE
        WHEN signup_completed_at IS NOT NULL AND signup_started_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM signup_completed_at - signup_started_at) / 60
    END AS minutes_to_signup,
    
    CASE
        WHEN first_transfer_completed_at IS NOT NULL AND signup_completed_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM first_transfer_completed_at - signup_completed_at) / 3600
    END AS hours_to_first_transfer

FROM user_funnel
