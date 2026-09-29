# Concepts & Vocabulary

**Event / user / session.** An event is one action (page_view, add_to_cart, purchase). A user is
identified by `user_pseudo_id` (a device/browser cookie, not a person). A session is a visit, keyed
by `ga_session_id` inside `event_params`.

**`UNNEST(event_params)`.** GA4 stores parameters as a list of key/value structs. `UNNEST` turns
the list into rows so you can `WHERE key = '...'`. *Analogy:* opening a folder to read one form.

**Sharded tables / `_TABLE_SUFFIX`.** One table per day (`events_20201203`). Querying
`events_*` with a `_TABLE_SUFFIX BETWEEN …` filter scans only those days, which controls BigQuery cost.

**CTE.** A named sub-query (`WITH x AS (...)`). Makes long analyses read top-down.

**Window function.** A calculation across related rows without collapsing them, e.g.
`LAG(users) OVER (ORDER BY step)` for the previous funnel step. **QUALIFY** filters on a window
result (like `HAVING` for windows).

**DAU / WAU / MAU / stickiness.** Distinct users in 1 / 7 / 28 days; DAU/MAU is how often monthly
users come back.

**Conversion rate.** Purchases ÷ a denominator: sessions (session CR) or users (user CR). **AOV** =
revenue ÷ orders.

**Funnel, step conversion, drop-off.** Users reaching each step in order; step conversion = step ÷
previous; drop-off = 1 − step conversion.

**Cohort / retention.** A cohort is users who first visited in the same week. Retention(week N) is
the share of the cohort active N weeks later. *Analogy:* following one school class, year by year.

**RFM.** Recency (days since last order), Frequency (orders), Monetary (revenue). NTILE(5) turns
each into a 1–5 score. Combinations become segments like Champions or At risk.

**Randomised controlled experiment (A/B test).** Random assignment makes the groups comparable, so
outcome differences are caused by the treatment (plus noise).

**Unit of randomisation / analysis.** Here: user (hashed id). Analyse at the same unit you
randomise, or the standard errors are wrong.

**Primary / guardrail metric.** Primary decides the test (conversion). Guardrails must not get
worse (revenue per user, AOV).

**p-value.** If the change had no effect, the probability of seeing a difference at least this
large. It's *not* the probability that the change works.

**Confidence interval.** A range of effect sizes compatible with the data. Report it, not just p.

**Absolute vs relative lift.** +0.35 percentage points vs +14%. Say which one.

**Two-proportion z-test / chi-square.** Tests whether two conversion rates differ; on a 2×2 table
they're the same test (χ² = z²).

**Power / MDE.** Power = chance of detecting a real effect of a given size. MDE = the smallest
effect the test can reliably detect. Decide both *before* the test.

**SRM (sample ratio mismatch).** Arms not in the designed ratio → broken assignment or logging →
don't trust results until explained. Check overall **and** by day/segment.

**Contamination.** Users exposed to both variants. Remove them from both arms.

**Peeking.** Checking repeatedly and stopping on the first significant result inflates false
positives (26% instead of 5% with 20 looks, in the notebook).

**Novelty effect.** Early lift from curiosity that fades. Measured with time-sliced lifts or a
long-running **holdout**.

**Simpson's paradox.** A pooled effect can reverse within every segment if segment mix differs
between groups. Check that randomisation balanced the mix.

**Bootstrap.** Resample the data many times to get a CI without distribution assumptions. Good
for revenue per user.

**Star schema.** Fact tables (events, orders) surrounded by dimension tables (date, user, device),
joined one-to-many. The recommended Power BI model.

**DAX measure / filter context / CALCULATE.** A measure is a formula evaluated in the current
filter context (slicers, rows). `CALCULATE` changes that context, e.g. "same measure, last month".
