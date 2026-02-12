/*
  이상 거래 탐지 (Anomaly Detection)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Z-score + 이동평균 기반 이상치 탐지
  - 일별 거래 볼륨 이상
  - 고액 거래 탐지
  - 에러율 급증 탐지
*/

-- ① 일별 거래 볼륨 이상 탐지 (Z-score)
WITH daily_volume AS (
    SELECT
        CAST(created_at AS DATE) AS txn_date,
        COUNT(*) AS txn_count,
        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) AS daily_gmv,
        COUNT(CASE WHEN status = 'failed' THEN 1 END) AS failed_count,
        ROUND(COUNT(CASE WHEN status = 'failed' THEN 1 END) * 100.0 / COUNT(*), 2) AS error_rate
    FROM transactions
    GROUP BY 1
),
stats AS (
    SELECT
        AVG(txn_count) AS mean_txn,
        STDDEV(txn_count) AS std_txn,
        AVG(daily_gmv) AS mean_gmv,
        STDDEV(daily_gmv) AS std_gmv,
        AVG(error_rate) AS mean_error_rate,
        STDDEV(error_rate) AS std_error_rate
    FROM daily_volume
)

SELECT
    dv.txn_date,
    dv.txn_count,
    dv.daily_gmv,
    dv.error_rate,
    
    -- Z-score (거래 건수)
    ROUND((dv.txn_count - s.mean_txn) / NULLIF(s.std_txn, 0), 2) AS txn_count_zscore,
    
    -- Z-score (GMV)
    ROUND((dv.daily_gmv - s.mean_gmv) / NULLIF(s.std_gmv, 0), 2) AS gmv_zscore,
    
    -- Z-score (에러율)
    ROUND((dv.error_rate - s.mean_error_rate) / NULLIF(s.std_error_rate, 0), 2) AS error_rate_zscore,
    
    -- 이상 여부 (|Z| > 2)
    CASE WHEN ABS((dv.txn_count - s.mean_txn) / NULLIF(s.std_txn, 0)) > 2 THEN '🔴 ALERT' ELSE '✅ OK' END AS txn_alert,
    CASE WHEN ABS((dv.error_rate - s.mean_error_rate) / NULLIF(s.std_error_rate, 0)) > 2 THEN '🔴 ALERT' ELSE '✅ OK' END AS error_alert

FROM daily_volume dv
CROSS JOIN stats s
ORDER BY dv.txn_date;


-- ② 고액 거래 탐지 (사용자 평균 대비 10배 이상)
WITH user_avg AS (
    SELECT
        user_id,
        AVG(amount) AS avg_amount,
        STDDEV(amount) AS std_amount,
        COUNT(*) AS txn_count
    FROM transactions
    WHERE status = 'completed'
    GROUP BY 1
    HAVING COUNT(*) >= 5  -- 최소 5건 이상 거래 이력
)

SELECT
    t.transaction_id,
    t.user_id,
    t.transaction_type,
    t.amount,
    t.created_at,
    ua.avg_amount AS user_avg_amount,
    ROUND(t.amount / NULLIF(ua.avg_amount, 0), 1) AS amount_ratio,
    ROUND((t.amount - ua.avg_amount) / NULLIF(ua.std_amount, 0), 2) AS user_zscore,
    '⚠️ 고액 거래' AS alert_type
FROM transactions t
JOIN user_avg ua ON t.user_id = ua.user_id
WHERE t.status = 'completed'
  AND t.amount > ua.avg_amount * 10
ORDER BY amount_ratio DESC
LIMIT 50;


-- ③ 에러 코드별 추이 (에러 급증 탐지)
WITH daily_errors AS (
    SELECT
        CAST(created_at AS DATE) AS error_date,
        error_code,
        COUNT(*) AS error_count
    FROM transactions
    WHERE status = 'failed' AND error_code IS NOT NULL
    GROUP BY 1, 2
),
error_avg AS (
    SELECT
        error_code,
        AVG(error_count) AS avg_daily_errors,
        STDDEV(error_count) AS std_daily_errors
    FROM daily_errors
    GROUP BY 1
)
SELECT
    de.error_date,
    de.error_code,
    de.error_count,
    ea.avg_daily_errors,
    CASE
        WHEN de.error_count > ea.avg_daily_errors + 2 * ea.std_daily_errors
        THEN '🔴 에러 급증'
        ELSE '✅ 정상'
    END AS alert
FROM daily_errors de
JOIN error_avg ea ON de.error_code = ea.error_code
WHERE de.error_count > ea.avg_daily_errors + 2 * ea.std_daily_errors
ORDER BY de.error_date, de.error_count DESC;
