"""Phase 7.4 Day 1 — Shannon entropy + analytical closed forms.

Provides entropy estimates for the 8 distribution kinds shipped by Phase 7.0
(beta, normal, poisson, categorical, gamma, bernoulli, vector, exp_decay).

For each conjugate / closed-form distribution we expose a dedicated
`analytical_entropy_*` helper. `entropy_for_distribution_spec` dispatches:
analytical when available, numerical 1000-sample histogram fallback
otherwise.

Reference:
    - Cover & Thomas, *Elements of Information Theory* 2nd ed. (2006)
    - scipy.stats.beta.entropy / scipy.stats.norm.entropy (sanity checks)
    - Phase 7.4 spec §1 Day 1 (Lindley 1956 primer)

Hard rules honored:
    * No PHI — samples drawn from priors in `dimensions.toml` only.
    * Base defaults to `math.e` (nats); pass `base=2` for bits.
    * Robust to zero-probability events (treat 0*log0 := 0).
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from scipy import special

from brain.belief.schema import DistributionSpec


# ---------------------------------------------------------------------------
# Core histogram + discrete entropy
# ---------------------------------------------------------------------------
def shannon_entropy_continuous(
    samples: np.ndarray,
    *,
    base: float = math.e,
    bins: int = 64,
) -> float:
    """Histogram-based differential entropy estimator.

    Uses a fixed number of bins on the empirical range. Returns entropy in
    nats by default (`base=e`), bits when `base=2`.

    Edge cases:
        - Empty samples -> 0.0
        - Single-value samples (zero variance) -> 0.0 (degenerate -> -inf in
          the limit, but we clamp at 0 for downstream EIG arithmetic).
    """
    arr = np.asarray(samples, dtype=float).ravel()
    if arr.size == 0:
        return 0.0
    if np.allclose(arr.min(), arr.max()):
        return 0.0

    hist, edges = np.histogram(arr, bins=bins, density=True)
    widths = np.diff(edges)
    probs = hist * widths  # discrete prob mass per bin
    probs = probs[probs > 0]
    if probs.size == 0:
        return 0.0
    # Differential entropy: H = -Σ p_i * log(p_i / Δx_i). We rebuild from
    # density to avoid bin-width bias.
    h = 0.0
    for d, w in zip(hist, widths):
        if d > 0:
            h -= d * w * math.log(d) / math.log(base)
    return float(h)


def shannon_entropy_discrete(
    probs: np.ndarray,
    *,
    base: float = math.e,
) -> float:
    """Discrete entropy `-Σ p log p`. Robust to zero probabilities."""
    arr = np.asarray(probs, dtype=float).ravel()
    if arr.size == 0:
        return 0.0
    total = arr.sum()
    if total <= 0:
        return 0.0
    arr = arr / total  # normalise defensively
    h = 0.0
    for p in arr:
        if p > 0:
            h -= p * math.log(p) / math.log(base)
    return float(h)


# ---------------------------------------------------------------------------
# Closed-form analytical entropies
# ---------------------------------------------------------------------------
def analytical_entropy_beta(alpha: float, beta_param: float) -> float:
    """Beta(α, β) differential entropy in nats.

    H = log B(α,β) - (α-1) ψ(α) - (β-1) ψ(β) + (α+β-2) ψ(α+β)
    """
    a = float(alpha)
    b = float(beta_param)
    log_beta = special.betaln(a, b)
    h = (
        log_beta
        - (a - 1.0) * special.digamma(a)
        - (b - 1.0) * special.digamma(b)
        + (a + b - 2.0) * special.digamma(a + b)
    )
    return float(h)


def analytical_entropy_normal(mu: float, sigma: float) -> float:
    """Normal(μ, σ²) differential entropy in nats: 0.5 * log(2πeσ²)."""
    s = float(sigma)
    if s <= 0:
        return 0.0
    return float(0.5 * math.log(2.0 * math.pi * math.e * s * s))


def analytical_entropy_gamma(alpha: float, beta_param: float) -> float:
    """Gamma(α, β) (rate parameterisation) differential entropy in nats.

    H = α - log β + log Γ(α) + (1-α) ψ(α)
    """
    a = float(alpha)
    b = float(beta_param)
    return float(
        a - math.log(b) + special.gammaln(a) + (1.0 - a) * special.digamma(a)
    )


def analytical_entropy_poisson(mu: float) -> float:
    """Poisson(μ) discrete entropy in nats.

    Closed form is an infinite sum; for μ > 5 use the asymptotic
    `0.5 * log(2πeμ)`. Otherwise sum exactly over support
    {0 .. 2*ceil(μ) + 10}.
    """
    m = float(mu)
    if m <= 0:
        return 0.0
    if m > 5.0:
        return float(0.5 * math.log(2.0 * math.pi * math.e * m))
    # Numerical sum over a generous prefix of the support
    upper = int(2 * math.ceil(m) + 10)
    h = 0.0
    log_mu = math.log(m)
    for k in range(0, upper + 1):
        log_p = k * log_mu - m - special.gammaln(k + 1)
        p = math.exp(log_p)
        if p > 0:
            h -= p * log_p
    return float(h)


def analytical_entropy_bernoulli(p: float) -> float:
    """Bernoulli(p) discrete entropy in nats."""
    q = float(p)
    if q <= 0.0 or q >= 1.0:
        return 0.0
    return float(-(q * math.log(q) + (1.0 - q) * math.log(1.0 - q)))


# ---------------------------------------------------------------------------
# Dispatch — DistributionSpec -> H
# ---------------------------------------------------------------------------
def _sample_from_spec(spec: DistributionSpec, n: int, rng: np.random.Generator) -> np.ndarray:
    """Numerical fallback sampler for non-conjugate dispatch."""
    p = spec.params
    kind = spec.kind
    if kind == "beta":
        return rng.beta(p["alpha"], p["beta"], size=n)
    if kind == "normal":
        return rng.normal(p["mu"], p["sigma"], size=n)
    if kind == "poisson":
        return rng.poisson(p["mu"], size=n).astype(float)
    if kind == "gamma":
        # numpy gamma: shape (alpha), scale = 1/rate(beta)
        return rng.gamma(p["alpha"], 1.0 / p["beta"], size=n)
    if kind == "bernoulli":
        return rng.binomial(1, p["p"], size=n).astype(float)
    if kind == "exp_decay":
        # exponential with rate `lam` -> mean 1/lam
        return rng.exponential(1.0 / p["lam"], size=n)
    if kind == "vector":
        mu_vec = np.asarray(p["mu_vec"], dtype=float)
        sigma_vec = np.asarray(p["sigma_vec"], dtype=float)
        # Independent normals over the vector -> flatten before histogramming
        return rng.normal(mu_vec, sigma_vec, size=(n, mu_vec.size)).ravel()
    if kind == "categorical":
        probs = np.asarray(p["probs"], dtype=float)
        probs = probs / probs.sum()
        return rng.choice(len(probs), size=n, p=probs).astype(float)
    raise ValueError(f"unsupported distribution kind for sampling: {kind!r}")


def entropy_for_distribution_spec(
    spec: DistributionSpec,
    *,
    n_simulations: int = 1000,
    rng: Optional[np.random.Generator] = None,
) -> float:
    """Return entropy in nats for `spec`. Analytical when possible."""
    p = spec.params
    kind = spec.kind
    if kind == "beta":
        return analytical_entropy_beta(p["alpha"], p["beta"])
    if kind == "normal":
        return analytical_entropy_normal(p["mu"], p["sigma"])
    if kind == "gamma":
        return analytical_entropy_gamma(p["alpha"], p["beta"])
    if kind == "poisson":
        return analytical_entropy_poisson(p["mu"])
    if kind == "bernoulli":
        return analytical_entropy_bernoulli(p["p"])
    if kind == "categorical":
        return shannon_entropy_discrete(np.asarray(p["probs"], dtype=float))
    # Numerical fallback (vector, exp_decay)
    if rng is None:
        rng = np.random.default_rng(7)
    samples = _sample_from_spec(spec, n_simulations, rng)
    return shannon_entropy_continuous(samples)


__all__ = [
    "shannon_entropy_continuous",
    "shannon_entropy_discrete",
    "analytical_entropy_beta",
    "analytical_entropy_normal",
    "analytical_entropy_gamma",
    "analytical_entropy_poisson",
    "analytical_entropy_bernoulli",
    "entropy_for_distribution_spec",
]
