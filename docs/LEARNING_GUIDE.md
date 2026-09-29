# Interview Guide — model answers

## 0. The 60-second story
> "I analysed three months of GA4-format e-commerce events, about 530k users and 4.3M events, with
> BigQuery SQL. From the funnel, mobile users complete checkout at 43% vs 61% on desktop. We ran
> an A/B test of a one-page checkout. The overall sample-ratio check passed, but I checked it per
> day and found a logging outage on one day that would have biased the result, so I excluded it.
> The test showed a 14% relative lift in purchase conversion, with a CI from 8 to 20%, and revenue
> per user went up too. I recommended shipping with a 5% holdout, because the weekly data was too
> noisy to rule out a novelty effect, and flagged mobile checkout as the next test."

## 1. How did you choose the primary and guardrail metrics?
Primary = the business outcome the change targets and can move within the test window: user-level
purchase conversion after exposure. Guardrails = things that must not get worse: revenue per user
(catches "more but smaller orders") and AOV. I pre-registered the decision rule so the result
couldn't steer the metric choice.

## 2. p-value vs practical significance
p = 1.2×10⁻⁶ says the difference is very unlikely to be noise. Practical significance is the
*size*: +0.35 pp, +14% relative, about $31k per 4 weeks, with a CI whose low end (+8%) still
justifies the engineering cost. With a huge sample, a trivial effect can be "significant". With a
small one, a valuable effect can be non-significant. Always read the CI.

## 3. Sample ratio mismatch
SRM means the arms' sizes don't match the design, so assignment or logging is broken and the
groups may not be comparable. Test it with a chi-square goodness-of-fit, using a strict threshold
(p < 0.001) because it's an alarm, not a finding. **My case:** overall p = 0.32 (fine), but a
per-day check showed 38% treatment on 24 Dec (p ≈ 10⁻⁴⁰), a logging outage. A problem that's big
on one day is diluted in the total, so check SRM by day and by segment.

## 4. The peeking problem
If you look at the p-value every day and stop at the first p < 0.05, the false-positive rate climbs.
My A/A simulation with 20 looks gave 26% instead of 5%. Fixes: fix the sample size up front, or use
a sequential design (alpha spending, mSPRT, always-valid p-values).

## 5. Why cohort retention beats aggregate retention
Aggregate retention mixes users of different ages and acquisition sources. A burst of new users
(the holiday season) drags it down even if nothing changed for existing users. Cohorts separate
"who we acquired" from "how long they stay". Here holiday cohorts retain about 35% worse in week 1,
which points to deal-seekers, not a product problem.

## 6. Simpson's paradox by segment
A treatment can look better overall and worse in every segment (or vice versa) when the segment mix
differs between groups. Randomisation should balance the mix. I checked that treatment share was
about 50% in every device, and that the lift had the same sign in each, so the pooled estimate
stands. Segment results are exploratory: many segments means many comparisons.

## 7. Rapid-fire
| Q | A |
|---|---|
| Chi-square vs z-test? | Same test on a 2×2 (χ² = z²); z gives a signed effect and a CI. |
| Pooled vs unpooled SE? | Pooled under H0 for the test statistic; unpooled for the CI. |
| Why a bootstrap for revenue? | Zero-inflated and skewed, so normality is doubtful. |
| What if SRM is detected? | Stop, find the cause, fix or exclude with a justification, re-check. Never just proceed. |
| Novelty effect? | Time-sliced lifts; long-running holdout; compare new vs returning users. |
| How to reduce the required sample? | CUPED (pre-period covariate), higher-sensitivity metrics, one-sided test if justified. |
| Unit of analysis? | Same as the unit of randomisation (user), otherwise SEs are too small. |
| Multiple testing? | Pre-register one primary; treat segments as exploratory or apply Holm/BH. |

## 8. Honest limitations
Simulated data (with known truth, which is also a strength). The Power BI file must be built from the
guide. December is a special month, so the holdout matters. Channel attribution is last-touch.
