"""Phase 7.2 Day 10 — Causal estimate -> belief_evidence cross-link.

When DoWhy produces a usable ``EstimateResult`` for a treatment-outcome
pair, that estimate is itself *evidence* about the underlying belief
dimension (e.g. a Bayley score or seizure-frequency posterior). This
module folds the estimate into the Phase 7.0 belief layer by writing a
:class:`brain.belief.persistence.BeliefEvidence` row with
``source="causal_estimate"`` (the persistence layer already whitelists
this source on its ``ALLOWED_EVIDENCE_SOURCES`` frozen-set).

Idempotency: the cross-link delegates to ``write_evidence``, which
collapses identical evidence on its deterministic
``compute_evidence_hash`` so the same (dimension, estimate, source_ref,
value) round-trips to a single row.

Code-complete-without-infra contract: when ``SUPABASE_DB_URL`` is unset,
the cross-link does NOT attempt a DB connection. It returns the sentinel
``"DRY_RUN:<evidence_hash>"`` and logs to stderr so unit-tests stay
self-contained.

Reference:
    - Phase 7.0 §3 (belief_evidence schema), §5 (idempotency contract).
    - Phase 7.2 spec §1 Day 10 + verifier check #8.
"""

from __future__ import annotations

import math
import os
import sys
from datetime import datetime
from typing import Any

from brain.belief.persistence import (
    BeliefEvidence,
    compute_evidence_hash,
    write_evidence,
)
from brain.causal.estimators import EstimateResult


# ---------------------------------------------------------------------------
# Confidence derivation
# ---------------------------------------------------------------------------
def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _confidence_from_estimate(
    estimate: EstimateResult,
    *,
    confidence_floor: float,
) -> float:
    """Derive a [floor, 0.99] confidence from CI width relative to effect.

    Heuristic:

        confidence = clip(1 - (ci_high - ci_low) / max(|effect|, 1e-6) / 4,
                          confidence_floor, 0.99)

    Intuition: a 95% CI four times as wide as the effect is near-useless
    (confidence -> floor); a CI tightly bracketing the effect should
    push confidence to ~0.99.

    When either CI bound is None, return ``confidence_floor`` — CI absence
    is itself a signal of low precision.
    """
    if estimate.ci_low is None or estimate.ci_high is None:
        return float(confidence_floor)
    width = float(estimate.ci_high) - float(estimate.ci_low)
    if not math.isfinite(width):
        return float(confidence_floor)
    denom = max(abs(float(estimate.effect)), 1e-6)
    relative = width / denom
    raw = 1.0 - relative / 4.0
    return float(_clip(raw, confidence_floor, 0.99))


# ---------------------------------------------------------------------------
# Build the value payload (JSON-safe — no numpy scalars)
# ---------------------------------------------------------------------------
def _build_value_payload(estimate: EstimateResult) -> dict[str, Any]:
    """Project an EstimateResult to a JSON-serialisable dict.

    Every numeric field passes through ``float()`` so numpy scalars
    do not leak into the JSONB column (psycopg2 rejects ``np.float64``
    inside a json.dumps payload unless explicitly cast).
    """
    return {
        "effect": float(estimate.effect),
        "ci_low": float(estimate.ci_low) if estimate.ci_low is not None else None,
        "ci_high": float(estimate.ci_high) if estimate.ci_high is not None else None,
        "method": str(estimate.method),
        "units": str(estimate.units) if estimate.units is not None else None,
        "n_samples": int(estimate.n_samples),
        "identified_estimand_str": str(estimate.identified_estimand_str),
    }


# ---------------------------------------------------------------------------
# Public — record a causal estimate as belief evidence
# ---------------------------------------------------------------------------
def record_causal_estimate_as_evidence(
    *,
    estimate: EstimateResult,
    target_dimension_id: int,
    source_ref: str,
    observed_at: datetime,
    confidence_floor: float = 0.4,
) -> str:
    """Persist a causal estimate into ``belief_evidence``.

    Args:
        estimate: the typed :class:`EstimateResult` from
            :func:`brain.causal.estimators.estimate_effect`.
        target_dimension_id: primary key of the
            :class:`~brain.belief.persistence.BeliefDimension` this
            estimate informs. Caller must resolve via
            :func:`brain.belief.persistence.get_dimension` /
            :func:`brain.belief.persistence.get_dimension_by_id`.
        source_ref: a stable reference string for this estimate (e.g.
            ``"scm:reference_vigabatrin_seizure/linear_regression"``).
            Hashing keys on this so callers can choose any granularity.
        observed_at: timestamp the estimate was computed; copied to
            ``belief_evidence.observed_at``.
        confidence_floor: lower bound for the derived confidence in
            [0, 1]; defaults to 0.4 (matches Phase 7.0 §5 "moderate
            evidence" tier).

    Returns:
        * ``str(row_uuid)`` when SUPABASE_DB_URL is set and the write
          succeeds.
        * ``"DRY_RUN:<evidence_hash>"`` when SUPABASE_DB_URL is unset —
          a deterministic sentinel that lets callers (and tests) verify
          the would-be hash without an infra dependency.
    """
    if not (0.0 <= confidence_floor <= 1.0):
        raise ValueError(
            f"confidence_floor must lie in [0, 1]; got {confidence_floor!r}"
        )

    value = _build_value_payload(estimate)
    confidence = _confidence_from_estimate(
        estimate, confidence_floor=confidence_floor
    )

    evidence_hash = compute_evidence_hash(
        target_dimension_id, "causal_estimate", source_ref, value
    )

    # Code-complete-without-infra path
    if not os.environ.get("SUPABASE_DB_URL"):
        sentinel = f"DRY_RUN:{evidence_hash}"
        print(
            "[cross_link] SUPABASE_DB_URL unset — skipping write_evidence; "
            f"returning {sentinel}",
            file=sys.stderr,
        )
        return sentinel

    ev = BeliefEvidence(
        dimension_id=target_dimension_id,
        source="causal_estimate",
        source_ref=source_ref,
        value=value,
        evidence_hash=evidence_hash,
        confidence=confidence,
        observed_at=observed_at,
    )
    return write_evidence(ev)


__all__ = ["record_causal_estimate_as_evidence"]
