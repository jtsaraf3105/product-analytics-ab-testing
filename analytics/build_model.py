"""Build the Power BI star schema from the SQL extracts in data/processed/.

    fact_user_day   one row per user per active day (sessions, funnel flags, orders, revenue)
    fact_experiment one row per exposed user (variant, converted, revenue, flags)
    dim_date        calendar (week, month, weekday, holiday flag)
    dim_user        first visit date, weekly cohort, first device/channel/country
    dim_device, dim_channel, dim_country

Relationships (all single-direction, one-to-many):
    dim_date[date] -> fact_user_day[day]
    dim_user[user_pseudo_id] -> fact_user_day[user_pseudo_id], fact_experiment[user_pseudo_id]
    dim_device[device] -> fact_user_day[device]      (same for channel, country)

    python -m analytics.build_model
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def build(processed: Path, out: Path) -> dict[str, int]:
    out.mkdir(parents=True, exist_ok=True)
    f = pd.read_csv(processed / "09_star_schema.csv", parse_dates=["day", "first_visit_date"])
    exp = pd.read_csv(processed / "08_experiment_extract.csv", parse_dates=["first_exposure_day"])

    dates = pd.DataFrame({"date": pd.date_range(f["day"].min(), f["day"].max(), freq="D")})
    dates["week_start"] = dates["date"] - pd.to_timedelta(dates["date"].dt.weekday, unit="D")
    dates["month"] = dates["date"].dt.strftime("%Y-%m")
    dates["weekday"] = dates["date"].dt.day_name()
    dates["is_weekend"] = dates["date"].dt.weekday >= 5
    dates["is_holiday_season"] = dates["date"].between("2020-11-25", "2020-12-31")

    first = f.sort_values("day").groupby("user_pseudo_id").first()
    users = pd.DataFrame(
        {
            "user_pseudo_id": first.index,
            "first_visit_date": first["first_visit_date"].values,
            "first_device": first["device"].values,
            "first_channel": first["channel"].values,
            "country": first["country"].values,
        }
    )
    users["cohort_week"] = users["first_visit_date"] - pd.to_timedelta(
        users["first_visit_date"].dt.weekday, unit="D"
    )

    tables = {
        "fact_user_day": f.drop(columns=["first_visit_date"]),
        "fact_experiment": exp,
        "dim_date": dates,
        "dim_user": users,
        "dim_device": pd.DataFrame({"device": sorted(f["device"].dropna().unique())}),
        "dim_channel": pd.DataFrame({"channel": sorted(f["channel"].dropna().unique())}),
        "dim_country": pd.DataFrame({"country": sorted(f["country"].dropna().unique())}),
    }
    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False)
    return {k: len(v) for k, v in tables.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--processed", default="data/processed")
    ap.add_argument("--out", default="powerbi/data")
    a = ap.parse_args()
    for name, n in build(Path(a.processed), Path(a.out)).items():
        print(f"{name:16s} {n:>9,} rows")


if __name__ == "__main__":
    main()
