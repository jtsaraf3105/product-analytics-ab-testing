-- Business question: Which channels, devices and countries bring revenue — and which
-- convert their traffic best? (Where should marketing and UX effort go?)
WITH ev AS (
  SELECT
    user_pseudo_id,
    event_name,
    traffic_source.medium AS channel,
    device.category AS device,
    geo.country AS country,
    ecommerce.purchase_revenue_in_usd AS revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
),
seg AS (
  SELECT 'channel' AS dimension, channel AS segment, * EXCEPT (channel, device, country) FROM ev
  UNION ALL
  SELECT 'device', device, * EXCEPT (channel, device, country) FROM ev
  UNION ALL
  SELECT 'country', country, * EXCEPT (channel, device, country) FROM ev
)
SELECT
  dimension,
  segment,
  COUNT(DISTINCT user_pseudo_id) AS users,
  COUNT(DISTINCT IF(event_name = 'purchase', user_pseudo_id, NULL)) AS purchasers,
  COUNTIF(event_name = 'purchase') AS orders,
  ROUND(SUM(IF(event_name = 'purchase', revenue, 0)), 2) AS revenue,
  SAFE_DIVIDE(COUNT(DISTINCT IF(event_name = 'purchase', user_pseudo_id, NULL)),
              COUNT(DISTINCT user_pseudo_id)) AS user_conversion_rate,
  SAFE_DIVIDE(SUM(IF(event_name = 'purchase', revenue, 0)), COUNTIF(event_name = 'purchase')) AS aov,
  SAFE_DIVIDE(SUM(IF(event_name = 'purchase', revenue, 0)), COUNT(DISTINCT user_pseudo_id)) AS revenue_per_user
FROM seg
GROUP BY dimension, segment
QUALIFY ROW_NUMBER() OVER (PARTITION BY dimension ORDER BY SUM(IF(event_name = 'purchase', revenue, 0)) DESC) <= 12
ORDER BY dimension, revenue DESC
