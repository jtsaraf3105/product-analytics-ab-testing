"""A/B test statistics, written out explicitly (and cross-checked against scipy/statsmodels
in tests/test_stats.py) so every number in the notebook can be explained on a whiteboard."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class SRMResult:
    n_control: int
    n_treatment: int
    expected_share: float
    chi2: float
    p_value: float

    @property
    def mismatch(self) -> bool:
        # A strict threshold is standard for SRM: it's a data-quality alarm, not a hypothesis test.
        return self.p_value < 0.001


def srm_test(n_control: int, n_treatment: int, expected_share: float = 0.5) -> SRMResult:
    """Sample Ratio Mismatch: chi-square goodness-of-fit of observed arm sizes vs the design."""
    total = n_control + n_treatment
    expected = np.array([total * expected_share, total * (1 - expected_share)])
    observed = np.array([n_control, n_treatment])
    chi2 = float(((observed - expected) ** 2 / expected).sum())
    return SRMResult(n_control, n_treatment, expected_share, chi2, float(stats.chi2.sf(chi2, 1)))


@dataclass(frozen=True)
class ProportionTest:
    p_control: float
    p_treatment: float
    abs_diff: float
    rel_lift: float
    z: float
    p_value: float
    ci_abs: tuple[float, float]
    ci_rel: tuple[float, float]

    @property
    def significant(self) -> bool:
        return self.p_value < 0.05


def two_proportion_ztest(
    x_c: int, n_c: int, x_t: int, n_t: int, alpha: float = 0.05
) -> ProportionTest:
    """Two-sided z-test for p_t - p_c.

    * test statistic uses the **pooled** proportion (under H0 both arms share one rate);
    * the CI for the absolute difference uses the **unpooled** (Wald) standard error;
    * the CI for relative lift (p_t / p_c - 1) uses the delta method on log(p_t / p_c).
    """
    p_c, p_t = x_c / n_c, x_t / n_t
    pooled = (x_c + x_t) / (n_c + n_t)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / n_c + 1 / n_t))
    z = (p_t - p_c) / se_pooled
    p_value = 2 * stats.norm.sf(abs(z))
    zc = stats.norm.ppf(1 - alpha / 2)
    se = math.sqrt(p_c * (1 - p_c) / n_c + p_t * (1 - p_t) / n_t)
    diff = p_t - p_c
    se_log = math.sqrt((1 - p_t) / x_t + (1 - p_c) / x_c)
    log_ratio = math.log(p_t / p_c)
    return ProportionTest(
        p_c,
        p_t,
        diff,
        p_t / p_c - 1,
        z,
        float(p_value),
        (diff - zc * se, diff + zc * se),
        (math.exp(log_ratio - zc * se_log) - 1, math.exp(log_ratio + zc * se_log) - 1),
    )


def chi_square_test(x_c: int, n_c: int, x_t: int, n_t: int) -> tuple[float, float]:
    """Pearson chi-square on the 2x2 (converted / not) table, no continuity correction.
    For a 2x2 table chi2 == z**2 of the pooled z-test, so the p-values agree."""
    table = np.array([[x_c, n_c - x_c], [x_t, n_t - x_t]])
    chi2, p, _, _ = stats.chi2_contingency(table, correction=False)
    return float(chi2), float(p)


def sample_size_per_arm(
    p_base: float, mde_rel: float, alpha: float = 0.05, power: float = 0.8
) -> int:
    """Users per arm to detect a relative lift `mde_rel` on baseline `p_base` (two-sided)."""
    p2 = p_base * (1 + mde_rel)
    za, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    p_bar = (p_base + p2) / 2
    num = (
        za * math.sqrt(2 * p_bar * (1 - p_bar))
        + zb * math.sqrt(p_base * (1 - p_base) + p2 * (1 - p2))
    ) ** 2
    return math.ceil(num / (p2 - p_base) ** 2)


def power_two_proportions(
    p_base: float, p_treat: float, n_per_arm: int, alpha: float = 0.05
) -> float:
    za = stats.norm.ppf(1 - alpha / 2)
    se = math.sqrt(p_base * (1 - p_base) / n_per_arm + p_treat * (1 - p_treat) / n_per_arm)
    return float(stats.norm.cdf(abs(p_treat - p_base) / se - za))


def minimum_detectable_effect(
    p_base: float, n_per_arm: int, alpha: float = 0.05, power: float = 0.8
) -> float:
    """Smallest relative lift detectable with the given sample (approximation)."""
    za, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    abs_mde = (za + zb) * math.sqrt(2 * p_base * (1 - p_base) / n_per_arm)
    return abs_mde / p_base


def bootstrap_diff_ci(
    a: np.ndarray, b: np.ndarray, n_boot: int = 2000, alpha: float = 0.05, seed: int = 0
) -> tuple[float, float, float]:
    """Percentile bootstrap CI for mean(b) - mean(a). For skewed metrics like revenue/user."""
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        diffs[i] = rng.choice(b, b.size).mean() - rng.choice(a, a.size).mean()
    lo, hi = np.quantile(diffs, [alpha / 2, 1 - alpha / 2])
    return float(b.mean() - a.mean()), float(lo), float(hi)


def peeking_false_positive_rate(
    p: float = 0.03,
    n_per_arm: int = 20_000,
    looks: int = 20,
    sims: int = 2000,
    alpha: float = 0.05,
    seed: int = 1,
) -> float:
    """A/A simulation: stop at the first of `looks` interim analyses with p < alpha.
    Shows why peeking without correction inflates the false-positive rate far above alpha."""
    rng = np.random.default_rng(seed)
    checkpoints = np.linspace(n_per_arm / looks, n_per_arm, looks).astype(int)
    false_pos = 0
    for _ in range(sims):
        a = rng.random(n_per_arm) < p
        b = rng.random(n_per_arm) < p
        ca, cb = np.cumsum(a), np.cumsum(b)
        for n in checkpoints:
            pooled = (ca[n - 1] + cb[n - 1]) / (2 * n)
            if pooled in (0, 1):
                continue
            z = (cb[n - 1] - ca[n - 1]) / n / math.sqrt(pooled * (1 - pooled) * 2 / n)
            if 2 * stats.norm.sf(abs(z)) < alpha:
                false_pos += 1
                break
    return false_pos / sims
