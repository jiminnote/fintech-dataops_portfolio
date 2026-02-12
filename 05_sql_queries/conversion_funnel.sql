/*
  가입→첫송금 전환 퍼널 분석
  ━━━━━━━━━━━━━━━━━━━━━━━━━━
  6단계 퍼널의 단계별 전환율과 이탈률을 분석
*/

-- ① 전체 퍼널 전환율
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
)

SELECT
    'Step 1: 가입 시작' AS funnel_step,
    SUM(step1) AS users,
    ROUND(SUM(step1) * 100.0 / SUM(step1), 1) AS pct_from_start,
    100.0 AS pct_from_prev
FROM user_funnel
UNION ALL
SELECT
    'Step 2: 정보 제출',
    SUM(step2),
    ROUND(SUM(step2) * 100.0 / SUM(step1), 1),
    ROUND(SUM(step2) * 100.0 / SUM(step1), 1)
FROM user_funnel
UNION ALL
SELECT
    'Step 3: 가입 완료',
    SUM(step3),
    ROUND(SUM(step3) * 100.0 / SUM(step1), 1),
    ROUND(SUM(step3) * 100.0 / SUM(step2), 1)
FROM user_funnel
UNION ALL
SELECT
    'Step 4: 본인인증',
    SUM(step4),
    ROUND(SUM(step4) * 100.0 / SUM(step1), 1),
    ROUND(SUM(step4) * 100.0 / SUM(step3), 1)
FROM user_funnel
UNION ALL
SELECT
    'Step 5: 첫 송금 시도',
    SUM(step5),
    ROUND(SUM(step5) * 100.0 / SUM(step1), 1),
    ROUND(SUM(step5) * 100.0 / SUM(step4), 1)
FROM user_funnel
UNION ALL
SELECT
    'Step 6: 첫 송금 완료',
    SUM(step6),
    ROUND(SUM(step6) * 100.0 / SUM(step1), 1),
    ROUND(SUM(step6) * 100.0 / SUM(step5), 1)
FROM user_funnel;


-- ② 플랫폼별 퍼널 비교
WITH user_funnel_platform AS (
    SELECT
        user_id,
        platform,
        MAX(CASE WHEN event_name = 'auth_signup_started' THEN 1 ELSE 0 END) AS started,
        MAX(CASE WHEN event_name = 'auth_signup_completed' THEN 1 ELSE 0 END) AS completed,
        MAX(CASE WHEN event_name = 'payment_transfer_completed' THEN 1 ELSE 0 END) AS transferred
    FROM events
    WHERE event_name IN (
        'auth_signup_started', 'auth_signup_completed', 'payment_transfer_completed'
    )
    GROUP BY 1, 2
)
SELECT
    platform,
    SUM(started) AS signup_started,
    SUM(completed) AS signup_completed,
    SUM(transferred) AS first_transfer,
    ROUND(SUM(completed) * 100.0 / NULLIF(SUM(started), 0), 1) AS signup_rate,
    ROUND(SUM(transferred) * 100.0 / NULLIF(SUM(started), 0), 1) AS full_conversion_rate
FROM user_funnel_platform
GROUP BY 1
ORDER BY full_conversion_rate DESC;
