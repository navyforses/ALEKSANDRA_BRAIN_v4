"""Phase 7.4 Day 1 — entropy tests."""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats

from brain.active.entropy import (
    analytical_entropy_bernoulli,
    analytical_entropy_beta,
    analytical_entropy_gamma,
    analytical_entropy_normal,
    analytical_entropy_poisson,
    entropy_for_distribution_spec,
    shannon_entropy_continuous,
    shannon_entropy_discrete,
)
from brain.belief.schema import DistributionSpec


def test_beta_matches_scipy() -> None:
    """Verifier check 1: Beta(2,8) entropy matches scipy reference within 1e-6."""
    ours = analytical_entropy_beta(2.0, 8.0)
    ref = float(stats.beta.entropy(2.0, 8.0))
    assert ours == pytest.approx(ref, abs=1e-6)


def test_normal_closed_form() -> None:
    ours = analytical_entropy_normal(0.0, 1.0)
    expected = 0.5 * math.log(2.0 * math.pi * math.e)
    assert ours == pytest.approx(expected, abs=1e-9)


def test_bernoulli_max_at_half() -> None:
    assert analytical_entropy_bernoulli(0.5) == pytest.approx(math.log(2.0), abs=1e-9)


def test_bernoulli_zero_one_collapse() -> None:
    assert analytical_entropy_bernoulli(0.0) == 0.0
    assert analytical_entropy_bernoulli(1.0) == 0.0


def test_poisson_nonneg() -> None:
    assert analytical_entropy_poisson(10.0) > 0.0
    assert analytical_entropy_poisson(0.5) > 0.0


def test_uniform_discrete_log_n() -> None:
    probs = np.full(5, 0.2)
    assert shannon_entropy_discrete(probs) == pytest.approx(math.log(5.0), abs=1e-9)


def test_zero_prob_event_handled() -> None:
    # Zero-probability events must not produce -inf or NaN.
    probs = np.array([0.5, 0.0, 0.5])
    h = shannon_entropy_discrete(probs)
    assert math.isfinite(h)
    assert h == pytest.approx(math.log(2.0), abs=1e-9)


def test_continuous_empty_returns_zero() -> None:
    assert shannon_entropy_continuous(np.array([])) == 0.0
    assert shannon_entropy_continuous(np.array([3.0, 3.0, 3.0])) == 0.0


def test_gamma_closed_form_matches_scipy() -> None:
    # scipy.stats.gamma uses scale (=1/rate); we use rate (β).
    alpha, beta = 1.5, 0.5
    ours = analytical_entropy_gamma(alpha, beta)
    ref = float(stats.gamma.entropy(alpha, scale=1.0 / beta))
    assert ours == pytest.approx(ref, abs=1e-6)


def test_entropy_for_distribution_spec_dispatch() -> None:
    beta_spec = DistributionSpec(kind="beta", params={"alpha": 2.0, "beta": 8.0})
    h_beta = entropy_for_distribution_spec(beta_spec)
    assert h_beta == pytest.approx(analytical_entropy_beta(2.0, 8.0), abs=1e-9)

    cat_spec = DistributionSpec(
        kind="categorical", params={"probs": [0.2, 0.2, 0.2, 0.2, 0.2]}
    )
    h_cat = entropy_for_distribution_spec(cat_spec)
    assert h_cat == pytest.approx(math.log(5.0), abs=1e-9)

    vec_spec = DistributionSpec(
        kind="vector",
        params={"mu_vec": [0.0, 0.0], "sigma_vec": [1.0, 1.0]},
    )
    h_vec = entropy_for_distribution_spec(vec_spec, n_simulations=500)
    assert math.isfinite(h_vec)
