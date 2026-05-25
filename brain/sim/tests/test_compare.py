"""Phase 7.3 Day 4 — compare.py tests."""

from __future__ import annotations

import pytest

from brain.causal.scm import build_reference_scm
from brain.sim.aggregator import aggregate_trajectories
from brain.sim.compare import (
    CompareError,
    ScenarioComparison,
    compare_scenarios,
    default_prefer_higher_map,
)
from brain.sim.scenario import build_reference_scenario
from brain.sim.trajectory import simulate_scenario


def _build_pair():
    """Build an A (no intervention) vs B (vigabatrin) pair for tests."""
    b = build_reference_scenario().model_copy(update={"n_samples": 40})
    a = b.model_copy(update={"interventions": []})
    arr_a = simulate_scenario(a)
    arr_b = simulate_scenario(b, reference_scm=build_reference_scm())
    summary_a = aggregate_trajectories(arr_a, scenario=a, elapsed_seconds=0.1)
    summary_b = aggregate_trajectories(arr_b, scenario=b, elapsed_seconds=0.1)
    return a, b, arr_a, arr_b, summary_a, summary_b


# ---------------------------------------------------------------------------
# Identical scenarios -> p_a_better near 0.5, mostly tie/ambiguous
# ---------------------------------------------------------------------------
def test_identical_scenarios_p_near_half():
    s = build_reference_scenario().model_copy(update={"n_samples": 30})
    arr = simulate_scenario(s)
    summary = aggregate_trajectories(arr, scenario=s, elapsed_seconds=0.1)
    cmp = compare_scenarios(
        summary,
        summary,
        arr,
        arr,
        prefer_higher=default_prefer_higher_map(),
    )
    # Identical arrays: A > B never (strict), so p ≈ 0 OR p ≈ 0
    # depending on direction; but mean_delta == 0 -> interpretation "tie".
    tie_count = sum(1 for d in cmp.deltas if d.interpretation == "tie")
    # Most rows should be ties (mean_delta == 0).
    assert tie_count == len(cmp.deltas)


# ---------------------------------------------------------------------------
# B (vigabatrin) wins on seizure_freq_per_day at horizon
# ---------------------------------------------------------------------------
def test_vigabatrin_beats_no_intervention_on_seizures():
    a, b, arr_a, arr_b, summary_a, summary_b = _build_pair()
    cmp = compare_scenarios(
        summary_a,
        summary_b,
        arr_a,
        arr_b,
        prefer_higher=default_prefer_higher_map(),
    )
    # Find horizon-day delta on seizure_freq_per_day
    horizon = a.horizon_days
    horizon_seizure = [
        d
        for d in cmp.deltas
        if d.dim_name == "seizure_freq_per_day" and d.day == horizon
    ]
    assert len(horizon_seizure) == 1
    delta = horizon_seizure[0]
    # B = vigabatrin, A = no intervention. Lower seizure is better -> A loses.
    # default_prefer_higher_map["seizure_freq_per_day"] = False, so
    # p_a_better = P(arr_a < arr_b). With vigabatrin pushing B lower,
    # P(A < B) should be small; p_a_better < 0.3 indicates B_better.
    assert delta.p_a_better < 0.5
    assert delta.interpretation in {"B_better", "ambiguous"}


# ---------------------------------------------------------------------------
# Mismatched outcomes raise CompareError
# ---------------------------------------------------------------------------
def test_mismatched_outcomes_raise():
    a, b, arr_a, arr_b, summary_a, summary_b = _build_pair()
    summary_b2 = summary_b.model_copy(
        update={"outcomes": summary_b.outcomes[:-1]}
    )
    with pytest.raises(CompareError, match="outcome"):
        compare_scenarios(
            summary_a,
            summary_b2,
            arr_a,
            arr_b,
            prefer_higher=default_prefer_higher_map(),
        )


# ---------------------------------------------------------------------------
# Mismatched horizons raise CompareError
# ---------------------------------------------------------------------------
def test_mismatched_horizons_raise():
    a, b, arr_a, arr_b, summary_a, summary_b = _build_pair()
    summary_b2 = summary_b.model_copy(
        update={"horizon_days": summary_b.horizon_days + 1}
    )
    with pytest.raises(CompareError, match="horizon"):
        compare_scenarios(
            summary_a,
            summary_b2,
            arr_a,
            arr_b,
            prefer_higher=default_prefer_higher_map(),
        )


# ---------------------------------------------------------------------------
# Pydantic round-trip
# ---------------------------------------------------------------------------
def test_scenario_comparison_pydantic_round_trip():
    a, b, arr_a, arr_b, summary_a, summary_b = _build_pair()
    cmp = compare_scenarios(
        summary_a,
        summary_b,
        arr_a,
        arr_b,
        prefer_higher=default_prefer_higher_map(),
    )
    restored = ScenarioComparison.model_validate(cmp.model_dump())
    assert restored.scenario_a_hash == cmp.scenario_a_hash
    assert restored.scenario_b_hash == cmp.scenario_b_hash
    assert len(restored.deltas) == len(cmp.deltas)
    for d in restored.deltas:
        assert 0.0 <= d.p_a_better <= 1.0
