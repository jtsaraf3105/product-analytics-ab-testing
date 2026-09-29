-- Business question: Can we trust this data? How many events are malformed, duplicated,
-- or implausible before we compute any KPI?
-- Checks: null keys, exact-duplicate events, purchases without revenue/transaction id,
-- duplicate transaction ids, revenue outliers (> p99 * 3), events outside the analysis window.
WITH ev AS (
  SELECT
    *,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'transaction_id') AS transaction_id
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
),
dupes AS (
  SELECT COUNT(*) - COUNT(DISTINCT CONCAT(user_pseudo_id, '|', CAST(event_timestamp AS STRING), '|', event_name)) AS n
  FROM ev
),
purchases AS (
  SELECT transaction_id, ecommerce.purchase_revenue_in_usd AS revenue
  FROM ev
  WHERE event_name = 'purchase'
),
p99 AS (
  SELECT APPROX_QUANTILES(revenue, 100)[OFFSET(99)] AS v FROM purchases
)
SELECT 'total_events' AS check_name, COUNT(*) AS n FROM ev
UNION ALL SELECT 'null_user_pseudo_id', COUNTIF(user_pseudo_id IS NULL) FROM ev
UNION ALL SELECT 'null_event_timestamp', COUNTIF(event_timestamp IS NULL) FROM ev
UNION ALL SELECT 'null_device_category', COUNTIF(device.category IS NULL) FROM ev
UNION ALL SELECT 'duplicate_events_exact', (SELECT n FROM dupes)
UNION ALL SELECT 'purchases', COUNT(*) FROM purchases
UNION ALL SELECT 'purchases_missing_revenue', COUNTIF(revenue IS NULL OR revenue <= 0) FROM purchases
UNION ALL SELECT 'purchases_missing_transaction_id', COUNTIF(transaction_id IS NULL) FROM purchases
UNION ALL SELECT 'duplicate_transaction_ids', COUNT(*) - COUNT(DISTINCT transaction_id) FROM purchases
UNION ALL SELECT 'revenue_outliers_gt_3x_p99', COUNTIF(revenue > 3 * (SELECT v FROM p99)) FROM purchases
UNION ALL SELECT 'distinct_users', COUNT(DISTINCT user_pseudo_id) FROM ev
