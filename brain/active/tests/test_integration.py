"""Phase 7.4 Day 9 — integration tests (DRY_RUN path)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from brain.active.integration import (
    apply_response_and_compute_delta,
    parsed_response_to_evidence,
)
from brain.active.response_parser import ParsedResponse, parse_response
from brain.belief.persistence import BeliefEvidence
from brain.belief.schema import load_dimensions_from_toml


def _get_dim(name: str):
    for d in load_dimensions_from_toml():
        if d.name == name:
            d.id = 1  # synthetic id; persistence DRY_RUN accepts
            return d
    raise AssertionError(f"dim {name} not found")


@pytest.fixture(autouse=True)
def _force_dry_run(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    yield


def test_builds_valid_belief_evidence_from_integer_seconds() -> None:
    """Verifier check 8: builds valid BeliefEvidence in DRY_RUN."""
    dim = _get_dim("head_control_seconds")
    parsed = parse_response("8 წამი", expected_format="integer_seconds")
    ev = parsed_response_to_evidence(
        dim=dim,
        parsed=parsed,
        observation_type="tummy_time_timer",
        source_ref="2026-W45/0",
        observed_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
    )
    assert isinstance(ev, BeliefEvidence)
    assert ev.source == "manual"
    assert ev.value["int"] == 8
    assert ev.value["observation_type"] == "tummy_time_timer"
    assert ev.confidence >= 0.9
    assert len(ev.evidence_hash) == 64  # SHA-256 hex


def test_evidence_hash_deterministic() -> None:
    dim = _get_dim("seizure_freq_per_day")
    parsed = parse_response("0", expected_format="integer_count")
    when = datetime(2026, 11, 9, tzinfo=timezone.utc)
    ev1 = parsed_response_to_evidence(
        dim=dim, parsed=parsed, observation_type="parent_log_count",
        source_ref="x", observed_at=when,
    )
    ev2 = parsed_response_to_evidence(
        dim=dim, parsed=parsed, observation_type="parent_log_count",
        source_ref="x", observed_at=when,
    )
    assert ev1.evidence_hash == ev2.evidence_hash


def test_integer_count_round_trip() -> None:
    dim = _get_dim("seizure_freq_per_day")
    parsed = parse_response("3", expected_format="integer_count")
    ev = parsed_response_to_evidence(
        dim=dim, parsed=parsed, observation_type="parent_log_count",
        source_ref="t", observed_at=datetime.now(timezone.utc),
    )
    assert ev.value["int"] == 3


def test_apply_and_compute_delta_dry_run_status() -> None:
    dim = _get_dim("head_control_seconds")
    parsed = parse_response("12 seconds", expected_format="integer_seconds")
    res = apply_response_and_compute_delta(
        dim=dim, parsed=parsed, observation_type="tummy_time_timer",
        source_ref="2026-W45", observed_at=datetime.now(timezone.utc),
    )
    assert res["status"] == "dry_run"
    assert res["delta_kl"] is None
    assert "evidence_hash" in res
    assert res["dim_name"] == "head_control_seconds"


def test_boolean_payload_shape() -> None:
    dim = _get_dim("respiratory_apnea_per_day")
    parsed = parse_response("no", expected_format="boolean")
    ev = parsed_response_to_evidence(
        dim=dim, parsed=parsed, observation_type="monitor_apnea_count",
        source_ref="x", observed_at=datetime.now(timezone.utc),
    )
    assert ev.value["bool"] is False
