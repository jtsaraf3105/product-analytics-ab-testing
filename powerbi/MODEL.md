# Power BI report — model and build guide

The `.pbix` file has to be authored in **Power BI Desktop (Windows)**. Everything it needs is in
this folder: the star-schema CSVs (`powerbi/data/`, produced by `make model`), every DAX measure
(`measures.dax`), and the theme (`theme.json`). Building it takes about an hour following the
steps below. Once it's built, save it as `powerbi/product_analytics.pbix`, export the PDF
(File › Export › PDF) to `powerbi/product_analytics.pdf`, and replace the screenshots in `docs/img/`.
Until then, `dashboard/index.html` is a Plotly build of the **same four pages** (screenshots in
the README).

## 1. Load data
Get Data › Text/CSV, load all files in `powerbi/data/`:

| Table | Grain | Key columns |
|---|---|---|
| `fact_user_day` | user × active day | `day`, `user_pseudo_id`, `device`, `channel`, `country`, `sessions`, `viewed_item`, `added_to_cart`, `began_checkout`, `orders`, `revenue` |
| `fact_experiment` | exposed user | `user_pseudo_id`, `variant`, `n_variants`, `first_exposure_day`, `device`, `converted`, `revenue` |
| `dim_date` | day | `date`, `week_start`, `month`, `weekday`, `is_weekend`, `is_holiday_season` |
| `dim_user` | user | `user_pseudo_id`, `first_visit_date`, `cohort_week`, `first_device`, `first_channel`, `country` |
| `dim_device`, `dim_channel`, `dim_country` | member | `device` / `channel` / `country` |

In Power Query set types: dates as Date, `revenue` as Fixed decimal, flags as Whole number.

## 2. Relationships (Model view) — star schema, single direction, many-to-one
- `dim_date[date]` 1 ─► * `fact_user_day[day]`  (mark `dim_date` as the date table)
- `dim_user[user_pseudo_id]` 1 ─► * `fact_user_day[user_pseudo_id]`
- `dim_user[user_pseudo_id]` 1 ─► * `fact_experiment[user_pseudo_id]`
- `dim_device[device]`, `dim_channel[channel]`, `dim_country[country]` 1 ─► * `fact_user_day`

Add calculated column on `fact_user_day`:
`Week N = DATEDIFF ( RELATED ( dim_user[cohort_week] ), fact_user_day[day], WEEK )`

## 3. Measures
Create a `_Measures` table (Enter data › empty) and add every measure from `measures.dax`.
Format: `%` measures as percentage (1–2 dp), `Revenue`/`AOV` as currency.

## 4. Pages (apply `theme.json` via View › Themes › Browse)

**Page 1 — Executive KPIs.** Cards: Revenue, Revenue MoM %, Orders, AOV, DAU, Stickiness DAU/MAU,
User Conversion %. Line chart: Revenue by `dim_date[date]`. Line chart: DAU / WAU / MAU by date.
Bar: Revenue and User Conversion % by `dim_channel[channel]`. Slicers: date range, device, channel.

**Page 2 — Funnel.** Funnel visual with Funnel Viewed / Carted / Checkout / Purchased.
Clustered bar: Checkout Completion % and Checkout Drop-off % by device. Matrix: channel × funnel
rates. Slicers: date, device, channel.

**Page 3 — Cohort retention.** Matrix: rows `dim_user[cohort_week]`, columns `fact_user_day[Week N]`
(filter 1–8), values `Retention %` with background colour scale (white → dark blue). Card: average
week-1 retention. Slicer: first channel.

**Page 4 — Experiment.** Cards: Exp Conv Control, Exp Conv Treatment, Exp Relative Lift %, Exp Z.
Line: Exp Treatment Share by `first_exposure_day` with a 50 % constant line (SRM monitor).
Clustered column: Exp Conversion % by device and variant. Text box: the decision from
`REPORT.md`. Page filter: exclude `first_exposure_day` = 2020-12-24 (see notebook §1b).
