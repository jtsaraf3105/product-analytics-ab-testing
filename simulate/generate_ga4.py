"""Seeded simulator that writes a GA4-BigQuery-export-shaped e-commerce dataset.

Why a simulator? The real `bigquery-public-data.ga4_obfuscated_sample_ecommerce` dataset needs a
GCP project to query. This produces the *same schema* (sharded `events_YYYYMMDD` tables, nested
`event_params`, `device`, `geo`, `traffic_source`, `ecommerce`, `items`) over the *same period*
(2020-11-01 .. 2021-01-31), so every SQL file in `sql/` runs unchanged on either source.

Because it's simulated, the "truth" is known and documented in `GROUND_TRUTH` below. The analysis
never reads these constants — it must *recover* them from the events, which is a good test of the
methods. Parameters were fixed before any analysis was run (the experiment was sized with a power
analysis, see docs/DECISIONS.md), and the seed was never changed to get a nicer result.

    python -m simulate.generate_ga4 --out data/raw/ga4 --users-per-day 5000 --seed 42
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

START, END = date(2020, 11, 1), date(2021, 1, 31)
EXP_START, EXP_END = date(2020, 12, 1), date(2020, 12, 28)  # inclusive
LOGGING_INCIDENT_DAY = date(2020, 12, 24)  # treatment impressions partly dropped (SRM trap)

GROUND_TRUTH = {
    "experiment": {
        "id": "one_page_checkout_v1",
        "window": [str(EXP_START), str(EXP_END)],
        "unit": "user (hash of user_pseudo_id), 50/50",
        "treatment": "one-page checkout: boosts add_payment_info and purchase step conversion",
        "per_step_relative_lift": {"mobile": 0.07, "desktop": 0.025, "tablet": 0.04},
        "novelty": "effect x1.8 in week 1, x1.35 week 2, x1.0 from week 3",
        "logging_incident": f"{LOGGING_INCIDENT_DAY}: 40% of treatment impressions not logged",
        "flicker_bug": "0.25% of users logged in both variants",
        "duplicate_impressions": "0.4% of impressions duplicated",
    },
    "behaviour": {
        "mobile_checkout_penalty": "shipping 0.78 vs 0.86, payment 0.74 vs 0.86, purchase 0.71 vs 0.81",
        "email_add_to_cart_multiplier": 1.6,
        "holiday_cohort_return_multiplier": 0.65,
    },
}

DEVICES = np.array(["desktop", "mobile", "tablet"])
DEVICE_P = [0.56, 0.41, 0.03]
OS = {
    "desktop": ["Windows", "Macintosh", "Linux", "Chrome OS"],
    "mobile": ["iOS", "Android"],
    "tablet": ["iOS", "Android"],
}
BROWSERS = ["Chrome", "Safari", "Edge", "Firefox"]
COUNTRIES = np.array(
    [
        "United States",
        "India",
        "Canada",
        "United Kingdom",
        "Germany",
        "France",
        "Japan",
        "Spain",
        "Taiwan",
        "Australia",
        "Brazil",
        "Singapore",
    ]
)
COUNTRY_P = np.array([0.44, 0.09, 0.07, 0.06, 0.05, 0.04, 0.04, 0.035, 0.03, 0.03, 0.03, 0.025])
COUNTRY_P = COUNTRY_P / COUNTRY_P.sum()
# (medium, source, name, share, add_to_cart multiplier, return multiplier)
CHANNELS = [
    ("organic", "google", "(organic)", 0.37, 1.00, 1.00),
    ("(none)", "(direct)", "(direct)", 0.24, 1.05, 1.15),
    ("referral", "shop.googlemerchandisestore.com", "(referral)", 0.19, 0.90, 0.95),
    ("cpc", "google", "Holiday Promo", 0.13, 1.10, 0.80),
    ("email", "newsletter", "Winter Sale", 0.07, 1.60, 1.45),
]
CATEGORIES = {
    "Apparel": (18, 65),
    "Bags": (25, 90),
    "Drinkware": (8, 28),
    "Office": (3, 20),
    "Lifestyle": (6, 40),
    "Electronics": (15, 120),
    "Stationery": (2, 12),
}
PAGES = [
    "Home",
    "Apparel | Google Merchandise Store",
    "Bags | Google Merchandise Store",
    "Drinkware | Google Merchandise Store",
    "Sale | Google Merchandise Store",
    "Shopping Cart",
    "Checkout Your Information",
    "Payment Method",
    "Checkout Confirmation",
]


@dataclass
class Item:
    item_id: str
    item_name: str
    item_category: str
    price: float


def make_catalog(rng: np.random.Generator, n: int = 220) -> list[Item]:
    cats = list(CATEGORIES)
    items = []
    for i in range(n):
        cat = cats[i % len(cats)]
        lo, hi = CATEGORIES[cat]
        price = float(np.round(rng.uniform(lo, hi), 2))
        items.append(Item(f"GGOE{i:05d}", f"Google {cat} Item {i:03d}", cat, price))
    return items


def daily_new_users(d: date, base: float) -> float:
    """Weekly seasonality + holiday peak (Black Friday / Cyber Monday / pre-Christmas)."""
    weekly = [1.08, 1.06, 1.04, 1.0, 0.95, 0.88, 0.92][d.weekday()]
    t = (d - START).days
    holiday = 1.0
    bf = (d - date(2020, 11, 27)).days
    if -3 <= bf <= 3:  # Black Friday .. Cyber Monday
        holiday += 0.9 * np.exp(-abs(bf) / 2)
    if date(2020, 12, 1) <= d <= date(2020, 12, 20):
        holiday += 0.35
    if date(2020, 12, 24) <= d <= date(2021, 1, 1):
        holiday -= 0.30
    trend = 1.0 + 0.002 * t
    return base * weekly * holiday * trend


def variant_of(user_id: str) -> str:
    h = int(hashlib.md5(f"one_page_checkout_v1:{user_id}".encode()).hexdigest(), 16)
    return "treatment" if h % 2 else "control"


def novelty_multiplier(d: date) -> float:
    week = (d - EXP_START).days // 7
    return {0: 1.8, 1: 1.35}.get(week, 1.0)


def ev_param(key: str, value: str | int | float) -> dict:
    v: dict = {"string_value": None, "int_value": None, "float_value": None, "double_value": None}
    if isinstance(value, str):
        v["string_value"] = value
    elif isinstance(value, int):
        v["int_value"] = value
    else:
        v["double_value"] = float(value)
    return {"key": key, "value": v}


class Simulator:
    def __init__(self, seed: int, users_per_day: float) -> None:
        self.rng = np.random.default_rng(seed)
        self.base = users_per_day
        self.catalog = make_catalog(self.rng)
        self.events: dict[date, list[dict]] = {}
        self.tx = 0
        self.exposed: dict[str, date] = {}

    # ------------------------------------------------------------------ users + sessions

    def run(self, out: Path) -> int:
        """Simulate arrival day by arrival day. Users only *return* on later days, so once
        arrival day D is simulated, day D's events are complete: write that shard and free it.
        Memory stays bounded by the not-yet-final future days instead of the whole dataset."""
        rng = self.rng
        out.mkdir(parents=True, exist_ok=True)
        uid_counter, written = 0, 0
        d = START
        while d <= END:
            n = rng.poisson(daily_new_users(d, self.base))
            for _ in range(n):
                uid_counter += 1
                self._simulate_user(uid_counter, d)
            written += write_day(self.events.pop(d, []), d, out)
            d += timedelta(days=1)
        return written

    def _simulate_user(self, k: int, first_day: date) -> None:
        rng = self.rng
        user_id = f"{rng.integers(10**8, 10**9)}.{k:07d}"
        device = str(rng.choice(DEVICES, p=DEVICE_P))
        country = str(rng.choice(COUNTRIES, p=COUNTRY_P))
        ch = CHANNELS[int(rng.choice(len(CHANNELS), p=[c[3] for c in CHANNELS]))]
        profile = {
            "user_id": user_id,
            "device": device,
            "os": str(rng.choice(OS[device])),
            "browser": str(rng.choice(BROWSERS, p=[0.62, 0.22, 0.09, 0.07])),
            "country": country,
            "channel": ch,
            "first_touch_us": None,
        }
        holiday_cohort = date(2020, 11, 25) <= first_day <= date(2020, 12, 20)
        p_return = {"desktop": 0.42, "mobile": 0.30, "tablet": 0.35}[device] * ch[5]
        if holiday_cohort:
            p_return *= GROUND_TRUTH["behaviour"]["holiday_cohort_return_multiplier"]
        days = [first_day]
        cur = first_day
        while rng.random() < min(p_return, 0.85):
            cur = cur + timedelta(days=int(rng.exponential(9)) + 1)
            if cur > END:
                break
            days.append(cur)
            p_return *= 0.8  # each further return is less likely
        for i, day in enumerate(days):
            self._simulate_session(profile, day, returning=i > 0)

    def _simulate_session(self, u: dict, day: date, returning: bool) -> None:
        rows: list[dict] = []
        try:
            self._session_events(u, day, returning, rows)
        finally:  # sessions end early (bounce, abandoned cart) — flush whatever happened
            for r in rows:
                self.events.setdefault(r["_day"], []).append(r)

    def _session_events(self, u: dict, day: date, returning: bool, rows: list[dict]) -> None:
        rng = self.rng
        start = datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(
            seconds=float(rng.uniform(0, 86_000))
        )
        ts = [start]

        def tick() -> datetime:
            ts[0] = ts[0] + timedelta(seconds=float(rng.exponential(35)) + 2)
            return ts[0]

        sid = int(start.timestamp())
        if u["first_touch_us"] is None:
            u["first_touch_us"] = int(start.timestamp() * 1e6)

        def emit(
            name: str,
            when: datetime,
            page: str,
            extra: list[dict] | None = None,
            ecommerce: dict | None = None,
            items: list[dict] | None = None,
        ) -> None:
            params = [
                ev_param("ga_session_id", sid),
                ev_param("page_title", page),
                ev_param("engagement_time_msec", int(rng.integers(500, 60_000))),
            ]
            rows.append(self._row(u, name, when, params + (extra or []), ecommerce, items))

        if not returning:
            emit("first_visit", start, "Home")
        emit("session_start", start, "Home")
        emit("page_view", start, "Home")

        # Experiment exposure: every active user in the window, logged once per session.
        in_exp = EXP_START <= day <= EXP_END
        variant = variant_of(u["user_id"]) if in_exp else None
        if in_exp and variant is not None:
            logged = not (
                variant == "treatment" and day == LOGGING_INCIDENT_DAY and rng.random() < 0.40
            )
            if logged:
                shown = variant
                if rng.random() < 0.0025:  # flicker bug: the other variant logged
                    shown = "control" if variant == "treatment" else "treatment"
                exp = [
                    ev_param("experiment_id", "one_page_checkout_v1"),
                    ev_param("variant", shown),
                ]
                emit("experiment_impression", start, "Home", exp)
                if rng.random() < 0.004:
                    emit("experiment_impression", start, "Home", exp)  # duplicate hit
                self.exposed.setdefault(u["user_id"], day)

        for _ in range(int(rng.integers(0, 4))):
            emit("page_view", tick(), str(rng.choice(PAGES[1:5])))
        if rng.random() > 0.40:
            return  # bounced before viewing a product
        basket = [
            self.catalog[int(i)]
            for i in rng.choice(len(self.catalog), size=int(rng.integers(1, 5)), replace=False)
        ]
        for it in basket:
            emit("view_item", tick(), it.item_name, items=[self._item(it, 1)])
        p_cart = 0.07 * u["channel"][4] * (1.25 if returning else 1.0)
        in_cart = [it for it in basket if rng.random() < p_cart]
        if not in_cart:
            return
        for it in in_cart:
            emit("add_to_cart", tick(), "Shopping Cart", items=[self._item(it, 1)])
        if rng.random() > 0.55:
            return
        qty = {it.item_id: int(rng.integers(1, 3)) for it in in_cart}
        items = [self._item(it, qty[it.item_id]) for it in in_cart]
        emit("begin_checkout", tick(), "Checkout Your Information", items=items)
        mob = u["device"] == "mobile"
        p_ship = 0.78 if mob else 0.86
        p_pay = 0.74 if mob else 0.86
        p_buy = 0.71 if mob else 0.81
        if variant == "treatment":
            lift = GROUND_TRUTH["experiment"]["per_step_relative_lift"][u["device"]]
            lift *= novelty_multiplier(day)
            p_pay = min(0.99, p_pay * (1 + lift))
            p_buy = min(0.99, p_buy * (1 + lift))
        if rng.random() > p_ship:
            return
        emit("add_shipping_info", tick(), "Checkout Your Information", items=items)
        if rng.random() > p_pay:
            return
        emit("add_payment_info", tick(), "Payment Method", items=items)
        if rng.random() > p_buy:
            return
        self.tx += 1
        revenue = float(round(sum(i["item_revenue_in_usd"] for i in items), 2))
        emit(
            "purchase",
            tick(),
            "Checkout Confirmation",
            extra=[ev_param("transaction_id", f"T{self.tx:07d}")],
            ecommerce={
                "total_item_quantity": sum(i["quantity"] for i in items),
                "purchase_revenue_in_usd": revenue,
                "purchase_revenue": revenue,
                "unique_items": len(items),
                "transaction_id": f"T{self.tx:07d}",
            },
            items=items,
        )

    def _item(self, it: Item, qty: int) -> dict:
        return {
            "item_id": it.item_id,
            "item_name": it.item_name,
            "item_category": it.item_category,
            "price_in_usd": it.price,
            "price": it.price,
            "quantity": qty,
            "item_revenue_in_usd": round(it.price * qty, 2),
            "item_revenue": round(it.price * qty, 2),
        }

    def _row(
        self,
        u: dict,
        name: str,
        when: datetime,
        params: list[dict],
        ecommerce: dict | None,
        items: list[dict] | None,
    ) -> dict:
        medium, source, cname = u["channel"][:3]
        return {
            "_day": when.date(),
            "event_date": when.strftime("%Y%m%d"),
            "event_timestamp": int(when.timestamp() * 1e6),
            "event_name": name,
            "event_params": params,
            "user_pseudo_id": u["user_id"],
            "user_first_touch_timestamp": u["first_touch_us"],
            "device": {
                "category": u["device"],
                "operating_system": u["os"],
                "web_info": {"browser": u["browser"]},
            },
            "geo": {"country": u["country"]},
            "traffic_source": {"medium": medium, "source": source, "name": cname},
            "ecommerce": ecommerce,
            "items": items or [],
        }


PARAM_VALUE = pa.struct(
    [
        ("string_value", pa.string()),
        ("int_value", pa.int64()),
        ("float_value", pa.float64()),
        ("double_value", pa.float64()),
    ]
)
ITEM = pa.struct(
    [
        ("item_id", pa.string()),
        ("item_name", pa.string()),
        ("item_category", pa.string()),
        ("price_in_usd", pa.float64()),
        ("price", pa.float64()),
        ("quantity", pa.int64()),
        ("item_revenue_in_usd", pa.float64()),
        ("item_revenue", pa.float64()),
    ]
)
SCHEMA = pa.schema(
    [
        ("event_date", pa.string()),
        ("event_timestamp", pa.int64()),
        ("event_name", pa.string()),
        ("event_params", pa.list_(pa.struct([("key", pa.string()), ("value", PARAM_VALUE)]))),
        ("user_pseudo_id", pa.string()),
        ("user_first_touch_timestamp", pa.int64()),
        (
            "device",
            pa.struct(
                [
                    ("category", pa.string()),
                    ("operating_system", pa.string()),
                    ("web_info", pa.struct([("browser", pa.string())])),
                ]
            ),
        ),
        ("geo", pa.struct([("country", pa.string())])),
        (
            "traffic_source",
            pa.struct([("medium", pa.string()), ("source", pa.string()), ("name", pa.string())]),
        ),
        (
            "ecommerce",
            pa.struct(
                [
                    ("total_item_quantity", pa.int64()),
                    ("purchase_revenue_in_usd", pa.float64()),
                    ("purchase_revenue", pa.float64()),
                    ("unique_items", pa.int64()),
                    ("transaction_id", pa.string()),
                ]
            ),
        ),
        ("items", pa.list_(ITEM)),
    ]
)


def write_day(rows: list[dict], d: date, out: Path) -> int:
    rows.sort(key=lambda r: r["event_timestamp"])
    for r in rows:
        r.pop("_day", None)
    pq.write_table(
        pa.Table.from_pylist(rows, schema=SCHEMA),
        out / f"events_{d:%Y%m%d}.parquet",
        compression="zstd",
    )
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw/ga4")
    ap.add_argument("--users-per-day", type=float, default=5000)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    sim = Simulator(a.seed, a.users_per_day)
    n = sim.run(Path(a.out))
    (Path(a.out) / "GROUND_TRUTH.json").write_text(json.dumps(GROUND_TRUTH, indent=2))
    days = (END - START).days + 1
    print(f"wrote {n:,} events over {days} daily tables to {a.out}")


if __name__ == "__main__":
    main()
