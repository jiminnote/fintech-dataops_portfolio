/*
  stg_events — 이벤트 로그 스테이징
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  원본 events 테이블에서:
  - 타임스탬프 파싱 및 KST 변환
  - 봇/테스트 계정 제외
  - 필드명 표준화
*/

WITH source AS (
    SELECT * FROM {{ source('raw', 'events') }}
),

cleaned AS (
    SELECT
        event_id,
        event_name,
        
        -- 타임스탬프 처리
        CAST(event_timestamp AS TIMESTAMP) AS event_timestamp_utc,
        CAST(event_timestamp AS TIMESTAMP) + INTERVAL '9 hours' AS event_timestamp_kst,
        CAST(DATE_TRUNC('day', CAST(event_timestamp AS TIMESTAMP) + INTERVAL '9 hours') AS DATE) AS event_date_kst,
        EXTRACT(HOUR FROM CAST(event_timestamp AS TIMESTAMP) + INTERVAL '9 hours') AS event_hour_kst,
        
        CAST(received_at AS TIMESTAMP) AS received_at,
        
        -- 사용자/세션 정보
        user_id,
        session_id,
        device_id,
        platform,
        app_version,
        os_version,
        device_model,
        
        -- 도메인 분류
        SPLIT_PART(event_name, '_', 1) AS event_domain,
        
        -- 주요 이벤트 속성 (flatten)
        TRY_CAST(prop_amount AS BIGINT) AS amount,
        prop_screen_name AS screen_name,
        prop_merchant_id AS merchant_id,
        prop_merchant_category AS merchant_category,
        prop_error_code AS error_code,
        prop_signup_method AS signup_method,
        prop_transfer_type AS transfer_type,
        TRY_CAST(prop_fee AS BIGINT) AS fee,
        TRY_CAST(prop_latency_ms AS INTEGER) AS latency_ms
        
    FROM source
    WHERE
        -- 테스트 계정 제외
        user_id NOT LIKE 'usr_test%'
        -- null event_name 제외
        AND event_name IS NOT NULL
)

SELECT * FROM cleaned
