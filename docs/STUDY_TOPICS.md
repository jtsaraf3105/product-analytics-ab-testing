# Topics to Study — product-analytics-ab-testing

Checklist in dependency order: **why here**, **explain**, **search terms**, **where in repo**, and
a **self-check** to answer out loud. About 20 hours over 1–2 weeks.

## Level 1 — SQL for analytics
### 1.1 CTEs and query structure
- **Explain:** `WITH` blocks as named steps; readability; when to materialise.
- **Search:** `SQL CTE tutorial`, `BigQuery WITH clause`
- **Repo:** every file in `sql/`
- **Self-check:** *Rewrite `04_funnel.sql` without CTEs. Why is it worse?*

### 1.2 Window functions
- **Explain:** `OVER (PARTITION BY … ORDER BY …)`; `ROW_NUMBER`, `LAG`, `FIRST_VALUE`, `NTILE`;
  frames; `QUALIFY` to filter on window results.
- **Search:** `SQL window functions explained`, `BigQuery QUALIFY`, `NTILE`
- **Repo:** `03` (QUALIFY top-N), `04` (LAG for step conversion), `06` (FIRST_VALUE cohort size), `07` (NTILE)
- **Self-check:** *What's the difference between `RANK`, `DENSE_RANK` and `ROW_NUMBER` on ties?*

### 1.3 GA4 BigQuery export schema
- **Explain:** sharded `events_*` tables + `_TABLE_SUFFIX`; nested `event_params` and `UNNEST`;
  `user_pseudo_id`; micro-second timestamps; how sessions are reconstructed from `ga_session_id`.
- **Search:** `GA4 BigQuery export schema`, `GA4 UNNEST event_params`, `ga4sql.com`
- **Repo:** `simulate/generate_ga4.py::SCHEMA`, any `sql/*.sql`
- **Self-check:** *Why is `_TABLE_SUFFIX` filtering important for BigQuery cost?*

### 1.4 SQL dialects and portability
- **Explain:** BigQuery vs DuckDB/Postgres differences; transpilers (`sqlglot`).
- **Repo:** `analytics/run_sql.py`, [DECISIONS.md](DECISIONS.md) D3
- **Self-check:** *Name two constructs that didn't port and how they were rewritten.*

## Level 2 — Product metrics
| Topic | Explain | Search | Repo |
|---|---|---|---|
| DAU/WAU/MAU & stickiness | rolling distinct counts; DAU/MAU | `DAU MAU stickiness` | `01_kpis_active_users.sql` |
| Conversion rate & AOV | per session vs per user; AOV = revenue/orders | `ecommerce conversion rate definition` | `02_kpis_daily.sql` |
| Funnel analysis | step conversion, drop-off, open vs closed funnels | `funnel analysis SQL` | `04`, `05` |
| Cohort retention | cohort definition, week-N, triangle heatmap; why aggregate retention misleads | `cohort retention analysis SQL` | `06_cohort_retention.sql` |
| RFM segmentation | recency/frequency/monetary scoring with NTILE; naming segments | `RFM segmentation SQL NTILE` | `07_rfm.sql` |
| North-star & guardrail metrics | primary vs secondary vs guardrail | `guardrail metrics experimentation` | notebook header |

## Level 3 — Experimentation statistics (the interview core)
### 3.1 Hypothesis testing basics
- **Explain:** H0/H1, α, p-value (and what it is *not*), type I/II errors, power.
- **Search:** `p-value misconceptions`, `type I type II error power`

### 3.2 Two-proportion z-test and chi-square
- **Explain:** pooled SE for the test, unpooled for the CI; chi-square on a 2×2 equals z²;
  when to use Fisher's exact test (tiny counts).
- **Search:** `two proportion z test formula`, `chi square test 2x2 equals z squared`
- **Repo:** `analytics/stats.py::two_proportion_ztest`, `chi_square_test`, `tests/test_stats.py`
- **Self-check:** *Compute z for 300/10,000 vs 360/10,000 by hand.*

### 3.3 Confidence intervals for lift
- **Explain:** absolute (pp) vs relative (%) lift; delta-method CI for a ratio; bootstrap for
  skewed metrics (revenue/user).
- **Search:** `confidence interval relative lift delta method`, `bootstrap confidence interval`

### 3.4 Power and sample size
- **Explain:** MDE, baseline rate, α, power → n; why small baselines need huge samples;
  post-hoc power is not a thing to report as evidence.
- **Search:** `sample size calculator A/B test`, `minimum detectable effect`, `Evan Miller sample size`
- **Repo:** `sample_size_per_arm`, `minimum_detectable_effect`, [DECISIONS.md](DECISIONS.md) D5
- **Self-check:** *Baseline 2.5%, MDE 8% relative: roughly how many users per arm?*

### 3.5 Sanity checks: SRM, contamination, duplicates
- **Explain:** sample ratio mismatch as a data-quality alarm (p < 0.001); why it must also be
  checked per day/segment; users exposed to both variants; logging bugs vs randomisation bugs.
- **Search:** `sample ratio mismatch Microsoft Fabijan`, `trustworthy online controlled experiments`
- **Repo:** notebook §1

### 3.6 Peeking, novelty, multiple comparisons, Simpson's paradox
- **Explain:** optional stopping inflates false positives (here 26% with 20 peeks); sequential
  tests; novelty/primacy effects and holdouts; segment analysis as exploration; Simpson's paradox.
- **Search:** `peeking problem A/B testing`, `novelty effect A/B test`, `Simpson's paradox example`, `Bonferroni vs Benjamini-Hochberg`
- **Repo:** notebook §5–§7

## Level 4 — BI & communication
| Topic | Search | Repo |
|---|---|---|
| Star schema (facts vs dimensions) | `Kimball star schema`, `Power BI star schema guidance` | `analytics/build_model.py`, `powerbi/MODEL.md` |
| DAX basics: CALCULATE, filter context, time intelligence | `DAX CALCULATE filter context`, `DAX DATEADD` | `powerbi/measures.dax` |
| Dashboard design | `dashboard design best practices` | `dashboard/index.html` |
| Writing for stakeholders | `Minto pyramid principle`, `BLUF writing` | `REPORT.md` |

## Level 5 — Compare & contrast
- Frequentist vs Bayesian A/B testing; CUPED variance reduction; switchback tests; multi-armed bandits.
- Tableau / Looker Studio vs Power BI (rebuild one page in Tableau Public to claim it honestly).

## Plan
| Days | Do |
|---|---|
| 1–3 | Level 1–2; run each SQL file with `python -m analytics.run_sql --only <name>` and explain its output. |
| 4–7 | Level 3; re-derive every number in the notebook with a calculator. |
| 8–9 | Level 4; build the Power BI report from `powerbi/MODEL.md`. |
| 10 | LEARNING_GUIDE out loud; present REPORT.md in 3 minutes. |
