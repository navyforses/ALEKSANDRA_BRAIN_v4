"""Phase 7.3 Day 3 — aggregator.py tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from brain.sim.aggregator import (
    OutcomeSummary,
    ScenarioSummary,
    aggregate_trajectories,
    summary_to_dataframe,
)
from brain.sim.scenario import build_reference_scenario
from brain.sim.trajectory import simulate_scenario


# ---------------------------------------------------------------------------
# Shape correctness
# ---------------------------------------------------------------------------
def test_aggregate_returns_one_row_per_outcome_day():
    s = build_reference_scenario()  # n_samples=100, horizon=400
    arr = simulate_scenario(s)
    summary = aggregate_trajectories(arr, scenario=s, elapsed_seconds=1.5)
    expected_rows = len(s.outcomes) * (s.horizon_days + 1)
    assert len(summary.summaries) == expected_rows
    assert summary.n_samples == 100
    assert summary.horizon_days == 400
    assert summary.outcomes == s.outcomes


# ---------------------------------------------------------------------------
# Pydantic validation
# ---------------------------------------------------------------------------
def test_scenario_summary_pydantic_round_trip():
    s = build_reference_scenario().model_copy(update={"n_samples": 10})
    arr = simulate_scenario(s)
    summary = aggregate_trajectories(arr, scenario=s, elapsed_seconds=0.1)
    dumped = summary.model_dump()
    restored = ScenarioSummary.model_validate(dumped)
    assert restored.scenario_hash == summary.scenario_hash
    assert len(restored.summaries) == len(summary.summaries)


# ---------------------------------------------------------------------------
# HDI ordering invariants
# ---------------------------------------------------------------------------
def test_hdi_80_narrower_than_hdi_95():
    s = build_reference_scenario().model_copy(update={"n_samples": 50})
    arr = simulate_scenario(s)
    summary = aggregate_trajectories(arr, scenario=s, elapsed_seconds=0.1)
    for row in summary.summaries:
        w80 = row.hdi_80_high - row.hdi_80_low
        w95 = row.hdi_95_high - row.hdi_95_low
        # 95% HDI must be at least as wide as 80% HDI (within fp slack)
        assert w95 + 1e-9 >= w80


# ---------------------------------------------------------------------------
# No NaN / inf in numeric fields
# ---------------------------------------------------------------------------
def test_no_nan_or_inf_in_aggregated_fields():
    s = build_reference_scenario().model_copy(update={"n_samples": 20})
    arr = simulate_scenario(s)
    summary = aggregate_trajectories(arr, scenario=s, elapsed_seconds=0.1)
    for row in summary.summaries:
        for field in (
            "mean",
            "sd",
            "hdi_80_low",
            "hdi_80_high",
            "hdi_95_low",
            "hdi_95_high",
        ):
            value = getattr(row, field)
            assert np.isfinite(value), f"{field} not finite: {value}"


# ---------------------------------------------------------------------------
# summary_to_dataframe
# ---------------------------------------------------------------------------
def test_summary_to_dataframe_round_trip():
    s = build_reference_scenario().model_copy(update={"n_samples": 10})
    arr = simulate_scenario(s)
    summary = aggregate_trajectories(arr, scenario=s, elapsed_seconds=0.1)
    df = summary_to_dataframe(summary)
    assert isinstance(df, pd.DataFrame)
    assert {"dim_name", "day", "mean", "sd"} <= set(df.columns)
    assert len(df) == len(summary.summaries)


# ---------------------------------------------------------------------------
# Shape-mismatch defensive error
# ---------------------------------------------------------------------------
def test_aggregate_wrong_shape_raises():
    s = build_reference_scenario()
    bad = np.zeros((2, 2))  # 2-D, not 3-D
    with pytest.raises(ValueError, match="3-D"):
        aggregate_trajectories(bad, scenario=s, elapsed_seconds=0.1)
