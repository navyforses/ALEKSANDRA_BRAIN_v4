"""Phase 7.4 Day 9 — ParsedResponse -> BeliefEvidence -> update() integration.

Bridges Layer B (wife-facing question + parser) into Phase 7.0's
posterior-update API. DRY_RUN sentinel when `SUPABASE_DB_URL` unset
(matches `brain/causal/cross_link.py` pattern).

The evidence `value` JSONB schema is per-format:

    integer_seconds / integer_count   {"int": <int>}
    float_value                       {"float": <float>}
    boolean                           {"bool": <bool>}
    categorical_choice                {"choice": "<label>"}
    scale_0_5                         {"int": <0..5>}

`compute_evidence_hash` keys idempotency, so re-submitting the same parsed
response collapses to a single belief_evidence row.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any

from brain.active.response_parser import ParsedResponse
from brain.belief.persistence import (
    BeliefDimension,
    BeliefEvidence,
    compute_evidence_hash,
)


def _is_dry_run() -> bool:
    return not os.environ.get("SUPABASE_DB_URL")


def _value_payload(parsed: ParsedResponse) -> dict[str, Any]:
    """Project a ParsedResponse onto the JSONB `value` dict for evidence."""
    val = parsed.parsed_value
    fmt = parsed.expected_format
    if val is None:
        return {"unparsed": True, "raw_text_len": len(parsed.raw_text)}
    if fmt in {"integer_seconds", "integer_count", "scale_0_5"}:
        return {"int": int(val)}
    if fmt == "float_value":
        return {"float": float(val)}
    if fmt == "boolean":
        return {"bool": bool(val)}
    if fmt == "categorical_choice":
        return {"choice": str(val)}
    return {"raw": str(val)}


def parsed_response_to_evidence(
    *,
    dim: BeliefDimension,
    parsed: ParsedResponse,
    observation_type: str,
    source_ref: str,
    observed_at: datetime,
) -> BeliefEvidence:
    """Build a valid BeliefEvidence from a ParsedResponse.

    `source="manual"` (whitelisted in Phase 7.0 ALLOWED_EVIDENCE_SOURCES);
    confidence carries through from the parser; observation_type embedded
    inside the value payload for downstream replay.
    """
    if dim.id is None:
        # Per Phase 7.0 persistence contract, dimension_id is REQUIRED to
        # write evidence. In DRY_RUN tests we accept id=0 as sentinel.
        dim_id = 0
    else:
        dim_id = int(dim.id)

    value = _value_payload(parsed)
    value["observation_type"] = observation_type
    value["parser_confidence"] = float(parsed.confidence)

    ev_hash = compute_evidence_hash(
        dimension_id=dim_id,
        source="manual",
        source_ref=source_ref,
        value=value,
    )
    return BeliefEvidence(
        dimension_id=dim_id,
        source="manual",
        source_ref=source_ref,
        value=value,
        evidence_hash=ev_hash,
        confidence=float(parsed.confidence),
        observed_at=observed_at,
    )


def apply_response_and_compute_delta(
    *,
    dim: BeliefDimension,
    parsed: ParsedResponse,
    observation_type: str,
    source_ref: str,
    observed_at: datetime,
) -> dict:
    """End-to-end: build evidence, call update() in production, DRY_RUN else.

    Returns dict with `{"evidence_hash", "status", ...}`. In production the
    `update()` PosteriorDelta is dumped under "delta".
    """
    ev = parsed_response_to_evidence(
        dim=dim,
        parsed=parsed,
        observation_type=observation_type,
        source_ref=source_ref,
        observed_at=observed_at,
    )

    if _is_dry_run():
        print(
            f"[active.integration] DRY_RUN evidence_hash={ev.evidence_hash[:12]} "
            f"dim={dim.name} obs={observation_type}",
            file=sys.stderr,
        )
        return {
            "evidence_hash": ev.evidence_hash,
            "status": "dry_run",
            "delta_kl": None,
            "dim_name": dim.name,
            "observation_type": observation_type,
            "value": ev.value,
            "confidence": ev.confidence,
        }

    # Production path
    try:
        from brain.belief.update import update  # noqa: WPS433
    except Exception as exc:  # noqa: BLE001
        return {
            "evidence_hash": ev.evidence_hash,
            "status": "error",
            "error": f"could not import update(): {exc}",
        }
    try:
        delta = update(ev)
        return {
            "evidence_hash": ev.evidence_hash,
            "status": "ok",
            "delta": delta.model_dump(),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "evidence_hash": ev.evidence_hash,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
        }


__all__ = [
    "parsed_response_to_evidence",
    "apply_response_and_compute_delta",
]
