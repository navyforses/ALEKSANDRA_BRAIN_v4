"""Phase 7.3 Day 3 — Trajectory aggregator (mean / sd / HDI 80 / HDI 95).

Reduces a 3-D Monte Carlo array of shape
``(n_samples, n_outcomes, horizon_days + 1)`` produced by
``brain.sim.trajectory.simulate_scenario`` into a typed
``ScenarioSummary`` whose ``summaries`` list carries one
``OutcomeSummary`` per (outcome, day).

HDI strategy:
    - Primary: ``arviz.hdi(arr, hdi_prob=p)``; ArviZ is a hard dep of the
      Phase 7.0 belief layer so it is always available in ``.venv-v7``.
    - Fallback (defensive only): equal-tail percentile interval
      (``np.percentile(arr, [(1 - p) / 2 * 100, (1 + p) / 2 * 100])``).
      The fallback documents what happens when arviz import fails for
      any reason (e.g. partial install during a future env change).

Reference:
    - v7_architecture/70_PHASES/73_PHASE_7_3_SIMULATION_ENGINE_3W.md
      section 1 layer A Day 3 + section 2.4 output table.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

try:
    import arviz as az

    _HAS_ARVIZ = True
except ImportError:  # pragma: no cover — arviz is a hard dep in v7 env
    az = None  # type: ignore[assignment]
    _HAS_ARVIZ = False

from brain.sim.scenario import Scenario, compute_scenario_hash


# ---------------------------------------------------------------------------
# Pydantic summary models
# ---------------------------------------------------------------------------
class OutcomeSummary(BaseModel):
    """Per (outcome, day) reduction."""

    model_config = ConfigDict(extra="forbid")

    dim_name: str = Field(..., min_length=1)
    day: int = Field(..., ge=0)
    mean: float
    sd: float
    hdi_80_low: float
    hdi_80_high: float
    hdi_95_low: float
    hdi_95_high: float
    n_samples: int = Field(..., ge=1)


class ScenarioSummary(BaseModel):
    """Aggregated reduction across a 3-D trajectory array."""

    model_config = ConfigDict(extra="forbid")

    scenario_hash: str = Field(..., min_length=64, max_length=64)
    n_samples: int = Field(..., ge=1)
    horizon_days: int = Field(..., ge=0)
    outcomes: list[str]
    summaries: list[OutcomeSummary]
    elapsed_seconds: float = Field(..., ge=0.0)


# ---------------------------------------------------------------------------
# HDI helpers
# ---------------------------------------------------------------------------
def _hdi_pair(samples: np.ndarray, prob: float) -> tuple[float, float]:
    """Return (low, high) HDI bounds for a 1-D sample vector.

    Uses arviz when available; falls back to equal-tail percentile.
    """
    if _HAS_ARVIZ and samples.size > 1:
        try:
            bounds = az.hdi(samples, hdi_prob=prob)
            # arviz returns a numpy array of shape (2,)
            arr = np.asarray(bounds).reshape(-1)
            if arr.size >= 2:
                return float(arr[0]), float(arr[-1])
        except Exception:  # noqa: BLE001 — fall through to percentile path
            pass

    tail = (1.0 - prob) / 2.0 * 100.0
    low = float(np.percentile(samples, tail))
    high = float(np.percentile(samples, 100.0 - tail))
    return low, high


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------
def aggregate_trajectories(
    arr: np.ndarray,
    *,
    scenario: Scenario,
    elapsed_seconds: float,
) -> ScenarioSummary:
    """Reduce a 3-D ``(n_samples, n_outcomes, horizon_days + 1)`` array.

    Returns a ScenarioSummary with one OutcomeSummary per (outcome, day).
    """
    if arr.ndim != 3:
        raise ValueError(
            f"arr must be 3-D (n_samples, n_outcomes, n_steps); got shape {arr.shape}"
        )
    n_samples, n_outcomes, n_steps = arr.shape
    if n_outcomes != len(scenario.outcomes):
        raise ValueError(
            f"arr second axis ({n_outcomes}) != len(scenario.outcomes) "
            f"({len(scenario.outcomes)})"
        )
    if n_steps != scenario.horizon_days + 1:
        raise ValueError(
            f"arr third axis ({n_steps}) != horizon_days + 1 "
            f"({scenario.horizon_days + 1})"
        )

    scenario_hash = compute_scenario_hash(scenario)

    summaries: list[OutcomeSummary] = []
    for j, name in enumerate(scenario.outcomes):
        outcome_arr = arr[:, j, :]  # shape (n_samples, n_steps)
        means = outcome_arr.mean(axis=0)
        sds = outcome_arr.std(axis=0, ddof=1)
        for day in range(n_steps):
            day_samples = outcome_arr[:, day]
            hdi80_low, hdi80_high = _hdi_pair(day_samples, 0.80)
            hdi95_low, hdi95_high = _hdi_pair(day_samples, 0.95)
            summaries.append(
                OutcomeSummary(
                    dim_name=name,
                    day=day,
                    mean=float(means[day]),
                    sd=float(sds[day]) if np.isfinite(sds[day]) else 0.0,
                    hdi_80_low=hdi80_low,
                    hdi_80_high=hdi80_high,
                    hdi_95_low=hdi95_low,
                    hdi_95_high=hdi95_high,
                    n_samples=int(n_samples),
                )
            )

    return ScenarioSummary(
        scenario_hash=scenario_hash,
        n_samples=int(n_samples),
        horizon_days=int(scenario.horizon_days),
        outcomes=list(scenario.outcomes),
        summaries=summaries,
        elapsed_seconds=float(elapsed_seconds),
    )


# ---------------------------------------------------------------------------
# Long-form DataFrame helper
# ---------------------------------------------------------------------------
def summary_to_dataframe(summary: ScenarioSummary) -> pd.DataFrame:
    """Project a ScenarioSummary to a long-form pandas DataFrame.

    Columns: ``dim_name, day, mean, sd, hdi_80_low, hdi_80_high,
    hdi_95_low, hdi_95_high, n_samples``.
    """
    rows = [s.model_dump() for s in summary.summaries]
    return pd.DataFrame(rows)


__all__ = [
    "OutcomeSummary",
    "ScenarioSummary",
    "aggregate_trajectories",
    "summary_to_dataframe",
]


def _has_arviz() -> Optional[bool]:  # pragma: no cover — diagnostics only
    return _HAS_ARVIZ
