"""
brain/belief/tests/test_persistence.py — Phase 7.0 Day 5a unit tests.

All tests are schema-agnostic: they exercise hashing, Pydantic
validation, env-handling, and round-tripping without touching the live
Supabase DB. Integration tests against `belief_dimensions` / `belief_evidence`
/ `belief_traces` will land in Day 5b after v7-devops applies the
matching SQL migration (target: 017_belief_state_tables.sql).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest import mock

import pytest
from pydantic import ValidationError

from brain.belief.persistence import (
    BeliefDimension,
    BeliefEvidence,
    BeliefTrace,
    _get_conn,
    compute_evidence_hash,
)


# ---------------------------------------------------------------------------
# evidence_hash determinism
# ---------------------------------------------------------------------------
def test_compute_evidence_hash_deterministic() -> None:
    """Same inputs → same hash (locale-independent)."""
    h1 = compute_evidence_hash(
        dimension_id=1,
        source="mri_report",
        source_ref="r2://mri/2026-05-15.json",
        value={"volume_cc": 4.2, "side": "bilateral"},
    )
    h2 = compute_evidence_hash(
        dimension_id=1,
        source="mri_report",
        source_ref="r2://mri/2026-05-15.json",
        value={"volume_cc": 4.2, "side": "bilateral"},
    )
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_compute_evidence_hash_ordering_invariant() -> None:
    """Value dict key order does not change the hash (json.dumps sort_keys=True)."""
    h_a = compute_evidence_hash(
        dimension_id=2,
        source="voice_note",
        source_ref="intake_drop:abc",
        value={"tone": "hypertonic", "limb": "left_arm", "score": 3},
    )
    h_b = compute_evidence_hash(
        dimension_id=2,
        source="voice_note",
        source_ref="intake_drop:abc",
        value={"score": 3, "tone": "hypertonic", "limb": "left_arm"},
    )
    assert h_a == h_b


def test_compute_evidence_hash_changes_with_input() -> None:
    """Any input change flips the hash."""
    base = compute_evidence_hash(1, "manual", "ref1", {"x": 1})
    assert compute_evidence_hash(2, "manual", "ref1", {"x": 1}) != base
    assert compute_evidence_hash(1, "manual", "ref2", {"x": 1}) != base
    assert compute_evidence_hash(1, "manual", "ref1", {"x": 2}) != base


# ---------------------------------------------------------------------------
# BeliefDimension validation
# ---------------------------------------------------------------------------
def test_belief_dimension_requires_citation() -> None:
    """Empty citation raises (Phase 7.0 hard rule: every prior carries source)."""
    with pytest.raises(ValidationError):
        BeliefDimension(
            name="cyst_volume",
            distribution="beta",
            prior_params={"alpha": 2.0, "beta": 5.0},
            citation="",
        )


def test_belief_dimension_rejects_unknown_distribution() -> None:
    with pytest.raises(ValidationError):
        BeliefDimension(
            name="weird",
            distribution="lognormal_pareto_chimera",
            prior_params={},
            citation="https://example.com/source",
        )


def test_belief_dimension_accepts_all_eight_distributions() -> None:
    for dist in [
        "beta",
        "normal",
        "poisson",
        "categorical",
        "gamma",
        "bernoulli",
        "vector",
        "exp_decay",
    ]:
        BeliefDimension(
            name=f"dim_{dist}",
            distribution=dist,
            prior_params={"k": 1.0},
            citation="https://pubmed.ncbi.nlm.nih.gov/0",
        )


# ---------------------------------------------------------------------------
# BeliefEvidence validation
# ---------------------------------------------------------------------------
def _evidence_kwargs(**overrides: object) -> dict:
    base = dict(
        dimension_id=1,
        source="manual",
        source_ref="test:ref",
        value={"x": 1},
        evidence_hash="0" * 64,
        confidence=0.5,
        observed_at=datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc),
    )
    base.update(overrides)
    return base


def test_belief_evidence_confidence_range() -> None:
    """Confidence outside [0, 1] rejected by Pydantic."""
    with pytest.raises(ValidationError):
        BeliefEvidence(**_evidence_kwargs(confidence=1.5))
    with pytest.raises(ValidationError):
        BeliefEvidence(**_evidence_kwargs(confidence=-0.1))


def test_belief_evidence_rejects_unknown_source() -> None:
    with pytest.raises(ValidationError):
        BeliefEvidence(**_evidence_kwargs(source="telepathy"))


# ---------------------------------------------------------------------------
# BeliefTrace shape
# ---------------------------------------------------------------------------
def test_belief_trace_rhat_field_present() -> None:
    """Model carries the sampler diagnostics required by the v7-bayes role."""
    t = BeliefTrace(
        dimension_id=1,
        evidence_id="00000000-0000-0000-0000-000000000000",
        posterior_mean=0.42,
        posterior_sd=0.05,
        hdi_3=0.32,
        hdi_97=0.51,
        n_samples=2000,
        rhat=1.001,
        ess_bulk=1200.0,
    )
    assert t.rhat == 1.001
    assert t.ess_bulk == 1200.0


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------
def test_get_conn_raises_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear env, expect a clear RuntimeError naming the missing var."""
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    # Patch the env loader so it cannot silently repopulate the var.
    with mock.patch("brain.belief.persistence.load_env", lambda: None):
        with pytest.raises(RuntimeError, match="SUPABASE_DB_URL"):
            _get_conn()


# ---------------------------------------------------------------------------
# Pydantic round-trip
# ---------------------------------------------------------------------------
def test_pydantic_round_trip_dimension() -> None:
    dim = BeliefDimension(
        id=1,
        name="cyst_volume",
        distribution="beta",
        prior_params={"alpha": 2.0, "beta": 5.0},
        units="cc",
        valid_min=0.0,
        valid_max=100.0,
        citation="https://www.nature.com/articles/s41597-024-03986-7",
    )
    d = dim.model_dump()
    dim2 = BeliefDimension(**d)
    assert dim == dim2
    assert dim2.prior_params == {"alpha": 2.0, "beta": 5.0}
    assert dim2.citation.startswith("https://")


def test_pydantic_round_trip_evidence() -> None:
    ev = BeliefEvidence(
        id="00000000-0000-0000-0000-00000000abcd",
        dimension_id=3,
        source="mri_report",
        source_ref="r2://mri/2026-05-15.json",
        value={
            "volume_cc": 4.2,
            "side": "bilateral",
            "regions": ["L_putamen", "R_putamen"],
        },
        evidence_hash="a" * 64,
        confidence=0.87,
        observed_at=datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 5, 24, 12, 5, tzinfo=timezone.utc),
    )
    d = ev.model_dump()
    ev2 = BeliefEvidence(**d)
    assert ev == ev2
    # JSONB content survives the round trip
    assert ev2.value["regions"] == ["L_putamen", "R_putamen"]
    assert ev2.confidence == 0.87
