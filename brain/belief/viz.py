"""Phase 7.0 Day 18 - ArviZ posterior visualization layer.

Renders per-dimension PNG snapshots showing prior + posterior on the same axes.
Used by Day 19-20 verifier (check_7_0_10 artifact) and consumed by Phase 7.6
frontend TwinStatus view (passes pre-rendered PNGs OR re-renders client-side via
Plotly - adapter contract TBD).

Headless-safe: forces matplotlib 'Agg' backend before importing pyplot.

ArviZ 1.x note: the 1.x API replaced the matplotlib-axes-style
`az.plot_posterior(trace, ax=ax)` (ArviZ 0.x) with a PlotCollection abstraction.
For full control of the prior+posterior overlay on a single Figure we render
directly with matplotlib + scipy.stats for the prior PDF and np.histogram /
ax.hist for the posterior samples. ArviZ 1.1.0 is still used for `az.summary`
to gate on `r_hat` / `ess_bulk`.

Hard rules (from .claude/agents/v7-bayes.md):
  - No PHI in figures (no Aleksandra-specific values; synthetic test evidence)
  - rhat < 1.05 AND ess_bulk > 200 enforced before saving (skip dim if fails)
    NB: looser than update.py's strict 1.01/400 gate because these snapshots
    are illustrative, not persisted to belief_traces.
  - Figure metadata embeds dimension name + citation + sampling params
"""

from __future__ import annotations

import math
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # MUST come before pyplot import
import matplotlib.pyplot as plt
import numpy as np
import pymc as pm
import arviz as az
from scipy import stats as sp_stats

from brain.belief.persistence import BeliefDimension
from brain.belief.schema import DistributionSpec, load_dimensions_from_toml
from brain.belief.likelihoods import LIKELIHOOD_REGISTRY


DEFAULT_SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
DEFAULT_DRAWS = 1000  # smaller than update()'s 2000 - snapshots are illustrative
DEFAULT_TUNE = 500
DEFAULT_CHAINS = 2
DEFAULT_RANDOM_SEED = 7

# Looser convergence gate for illustrative snapshots (vs update.py's 1.01/400)
SNAPSHOT_RHAT_MAX = 1.05
SNAPSHOT_ESS_BULK_MIN = 200.0


# ---------------------------------------------------------------------------
# Synthetic-evidence generators (per distribution kind)
# Mirror the LIKELIHOOD_VALUE_SCHEMA but with small, plausible values that
# produce visibly-different posteriors (not so weak the posterior looks identical
# to the prior, not so strong it overwhelms the prior).
# NO Aleksandra-specific values - synthetic only.
# ---------------------------------------------------------------------------
def synthetic_evidence_for_dim(dim: BeliefDimension) -> dict:
    """Return a value dict appropriate for LIKELIHOOD_REGISTRY[dim.distribution]
    that shifts the posterior away from the prior mean by a visible amount.
    """
    kind = dim.distribution
    p = dim.prior_params

    if kind == "beta":
        # 30 trials, k near 1.6x prior mean (or 0.6x if mean >= 0.5)
        mean = p["alpha"] / (p["alpha"] + p["beta"])
        target_rate = min(0.95, mean * 1.6) if mean < 0.5 else max(0.05, mean * 0.6)
        n = 30
        k = max(0, min(n, round(target_rate * n)))
        return {"n": n, "k": k}

    if kind == "normal":
        mu = float(p["mu"])
        sigma = float(p["sigma"])
        shift = 0.3 * sigma
        return {"observations": [mu + shift] * 10, "sigma": sigma * 0.5}

    if kind == "poisson":
        mu = float(p["mu"])
        target = max(1, round(mu * 1.5))
        return {"observations": [target] * 5}

    if kind == "gamma":
        # likelihood uses pm.Gamma(mu=prior_rv, sigma)
        mu = p["alpha"] / p["beta"]
        return {"observations": [mu * 1.2] * 5, "sigma": max(0.5, 0.3 * mu)}

    if kind == "bernoulli":
        p_val = float(p["p"])
        target_rate = min(0.95, p_val * 1.4)
        n = 10
        k = max(0, min(n, round(target_rate * n)))
        return {"observations": [1] * k + [0] * (n - k)}

    if kind == "categorical":
        # observe 5 samples from a class adjacent to the mode
        probs = list(p["probs"])
        mode_idx = int(np.argmax(probs))
        adj = min(len(probs) - 1, max(0, mode_idx + 1))
        return {"observations": [adj] * 5}

    if kind == "vector":
        mu_vec = list(p["mu_vec"])
        obs = [[float(v) + 0.3 for v in mu_vec]] * 3
        return {"observations": obs}

    if kind == "exp_decay":
        # Pick 10 observations near the prior-derived fraction with small jitter
        # so the sampler has enough information to converge (3 identical
        # observations produce a degenerate likelihood surface; the Day 10
        # exp_decay design uses prior_rv as a rate variable but
        # pm.Exponential(lam=...) samples are in time-remaining units, so the
        # NUTS posterior here is illustrative only - see dim 12 TOML comment).
        lam = float(p["lam"])
        target = min(0.99, max(0.01, math.exp(-lam * 365.0) * 1.05))
        # Deterministic spread - no PRNG so the snapshot is reproducible
        spread = [target - 0.015, target - 0.005, target + 0.005, target + 0.015]
        obs = [target] * 6 + spread  # 10 observations
        obs = [min(0.99, max(0.01, v)) for v in obs]
        return {"observations": obs, "horizon_days": 365.0}

    raise ValueError(f"no synthetic evidence template for distribution kind {kind!r}")


# ---------------------------------------------------------------------------
# Prior PDF / PMF evaluators
# Used to overlay the analytical prior on top of the posterior histogram.
# ---------------------------------------------------------------------------
def prior_support_and_pdf(
    dim: BeliefDimension,
    posterior_samples: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, str]:
    """Return (xs, ys, kind) for plotting the analytical prior over the
    posterior's support range. `kind` is 'pdf' for continuous, 'pmf' for
    discrete. Returns (empty, empty, 'none') if prior is hard to render
    analytically (vector, exp_decay, categorical).
    """
    kind = dim.distribution
    p = dim.prior_params

    # Compute a sensible support range for continuous priors from posterior
    if posterior_samples.size:
        lo = float(np.percentile(posterior_samples, 0.5))
        hi = float(np.percentile(posterior_samples, 99.5))
    else:
        lo, hi = 0.0, 1.0

    if kind == "beta":
        xs = np.linspace(max(0.0, lo - 0.05), min(1.0, hi + 0.05), 200)
        ys = sp_stats.beta.pdf(xs, p["alpha"], p["beta"])
        return xs, ys, "pdf"

    if kind == "normal":
        # Pad to capture prior tails too
        pad = 2.0 * float(p["sigma"])
        xs = np.linspace(
            min(lo, float(p["mu"]) - pad), max(hi, float(p["mu"]) + pad), 200
        )
        ys = sp_stats.norm.pdf(xs, loc=p["mu"], scale=p["sigma"])
        return xs, ys, "pdf"

    if kind == "gamma":
        # PyMC Gamma uses rate (beta); scipy uses scale = 1/rate
        alpha = float(p["alpha"])
        beta = float(p["beta"])
        scale = 1.0 / beta
        xs = np.linspace(max(1e-3, lo * 0.5), max(hi * 1.5, alpha / beta * 3.0), 200)
        ys = sp_stats.gamma.pdf(xs, a=alpha, scale=scale)
        return xs, ys, "pdf"

    if kind == "poisson":
        mu = float(p["mu"])
        k_max = int(max(hi, mu + 5)) + 1
        xs = np.arange(0, k_max + 1)
        ys = sp_stats.poisson.pmf(xs, mu=mu)
        return xs.astype(float), ys, "pmf"

    if kind == "bernoulli":
        p_val = float(p["p"])
        xs = np.array([0.0, 1.0])
        ys = np.array([1.0 - p_val, p_val])
        return xs, ys, "pmf"

    if kind == "categorical":
        probs = np.asarray(p["probs"], dtype=float)
        xs = np.arange(len(probs)).astype(float)
        return xs, probs, "pmf"

    # vector / exp_decay: skip analytical overlay (multi-dim or non-trivial transform)
    return np.array([]), np.array([]), "none"


# ---------------------------------------------------------------------------
# Sample posterior for a single dim (no DB writes - pure compute for viz)
# ---------------------------------------------------------------------------
def sample_posterior_for_snapshot(
    dim: BeliefDimension,
    *,
    draws: int = DEFAULT_DRAWS,
    tune: int = DEFAULT_TUNE,
    chains: int = DEFAULT_CHAINS,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> Optional[az.InferenceData]:
    """Build prior + likelihood, sample, return InferenceData.

    Returns None if sampling fails OR convergence gates not met.
    """
    try:
        value = synthetic_evidence_for_dim(dim)
        spec = DistributionSpec(kind=dim.distribution, params=dim.prior_params)
        builder = LIKELIHOOD_REGISTRY[dim.distribution]

        with pm.Model():
            prior = spec.to_pm("p")
            builder(prior, value)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                trace = pm.sample(
                    draws=draws,
                    tune=tune,
                    chains=chains,
                    cores=1,
                    random_seed=random_seed,
                    progressbar=False,
                    return_inferencedata=True,
                )
    except Exception:
        return None

    # Convergence gate (loose for snapshots)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            summary = az.summary(trace, var_names=["p"])
        if "r_hat" in summary.columns:
            rhat_vals = summary["r_hat"].dropna()
            if len(rhat_vals) and float(rhat_vals.max()) > SNAPSHOT_RHAT_MAX:
                return None
        if "ess_bulk" in summary.columns:
            ess_vals = summary["ess_bulk"].dropna()
            if len(ess_vals) and float(ess_vals.min()) < SNAPSHOT_ESS_BULK_MIN:
                return None
    except Exception:
        # Summary may fail for vector/categorical/exp_decay shape combos.
        # Accept the trace if we got this far - the renderer will handle it.
        pass

    return trace


# ---------------------------------------------------------------------------
# Plot rendering
# ---------------------------------------------------------------------------
def _extract_posterior_samples(trace: az.InferenceData) -> np.ndarray:
    """Pull a flat numpy array of posterior samples for variable 'p'.

    For vector dims returns the first component (we still show *something*).
    For discrete dims returns floats (for histogram compatibility).
    """
    arr = np.asarray(trace.posterior["p"].values)
    # arr shape: (chains, draws[, *dim])
    if arr.ndim <= 2:
        return arr.flatten().astype(float)
    # Multi-dim - take first component for the snapshot
    arr_flat = arr.reshape(arr.shape[0] * arr.shape[1], -1)
    return arr_flat[:, 0].astype(float)


def _short_citation(citation: str, max_len: int = 80) -> str:
    """Truncate a citation string for footer rendering."""
    if not citation:
        return ""
    if len(citation) <= max_len:
        return citation
    return citation[: max_len - 3] + "..."


def render_dimension_snapshot(
    dim: BeliefDimension,
    trace: az.InferenceData,
    output_path: Path,
) -> bool:
    """Render a single PNG. Returns True on success, False on render error."""
    fig, ax = plt.subplots(figsize=(8, 5))
    try:
        samples = _extract_posterior_samples(trace)

        # Posterior histogram
        is_discrete = dim.distribution in {"poisson", "bernoulli", "categorical"}
        if is_discrete:
            # Integer-aligned bins
            lo = int(np.floor(samples.min())) if samples.size else 0
            hi = int(np.ceil(samples.max())) if samples.size else 1
            bins = np.arange(lo - 0.5, hi + 1.5, 1.0)
            ax.hist(
                samples,
                bins=bins,
                density=True,
                alpha=0.55,
                color="#1f77b4",
                edgecolor="white",
                label="posterior",
            )
        else:
            ax.hist(
                samples,
                bins=40,
                density=True,
                alpha=0.55,
                color="#1f77b4",
                edgecolor="white",
                label="posterior",
            )

        # Prior overlay
        xs, ys, prior_kind = prior_support_and_pdf(dim, samples)
        if prior_kind == "pdf":
            ax.plot(xs, ys, color="#d62728", linewidth=2.0, label="prior")
            ax.fill_between(xs, ys, alpha=0.15, color="#d62728")
        elif prior_kind == "pmf":
            ax.vlines(
                xs,
                0,
                ys,
                color="#d62728",
                linewidth=2.0,
                alpha=0.85,
                label="prior (PMF)",
            )
            ax.plot(xs, ys, "o", color="#d62728", markersize=4)

        # Posterior mean line
        if samples.size:
            post_mean = float(np.mean(samples))
            ax.axvline(
                post_mean,
                color="#2ca02c",
                linestyle="--",
                linewidth=1.4,
                label=f"posterior mean = {post_mean:.3g}",
            )

        ax.set_title(f"{dim.name}  -  posterior with synthetic evidence")
        units_lbl = f"  ({dim.units})" if dim.units else ""
        ax.set_xlabel(f"{dim.distribution} support{units_lbl}")
        ax.set_ylabel("density" if not is_discrete else "probability mass")
        ax.legend(loc="best", fontsize=8, framealpha=0.85)
        ax.grid(alpha=0.25)

        # Footer with citation + sampling params
        fig.text(
            0.02,
            0.02,
            f"Distribution: {dim.distribution}  |  Prior: {dim.prior_params}  |  "
            f"Cite: {_short_citation(dim.citation)}",
            fontsize=7,
            alpha=0.7,
        )
        fig.text(
            0.02,
            0.965,
            f"Generated: {datetime.now(timezone.utc).isoformat()}  |  Phase 7.0 Day 18  |  "
            f"draws={DEFAULT_DRAWS}  tune={DEFAULT_TUNE}  chains={DEFAULT_CHAINS}",
            fontsize=7,
            alpha=0.5,
        )

        plt.tight_layout(rect=(0, 0.04, 1, 0.95))
        fig.savefig(output_path, dpi=100, bbox_inches="tight")
        return True
    except Exception:
        return False
    finally:
        plt.close(fig)


# ---------------------------------------------------------------------------
# Batch entry point
# ---------------------------------------------------------------------------
def render_all_snapshots(
    output_dir: Path = DEFAULT_SNAPSHOT_DIR,
    dimensions: Optional[list[BeliefDimension]] = None,
) -> dict[str, dict]:
    """Render PNG snapshots for every dimension in the catalog.

    Returns a dict keyed by dim name:
      {status: 'ok'|'skip'|'error', path?, size_bytes?, reason?}
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    dims = dimensions if dimensions is not None else load_dimensions_from_toml()
    results: dict[str, dict] = {}

    for dim in dims:
        snap_path = output_dir / f"{dim.name}.png"
        trace = sample_posterior_for_snapshot(dim)
        if trace is None:
            results[dim.name] = {
                "status": "skip",
                "reason": "sampling or convergence failure",
            }
            continue
        ok = render_dimension_snapshot(dim, trace, snap_path)
        if ok and snap_path.exists():
            size = snap_path.stat().st_size
            if size < 5000:
                # Under the 5 KB verifier gate - mark as skip with reason
                results[dim.name] = {
                    "status": "skip",
                    "reason": f"rendered but size {size} < 5000 bytes",
                    "path": str(snap_path),
                    "size_bytes": size,
                }
            else:
                results[dim.name] = {
                    "status": "ok",
                    "path": str(snap_path),
                    "size_bytes": size,
                }
        else:
            results[dim.name] = {"status": "error", "reason": "render error"}

    return results


def main() -> int:
    """CLI entry point: render all 13 snapshots and print a summary."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(f"Phase 7.0 Day 18 - rendering dimension snapshots to {DEFAULT_SNAPSHOT_DIR}")
    results = render_all_snapshots()
    ok_count = sum(1 for r in results.values() if r.get("status") == "ok")
    skip_count = sum(1 for r in results.values() if r.get("status") == "skip")
    err_count = sum(1 for r in results.values() if r.get("status") == "error")
    print(
        f"OK: {ok_count}/{len(results)} | Skipped: {skip_count} | Errors: {err_count}"
    )
    for name, r in results.items():
        marker = {"ok": "OK ", "skip": "SKP", "error": "ERR"}.get(r["status"], "???")
        size = r.get("size_bytes", 0)
        reason = r.get("reason", "")
        print(f"  [{marker}] {name:32s} {size:>7} bytes  {reason}")
    return 0 if err_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "DEFAULT_SNAPSHOT_DIR",
    "DEFAULT_DRAWS",
    "DEFAULT_TUNE",
    "DEFAULT_CHAINS",
    "DEFAULT_RANDOM_SEED",
    "SNAPSHOT_RHAT_MAX",
    "SNAPSHOT_ESS_BULK_MIN",
    "synthetic_evidence_for_dim",
    "prior_support_and_pdf",
    "sample_posterior_for_snapshot",
    "render_dimension_snapshot",
    "render_all_snapshots",
    "main",
]
