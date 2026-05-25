"""Phase 7.2 Day 6 — DoWhy effect estimators (linear / PSM / IV).

Wraps ``dowhy.CausalModel.estimate_effect`` with a typed, snapshot-stable
Pydantic ``EstimateResult`` so downstream callers (Day 7 do-API, Day 10
belief writeback, Phase 7.6 frontend) never have to touch the raw DoWhy
``CausalEstimate`` object directly.

Three estimator methods are exposed:

    - ``"linear_regression"``           -> DoWhy ``backdoor.linear_regression``
    - ``"propensity_score_matching"``   -> DoWhy ``backdoor.propensity_score_matching``
    - ``"instrumental_variable"``       -> DoWhy ``iv.instrumental_variable``

IV is only valid when the identified estimand has a non-empty
``instrumental_variables`` set; otherwise this module raises
``EstimationError`` rather than letting DoWhy fail with an opaque message.

Reference:
    - Pearl, _Causality_ 2nd ed., 2009, §3.3 (backdoor) + §3.5 (IV).
    - DoWhy estimator catalogue:
      https://www.pywhy.org/dowhy/v0.11.1/user_guide/causal_tasks/estimating_causal_effects/index.html
    - Phase 7.2 spec §1 Day 6, §2.3 API contract,
      v7_architecture/70_PHASES/72_PHASE_7_2_CAUSAL_LAYER_3W.md
"""

from __future__ import annotations

from typing import Any, Literal, Optional

import math
import numpy as np
from dowhy import CausalModel
from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
EstimateMethod = Literal[
    "linear_regression",
    "propensity_score_matching",
    "instrumental_variable",
]


_METHOD_TO_DOWHY: dict[str, str] = {
    "linear_regression": "backdoor.linear_regression",
    "propensity_score_matching": "backdoor.propensity_score_matching",
    "instrumental_variable": "iv.instrumental_variable",
}


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------
class EstimationError(RuntimeError):
    """Estimator could not run (e.g. IV requested but no instruments in graph)."""


# ---------------------------------------------------------------------------
# Pydantic result
# ---------------------------------------------------------------------------
class EstimateResult(BaseModel):
    """Typed wrapper for one DoWhy causal estimate.

    Numerical fields are rounded to 6 decimals so snapshot tests stay
    stable across DoWhy/NumPy minor versions.
    """

    model_config = ConfigDict(extra="forbid")

    method: EstimateMethod
    effect: float
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    n_samples: int = Field(..., ge=0)
    identified_estimand_str: str
    raw_effect_summary: Optional[dict[str, Any]] = None
    units: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _round6(x: Any) -> Optional[float]:
    """Round x to 6 decimals; return None if x is None / NaN / non-finite."""
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(xf):
        return None
    return round(xf, 6)


def _extract_ci(estimate: Any) -> tuple[Optional[float], Optional[float]]:
    """Pull (ci_low, ci_high) out of a DoWhy CausalEstimate.

    DoWhy may return ``None``, a 2-tuple of floats, a 2-tuple of np scalars,
    or a 1x2 numpy array depending on estimator. NaN -> None.
    """
    try:
        ci = estimate.get_confidence_intervals()
    except Exception:  # pragma: no cover — defensive (some estimators raise)
        return (None, None)
    if ci is None:
        return (None, None)
    # Tolerate ndarray / list / tuple shapes
    arr = np.asarray(ci).flatten().tolist()
    if len(arr) < 2:
        return (None, None)
    return (_round6(arr[0]), _round6(arr[1]))


# ---------------------------------------------------------------------------
# Public estimator
# ---------------------------------------------------------------------------
def estimate_effect(
    model: CausalModel,
    identified_estimand: dict,
    method: EstimateMethod,
    *,
    confidence_level: float = 0.95,
    units: Optional[str] = None,
) -> EstimateResult:
    """Run a DoWhy estimator and return a typed ``EstimateResult``.

    Note on the ``identified_estimand`` argument:
        ``brain.causal.dowhy_bootstrap.identify_effect`` returns a *dict*
        (structured for API serialization). DoWhy's estimator API needs
        the raw ``IdentifiedEstimand`` Python object — so this function
        re-runs ``model.identify_effect(proceed_when_unidentifiable=True)``
        internally to obtain it. The ``identified_estimand`` dict is used
        only to (a) record ``estimand_str`` on the result and (b) check
        the instrumental-variables precondition for IV.

    Args:
        model: a ``dowhy.CausalModel`` built via
            :func:`brain.causal.dowhy_bootstrap.build_causal_model`.
        identified_estimand: the dict returned by
            :func:`brain.causal.dowhy_bootstrap.identify_effect`. MUST
            contain keys ``"instrumental_variables"`` and
            ``"estimand_str"`` (this is enforced by the bootstrap module).
        method: one of ``"linear_regression"``,
            ``"propensity_score_matching"``, or ``"instrumental_variable"``.
        confidence_level: passed through to DoWhy as
            ``method_params={"confidence_level": ...}``. Wider CL widens
            the interval. Defaults to 0.95.
        units: optional human-readable units string (e.g. ``"seizures/day"``);
            propagated onto the result for downstream rendering.

    Raises:
        EstimationError: if ``method`` is unknown OR if IV requested
            with no instruments in the graph.

    Returns:
        :class:`EstimateResult` with rounded numerical fields.
    """
    if method not in _METHOD_TO_DOWHY:
        raise EstimationError(
            f"unknown estimator method {method!r}; "
            f"choose one of {sorted(_METHOD_TO_DOWHY)}"
        )
    if not (0.0 < confidence_level < 1.0):
        raise EstimationError(
            f"confidence_level must lie strictly in (0,1); got {confidence_level!r}"
        )

    # IV precondition — DoWhy will silently return junk otherwise
    if method == "instrumental_variable":
        iv_set = identified_estimand.get("instrumental_variables") or []
        if len(iv_set) == 0:
            raise EstimationError(
                "instrumental_variable estimator requested but identified estimand "
                "has no instrumental variables; pick a different method or extend "
                "the SCM with an IV node."
            )

    dowhy_method = _METHOD_TO_DOWHY[method]

    # Re-identify to get the raw IdentifiedEstimand object DoWhy needs
    raw_estimand = model.identify_effect(proceed_when_unidentifiable=True)

    try:
        causal_estimate = model.estimate_effect(
            raw_estimand,
            method_name=dowhy_method,
            confidence_intervals=True,
            test_significance=False,
            method_params={"confidence_level": confidence_level},
        )
    except Exception as exc:
        raise EstimationError(
            f"DoWhy estimator {dowhy_method!r} failed: {exc!s}"
        ) from exc

    ci_low, ci_high = _extract_ci(causal_estimate)

    # Sample count from the underlying DataFrame the model was built on
    try:
        n_samples = int(len(model._data))
    except Exception:  # pragma: no cover
        n_samples = 0

    raw_summary: dict[str, Any] = {
        "control_value": _round6(getattr(causal_estimate, "control_value", None)),
        "treatment_value": _round6(
            getattr(causal_estimate, "treatment_value", None)
        ),
        "confidence_level": round(float(confidence_level), 6),
        "dowhy_method": dowhy_method,
    }

    return EstimateResult(
        method=method,
        effect=_round6(causal_estimate.value) or 0.0,
        ci_low=ci_low,
        ci_high=ci_high,
        n_samples=n_samples,
        identified_estimand_str=str(
            identified_estimand.get("estimand_str", "")
        ),
        raw_effect_summary=raw_summary,
        units=units,
    )


__all__ = [
    "EstimateMethod",
    "EstimateResult",
    "EstimationError",
    "estimate_effect",
]
