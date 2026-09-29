import numpy as np
import pytest
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize, proportions_ztest

from analytics.stats import (
    bootstrap_diff_ci,
    chi_square_test,
    minimum_detectable_effect,
    peeking_false_positive_rate,
    power_two_proportions,
    sample_size_per_arm,
    srm_test,
    two_proportion_ztest,
)


def test_ztest_matches_statsmodels():
    r = two_proportion_ztest(300, 10_000, 360, 10_000)
    z, p = proportions_ztest([360, 300], [10_000, 10_000])
    assert r.z == pytest.approx(z) and r.p_value == pytest.approx(p)
    assert r.rel_lift == pytest.approx(0.2)
    assert r.ci_abs[0] < r.abs_diff < r.ci_abs[1]
    assert r.ci_rel[0] < r.rel_lift < r.ci_rel[1]


def test_chi_square_equals_z_squared_on_2x2():
    r = two_proportion_ztest(300, 10_000, 360, 10_000)
    chi2, p = chi_square_test(300, 10_000, 360, 10_000)
    assert chi2 == pytest.approx(r.z**2) and p == pytest.approx(r.p_value)


def test_null_effect_ci_contains_zero():
    r = two_proportion_ztest(500, 20_000, 500, 20_000)
    assert r.p_value == pytest.approx(1.0) and r.ci_abs[0] < 0 < r.ci_abs[1]


def test_srm():
    assert not srm_test(50_000, 50_300).mismatch
    bad = srm_test(50_000, 48_500)
    assert bad.mismatch and bad.p_value < 1e-5


def test_sample_size_close_to_statsmodels_and_consistent_with_power():
    n = sample_size_per_arm(0.03, 0.10)
    h = proportion_effectsize(0.033, 0.03)
    sm = NormalIndPower().solve_power(effect_size=h, alpha=0.05, power=0.8)
    assert n == pytest.approx(sm, rel=0.02)
    assert power_two_proportions(0.03, 0.033, n) == pytest.approx(0.8, abs=0.01)
    assert minimum_detectable_effect(0.03, n) == pytest.approx(0.10, rel=0.03)


def test_bootstrap_ci_covers_true_difference():
    rng = np.random.default_rng(3)
    a = rng.exponential(10, 4000)
    b = rng.exponential(11, 4000)
    diff, lo, hi = bootstrap_diff_ci(a, b, n_boot=500)
    assert lo < 1.0 < hi and lo < diff < hi


def test_peeking_inflates_false_positives():
    fpr = peeking_false_positive_rate(sims=300, n_per_arm=5_000, looks=10)
    assert fpr > 0.10  # nominal alpha is 0.05
