-- Business question: Is the checkout drop-off the same for everyone, or is one device /
-- channel leaking much more? (Segmented version of 04_funnel.sql, incl. the detailed checkout
-- sub-steps shipping -> payment -> purchase.)
WITH steps AS (
  SELECT
    user_pseudo_id,
    ANY_VALUE(device.category) AS device,
    ANY_VALUE(traffic_source.medium) AS channel,
    MAX(IF(event_name = 'view_item', 1, 0)) AS v,
    MAX(IF(event_name = 'add_to_cart', 1, 0)) AS c,
    MAX(IF(event_name = 'begin_checkout', 1, 0)) AS b,
    MAX(IF(event_name = 'add_shipping_info', 1, 0)) AS s,
    MAX(IF(event_name = 'add_payment_info', 1, 0)) AS p,
    MAX(IF(event_name = 'purchase', 1, 0)) AS o
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
  GROUP BY user_pseudo_id
),
seg AS (
  SELECT 'device' AS dimension, device AS segment, v, c, b, s, p, o FROM steps
  UNION ALL
  SELECT 'channel', channel, v, c, b, s, p, o FROM steps
)
SELECT
  dimension,
  segment,
  SUM(v) AS view_item,
  SUM(v * c) AS add_to_cart,
  SUM(v * c * b) AS begin_checkout,
  SUM(v * c * b * o) AS purchase,
  SAFE_DIVIDE(SUM(v * c), SUM(v)) AS cart_rate,
  SAFE_DIVIDE(SUM(v * c * b), SUM(v * c)) AS checkout_rate,
  SAFE_DIVIDE(SUM(v * c * b * o), SUM(v * c * b)) AS checkout_completion,
  1 - SAFE_DIVIDE(SUM(v * c * b * o), SUM(v * c * b)) AS checkout_drop_off,
  SAFE_DIVIDE(SUM(b * s), SUM(b)) AS shipping_rate,
  SAFE_DIVIDE(SUM(b * s * p), SUM(b * s)) AS payment_rate,
  SAFE_DIVIDE(SUM(b * s * p * o), SUM(b * s * p)) AS purchase_after_payment_rate,
  SAFE_DIVIDE(SUM(v * c * b * o), SUM(v)) AS view_to_purchase
FROM seg
GROUP BY dimension, segment
ORDER BY dimension, view_item DESC
