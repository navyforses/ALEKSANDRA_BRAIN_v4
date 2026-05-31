"""Phase 7.0 Days 16-17 — Evidence adapters from Phase 1 (MRI) + Phase 5 (voice) to BeliefEvidence.

Adapters are READ-ONLY: they parse caller-provided Pydantic row shapes
(`MriReportRow`, `IntakeDropRow`) and emit `list[BeliefEvidence]`. They do
NOT touch the DB layer — callers fetch rows via psycopg2 (or fixtures in
tests) and feed them in. The returned `BeliefEvidence` objects can then be
passed to `brain.belief.update.update(...)` or persisted via
`brain.belief.persistence.write_evidence(...)`.

Hard rules:
  - NO PHI in code or logs (synthetic test fixtures only; only field names
    + extraction status are logged, never raw transcript / report bodies).
  - Idempotent via `BeliefEvidence.evidence_hash` (computed from
    `(dimension_id, source, source_ref, value)`).
  - Failed extraction returns `None`, NOT an exception — partial-success
    pipeline philosophy. Adapters never raise on unparseable inputs;
    they emit a logger.warning(dim_name + status) and move on.
  - Confidence reflects extraction method:
      explicit numeric in text  → 0.90 (MRI) / 0.85 (voice)
      regex-parsed from prose   → 0.75
      keyword-based classification → 0.65–0.70
      inferred / staging-only   → 0.55
"""

from brain.belief.adapters.mri_report import (  # noqa: F401
    MriReportRow,
    adapt_mri_report,
    extract_brainstem_function,
    extract_csf_biomarkers,
    extract_cyst_volume,
)
from brain.belief.adapters.voice_note import (  # noqa: F401
    IntakeDropRow,
    adapt_voice_note,
    extract_eye_tracking,
    extract_feeding_stage,
    extract_head_control,
    extract_muscle_tone,
)

__all__ = [
    "MriReportRow",
    "IntakeDropRow",
    "adapt_mri_report",
    "adapt_voice_note",
    "extract_cyst_volume",
    "extract_brainstem_function",
    "extract_csf_biomarkers",
    "extract_eye_tracking",
    "extract_head_control",
    "extract_muscle_tone",
    "extract_feeding_stage",
]
