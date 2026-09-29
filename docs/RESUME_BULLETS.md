# Resume bullets (every number is from this repo)

**Product Analytics & A/B Testing**: SQL (BigQuery, window functions, CTEs), Python (pandas, SciPy,
statsmodels), DuckDB, Plotly, Power BI (DAX) · [github link]

- Analysed 4.3M GA4-schema e-commerce events (534k users) with BigQuery SQL: KPIs (DAU/WAU/MAU,
  conversion, AOV), funnel drop-off by device and channel, weekly cohort retention and RFM (NTILE).
  Found **mobile checkout completion at 43% vs 61% on desktop**, and holiday-season cohorts retaining
  **~35% worse** in week 1.
- Evaluated a one-page-checkout A/B test (198k users): contamination and duplicate checks, and a
  **per-day sample-ratio check that caught a logging outage** the aggregate check missed. Chi-square
  and two-proportion z-tests with 95% CIs showed a **+14.0% conversion lift (CI +8–20%)** and
  +$0.16 revenue per user, with power analysis and a peeking simulation (26% false-positive rate).
- Built a star-schema model with DAX measures (conversion, retention, MoM growth, experiment lift)
  and a 4-page dashboard, and wrote a stakeholder memo recommending rollout with a 5% holdout,
  worth an estimated **~$31k per 4 weeks**.

**Before using these:** the events are simulated at GA4 scale (see README). Keep "GA4-schema" in the
wording, or run the SQL on the real public dataset first. Claim **Power BI** only after you build the
`.pbix` from `powerbi/MODEL.md` (about 1 hour).
