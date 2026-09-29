# Analysis Tour — from raw events to a decision

## 1. Generate (or query) the events — `simulate/generate_ga4.py`
Day by day, new users arrive (weekly seasonality, Black-Friday and December peaks). Each gets a
device, country and channel, and a chance of returning that depends on all three (holiday arrivals
return less). Each session walks the funnel with realistic step probabilities (mobile is worse at
every checkout step). During 1–28 Dec, every active user gets an `experiment_impression` with a
hash-assigned variant; treatment raises two checkout steps. Injected problems: 0.25% flicker (other
variant logged), 0.4% duplicate hits, and a 40% loss of treatment impressions on 24 Dec. A day's
Parquet shard is written as soon as it's final, so memory stays bounded.

## 2. Shape with SQL — `sql/*.sql` via `analytics/run_sql.py`
`run_sql` swaps the BigQuery table name for a DuckDB view (with `_TABLE_SUFFIX`), transpiles with
sqlglot, fixes the one GA4 idiom sqlglot doesn't translate (`FROM UNNEST(event_params)` inside a
scalar subquery → `UNNEST(..., max_depth := 2)`), runs it, and writes `data/processed/<name>.csv`.
`tests/test_sql.py` runs all files on a small dataset and checks invariants: funnel monotonic,
DAU ≤ WAU ≤ MAU, week-0 retention = 100%, **revenue reconciles across three independent queries**,
one row per user in the experiment extract.

Worth reading closely:
- `04_funnel.sql`: per-user step flags with `MAX(IF(...))`, then `LAG` for step conversion.
- `06_cohort_retention.sql`: `DATE_TRUNC(..., WEEK(MONDAY))`, `DATE_DIFF(..., WEEK)`, `FIRST_VALUE` for cohort size.
- `07_rfm.sql`: three `NTILE(5)` windows and a `CASE` segment map.
- `08_experiment_extract.sql`: first impression via `QUALIFY ROW_NUMBER() = 1`; contamination flag
  via `COUNT(DISTINCT variant)`; conversion only counts purchases **after** first exposure.

## 3. Decide — `notebooks/ab_test.ipynb` (source `ab_test.py`)
1. Contamination: 203 users in both variants → removed.
2. SRM overall (passes) → SRM per day (fails on 24 Dec) → exclude that day's new users → passes.
3. Primary metric: z-test, chi-square, absolute and relative CIs.
4. Power: pre-registered n vs achieved n, MDE.
5. Guardrails: bootstrap revenue/user; AOV.
6. Novelty: daily conversion of active exposed users from the star table → weekly lifts with CIs.
7. Segments + Simpson's check.
8. Peeking simulation.
9. Decision + appendix grading the estimates against the simulator's ground truth.

## 4. Present — `analytics/build_model.py`, `build_dashboard.py`, `powerbi/`, `REPORT.md`
The star schema feeds both the Plotly dashboard and the Power BI kit. The memo converts the
statistics into money (~$31k per 4 weeks) and actions.
