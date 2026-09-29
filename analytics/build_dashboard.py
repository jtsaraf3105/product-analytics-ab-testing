"""Build dashboard/index.html — a self-contained, 4-page interactive dashboard (Plotly) with the
same pages and measures as the Power BI report specified in powerbi/ (Executive KPIs, Funnel,
Cohort retention, Experiment). Open the HTML file in any browser; no server needed.

    python -m analytics.build_dashboard
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analytics.stats import srm_test, two_proportion_ztest

P = Path("data/processed")
BLUE, ORANGE, GREY, GREEN = "#2563eb", "#ea580c", "#64748b", "#16a34a"


def kpi_cards(daily: pd.DataFrame, users: pd.DataFrame) -> str:
    daily["month"] = pd.to_datetime(daily.day).dt.strftime("%Y-%m")
    m = daily.groupby("month").agg(revenue=("revenue", "sum"), orders=("orders", "sum"))
    mom = m.revenue.pct_change().iloc[-1]
    cards = [
        ("Revenue", f"${daily.revenue.sum():,.0f}", f"MoM (Jan vs Dec) {mom:+.1%}"),
        (
            "Orders",
            f"{int(daily.orders.sum()):,}",
            f"AOV ${daily.revenue.sum() / daily.orders.sum():.2f}",
        ),
        (
            "Avg DAU",
            f"{users.dau.mean():,.0f}",
            f"stickiness DAU/MAU {users.stickiness_dau_mau.iloc[27:].mean():.1%}",
        ),
        (
            "Session conversion",
            f"{daily.orders.sum() / daily.sessions.sum():.2%}",
            f"user conversion {daily.purchasers.sum() / daily.users.sum():.2%} (daily avg)",
        ),
    ]
    return "".join(
        f'<div class="card"><div class="k">{k}</div><div class="v">{v}</div>'
        f'<div class="s">{s}</div></div>'
        for k, v, s in cards
    )


def page_exec(daily: pd.DataFrame, users: pd.DataFrame, seg: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Daily revenue ($)",
            "Active users: DAU / WAU / MAU",
            "Revenue by channel",
            "User conversion by device",
        ),
        vertical_spacing=0.14,
    )
    fig.add_bar(x=daily.day, y=daily.revenue, marker_color=BLUE, name="revenue", row=1, col=1)
    for col, color in (("dau", BLUE), ("wau", ORANGE), ("mau", GREY)):
        fig.add_scatter(x=users.day, y=users[col], name=col.upper(), line_color=color, row=1, col=2)
    ch = seg[seg.dimension == "channel"].sort_values("revenue")
    fig.add_bar(
        x=ch.revenue,
        y=ch.segment,
        orientation="h",
        marker_color=BLUE,
        name="channel",
        text=[f"conv {v:.1%}" for v in ch.user_conversion_rate],
        row=2,
        col=1,
    )
    dv = seg[seg.dimension == "device"]
    fig.add_bar(
        x=dv.segment,
        y=dv.user_conversion_rate,
        marker_color=ORANGE,
        name="device",
        text=[f"{v:.2%}" for v in dv.user_conversion_rate],
        row=2,
        col=2,
    )
    fig.update_yaxes(tickformat=".1%", row=2, col=2)
    fig.update_layout(height=720, showlegend=False, margin=dict(t=60, l=40, r=20, b=40))
    return fig


def page_funnel(funnel_seg: pd.DataFrame) -> go.Figure:
    steps = ["view_item", "add_to_cart", "begin_checkout", "purchase"]
    dev = funnel_seg[funnel_seg.dimension == "device"].set_index("segment")
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Funnel by device (users)", "Checkout sub-step conversion by device"),
        specs=[[{"type": "funnel"}, {"type": "bar"}]],
    )
    for d, color in (("desktop", BLUE), ("mobile", ORANGE)):
        fig.add_trace(
            go.Funnel(
                name=d,
                y=steps,
                x=[dev.loc[d, s] for s in steps],
                legendgroup=d,
                textinfo="value+percent initial",
                marker_color=color,
            ),
            1,
            1,
        )
    sub = ["shipping_rate", "payment_rate", "purchase_after_payment_rate", "checkout_completion"]
    for d, color in (("desktop", BLUE), ("mobile", ORANGE), ("tablet", GREY)):
        fig.add_bar(
            x=["shipping", "payment", "purchase|payment", "checkout completion"],
            y=[dev.loc[d, s] for s in sub],
            name=d,
            marker_color=color,
            legendgroup=d,
            showlegend=d == "tablet",
            text=[f"{dev.loc[d, s]:.0%}" for s in sub],
            row=1,
            col=2,
        )
    fig.update_yaxes(tickformat=".0%", row=1, col=2)
    fig.update_layout(height=520, barmode="group", margin=dict(t=60, l=40, r=20, b=40))
    return fig


def page_cohorts(cohorts: pd.DataFrame) -> go.Figure:
    c = cohorts[cohorts.week_n <= 8].pivot(
        index="cohort_week", columns="week_n", values="retention"
    )
    c = c.drop(columns=[0])
    fig = go.Figure(
        go.Heatmap(
            z=c.values,
            x=[f"W{w}" for w in c.columns],
            y=[str(d)[:10] for d in c.index],
            colorscale="Blues",
            zmin=0,
            zmax=float(c.max().max()),
            text=[[("" if pd.isna(v) else f"{v:.1%}") for v in row] for row in c.values],
            texttemplate="%{text}",
            hovertemplate="cohort %{y}<br>%{x}: %{z:.2%}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Weekly cohort retention (share of cohort active in week N)",
        height=560,
        yaxis_autorange="reversed",
        yaxis_type="category",
        yaxis_title="cohort (week of first visit)",
        margin=dict(t=60, l=110, r=20, b=40),
    )
    return fig


def page_experiment(exp: pd.DataFrame) -> tuple[go.Figure, str]:
    exp = exp[exp.n_variants == 1].copy()
    daily = exp.groupby(["first_exposure_day", "variant"]).size().unstack()
    daily["share"] = daily.treatment / (daily.control + daily.treatment)
    bad = [
        d
        for d, c_, t_ in zip(daily.index, daily.control, daily.treatment, strict=True)
        if srm_test(c_, t_).mismatch
    ]
    clean = exp[~exp.first_exposure_day.isin(bad)]
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            "Treatment share of new exposures (SRM monitor)",
            "Conversion by variant and device",
        ),
    )
    fig.add_scatter(
        x=daily.index,
        y=daily.share,
        mode="lines+markers",
        line_color=BLUE,
        name="treatment share",
        row=1,
        col=1,
    )
    fig.add_hline(y=0.5, line_dash="dash", line_color=GREY, row=1, col=1)
    for d in bad:
        fig.add_annotation(
            x=d,
            y=daily.loc[d, "share"],
            text="logging incident",
            row=1,
            col=1,
            font_color="crimson",
            showarrow=True,
        )
    g = clean.groupby(["device", "variant"]).converted.mean().unstack()
    for v, color in (("control", GREY), ("treatment", GREEN)):
        fig.add_bar(
            x=g.index,
            y=g[v],
            name=v,
            marker_color=color,
            text=[f"{x:.2%}" for x in g[v]],
            row=1,
            col=2,
        )
    fig.update_yaxes(tickformat=".0%", row=1, col=1)
    fig.update_yaxes(tickformat=".1%", row=1, col=2)
    fig.update_layout(height=480, barmode="group", margin=dict(t=60, l=40, r=20, b=40))
    s = clean.groupby("variant").converted.agg(["sum", "count"])
    r = two_proportion_ztest(
        int(s.loc["control", "sum"]),
        int(s.loc["control", "count"]),
        int(s.loc["treatment", "sum"]),
        int(s.loc["treatment", "count"]),
    )
    verdict = (
        f"Control {r.p_control:.2%} → treatment {r.p_treatment:.2%}: relative lift "
        f"<b>{r.rel_lift:+.1%}</b> (95% CI {r.ci_rel[0]:+.1%} to {r.ci_rel[1]:+.1%}), "
        f"p = {r.p_value:.1e}, n = {int(s['count'].sum()):,} users after excluding "
        f"{len(bad)} SRM day(s). Recommendation: <b>ship</b>, with a 5% post-launch holdout."
    )
    return fig, verdict


def main() -> None:
    daily = pd.read_csv(P / "02_kpis_daily.csv")
    users = pd.read_csv(P / "01_kpis_active_users.csv")
    seg = pd.read_csv(P / "03_revenue_by_segment.csv")
    funnel_seg = pd.read_csv(P / "05_funnel_by_segment.csv")
    cohorts = pd.read_csv(P / "06_cohort_retention.csv")
    exp = pd.read_csv(P / "08_experiment_extract.csv")
    exp_fig, verdict = page_experiment(exp)
    pages = [
        ("Executive KPIs", page_exec(daily, users, seg), kpi_cards(daily, users)),
        ("Funnel", page_funnel(funnel_seg), ""),
        ("Cohort retention", page_cohorts(cohorts), ""),
        ("Experiment", exp_fig, f'<p class="verdict">{verdict}</p>'),
    ]
    tabs = "".join(
        f'<button onclick="show({i})" id="t{i}">{name}</button>'
        for i, (name, _, _) in enumerate(pages)
    )
    body = ""
    for i, (_, fig, extra) in enumerate(pages):
        html = fig.to_html(
            full_html=False,
            include_plotlyjs="cdn" if i == 0 else False,
            config={"displaylogo": False},
        )
        body += f'<section id="p{i}" style="display:{"block" if i == 0 else "none"}">{extra}{html}</section>'
    Path("dashboard").mkdir(exist_ok=True)
    Path("dashboard/index.html").write_text(f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Product Analytics Dashboard</title>
<style>
 body{{font-family:system-ui,-apple-system,sans-serif;margin:0;background:#f8fafc;color:#0f172a}}
 header{{padding:16px 24px;background:#0f172a;color:#fff}} header h1{{margin:0;font-size:18px}}
 header p{{margin:4px 0 0;color:#94a3b8;font-size:13px}}
 nav{{padding:8px 24px;background:#fff;border-bottom:1px solid #e2e8f0;display:flex;gap:8px;flex-wrap:wrap}}
 nav button{{border:1px solid #cbd5e1;background:#fff;border-radius:6px;padding:6px 12px;cursor:pointer}}
 nav button.on{{background:{BLUE};color:#fff;border-color:{BLUE}}}
 section{{padding:16px 24px}} .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:12px}}
 .card{{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px}}
 .k{{color:#64748b;font-size:12px;text-transform:uppercase}} .v{{font-size:26px;font-weight:600}} .s{{color:#64748b;font-size:12px}}
 .verdict{{background:#fff;border-left:4px solid {GREEN};padding:12px;border-radius:6px}}
</style></head><body>
<header><h1>E-commerce product analytics · Nov 2020 – Jan 2021</h1>
<p>GA4-schema export (simulated, see README) · SQL in sql/ · stats in notebooks/ab_test.ipynb</p></header>
<nav>{tabs}</nav>{body.replace(pages[0][2], '<div class="cards">' + pages[0][2] + "</div>", 1)}
<script>
function show(i){{document.querySelectorAll('section').forEach((s,j)=>s.style.display=j===i?'block':'none');
document.querySelectorAll('nav button').forEach((b,j)=>b.classList.toggle('on',j===i));
window.dispatchEvent(new Event('resize'));}}
show(parseInt(location.hash.slice(1)) || 0);
</script></body></html>""")
    Path("dashboard/summary.json").write_text(json.dumps({"verdict": verdict}, indent=2))
    print("wrote dashboard/index.html")


if __name__ == "__main__":
    main()
