-- Business question: Do the users we acquire keep coming back — and are some cohorts
-- (e.g. the holiday-sale cohorts) worse than others? Aggregate retention hides this.
-- Weekly cohorts by first visit; retention(week N) = active users in week N / cohort size.
WITH activity AS (
  SELECT DISTINCT
    user_pseudo_id,
    DATE_TRUNC(PARSE_DATE('%Y%m%d', event_date), WEEK(MONDAY)) AS activity_week
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
),
first_seen AS (
  SELECT user_pseudo_id, MIN(activity_week) AS cohort_week
  FROM activity
  GROUP BY user_pseudo_id
),
cohort_activity AS (
  SELECT
    f.cohort_week,
    DATE_DIFF(a.activity_week, f.cohort_week, WEEK) AS week_n,
    COUNT(DISTINCT a.user_pseudo_id) AS active_users
  FROM activity AS a
  JOIN first_seen AS f USING (user_pseudo_id)
  GROUP BY f.cohort_week, week_n
)
SELECT
  cohort_week,
  week_n,
  active_users,
  FIRST_VALUE(active_users) OVER (PARTITION BY cohort_week ORDER BY week_n) AS cohort_size,
  SAFE_DIVIDE(active_users, FIRST_VALUE(active_users) OVER (PARTITION BY cohort_week ORDER BY week_n)) AS retention
FROM cohort_activity
ORDER BY cohort_week, week_n
