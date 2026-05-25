"""Phase 7.3 Layer C Days 12-14 — api.py tests (handler + budget guard).

All tests run with ``SUPABASE_DB_URL`` unset; DRY_RUN sentinels validated
end-to-end. Budget guard covers both the hard n_samples cap and the
sd/mean RULE-10 soft cap.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from brain.belief.persistence import BeliefDimension
from brain.belief.schema import load_dimensions_from_toml
from brain.sim.api import (
    BudgetGuardError,
    CompareScenariosRequest,
    CompareScenariosResponse,
    HARD_N_SAMPLES_CAP,
    ListScenariosResponse,
    SaveScenarioRequest,
    SaveScenarioResponse,
    check_simulation_budget,
    handle_compare_scenarios,
    handle_list_scenarios,
    handle_save_scenario,
)
from brain.sim.compare import CompareError
from brain.sim.persistence import scenario_to_json
from brain.sim.scenario import build_reference_scenario


# ---------------------------------------------------------------------------
# Fixture: guarantee DRY_RUN mode for every test (DSN unset).
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _ensure_dry_run(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)


# ---------------------------------------------------------------------------
# Pydantic request / response validation
# ---------------------------------------------------------------------------
def test_save_scenario_request_validates_min_payload():
    req = SaveScenarioRequest(
        scenario=scenario_to_json(build_reference_scenario()),
        created_by="pytest",
    )
    assert req.created_by == "pytest"


def test_save_scenario_request_rejects_extra_fields():
    with pytest.raises(ValidationError):
        SaveScenarioRequest(
            scenario={},
            created_by="pytest",
            unexpected="boom",  # type: ignore[call-arg]
        )


def test_save_scenario_response_rejects_extra_fields():
    with pytest.raises(ValidationError):
        SaveScenarioResponse(
            scenario_id="abc",
            scenario_hash="a" * 64,
            was_dry_run=True,
            unexpected="boom",  # type: ignore[call-arg]
        )


def test_compare_request_rejects_extra_fields():
    with pytest.raises(ValidationError):
        CompareScenariosRequest(
            scenario_a_name="a",
            scenario_b_name="b",
            unexpected="boom",  # type: ignore[call-arg]
        )


# ---------------------------------------------------------------------------
# handle_save_scenario
# ---------------------------------------------------------------------------
def test_handle_save_scenario_dry_run_returns_sentinel_response():
    scenario = build_reference_scenario()
    req = SaveScenarioRequest(
        scenario=scenario_to_json(scenario),
        created_by="pytest",
    )
    resp = handle_save_scenario(req)
    assert resp.scenario_id.startswith("DRY_RUN:")
    assert resp.was_dry_run is True
    assert len(resp.scenario_hash) == 64


def test_handle_save_scenario_payload_validation_failure_raises():
    req = SaveScenarioRequest(
        scenario={"name": "incomplete"},  # missing horizon_days etc.
        created_by="pytest",
    )
    with pytest.raises(ValidationError):
        handle_save_scenario(req)


# ---------------------------------------------------------------------------
# handle_list_scenarios
# ---------------------------------------------------------------------------
def test_handle_list_scenarios_dry_run_empty():
    resp = handle_list_scenarios()
    assert isinstance(resp, ListScenariosResponse)
    assert resp.count == 0
    assert resp.scenarios == []


# ---------------------------------------------------------------------------
# handle_compare_scenarios
# ---------------------------------------------------------------------------
def test_handle_compare_scenarios_with_inline_payload_dry_run():
    scenario_a = build_reference_scenario()
    scenario_b = build_reference_scenario()
    # Make B subtly different so the cache treats them as distinct.
    scenario_b_payload = scenario_to_json(scenario_b)
    scenario_b_payload["name"] = "alt_scenario"
    # Tweak first intervention dose so the canonical hash differs.
    scenario_b_payload["interventions"][0]["dose_mg_kg"] = 75.0

    req = CompareScenariosRequest(
        scenario_a_name=scenario_a.name,
        scenario_b_name="alt_scenario",
        scenario_a_payload=scenario_to_json(scenario_a),
        scenario_b_payload=scenario_b_payload,
    )
    resp = handle_compare_scenarios(req)
    assert isinstance(resp, CompareScenariosResponse)
    assert resp.comparison_id.startswith("DRY_RUN:")
    assert resp.was_dry_run is True
    assert resp.summary_a_hash != resp.summary_b_hash


def test_handle_compare_scenarios_mismatched_outcomes_raises_compare_error():
    scenario_a = build_reference_scenario()
    scenario_b_payload = scenario_to_json(scenario_a)
    scenario_b_payload["name"] = "different_outcomes"
    # Drop one outcome to provoke CompareError downstream.
    scenario_b_payload["outcomes"] = ["seizure_freq_per_day"]
    req = CompareScenariosRequest(
        scenario_a_name=scenario_a.name,
        scenario_b_name="different_outcomes",
        scenario_a_payload=scenario_to_json(scenario_a),
        scenario_b_payload=scenario_b_payload,
    )
    with pytest.raises(CompareError):
        handle_compare_scenarios(req)


def test_handle_compare_scenarios_missing_payload_in_dry_run_raises():
    req = CompareScenariosRequest(
        scenario_a_name="never_saved",
        scenario_b_name="also_never_saved",
        # no payloads supplied
    )
    with pytest.raises(ValueError, match="not found"):
        handle_compare_scenarios(req)


# ---------------------------------------------------------------------------
# Budget guard
# ---------------------------------------------------------------------------
def test_budget_guard_rejects_n_samples_above_cap():
    # Build a scenario whose n_samples is exactly the cap + 1.
    # Scenario.n_samples Field validator caps at 10_000; we instead
    # bypass via model_construct to test the api.py guard directly.
    scenario = build_reference_scenario()
    scenario = scenario.model_copy(update={"n_samples": HARD_N_SAMPLES_CAP})
    # n_samples == cap should pass the n_samples branch (the dim guard
    # is separately enforced by the next test).
    # Bump just above the cap via model_construct since the Pydantic
    # validator clamps:
    scenario_oversize = scenario.model_construct(
        **{**scenario.model_dump(), "n_samples": HARD_N_SAMPLES_CAP + 1}
    )
    with pytest.raises(BudgetGuardError, match="n_samples"):
        check_simulation_budget(scenario_oversize)


def test_budget_guard_rejects_high_uncertainty_dim_set():
    scenario = build_reference_scenario()
    # Build a 13-dim catalog where every dim has sd/mean > 0.5 so the
    # guard refuses. Use Normal mu=1, sigma=10 (ratio = 10) for all.
    high_uncertainty_dims: list[BeliefDimension] = []
    for i in range(13):
        high_uncertainty_dims.append(
            BeliefDimension(
                name=f"synthetic_high_unc_{i}",
                distribution="normal",
                prior_params={"mu": 1.0, "sigma": 10.0},
                units="z",
                valid_min=-50.0,
                valid_max=50.0,
                citation="PMID:0000000",
            )
        )
    with pytest.raises(BudgetGuardError, match="dimensions pass"):
        check_simulation_budget(scenario, dims=high_uncertainty_dims)


def test_budget_guard_error_message_mentions_failing_dim():
    scenario = build_reference_scenario()
    # 8 dims fail, 5 dims pass — should fail the 7/13 threshold.
    dims_mixed: list[BeliefDimension] = []
    for i in range(8):
        dims_mixed.append(
            BeliefDimension(
                name=f"high_unc_{i}",
                distribution="normal",
                prior_params={"mu": 1.0, "sigma": 10.0},
                units="z",
                valid_min=-50.0,
                valid_max=50.0,
                citation="PMID:0000000",
            )
        )
    for i in range(5):
        dims_mixed.append(
            BeliefDimension(
                name=f"low_unc_{i}",
                distribution="normal",
                prior_params={"mu": 100.0, "sigma": 1.0},
                units="z",
                valid_min=0.0,
                valid_max=200.0,
                citation="PMID:0000000",
            )
        )
    with pytest.raises(BudgetGuardError) as exc_info:
        check_simulation_budget(scenario, dims=dims_mixed)
    msg = str(exc_info.value)
    assert "high_unc_" in msg  # at least one failing-dim name surfaced


def test_budget_guard_reference_scenario_passes():
    # Spec requires the reference scenario to pass the budget guard.
    scenario = build_reference_scenario()
    check_simulation_budget(scenario)  # must not raise


def test_budget_guard_n_samples_at_exactly_cap_passes():
    scenario = build_reference_scenario()
    at_cap = scenario.model_copy(update={"n_samples": HARD_N_SAMPLES_CAP})
    # at-cap must NOT raise on the n_samples branch (uncertainty guard
    # then applies and the reference scenario passes 7/13).
    check_simulation_budget(at_cap)


def test_budget_guard_passes_when_7_of_13_dims_satisfy_ratio():
    scenario = build_reference_scenario()
    # 7 passing + 6 failing dims -> threshold exactly met.
    dims_boundary: list[BeliefDimension] = []
    for i in range(7):
        dims_boundary.append(
            BeliefDimension(
                name=f"ok_{i}",
                distribution="normal",
                prior_params={"mu": 100.0, "sigma": 1.0},
                units="z",
                valid_min=0.0,
                valid_max=200.0,
                citation="PMID:0000000",
            )
        )
    for i in range(6):
        dims_boundary.append(
            BeliefDimension(
                name=f"bad_{i}",
                distribution="normal",
                prior_params={"mu": 1.0, "sigma": 10.0},
                units="z",
                valid_min=-50.0,
                valid_max=50.0,
                citation="PMID:0000000",
            )
        )
    check_simulation_budget(scenario, dims=dims_boundary)
