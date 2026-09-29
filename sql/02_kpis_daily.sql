-- Business question: How is the business doing day by day?
-- Sessions, users, orders, revenue, session conversion rate, user conversion rate and
-- average order value (AOV = revenue / orders).
WITH ev AS (
  SELECT
    PARSE_DATE('%Y%m%d', event_date) AS day,
    user_pseudo_id,
    event_name,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
    ecommerce.purchase_revenue_in_usd AS revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
)
SELECT
  day,
  COUNT(DISTINCT CONCAT(user_pseudo_id, CAST(session_id AS STRING))) AS sessions,
  COUNT(DISTINCT user_pseudo_id) AS users,
  COUNTIF(event_name = 'purchase') AS orders,
  COUNT(DISTINCT IF(event_name = 'purchase', user_pseudo_id, NULL)) AS purchasers,
  ROUND(SUM(IF(event_name = 'purchase', revenue, 0)), 2) AS revenue,
  SAFE_DIVIDE(COUNTIF(event_name = 'purchase'),
              COUNT(DISTINCT CONCAT(user_pseudo_id, CAST(session_id AS STRING)))) AS session_conversion_rate,
  SAFE_DIVIDE(COUNT(DISTINCT IF(event_name = 'purchase', user_pseudo_id, NULL)),
              COUNT(DISTINCT user_pseudo_id)) AS user_conversion_rate,
  SAFE_DIVIDE(SUM(IF(event_name = 'purchase', revenue, 0)), COUNTIF(event_name = 'purchase')) AS aov
FROM ev
GROUP BY day
ORDER BY day
