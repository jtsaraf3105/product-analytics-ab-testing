-- Business question: Did the one-page checkout (experiment one_page_checkout_v1,
-- 2020-12-01..2020-12-28) change purchase conversion?
-- One row per exposed user: first logged variant, whether they were logged in BOTH variants
-- (to be excluded), first exposure time, device/channel, and whether they purchased AFTER
-- their first exposure within the window (the primary metric), plus revenue (guardrail metric).
WITH ev AS (
  SELECT
    user_pseudo_id,
    event_name,
    event_timestamp,
    PARSE_DATE('%Y%m%d', event_date) AS day,
    device.category AS device,
    traffic_source.medium AS channel,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'experiment_id') AS experiment_id,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'variant') AS variant,
    ecommerce.purchase_revenue_in_usd AS revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201201' AND '20201228'
),
impressions AS (
  SELECT user_pseudo_id, variant, event_timestamp, day
  FROM ev
  WHERE event_name = 'experiment_impression' AND experiment_id = 'one_page_checkout_v1'
),
first_impression AS (
  SELECT *
  FROM impressions
  QUALIFY ROW_NUMBER() OVER (PARTITION BY user_pseudo_id ORDER BY event_timestamp) = 1
),
exposures AS (
  SELECT
    f.user_pseudo_id,
    f.event_timestamp AS first_exposure_ts,
    f.day AS first_exposure_day,
    f.variant,
    a.n_variants,
    a.n_impressions
  FROM first_impression AS f
  JOIN (
    SELECT user_pseudo_id, COUNT(DISTINCT variant) AS n_variants, COUNT(*) AS n_impressions
    FROM impressions
    GROUP BY user_pseudo_id
  ) AS a USING (user_pseudo_id)
),
outcomes AS (
  SELECT
    e.user_pseudo_id,
    MAX(IF(ev.event_name = 'purchase' AND ev.event_timestamp >= e.first_exposure_ts, 1, 0)) AS converted,
    SUM(IF(ev.event_name = 'purchase' AND ev.event_timestamp >= e.first_exposure_ts, ev.revenue, 0)) AS revenue,
    ANY_VALUE(ev.device) AS device,
    ANY_VALUE(ev.channel) AS channel
  FROM exposures AS e
  JOIN ev USING (user_pseudo_id)
  GROUP BY e.user_pseudo_id
)
SELECT
  e.user_pseudo_id,
  e.variant,
  e.n_variants,
  e.n_impressions,
  e.first_exposure_day,
  o.device,
  o.channel,
  o.converted,
  ROUND(o.revenue, 2) AS revenue
FROM exposures AS e
JOIN outcomes AS o USING (user_pseudo_id)
ORDER BY e.first_exposure_ts
