"""
patient_context.py — Phase 4 ACD-05 versioned patient-context snapshot.

The clinician PDF must embed the *version* of the Aleksandra context block
that was current when the PDF was rendered. This module produces that
snapshot deterministically — same inputs always yield the same
`version_hash`, so Dr. Hien can verify "this PDF was produced under
context version 7a3f9c…".

Snapshot source order (first match wins):
  1. `data/patient_context.yaml` — Shako-curated source of truth (if present).
     YAML doc with keys: identity_default, diagnosis, age_band, location,
     active_programs, last_updated_iso.
  2. CLAUDE.md "## პაციენტი" + "## აქტიური პროგრამები" sections — fallback
     parsed for the same fields.
  3. Embedded constants below — last-resort fallback so the renderer
     never crashes for missing config.

The snapshot intentionally contains NO PHI fields (no full name, no DOB
day, no MRN). Identity defaults to "A.J., 8-month-old infant with severe
HIE" — same default the Phase 3 PHI redactor uses.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # PyYAML is installed in Phase 3 Day 6 reqs; the fallback path works without it


ROOT = Path(__file__).resolve().parent.parent.parent
PATIENT_YAML = ROOT / "data" / "patient_context.yaml"


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PatientContext:
    identity_default: str
    diagnosis_summary: str
    age_band: str
    location: str
    active_programs: tuple[str, ...]
    last_updated_iso: str
    version_hash: str  # first 12 hex chars of SHA-256 over the canonical JSON


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_FALLBACK = {
    "identity_default": "A.J., 8-month-old infant with severe HIE",
    "diagnosis_summary": (
        "Severe hypoxic-ischemic encephalopathy with diffuse cystic "
        "encephalomalacia. Brainstem preserved. Receiving standard "
        "anticonvulsant therapy."
    ),
    "age_band": "0-12 months (neuroplasticity window)",
    "location": "U.S. East Coast (family-controlled detail)",
    "active_programs": (
        "Duke EAP cord blood (vigabatrin washout window)",
        "Wisconsin Virtual A2",
        "BMC primary care + neurology",
    ),
    "last_updated_iso": "",
}


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def _load_from_yaml(path: Path) -> dict[str, Any] | None:
    if not path.exists() or yaml is None:
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _coerce(raw: dict[str, Any]) -> dict[str, Any]:
    """Merge `raw` over `_FALLBACK`, coercing types defensively."""
    merged = dict(_FALLBACK)
    for k, v in (raw or {}).items():
        if v is None:
            continue
        merged[k] = v
    progs = merged.get("active_programs") or []
    if isinstance(progs, str):
        progs = [progs]
    merged["active_programs"] = tuple(str(p).strip() for p in progs if p)
    for k in ("identity_default", "diagnosis_summary", "age_band", "location"):
        merged[k] = str(merged.get(k) or "").strip()
    last = str(merged.get("last_updated_iso") or "").strip()
    merged["last_updated_iso"] = last or datetime.now(timezone.utc).date().isoformat()
    return merged


def _hash(snapshot: dict[str, Any]) -> str:
    canonical = json.dumps(
        {
            "identity_default": snapshot["identity_default"],
            "diagnosis_summary": snapshot["diagnosis_summary"],
            "age_band": snapshot["age_band"],
            "location": snapshot["location"],
            "active_programs": list(snapshot["active_programs"]),
            "last_updated_iso": snapshot["last_updated_iso"],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def current_context() -> PatientContext:
    """Return the current patient-context snapshot.

    Deterministic for a given (yaml-or-not, content) input — the same call
    on the same machine seconds apart returns the same version_hash unless
    the underlying yaml changed.
    """
    raw = _load_from_yaml(PATIENT_YAML) or {}
    merged = _coerce(raw)
    version = _hash(merged)
    return PatientContext(
        identity_default=merged["identity_default"],
        diagnosis_summary=merged["diagnosis_summary"],
        age_band=merged["age_band"],
        location=merged["location"],
        active_programs=tuple(merged["active_programs"]),
        last_updated_iso=merged["last_updated_iso"],
        version_hash=version,
    )


def to_dict(ctx: PatientContext) -> dict[str, Any]:
    """Plain-dict form for embedding in PDFs / JSON payloads."""
    return asdict(ctx)


__all__ = ["PatientContext", "current_context", "to_dict"]
