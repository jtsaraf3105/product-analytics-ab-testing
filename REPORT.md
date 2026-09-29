# Memo: One-page checkout test result and three growth opportunities

**To:** Head of E-commerce, Product & Marketing leads · **From:** Product Analytics · **Period analysed:** 1 Nov 2020 – 31 Jan 2021 (534k users, 16,000 orders, $842k revenue)

> Data note: GA4-schema e-commerce export, simulated at the scale of Google's public GA4 sample
> (see README). All SQL runs unchanged on the real BigQuery dataset.

## 1. Question
Should we roll out the new **one-page checkout** tested from 1–28 Dec 2020? Where else is revenue
leaking?

## 2. Method
- **Randomised A/B test**, 50/50 by user, 198k users analysed. Primary metric: share of users who
  purchase after first exposure. Guardrail: revenue per user. Pre-registered sizing: 98k users/arm to
  detect an 8% relative lift with 80% power; the test reached 99k/arm.
- **Data-quality gates before reading results:** removed 203 users logged in both variants
  (0.1%); a daily sample-ratio check found a **logging outage on 24 Dec** (treatment share 38%
  vs 50%, p ≈ 10⁻⁴⁰) that the overall check missed, so users first exposed that day were excluded
  (1.7% of users).
- Two-proportion z-test and chi-square (identical here), 95% CIs, bootstrap for revenue.
  Funnel, weekly cohort and RFM analyses in SQL.

## 3. Results
**Checkout test: ship it.**

| | Control | One-page checkout | Difference (95% CI) |
|---|---:|---:|---:|
| Purchase conversion | 2.53% | 2.89% | **+14.0%** relative (+8.1% to +20.2%), p = 1.2×10⁻⁶ |
| Revenue per exposed user | $1.335 | $1.495 | +$0.16 (+$0.06 to +$0.26) |
| Average order value | $52.77 | $51.81 | ≈ unchanged — the gain is more buyers, not smaller baskets |

On December's traffic that is **≈ $31k extra revenue per 4 weeks (CI $12k–$51k)**. The lift is
significant on both desktop (+13%) and mobile (+17%); tablet is too small to read.

**Three further insights**
1. **Mobile checkout is the biggest leak.** Only **43%** of mobile users who begin checkout
   complete it, vs **61%** on desktop — an 18-point gap, spread over the shipping (78% vs 87%),
   payment (76% vs 87%) and final-purchase (72% vs 82%) steps. Mobile is 41% of users but 30% of
   revenue.
2. **Email is our most valuable channel and under-used.** Email brings 7% of users but **13% of
   revenue**; its users convert at **5.1%** vs 2.9% for organic search and earn $2.87 per user vs
   $1.51.
3. **Holiday-sale cohorts don't stick.** Users acquired 23 Nov – 20 Dec came back in week 1 at
   **10–12%**, vs **~16.5%** for cohorts acquired outside the season — about 35% lower, and the gap
   persists to week 4. Aggregate retention hides this because holiday volume is so large.
   Separately, the top RFM segment ("Champions") is **16% of purchasers and 30% of revenue**.

## 4. Recommendation
1. **Roll out the one-page checkout to 100%**, keeping a **5% holdout for 4 weeks**: weekly
   estimates were too noisy (±12 pts) to rule out a novelty effect, so the holdout measures the
   steady-state lift before it goes into forecasts.
2. **Next test: mobile checkout** — wallet payments and address autofill, where the remaining
   18-point gap sits. Halving the gap would add roughly 1,000 purchasers per quarter at current
   traffic.
3. **Grow email capture** (e.g. an incentive at first visit) and target holiday-acquired users with a
   January re-engagement series rather than more paid acquisition.
4. **Add a daily SRM alert** to the experiment pipeline: the 24-Dec outage was invisible in the
   overall check.

## 5. Risks and caveats
- **Novelty:** the long-run lift may be smaller than +14%; the holdout addresses this.
- **Seasonality:** the test ran in December (gift buyers, high intent). Re-check the effect on the
  holdout in January.
- **Multiple comparisons:** device results are exploratory; the decision rests on the pre-registered
  primary metric only.
- **Attribution:** channel values are last-touch (GA4 `traffic_source`); email's value partly
  reflects already-engaged users, so treat channel ROI as directional.
