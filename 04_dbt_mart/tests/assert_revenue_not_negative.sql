-- dbt test: 수수료 매출은 음수가 될 수 없음
-- mart_revenue.fee_revenue >= 0

SELECT
    transaction_month,
    transaction_type,
    fee_revenue
FROM {{ ref('mart_revenue') }}
WHERE fee_revenue < 0
