# Decisions

**D1. Simulated GA4 export instead of querying BigQuery.** The public dataset needs a GCP project
(free tier is enough, but not available in this build environment). The simulator reproduces the
schema, period and scale, and makes ground truth known, so the methods can be *graded*. The SQL
stays BigQuery-native, so switching to the real data is a copy-paste. **Resume implication:** say
"GA4-schema e-commerce events (BigQuery SQL)", and only claim the real dataset once you've run the
queries there.

**D2. Experiment simulated on GA4 users (not the Kaggle landing-page dataset).** Allowed by the
PRD. It lets the experiment interact with the funnel (it changes checkout steps, not a landing
page), and includes realistic failure modes: contamination, duplicate hits, a logging outage.

**D3. BigQuery SQL + sqlglot → DuckDB.** One source of truth for queries. Two constructs needed
changes. `ARRAY_AGG(... ORDER BY ... LIMIT 1)[OFFSET(0)]` was replaced by the portable
`QUALIFY ROW_NUMBER() = 1`, and `QUALIFY ... ORDER BY revenue` was made explicit because DuckDB
bound the raw column instead of the alias. One post-transpile rewrite handles scalar
`UNNEST(event_params)` subqueries.

**D4. Behavioural calibration before any experiment analysis.** The first simulator draft gave 12.6%
user conversion (a real store is ~1.5–3%). The funnel baselines were calibrated to 3.0% before any
experiment result was looked at. Calibration used only aggregate funnel rates and the control arm's
baseline.

**D5. Experiment sized a priori.** With the control baseline at ~2.6%, detecting an 8% relative lift
with 80% power at α = 0.05 needs ~98k users per arm. 5,000 new users/day over a 4-week window gives
~100k per arm, so that traffic level was fixed before generating the final dataset. The seed (42)
was never changed.

**D6. Primary metric = user-level conversion after first exposure (intent-to-treat).** All exposed
users count, including those who never reach checkout. That dilutes the effect but is unbiased, and
matches what a rollout would actually deliver. A checkout-only metric would be larger, but it's
conditioned on post-treatment behaviour.

**D7. Excluding the incident day rather than "fixing" it.** Missing treatment impressions can't be
recovered from the logs, and keeping the day compares all control users with a *surviving subset*
of treatment users. Excluding new exposures that day costs 1.7% of users and removes the bias. The
alternative, re-deriving assignment from the hash, would work here, but in real systems the logs
are often the only record.

**D8. Bootstrap for revenue per user.** Most users have zero revenue and a few have large baskets,
so the distribution is far from normal. A percentile bootstrap (2,000 resamples) avoids the
normality assumption.

**D9. Honest novelty conclusion.** The simulator does plant a novelty decay, but the weekly lift
estimates (±12 pts) can't resolve it. The notebook says so, and the memo recommends a holdout
instead of claiming the effect is stable.

**D10. Plotly dashboard + Power BI kit.** Power BI Desktop is Windows-only and this environment is
macOS. Rather than hand-write an unverifiable `.pbix`/TMDL, the repo ships the model CSVs, every DAX
measure, a page-by-page build guide, and a working HTML version of the same pages.

**D11. matplotlib in the notebook, Plotly in the dashboard.** GitHub renders static notebook images
but not Plotly's JavaScript. The dashboard is a standalone HTML file where interactivity works.
