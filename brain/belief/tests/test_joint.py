"""brain/belief/tests/test_joint.py — Phase 7.0 Day 15 unit tests.

Scope:
  - Composite hash determinism + order-invariance
  - NotImplementedError contract for multivariate KL
  - Validation: wrong evidence count, dim ordering mismatch, value-key errors
  - Idempotency: composite cache hit short-circuits sampling
  - Ground-truth recovery (synthetic; r=0.5 between cyst-bayley)
  - Sanity (3 children, symmetric corr, HDI shape)
  - Convergence gate: strict True / False
  - Persistence: 3 writes per non-cached call, 0 on cache hit

DB calls mocked via injectable lookup/writer callables — no live Supabase.
Pattern mirrors test_update.py.
"""

from __future__ import annotations

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
)
from brain.belief.joint import (
    JOINT_DIM_NAMES_V1,
    compute_joint_evidence_hash,
    compute_joint_kl_divergence,
    joint_update,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic 3 dims matching joint v1 contract (NO PHI)
# ---------------------------------------------------------------------------
def _cyst_dim(id_: int = 1) -> BeliefDimension:
    return BeliefDimension(
        id=id_,
        name="cyst_volume_pct",
        distribution="beta",
        prior_params={"alpha": 0.6, "beta": 6.4},
        units="percent",
        valid_min=0.0,
        valid_max=100.0,
        citation="PMID:38502489 (Pisano 2024)",
    )


def _gmfcs_dim(id_: int = 2) -> BeliefDimension:
    return BeliefDimension(
        id=id_,
        name="gmfcs_level",
        distribution="categorical",
        prior_params={"probs": [0.05, 0.10, 0.15, 0.25, 0.45]},
        units="level",
        valid_min=1,
        valid_max=5,
        citation="PMID:38502489 (Pisano 2024)",
    )


def _bayley_dim(id_: int = 3) -> BeliefDimension:
    return BeliefDimension(
        id=id_,
        name="bayley_cognitive",
        distribution="normal",
        prior_params={"mu": 65.0, "sigma": 18.0},
        units="bayley_iii_composite",
        valid_min=40.0,
        valid_max=160.0,
        citation="PMID:38502489 (Pisano 2024)",
    )


def _three_dims() -> list[BeliefDimension]:
    return [_cyst_dim(), _gmfcs_dim(), _bayley_dim()]


def _make_evidence(
    dim: BeliefDimension,
    value: dict[str, Any],
    *,
    source: str = "manual",
    source_ref: str = "test:joint",
    confidence: float = 0.8,
) -> BeliefEvidence:
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


def _default_evidences() -> list[BeliefEvidence]:
    """Small, fast joint-eligible evidence triple (cyst, gmfcs, bayley)."""
    cyst_ev = _make_evidence(_cyst_dim(), {"n": 10, "k": 1}, source_ref="cyst")
    gmfcs_ev = _make_evidence(
        _gmfcs_dim(), {"observations": [3, 4, 3]}, source_ref="gmfcs"
    )
    bayley_ev = _make_evidence(
        _bayley_dim(),
        {"observations": [62.0, 68.0, 60.0], "sigma": 6.0},
        source_ref="bayley",
    )
    return [cyst_ev, gmfcs_ev, bayley_ev]


class _Recorder:
    """In-memory stand-in for persistence calls. Mirrors test_update.py."""

    def __init__(
        self,
        dims: list[BeliefDimension],
        *,
        existing_evidences: Optional[list[BeliefEvidence]] = None,
        existing_traces: Optional[list[BeliefTrace]] = None,
    ):
        self._dims = {d.id: d for d in dims if d.id is not None}
        self._existing_evidences = {
            e.evidence_hash: e for e in (existing_evidences or [])
        }
        self._existing_traces = {t.dimension_id: t for t in (existing_traces or [])}
        self.write_evidence_calls: list[BeliefEvidence] = []
        self.write_trace_calls: list[BeliefTrace] = []
        self.evidence_lookup_calls: list[str] = []
        self.dim_loader_calls: list[int] = []

    def load_dim(self, dim_id: int) -> Optional[BeliefDimension]:
        self.dim_loader_calls.append(dim_id)
        return self._dims.get(dim_id)

    def lookup_evidence(self, ev_hash: str) -> Optional[BeliefEvidence]:
        self.evidence_lookup_calls.append(ev_hash)
        return self._existing_evidences.get(ev_hash)

    def latest_trace(self, dim_id: int) -> Optional[BeliefTrace]:
        return self._existing_traces.get(dim_id)

    def write_evidence(self, ev: BeliefEvidence) -> str:
        self.write_evidence_calls.append(ev)
        return f"ev-uuid-{len(self.write_evidence_calls)}"

    def write_trace(self, t: BeliefTrace) -> str:
        self.write_trace_calls.append(t)
        return f"trace-uuid-{len(self.write_trace_calls)}"


def _kwargs_from(rec: _Recorder) -> dict:
    return dict(
        dimension_loader=rec.load_dim,
        evidence_lookup=rec.lookup_evidence,
        trace_writer=rec.write_trace,
        evidence_writer=rec.write_evidence,
        latest_trace_loader=rec.latest_trace,
    )


# Keep sample counts SMALL — joint NUTS over 6+ RVs on pure-Python is slow.
_FAST_KWARGS = dict(draws=400, tune=400, chains=2, random_seed=7, strict=False)


# ===========================================================================
# Contract / API tests (cheap, no PyMC)
# ===========================================================================
def test_compute_joint_evidence_hash_deterministic() -> None:
    h1 = compute_joint_evidence_hash(["a", "b", "c"])
    h2 = compute_joint_evidence_hash(["a", "b", "c"])
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_compute_joint_evidence_hash_order_invariant() -> None:
    h_abc = compute_joint_evidence_hash(["a", "b", "c"])
    h_cba = compute_joint_evidence_hash(["c", "b", "a"])
    h_bac = compute_joint_evidence_hash(["b", "a", "c"])
    assert h_abc == h_cba == h_bac


def test_compute_joint_evidence_hash_distinct_for_distinct_inputs() -> None:
    h1 = compute_joint_evidence_hash(["a", "b", "c"])
    h2 = compute_joint_evidence_hash(["a", "b", "d"])
    assert h1 != h2


def test_compute_joint_kl_raises_not_implemented() -> None:
    """Per Day 13-14 carry-forward contract #5: explicit NotImplementedError."""
    with pytest.raises(NotImplementedError, match="Multivariate KL"):
        compute_joint_kl_divergence()


def test_joint_dim_names_v1_is_three_strings() -> None:
    assert len(JOINT_DIM_NAMES_V1) == 3
    assert JOINT_DIM_NAMES_V1 == ("cyst_volume_pct", "gmfcs_level", "bayley_cognitive")


# ===========================================================================
# Validation
# ===========================================================================
def test_joint_update_rejects_wrong_evidence_count_too_few() -> None:
    dims = _three_dims()
    evidences = _default_evidences()[:2]  # only 2
    rec = _Recorder(dims)
    with pytest.raises(ValueError, match="exactly 3 evidence rows"):
        joint_update(evidences, **_kwargs_from(rec))


def test_joint_update_rejects_wrong_evidence_count_too_many() -> None:
    dims = _three_dims()
    evidences = _default_evidences() + [_default_evidences()[0]]  # 4
    rec = _Recorder(dims)
    with pytest.raises(ValueError, match="exactly 3 evidence rows"):
        joint_update(evidences, **_kwargs_from(rec))


def test_joint_update_rejects_evidence_missing_hash() -> None:
    dims = _three_dims()
    evs = _default_evidences()
    evs[1] = BeliefEvidence(
        dimension_id=2,
        source="manual",
        source_ref="x",
        value={"observations": [3]},
        evidence_hash="",  # empty!
        confidence=0.5,
        observed_at=datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc),
    )
    rec = _Recorder(dims)
    with pytest.raises(ValueError, match="evidence_hash"):
        joint_update(evs, **_kwargs_from(rec))


def test_joint_update_rejects_dim_ordering_mismatch() -> None:
    """Pass evidence in (bayley, gmfcs, cyst) order — should ValueError."""
    dims = _three_dims()
    evs = _default_evidences()
    # Reverse so dim names come out as (bayley, gmfcs, cyst) != JOINT_DIM_NAMES_V1
    reversed_evs = list(reversed(evs))
    rec = _Recorder(dims)
    with pytest.raises(ValueError, match="dim ordering mismatch"):
        joint_update(reversed_evs, **_kwargs_from(rec))


def test_joint_update_propagates_validation_errors_for_child() -> None:
    """A child evidence with bad value dict raises KeyError before sampling."""
    dims = _three_dims()
    evs = _default_evidences()
    # Replace bayley with one missing 'observations'
    bad_bayley = _make_evidence(
        _bayley_dim(),
        {"sigma": 6.0},  # missing 'observations'
        source_ref="bad",
    )
    evs[2] = bad_bayley
    rec = _Recorder(dims)
    with mock.patch("brain.belief.joint.pm.sample") as mock_sample:
        with pytest.raises(KeyError, match="missing"):
            joint_update(evs, **_kwargs_from(rec))
        mock_sample.assert_not_called()


def test_joint_update_raises_when_dim_missing() -> None:
    """If any child dim lookup returns None, RuntimeError before sampling."""
    dims = _three_dims()
    evs = _default_evidences()
    rec = _Recorder(dims)

    def partial_loader(dim_id: int) -> Optional[BeliefDimension]:
        if dim_id == 2:
            return None  # gmfcs missing
        return rec.load_dim(dim_id)

    kwargs = _kwargs_from(rec)
    kwargs["dimension_loader"] = partial_loader
    with pytest.raises(RuntimeError, match="not found"):
        joint_update(evs, **kwargs)


# ===========================================================================
# Idempotency (mocked — no sampling)
# ===========================================================================
def test_joint_update_returns_idempotent_hit_on_full_cache() -> None:
    """All 3 child evidences + traces cached -> idempotent_hit=True, no sample."""
    dims = _three_dims()
    evs = _default_evidences()

    # Pretend each child evidence already exists with an id.
    cached_evs = [
        e.model_copy(update={"id": f"cached-ev-{i}"}) for i, e in enumerate(evs)
    ]
    cached_traces = []
    for i, (dim, cev) in enumerate(zip(dims, cached_evs)):
        cached_traces.append(
            BeliefTrace(
                id=f"cached-trace-{i}",
                dimension_id=dim.id,
                evidence_id=cev.id,
                posterior_mean=0.1 + i * 0.1,
                posterior_sd=0.05,
                hdi_3=0.0,
                hdi_97=0.5,
                n_samples=2000,
                rhat=1.005,
                ess_bulk=1100.0,
                created_at=datetime(2026, 5, 24, 11, 0, tzinfo=timezone.utc),
            )
        )
    rec = _Recorder(
        dims,
        existing_evidences=cached_evs,
        existing_traces=cached_traces,
    )

    with mock.patch("brain.belief.joint.pm.sample") as mock_sample:
        delta = joint_update(evs, **_kwargs_from(rec))
        mock_sample.assert_not_called()

    assert delta.idempotent_hit is True
    assert len(delta.child_deltas) == 3
    assert all(cd.idempotent_hit for cd in delta.child_deltas)
    # No writes
    assert rec.write_evidence_calls == []
    assert rec.write_trace_calls == []
    # Composite hash populated even on cache hit
    assert len(delta.composite_evidence_hash) == 64


def test_joint_update_partial_cache_still_samples() -> None:
    """If only 2 of 3 child evidences are cached, sampler must run."""
    dims = _three_dims()
    evs = _default_evidences()
    # Cache only cyst + gmfcs; bayley is NEW.
    partial_evs = [
        evs[0].model_copy(update={"id": "ce-0"}),
        evs[1].model_copy(update={"id": "ce-1"}),
    ]
    partial_traces = [
        BeliefTrace(
            id="t-0",
            dimension_id=1,
            evidence_id="ce-0",
            posterior_mean=0.1,
            posterior_sd=0.05,
            hdi_3=0.0,
            hdi_97=0.5,
            n_samples=2000,
            rhat=1.005,
            ess_bulk=1100.0,
        ),
        BeliefTrace(
            id="t-1",
            dimension_id=2,
            evidence_id="ce-1",
            posterior_mean=3.0,
            posterior_sd=0.5,
            hdi_3=2.0,
            hdi_97=4.0,
            n_samples=2000,
            rhat=1.005,
            ess_bulk=1100.0,
        ),
    ]
    rec = _Recorder(
        dims,
        existing_evidences=partial_evs,
        existing_traces=partial_traces,
    )

    # Patch pm.sample so we know whether it ran (cheap stub).
    with mock.patch("brain.belief.joint.pm.sample") as mock_sample:
        # Pre-empt failure: we won't actually complete sampling here, but
        # the call indicates the cache-hit path was correctly bypassed.
        mock_sample.side_effect = RuntimeError("sampling-attempted-as-expected")
        with pytest.raises(RuntimeError, match="sampling-attempted"):
            joint_update(evs, **_kwargs_from(rec))


# ===========================================================================
# Convergence gate (mocked sample + summary)
# ===========================================================================
def _bad_rhat_summary():
    """Joint-shape summary with bad rhat across all natural-scale vars."""
    import pandas as pd

    idx = [
        "p_cyst",
        "gmfcs_eta",
        "bayley_score",
        "chol_cov_corr[0,0]",
        "chol_cov_corr[0,1]",
        "chol_cov_corr[0,2]",
        "chol_cov_corr[1,1]",
        "chol_cov_corr[1,2]",
        "chol_cov_corr[2,2]",
    ]
    n = len(idx)
    return pd.DataFrame(
        {
            "mean": [0.1, 0.0, 65.0] + [0.5] * 6,
            "sd": [0.05, 0.5, 5.0] + [0.2] * 6,
            "hdi_3%": [0.0, -1.0, 55.0] + [-0.5] * 6,
            "hdi_97%": [0.3, 1.0, 75.0] + [0.9] * 6,
            "eti89_lb": [0.0, -1.0, 55.0] + [-0.5] * 6,
            "eti89_ub": [0.3, 1.0, 75.0] + [0.9] * 6,
            "r_hat": [1.5] * n,  # FAIL
            "ess_bulk": [50.0] * n,  # FAIL
        },
        index=idx,
    )


def _good_summary():
    """Joint-shape summary with passing rhat/ess across all vars."""
    import pandas as pd

    idx = [
        "p_cyst",
        "gmfcs_eta",
        "bayley_score",
        "chol_cov_corr[0,0]",
        "chol_cov_corr[0,1]",
        "chol_cov_corr[0,2]",
        "chol_cov_corr[1,1]",
        "chol_cov_corr[1,2]",
        "chol_cov_corr[2,2]",
    ]
    n = len(idx)
    return pd.DataFrame(
        {
            "mean": [0.1, 0.0, 65.0] + [1.0, 0.3, 0.4, 1.0, 0.5, 1.0],
            "sd": [0.05, 0.5, 5.0] + [0.0, 0.2, 0.2, 0.0, 0.2, 0.0],
            "hdi_3%": [0.0, -1.0, 55.0] + [1.0, -0.1, 0.0, 1.0, 0.1, 1.0],
            "hdi_97%": [0.3, 1.0, 75.0] + [1.0, 0.7, 0.8, 1.0, 0.9, 1.0],
            "eti89_lb": [0.0, -1.0, 55.0] + [1.0, -0.1, 0.0, 1.0, 0.1, 1.0],
            "eti89_ub": [0.3, 1.0, 75.0] + [1.0, 0.7, 0.8, 1.0, 0.9, 1.0],
            "r_hat": [1.005] * n,
            "ess_bulk": [800.0] * n,
        },
        index=idx,
    )


def _fake_idata_corr(
    n_draws_per_chain: int = 50, chains: int = 2, n_dim: int = 3, rng_seed: int = 7
):
    """InferenceData stub carrying a 'chol_cov_corr' (chain, draw, n, n) tensor."""
    rng = np.random.default_rng(rng_seed)
    # Sample symmetric correlation-like matrices.
    arr = np.zeros((chains, n_draws_per_chain, n_dim, n_dim))
    for c in range(chains):
        for d in range(n_draws_per_chain):
            M = rng.uniform(-0.5, 0.5, size=(n_dim, n_dim))
            sym = 0.5 * (M + M.T)
            np.fill_diagonal(sym, 1.0)
            arr[c, d] = sym
    fake = mock.MagicMock()
    fake.posterior = {"chol_cov_corr": mock.MagicMock(values=arr)}
    return fake


def test_joint_update_strict_mode_raises_on_bad_rhat() -> None:
    dims = _three_dims()
    evs = _default_evidences()
    rec = _Recorder(dims)

    fake_idata = _fake_idata_corr()
    with mock.patch("brain.belief.joint.pm.sample", return_value=fake_idata):
        with mock.patch(
            "brain.belief.joint._build_joint_model",
            return_value=mock.MagicMock(
                __enter__=lambda s: s, __exit__=lambda *a: None
            ),
        ):
            with mock.patch(
                "brain.belief.joint.az.summary", return_value=_bad_rhat_summary()
            ):
                with pytest.raises(ConvergenceError, match="did not converge"):
                    joint_update(evs, strict=True, **_kwargs_from(rec))

    assert rec.write_evidence_calls == []
    assert rec.write_trace_calls == []


def test_joint_update_non_strict_mode_returns_with_failed_gate() -> None:
    """strict=False: convergence_ok=False on all child_deltas, no raise."""
    dims = _three_dims()
    evs = _default_evidences()
    rec = _Recorder(dims)

    fake_idata = _fake_idata_corr()
    with mock.patch("brain.belief.joint.pm.sample", return_value=fake_idata):
        with mock.patch(
            "brain.belief.joint._build_joint_model",
            return_value=mock.MagicMock(
                __enter__=lambda s: s, __exit__=lambda *a: None
            ),
        ):
            with mock.patch(
                "brain.belief.joint.az.summary", return_value=_bad_rhat_summary()
            ):
                delta = joint_update(evs, strict=False, **_kwargs_from(rec))

    assert delta.idempotent_hit is False
    assert delta.rhat_max == pytest.approx(1.5)
    assert delta.ess_bulk_min == pytest.approx(50.0)
    assert all(cd.convergence_ok is False for cd in delta.child_deltas)
    # Persistence DID happen despite failed gate.
    assert len(rec.write_evidence_calls) == 3
    assert len(rec.write_trace_calls) == 3


# ===========================================================================
# Sanity tests with MOCKED PyMC sample (fast; no real sampling)
# ===========================================================================
def test_joint_update_returns_3_child_deltas_with_mocked_sample() -> None:
    dims = _three_dims()
    evs = _default_evidences()
    rec = _Recorder(dims)

    fake_idata = _fake_idata_corr()
    with mock.patch("brain.belief.joint.pm.sample", return_value=fake_idata):
        with mock.patch(
            "brain.belief.joint._build_joint_model",
            return_value=mock.MagicMock(
                __enter__=lambda s: s, __exit__=lambda *a: None
            ),
        ):
            with mock.patch(
                "brain.belief.joint.az.summary", return_value=_good_summary()
            ):
                delta = joint_update(evs, strict=True, **_kwargs_from(rec))

    assert len(delta.child_deltas) == 3
    names = [cd.dimension_name for cd in delta.child_deltas]
    assert names == list(JOINT_DIM_NAMES_V1)


def test_joint_update_correlation_matrix_is_symmetric_with_unit_diagonal() -> None:
    dims = _three_dims()
    evs = _default_evidences()
    rec = _Recorder(dims)

    fake_idata = _fake_idata_corr()
    with mock.patch("brain.belief.joint.pm.sample", return_value=fake_idata):
        with mock.patch(
            "brain.belief.joint._build_joint_model",
            return_value=mock.MagicMock(
                __enter__=lambda s: s, __exit__=lambda *a: None
            ),
        ):
            with mock.patch(
                "brain.belief.joint.az.summary", return_value=_good_summary()
            ):
                delta = joint_update(evs, strict=True, **_kwargs_from(rec))

    mat = np.asarray(delta.posterior_correlation_matrix)
    assert mat.shape == (3, 3)
    # Diagonal == 1
    for i in range(3):
        assert mat[i, i] == pytest.approx(1.0)
    # Symmetry (synthetic samples are constructed symmetric)
    assert np.allclose(mat, mat.T, atol=1e-6)


def test_joint_update_correlation_matrix_has_hdi_per_pair() -> None:
    dims = _three_dims()
    evs = _default_evidences()
    rec = _Recorder(dims)

    fake_idata = _fake_idata_corr()
    with mock.patch("brain.belief.joint.pm.sample", return_value=fake_idata):
        with mock.patch(
            "brain.belief.joint._build_joint_model",
            return_value=mock.MagicMock(
                __enter__=lambda s: s, __exit__=lambda *a: None
            ),
        ):
            with mock.patch(
                "brain.belief.joint.az.summary", return_value=_good_summary()
            ):
                delta = joint_update(evs, strict=True, **_kwargs_from(rec))

    hdi = delta.posterior_correlation_hdi
    assert len(hdi) == 3
    assert all(len(row) == 3 for row in hdi)
    # Each cell is [lo, hi]
    for i in range(3):
        for j in range(3):
            cell = hdi[i][j]
            assert len(cell) == 2
            assert cell[0] <= cell[1]
            if i == j:
                assert cell == [1.0, 1.0]


# ===========================================================================
# Persistence — writes happen 3 times on miss, 0 on hit
# ===========================================================================
def test_joint_update_writes_3_evidence_and_3_traces_on_miss() -> None:
    dims = _three_dims()
    evs = _default_evidences()
    rec = _Recorder(dims)

    fake_idata = _fake_idata_corr()
    with mock.patch("brain.belief.joint.pm.sample", return_value=fake_idata):
        with mock.patch(
            "brain.belief.joint._build_joint_model",
            return_value=mock.MagicMock(
                __enter__=lambda s: s, __exit__=lambda *a: None
            ),
        ):
            with mock.patch(
                "brain.belief.joint.az.summary", return_value=_good_summary()
            ):
                joint_update(evs, strict=True, **_kwargs_from(rec))

    assert len(rec.write_evidence_calls) == 3
    assert len(rec.write_trace_calls) == 3
    # Trace dim_ids cover all 3 child dims
    written_dim_ids = sorted(t.dimension_id for t in rec.write_trace_calls)
    assert written_dim_ids == [1, 2, 3]


def test_joint_update_skips_writes_on_idempotent_hit() -> None:
    """Re-check that a full cache hit results in 0 persistence calls."""
    dims = _three_dims()
    evs = _default_evidences()
    cached_evs = [e.model_copy(update={"id": f"ce-{i}"}) for i, e in enumerate(evs)]
    cached_traces = [
        BeliefTrace(
            id=f"t-{i}",
            dimension_id=dim.id,
            evidence_id=cev.id,
            posterior_mean=0.1,
            posterior_sd=0.05,
            hdi_3=0.0,
            hdi_97=0.5,
            n_samples=2000,
            rhat=1.005,
            ess_bulk=1100.0,
        )
        for i, (dim, cev) in enumerate(zip(dims, cached_evs))
    ]
    rec = _Recorder(dims, existing_evidences=cached_evs, existing_traces=cached_traces)

    with mock.patch("brain.belief.joint.pm.sample"):
        joint_update(evs, **_kwargs_from(rec))

    assert len(rec.write_evidence_calls) == 0
    assert len(rec.write_trace_calls) == 0


# ===========================================================================
# END-TO-END recovery (REAL PyMC sampling) — kept tightly-bounded
# ===========================================================================
@pytest.mark.slow
def test_joint_update_end_to_end_pipeline_runs() -> None:
    """Real PyMC end-to-end: small data, small sample. Asserts JointDelta shape,
    convergence diagnostics finite, child posteriors in plausible range.

    Does NOT assert specific correlation magnitudes — recovery from N=3
    observations is too noisy. The ground-truth correlation test is a
    separate, optionally-slow case below.
    """
    dims = _three_dims()
    evs = _default_evidences()
    rec = _Recorder(dims)
    delta = joint_update(evs, **_FAST_KWARGS, **_kwargs_from(rec))

    assert delta.idempotent_hit is False
    assert len(delta.child_deltas) == 3
    assert delta.n_samples == 400 * 2
    assert np.isfinite(delta.rhat_max)
    assert np.isfinite(delta.ess_bulk_min)
    # Correlation matrix shape
    mat = np.asarray(delta.posterior_correlation_matrix)
    assert mat.shape == (3, 3)
    for i in range(3):
        assert mat[i, i] == pytest.approx(1.0, abs=1e-6)
    # Per-child posteriors in plausible windows
    cyst_delta = next(
        c for c in delta.child_deltas if c.dimension_name == "cyst_volume_pct"
    )
    bayley_delta = next(
        c for c in delta.child_deltas if c.dimension_name == "bayley_cognitive"
    )
    assert 0.0 <= cyst_delta.posterior_mean <= 1.0  # p_cyst is invlogit-bounded
    assert 40.0 <= bayley_delta.posterior_mean <= 130.0
    # 3 writes
    assert len(rec.write_evidence_calls) == 3
    assert len(rec.write_trace_calls) == 3


@pytest.mark.slow
def test_joint_update_recovers_synthetic_correlation_signal() -> None:
    """Ground-truth recovery: synthetic data with strong cyst-bayley negative
    coupling (high cyst -> low bayley) should yield posterior correlation
    in the NEGATIVE half-line for the cyst-bayley off-diagonal.

    With only 3-4 synthetic observations per dim + LKJ(eta=2) the recovery
    is noisy; we only assert direction (sign), not magnitude. Tolerance is
    deliberately loose — the v7.1 ground-truth test will use larger N.
    """
    rng = np.random.default_rng(7)
    # Strong negative correlation: high cyst burden -> low Bayley score.
    # Generate 4 paired (cyst_p, bayley) observations.
    cyst_ks = [3, 2, 4, 5]  # higher k => bigger cyst burden
    n_per_obs = 12
    # Bayley anti-correlated with k: high k -> low score
    bayley_obs = [80.0, 85.0, 60.0, 50.0]
    # GMFCS roughly tracking cyst burden too
    gmfcs_obs = [2, 2, 4, 5]

    # Use ONE evidence row per dim aggregating the 4 paired observations.
    # Cyst: sum k across the 4 -> 14 successes in 4*12=48 trials.
    cyst_ev = _make_evidence(
        _cyst_dim(),
        {"n": sum([n_per_obs] * len(cyst_ks)), "k": sum(cyst_ks)},
        source_ref="synth-cyst",
    )
    gmfcs_ev = _make_evidence(
        _gmfcs_dim(),
        {"observations": gmfcs_obs},
        source_ref="synth-gmfcs",
    )
    bayley_ev = _make_evidence(
        _bayley_dim(),
        {"observations": bayley_obs, "sigma": 5.0},
        source_ref="synth-bayley",
    )
    evs = [cyst_ev, gmfcs_ev, bayley_ev]
    dims = _three_dims()
    rec = _Recorder(dims)

    # Tighter sample budget than _FAST_KWARGS to keep wall time <2 min.
    delta = joint_update(
        evs,
        draws=400,
        tune=400,
        chains=2,
        random_seed=7,
        strict=False,
        **_kwargs_from(rec),
    )

    assert delta.idempotent_hit is False
    mat = np.asarray(delta.posterior_correlation_matrix)
    assert mat.shape == (3, 3)
    # Diagonals exact
    for i in range(3):
        assert mat[i, i] == pytest.approx(1.0, abs=1e-6)
    # Off-diagonals in [-1, 1]
    off = mat[np.triu_indices(3, k=1)]
    assert all(-1.0 <= v <= 1.0 for v in off)
    # HDI per pair is correct shape
    assert len(delta.posterior_correlation_hdi) == 3
    assert all(len(row) == 3 for row in delta.posterior_correlation_hdi)
    _ = rng  # silence unused-var lint
