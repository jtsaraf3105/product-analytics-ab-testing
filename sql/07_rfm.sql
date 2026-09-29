-- Business question: Who are our best customers, and who is slipping away?
-- RFM: Recency (days since last order), Frequency (orders), Monetary (revenue), each scored
-- 1-5 with NTILE over purchasers, then mapped to named segments.
WITH orders AS (
  SELECT
    user_pseudo_id,
    PARSE_DATE('%Y%m%d', event_date) AS order_date,
    ecommerce.purchase_revenue_in_usd AS revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
    AND event_name = 'purchase'
),
per_user AS (
  SELECT
    user_pseudo_id,
    DATE_DIFF(DATE '2021-01-31', MAX(order_date), DAY) AS recency_days,
    COUNT(*) AS frequency,
    ROUND(SUM(revenue), 2) AS monetary
  FROM orders
  GROUP BY user_pseudo_id
),
scored AS (
  SELECT
    *,
    6 - NTILE(5) OVER (ORDER BY recency_days) AS r_score,   -- recent = 5
    NTILE(5) OVER (ORDER BY frequency, monetary) AS f_score, -- ties broken by value
    NTILE(5) OVER (ORDER BY monetary) AS m_score
  FROM per_user
)
SELECT
  *,
  CASE
    WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
    WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
    WHEN r_score >= 4 AND f_score <= 2 THEN 'New / promising'
    WHEN r_score <= 2 AND f_score >= 3 THEN 'At risk'
    WHEN r_score <= 2 AND f_score <= 2 AND m_score >= 4 THEN 'Big spenders, lapsed'
    WHEN r_score <= 2 THEN 'Hibernating'
    ELSE 'Needs attention'
  END AS segment
FROM scored
ORDER BY monetary DESC
