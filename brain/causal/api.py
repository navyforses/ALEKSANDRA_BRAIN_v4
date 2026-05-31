"""Phase 7.2 Days 7 + 8 — Framework-agnostic do() + counterfactual handlers.

These handlers are **framework-agnostic**: they expose typed Pydantic
request / response models plus pure functions that take an SCM + DataFrame
and return a response. Mount them onto FastAPI / Starlette / Flask in
the operator bootstrap (Phase 7.6 frontend); Phase 7.2 ships the contract
+ behaviour, NOT the HTTP server. FastAPI is intentionally NOT a
dependency of the brain package at this phase.

API shape matches v7_architecture/70_PHASES/72_PHASE_7_2_CAUSAL_LAYER_3W.md §2.3.

Two endpoints worth of contract:

    POST /api/causal/do            -> handle_do_query
    POST /api/causal/counterfactual -> handle_counterfactual_query

Reference:
    - Pearl, _Causality_ 2nd ed., 2009, §3.4 (do-operator),  §7 (counterfactual).
    - Phase 7.2 spec §1 Days 7-8 + §2.3 API contract.
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from brain.causal.counterfactual import counterfactual_predict
from brain.causal.dowhy_bootstrap import build_causal_model, identify_effect
from brain.causal.estimators import (
    EstimateMethod,
    EstimateResult,
    estimate_effect,
)
from brain.causal.scm import SCM


# ---------------------------------------------------------------------------
# do-query — request + response
# ---------------------------------------------------------------------------
class DoQueryRequest(BaseModel):
    """Request body for POST /api/causal/do.

    ``scm_name`` is captured for audit/telemetry; the actual SCM object
    is passed to the handler via a kwarg (handlers are pure functions —
    SCM resolution from name is the caller's job, typically a registry
    lookup in the route adapter).
    """

    model_config = ConfigDict(extra="forbid")

    scm_name: str = Field(..., min_length=1)
    treatment: str = Field(..., min_length=1)
    treatment_value: float | bool
    outcome: str = Field(..., min_length=1)
    method: EstimateMethod = "linear_regression"
    confidence_level: float = Field(0.95, gt=0.0, lt=1.0)
    units: Optional[str] = None


class DoQueryResponse(BaseModel):
    """Response body for POST /api/causal/do.

    Mirrors the spec's §2.3 schema; ``refutation`` is optional so a
    caller wanting a fast point estimate can skip the sensitivity sweep.
    """

    model_config = ConfigDict(extra="forbid")

    effect: float
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    units: Optional[str] = None
    method: EstimateMethod
    n_samples: int = Field(..., ge=0)
    identified_estimand: str
    refutation: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Counterfactual — request + response
# ---------------------------------------------------------------------------
class CounterfactualRequest(BaseModel):
    """Request body for POST /api/causal/counterfactual."""

    model_config = ConfigDict(extra="forbid")

    scm_name: str = Field(..., min_length=1)
    factual: dict[str, float]
    intervention: dict[str, float]
    outcome: str = Field(..., min_length=1)


class CounterfactualResponse(BaseModel):
    """Response body for POST /api/causal/counterfactual."""

    model_config = ConfigDict(extra="forbid")

    predicted_outcome: float
    delta_vs_factual: float
    method: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Handlers (pure functions — no I/O)
# ---------------------------------------------------------------------------
def handle_do_query(
    req: DoQueryRequest,
    *,
    scm: SCM,
    data: pd.DataFrame,
) -> DoQueryResponse:
    """Resolve a do-query request into a typed response.

    The handler:
        1. Checks ``req.treatment == scm.treatment`` and ``req.outcome
           == scm.outcome`` (route adapters should already pick the right
           SCM, but we double-guard here for defence in depth).
        2. Builds the DoWhy CausalModel via the bootstrap module.
        3. Identifies the estimand.
        4. Runs the requested estimator at the requested confidence level.

    Args:
        req: validated :class:`DoQueryRequest`.
        scm: the :class:`SCM` resolved from ``req.scm_name`` by the caller.
        data: observational :class:`pandas.DataFrame` for the SCM.

    Raises:
        ValueError: treatment / outcome mismatch.
        brain.causal.estimators.EstimationError: estimator failure.
        brain.causal.scm.SCMError: cyclic graph / missing columns.
    """
    if req.treatment != scm.treatment:
        raise ValueError(
            f"request treatment {req.treatment!r} != scm.treatment {scm.treatment!r}"
        )
    if req.outcome != scm.outcome:
        raise ValueError(
            f"request outcome {req.outcome!r} != scm.outcome {scm.outcome!r}"
        )

    model = build_causal_model(scm, data)
    estimand = identify_effect(model)

    estimate: EstimateResult = estimate_effect(
        model,
        estimand,
        req.method,
        confidence_level=req.confidence_level,
        units=req.units,
    )

    return DoQueryResponse(
        effect=estimate.effect,
        ci_low=estimate.ci_low,
        ci_high=estimate.ci_high,
        units=estimate.units,
        method=estimate.method,
        n_samples=estimate.n_samples,
        identified_estimand=estimate.identified_estimand_str,
        refutation=None,
    )


def handle_counterfactual_query(
    req: CounterfactualRequest,
    *,
    scm: SCM,
    data: pd.DataFrame,
) -> CounterfactualResponse:
    """Resolve a counterfactual request into a typed response.

    Delegates to :func:`brain.causal.counterfactual.counterfactual_predict`
    (Day 8) which implements the structural-linear extrapolation method.

    Args:
        req: validated :class:`CounterfactualRequest`.
        scm: the :class:`SCM` resolved from ``req.scm_name`` by the caller.
        data: observational :class:`pandas.DataFrame` for the SCM.

    Raises:
        ValueError: outcome mismatch, empty intervention, or unknown
            variable in ``factual`` / ``intervention``.
        brain.causal.scm.SCMError: cyclic graph / missing outcome parents.
    """
    if req.outcome != scm.outcome:
        raise ValueError(
            f"request outcome {req.outcome!r} != scm.outcome {scm.outcome!r}"
        )

    result = counterfactual_predict(
        scm,
        factual=req.factual,
        intervention=req.intervention,
        outcome=req.outcome,
        data=data,
    )

    return CounterfactualResponse(
        predicted_outcome=result["predicted_outcome"],
        delta_vs_factual=result["delta_vs_factual"],
        method=result["method"],
    )


__all__ = [
    "DoQueryRequest",
    "DoQueryResponse",
    "CounterfactualRequest",
    "CounterfactualResponse",
    "handle_do_query",
    "handle_counterfactual_query",
]
