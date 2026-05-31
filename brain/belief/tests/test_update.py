"""brain/belief/tests/test_update.py — Phase 7.0 Days 13-14 unit tests.

Scope:
  - Idempotency: cache hit short-circuits sampling.
  - Validation: bad distribution kind, missing value keys, domain errors propagate.
  - Convergence gate: strict=True raises; strict=False persists with flag.
  - Per-distribution end-to-end smoke (subset; small draws for CI speed).
  - Persistence integration: writers called once on miss, zero on hit.
  - PosteriorDelta correctness: mean_shift, rhat, ess, KL.

All DB calls are mocked via injectable lookup/writer callables — no live Supabase
connection. Pattern mirrors Day 5 `test_persistence.py`.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Optional
from unittest import mock

import numpy as np
import pytest

from brain.belief.persistence import (
    BeliefDimension,
    BeliefEvidence,
    BeliefTrace,
    compute_evidence_hash,
)
from brain.belief.update import (
    ConvergenceError,
    _compute_prior_mean,
    _estimate_kl_divergence,
    update,
)


# ---------------------------------------------------------------------------
# Test fixtures — synthetic dimensions + evidence (NO PHI)
# ---------------------------------------------------------------------------
def _dim(
    distribution: str,
    prior_params: dict[str, Any],
    *,
    name: Optional[str] = None,
    id_: int = 1,
    citation: str = "https://pubmed.ncbi.nlm.nih.gov/test",
) -> BeliefDimension:
    return BeliefDimension(
        id=id_,
        name=name or f"dim_{distribution}_{id_}",
        distribution=distribution,
        prior_params=prior_params,
        citation=citation,
    )


def _evidence(
    dim: BeliefDimension,
    value: dict[str, Any],
    *,
    source: str = "manual",
    source_ref: str = "test:ref",
    confidence: float = 0.8,
) -> BeliefEvidence:
    """Build a BeliefEvidence with auto-computed evidence_hash."""
    dim_id = dim.id or 1
    ev_hash = compute_evidence_hash(dim_id, source, source_ref, value)
    return BeliefEvidence(
        dimension_id=dim_id,
        source=source,
        source_ref=source_ref,
        value=value,
        evidence_hash=ev_hash,
        confidence=confidence,
        observed_at=datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc),
    )


class _Recorder:
    """In-memory stand-in for persistence calls. Tracks call counts + args."""

    def __init__(
        self,
        dims: list[BeliefDimension],
        *,
        existing_evidence: Optional[BeliefEvidence] = None,
        existing_trace: Optional[BeliefTrace] = None,
    ):
        self._dims = {d.id: d for d in dims if d.id is not None}
        self._existing_evidence = existing_evidence
        self._existing_trace = existing_trace
        self.write_evidence_calls: list[BeliefEvidence] = []
        self.write_trace_calls: list[BeliefTrace] = []
        self.evidence_lookup_calls: list[str] = []
        self.dim_loader_calls: list[int] = []

    def load_dim(self, dim_id: int) -> Optional[BeliefDimension]:
        self.dim_loader_calls.append(dim_id)
        return self._dims.get(dim_id)

    def lookup_evidence(self, ev_hash: str) -> Optional[BeliefEvidence]:
        self.evidence_lookup_calls.append(ev_hash)
        if self._existing_evidence and self._existing_evidence.evidence_hash == ev_hash:
            return self._existing_evidence
        return None

    def latest_trace(self, dim_id: int) -> Optional[BeliefTrace]:
        if self._existing_trace and self._existing_trace.dimension_id == dim_id:
            return self._existing_trace
        return None

    def write_evidence(self, ev: BeliefEvidence) -> str:
        self.write_evidence_calls.append(ev)
        return "ev-uuid-" + str(len(self.write_evidence_calls))

    def write_trace(self, t: BeliefTrace) -> str:
        self.write_trace_calls.append(t)
        return "trace-uuid-" + str(len(self.write_trace_calls))


def _kwargs_from(rec: _Recorder) -> dict:
    return dict(
        dimension_loader=rec.load_dim,
        evidence_lookup=rec.lookup_evidence,
        trace_writer=rec.write_trace,
        evidence_writer=rec.write_evidence,
        latest_trace_lookup=rec.latest_trace,
    )


# ---------------------------------------------------------------------------
# _compute_prior_mean — unit-tests (cheap; no PyMC)
# ---------------------------------------------------------------------------
def test_prior_mean_beta() -> None:
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    assert _compute_prior_mean(dim) == pytest.approx(0.2)


def test_prior_mean_normal() -> None:
    dim = _dim("normal", {"mu": 1.5, "sigma": 2.0})
    assert _compute_prior_mean(dim) == pytest.approx(1.5)


def test_prior_mean_poisson() -> None:
    dim = _dim("poisson", {"mu": 2.5})
    assert _compute_prior_mean(dim) == pytest.approx(2.5)


def test_prior_mean_gamma() -> None:
    dim = _dim("gamma", {"alpha": 4.0, "beta": 2.0})
    # mean = alpha / beta = 2.0
    assert _compute_prior_mean(dim) == pytest.approx(2.0)


def test_prior_mean_bernoulli() -> None:
    dim = _dim("bernoulli", {"p": 0.3})
    assert _compute_prior_mean(dim) == pytest.approx(0.3)


def test_prior_mean_categorical() -> None:
    dim = _dim("categorical", {"probs": [0.5, 0.3, 0.2]})
    # 0*0.5 + 1*0.3 + 2*0.2 = 0.7
    assert _compute_prior_mean(dim) == pytest.approx(0.7)


def test_prior_mean_vector_first_dim() -> None:
    dim = _dim("vector", {"mu_vec": [1.0, 2.0, 3.0], "sigma_vec": [0.5, 0.5, 0.5]})
    assert _compute_prior_mean(dim) == pytest.approx(1.0)


def test_prior_mean_exp_decay_at_365_days() -> None:
    dim = _dim("exp_decay", {"lam": 0.001})
    expected = math.exp(-0.001 * 365.0)
    assert _compute_prior_mean(dim) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Idempotency — does NOT sample
# ---------------------------------------------------------------------------
def test_update_returns_idempotent_hit_when_hash_exists() -> None:
    """If evidence_hash already has a trace, return cached delta — no PyMC call."""
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    ev = _evidence(dim, {"n": 20, "k": 4})
    # Pretend the row was previously stored:
    cached_ev = ev.model_copy(update={"id": "cached-ev-uuid"})
    cached_trace = BeliefTrace(
        id="cached-trace-uuid",
        dimension_id=dim.id or 1,
        evidence_id="cached-ev-uuid",
        posterior_mean=0.22,
        posterior_sd=0.07,
        hdi_3=0.10,
        hdi_97=0.36,
        n_samples=2000,
        rhat=1.005,
        ess_bulk=1100.0,
        created_at=datetime(2026, 5, 24, 11, 0, tzinfo=timezone.utc),
    )
    rec = _Recorder([dim], existing_evidence=cached_ev, existing_trace=cached_trace)

    # If PyMC sample is called, fail — it must not be reached.
    with mock.patch("brain.belief.update.pm.sample") as mock_sample:
        delta = update(ev, **_kwargs_from(rec))
        mock_sample.assert_not_called()

    assert delta.idempotent_hit is True
    assert delta.trace_id == "cached-trace-uuid"
    assert delta.evidence_id == "cached-ev-uuid"
    assert delta.posterior_mean == pytest.approx(0.22)
    assert delta.prior_mean == pytest.approx(0.2)
    assert delta.mean_shift == pytest.approx(0.02)
    assert delta.abs_mean_shift == pytest.approx(0.02)
    assert delta.sampling_seconds == 0.0
    assert rec.write_evidence_calls == []
    assert rec.write_trace_calls == []


def test_update_idempotent_hit_skips_writes() -> None:
    """Persistence writers must not be invoked on cache hit."""
    dim = _dim("normal", {"mu": 0.0, "sigma": 1.0})
    ev = _evidence(dim, {"observations": [0.5, 1.0]})
    cached_ev = ev.model_copy(update={"id": "ev-x"})
    cached_trace = BeliefTrace(
        id="t-x",
        dimension_id=dim.id or 1,
        evidence_id="ev-x",
        posterior_mean=0.75,
        posterior_sd=0.5,
        hdi_3=-0.2,
        hdi_97=1.7,
        n_samples=2000,
        rhat=1.001,
        ess_bulk=900.0,
    )
    rec = _Recorder([dim], existing_evidence=cached_ev, existing_trace=cached_trace)

    with mock.patch("brain.belief.update.pm.sample") as mock_sample:
        update(ev, **_kwargs_from(rec))
        mock_sample.assert_not_called()

    assert len(rec.write_evidence_calls) == 0
    assert len(rec.write_trace_calls) == 0


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def test_update_rejects_unknown_distribution_kind() -> None:
    """Dimension with bogus distribution -> KeyError from get_likelihood."""
    # Bypass BeliefDimension validation (which rejects unknown kinds) by
    # building a "valid" dim then forcing a bad distribution via mock loader.
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    rogue = dim.model_copy(update={"distribution": "beta"})
    # Mutate after construction to bypass Pydantic validator:
    object.__setattr__(rogue, "distribution", "lognormal_pareto_chimera")
    ev = _evidence(dim, {"n": 10, "k": 3})

    def loader(_id: int) -> BeliefDimension:
        return rogue

    rec = _Recorder([dim])
    kwargs = _kwargs_from(rec)
    kwargs["dimension_loader"] = loader

    with pytest.raises(KeyError, match="No likelihood registered"):
        update(ev, **kwargs)


def test_update_validates_evidence_value_before_sampling() -> None:
    """Missing required value keys -> KeyError BEFORE any PyMC call."""
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    bad_ev = _evidence(dim, {"n": 10})  # missing 'k'
    rec = _Recorder([dim])

    with mock.patch("brain.belief.update.pm.sample") as mock_sample:
        with pytest.raises(KeyError, match="missing"):
            update(bad_ev, **_kwargs_from(rec))
        mock_sample.assert_not_called()


def test_update_propagates_likelihood_errors() -> None:
    """k > n raises ValueError from beta likelihood — not swallowed."""
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    bad_ev = _evidence(dim, {"n": 10, "k": 99})  # k > n
    rec = _Recorder([dim])

    with pytest.raises(ValueError, match="invalid beta-binomial"):
        update(bad_ev, **_kwargs_from(rec))


def test_update_raises_when_dimension_not_found() -> None:
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    ev = _evidence(dim, {"n": 10, "k": 3})

    def loader(_id: int) -> Optional[BeliefDimension]:
        return None

    rec = _Recorder([dim])
    kwargs = _kwargs_from(rec)
    kwargs["dimension_loader"] = loader

    with pytest.raises(RuntimeError, match="not found"):
        update(ev, **kwargs)


def test_update_requires_evidence_hash() -> None:
    """An empty evidence_hash fails fast — caller must populate it."""
    # Build via persistence model with manual empty hash (validator allows any
    # string at the schema layer; update() rejects empty).
    ev = BeliefEvidence(
        dimension_id=1,
        source="manual",
        source_ref="x",
        value={"n": 10, "k": 3},
        evidence_hash="",
        confidence=0.5,
        observed_at=datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc),
    )
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    rec = _Recorder([dim])
    with pytest.raises(ValueError, match="evidence_hash"):
        update(ev, **_kwargs_from(rec))


# ---------------------------------------------------------------------------
# Convergence gate — strict True / False
# ---------------------------------------------------------------------------
def _bad_rhat_idata_summary() -> Any:
    """Return an ArviZ-summary-like DataFrame with bad rhat.

    Supplies columns under BOTH naming conventions (hdi_3%/eti89_lb etc.) so
    the test passes regardless of which ArviZ build is installed in .venv-v7.
    """
    import pandas as pd

    return pd.DataFrame(
        {
            "mean": [0.5],
            "sd": [0.1],
            "hdi_3%": [0.3],
            "hdi_97%": [0.7],
            "eti89_lb": [0.3],
            "eti89_ub": [0.7],
            "r_hat": [1.5],  # FAIL: > 1.01
            "ess_bulk": [50.0],  # FAIL: < 400
        },
        index=["p"],
    )


def test_update_strict_mode_raises_on_bad_rhat() -> None:
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    ev = _evidence(dim, {"n": 20, "k": 4})
    rec = _Recorder([dim])

    fake_idata = mock.MagicMock()
    # posterior["p"].values for KL — shape (chains, draws); make it trivial.
    fake_idata.posterior = {"p": mock.MagicMock(values=np.array([[0.5, 0.5, 0.5]]))}

    with mock.patch("brain.belief.update.pm.sample", return_value=fake_idata):
        with mock.patch(
            "brain.belief.update.az.summary",
            return_value=_bad_rhat_idata_summary(),
        ):
            with pytest.raises(ConvergenceError, match="did not converge"):
                update(ev, strict=True, **_kwargs_from(rec))

    # No write should have happened (we raised before persistence).
    assert rec.write_evidence_calls == []
    assert rec.write_trace_calls == []


def test_update_non_strict_mode_persists_anyway_with_flag() -> None:
    """strict=False: persist with convergence_ok=False and don't raise."""
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    ev = _evidence(dim, {"n": 20, "k": 4})
    rec = _Recorder([dim])

    fake_idata = mock.MagicMock()
    fake_idata.posterior = {
        "p": mock.MagicMock(
            values=np.array([[0.45, 0.50, 0.55]] * 30)  # >=50 samples for KL path
        )
    }

    with mock.patch("brain.belief.update.pm.sample", return_value=fake_idata):
        with mock.patch(
            "brain.belief.update.az.summary",
            return_value=_bad_rhat_idata_summary(),
        ):
            delta = update(ev, strict=False, **_kwargs_from(rec))

    assert delta.convergence_ok is False
    assert delta.rhat == pytest.approx(1.5)
    assert delta.ess_bulk == pytest.approx(50.0)
    # Persistence DID happen despite failed gate.
    assert len(rec.write_evidence_calls) == 1
    assert len(rec.write_trace_calls) == 1
    # arviz_summary records the failure.
    assert rec.write_trace_calls[0].arviz_summary["convergence_ok"] is False


# ---------------------------------------------------------------------------
# Per-distribution end-to-end smoke (REAL PyMC sampling; small draws)
# ---------------------------------------------------------------------------
# Tunables kept very small to stay inside the 5-min suite budget. We test the
# most common kinds end-to-end and rely on test_likelihoods.py for the rest.

_FAST_KWARGS = dict(draws=400, tune=400, chains=2, random_seed=7, strict=False)


def test_update_beta_binomial_end_to_end() -> None:
    """Beta(2,8) + Binomial(20, 4) -> posterior mean ≈ 0.20 (analytical = 6/30)."""
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    ev = _evidence(dim, {"n": 20, "k": 4})
    rec = _Recorder([dim])
    delta = update(ev, **_FAST_KWARGS, **_kwargs_from(rec))
    assert delta.idempotent_hit is False
    assert abs(delta.posterior_mean - 0.2) < 0.05
    assert delta.prior_mean == pytest.approx(0.2)
    assert len(rec.write_evidence_calls) == 1
    assert len(rec.write_trace_calls) == 1
    assert delta.n_samples == 400 * 2


def test_update_beta_binomial_dramatic_shift() -> None:
    """Beta(2,8) + Binomial(20, 15) -> posterior mean ≈ 0.567; mean_shift ≈ +0.367."""
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    ev = _evidence(dim, {"n": 20, "k": 15})
    rec = _Recorder([dim])
    delta = update(ev, **_FAST_KWARGS, **_kwargs_from(rec))
    analytical = 17.0 / 30.0  # Beta(17, 13)
    assert abs(delta.posterior_mean - analytical) < 0.05
    assert delta.mean_shift > 0.25
    assert delta.abs_mean_shift > 0.25


def test_update_normal_end_to_end() -> None:
    """Normal(0, 5) prior + observations -> posterior mean drifts toward data mean."""
    dim = _dim("normal", {"mu": 0.0, "sigma": 5.0})
    ev = _evidence(dim, {"observations": [1.0, 2.0, 3.0, 4.0, 5.0], "sigma": 1.0})
    rec = _Recorder([dim])
    delta = update(ev, **_FAST_KWARGS, **_kwargs_from(rec))
    # Posterior mean should be between prior (0) and data mean (3.0), closer to 3.
    assert delta.posterior_mean > 1.5
    assert delta.posterior_mean < 3.5


def test_update_poisson_end_to_end() -> None:
    """Poisson(2.0) prior + observations=[3,4,2] -> posterior mean shifts toward data."""
    dim = _dim("poisson", {"mu": 2.0})
    ev = _evidence(dim, {"observations": [3, 4, 2]})
    rec = _Recorder([dim])
    delta = update(ev, **_FAST_KWARGS, **_kwargs_from(rec))
    assert delta.posterior_mean > 1.5  # observed mean = 3.0
    assert delta.prior_mean == pytest.approx(2.0)


def test_update_bernoulli_end_to_end() -> None:
    """Bernoulli(p=0.3) prior + 10 observations -> end-to-end smoke.

    KNOWN LIMITATION (Day 11-12 design + Day 13-14 carry-forward):
    The Bernoulli-prior pattern is semantically degenerate — the "prior" RV
    is itself a discrete 0/1 draw, NOT a latent probability. Inference here
    samples a discrete RV; updating the underlying p requires a Beta-Bernoulli
    conjugate model (out of scope for Phase 7.0 MVP — covered by Beta + Binomial).

    This test asserts the pipeline COMPLETES (persistence + delta) but does
    not assert any specific posterior direction. The discrete-sampling
    pathology is documented as the MVP behaviour in `likelihoods.py`.
    """
    dim = _dim("bernoulli", {"p": 0.3})
    obs = [1, 1, 1, 1, 1, 1, 1, 0, 0, 0]
    ev = _evidence(dim, {"observations": obs})
    rec = _Recorder([dim])
    delta = update(ev, **_FAST_KWARGS, **_kwargs_from(rec))
    # Pipeline ran:
    assert delta.idempotent_hit is False
    assert delta.prior_mean == pytest.approx(0.3)
    assert len(rec.write_evidence_calls) == 1
    assert len(rec.write_trace_calls) == 1
    # Posterior mean is in [0, 1] (Bernoulli range) — sanity.
    assert 0.0 <= delta.posterior_mean <= 1.0


# ---------------------------------------------------------------------------
# Persistence integration (mocked) — writes happen exactly once
# ---------------------------------------------------------------------------
def test_update_writes_evidence_and_trace_to_persistence() -> None:
    """Non-idempotent path: writers called exactly once each."""
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    ev = _evidence(dim, {"n": 10, "k": 3})
    rec = _Recorder([dim])
    delta = update(ev, **_FAST_KWARGS, **_kwargs_from(rec))
    assert len(rec.write_evidence_calls) == 1
    assert len(rec.write_trace_calls) == 1
    assert delta.evidence_id.startswith("ev-uuid-")
    assert delta.trace_id.startswith("trace-uuid-")
    # Trace carries the rhat/ess we measured.
    persisted_trace = rec.write_trace_calls[0]
    assert persisted_trace.rhat == delta.rhat
    assert persisted_trace.ess_bulk == delta.ess_bulk


def test_update_caches_after_first_call() -> None:
    """First call samples; second call (same hash) should short-circuit if cache provided."""
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    ev = _evidence(dim, {"n": 10, "k": 3})

    # First pass: empty cache -> writes.
    rec1 = _Recorder([dim])
    delta1 = update(ev, **_FAST_KWARGS, **_kwargs_from(rec1))
    assert delta1.idempotent_hit is False
    assert len(rec1.write_trace_calls) == 1

    # Second pass: pre-populated cache -> idempotent hit.
    cached_ev = ev.model_copy(update={"id": "cached"})
    cached_trace = BeliefTrace(
        id="cached-t",
        dimension_id=dim.id or 1,
        evidence_id="cached",
        posterior_mean=delta1.posterior_mean,
        posterior_sd=delta1.posterior_sd,
        hdi_3=delta1.hdi_3,
        hdi_97=delta1.hdi_97,
        n_samples=delta1.n_samples,
        rhat=delta1.rhat,
        ess_bulk=delta1.ess_bulk,
    )
    rec2 = _Recorder([dim], existing_evidence=cached_ev, existing_trace=cached_trace)

    with mock.patch("brain.belief.update.pm.sample") as mock_sample:
        delta2 = update(ev, **_FAST_KWARGS, **_kwargs_from(rec2))
        mock_sample.assert_not_called()

    assert delta2.idempotent_hit is True
    assert len(rec2.write_evidence_calls) == 0
    assert len(rec2.write_trace_calls) == 0


# ---------------------------------------------------------------------------
# PosteriorDelta correctness — shape + diagnostics
# ---------------------------------------------------------------------------
def test_posterior_delta_includes_rhat_and_ess() -> None:
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    ev = _evidence(dim, {"n": 10, "k": 3})
    rec = _Recorder([dim])
    delta = update(ev, **_FAST_KWARGS, **_kwargs_from(rec))
    assert math.isfinite(delta.rhat)
    assert delta.rhat >= 1.0
    assert math.isfinite(delta.ess_bulk)
    assert delta.ess_bulk > 0


def test_posterior_delta_sampling_seconds_positive() -> None:
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    ev = _evidence(dim, {"n": 10, "k": 3})
    rec = _Recorder([dim])
    delta = update(ev, **_FAST_KWARGS, **_kwargs_from(rec))
    assert delta.sampling_seconds > 0.0


# ---------------------------------------------------------------------------
# KL divergence behavior
# ---------------------------------------------------------------------------
def test_kl_divergence_returns_none_for_vector_dim() -> None:
    """Vector kind -> KL is None (deferred)."""
    dim = _dim("vector", {"mu_vec": [0.0, 0.0], "sigma_vec": [1.0, 1.0]})
    samples = np.random.RandomState(7).normal(size=200)
    assert _estimate_kl_divergence(samples, dim) is None


def test_kl_divergence_returns_none_for_exp_decay() -> None:
    """exp_decay -> KL not in supported set."""
    dim = _dim("exp_decay", {"lam": 0.001})
    samples = np.random.RandomState(7).exponential(scale=1 / 0.001, size=200)
    assert _estimate_kl_divergence(samples, dim) is None


def test_kl_divergence_returns_value_for_beta() -> None:
    """Posterior shifted away from prior -> KL > 0."""
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})  # prior mean 0.2
    # Synthetic "posterior" centered near 0.5 (different from prior)
    rng = np.random.RandomState(7)
    samples = rng.beta(5.0, 5.0, size=500)
    kl = _estimate_kl_divergence(samples, dim)
    assert kl is not None
    assert kl > 0.0
    assert math.isfinite(kl)


def test_kl_divergence_returns_value_for_normal() -> None:
    dim = _dim("normal", {"mu": 0.0, "sigma": 1.0})
    rng = np.random.RandomState(7)
    samples = rng.normal(loc=2.0, scale=0.5, size=500)
    kl = _estimate_kl_divergence(samples, dim)
    assert kl is not None
    assert kl > 0.0


def test_kl_divergence_returns_value_for_bernoulli() -> None:
    dim = _dim("bernoulli", {"p": 0.3})
    rng = np.random.RandomState(7)
    samples = rng.binomial(1, 0.7, size=300).astype(float)
    kl = _estimate_kl_divergence(samples, dim)
    assert kl is not None
    assert kl > 0.0


def test_kl_divergence_returns_none_for_degenerate_posterior() -> None:
    """All samples identical -> hi - lo < eps -> None."""
    dim = _dim("beta", {"alpha": 2.0, "beta": 8.0})
    samples = np.full(100, 0.5)
    assert _estimate_kl_divergence(samples, dim) is None
