/*
  mart_daily_kpi — 일간 핵심 KPI 마트
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Tableau 대시보드의 메인 데이터 소스
  DAU, MAU, 거래 건수, GMV, 수수료 매출 등 핵심 지표를 일자별 집계
*/

WITH daily_users AS (
    SELECT
        activity_date,
        COUNT(DISTINCT user_id) AS dau,
        COUNT(DISTINCT CASE WHEN user_type = 'new' THEN user_id END) AS new_users,
        COUNT(DISTINCT CASE WHEN user_type = 'returning' THEN user_id END) AS returning_users,
        COUNT(DISTINCT CASE WHEN platform = 'ios' THEN user_id END) AS dau_ios,
        COUNT(DISTINCT CASE WHEN platform = 'android' THEN user_id END) AS dau_android,
        COUNT(DISTINCT CASE WHEN platform = 'web' THEN user_id END) AS dau_web
    FROM {{ ref('int_daily_active_users') }}
    GROUP BY 1
),

daily_transactions AS (
    SELECT
        transaction_date,
        
        -- 전체 거래
        COUNT(*) AS total_transactions,
        COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed_transactions,
        COUNT(CASE WHEN status = 'failed' THEN 1 END) AS failed_transactions,
        
        -- GMV
        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) AS gmv,
        SUM(CASE WHEN status = 'completed' AND transaction_type = 'transfer' THEN amount ELSE 0 END) AS transfer_gmv,
        SUM(CASE WHEN status = 'completed' AND transaction_type = 'qr_payment' THEN amount ELSE 0 END) AS qr_payment_gmv,
        
        -- 수수료
        SUM(CASE WHEN status = 'completed' THEN fee ELSE 0 END) AS total_fee_revenue,
        
        -- 평균 거래액
        AVG(CASE WHEN status = 'completed' THEN amount END) AS avg_transaction_amount,
        AVG(CASE WHEN status = 'completed' AND transaction_type = 'transfer' THEN amount END) AS avg_transfer_amount,
        
        -- 거래 유형별 건수
        COUNT(CASE WHEN transaction_type = 'transfer' AND status = 'completed' THEN 1 END) AS transfer_count,
        COUNT(CASE WHEN transaction_type = 'qr_payment' AND status = 'completed' THEN 1 END) AS qr_payment_count,
        COUNT(CASE WHEN transaction_type = 'charge' AND status = 'completed' THEN 1 END) AS charge_count,
        
        -- 성공률
        ROUND(
            COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0),
            2
        ) AS success_rate
        
    FROM {{ ref('stg_transactions') }}
    GROUP BY 1
),

-- 7일 / 30일 Rolling MAU
rolling_users AS (
    SELECT
        du.activity_date,
        COUNT(DISTINCT all_users.user_id) AS wau_7d,
        (SELECT COUNT(DISTINCT u2.user_id)
         FROM {{ ref('int_daily_active_users') }} u2
         WHERE u2.activity_date BETWEEN du.activity_date - INTERVAL '29 days' AND du.activity_date
        ) AS mau_30d
    FROM (SELECT DISTINCT activity_date FROM {{ ref('int_daily_active_users') }}) du
    LEFT JOIN {{ ref('int_daily_active_users') }} all_users
        ON all_users.activity_date BETWEEN du.activity_date - INTERVAL '6 days' AND du.activity_date
    GROUP BY 1
)

SELECT
    du.activity_date AS date,
    EXTRACT(DOW FROM du.activity_date) AS day_of_week,
    CASE EXTRACT(DOW FROM du.activity_date)
        WHEN 0 THEN '일' WHEN 1 THEN '월' WHEN 2 THEN '화' WHEN 3 THEN '수'
        WHEN 4 THEN '목' WHEN 5 THEN '금' WHEN 6 THEN '토'
    END AS day_name,
    
    -- 사용자 지표
    du.dau,
    du.new_users,
    du.returning_users,
    du.dau_ios,
    du.dau_android,
    du.dau_web,
    ru.wau_7d,
    ru.mau_30d,
    ROUND(du.dau * 100.0 / NULLIF(ru.mau_30d, 0), 2) AS stickiness_ratio,
    
    -- 거래 지표
    COALESCE(dt.total_transactions, 0) AS total_transactions,
    COALESCE(dt.completed_transactions, 0) AS completed_transactions,
    COALESCE(dt.failed_transactions, 0) AS failed_transactions,
    COALESCE(dt.success_rate, 0) AS success_rate,
    
    -- 매출 지표
    COALESCE(dt.gmv, 0) AS gmv,
    COALESCE(dt.transfer_gmv, 0) AS transfer_gmv,
    COALESCE(dt.qr_payment_gmv, 0) AS qr_payment_gmv,
    COALESCE(dt.total_fee_revenue, 0) AS fee_revenue,
    
    -- 평균 지표
    dt.avg_transaction_amount,
    dt.avg_transfer_amount,
    COALESCE(dt.transfer_count, 0) AS transfer_count,
    COALESCE(dt.qr_payment_count, 0) AS qr_payment_count,
    COALESCE(dt.charge_count, 0) AS charge_count,
    
    -- 인당 지표
    ROUND(COALESCE(dt.gmv, 0) * 1.0 / NULLIF(du.dau, 0), 0) AS gmv_per_dau,
    ROUND(COALESCE(dt.total_transactions, 0) * 1.0 / NULLIF(du.dau, 0), 2) AS txn_per_dau

FROM daily_users du
LEFT JOIN daily_transactions dt ON du.activity_date = dt.transaction_date
LEFT JOIN rolling_users ru ON du.activity_date = ru.activity_date
ORDER BY du.activity_date
