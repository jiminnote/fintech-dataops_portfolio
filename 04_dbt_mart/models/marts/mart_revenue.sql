/*
  mart_revenue — 매출 분석 마트
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Tableau 매출 대시보드의 데이터 소스
  월별 ARPPU, 수수료 매출, 거래 유형별 분석
*/

WITH monthly_revenue AS (
    SELECT
        transaction_month,
        transaction_type,
        
        -- 거래 건수
        COUNT(*) AS total_transactions,
        COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed_count,
        
        -- GMV
        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) AS gmv,
        
        -- 수수료 매출
        SUM(CASE WHEN status = 'completed' THEN fee ELSE 0 END) AS fee_revenue,
        
        -- 유니크 사용자
        COUNT(DISTINCT user_id) AS unique_users,
        COUNT(DISTINCT CASE WHEN status = 'completed' AND fee > 0 THEN user_id END) AS paying_users,
        
        -- 평균
        AVG(CASE WHEN status = 'completed' THEN amount END) AS avg_amount,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CASE WHEN status = 'completed' THEN amount END) AS median_amount
        
    FROM {{ ref('stg_transactions') }}
    GROUP BY 1, 2
),

monthly_total AS (
    SELECT
        transaction_month,
        SUM(gmv) AS total_gmv,
        SUM(fee_revenue) AS total_fee_revenue,
        SUM(unique_users) AS total_unique_users,
        SUM(paying_users) AS total_paying_users
    FROM monthly_revenue
    GROUP BY 1
)

SELECT
    mr.transaction_month,
    mr.transaction_type,
    mr.total_transactions,
    mr.completed_count,
    mr.gmv,
    mr.fee_revenue,
    mr.unique_users,
    mr.paying_users,
    mr.avg_amount,
    mr.median_amount,
    
    -- ARPPU (결제 사용자당 평균 매출)
    ROUND(mr.fee_revenue * 1.0 / NULLIF(mr.paying_users, 0), 0) AS arppu,
    
    -- ARPU (전체 사용자당 평균 매출)
    ROUND(mr.fee_revenue * 1.0 / NULLIF(mr.unique_users, 0), 0) AS arpu,
    
    -- 거래 유형 비중
    ROUND(mr.gmv * 100.0 / NULLIF(mt.total_gmv, 0), 2) AS gmv_share_pct,
    
    -- 전월 대비 (self-join으로 계산하면 좋지만, 단순화)
    mt.total_gmv AS monthly_total_gmv,
    mt.total_fee_revenue AS monthly_total_fee_revenue

FROM monthly_revenue mr
LEFT JOIN monthly_total mt ON mr.transaction_month = mt.transaction_month
ORDER BY mr.transaction_month, mr.transaction_type
