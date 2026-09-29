-- Business question: Where do shoppers drop out between seeing a product and paying?
-- User-level funnel: a user counts at a step if they ever fired that event in the window.
-- Step conversion = step / previous step; drop-off = 1 - step conversion.
WITH steps AS (
  SELECT
    user_pseudo_id,
    MAX(IF(event_name = 'view_item', 1, 0)) AS s1_view_item,
    MAX(IF(event_name = 'add_to_cart', 1, 0)) AS s2_add_to_cart,
    MAX(IF(event_name = 'begin_checkout', 1, 0)) AS s3_begin_checkout,
    MAX(IF(event_name = 'purchase', 1, 0)) AS s4_purchase
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
  GROUP BY user_pseudo_id
),
counts AS (
  SELECT 1 AS step_order, 'view_item' AS step, SUM(s1_view_item) AS users FROM steps
  UNION ALL SELECT 2, 'add_to_cart', SUM(s1_view_item * s2_add_to_cart) FROM steps
  UNION ALL SELECT 3, 'begin_checkout', SUM(s1_view_item * s2_add_to_cart * s3_begin_checkout) FROM steps
  UNION ALL SELECT 4, 'purchase', SUM(s1_view_item * s2_add_to_cart * s3_begin_checkout * s4_purchase) FROM steps
)
SELECT
  step_order,
  step,
  users,
  SAFE_DIVIDE(users, LAG(users) OVER (ORDER BY step_order)) AS step_conversion,
  1 - SAFE_DIVIDE(users, LAG(users) OVER (ORDER BY step_order)) AS drop_off,
  SAFE_DIVIDE(users, FIRST_VALUE(users) OVER (ORDER BY step_order)) AS conversion_from_view
FROM counts
ORDER BY step_order
