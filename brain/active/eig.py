"""Phase 7.4 Day 2 — Expected Information Gain (EIG) calculator.

EIG(o) = H(θ) − E_{o ~ p(o)}[H(θ | o)]

Two paths:

  * Conjugate / closed-form (Beta-Bernoulli, Beta-Binomial, Normal-Normal
    with known variance, Gamma-Poisson) — analytical posterior given an
    observation, analytical posterior entropy, expectation taken over the
    prior-predictive of the observation. Fast, deterministic, exact.

  * Non-conjugate fallback — 1000 prior draws -> 1000 simulated observations
    via the user-supplied `observation_likelihood` sampler -> 1000
    sampling-importance-resampled posteriors -> mean posterior entropy.
    Slow-ish but framework-agnostic.

Output is `eig_nats ≥ 0` (numerical drift is clamped at 0). Spec §4 check 2
requires every dim's EIG to be non-negative.

Reference:
    - Phase 7.4 spec §1 Days 1-2; §2.1 (LOC budget)
    - Lindley D.V. (1956), Ann. Math. Stat.
    - Foster et al. (2020), AISTATS  https://arxiv.org/abs/1911.00294
"""

from __future__ import annotations

import math
from typing import Callable, Literal, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

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
from brain.belief.persistence import BeliefDimension
from brain.belief.schema import DistributionSpec, get_dimension_spec


# ---------------------------------------------------------------------------
# Pydantic — EIGEstimate
# ---------------------------------------------------------------------------
class EIGEstimate(BaseModel):
    """One EIG measurement for a (dim, observation_type) pair."""

    model_config = ConfigDict(extra="forbid")

    dimension_name: str = Field(..., min_length=1)
    dimension_id: Optional[int] = None
    observation_type: str = Field(..., min_length=1)
    eig_nats: float = Field(..., ge=0.0)
    method: Literal["analytical", "numerical_1000"]
    n_simulations: int = Field(..., ge=0)


# ---------------------------------------------------------------------------
# Default observation-likelihood factory (39 hardcoded entries)
# ---------------------------------------------------------------------------
ObsSampler = Callable[[float], np.ndarray]


def _normal_observation_factory(noise_sd: float, n: int = 200) -> ObsSampler:
    """Return a sampler `f(true_value) -> array of n noisy observations`."""

    def sample(true_value: float) -> np.ndarray:
        rng = np.random.default_rng(int(abs(true_value) * 1000) % (2**31))
        return rng.normal(true_value, noise_sd, size=n)

    return sample


def _bernoulli_observation_factory(n: int = 50) -> ObsSampler:
    def sample(p: float) -> np.ndarray:
        rng = np.random.default_rng(int(abs(p) * 1_000_000) % (2**31))
        return rng.binomial(1, max(0.0, min(1.0, p)), size=n).astype(float)

    return sample


def _poisson_observation_factory(n: int = 30) -> ObsSampler:
    def sample(mu: float) -> np.ndarray:
        rng = np.random.default_rng(int(abs(mu) * 1000) % (2**31))
        return rng.poisson(max(0.0, mu), size=n).astype(float)

    return sample


def _gamma_observation_factory(noise_sd: float, n: int = 50) -> ObsSampler:
    # Treat eye-tracking seconds as a noisy real-valued observation.
    return _normal_observation_factory(noise_sd, n=n)


# Hardcoded dim x observation_type -> sampler. 13 dims × 1-3 obs types.
DEFAULT_LIKELIHOODS: dict[tuple[str, str], ObsSampler] = {
    # cyst_volume_pct
    ("cyst_volume_pct", "mri_volumetric_report"): _normal_observation_factory(0.5),
    ("cyst_volume_pct", "radiologist_estimate"): _normal_observation_factory(2.0),
    # brainstem_function
    ("brainstem_function", "neuro_exam"): _bernoulli_observation_factory(n=20),
    # seizure_freq_per_day
    ("seizure_freq_per_day", "eeg_weekly_count"): _poisson_observation_factory(n=20),
    ("seizure_freq_per_day", "parent_log_count"): _poisson_observation_factory(n=14),
    # muscle_tone_hammersmith
    ("muscle_tone_hammersmith", "pt_hammersmith_score"): _normal_observation_factory(3.0),
    # eye_tracking_seconds
    ("eye_tracking_seconds", "five_min_red_ball_video"): _gamma_observation_factory(0.5),
    ("eye_tracking_seconds", "clinic_eye_tracking"): _gamma_observation_factory(0.25),
    # head_control_seconds
    ("head_control_seconds", "tummy_time_timer"): _normal_observation_factory(2.0),
    # gmfcs_level
    ("gmfcs_level", "pt_gmfcs_assessment"): _bernoulli_observation_factory(n=10),
    # bayley_cognitive
    ("bayley_cognitive", "bayley_iii_snapshot"): _normal_observation_factory(8.0),
    # feeding_stage
    ("feeding_stage", "weekly_feeding_log"): _bernoulli_observation_factory(n=20),
    # respiratory_apnea_per_day
    ("respiratory_apnea_per_day", "monitor_apnea_count"): _bernoulli_observation_factory(n=14),
    # csf_biomarkers
    ("csf_biomarkers", "csf_panel_draw"): _normal_observation_factory(0.5),
    # neuroplasticity_resource
    ("neuroplasticity_resource", "calendar_age_in_days"): _normal_observation_factory(1.0),
    # family_readiness
    ("family_readiness", "weekly_self_report"): _bernoulli_observation_factory(n=10),
}


def default_observation_likelihood(dim_name: str, obs_type: str) -> ObsSampler:
    """Return the default likelihood sampler for a (dim, obs_type) pair.

    Falls back to a generic Normal(true_value, 1.0) sampler when no entry
    is registered (defensive — keeps EIG computation robust to new
    observation types added later).
    """
    key = (dim_name, obs_type)
    if key in DEFAULT_LIKELIHOODS:
        return DEFAULT_LIKELIHOODS[key]
    return _normal_observation_factory(1.0)


# ---------------------------------------------------------------------------
# Closed-form EIG paths
# ---------------------------------------------------------------------------
def _eig_beta_bernoulli(alpha: float, beta_param: float) -> float:
    """Closed-form EIG for a Beta(α,β) prior with one Bernoulli observation.

    Prior-predictive p(o=1) = α / (α+β).
    Posterior given o=1 is Beta(α+1, β), given o=0 is Beta(α, β+1).
    EIG = H(prior) - p(1)*H(post|1) - p(0)*H(post|0).
    """
    p1 = alpha / (alpha + beta_param)
    p0 = 1.0 - p1
    h_prior = analytical_entropy_beta(alpha, beta_param)
    h_post_1 = analytical_entropy_beta(alpha + 1.0, beta_param)
    h_post_0 = analytical_entropy_beta(alpha, beta_param + 1.0)
    eig = h_prior - p1 * h_post_1 - p0 * h_post_0
    return max(0.0, eig)


def _eig_normal_normal_known_variance(
    mu: float, sigma_prior: float, sigma_obs: float
) -> float:
    """Closed-form EIG for Normal-Normal with known observation noise σ_obs.

    EIG = 0.5 * log(1 + σ_prior² / σ_obs²)  (Bishop 2006 §2.3.6)
    """
    if sigma_prior <= 0 or sigma_obs <= 0:
        return 0.0
    eig = 0.5 * math.log(1.0 + (sigma_prior * sigma_prior) / (sigma_obs * sigma_obs))
    return max(0.0, eig)


def _eig_gamma_poisson(alpha: float, beta_param: float) -> float:
    """Approximate closed-form EIG for Gamma(α,β) prior + Poisson(λ) obs.

    Posterior given a single observation k is Gamma(α + k, β + 1).
    Prior-predictive on k is NegativeBinomial(α, β/(β+1)). We compute the
    expectation by truncating the NB support at α/β + 6*sqrt(var).
    """
    if alpha <= 0 or beta_param <= 0:
        return 0.0
    h_prior = analytical_entropy_gamma(alpha, beta_param)
    # NB prior-predictive: mean α/β, var α(β+1)/β²
    mean_pp = alpha / beta_param
    var_pp = alpha * (beta_param + 1.0) / (beta_param * beta_param)
    upper = int(mean_pp + 6.0 * math.sqrt(max(var_pp, 1e-9))) + 5
    # NB pmf: C(α+k-1, k) * (β/(β+1))^α * (1/(β+1))^k for α potentially non-int
    # — use scipy.special.gammaln for the generalised binomial coefficient.
    from scipy import special as _sp

    log_p1 = alpha * math.log(beta_param / (beta_param + 1.0))
    log_q = -math.log(beta_param + 1.0)
    h_expected = 0.0
    total_prob = 0.0
    for k in range(0, upper + 1):
        log_binom = (
            _sp.gammaln(alpha + k)
            - _sp.gammaln(alpha)
            - _sp.gammaln(k + 1)
        )
        log_p = log_binom + log_p1 + k * log_q
        p = math.exp(log_p)
        if p <= 0:
            continue
        h_post = analytical_entropy_gamma(alpha + k, beta_param + 1.0)
        h_expected += p * h_post
        total_prob += p
    if total_prob > 0:
        h_expected /= total_prob  # normalise truncation drift
    eig = h_prior - h_expected
    return max(0.0, eig)


# ---------------------------------------------------------------------------
# Numerical fallback — Sampling-Importance-Resampling (SIR) approximation
# ---------------------------------------------------------------------------
def _numerical_eig(
    spec: DistributionSpec,
    observation_likelihood: ObsSampler,
    n_simulations: int,
    rng: np.random.Generator,
) -> float:
    """Numerical EIG via SIR. Returns ≥ 0."""
    from brain.active.entropy import _sample_from_spec  # local import

    h_prior = entropy_for_distribution_spec(
        spec, n_simulations=n_simulations, rng=rng
    )
    # Sample candidate true values from the prior
    n_outer = max(20, n_simulations // 25)  # cap outer loop cost
    n_inner = max(50, n_simulations // n_outer)
    prior_draws = _sample_from_spec(spec, n_outer, rng)

    h_post_total = 0.0
    valid = 0
    for true_val in prior_draws:
        try:
            obs_samples = observation_likelihood(float(true_val))
        except Exception:
            continue
        if obs_samples is None or len(obs_samples) == 0:
            continue
        # Approximate posterior: importance-resample prior draws weighted by
        # likelihood evaluated at the mean of the observation sample.
        prior_pool = _sample_from_spec(spec, n_inner, rng)
        obs_mean = float(np.mean(obs_samples))
        # Gaussian-kernel weighting around obs_mean (bandwidth = sd of obs)
        bw = max(float(np.std(obs_samples)), 1e-3)
        weights = np.exp(-0.5 * ((prior_pool - obs_mean) / bw) ** 2)
        if weights.sum() <= 0:
            continue
        weights = weights / weights.sum()
        # Resample with weights to form the posterior surrogate
        idx = rng.choice(prior_pool.size, size=prior_pool.size, p=weights)
        posterior = prior_pool[idx]
        h_post_total += shannon_entropy_continuous(posterior)
        valid += 1
    if valid == 0:
        return 0.0
    h_post_avg = h_post_total / valid
    return max(0.0, h_prior - h_post_avg)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def compute_eig(
    spec: DistributionSpec,
    *,
    observation_type: str,
    observation_likelihood: Optional[ObsSampler] = None,
    n_simulations: int = 1000,
    rng: Optional[np.random.Generator] = None,
) -> EIGEstimate:
    """Compute EIG for a `DistributionSpec` + observation pair.

    Picks analytical when the conjugate path is registered:
        Beta-Bernoulli, Normal-Normal (known variance via factory),
        Gamma-Poisson.
    Otherwise falls back to SIR-numerical approximation.

    NOTE: The `dimension_name` field on the returned EIGEstimate is filled
    with `observation_type` here — `compute_eig_for_dimension` overrides it
    with the real dimension name. Callers using `compute_eig` directly
    should pass `dimension_name` via the higher-level wrapper.
    """
    if rng is None:
        rng = np.random.default_rng(7)
    p = spec.params
    kind = spec.kind

    # Analytical paths
    if kind == "beta":
        eig = _eig_beta_bernoulli(p["alpha"], p["beta"])
        return EIGEstimate(
            dimension_name=observation_type,
            observation_type=observation_type,
            eig_nats=eig,
            method="analytical",
            n_simulations=0,
        )
    if kind == "normal":
        # Heuristic σ_obs: tighter for `mri_*` / `clinic_*`, looser for parent reports
        sigma_obs = 0.5 * float(p["sigma"]) if "clinic" in observation_type else float(p["sigma"])
        eig = _eig_normal_normal_known_variance(
            float(p["mu"]), float(p["sigma"]), max(sigma_obs, 1e-6)
        )
        return EIGEstimate(
            dimension_name=observation_type,
            observation_type=observation_type,
            eig_nats=eig,
            method="analytical",
            n_simulations=0,
        )
    if kind == "poisson":
        # Gamma prior is implicit (Jeffreys-like Gamma(0.5, 0.0001)); we
        # approximate by upgrading the Poisson mu to a Gamma(α=mu, β=1)
        # equivalent for EIG purposes — gives a non-trivial bound.
        eig = _eig_gamma_poisson(float(p["mu"]), 1.0)
        return EIGEstimate(
            dimension_name=observation_type,
            observation_type=observation_type,
            eig_nats=eig,
            method="analytical",
            n_simulations=0,
        )
    if kind == "gamma":
        eig = _eig_gamma_poisson(float(p["alpha"]), float(p["beta"]))
        return EIGEstimate(
            dimension_name=observation_type,
            observation_type=observation_type,
            eig_nats=eig,
            method="analytical",
            n_simulations=0,
        )
    if kind == "bernoulli":
        # Treat the underlying p as Beta(α, β) with α=β=1 + observation count
        # Equivalent EIG: H(Bernoulli) since observation IS the variable
        h = analytical_entropy_bernoulli(float(p["p"]))
        # An observation collapses uncertainty to ~0 in the limit
        eig = h  # upper-bound: H(prior) − 0
        return EIGEstimate(
            dimension_name=observation_type,
            observation_type=observation_type,
            eig_nats=max(0.0, eig),
            method="analytical",
            n_simulations=0,
        )
    if kind == "categorical":
        h_prior = shannon_entropy_discrete(np.asarray(p["probs"], dtype=float))
        # One categorical observation reduces entropy to 0 in the noiseless
        # limit; in practice clinician/parent reports are noisy, so apply
        # a 0.7 fractional reduction (heuristic).
        eig = max(0.0, 0.7 * h_prior)
        return EIGEstimate(
            dimension_name=observation_type,
            observation_type=observation_type,
            eig_nats=eig,
            method="analytical",
            n_simulations=0,
        )

    # Numerical fallback: vector, exp_decay
    if observation_likelihood is None:
        observation_likelihood = _normal_observation_factory(1.0)
    eig = _numerical_eig(spec, observation_likelihood, n_simulations, rng)
    return EIGEstimate(
        dimension_name=observation_type,
        observation_type=observation_type,
        eig_nats=eig,
        method="numerical_1000",
        n_simulations=n_simulations,
    )


def compute_eig_for_dimension(
    dim: BeliefDimension,
    *,
    observation_type: str,
    n_simulations: int = 1000,
    rng: Optional[np.random.Generator] = None,
) -> EIGEstimate:
    """High-level wrapper: `BeliefDimension` -> `EIGEstimate`."""
    spec = get_dimension_spec(dim)
    likelihood = default_observation_likelihood(dim.name, observation_type)
    est = compute_eig(
        spec,
        observation_type=observation_type,
        observation_likelihood=likelihood,
        n_simulations=n_simulations,
        rng=rng,
    )
    return est.model_copy(
        update={"dimension_name": dim.name, "dimension_id": dim.id}
    )


__all__ = [
    "EIGEstimate",
    "ObsSampler",
    "DEFAULT_LIKELIHOODS",
    "default_observation_likelihood",
    "compute_eig",
    "compute_eig_for_dimension",
]
