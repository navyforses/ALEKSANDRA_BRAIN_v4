"""Phase 7.2 Day 9 — Refutation / sensitivity analysis wrapper.

Wraps two DoWhy refuters into typed reports:

    - ``random_common_cause``          - add a synthetic unobserved
      confounder; a robust estimate should not move much.
    - ``placebo_treatment_refuter``    - swap the treatment for a
      randomised placebo; a robust estimate should collapse to ~0.

Pass criteria (deliberately strict but well-calibrated for the reference SCM):

    - ``random_common_cause`` passes when
      ``|new - original| / max(|original|, 1e-6) < 0.3``
    - ``placebo_treatment_refuter`` passes when
      ``|new| < 0.2 * |original|``

Both are encoded as plain floats; callers can tighten as they accumulate
domain calibration.

Reference:
    - Pearl, _Causality_ 2nd ed., 2009, §11 (sensitivity).
    - DoWhy refutation guide:
      https://www.pywhy.org/dowhy/v0.11.1/user_guide/causal_tasks/refute_estimates/index.html
    - Phase 7.2 spec §1 Day 9 + verifier checks 7-8.
"""

from __future__ import annotations

import sys
from typing import Any, Literal, Optional

import math
from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
Refuter = Literal["random_common_cause", "placebo_treatment_refuter"]

_ALLOWED_REFUTERS: tuple[str, ...] = (
    "random_common_cause",
    "placebo_treatment_refuter",
)


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------
class RefutationError(RuntimeError):
    """Raised when DoWhy's refuter cannot run for the given estimator."""


# ---------------------------------------------------------------------------
# Pydantic report
# ---------------------------------------------------------------------------
class RefutationReport(BaseModel):
    """One refuter's verdict + interpretation.

    Numeric fields are rounded to 6 decimals to stay snapshot-stable.
    """

    model_config = ConfigDict(extra="forbid")

    refuter: Refuter
    original_effect: float
    new_effect: float
    p_value: Optional[float] = None
    passed: bool
    interpretation: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _round6(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(xf):
        return None
    return round(xf, 6)


def _evaluate_random_common_cause(orig: float, new: float) -> tuple[bool, str]:
    denom = max(abs(orig), 1e-6)
    rel_shift = abs(new - orig) / denom
    passed = rel_shift < 0.3
    interp = (
        f"random_common_cause: |new - original| / max(|original|, 1e-6) "
        f"= {rel_shift:.4f}; "
        + ("PASS (< 0.3 threshold)." if passed else "FAIL (>= 0.3 threshold).")
    )
    return passed, interp


def _evaluate_placebo(orig: float, new: float) -> tuple[bool, str]:
    threshold = 0.2 * abs(orig)
    passed = abs(new) < threshold
    interp = (
        f"placebo_treatment_refuter: |new| = {abs(new):.4f}, "
        f"0.2 * |original| = {threshold:.4f}; "
        + ("PASS (placebo effect near zero)." if passed else
           "FAIL (placebo treatment produced material effect).")
    )
    return passed, interp


# ---------------------------------------------------------------------------
# Public — refute a single estimate
# ---------------------------------------------------------------------------
def refute_estimate(
    model: Any,                # dowhy.CausalModel
    identified_estimand: Any,  # dowhy IdentifiedEstimand
    causal_estimate: Any,      # dowhy CausalEstimate
    refuter: Refuter,
) -> RefutationReport:
    """Run one DoWhy refuter and return a typed verdict.

    Args:
        model: a ``dowhy.CausalModel``.
        identified_estimand: the raw ``IdentifiedEstimand`` object (NOT the
            dict from ``dowhy_bootstrap.identify_effect``; pass
            ``model.identify_effect(proceed_when_unidentifiable=True)``).
        causal_estimate: the raw ``CausalEstimate`` from
            ``model.estimate_effect(...)``.
        refuter: one of the literals in :data:`_ALLOWED_REFUTERS`.

    Raises:
        RefutationError: refuter not supported by this estimator (DoWhy
            raises various exceptions for unsupported combinations; we
            wrap them in a single error type).
    """
    if refuter not in _ALLOWED_REFUTERS:
        raise RefutationError(
            f"unknown refuter {refuter!r}; "
            f"choose one of {list(_ALLOWED_REFUTERS)}"
        )

    try:
        result = model.refute_estimate(
            identified_estimand,
            causal_estimate,
            method_name=refuter,
        )
    except Exception as exc:  # pragma: no cover — DoWhy-internal failures
        raise RefutationError(
            f"DoWhy refuter {refuter!r} failed: {exc!s}"
        ) from exc

    orig = _round6(getattr(result, "estimated_effect", None)) or 0.0
    new = _round6(getattr(result, "new_effect", None)) or 0.0
    p_val_raw = None
    try:
        rr = getattr(result, "refutation_result", None)
        if isinstance(rr, dict):
            p_val_raw = rr.get("p_value")
    except Exception:  # pragma: no cover
        p_val_raw = None
    p_val = _round6(p_val_raw)

    if refuter == "random_common_cause":
        passed, interp = _evaluate_random_common_cause(orig, new)
    else:  # placebo_treatment_refuter
        passed, interp = _evaluate_placebo(orig, new)

    return RefutationReport(
        refuter=refuter,
        original_effect=orig,
        new_effect=new,
        p_value=p_val,
        passed=passed,
        interpretation=interp,
    )


# ---------------------------------------------------------------------------
# Public — run both refuters, tolerate per-refuter failure
# ---------------------------------------------------------------------------
def refute_estimate_all(
    model: Any,
    identified_estimand: Any,
    causal_estimate: Any,
) -> list[RefutationReport]:
    """Run every refuter in :data:`_ALLOWED_REFUTERS`.

    A per-refuter failure is converted into a failed
    :class:`RefutationReport` (``passed=False``, ``interpretation``
    starts with ``"error: "``) and logged to stderr — never re-raised.
    This lets the caller persist a complete refutation sweep even when
    one estimator/refuter combination is incompatible.
    """
    out: list[RefutationReport] = []
    orig_estimate = _round6(getattr(causal_estimate, "value", None)) or 0.0
    for ref in _ALLOWED_REFUTERS:
        try:
            out.append(
                refute_estimate(
                    model, identified_estimand, causal_estimate, ref  # type: ignore[arg-type]
                )
            )
        except RefutationError as exc:
            print(
                f"[sensitivity] refuter {ref!r} failed: {exc!s}",
                file=sys.stderr,
            )
            out.append(
                RefutationReport(
                    refuter=ref,  # type: ignore[arg-type]
                    original_effect=orig_estimate,
                    new_effect=0.0,
                    p_value=None,
                    passed=False,
                    interpretation=f"error: {exc!s}",
                )
            )
    return out


__all__ = [
    "Refuter",
    "RefutationError",
    "RefutationReport",
    "refute_estimate",
    "refute_estimate_all",
]
