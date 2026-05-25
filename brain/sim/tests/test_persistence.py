"""Phase 7.3 Layer C Day 11 — persistence.py tests (DRY_RUN-mode only).

All tests run with ``SUPABASE_DB_URL`` unset, exercising the DRY_RUN
fallback that returns ``"DRY_RUN:<sha>"`` sentinels and empty reads. The
production-mode path (live DB) is covered by the verifier in
``--mode production`` and is not exercised here to keep the test suite
infrastructure-free.
"""

from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from brain.sim.aggregator import aggregate_trajectories
from brain.sim.compare import compare_scenarios, default_prefer_higher_map
from brain.sim.persistence import (
    ALLOWED_ENGINES,
    ScenarioComparisonRecord,
    ScenarioRecord,
    SimulationRunRecord,
    delete_scenario,
    get_scenario,
    json_to_scenario,
    list_scenarios,
    save_scenario,
    save_scenario_comparison,
    save_simulation_run,
    scenario_to_json,
)
from brain.sim.scenario import build_reference_scenario, compute_scenario_hash
from brain.sim.trajectory import simulate_scenario


# ---------------------------------------------------------------------------
# Fixture: guarantee DRY_RUN mode for every test (DSN unset).
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _ensure_dry_run(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)


# ---------------------------------------------------------------------------
# save_scenario
# ---------------------------------------------------------------------------
def test_save_scenario_dry_run_returns_sentinel():
    scenario = build_reference_scenario()
    out = save_scenario(scenario, created_by="pytest")
    assert isinstance(out, str)
    assert out.startswith("DRY_RUN:")
    # sha256 hex is 64 chars; sentinel total is "DRY_RUN:" + 64
    assert len(out) == 8 + 64


def test_save_scenario_dry_run_deterministic_for_same_scenario():
    scenario = build_reference_scenario()
    s1 = save_scenario(scenario, created_by="pytest")
    s2 = save_scenario(scenario, created_by="pytest")
    assert s1 == s2  # same payload + same op -> same sentinel


def test_save_scenario_requires_nonempty_created_by():
    scenario = build_reference_scenario()
    with pytest.raises(ValueError, match="created_by"):
        save_scenario(scenario, created_by="")
    with pytest.raises(ValueError, match="created_by"):
        save_scenario(scenario, created_by="   ")


# ---------------------------------------------------------------------------
# get_scenario / list_scenarios / delete_scenario
# ---------------------------------------------------------------------------
def test_get_scenario_dry_run_returns_none():
    assert get_scenario("never_existed") is None


def test_list_scenarios_dry_run_returns_empty():
    rows = list_scenarios()
    assert isinstance(rows, list)
    assert rows == []


def test_delete_scenario_dry_run_returns_zero():
    assert delete_scenario("never_existed") == 0


# ---------------------------------------------------------------------------
# save_simulation_run
# ---------------------------------------------------------------------------
def test_save_simulation_run_dry_run_returns_sentinel():
    scenario = build_reference_scenario()
    arr = simulate_scenario(scenario)
    summary = aggregate_trajectories(arr, scenario=scenario, elapsed_seconds=1.0)
    out = save_simulation_run(
        scenario_id="DRY_RUN:" + "0" * 64,
        engine="monte_carlo",
        n_samples=scenario.n_samples,
        duration_ms_sim=None,
        elapsed_seconds=1.0,
        summary=summary,
    )
    assert isinstance(out, str)
    assert out.startswith("DRY_RUN:")


def test_save_simulation_run_rejects_unknown_engine():
    scenario = build_reference_scenario()
    arr = simulate_scenario(scenario)
    summary = aggregate_trajectories(arr, scenario=scenario, elapsed_seconds=1.0)
    with pytest.raises(ValueError, match="engine"):
        save_simulation_run(
            scenario_id="DRY_RUN:abc",
            engine="quantum",  # not in ALLOWED_ENGINES
            n_samples=10,
            duration_ms_sim=None,
            elapsed_seconds=1.0,
            summary=summary,
        )


def test_save_simulation_run_rejects_negative_elapsed():
    scenario = build_reference_scenario()
    arr = simulate_scenario(scenario)
    summary = aggregate_trajectories(arr, scenario=scenario, elapsed_seconds=1.0)
    with pytest.raises(ValueError, match="elapsed_seconds"):
        save_simulation_run(
            scenario_id="DRY_RUN:abc",
            engine="monte_carlo",
            n_samples=10,
            duration_ms_sim=None,
            elapsed_seconds=-0.001,
            summary=summary,
        )


# ---------------------------------------------------------------------------
# save_scenario_comparison
# ---------------------------------------------------------------------------
def test_save_scenario_comparison_dry_run_returns_sentinel():
    scenario = build_reference_scenario()
    arr = simulate_scenario(scenario)
    summary = aggregate_trajectories(arr, scenario=scenario, elapsed_seconds=1.0)
    comparison = compare_scenarios(
        summary,
        summary,
        arr,
        arr,
        prefer_higher=default_prefer_higher_map(),
    )
    out = save_scenario_comparison(
        scenario_a_id="DRY_RUN:" + "0" * 64,
        scenario_b_id="DRY_RUN:" + "1" * 64,
        comparison=comparison,
    )
    assert isinstance(out, str)
    assert out.startswith("DRY_RUN:")


# ---------------------------------------------------------------------------
# Pydantic record validation
# ---------------------------------------------------------------------------
def test_scenario_record_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ScenarioRecord(
            name="x",
            scenario_json={},
            scenario_hash="a" * 64,
            created_by="pytest",
            extra_field="boom",  # type: ignore[call-arg]
        )


def test_simulation_run_record_rejects_extra_fields():
    with pytest.raises(ValidationError):
        SimulationRunRecord(
            engine="monte_carlo",
            summary_json={},
            extra_field="boom",  # type: ignore[call-arg]
        )


def test_simulation_run_record_engine_must_be_allowed():
    with pytest.raises(ValidationError):
        SimulationRunRecord(
            engine="quantum",  # type: ignore[arg-type]
            summary_json={},
        )


def test_scenario_comparison_record_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ScenarioComparisonRecord(
            delta_json={},
            p_a_better_json={},
            extra_field="boom",  # type: ignore[call-arg]
        )


def test_simulation_run_record_elapsed_seconds_must_be_nonneg():
    with pytest.raises(ValidationError):
        SimulationRunRecord(
            engine="monte_carlo",
            summary_json={},
            elapsed_seconds=-0.5,
        )


# ---------------------------------------------------------------------------
# scenario_to_json / json_to_scenario round-trip
# ---------------------------------------------------------------------------
def test_scenario_to_json_round_trip_preserves_reference_scenario():
    original = build_reference_scenario()
    payload = scenario_to_json(original)
    rebuilt = json_to_scenario(payload)
    assert rebuilt.name == original.name
    assert rebuilt.horizon_days == original.horizon_days
    assert rebuilt.n_samples == original.n_samples
    assert rebuilt.outcomes == original.outcomes
    assert len(rebuilt.interventions) == len(original.interventions)
    # Compare scenario hashes — they must collide since hash excludes
    # name + description + seed only.
    assert compute_scenario_hash(rebuilt) == compute_scenario_hash(original)


def test_json_to_scenario_rejects_non_dict_payload():
    with pytest.raises(ValueError, match="dict"):
        json_to_scenario("not a dict")  # type: ignore[arg-type]


def test_json_to_scenario_rejects_malformed_payload():
    # Missing required field horizon_days
    with pytest.raises(ValidationError):
        json_to_scenario({"name": "x"})


def test_allowed_engines_constant_matches_migration_019():
    assert ALLOWED_ENGINES == frozenset(
        {"monte_carlo", "tvb", "combined"}
    )


def test_get_scenario_dry_run_safely_silent():
    # Should not raise even when DSN absent.
    assert get_scenario("any") is None
    assert "SUPABASE_DB_URL" not in os.environ
