"""Phase 7.0 Days 13-14 — Central Bayesian update() API.

Wires schema (priors) + likelihoods (data-generating) + persistence (DB)
into a single function: BeliefEvidence -> sample posterior -> PosteriorDelta.

Idempotent: same `evidence_hash` returns the existing trace's delta without
re-sampling.

Pipeline:
    1. Compute / verify evidence_hash; probe persistence for existing row.
    2. Look up BeliefDimension (id-keyed, injectable for tests).
    3. validate_evidence_value(distribution, value) — fails fast on bad shape.
    4. Open `pm.Model()`:
         - prior = DistributionSpec(...).to_pm("p")
         - obs  = LIKELIHOOD_REGISTRY[distribution](prior, evidence.value)
         - idata = pm.sample(...)
    5. ArviZ summary -> posterior_mean, sd, hdi_3, hdi_97, rhat, ess_bulk.
    6. Convergence gate: rhat < 1.01 AND ess_bulk > 400 (strict mode).
    7. Analytical prior mean + KL-divergence estimate (histogram-based).
    8. Write evidence (idempotent on hash) + trace (idempotent on
       (dim_id, evidence_id)) — both no-ops on cache hit.
    9. Return PosteriorDelta.

Hard rules honored (from .claude/agents/v7-bayes.md):
    - random_seed=7 default in every sample() call.
    - rhat < 1.01 AND ess_bulk > 400 enforced HERE (not at likelihood layer).
    - No PHI in module; evidence flows in via BeliefEvidence.value.
    - Idempotency keyed by evidence_hash UNIQUE.
"""

from __future__ import annotations

import math
import time
from datetime import datetime
from typing import Callable, Optional

import numpy as np
import pymc as pm
import arviz as az
from pydantic import BaseModel, ConfigDict

from brain.belief.persistence import (
    BeliefDimension,
    BeliefEvidence,
    BeliefTrace,
    get_dimension_by_id,
    get_evidence_by_hash,
    latest_trace,
    write_evidence,
    write_trace,
)
from brain.belief.schema import get_dimension_spec
from brain.belief.likelihoods import (
    get_likelihood,
    validate_evidence_value,
)


# ---------------------------------------------------------------------------
# Convergence + sampling defaults (Phase 7.0 gate)
# ---------------------------------------------------------------------------
DEFAULT_DRAWS = 2000
DEFAULT_TUNE = 1000
DEFAULT_CHAINS = 2
DEFAULT_CORES = 1  # pure-Python sampler; single-core safer on Windows
DEFAULT_RANDOM_SEED = 7
STRICT_RHAT_MAX = 1.01
STRICT_ESS_BULK_MIN = 400.0


# Distribution kinds whose posterior summary is naturally univariate AND
# whose prior we know how to evaluate analytically — they get a KL estimate.
_KL_SUPPORTED_KINDS = frozenset({"beta", "normal", "poisson", "gamma", "bernoulli"})


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class ConvergenceError(RuntimeError):
    """Posterior sampler did not converge — rhat or ess_bulk gate failed."""


class BeliefWithoutEvidenceError(ValueError):
    """Phase 7.5 Rule #8 — posterior update requires at least one evidence row.

    Anthropic Constitutional AI pattern: the rule lives at the entry of
    update() so a future code path cannot accidentally call update(None)
    and silently advance the posterior with no informative input.
    """


# ---------------------------------------------------------------------------
# PosteriorDelta — return value of update()
# ---------------------------------------------------------------------------
class PosteriorDelta(BaseModel):
    """Summary of what changed when a single evidence row was applied."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    dimension_name: str
    evidence_id: str
    trace_id: str
    prior_mean: float
    posterior_mean: float
    posterior_sd: float
    hdi_3: float
    hdi_97: float
    mean_shift: float
    abs_mean_shift: float
    kl_divergence_estimate: Optional[float] = None
    n_samples: int
    rhat: float
    ess_bulk: float
    sampling_seconds: float
    convergence_ok: bool = True
    idempotent_hit: bool = False
    cached_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Analytical prior-mean helpers
# ---------------------------------------------------------------------------
def _compute_prior_mean(dim: BeliefDimension) -> float:
    """Analytical prior mean per distribution kind.

    Returns float (NaN for kinds without a univariate scalar interpretation).
    """
    kind = dim.distribution
    p = dim.prior_params
    if kind == "beta":
        return float(p["alpha"]) / (float(p["alpha"]) + float(p["beta"]))
    if kind == "normal":
        return float(p["mu"])
    if kind == "poisson":
        return float(p["mu"])
    if kind == "gamma":
        return float(p["alpha"]) / float(p["beta"])
    if kind == "bernoulli":
        return float(p["p"])
    if kind == "categorical":
        probs = list(p["probs"])
        return float(sum(i * pi for i, pi in enumerate(probs)))
    if kind == "vector":
        mu_vec = list(p.get("mu_vec", []))
        return float(mu_vec[0]) if mu_vec else float("nan")
    if kind == "exp_decay":
        # Resource-fraction at a 365-day horizon (Day 10 convention).
        lam = float(p["lam"])
        return float(math.exp(-lam * 365.0))
    return float("nan")


def _prior_pdf(dim: BeliefDimension, x: np.ndarray) -> Optional[np.ndarray]:
    """Evaluate prior PDF on an array of points. Returns None for unsupported.

    Used by _estimate_kl_divergence for histogram-based KL.
    """
    from scipy import stats  # local import; keeps top-level import set small

    kind = dim.distribution
    p = dim.prior_params
    try:
        if kind == "beta":
            return stats.beta.pdf(x, float(p["alpha"]), float(p["beta"]))
        if kind == "normal":
            return stats.norm.pdf(x, loc=float(p["mu"]), scale=float(p["sigma"]))
        if kind == "poisson":
            # discrete: use pmf
            return stats.poisson.pmf(np.round(x).astype(int), mu=float(p["mu"]))
        if kind == "gamma":
            # PyMC Gamma uses (alpha, beta=rate). scipy.gamma uses scale=1/rate.
            return stats.gamma.pdf(x, a=float(p["alpha"]), scale=1.0 / float(p["beta"]))
        if kind == "bernoulli":
            # Discrete on {0, 1}
            pp = float(p["p"])
            return np.where(
                np.isclose(x, 1.0),
                pp,
                np.where(np.isclose(x, 0.0), 1.0 - pp, 0.0),
            )
    except Exception:
        return None
    return None


def _estimate_kl_divergence(
    posterior_samples: np.ndarray,
    dim: BeliefDimension,
) -> Optional[float]:
    """Crude histogram-based KL(posterior || prior).

    For univariate continuous kinds, bin posterior samples, evaluate the
    analytical prior PDF at bin centers, and compute discrete KL.

    Returns None for:
      - vector / exp_decay / categorical (deferred)
      - degenerate posterior (all samples identical)
      - any numerical failure
    """
    kind = dim.distribution
    if kind not in _KL_SUPPORTED_KINDS:
        return None

    samples = np.asarray(posterior_samples, dtype=float).ravel()
    if samples.size < 50:
        return None

    try:
        if kind == "bernoulli":
            # Discrete on {0, 1}
            p_post_1 = float((samples >= 0.5).mean())
            p_post_0 = 1.0 - p_post_1
            p_prior_1 = float(dim.prior_params["p"])
            p_prior_0 = 1.0 - p_prior_1
            kl = 0.0
            for q, pp in [(p_post_0, p_prior_0), (p_post_1, p_prior_1)]:
                if q > 0 and pp > 0:
                    kl += q * math.log(q / pp)
            return float(kl) if math.isfinite(kl) else None

        if kind == "poisson":
            # Discrete histogram over observed integer values.
            ints = np.round(samples).astype(int)
            ints = ints[ints >= 0]
            if ints.size == 0:
                return None
            max_k = int(ints.max()) + 1
            counts = np.bincount(ints, minlength=max_k + 1).astype(float)
            q_probs = counts / counts.sum()
            xs = np.arange(q_probs.size)
            p_probs = _prior_pdf(dim, xs.astype(float))
            if p_probs is None:
                return None
            mask = (q_probs > 0) & (p_probs > 0)
            if not mask.any():
                return None
            kl = float((q_probs[mask] * np.log(q_probs[mask] / p_probs[mask])).sum())
            return kl if math.isfinite(kl) else None

        # Continuous: beta / normal / gamma — histogram with ~40 bins.
        lo = float(samples.min())
        hi = float(samples.max())
        if hi - lo < 1e-9:
            return None
        n_bins = 40
        counts, edges = np.histogram(samples, bins=n_bins, range=(lo, hi))
        widths = np.diff(edges)
        if widths.sum() <= 0:
            return None
        q_density = counts.astype(float) / (counts.sum() * widths)
        centers = 0.5 * (edges[:-1] + edges[1:])
        p_density = _prior_pdf(dim, centers)
        if p_density is None:
            return None
        mask = (q_density > 0) & (p_density > 0)
        if not mask.any():
            return None
        # KL(q || p) ≈ Σ q(x) log(q(x)/p(x)) * Δx
        kl = float(
            (
                q_density[mask]
                * np.log(q_density[mask] / p_density[mask])
                * widths[mask]
            ).sum()
        )
        return kl if math.isfinite(kl) else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main API: update()
# ---------------------------------------------------------------------------
def update(
    evidence: BeliefEvidence,
    *,
    draws: int = DEFAULT_DRAWS,
    tune: int = DEFAULT_TUNE,
    chains: int = DEFAULT_CHAINS,
    cores: int = DEFAULT_CORES,
    random_seed: int = DEFAULT_RANDOM_SEED,
    strict: bool = True,
    dimension_loader: Optional[Callable[[int], Optional[BeliefDimension]]] = None,
    evidence_lookup: Optional[Callable[[str], Optional[BeliefEvidence]]] = None,
    trace_writer: Optional[Callable[[BeliefTrace], str]] = None,
    evidence_writer: Optional[Callable[[BeliefEvidence], str]] = None,
    latest_trace_lookup: Optional[Callable[[int], Optional[BeliefTrace]]] = None,
) -> PosteriorDelta:
    """Apply a single evidence row to the belief state.

    Args:
        evidence: BeliefEvidence row to apply. Its `evidence_hash` field MUST
            be populated (call `compute_evidence_hash` first).
        draws / tune / chains / cores / random_seed: PyMC sampler knobs.
        strict: If True (default), raise ConvergenceError when rhat > 1.01 OR
            ess_bulk < 400. If False, persist anyway with convergence_ok=False.
        dimension_loader: Optional override of `get_dimension_by_id` (tests).
        evidence_lookup: Optional override of `get_evidence_by_hash` (tests).
        trace_writer / evidence_writer / latest_trace_lookup: Optional overrides
            for the four persistence calls (tests inject in-memory stand-ins).

    Returns:
        PosteriorDelta summary (with idempotent_hit=True if cache hit).

    Raises:
        KeyError: distribution kind not in registry, or evidence.value missing
            required keys for the dimension's distribution.
        ValueError: domain validity failure inside the likelihood builder
            (e.g., Beta k > n, Poisson observation < 0).
        ConvergenceError: sampler didn't converge and strict=True.
        RuntimeError: dimension lookup returned None.
    """
    # Phase 7.5 Rule #8 physical enforcement — Constitutional AI pattern.
    # update() refuses any null evidence at the very top so a downstream
    # code path cannot silently advance the posterior without an
    # informative input. The check fires BEFORE injection resolution so
    # tests that pass None deliberately hit this branch.
    if evidence is None:
        raise BeliefWithoutEvidenceError(
            "Phase 7.5 Rule #8: posterior update requires at least one "
            "evidence item. Pass a BeliefEvidence instance — empty/null "
            "evidence is forbidden."
        )

    # Resolve injection points to defaults.
    _load_dim = dimension_loader or get_dimension_by_id
    _lookup_evidence = evidence_lookup or get_evidence_by_hash
    _write_trace = trace_writer or write_trace
    _write_evidence = evidence_writer or write_evidence
    _latest_trace = latest_trace_lookup or latest_trace

    # ---- Step 0: ensure evidence_hash is present -----------------------------
    if not evidence.evidence_hash:
        raise ValueError(
            "evidence.evidence_hash is required — call compute_evidence_hash() first"
        )

    # ---- Step 1: idempotency probe -------------------------------------------
    existing_ev = _lookup_evidence(evidence.evidence_hash)
    if existing_ev is not None and existing_ev.id:
        # Look for an existing trace for this dimension.
        cached_trace = _latest_trace(evidence.dimension_id)
        if cached_trace is not None and cached_trace.evidence_id == existing_ev.id:
            # Cache hit — load dim for naming + analytical prior, then short-circuit.
            dim = _load_dim(evidence.dimension_id)
            if dim is None:
                raise RuntimeError(
                    f"dimension id={evidence.dimension_id} not found (cache hit)"
                )
            prior_mean = _compute_prior_mean(dim)
            mean_shift = cached_trace.posterior_mean - prior_mean
            return PosteriorDelta(
                dimension_name=dim.name,
                evidence_id=str(existing_ev.id),
                trace_id=str(cached_trace.id) if cached_trace.id else "",
                prior_mean=prior_mean,
                posterior_mean=cached_trace.posterior_mean,
                posterior_sd=cached_trace.posterior_sd,
                hdi_3=cached_trace.hdi_3,
                hdi_97=cached_trace.hdi_97,
                mean_shift=mean_shift,
                abs_mean_shift=abs(mean_shift),
                kl_divergence_estimate=None,  # not stored; would need re-derive
                n_samples=cached_trace.n_samples,
                rhat=cached_trace.rhat,
                ess_bulk=cached_trace.ess_bulk,
                sampling_seconds=0.0,
                convergence_ok=(
                    cached_trace.rhat < STRICT_RHAT_MAX
                    and cached_trace.ess_bulk > STRICT_ESS_BULK_MIN
                ),
                idempotent_hit=True,
                cached_at=cached_trace.created_at,
            )

    # ---- Step 2: load dimension ---------------------------------------------
    dim = _load_dim(evidence.dimension_id)
    if dim is None:
        raise RuntimeError(
            f"dimension id={evidence.dimension_id} not found in persistence"
        )

    # ---- Step 3: validate evidence shape (KeyError fast-fail) ---------------
    validate_evidence_value(dim.distribution, evidence.value)
    likelihood_builder = get_likelihood(dim.distribution)  # KeyError if unknown

    # ---- Step 4: build PyMC model + sample ----------------------------------
    spec = get_dimension_spec(dim)
    t0 = time.perf_counter()
    with pm.Model():
        prior = spec.to_pm("p")
        # Likelihood raises ValueError on domain violations (k>n, etc.) — propagate.
        likelihood_builder(prior, evidence.value)
        idata = pm.sample(
            draws=draws,
            tune=tune,
            chains=chains,
            cores=cores,
            random_seed=random_seed,
            progressbar=False,
            return_inferencedata=True,
        )
    sampling_seconds = time.perf_counter() - t0

    # ---- Step 5: ArviZ summary ----------------------------------------------
    # ArviZ column names differ across releases:
    #   - older builds: "hdi_3%" / "hdi_97%" (94% HDI)
    #   - newer builds (arviz-stats split): "eti89_lb" / "eti89_ub" (89% ETI)
    # Our PosteriorDelta fields are named hdi_3 / hdi_97 for backward
    # compatibility with the persistence schema; the actual interval width is
    # whatever the installed ArviZ default emits.
    summary = az.summary(idata, var_names=["p"])
    cols = list(summary.columns)

    def _pick(*candidates: str) -> str:
        for c in candidates:
            if c in cols:
                return c
        raise KeyError(
            f"None of {candidates!r} present in arviz summary; columns: {cols}"
        )

    lo_col = _pick("hdi_3%", "eti89_lb", "hdi_2.5%")
    hi_col = _pick("hdi_97%", "eti89_ub", "hdi_97.5%")
    rhat_col = _pick("r_hat", "rhat")
    ess_col = _pick("ess_bulk")

    # For multi-dim ("vector"), summary has one row per index; collapse to first.
    posterior_mean = float(summary["mean"].iloc[0])
    posterior_sd = float(summary["sd"].iloc[0])
    hdi_3 = float(summary[lo_col].iloc[0])
    hdi_97 = float(summary[hi_col].iloc[0])
    rhat = float(summary[rhat_col].iloc[0])
    ess_bulk = float(summary[ess_col].iloc[0])
    n_samples = int(draws * chains)

    # ---- Step 6: convergence gate -------------------------------------------
    convergence_ok = (
        math.isfinite(rhat)
        and math.isfinite(ess_bulk)
        and rhat < STRICT_RHAT_MAX
        and ess_bulk > STRICT_ESS_BULK_MIN
    )
    if strict and not convergence_ok:
        raise ConvergenceError(
            f"Sampler did not converge for dimension {dim.name!r}: "
            f"rhat={rhat:.4f} (max={STRICT_RHAT_MAX}), "
            f"ess_bulk={ess_bulk:.1f} (min={STRICT_ESS_BULK_MIN}). "
            f"Increase tune steps before increasing draws."
        )

    # ---- Step 7: prior-vs-posterior shift -----------------------------------
    prior_mean = _compute_prior_mean(dim)
    mean_shift = posterior_mean - prior_mean
    abs_mean_shift = abs(mean_shift)

    # ---- Step 8: KL divergence (best-effort) --------------------------------
    posterior_samples = idata.posterior["p"].values  # type: ignore[index]
    # Flatten chain × draw × (vector dim) -> 1D for univariate kinds.
    flat = np.asarray(posterior_samples).reshape(-1)
    if dim.distribution == "vector" and posterior_samples.ndim >= 3:
        # vector: KL not computed (returns None)
        kl_est: Optional[float] = None
    else:
        kl_est = _estimate_kl_divergence(flat, dim)

    # ---- Step 9: persist evidence + trace -----------------------------------
    evidence_id = _write_evidence(evidence)
    trace = BeliefTrace(
        dimension_id=dim.id if dim.id is not None else evidence.dimension_id,
        evidence_id=evidence_id,
        posterior_mean=posterior_mean,
        posterior_sd=posterior_sd,
        hdi_3=hdi_3,
        hdi_97=hdi_97,
        n_samples=n_samples,
        rhat=rhat,
        ess_bulk=ess_bulk,
        arviz_summary={
            "mean": posterior_mean,
            "sd": posterior_sd,
            "hdi_3%": hdi_3,
            "hdi_97%": hdi_97,
            "r_hat": rhat,
            "ess_bulk": ess_bulk,
            "convergence_ok": convergence_ok,
        },
    )
    trace_id = _write_trace(trace)

    # ---- Step 10: return delta ----------------------------------------------
    return PosteriorDelta(
        dimension_name=dim.name,
        evidence_id=evidence_id,
        trace_id=trace_id,
        prior_mean=prior_mean,
        posterior_mean=posterior_mean,
        posterior_sd=posterior_sd,
        hdi_3=hdi_3,
        hdi_97=hdi_97,
        mean_shift=mean_shift,
        abs_mean_shift=abs_mean_shift,
        kl_divergence_estimate=kl_est,
        n_samples=n_samples,
        rhat=rhat,
        ess_bulk=ess_bulk,
        sampling_seconds=sampling_seconds,
        convergence_ok=convergence_ok,
        idempotent_hit=False,
        cached_at=None,
    )


__all__ = [
    "DEFAULT_DRAWS",
    "DEFAULT_TUNE",
    "DEFAULT_CHAINS",
    "DEFAULT_CORES",
    "DEFAULT_RANDOM_SEED",
    "STRICT_RHAT_MAX",
    "STRICT_ESS_BULK_MIN",
    "ConvergenceError",
    "PosteriorDelta",
    "update",
    "_compute_prior_mean",
    "_estimate_kl_divergence",
]
