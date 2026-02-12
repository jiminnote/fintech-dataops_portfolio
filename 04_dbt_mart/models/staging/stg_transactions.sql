/*
  stg_transactions — 거래 데이터 스테이징
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  원본 transactions 테이블에서:
  - 금액 표준화 (음수 방지)
  - 상태 코드 매핑
  - 거래일자 파생
*/

WITH source AS (
    SELECT * FROM {{ source('raw', 'transactions') }}
),

cleaned AS (
    SELECT
        transaction_id,
        user_id,
        transaction_type,
        
        -- 금액 표준화
        CAST(ABS(amount) AS BIGINT) AS amount,
        CAST(COALESCE(fee, 0) AS BIGINT) AS fee,
        currency,
        
        -- 상태
        status,
        CASE
            WHEN status = 'completed' THEN '완료'
            WHEN status = 'failed' THEN '실패'
            WHEN status = 'pending' THEN '처리중'
            WHEN status = 'cancelled' THEN '취소'
            ELSE '기타'
        END AS status_label,
        
        -- 은행 정보
        bank_code,
        bank_name,
        
        -- 시간
        CAST(created_at AS TIMESTAMP) AS created_at,
        CAST(DATE_TRUNC('day', CAST(created_at AS TIMESTAMP)) AS DATE) AS transaction_date,
        CAST(DATE_TRUNC('month', CAST(created_at AS TIMESTAMP)) AS DATE) AS transaction_month,
        EXTRACT(HOUR FROM CAST(created_at AS TIMESTAMP)) AS transaction_hour,
        EXTRACT(DOW FROM CAST(created_at AS TIMESTAMP)) AS transaction_dow,
        CAST(completed_at AS TIMESTAMP) AS completed_at,
        
        -- 처리 시간 (초)
        CASE
            WHEN completed_at IS NOT NULL 
            THEN EXTRACT(EPOCH FROM CAST(completed_at AS TIMESTAMP) - CAST(created_at AS TIMESTAMP))
            ELSE NULL
        END AS processing_seconds,
        
        -- 에러 정보
        error_code,
        
        -- 가맹점 정보 (QR 결제)
        merchant_id,
        merchant_category
        
    FROM source
    WHERE
        amount > 0
        AND user_id IS NOT NULL
)

SELECT * FROM cleaned
