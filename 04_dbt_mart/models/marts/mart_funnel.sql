/*
  mart_funnel — 퍼널 전환 분석 마트
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Tableau 퍼널 대시보드의 데이터 소스
  가입→인증→첫 송금 퍼널의 단계별 전환율
*/

WITH funnel_summary AS (
    SELECT
        COUNT(*) AS total_users,
        
        -- 절대 수치
        SUM(CASE WHEN reached_signup_start THEN 1 ELSE 0 END) AS step1_signup_started,
        SUM(CASE WHEN reached_signup_submit THEN 1 ELSE 0 END) AS step2_signup_submitted,
        SUM(CASE WHEN reached_signup_complete THEN 1 ELSE 0 END) AS step3_signup_completed,
        SUM(CASE WHEN reached_identity_verify THEN 1 ELSE 0 END) AS step4_identity_verified,
        SUM(CASE WHEN reached_first_transfer_start THEN 1 ELSE 0 END) AS step5_transfer_started,
        SUM(CASE WHEN reached_first_transfer_complete THEN 1 ELSE 0 END) AS step6_transfer_completed,
        
        -- 평균 전환 시간
        AVG(minutes_to_signup) AS avg_minutes_to_signup,
        AVG(hours_to_first_transfer) AS avg_hours_to_first_transfer,
        
        -- 중앙값 전환 시간
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY minutes_to_signup) AS median_minutes_to_signup,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY hours_to_first_transfer) AS median_hours_to_first_transfer
        
    FROM {{ ref('int_funnel_conversion') }}
)

SELECT
    -- 퍼널 단계별 수치 (Tableau용 long format)
    'Step 1: 가입 시작' AS funnel_step,
    1 AS step_order,
    step1_signup_started AS users,
    100.0 AS conversion_from_start,
    100.0 AS conversion_from_prev,
    NULL::FLOAT AS avg_time_minutes
FROM funnel_summary

UNION ALL

SELECT
    'Step 2: 정보 제출',
    2,
    step2_signup_submitted,
    ROUND(step2_signup_submitted * 100.0 / NULLIF(step1_signup_started, 0), 2),
    ROUND(step2_signup_submitted * 100.0 / NULLIF(step1_signup_started, 0), 2),
    NULL
FROM funnel_summary

UNION ALL

SELECT
    'Step 3: 가입 완료',
    3,
    step3_signup_completed,
    ROUND(step3_signup_completed * 100.0 / NULLIF(step1_signup_started, 0), 2),
    ROUND(step3_signup_completed * 100.0 / NULLIF(step2_signup_submitted, 0), 2),
    avg_minutes_to_signup
FROM funnel_summary

UNION ALL

SELECT
    'Step 4: 본인인증',
    4,
    step4_identity_verified,
    ROUND(step4_identity_verified * 100.0 / NULLIF(step1_signup_started, 0), 2),
    ROUND(step4_identity_verified * 100.0 / NULLIF(step3_signup_completed, 0), 2),
    NULL
FROM funnel_summary

UNION ALL

SELECT
    'Step 5: 첫 송금 시도',
    5,
    step5_transfer_started,
    ROUND(step5_transfer_started * 100.0 / NULLIF(step1_signup_started, 0), 2),
    ROUND(step5_transfer_started * 100.0 / NULLIF(step4_identity_verified, 0), 2),
    NULL
FROM funnel_summary

UNION ALL

SELECT
    'Step 6: 첫 송금 완료',
    6,
    step6_transfer_completed,
    ROUND(step6_transfer_completed * 100.0 / NULLIF(step1_signup_started, 0), 2),
    ROUND(step6_transfer_completed * 100.0 / NULLIF(step5_transfer_started, 0), 2),
    avg_hours_to_first_transfer * 60  -- 시간→분 변환
FROM funnel_summary
