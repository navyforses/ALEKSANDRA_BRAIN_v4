"""Phase 7.3 Layer C Day 13 — viz.py tests (matplotlib PNG export)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from brain.sim.scenario import build_reference_scenario
from brain.sim.trajectory import simulate_scenario
from brain.sim.viz import (
    MIN_PNG_BYTES,
    render_comparison_panel,
    render_scenario_histogram,
    render_scenario_summary_panel,
)


# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def reference_arr():
    """A 100-sample reference trajectory array (cached for the module)."""
    scenario = build_reference_scenario()
    return scenario, simulate_scenario(scenario)


# ---------------------------------------------------------------------------
# Single-histogram tests
# ---------------------------------------------------------------------------
def test_single_histogram_writes_png_above_10kb(
    reference_arr, tmp_path: Path
):
    scenario, arr = reference_arr
    path = render_scenario_histogram(
        arr,
        scenario_name=scenario.name,
        outcome=scenario.outcomes[0],
        outcome_index=0,
        day=10,
        out_dir=tmp_path,
    )
    assert path.exists()
    assert path.stat().st_size > MIN_PNG_BYTES


def test_single_histogram_auto_creates_output_dir(
    reference_arr, tmp_path: Path
):
    scenario, arr = reference_arr
    nested = tmp_path / "deep" / "nested" / "dir"
    # nested does not exist; viz must mkdir parents
    assert not nested.exists()
    path = render_scenario_histogram(
        arr,
        scenario_name=scenario.name,
        outcome=scenario.outcomes[0],
        outcome_index=0,
        day=0,
        out_dir=nested,
    )
    assert path.exists()
    # parent should be nested / scenario_name
    assert path.parent.parent == nested


def test_single_histogram_raises_indexerror_on_bad_outcome_index(
    reference_arr, tmp_path: Path
):
    scenario, arr = reference_arr
    with pytest.raises(IndexError):
        render_scenario_histogram(
            arr,
            scenario_name=scenario.name,
            outcome="bad",
            outcome_index=999,
            day=0,
            out_dir=tmp_path,
        )


def test_single_histogram_raises_valueerror_on_non_3d_array(tmp_path: Path):
    arr_2d = np.zeros((10, 5))
    with pytest.raises(ValueError, match="3-D"):
        render_scenario_histogram(
            arr_2d,  # type: ignore[arg-type]
            scenario_name="x",
            outcome="y",
            outcome_index=0,
            day=0,
            out_dir=tmp_path,
        )


# ---------------------------------------------------------------------------
# Summary panel tests
# ---------------------------------------------------------------------------
def test_summary_panel_writes_one_png_per_outcome(
    reference_arr, tmp_path: Path
):
    scenario, arr = reference_arr
    paths = render_scenario_summary_panel(
        arr,
        scenario=scenario,
        day=50,
        out_dir=tmp_path,
    )
    assert len(paths) == len(scenario.outcomes)
    for path in paths:
        assert path.exists()
        assert path.stat().st_size > MIN_PNG_BYTES


def test_summary_panel_raises_on_outcome_mismatch(tmp_path: Path):
    scenario = build_reference_scenario()
    # arr second axis mismatches len(scenario.outcomes)=5
    arr_bad = np.zeros((10, 2, scenario.horizon_days + 1))
    with pytest.raises(IndexError, match="outcomes"):
        render_scenario_summary_panel(
            arr_bad,
            scenario=scenario,
            day=0,
            out_dir=tmp_path,
        )


# ---------------------------------------------------------------------------
# Comparison panel tests
# ---------------------------------------------------------------------------
def test_comparison_panel_writes_one_png_per_outcome(
    reference_arr, tmp_path: Path
):
    scenario, arr = reference_arr
    paths = render_comparison_panel(
        arr,
        arr,
        scenario_a_name=scenario.name,
        scenario_b_name=scenario.name + "_alt",
        outcomes=scenario.outcomes,
        day=200,
        out_dir=tmp_path,
    )
    assert len(paths) == len(scenario.outcomes)
    for path in paths:
        assert path.exists()
        assert path.stat().st_size > MIN_PNG_BYTES


def test_comparison_panel_rejects_incompatible_shapes(tmp_path: Path):
    arr_a = np.zeros((10, 3, 5))
    arr_b = np.zeros((10, 5, 5))
    with pytest.raises(ValueError, match="incompatible"):
        render_comparison_panel(
            arr_a,
            arr_b,
            scenario_a_name="a",
            scenario_b_name="b",
            outcomes=["o1", "o2", "o3"],
            day=0,
            out_dir=tmp_path,
        )
