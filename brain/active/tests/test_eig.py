"""Phase 7.4 Day 2 — EIG tests."""

from __future__ import annotations

import numpy as np
import pytest

from brain.active.eig import (
    EIGEstimate,
    _eig_beta_bernoulli,
    _eig_normal_normal_known_variance,
    _numerical_eig,
    _normal_observation_factory,
    compute_eig,
    compute_eig_for_dimension,
)
from brain.belief.schema import DistributionSpec, load_dimensions_from_toml


def test_eig_nonneg_all_dims() -> None:
    """Verifier check 2: EIG ≥ 0 for every dimension in dimensions.toml."""
    dims = load_dimensions_from_toml()
    assert len(dims) == 13
    rng = np.random.default_rng(7)
    # Pick one obs_type per dim (first valid one from default likelihoods)
    obs_map = {
        "cyst_volume_pct": "mri_volumetric_report",
        "brainstem_function": "neuro_exam",
        "seizure_freq_per_day": "eeg_weekly_count",
        "muscle_tone_hammersmith": "pt_hammersmith_score",
        "eye_tracking_seconds": "five_min_red_ball_video",
        "head_control_seconds": "tummy_time_timer",
        "gmfcs_level": "pt_gmfcs_assessment",
        "bayley_cognitive": "bayley_iii_snapshot",
        "feeding_stage": "weekly_feeding_log",
        "respiratory_apnea_per_day": "monitor_apnea_count",
        "csf_biomarkers": "csf_panel_draw",
        "neuroplasticity_resource": "calendar_age_in_days",
        "family_readiness": "weekly_self_report",
    }
    for dim in dims:
        est = compute_eig_for_dimension(
            dim,
            observation_type=obs_map[dim.name],
            n_simulations=200,
            rng=rng,
        )
        assert est.eig_nats >= 0.0, f"{dim.name} negative EIG: {est.eig_nats}"
        assert isinstance(est, EIGEstimate)


def test_eig_beta_bernoulli_uninformative_positive() -> None:
    # Beta(1,1) is the uninformative prior; a single Bernoulli obs is highly informative.
    eig = _eig_beta_bernoulli(1.0, 1.0)
    assert eig > 0.1, f"expected positive EIG, got {eig}"


def test_eig_uninformative_observation_is_zero() -> None:
    # Normal prior with σ_obs >> σ_prior makes the observation nearly useless.
    eig = _eig_normal_normal_known_variance(0.0, 1.0, sigma_obs=1000.0)
    assert eig < 0.01, f"expected near-zero EIG, got {eig}"


def test_analytical_and_numerical_both_nonneg() -> None:
    """Both analytical (single-obs) and numerical (multi-obs SIR) >= 0.

    They measure different things (analytical = single observation EIG;
    numerical SIR uses a kernel over n_obs samples), so we don't compare
    magnitudes — only that both return valid non-negative estimates.
    """
    spec = DistributionSpec(kind="beta", params={"alpha": 2.0, "beta": 5.0})
    analytical = compute_eig(spec, observation_type="x")
    rng = np.random.default_rng(7)
    numerical = _numerical_eig(spec, _normal_observation_factory(0.1, n=20), 400, rng)
    assert analytical.eig_nats >= 0.0
    assert numerical >= 0.0


def test_eig_estimate_pydantic_validation() -> None:
    with pytest.raises(Exception):
        EIGEstimate(
            dimension_name="x",
            observation_type="y",
            eig_nats=-0.5,  # negative -> rejected
            method="analytical",
            n_simulations=0,
        )


def test_compute_eig_small_n_simulations_works() -> None:
    spec = DistributionSpec(
        kind="exp_decay", params={"lam": 0.0019}
    )
    est = compute_eig(
        spec,
        observation_type="calendar_age_in_days",
        observation_likelihood=_normal_observation_factory(1.0, n=10),
        n_simulations=10,
    )
    assert est.eig_nats >= 0.0
    assert est.method == "numerical_1000"


def test_compute_eig_for_dimension_overrides_name() -> None:
    dims = load_dimensions_from_toml()
    dim = next(d for d in dims if d.name == "cyst_volume_pct")
    est = compute_eig_for_dimension(
        dim, observation_type="mri_volumetric_report", n_simulations=100
    )
    assert est.dimension_name == "cyst_volume_pct"
    assert est.observation_type == "mri_volumetric_report"
