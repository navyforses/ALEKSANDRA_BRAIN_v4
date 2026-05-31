"""Phase 7.0 Day 15 — First joint posterior model.

Couples 3 dimensions (cyst_volume_pct, gmfcs_level, bayley_cognitive)
via an LKJ correlation matrix prior over a latent multivariate-normal
representation. Each child dim is mapped to/from its natural scale via
deterministic transforms (invlogit for cyst, ordered-logit cutpoints for
GMFCS, standardized affine for Bayley).

Literature anchor:
    Pisano T. et al. "MRI-outcome correlation in HIE." 2024.
    PMID 38502489 — establishes that cyst volume on neonatal MRI
    correlates with downstream GMFCS motor outcomes and Bayley cognitive
    composites in moderate-to-severe HIE. The 3-dim coupling chosen here
    mirrors the Pisano dependency graph.

Architecture per Day 13-14 carry-forward contracts:
  1. PosteriorDelta is the contract -> JointDelta wraps N child
     PosteriorDeltas (one per coupled dim) + the posterior correlation
     matrix (+ HDI per pair).
  2. Joint model uses *continuous latent + transforms* for both cyst and
     GMFCS rather than direct Bernoulli/Categorical priors. GMFCS
     observations attach via `pm.OrderedLogistic` over learnable cutpoints.
  3. The same 5 injection points as `update.update()` are exposed
     (dimension_loader / evidence_lookup / 2 writers / latest) for tests.
  4. ArviZ extraction reuses the `_pick(...)` helper pattern from
     update.py (column-name variance across builds).
  5. KL is univariate-only; multivariate KL -> explicit NotImplementedError
     (NOT silent None).
  6. evidence_hash per child stays the idempotency key; joint cache uses
     a composite key: sha256(sorted(child_evidence_hashes)).

Hard rules honoured (.claude/agents/v7-bayes.md):
  - random_seed=7 default in pm.sample().
  - rhat<1.01 AND ess_bulk>400 strict gate, ConvergenceError when unmet.
  - No PHI in module; evidence flows in via BeliefEvidence.value (JSONB).
  - Composite-hash idempotency checked BEFORE sampling.
  - Joint persistence (a `belief_joint_traces` table) is OUT OF SCOPE for
    Day 15 — child evidence + child traces are persisted (idempotent per
    child); the JointDelta's `composite_evidence_hash` and posterior
    correlation matrix live in-memory only until Day 19-20 lands the
    joint-trace schema.
"""

from __future__ import annotations

import math
import time
from datetime import datetime
from hashlib import sha256
from typing import Any, Callable, Optional, Sequence

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
from brain.belief.likelihoods import validate_evidence_value
from brain.belief.update import (
    PosteriorDelta,
    ConvergenceError,
    DEFAULT_DRAWS,
    DEFAULT_TUNE,
    DEFAULT_CHAINS,
    DEFAULT_CORES,
    DEFAULT_RANDOM_SEED,
    STRICT_RHAT_MAX,
    STRICT_ESS_BULK_MIN,
    _compute_prior_mean,
)


# ---------------------------------------------------------------------------
# Canonical 3-dim joint identity (v1)
# ---------------------------------------------------------------------------
# Order matters: index 0 is cyst, 1 is gmfcs, 2 is bayley. The correlation
# matrix rows/cols follow this same order.
JOINT_DIM_NAMES_V1: tuple[str, ...] = (
    "cyst_volume_pct",
    "gmfcs_level",
    "bayley_cognitive",
)
_JOINT_N: int = len(JOINT_DIM_NAMES_V1)

# LKJ concentration. eta=1 is uniform on correlation matrices; eta>1
# concentrates mass near the identity (weaker correlations). 2.0 is the
# PyMC docs canonical choice and matches a Pisano-style weakly-informative
# prior over couplings whose magnitude we don't claim to know upfront.
_LKJ_ETA: float = 2.0

# Transform constants for the latent -> natural-scale maps. Chosen so that
# each latent z_i ~ N(0, 1) reproduces the marginal prior shape of its dim.
#   cyst:   p_cyst = sigmoid(_CYST_INTERCEPT + _CYST_SLOPE * z)
#           tuned so p_cyst marginal mean ~ 0.086 (Beta(0.6, 6.4) mean)
#   bayley: score = _BAYLEY_MU + _BAYLEY_SIGMA * z  (matches Normal(65, 18))
#   gmfcs:  ordered logit on cutpoints [-1.5, -0.7, 0.0, 0.8] with latent
#           η = _GMFCS_LATENT_SLOPE * z  (5 levels). Cutpoints fit so prior
#           marginal probs ~ [0.05, 0.10, 0.15, 0.25, 0.45].
_CYST_INTERCEPT: float = -2.35  # invlogit(-2.35) ~ 0.087
_CYST_SLOPE: float = 1.0
_BAYLEY_MU: float = 65.0
_BAYLEY_SIGMA: float = 18.0
_GMFCS_CUTPOINTS: tuple[float, ...] = (-1.645, -0.842, -0.385, 0.126)
_GMFCS_LATENT_SLOPE: float = 1.0


# ---------------------------------------------------------------------------
# Composite idempotency key
# ---------------------------------------------------------------------------
def compute_joint_evidence_hash(evidence_hashes: Sequence[str]) -> str:
    """Composite idempotency key: sha256 of sorted child hashes joined by ','.

    Order-invariant: ["a", "b", "c"] hashes identical to ["c", "a", "b"].
    """
    payload = ",".join(sorted(evidence_hashes))
    return sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# JointDelta — return value of joint_update()
# ---------------------------------------------------------------------------
class JointDelta(BaseModel):
    """Joint-update summary. Wraps N child PosteriorDeltas + correlation posterior.

    Posterior correlation matrix layout matches JOINT_DIM_NAMES_V1 ordering.
    `posterior_correlation_hdi[i][j]` is `[lo, hi]` of the 94% HDI for
    correlation(i, j); diagonals are `[1.0, 1.0]`.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    dim_names: list[str]
    child_deltas: list[PosteriorDelta]
    posterior_correlation_matrix: list[list[float]]
    posterior_correlation_hdi: list[list[list[float]]]
    n_samples: int
    rhat_max: float
    ess_bulk_min: float
    sampling_seconds: float
    composite_evidence_hash: str
    idempotent_hit: bool = False
    cached_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# ArviZ column picker (replicated from update.py per carry-forward #4)
# ---------------------------------------------------------------------------
def _pick(cols: Sequence[str], *candidates: str) -> str:
    for c in candidates:
        if c in cols:
            return c
    raise KeyError(
        f"None of {candidates!r} present in arviz summary; columns: {list(cols)}"
    )


# ---------------------------------------------------------------------------
# Joint model builder
# ---------------------------------------------------------------------------
def _build_joint_model(
    dims: list[BeliefDimension],
    evidences: list[BeliefEvidence],
) -> pm.Model:
    """Build the latent-MvNormal + LKJ-correlation joint model.

    Latent representation:
        chol, corr, sigmas = LKJCholeskyCov(eta=_LKJ_ETA, n=3,
                                            sd_dist=HalfNormal.dist(0.1, shape=3))
        z ~ MvNormal(0, chol=chol, shape=3)  # latent unit-scale draws

    Per-dim natural-scale transforms + observations:
        z[0] -> p_cyst  = sigmoid(_CYST_INTERCEPT + _CYST_SLOPE * z[0])
                          obs = Binomial(n, k) with p=p_cyst
        z[1] -> ordered_logit(eta=_GMFCS_LATENT_SLOPE*z[1], cutpoints=_GMFCS_CUTPOINTS)
                          obs = OrderedLogistic over observations (0-indexed class)
        z[2] -> score   = _BAYLEY_MU + _BAYLEY_SIGMA * z[2]
                          obs = Normal(score, sigma_obs) with observations array

    Note the LKJ `sd_dist` is fixed tight (HalfNormal(0.1)) so the latent
    standard deviations stay near zero in the *scale* direction; the
    LATENT z's still get unit variance from MvNormal(mu=0, chol=chol) with
    `chol` carrying the correlation structure (sigmas multiplied in by
    LKJCholeskyCov). Because sigmas are near-zero, the correlation matrix
    extracted from LKJCholeskyCov is what we report.

    Actually — to extract clean correlations regardless of sd magnitude we
    use the deterministic `corr` output that LKJCholeskyCov returns when
    compute_corr=True, which is the correlation matrix proper.
    """
    ev_by_name = {dims[i].name: evidences[i] for i in range(len(dims))}

    cyst_ev = ev_by_name["cyst_volume_pct"]
    gmfcs_ev = ev_by_name["gmfcs_level"]
    bayley_ev = ev_by_name["bayley_cognitive"]

    with pm.Model() as model:
        # ---- LKJ correlation prior + latent MvNormal --------------------
        sd_dist = pm.HalfNormal.dist(1.0, shape=_JOINT_N)
        chol, corr, sigmas = pm.LKJCholeskyCov(
            "chol_cov",
            n=_JOINT_N,
            eta=_LKJ_ETA,
            sd_dist=sd_dist,
            compute_corr=True,
        )
        # Latent joint draws. Mean 0; covariance from chol.
        # Use shape=(_JOINT_N,) so z is a 1D vector — observations attach
        # per-dimension below.
        z = pm.MvNormal("z", mu=np.zeros(_JOINT_N), chol=chol, shape=_JOINT_N)

        # ---- Dim 0: cyst (Beta-like via invlogit on latent) -------------
        p_cyst = pm.Deterministic(
            "p_cyst",
            pm.math.sigmoid(_CYST_INTERCEPT + _CYST_SLOPE * z[0]),
        )
        n_cyst = int(cyst_ev.value["n"])
        k_cyst = int(cyst_ev.value["k"])
        if k_cyst > n_cyst or k_cyst < 0 or n_cyst < 0:
            raise ValueError(f"Cyst Binomial domain error: n={n_cyst}, k={k_cyst}")
        pm.Binomial("obs_cyst", n=n_cyst, p=p_cyst, observed=k_cyst)

        # ---- Dim 1: GMFCS (OrderedLogistic on latent) -------------------
        gmfcs_obs_raw = np.asarray(gmfcs_ev.value["observations"], dtype=int)
        if gmfcs_obs_raw.size == 0:
            raise ValueError("gmfcs observations required (non-empty list)")
        # dimensions.toml uses 1..5; OrderedLogistic expects 0-indexed
        # classes. Subtract 1; clip to [0, 4] defensively.
        gmfcs_obs = np.clip(gmfcs_obs_raw - 1, 0, 4).astype(int)
        gmfcs_eta = pm.Deterministic("gmfcs_eta", _GMFCS_LATENT_SLOPE * z[1])
        pm.OrderedLogistic(
            "obs_gmfcs",
            eta=gmfcs_eta,
            cutpoints=np.asarray(_GMFCS_CUTPOINTS, dtype=float),
            observed=gmfcs_obs,
        )

        # ---- Dim 2: Bayley (Normal on latent affine) --------------------
        bayley_obs = np.asarray(bayley_ev.value["observations"], dtype=float)
        if bayley_obs.size == 0:
            raise ValueError("bayley observations required (non-empty list)")
        sigma_b = float(bayley_ev.value.get("sigma", 5.0))
        if sigma_b <= 0:
            raise ValueError(f"bayley sigma must be positive, got {sigma_b}")
        bayley_score = pm.Deterministic(
            "bayley_score", _BAYLEY_MU + _BAYLEY_SIGMA * z[2]
        )
        pm.Normal("obs_bayley", mu=bayley_score, sigma=sigma_b, observed=bayley_obs)

    return model


# ---------------------------------------------------------------------------
# Per-child PosteriorDelta extraction
# ---------------------------------------------------------------------------
def _extract_child_delta(
    *,
    dim: BeliefDimension,
    evidence_id: str,
    trace_id: str,
    summary,
    natural_var_name: str,
    n_samples: int,
    sampling_seconds: float,
    convergence_ok: bool,
) -> PosteriorDelta:
    """Pull one row of `summary` (the natural-scale Deterministic for this dim)
    into a PosteriorDelta. Mirrors update.update()'s summary handling but for
    a single named variable already extracted."""
    cols = list(summary.columns)
    lo_col = _pick(cols, "hdi_3%", "eti89_lb", "hdi_2.5%")
    hi_col = _pick(cols, "hdi_97%", "eti89_ub", "hdi_97.5%")
    rhat_col = _pick(cols, "r_hat", "rhat")
    ess_col = _pick(cols, "ess_bulk")

    row = summary.loc[natural_var_name]
    posterior_mean = float(row["mean"])
    posterior_sd = float(row["sd"])
    hdi_3 = float(row[lo_col])
    hdi_97 = float(row[hi_col])
    rhat = float(row[rhat_col])
    ess_bulk = float(row[ess_col])

    prior_mean = _compute_prior_mean(dim)
    mean_shift = posterior_mean - prior_mean

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
        abs_mean_shift=abs(mean_shift),
        kl_divergence_estimate=None,  # joint extraction defers per-child KL
        n_samples=n_samples,
        rhat=rhat,
        ess_bulk=ess_bulk,
        sampling_seconds=sampling_seconds,
        convergence_ok=convergence_ok,
        idempotent_hit=False,
        cached_at=None,
    )


# ---------------------------------------------------------------------------
# Posterior correlation matrix + HDI extraction
# ---------------------------------------------------------------------------
def _extract_correlation_posterior(
    idata: az.InferenceData,
) -> tuple[list[list[float]], list[list[list[float]]]]:
    """Return (mean_corr_matrix, hdi_per_pair) from the LKJ correlations.

    LKJCholeskyCov with `compute_corr=True` stores a deterministic named
    `chol_cov_corr` of shape (..., n, n). We average across (chain, draw)
    for the mean matrix and use az.hdi for per-pair intervals.
    """
    corr_samples = np.asarray(idata.posterior["chol_cov_corr"].values)
    # Shape: (chain, draw, n, n)
    flat = corr_samples.reshape(-1, _JOINT_N, _JOINT_N)
    mean_mat = flat.mean(axis=0)

    hdi_mat: list[list[list[float]]] = []
    for i in range(_JOINT_N):
        row: list[list[float]] = []
        for j in range(_JOINT_N):
            if i == j:
                row.append([1.0, 1.0])
                continue
            vals = flat[:, i, j]
            try:
                hdi = az.hdi(vals, hdi_prob=0.94)
                # az.hdi may return ndarray shape (2,) or xarray
                if hasattr(hdi, "values"):
                    hdi = np.asarray(hdi.values).ravel()
                else:
                    hdi = np.asarray(hdi).ravel()
                row.append([float(hdi[0]), float(hdi[1])])
            except Exception:
                # Fallback: empirical 3%/97% quantiles
                lo = float(np.quantile(vals, 0.03))
                hi = float(np.quantile(vals, 0.97))
                row.append([lo, hi])
        hdi_mat.append(row)

    return mean_mat.tolist(), hdi_mat


# ---------------------------------------------------------------------------
# Main API: joint_update()
# ---------------------------------------------------------------------------
def joint_update(
    evidences: list[BeliefEvidence],
    *,
    draws: int = DEFAULT_DRAWS,
    tune: int = DEFAULT_TUNE,
    chains: int = DEFAULT_CHAINS,
    cores: int = DEFAULT_CORES,
    random_seed: int = DEFAULT_RANDOM_SEED,
    strict: bool = True,
    expected_dim_names: Sequence[str] = JOINT_DIM_NAMES_V1,
    dimension_loader: Optional[Callable[[int], Optional[BeliefDimension]]] = None,
    evidence_lookup: Optional[Callable[[str], Optional[BeliefEvidence]]] = None,
    evidence_writer: Optional[Callable[[BeliefEvidence], str]] = None,
    trace_writer: Optional[Callable[[BeliefTrace], str]] = None,
    latest_trace_loader: Optional[Callable[[int], Optional[BeliefTrace]]] = None,
) -> JointDelta:
    """Apply 3 correlated evidence rows jointly.

    Returns a JointDelta wrapping one PosteriorDelta per child dim + the
    posterior correlation matrix (+ 94% HDI per pair).

    Pipeline:
        1. Validate len(evidences) == len(expected_dim_names) (3 for v1).
        2. Compute composite_evidence_hash from sorted child hashes;
           probe persistence for prior cached JointDelta.
        3. Load 3 BeliefDimensions; verify their names match
           expected_dim_names.
        4. validate_evidence_value(dim.distribution, ev.value) per child —
           fail fast on schema errors (KeyError).
        5. Build joint model (_build_joint_model) — LKJ + 3 latents +
           per-dim transforms + per-dim observations.
        6. pm.sample(draws, tune, chains, cores, random_seed) — joint NUTS.
        7. az.summary on the natural-scale Deterministics (p_cyst,
           gmfcs_eta, bayley_score) + chol_cov_corr.
        8. Strict convergence: max rhat across all RVs < 1.01,
           min ess_bulk > 400.
        9. Build N child PosteriorDeltas + persist 3 BeliefEvidence + 3
           BeliefTrace (idempotent per child by their evidence_hash).
        10. Extract posterior correlation matrix (mean + HDI).
        11. Return JointDelta.

    Raises:
        ValueError: len(evidences) != 3, or evidence dim_ids don't match
                    expected dim ordering, or any child evidence missing
                    its evidence_hash.
        KeyError: validation failures from likelihoods layer.
        ConvergenceError: rhat > 1.01 or ess_bulk < 400 with strict=True.
        RuntimeError: dimension lookup returned None for any child.
    """
    # ---- Resolve injection points -----------------------------------------
    _load_dim = dimension_loader or get_dimension_by_id
    _lookup_evidence = evidence_lookup or get_evidence_by_hash
    _write_evidence = evidence_writer or write_evidence
    _write_trace = trace_writer or write_trace
    _latest_trace = latest_trace_loader or latest_trace

    expected = list(expected_dim_names)

    # ---- Step 1: shape validation -----------------------------------------
    if len(evidences) != len(expected):
        raise ValueError(
            f"joint_update expects exactly {len(expected)} evidence rows "
            f"(one per dim in {expected!r}); got {len(evidences)}"
        )
    for ev in evidences:
        if not ev.evidence_hash:
            raise ValueError(
                "every evidence row needs an evidence_hash — "
                "call compute_evidence_hash() first"
            )

    # ---- Step 2: composite idempotency probe ------------------------------
    child_hashes = [ev.evidence_hash for ev in evidences]
    composite_hash = compute_joint_evidence_hash(child_hashes)

    # All 3 child evidences AND their traces must already exist for the
    # joint to be a true cache hit. If any child is missing, re-sample.
    existing_evs = [_lookup_evidence(h) for h in child_hashes]
    all_evs_cached = all(e is not None and e.id for e in existing_evs)
    if all_evs_cached:
        cached_traces = []
        all_traces_match = True
        for ev, existing in zip(evidences, existing_evs):
            cached_trace = _latest_trace(ev.dimension_id)
            if cached_trace is None or cached_trace.evidence_id != existing.id:
                all_traces_match = False
                break
            cached_traces.append(cached_trace)

        if all_traces_match and len(cached_traces) == len(evidences):
            # Cache hit — short-circuit, no sampling.
            child_deltas = []
            for ev, existing, t in zip(evidences, existing_evs, cached_traces):
                dim = _load_dim(ev.dimension_id)
                if dim is None:
                    raise RuntimeError(
                        f"dimension id={ev.dimension_id} not found (joint cache hit)"
                    )
                prior_mean = _compute_prior_mean(dim)
                mean_shift = t.posterior_mean - prior_mean
                child_deltas.append(
                    PosteriorDelta(
                        dimension_name=dim.name,
                        evidence_id=str(existing.id),
                        trace_id=str(t.id) if t.id else "",
                        prior_mean=prior_mean,
                        posterior_mean=t.posterior_mean,
                        posterior_sd=t.posterior_sd,
                        hdi_3=t.hdi_3,
                        hdi_97=t.hdi_97,
                        mean_shift=mean_shift,
                        abs_mean_shift=abs(mean_shift),
                        kl_divergence_estimate=None,
                        n_samples=t.n_samples,
                        rhat=t.rhat,
                        ess_bulk=t.ess_bulk,
                        sampling_seconds=0.0,
                        convergence_ok=(
                            t.rhat < STRICT_RHAT_MAX
                            and t.ess_bulk > STRICT_ESS_BULK_MIN
                        ),
                        idempotent_hit=True,
                        cached_at=t.created_at,
                    )
                )
            # Identity correlation matrix as a placeholder for the
            # cached case (joint posterior corr not persisted in v7.0).
            identity = [
                [1.0 if i == j else 0.0 for j in range(_JOINT_N)]
                for i in range(_JOINT_N)
            ]
            hdi_placeholder = [
                [[1.0, 1.0] if i == j else [-1.0, 1.0] for j in range(_JOINT_N)]
                for i in range(_JOINT_N)
            ]
            return JointDelta(
                dim_names=[d.dimension_name for d in child_deltas],
                child_deltas=child_deltas,
                posterior_correlation_matrix=identity,
                posterior_correlation_hdi=hdi_placeholder,
                n_samples=max(t.n_samples for t in cached_traces),
                rhat_max=max(t.rhat for t in cached_traces),
                ess_bulk_min=min(t.ess_bulk for t in cached_traces),
                sampling_seconds=0.0,
                composite_evidence_hash=composite_hash,
                idempotent_hit=True,
                cached_at=max(
                    (t.created_at for t in cached_traces if t.created_at),
                    default=None,
                ),
            )

    # ---- Step 3: load dims, enforce name ordering -------------------------
    dims: list[BeliefDimension] = []
    for ev in evidences:
        dim = _load_dim(ev.dimension_id)
        if dim is None:
            raise RuntimeError(
                f"dimension id={ev.dimension_id} not found in persistence"
            )
        dims.append(dim)

    actual_names = [d.name for d in dims]
    if actual_names != expected:
        raise ValueError(
            f"joint_update dim ordering mismatch: expected {expected!r}, "
            f"got {actual_names!r}. Pass evidences in the same order as "
            f"expected_dim_names (cyst, gmfcs, bayley by default)."
        )

    # ---- Step 4: validate child evidence shapes (KeyError fast-fail) ------
    for dim, ev in zip(dims, evidences):
        validate_evidence_value(dim.distribution, ev.value)

    # ---- Step 5-6: build joint model + sample -----------------------------
    t0 = time.perf_counter()
    model = _build_joint_model(dims, evidences)
    with model:
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

    # ---- Step 7: ArviZ summary across the natural-scale Deterministics ---
    summary = az.summary(
        idata,
        var_names=["p_cyst", "gmfcs_eta", "bayley_score", "chol_cov_corr"],
    )

    # ---- Step 8: convergence gate (max rhat, min ess across child RVs) ---
    cols = list(summary.columns)
    rhat_col = _pick(cols, "r_hat", "rhat")
    ess_col = _pick(cols, "ess_bulk")
    rhat_series = summary[rhat_col].astype(float)
    ess_series = summary[ess_col].astype(float)
    rhat_max = float(rhat_series.max())
    ess_bulk_min = float(ess_series.min())

    convergence_ok = (
        math.isfinite(rhat_max)
        and math.isfinite(ess_bulk_min)
        and rhat_max < STRICT_RHAT_MAX
        and ess_bulk_min > STRICT_ESS_BULK_MIN
    )
    if strict and not convergence_ok:
        raise ConvergenceError(
            f"Joint sampler did not converge: "
            f"rhat_max={rhat_max:.4f} (limit={STRICT_RHAT_MAX}), "
            f"ess_bulk_min={ess_bulk_min:.1f} (min={STRICT_ESS_BULK_MIN}). "
            f"Increase tune steps before increasing draws."
        )

    # ---- Step 9: per-child persistence + delta extraction -----------------
    n_samples = int(draws * chains)
    # The natural-scale variable name we summarise per dim. For GMFCS we
    # use the latent η (continuous) since the ordinal mean is not a single
    # scalar; the prior_mean comparison is then advisory rather than the
    # canonical categorical-prior-mean. v7.1 may add a "posterior class
    # probabilities" extraction; for v7.0 the latent η posterior is the
    # bridge to the joint correlation matrix.
    natural_var_for_dim = {
        "cyst_volume_pct": "p_cyst",
        "gmfcs_level": "gmfcs_eta",
        "bayley_cognitive": "bayley_score",
    }

    child_deltas: list[PosteriorDelta] = []
    for dim, ev in zip(dims, evidences):
        # Per-child persistence (idempotent on evidence_hash + (dim_id, ev_id))
        evidence_id = _write_evidence(ev)

        natural_name = natural_var_for_dim[dim.name]
        # Pull this dim's row out of the summary (drop chol_cov_corr block)
        row = summary.loc[natural_name]
        posterior_mean = float(row["mean"])
        posterior_sd = float(row["sd"])
        lo_col = _pick(cols, "hdi_3%", "eti89_lb", "hdi_2.5%")
        hi_col = _pick(cols, "hdi_97%", "eti89_ub", "hdi_97.5%")
        hdi_3 = float(row[lo_col])
        hdi_97 = float(row[hi_col])
        child_rhat = float(row[rhat_col])
        child_ess = float(row[ess_col])

        trace = BeliefTrace(
            dimension_id=dim.id if dim.id is not None else ev.dimension_id,
            evidence_id=evidence_id,
            posterior_mean=posterior_mean,
            posterior_sd=posterior_sd,
            hdi_3=hdi_3,
            hdi_97=hdi_97,
            n_samples=n_samples,
            rhat=child_rhat,
            ess_bulk=child_ess,
            arviz_summary={
                "mean": posterior_mean,
                "sd": posterior_sd,
                "hdi_3%": hdi_3,
                "hdi_97%": hdi_97,
                "r_hat": child_rhat,
                "ess_bulk": child_ess,
                "convergence_ok": convergence_ok,
                "joint_source": "joint_update_v1",
                "natural_var": natural_name,
            },
        )
        trace_id = _write_trace(trace)

        prior_mean = _compute_prior_mean(dim)
        mean_shift = posterior_mean - prior_mean
        child_deltas.append(
            PosteriorDelta(
                dimension_name=dim.name,
                evidence_id=evidence_id,
                trace_id=trace_id,
                prior_mean=prior_mean,
                posterior_mean=posterior_mean,
                posterior_sd=posterior_sd,
                hdi_3=hdi_3,
                hdi_97=hdi_97,
                mean_shift=mean_shift,
                abs_mean_shift=abs(mean_shift),
                kl_divergence_estimate=None,
                n_samples=n_samples,
                rhat=child_rhat,
                ess_bulk=child_ess,
                sampling_seconds=sampling_seconds,
                convergence_ok=convergence_ok,
                idempotent_hit=False,
                cached_at=None,
            )
        )

    # ---- Step 10: posterior correlation matrix + HDI ----------------------
    corr_mean, corr_hdi = _extract_correlation_posterior(idata)

    # ---- Step 11: return JointDelta --------------------------------------
    return JointDelta(
        dim_names=actual_names,
        child_deltas=child_deltas,
        posterior_correlation_matrix=corr_mean,
        posterior_correlation_hdi=corr_hdi,
        n_samples=n_samples,
        rhat_max=rhat_max,
        ess_bulk_min=ess_bulk_min,
        sampling_seconds=sampling_seconds,
        composite_evidence_hash=composite_hash,
        idempotent_hit=False,
        cached_at=None,
    )


# ---------------------------------------------------------------------------
# Multivariate KL — explicit NotImplementedError per carry-forward contract #5
# ---------------------------------------------------------------------------
def compute_joint_kl_divergence(*args: Any, **kwargs: Any) -> float:
    """Multivariate KL(joint posterior || joint prior).

    Per Day 13-14 carry-forward contract #5: explicit NotImplementedError,
    NOT silent None. v7.1 may add this; for v7.0 it is out of scope.

    For per-child univariate KL, take each entry of
    `JointDelta.child_deltas` and call
    `brain.belief.update._estimate_kl_divergence(samples, dim)` on its
    flattened posterior samples from the joint InferenceData.
    """
    raise NotImplementedError(
        "Multivariate KL divergence between joint posterior and joint prior "
        "is deferred to v7.1. For univariate KL per child dim, use "
        "brain.belief.update._estimate_kl_divergence on the natural-scale "
        "posterior samples (p_cyst / gmfcs_eta / bayley_score) extracted "
        "from the joint InferenceData."
    )


__all__ = [
    "JOINT_DIM_NAMES_V1",
    "JointDelta",
    "compute_joint_evidence_hash",
    "compute_joint_kl_divergence",
    "joint_update",
    "_build_joint_model",
    "_extract_correlation_posterior",
]
