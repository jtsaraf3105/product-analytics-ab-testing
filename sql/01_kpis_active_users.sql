-- Business question: How big and how sticky is the active audience?
-- DAU = distinct users per day; WAU / MAU = distinct users in the trailing 7 / 28 days;
-- stickiness = DAU / MAU (how many monthly users come back on a given day).
WITH daily_users AS (
  SELECT DISTINCT PARSE_DATE('%Y%m%d', event_date) AS day, user_pseudo_id
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
),
days AS (SELECT DISTINCT day FROM daily_users)
SELECT
  d.day,
  COUNT(DISTINCT IF(u.day = d.day, u.user_pseudo_id, NULL)) AS dau,
  COUNT(DISTINCT IF(u.day > DATE_SUB(d.day, INTERVAL 7 DAY), u.user_pseudo_id, NULL)) AS wau,
  COUNT(DISTINCT u.user_pseudo_id) AS mau,
  SAFE_DIVIDE(COUNT(DISTINCT IF(u.day = d.day, u.user_pseudo_id, NULL)),
              COUNT(DISTINCT u.user_pseudo_id)) AS stickiness_dau_mau
FROM days AS d
JOIN daily_users AS u
  ON u.day > DATE_SUB(d.day, INTERVAL 28 DAY) AND u.day <= d.day
GROUP BY d.day
ORDER BY d.day
