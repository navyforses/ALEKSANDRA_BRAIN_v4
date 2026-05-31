"""Phase 7.3 Day 4 — Two-scenario comparison engine.

Given two ScenarioSummary objects plus their raw trajectory arrays, this
module computes:

    - ``mean_delta = mean_B - mean_A`` per (outcome, day)
    - ``p_a_better`` = P(A's outcome beats B's outcome) per the
      ``prefer_higher`` map (True -> higher is better; False -> lower is)
    - ``interpretation`` ∈ {"A_better","B_better","tie","ambiguous"}

The default ``prefer_higher`` map encodes domain-aware preferences for
the 13 dimensions (e.g. seizure-frequency lower is better, Bayley
cognition higher is better).

Reference:
    - v7_architecture/70_PHASES/73_PHASE_7_3_SIMULATION_ENGINE_3W.md
      section 1 layer A Day 4 + verifier check 5.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from brain.sim.aggregator import ScenarioSummary


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------
class CompareError(ValueError):
    """Two summaries / arrays are not compatible for comparison."""


# ---------------------------------------------------------------------------
# Pydantic types
# ---------------------------------------------------------------------------
InterpretationLiteral = Literal["A_better", "B_better", "tie", "ambiguous"]


class OutcomeDelta(BaseModel):
    """Per (outcome, day) comparison result."""

    model_config = ConfigDict(extra="forbid")

    dim_name: str = Field(..., min_length=1)
    day: int = Field(..., ge=0)
    mean_delta: float
    p_a_better: float = Field(..., ge=0.0, le=1.0)
    interpretation: InterpretationLiteral


class ScenarioComparison(BaseModel):
    """A vs B Monte Carlo comparison."""

    model_config = ConfigDict(extra="forbid")

    scenario_a_hash: str = Field(..., min_length=64, max_length=64)
    scenario_b_hash: str = Field(..., min_length=64, max_length=64)
    deltas: list[OutcomeDelta]
    n_samples_a: int = Field(..., ge=1)
    n_samples_b: int = Field(..., ge=1)


# ---------------------------------------------------------------------------
# Default direction preferences for the 13 belief dimensions.
# ---------------------------------------------------------------------------
def default_prefer_higher_map() -> dict[str, bool]:
    """Per-dimension "higher is better" preference for the 13-D catalog.

    Keys mirror ``brain/belief/dimensions.toml``. Rationale per entry is
    in inline comments. Callers can override per-key.
    """
    return {
        # Functional capacities: higher = better
        "bayley_cognitive": True,
        "eye_tracking_seconds": True,
        "head_control_seconds": True,
        "feeding_stage": True,  # higher stage = more oral
        "neuroplasticity_resource": True,  # more remaining = better
        "family_readiness": True,  # higher index = more thriving
        "brainstem_function": True,  # 0=impaired, 2=intact
        # Pathology / load: lower = better
        "cyst_volume_pct": False,
        "seizure_freq_per_day": False,
        "respiratory_apnea_per_day": False,
        "gmfcs_level": False,  # 1=mild, 5=severe
        "muscle_tone_hammersmith": False,  # high tone = bad for HIE
        "csf_biomarkers": False,  # elevated z-score = injury
    }


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------
def compare_scenarios(
    summary_a: ScenarioSummary,
    summary_b: ScenarioSummary,
    arr_a: np.ndarray,
    arr_b: np.ndarray,
    *,
    prefer_higher: dict[str, bool],
) -> ScenarioComparison:
    """Compute per (outcome, day) deltas + P(A better than B).

    Args:
        summary_a / summary_b: pre-aggregated ScenarioSummary objects.
        arr_a / arr_b: raw 3-D trajectory arrays of shape
            ``(n_samples, n_outcomes, n_steps)``.
        prefer_higher: map per outcome name -> True if higher value is
            better, False if lower is better. Unmapped outcomes default
            to True ("higher is better").

    Raises:
        CompareError: when outcomes or horizons disagree.
    """
    if summary_a.outcomes != summary_b.outcomes:
        raise CompareError(
            f"outcome sets disagree: A={summary_a.outcomes!r} "
            f"vs B={summary_b.outcomes!r}"
        )
    if summary_a.horizon_days != summary_b.horizon_days:
        raise CompareError(
            f"horizon_days disagree: A={summary_a.horizon_days} "
            f"vs B={summary_b.horizon_days}"
        )
    if arr_a.shape[1:] != arr_b.shape[1:]:
        raise CompareError(
            f"trajectory array shapes incompatible: A={arr_a.shape}, B={arr_b.shape}"
        )

    n_steps = summary_a.horizon_days + 1
    outcomes = summary_a.outcomes

    # Pre-index summary rows for O(1) mean lookup.
    mean_a = {(s.dim_name, s.day): s.mean for s in summary_a.summaries}
    mean_b = {(s.dim_name, s.day): s.mean for s in summary_b.summaries}

    deltas: list[OutcomeDelta] = []
    for j, name in enumerate(outcomes):
        prefer_high = prefer_higher.get(name, True)
        for day in range(n_steps):
            ma = mean_a[(name, day)]
            mb = mean_b[(name, day)]
            mean_delta = float(mb - ma)

            a_samples = arr_a[:, j, day]
            b_samples = arr_b[:, j, day]
            # P(A better than B). For mismatched sample sizes, broadcast
            # via outer comparison on a capped pair to keep cost O(n*m)
            # bounded — here both sides are capped at 10K each.
            if a_samples.size == b_samples.size:
                if prefer_high:
                    p_a_better = float((a_samples > b_samples).mean())
                else:
                    p_a_better = float((a_samples < b_samples).mean())
            else:
                # outer comparison
                if prefer_high:
                    p_a_better = float(
                        (a_samples[:, None] > b_samples[None, :]).mean()
                    )
                else:
                    p_a_better = float(
                        (a_samples[:, None] < b_samples[None, :]).mean()
                    )

            # Interpretation
            scale = max(abs(ma), abs(mb), 1e-6)
            if abs(mean_delta) < 0.01 * scale:
                interpretation: InterpretationLiteral = "tie"
            elif p_a_better >= 0.7:
                interpretation = "A_better"
            elif p_a_better <= 0.3:
                interpretation = "B_better"
            else:
                interpretation = "ambiguous"

            deltas.append(
                OutcomeDelta(
                    dim_name=name,
                    day=day,
                    mean_delta=mean_delta,
                    p_a_better=p_a_better,
                    interpretation=interpretation,
                )
            )

    return ScenarioComparison(
        scenario_a_hash=summary_a.scenario_hash,
        scenario_b_hash=summary_b.scenario_hash,
        deltas=deltas,
        n_samples_a=int(arr_a.shape[0]),
        n_samples_b=int(arr_b.shape[0]),
    )


__all__ = [
    "CompareError",
    "OutcomeDelta",
    "ScenarioComparison",
    "InterpretationLiteral",
    "default_prefer_higher_map",
    "compare_scenarios",
]
