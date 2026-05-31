"""Phase 7.0 Days 11-12 — Likelihood builders per distribution kind.

For each `distribution` in DISTRIBUTION_KINDS, define a closure that takes:
  - prior_rv: the PyMC RV returned by DistributionSpec.to_pm()
  - evidence_value: the dict from BeliefEvidence.value (JSONB-compatible)

and returns the observed PyMC RV (Binomial, Normal, Poisson, etc.) wired
to the prior, with `observed=` populated from the evidence value.

This is the Bayesian-update glue layer between schema.py (priors) and
update.py (Day 13-14: posterior sampling + persistence).

Design decisions (Day 11-12, recorded for Day 13-14 contract):

  - **exp_decay** (Day 10 resolution): the prior RV stays in its natural
    time-remaining parameter space (`pm.Exponential(lam)`); the likelihood
    computes the deterministic transform `exp(-lam * horizon_days)` INLINE
    via `pm.math.exp` and observes a Normal(mu=transform, sigma=0.05)
    around the clinical resource-fraction observation in [0, 1]. This keeps
    the prior consistent with its TOML definition while keeping evidence in
    the units a clinician/family actually records (fraction of resource
    remaining at the named horizon).

  - **gamma** parameterization: PyMC's `pm.Gamma` accepts either
    (alpha, beta) OR (mu, sigma). We adopt the `(mu, sigma)` form for the
    LIKELIHOOD only (`pm.Gamma(mu=prior_rv, sigma=...)`) because the prior
    RV represents the *mean* of the data-generating Gamma — that's the
    natural Bayesian-update semantics (Gamma prior on the mean of an
    observation Gamma, with a fixed shape proxy via sigma). The PRIOR
    itself still uses (alpha, beta) per `dimensions.toml`.

  - **categorical** degenerate-prior handling: the Categorical prior in
    `schema.to_pm` is a single class-index RV drawn from `probs`. The
    likelihood treats `evidence.value["observations"]` as a list of
    independent class-index observations from the SAME `probs` vector
    (the prior). This is technically a degenerate update — repeated
    observations re-fit `probs` only if upstream wires a Dirichlet over
    `probs` (deferred to Day 13-14 if needed). MVP behaviour: observed
    Categorical with the prior's `probs`.

  - **vector** MVP simplification: schema.to_pm returns independent
    `pm.Normal` with per-dim mu/sigma. The likelihood mirrors that —
    independent Normal observations per dimension. Full covariance
    handling (MvNormal with cov matrix) is deferred until update.py
    needs it (Day 13-14 may upgrade).
"""

from __future__ import annotations
from typing import Any, Callable

import numpy as np
import pymc as pm

# Type alias for clarity
LikelihoodBuilder = Callable[[Any, dict], Any]


# ---------------------------------------------------------------------------
# Per-distribution likelihood-shape contract
# ---------------------------------------------------------------------------
LIKELIHOOD_VALUE_SCHEMA: dict[str, set[str]] = {
    "beta": {"n", "k"},  # n trials, k successes → Binomial
    "normal": {"observations"},  # list[float] → Normal with prior_rv as mu
    "poisson": {"observations"},  # list[int] event counts → Poisson(mu=prior_rv)
    "categorical": {
        "observations"
    },  # list[int] class indices → Categorical(p=prior_rv probs)
    "gamma": {"observations"},  # list[float positive] → Gamma(mu=prior_rv, sigma)
    "bernoulli": {"observations"},  # list[0/1] → Bernoulli(p=prior_rv)
    "vector": {"observations"},  # list[list[float]] → independent Normal per dim
    "exp_decay": {
        "observations",
        "horizon_days",
    },  # observations in [0,1]; horizon converts to fraction
}


# ---------------------------------------------------------------------------
# Likelihood builders
# ---------------------------------------------------------------------------
def _beta_likelihood(prior_rv: Any, value: dict) -> Any:
    """Beta prior on p → Binomial(n, p) likelihood.

    evidence.value = {"n": int, "k": int} where 0 <= k <= n.
    """
    n = int(value["n"])
    k = int(value["k"])
    if n < 0:
        raise ValueError(f"n must be non-negative, got n={n}")
    if k < 0:
        raise ValueError(f"k must be non-negative, got k={k}")
    if k > n:
        raise ValueError(f"k={k} > n={n} — invalid beta-binomial observation")
    return pm.Binomial("obs", n=n, p=prior_rv, observed=k)


def _normal_likelihood(prior_rv: Any, value: dict) -> Any:
    """Normal prior on mu → Normal(mu, sigma) likelihood with fixed sigma.

    evidence.value = {"observations": list[float], "sigma": float (optional, default=1.0)}
    """
    obs = np.asarray(value["observations"], dtype=float)
    if obs.size == 0:
        raise ValueError("normal likelihood requires at least one observation")
    sigma = float(value.get("sigma", 1.0))
    if sigma <= 0:
        raise ValueError(f"sigma must be positive, got {sigma}")
    return pm.Normal("obs", mu=prior_rv, sigma=sigma, observed=obs)


def _poisson_likelihood(prior_rv: Any, value: dict) -> Any:
    """Poisson prior on mu → Poisson(mu) likelihood (i.i.d. over observations).

    evidence.value = {"observations": list[int]}
    """
    obs = np.asarray(value["observations"], dtype=int)
    if obs.size == 0:
        raise ValueError("poisson likelihood requires at least one observation")
    if (obs < 0).any():
        raise ValueError(
            f"Poisson observations must be non-negative, got {obs.tolist()}"
        )
    return pm.Poisson("obs", mu=prior_rv, observed=obs)


def _categorical_likelihood(prior_rv: Any, value: dict) -> Any:
    """Categorical(probs) prior → Categorical(probs) likelihood (i.i.d. class indices).

    See module docstring for the "degenerate prior" handling note.
    evidence.value = {"observations": list[int]} where each int is a class index.
    """
    obs = np.asarray(value["observations"], dtype=int)
    if obs.size == 0:
        raise ValueError("categorical likelihood requires at least one observation")
    if (obs < 0).any():
        raise ValueError(
            f"Categorical observations must be non-negative class indices, "
            f"got {obs.tolist()}"
        )
    return pm.Categorical("obs", p=prior_rv, observed=obs)


def _gamma_likelihood(prior_rv: Any, value: dict) -> Any:
    """Gamma prior — observation likelihood is Gamma with prior_rv as the mean.

    Convention: `pm.Gamma(mu=prior_rv, sigma=value.get("sigma", 1.0))` —
    prior_rv represents the data-generating mean.

    evidence.value = {"observations": list[float positive], "sigma": float (optional)}
    """
    obs = np.asarray(value["observations"], dtype=float)
    if obs.size == 0:
        raise ValueError("gamma likelihood requires at least one observation")
    if (obs <= 0).any():
        raise ValueError(
            f"Gamma observations must be strictly positive, got {obs.tolist()}"
        )
    sigma = float(value.get("sigma", 1.0))
    if sigma <= 0:
        raise ValueError(f"sigma must be positive, got {sigma}")
    return pm.Gamma("obs", mu=prior_rv, sigma=sigma, observed=obs)


def _bernoulli_likelihood(prior_rv: Any, value: dict) -> Any:
    """Bernoulli(p) prior → Bernoulli(p) likelihood (i.i.d. trials).

    evidence.value = {"observations": list[0/1]}
    """
    obs = np.asarray(value["observations"], dtype=int)
    if obs.size == 0:
        raise ValueError("bernoulli likelihood requires at least one observation")
    unique_vals = set(np.unique(obs).tolist())
    if not unique_vals.issubset({0, 1}):
        raise ValueError(
            f"Bernoulli observations must be in {{0, 1}}, got unique values "
            f"{sorted(unique_vals)}"
        )
    return pm.Bernoulli("obs", p=prior_rv, observed=obs)


def _vector_likelihood(prior_rv: Any, value: dict) -> Any:
    """Vector prior (independent Normals per `schema.to_pm`) → independent Normal observed.

    evidence.value = {"observations": list[list[float]]} where each inner list
    has length D matching the prior's vector dim.

    For MVP, treat as N independent Normal(mu_i, sigma=1.0) observations per
    dimension i. Sigma is configurable via value.get("sigma", 1.0).
    """
    obs = np.asarray(value["observations"], dtype=float)
    if obs.ndim != 2:
        raise ValueError(
            f"Vector observations must be 2D (N × D), got shape {obs.shape}"
        )
    if obs.size == 0:
        raise ValueError("vector likelihood requires at least one observation")
    sigma = float(value.get("sigma", 1.0))
    if sigma <= 0:
        raise ValueError(f"sigma must be positive, got {sigma}")
    return pm.Normal("obs", mu=prior_rv, sigma=sigma, observed=obs)


def _exp_decay_likelihood(prior_rv: Any, value: dict) -> Any:
    """Exp_decay prior — observation likelihood on the resource-fraction transform.

    Per Day 10 finding: prior_rv is in time-remaining units (pm.Exponential lam),
    but observations land as resource-fraction values in [0, 1]. Transform:
        resource_fraction(t) = exp(-lam * t)
    where t = horizon_days from evidence.value.

    evidence.value = {"observations": list[float in [0,1]], "horizon_days": float > 0}

    Likelihood: Normal(mu=resource_fraction, sigma=0.05) — a tight Gaussian
    around the deterministic transform. Day 13-14 may refine (e.g., Beta
    likelihood bounded on [0, 1]) if posterior diagnostics demand it.

    NOTE: prior_rv here is the RAW lam RV from `schema.to_pm` exp_decay branch.
    The transform is computed inline so the prior keeps its natural units.
    """
    obs = np.asarray(value["observations"], dtype=float)
    if obs.size == 0:
        raise ValueError("exp_decay likelihood requires at least one observation")
    if ((obs < 0) | (obs > 1)).any():
        raise ValueError(
            f"exp_decay observations must be in [0, 1], got {obs.tolist()}"
        )
    horizon = float(value["horizon_days"])
    if horizon <= 0:
        raise ValueError(f"horizon_days must be positive, got {horizon}")
    # Deterministic resource-fraction transform; observed against a tight Normal.
    resource_fraction = pm.math.exp(-prior_rv * horizon)
    return pm.Normal("obs", mu=resource_fraction, sigma=0.05, observed=obs)


# ---------------------------------------------------------------------------
# Registry + lookup helpers
# ---------------------------------------------------------------------------
LIKELIHOOD_REGISTRY: dict[str, LikelihoodBuilder] = {
    "beta": _beta_likelihood,
    "normal": _normal_likelihood,
    "poisson": _poisson_likelihood,
    "categorical": _categorical_likelihood,
    "gamma": _gamma_likelihood,
    "bernoulli": _bernoulli_likelihood,
    "vector": _vector_likelihood,
    "exp_decay": _exp_decay_likelihood,
}


def get_likelihood(distribution_kind: str) -> LikelihoodBuilder:
    """Lookup helper with a clear error message on unknown kind."""
    try:
        return LIKELIHOOD_REGISTRY[distribution_kind]
    except KeyError:
        raise KeyError(
            f"No likelihood registered for distribution kind "
            f"{distribution_kind!r}. Known kinds: "
            f"{sorted(LIKELIHOOD_REGISTRY.keys())}"
        )


def validate_evidence_value(distribution_kind: str, value: dict) -> None:
    """Check that `value` carries the keys this distribution's likelihood needs.

    Raises KeyError if required keys are missing. Use this BEFORE calling the
    likelihood builder to fail fast with a clear error.

    Unknown distribution_kind silently returns (no required-keys contract).
    Use `get_likelihood` first if you need a hard fail on unknown kind.
    """
    required = LIKELIHOOD_VALUE_SCHEMA.get(distribution_kind, set())
    missing = required - set(value.keys())
    if missing:
        raise KeyError(
            f"evidence.value for distribution {distribution_kind!r} missing "
            f"keys: {sorted(missing)}. Required: {sorted(required)}, "
            f"got: {sorted(value.keys())}"
        )


__all__ = [
    "LikelihoodBuilder",
    "LIKELIHOOD_VALUE_SCHEMA",
    "LIKELIHOOD_REGISTRY",
    "get_likelihood",
    "validate_evidence_value",
]
