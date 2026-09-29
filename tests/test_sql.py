"""Every BigQuery SQL file transpiles and runs on DuckDB, and results obey business invariants.
Uses a small simulated dataset (200 users/day) so CI runs in seconds."""

import pytest

from analytics.run_sql import SQL_DIR, connect, run_query, to_duckdb
from simulate.generate_ga4 import Simulator


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    out = tmp_path_factory.mktemp("ga4")
    Simulator(seed=7, users_per_day=200).run(out)
    return connect(out)


@pytest.fixture(scope="module")
def results(con):
    return {p.stem: run_query(con, p) for p in sorted(SQL_DIR.glob("*.sql"))}


def test_every_query_documents_its_business_question():
    for p in SQL_DIR.glob("*.sql"):
        assert p.read_text().startswith("-- Business question:"), p.name


def test_ga4_unnest_rewrite():
    sql = to_duckdb(
        "SELECT (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'x') "
        "FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`"
    )
    assert "UNNEST(event_params, max_depth := 2)" in sql and "FROM events" in sql


def test_all_queries_return_rows(results):
    assert all(len(df) > 0 for df in results.values())


def test_data_quality_clean_keys(results):
    dq = results["00_data_quality"].set_index("check_name")["n"]
    assert dq["null_user_pseudo_id"] == 0 and dq["duplicate_transaction_ids"] == 0
    assert dq["purchases_missing_revenue"] == 0


def test_active_users_ordering(results):
    u = results["01_kpis_active_users"]
    assert (u.dau <= u.wau).all() and (u.wau <= u.mau).all()


def test_funnel_is_monotonic(results):
    f = results["04_funnel"].sort_values("step_order")
    assert f.users.is_monotonic_decreasing
    assert f.conversion_from_view.iloc[0] == 1.0


def test_cohort_week0_is_full_cohort(results):
    c = results["06_cohort_retention"]
    assert (c[c.week_n == 0].retention == 1.0).all()
    assert (c.retention <= 1.0).all()


def test_rfm_scores_and_segments(results):
    r = results["07_rfm"]
    for col in ("r_score", "f_score", "m_score"):
        assert r[col].between(1, 5).all()
    assert r.user_pseudo_id.is_unique and r.segment.notna().all()


def test_experiment_extract_one_row_per_user(results):
    e = results["08_experiment_extract"]
    assert e.user_pseudo_id.is_unique
    assert set(e.variant) == {"control", "treatment"}
    assert e.converted.isin([0, 1]).all()
    assert (e.first_exposure_day.astype(str) >= "2020-12-01").all()


def test_revenue_reconciles_across_queries(results):
    daily = results["02_kpis_daily"].revenue.sum()
    star = results["09_star_schema"].revenue.sum()
    rfm = results["07_rfm"].monetary.sum()
    assert daily == pytest.approx(star, rel=1e-6) and daily == pytest.approx(rfm, rel=1e-6)


def test_star_schema_grain(results):
    s = results["09_star_schema"]
    assert not s.duplicated(["day", "user_pseudo_id"]).any()
