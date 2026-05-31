"""Phase 7.3 Day 2 — trajectory.py tests."""

from __future__ import annotations

import time

import numpy as np

from brain.belief.schema import load_dimensions_from_toml
from brain.causal.scm import build_reference_scm
from brain.sim.scenario import (
    Intervention,
    Scenario,
    build_reference_scenario,
)
from brain.sim.trajectory import (
    VIGABATRIN_TARGET_DIM,
    simulate_scenario,
    simulate_trajectory,
)


# ---------------------------------------------------------------------------
# Shape + types
# ---------------------------------------------------------------------------
def test_single_sample_reference_returns_3d_array():
    s = build_reference_scenario().model_copy(update={"n_samples": 10})
    arr = simulate_scenario(s)
    assert arr.shape == (10, len(s.outcomes), s.horizon_days + 1)
    assert arr.dtype == np.float64
    assert not np.any(np.isnan(arr))


# ---------------------------------------------------------------------------
# Wall-time budget — verifier check #2 target: 100 samples < 60s.
# ---------------------------------------------------------------------------
def test_100_sample_reference_under_60s():
    s = build_reference_scenario()  # n_samples=100, horizon=400
    t0 = time.perf_counter()
    arr = simulate_scenario(s, reference_scm=build_reference_scm())
    elapsed = time.perf_counter() - t0
    assert arr.shape == (100, 5, 401)
    assert elapsed < 60.0, f"100-sample run took {elapsed:.2f}s (cap 60s)"


# ---------------------------------------------------------------------------
# Vigabatrin reduces seizure-frequency at day-400 (mediator path)
# ---------------------------------------------------------------------------
def test_vigabatrin_reduces_seizure_frequency_at_horizon():
    """With reference SCM + Vigabatrin, day-400 seizure mean is below
    the no-intervention baseline at the same seed."""
    with_vigabatrin = build_reference_scenario().model_copy(
        update={"n_samples": 60}
    )
    no_intervention = with_vigabatrin.model_copy(
        update={"interventions": []}
    )

    arr_treat = simulate_scenario(
        with_vigabatrin, reference_scm=build_reference_scm()
    )
    arr_ctrl = simulate_scenario(no_intervention)

    seizure_idx = with_vigabatrin.outcomes.index(VIGABATRIN_TARGET_DIM)
    mean_treat = float(arr_treat[:, seizure_idx, -1].mean())
    mean_ctrl = float(arr_ctrl[:, seizure_idx, -1].mean())
    assert mean_treat < mean_ctrl, (
        f"expected vigabatrin to reduce seizure freq at day-400 "
        f"(treat={mean_treat:.3f}, ctrl={mean_ctrl:.3f})"
    )


# ---------------------------------------------------------------------------
# Manual dimension shift clipping
# ---------------------------------------------------------------------------
def test_manual_dimension_shift_clips_to_valid_max():
    s = Scenario(
        name="huge_shift",
        interventions=[
            Intervention(
                type="manual_dimension_shift",
                name="bayley_to_ceiling",
                start_day=5,
                target_dimension="bayley_cognitive",
                dimension_delta=9999.0,
                frequency="once",
            )
        ],
        horizon_days=20,
        n_samples=10,
        outcomes=["bayley_cognitive"],
        random_seed=0,
    )
    arr = simulate_scenario(s)
    # Bayley dim valid_max = 160 per dimensions.toml
    assert float(arr[:, 0, -1].max()) <= 160.0 + 1e-9


def test_manual_dimension_shift_clips_to_valid_min():
    s = Scenario(
        name="negative_shift",
        interventions=[
            Intervention(
                type="manual_dimension_shift",
                name="seizure_floor",
                start_day=5,
                target_dimension="seizure_freq_per_day",
                dimension_delta=-9999.0,
                frequency="once",
            )
        ],
        horizon_days=20,
        n_samples=10,
        outcomes=["seizure_freq_per_day"],
        random_seed=0,
    )
    arr = simulate_scenario(s)
    assert float(arr[:, 0, :].min()) >= 0.0 - 1e-9


# ---------------------------------------------------------------------------
# Weekly frequency only fires every 7 days
# ---------------------------------------------------------------------------
def test_weekly_frequency_only_fires_every_seven_days():
    s = Scenario(
        name="weekly_drug",
        interventions=[
            Intervention(
                type="manual_dimension_shift",
                name="weekly_boost",
                start_day=0,
                frequency="weekly",
                duration_days=30,
                target_dimension="head_control_seconds",
                dimension_delta=1.0,
            )
        ],
        horizon_days=21,  # days 0..21 inclusive
        n_samples=10,
        outcomes=["head_control_seconds"],
        random_seed=7,
    )
    dims = load_dimensions_from_toml()
    traj = simulate_trajectory(s, dims=dims, sample_id=0)
    series = traj["head_control_seconds"]
    # Differences from previous day: weekly delta should land on days 7, 14, 21.
    diffs = np.diff(series)
    expected_fire_days = {6, 13, 20}  # diff index = day-1
    fired = {i for i, d in enumerate(diffs) if d > 0.5}
    assert expected_fire_days <= fired, f"expected boosts on {expected_fire_days}, got {fired}"


# ---------------------------------------------------------------------------
# Determinism — same seed -> identical output
# ---------------------------------------------------------------------------
def test_trajectory_determinism_same_seed_same_output():
    s = build_reference_scenario().model_copy(update={"n_samples": 8})
    arr1 = simulate_scenario(s, reference_scm=build_reference_scm())
    arr2 = simulate_scenario(s, reference_scm=build_reference_scm())
    assert np.array_equal(arr1, arr2)


# ---------------------------------------------------------------------------
# cell_therapy with infusion_day-only (start_day is required by schema, so
# we set both to the same value to exercise the cell-therapy branch).
# ---------------------------------------------------------------------------
def test_cell_therapy_infusion_day_runs():
    s = Scenario(
        name="cord_blood_only",
        interventions=[
            Intervention(
                type="cell_therapy",
                name="cord_blood",
                start_day=10,
                infusion_day=10,
                frequency="once",
                effect_per_dim={"bayley_cognitive": 0.5},
            )
        ],
        horizon_days=20,
        n_samples=10,
        outcomes=["bayley_cognitive"],
        random_seed=11,
    )
    arr = simulate_scenario(s)
    assert arr.shape == (10, 1, 21)
    # Day-10 value should be >= day-9 (one-shot boost was applied)
    means = arr[:, 0, :].mean(axis=0)
    assert means[10] >= means[9] - 1e-6
