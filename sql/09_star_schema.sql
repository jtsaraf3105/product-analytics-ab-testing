-- Business question: (modelling) Produce the fact table the Power BI star schema is built on:
-- one row per user-day with activity, funnel flags, orders and revenue. Dimensions (date,
-- device, channel, country, cohort) are derived from it in analytics/build_model.py.
WITH ev AS (
  SELECT
    PARSE_DATE('%Y%m%d', event_date) AS day,
    user_pseudo_id,
    event_name,
    device.category AS device,
    traffic_source.medium AS channel,
    geo.country AS country,
    DATE(TIMESTAMP_MICROS(user_first_touch_timestamp)) AS first_visit_date,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
    ecommerce.purchase_revenue_in_usd AS revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
)
SELECT
  day,
  user_pseudo_id,
  ANY_VALUE(device) AS device,
  ANY_VALUE(channel) AS channel,
  ANY_VALUE(country) AS country,
  MIN(first_visit_date) AS first_visit_date,
  COUNT(DISTINCT session_id) AS sessions,
  MAX(IF(event_name = 'view_item', 1, 0)) AS viewed_item,
  MAX(IF(event_name = 'add_to_cart', 1, 0)) AS added_to_cart,
  MAX(IF(event_name = 'begin_checkout', 1, 0)) AS began_checkout,
  COUNTIF(event_name = 'purchase') AS orders,
  ROUND(SUM(IF(event_name = 'purchase', revenue, 0)), 2) AS revenue
FROM ev
GROUP BY day, user_pseudo_id
