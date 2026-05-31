"""Phase 7.3 Layer C Day 13 — matplotlib histogram PNG export for scenarios.

Mirrors ``brain/belief/viz.py`` (matplotlib Agg backend) for PNG snapshot
generation. Spec called for Plotly + Kaleido server-side rendering;
Plotly / Kaleido are NOT installed in ``.venv-v7`` and Phase 7.3 explicitly
substitutes matplotlib to stay infra-free and consistent with the Phase
7.0 belief viz path.

Three entry points:

    render_scenario_histogram      — one (outcome, day) histogram PNG.
    render_scenario_summary_panel  — N PNGs, one per scenario.outcomes.
    render_comparison_panel        — side-by-side A vs B for each outcome.

Snapshots land under
``brain/sim/snapshots/{scenario_name}/{outcome}_day{day}.png``. The
verifier (check 10) enforces a 10 KB floor per PNG.

Hard rules:
    - matplotlib Agg backend forced BEFORE pyplot import (headless safety).
    - No PHI in figures; titles use scenario_name + outcome name only.
    - Output dir auto-created with ``mkdir(parents=True, exist_ok=True)``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # MUST precede pyplot import
import matplotlib.pyplot as plt
import numpy as np

from brain.sim.scenario import Scenario


DEFAULT_SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
HIST_BINS = 50
FIG_SIZE = (8.0, 5.0)
FIG_DPI = 100
MIN_PNG_BYTES = 10 * 1024  # verifier check 10 floor


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _resolve_scenario_dir(out_dir: Optional[Path], scenario_name: str) -> Path:
    """Build the per-scenario output directory and ensure it exists."""
    root = Path(out_dir) if out_dir is not None else DEFAULT_SNAPSHOT_DIR
    target = root / scenario_name
    target.mkdir(parents=True, exist_ok=True)
    return target


def _safe_file_token(value: str) -> str:
    """Strip filesystem-hostile chars from outcome names."""
    return "".join(c if c.isalnum() or c in {"-", "_"} else "_" for c in value)


# ---------------------------------------------------------------------------
# Single-outcome histogram
# ---------------------------------------------------------------------------
def render_scenario_histogram(
    arr: np.ndarray,
    *,
    scenario_name: str,
    outcome: str,
    outcome_index: int,
    day: int,
    out_dir: Optional[Path] = None,
) -> Path:
    """Render one (outcome, day) histogram PNG and return its path.

    Args:
        arr: 3-D trajectory array of shape
            ``(n_samples, n_outcomes, horizon_days + 1)``.
        scenario_name: scenario identifier (used in the title + filename).
        outcome: outcome dimension name (used in the y-axis label + title).
        outcome_index: index into ``arr[:, outcome_index, day]``.
        day: which day-step to slice.
        out_dir: optional base directory; defaults to
            ``brain/sim/snapshots/``.

    Returns:
        Path to the written PNG.

    Raises:
        IndexError: ``outcome_index`` out of range OR ``day`` out of range.
        ValueError: ``arr`` is not 3-D.
    """
    if arr.ndim != 3:
        raise ValueError(
            f"arr must be 3-D (n_samples, n_outcomes, n_steps); "
            f"got shape {arr.shape}"
        )
    n_samples, n_outcomes, n_steps = arr.shape
    if not 0 <= outcome_index < n_outcomes:
        raise IndexError(
            f"outcome_index={outcome_index} out of range [0, {n_outcomes - 1}]"
        )
    if not 0 <= day < n_steps:
        raise IndexError(
            f"day={day} out of range [0, {n_steps - 1}]"
        )

    target_dir = _resolve_scenario_dir(out_dir, scenario_name)
    file_name = f"{_safe_file_token(outcome)}_day{day}.png"
    out_path = target_dir / file_name

    samples = arr[:, outcome_index, day]

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    try:
        ax.hist(
            samples,
            bins=HIST_BINS,
            color="#1f77b4",
            alpha=0.7,
            edgecolor="white",
        )
        mean_val = float(np.mean(samples))
        ax.axvline(
            mean_val,
            color="#d62728",
            linestyle="--",
            linewidth=1.5,
            label=f"mean = {mean_val:.3g}",
        )
        ax.set_title(
            f"{scenario_name}  -  {outcome}  -  day {day}",
            fontsize=11,
        )
        ax.set_xlabel(outcome)
        ax.set_ylabel(f"count of n={n_samples} samples")
        ax.legend(loc="best", fontsize=8)
        ax.grid(alpha=0.25)
        fig.text(
            0.02,
            0.02,
            f"Phase 7.3 Layer C viz  |  generated "
            f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}",
            fontsize=7,
            alpha=0.55,
        )
        fig.savefig(out_path, dpi=FIG_DPI, bbox_inches="tight")
    finally:
        plt.close(fig)

    return out_path


# ---------------------------------------------------------------------------
# Per-scenario summary panel (one PNG per outcome)
# ---------------------------------------------------------------------------
def render_scenario_summary_panel(
    arr: np.ndarray,
    *,
    scenario: Scenario,
    day: int,
    out_dir: Optional[Path] = None,
) -> list[Path]:
    """Render one histogram per scenario outcome at the given day.

    Returns the list of written paths (one per element of
    ``scenario.outcomes``).

    Raises:
        IndexError: ``day`` out of range OR ``len(scenario.outcomes)``
            mismatch with ``arr.shape[1]``.
        ValueError: ``arr`` is not 3-D.
    """
    if arr.ndim != 3:
        raise ValueError(
            f"arr must be 3-D (n_samples, n_outcomes, n_steps); "
            f"got shape {arr.shape}"
        )
    n_outcomes = arr.shape[1]
    if n_outcomes != len(scenario.outcomes):
        raise IndexError(
            f"arr.shape[1]={n_outcomes} != len(scenario.outcomes)="
            f"{len(scenario.outcomes)}"
        )
    paths: list[Path] = []
    for j, outcome in enumerate(scenario.outcomes):
        path = render_scenario_histogram(
            arr,
            scenario_name=scenario.name,
            outcome=outcome,
            outcome_index=j,
            day=day,
            out_dir=out_dir,
        )
        paths.append(path)
    return paths


# ---------------------------------------------------------------------------
# Side-by-side A-vs-B comparison panel
# ---------------------------------------------------------------------------
def render_comparison_panel(
    arr_a: np.ndarray,
    arr_b: np.ndarray,
    *,
    scenario_a_name: str,
    scenario_b_name: str,
    outcomes: list[str],
    day: int,
    out_dir: Optional[Path] = None,
) -> list[Path]:
    """Render one side-by-side A vs B PNG per outcome at the given day.

    The PNG file lands under
    ``{out_dir}/compare_{scenario_a_name}_vs_{scenario_b_name}/
    {outcome}_day{day}.png``.

    Raises:
        ValueError: shape mismatch between arr_a and arr_b.
        IndexError: day out of range OR outcome list length mismatch.
    """
    if arr_a.ndim != 3 or arr_b.ndim != 3:
        raise ValueError(
            f"arr_a and arr_b must be 3-D; got {arr_a.shape}, {arr_b.shape}"
        )
    if arr_a.shape[1:] != arr_b.shape[1:]:
        raise ValueError(
            f"trajectory shapes incompatible (outcome/day axis): "
            f"A={arr_a.shape}, B={arr_b.shape}"
        )
    n_outcomes_arr = arr_a.shape[1]
    if n_outcomes_arr != len(outcomes):
        raise IndexError(
            f"arr.shape[1]={n_outcomes_arr} != len(outcomes)={len(outcomes)}"
        )
    if not 0 <= day < arr_a.shape[2]:
        raise IndexError(
            f"day={day} out of range [0, {arr_a.shape[2] - 1}]"
        )

    panel_dir_name = f"compare_{scenario_a_name}_vs_{scenario_b_name}"
    target_dir = _resolve_scenario_dir(out_dir, panel_dir_name)

    paths: list[Path] = []
    for j, outcome in enumerate(outcomes):
        samples_a = arr_a[:, j, day]
        samples_b = arr_b[:, j, day]

        fig, ax = plt.subplots(figsize=FIG_SIZE)
        try:
            ax.hist(
                samples_a,
                bins=HIST_BINS,
                alpha=0.55,
                color="#1f77b4",
                edgecolor="white",
                label=scenario_a_name,
            )
            ax.hist(
                samples_b,
                bins=HIST_BINS,
                alpha=0.55,
                color="#ff7f0e",
                edgecolor="white",
                label=scenario_b_name,
            )
            mean_a = float(np.mean(samples_a))
            mean_b = float(np.mean(samples_b))
            ax.axvline(
                mean_a,
                color="#1f77b4",
                linestyle="--",
                linewidth=1.2,
            )
            ax.axvline(
                mean_b,
                color="#ff7f0e",
                linestyle="--",
                linewidth=1.2,
            )
            ax.set_title(
                f"{scenario_a_name}  vs  {scenario_b_name}  -  "
                f"{outcome}  -  day {day}",
                fontsize=10,
            )
            ax.set_xlabel(outcome)
            ax.set_ylabel("sample count")
            ax.legend(loc="best", fontsize=8)
            ax.grid(alpha=0.25)
            fig.text(
                0.02,
                0.02,
                f"Phase 7.3 Layer C viz  |  delta_mean="
                f"{(mean_b - mean_a):+.3g}",
                fontsize=7,
                alpha=0.6,
            )
            file_name = f"{_safe_file_token(outcome)}_day{day}.png"
            out_path = target_dir / file_name
            fig.savefig(out_path, dpi=FIG_DPI, bbox_inches="tight")
        finally:
            plt.close(fig)
        paths.append(out_path)

    return paths


__all__ = [
    "DEFAULT_SNAPSHOT_DIR",
    "HIST_BINS",
    "FIG_SIZE",
    "FIG_DPI",
    "MIN_PNG_BYTES",
    "render_scenario_histogram",
    "render_scenario_summary_panel",
    "render_comparison_panel",
]
