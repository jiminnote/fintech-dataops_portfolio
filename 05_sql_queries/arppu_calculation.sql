/*
  ARPPU (Average Revenue Per Paying User) 분석
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  월별 수수료 기반 ARPPU, ARPU, 사용자 세그먼트별 매출 분석
*/

-- ① 월별 ARPPU & ARPU
WITH monthly_metrics AS (
    SELECT
        DATE_TRUNC('month', created_at)::DATE AS month,
        
        COUNT(DISTINCT user_id) AS total_users,
        COUNT(DISTINCT CASE WHEN fee > 0 THEN user_id END) AS paying_users,
        
        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) AS total_gmv,
        SUM(CASE WHEN status = 'completed' THEN fee ELSE 0 END) AS total_fee_revenue,
        
        COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed_txns,
        AVG(CASE WHEN status = 'completed' THEN amount END) AS avg_txn_amount
        
    FROM transactions
    GROUP BY 1
)

SELECT
    month,
    total_users,
    paying_users,
    total_gmv,
    total_fee_revenue,
    completed_txns,
    ROUND(avg_txn_amount) AS avg_txn_amount,
    
    -- ARPPU (결제 사용자당 평균 매출)
    ROUND(total_fee_revenue * 1.0 / NULLIF(paying_users, 0)) AS arppu,
    
    -- ARPU (전체 사용자당 평균 매출)
    ROUND(total_fee_revenue * 1.0 / NULLIF(total_users, 0)) AS arpu,
    
    -- 유료 사용자 비율
    ROUND(paying_users * 100.0 / NULLIF(total_users, 0), 2) AS paying_user_ratio
    
FROM monthly_metrics
ORDER BY month;


-- ② 거래 유형별 월 매출 분해
SELECT
    DATE_TRUNC('month', created_at)::DATE AS month,
    transaction_type,
    COUNT(*) AS txn_count,
    SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) AS gmv,
    SUM(CASE WHEN status = 'completed' THEN fee ELSE 0 END) AS fee_revenue,
    COUNT(DISTINCT user_id) AS unique_users,
    ROUND(AVG(CASE WHEN status = 'completed' THEN amount END)) AS avg_amount
FROM transactions
GROUP BY 1, 2
ORDER BY 1, gmv DESC;


-- ③ 사용자 tier별 매출 (Whale Analysis)
WITH user_monthly_revenue AS (
    SELECT
        user_id,
        DATE_TRUNC('month', created_at)::DATE AS month,
        SUM(CASE WHEN status = 'completed' THEN fee ELSE 0 END) AS monthly_fee,
        COUNT(CASE WHEN status = 'completed' THEN 1 END) AS monthly_txns
    FROM transactions
    GROUP BY 1, 2
),
user_tier AS (
    SELECT
        *,
        CASE
            WHEN monthly_fee >= 2000 THEN 'Heavy (₩2,000+)'
            WHEN monthly_fee >= 500 THEN 'Medium (₩500~2,000)'
            WHEN monthly_fee > 0 THEN 'Light (₩1~500)'
            ELSE 'Free'
        END AS user_tier
    FROM user_monthly_revenue
)
SELECT
    month,
    user_tier,
    COUNT(DISTINCT user_id) AS users,
    SUM(monthly_fee) AS total_fee,
    ROUND(AVG(monthly_fee)) AS avg_fee,
    ROUND(SUM(monthly_fee) * 100.0 / SUM(SUM(monthly_fee)) OVER (PARTITION BY month), 2) AS revenue_share_pct
FROM user_tier
GROUP BY 1, 2
ORDER BY 1, total_fee DESC;
