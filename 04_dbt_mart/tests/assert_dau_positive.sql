-- dbt test: DAU는 항상 양수여야 함
-- mart_daily_kpi.dau > 0

SELECT
    date,
    dau
FROM {{ ref('mart_daily_kpi') }}
WHERE dau <= 0
