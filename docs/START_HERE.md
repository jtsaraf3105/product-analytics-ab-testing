# Start Here — product analytics & A/B testing, explained plainly

## 1. What this project does
An online store wants to know three things: **how is the business doing** (KPIs), **where do
customers get stuck** (funnel, retention, segments), and **did our change actually help** (A/B
test). This repo answers all three from raw event logs, the way an analyst on a product team would:
SQL to shape the data, statistics to decide, a dashboard to monitor, and a one-page memo that tells
leadership what to do.

## 2. The data in one picture
Google Analytics 4 records every user action as an **event** row:

```
event_date | event_timestamp | event_name     | user_pseudo_id | device.category | traffic_source.medium | ecommerce.purchase_revenue | event_params[...]
20201203   | 1606988012000000| view_item      | 181886.00067   | mobile          | organic               | NULL                       | [{ga_session_id: 1606987990}, ...]
20201203   | 1606988100000000| purchase       | 181886.00067   | mobile          | organic               | 58.40                      | [{transaction_id: T0004412}, ...]
```

`event_params` is a **nested list** of key/value pairs. Pulling one value out
(`(SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id')`) is the single
most common GA4 SQL idiom, and you'll see it everywhere in `sql/`.

## 3. The seven ideas
1. **Users, sessions, events.** Metrics depend on the denominator. Conversion *per session* ≠
   conversion *per user*. Always say which.
2. **Funnels.** Count users who reach each step, then compute step conversion and drop-off. The
   biggest drop is where the money is.
3. **Cohorts.** Group users by *when they arrived*, then follow each group over time. A healthy
   overall retention number can hide a bad cohort (here: holiday-sale shoppers).
4. **RFM.** Score purchasers on Recency, Frequency, Monetary value, and name the segments
   (Champions, At risk…) so marketing can act on each.
5. **A/B test = randomised comparison.** Randomly split users; the only systematic difference is the
   change, so a difference in outcomes is *caused* by it (within statistical noise).
6. **Check the data before the result.** Sample-ratio mismatch, users in both groups, duplicate
   logging. Here the overall check passed and a **daily** check caught an outage. That story is
   worth more in an interview than the p-value.
7. **Decide, don't just report.** The p-value says "probably not noise"; the confidence interval
   says "how big"; the guardrails say "nothing else broke"; the memo says "ship, with a holdout".

## 4. Reading order
1. [REPORT.md](../REPORT.md): the conclusions.
2. `sql/04_funnel.sql`, `06_cohort_retention.sql`, `07_rfm.sql`: the core SQL patterns.
3. [notebooks/ab_test.ipynb](../notebooks/ab_test.ipynb): the experiment, top to bottom.
4. [STUDY_TOPICS.md](STUDY_TOPICS.md): what to learn, in order.
5. [CONCEPTS.md](CONCEPTS.md), [ANALYSIS_TOUR.md](ANALYSIS_TOUR.md), [DECISIONS.md](DECISIONS.md).
6. [LEARNING_GUIDE.md](LEARNING_GUIDE.md): interview questions with model answers.
