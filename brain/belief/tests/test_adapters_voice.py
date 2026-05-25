"""Phase 7.0 Days 16-17 — Voice-note adapter unit tests.

All test fixtures are SYNTHETIC bilingual (EN + KA) transcripts. No
Aleksandra-specific clinical values. Test inputs deliberately use round
numbers (5, 8, 10) so the adapter's regex extraction is unambiguous.

Test coverage:
  1. Eye tracking — EN + KA variants
  2. Head control — EN + KA variants
  3. Muscle tone — clinical-score-only (EN)
  4. Feeding stage — NG / partial / puree / solid (EN + KA)
  5. Non-voice drop short-circuits to empty
  6. Empty / unparseable transcript -> empty
  7. Multi-dim transcript yields multiple evidences
  8. evidence_hash determinism
  9. PHI safety in logs
  10. Catalog-gap handling
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import pytest

from brain.belief.adapters.voice_note import (
    IntakeDropRow,
    adapt_voice_note,
    extract_eye_tracking,
    extract_feeding_stage,
    extract_head_control,
    extract_muscle_tone,
)
from brain.belief.persistence import BeliefDimension


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
SYNTHETIC_DATE = datetime(2026, 5, 10, 14, 0, tzinfo=timezone.utc)


def _stub_dim(name: str, dim_id: int, distribution: str) -> BeliefDimension:
    return BeliefDimension(
        id=dim_id,
        name=name,
        distribution=distribution,
        prior_params={"mu": 0.0, "sigma": 1.0}
        if distribution == "normal"
        else {"x": 0.0},
        citation="https://pubmed.ncbi.nlm.nih.gov/0",
    )


_DIM_TABLE = {
    "eye_tracking_seconds": _stub_dim("eye_tracking_seconds", 5, "gamma"),
    "head_control_seconds": _stub_dim("head_control_seconds", 6, "normal"),
    "muscle_tone_hammersmith": _stub_dim("muscle_tone_hammersmith", 4, "normal"),
    "feeding_stage": _stub_dim("feeding_stage", 9, "categorical"),
}


def _full_loader(name: str) -> Optional[BeliefDimension]:
    return _DIM_TABLE.get(name)


def _missing_loader(name: str) -> Optional[BeliefDimension]:
    return None


def _drop(
    text: str, ident: str = "drop-001", input_type: str = "voice"
) -> IntakeDropRow:
    return IntakeDropRow(
        id=ident,
        input_type=input_type,
        raw_content=text,
        created_at=SYNTHETIC_DATE,
        phi_redacted=True,
    )


# ---------------------------------------------------------------------------
# 1. Eye tracking — EN + KA
# ---------------------------------------------------------------------------
def test_voice_adapter_extracts_eye_tracking_en() -> None:
    drop = _drop("She held eye contact for 8 seconds during the visit.")
    ev = extract_eye_tracking(drop, dim_id=5)
    assert ev is not None
    assert ev.value == {"observations": [8.0]}
    assert ev.confidence == 0.85
    assert ev.source == "voice_note"


def test_voice_adapter_extracts_eye_tracking_ka() -> None:
    # Whisper-style Georgian: "Aleksandra fixated [her] eyes for 5 seconds"
    drop = _drop("ალექსანდრამ თვალი 5 წამი დაიჭირა.")
    ev = extract_eye_tracking(drop, dim_id=5)
    assert ev is not None
    assert ev.value == {"observations": [5.0]}


def test_voice_adapter_eye_tracking_no_pattern_returns_none() -> None:
    drop = _drop("She seemed alert today.")
    ev = extract_eye_tracking(drop, dim_id=5)
    assert ev is None


def test_voice_adapter_eye_tracking_rejects_zero() -> None:
    # Gamma requires strictly positive; 0 seconds is non-meaningful
    drop = _drop("Tried eye tracking; held for 0 seconds.")
    ev = extract_eye_tracking(drop, dim_id=5)
    assert ev is None


# ---------------------------------------------------------------------------
# 2. Head control — EN + KA
# ---------------------------------------------------------------------------
def test_voice_adapter_extracts_head_control_en() -> None:
    drop = _drop("Aleksandra held her head for 10 seconds in tummy time.")
    ev = extract_head_control(drop, dim_id=6)
    assert ev is not None
    assert ev.value == {"observations": [10.0]}
    assert ev.confidence == 0.85


def test_voice_adapter_extracts_head_control_ka() -> None:
    # KA: "[she] held [her] head 12 seconds"
    drop = _drop("თავი 12 წამი დაიჭირა დღეს ვარჯიშის დროს.")
    ev = extract_head_control(drop, dim_id=6)
    assert ev is not None
    assert ev.value == {"observations": [12.0]}


def test_voice_adapter_head_control_no_pattern_returns_none() -> None:
    drop = _drop("She was sleepy and quiet today.")
    ev = extract_head_control(drop, dim_id=6)
    assert ev is None


# ---------------------------------------------------------------------------
# 3. Muscle tone (clinical score only)
# ---------------------------------------------------------------------------
def test_voice_adapter_extracts_muscle_tone_when_hine_score_present() -> None:
    drop = _drop("Today's PT note: HINE score 32. Stable from last week.")
    ev = extract_muscle_tone(drop, dim_id=4)
    assert ev is not None
    assert ev.value == {"observations": [32.0]}
    assert ev.confidence == 0.85


def test_voice_adapter_extracts_muscle_tone_hammersmith_label() -> None:
    drop = _drop("Hammersmith score: 28 at this clinic visit.")
    ev = extract_muscle_tone(drop, dim_id=4)
    assert ev is not None
    assert ev.value == {"observations": [28.0]}


def test_voice_adapter_muscle_tone_rejects_out_of_range() -> None:
    # Hammersmith score is 0-78 typically; cap at 100 in adapter
    drop = _drop("Hammersmith score 250 — typo in original note.")
    ev = extract_muscle_tone(drop, dim_id=4)
    assert ev is None


def test_voice_adapter_muscle_tone_no_keyword_returns_none() -> None:
    drop = _drop("She seemed floppy today but no formal score recorded.")
    ev = extract_muscle_tone(drop, dim_id=4)
    assert ev is None


# ---------------------------------------------------------------------------
# 4. Feeding stage (4-class categorical)
# ---------------------------------------------------------------------------
def test_voice_adapter_extracts_feeding_stage_solid() -> None:
    drop = _drop("She ate solid food at dinner — a small piece of banana.")
    ev = extract_feeding_stage(drop, dim_id=9)
    assert ev is not None
    assert ev.value == {"observations": [3]}  # solid
    assert ev.confidence == 0.65


def test_voice_adapter_extracts_feeding_stage_ng() -> None:
    drop = _drop("NG tube feeding continued through the night.")
    ev = extract_feeding_stage(drop, dim_id=9)
    assert ev is not None
    assert ev.value == {"observations": [0]}  # NG-tube


def test_voice_adapter_extracts_feeding_stage_puree() -> None:
    drop = _drop("Ate pureed sweet potato today — full portion.")
    ev = extract_feeding_stage(drop, dim_id=9)
    assert ev is not None
    assert ev.value == {"observations": [2]}  # puree


def test_voice_adapter_extracts_feeding_stage_ka_partial() -> None:
    # KA: "few spoonfuls" — "ცოტა შეჭამა" + "კოვზი" → partial-oral
    drop = _drop("ცოტა შეჭამა დილით, 3 კოვზი ფაფისა.")
    ev = extract_feeding_stage(drop, dim_id=9)
    assert ev is not None
    assert ev.value == {"observations": [1]}  # partial-oral


def test_voice_adapter_feeding_stage_no_keyword_returns_none() -> None:
    drop = _drop("Quiet morning. No notes from feeding team yet.")
    ev = extract_feeding_stage(drop, dim_id=9)
    assert ev is None


# ---------------------------------------------------------------------------
# 5. Pipeline: non-voice short-circuit
# ---------------------------------------------------------------------------
def test_voice_adapter_rejects_non_voice_source(
    caplog: pytest.LogCaptureFixture,
) -> None:
    drop = _drop(
        "She held eye contact for 8 seconds.",
        input_type="pdf",
    )
    with caplog.at_level(logging.WARNING, logger="brain.belief.adapters.voice_note"):
        evidences = adapt_voice_note(drop, dimension_loader=_full_loader)
    assert evidences == []
    assert any("non-voice drop" in r.message for r in caplog.records)


def test_voice_adapter_accepts_voice_note_alias() -> None:
    """Adapter accepts both 'voice' (DB enum) and 'voice_note' (evidence enum)."""
    drop = _drop("She held eye contact for 6 seconds.", input_type="voice_note")
    evidences = adapt_voice_note(drop, dimension_loader=_full_loader)
    assert len(evidences) >= 1
    assert any(ev.dimension_id == 5 for ev in evidences)  # eye tracking


# ---------------------------------------------------------------------------
# 6. Pipeline integration
# ---------------------------------------------------------------------------
def test_voice_adapter_returns_empty_when_no_pattern_matches() -> None:
    drop = _drop("Quiet day. No new observations to record.")
    evidences = adapt_voice_note(drop, dimension_loader=_full_loader)
    assert evidences == []


def test_voice_adapter_extracts_multiple_dims_from_one_note() -> None:
    drop = _drop(
        "She held eye contact for 7 seconds. "
        "Held her head for 9 seconds in tummy time. "
        "Ate pureed sweet potato. "
        "HINE score 30."
    )
    evidences = adapt_voice_note(drop, dimension_loader=_full_loader)
    assert len(evidences) == 4
    dims = {ev.dimension_id for ev in evidences}
    assert dims == {5, 6, 4, 9}  # eye, head, tone, feeding


def test_voice_adapter_partial_extraction_subset() -> None:
    drop = _drop("She held her head for 5 seconds. Otherwise unchanged.")
    evidences = adapt_voice_note(drop, dimension_loader=_full_loader)
    assert len(evidences) == 1
    assert evidences[0].dimension_id == 6  # head only


# ---------------------------------------------------------------------------
# 7. Idempotency
# ---------------------------------------------------------------------------
def test_voice_adapter_evidence_hash_deterministic() -> None:
    drop = _drop("She held eye contact for 4 seconds.")
    ev1 = extract_eye_tracking(drop, dim_id=5)
    ev2 = extract_eye_tracking(drop, dim_id=5)
    assert ev1 is not None and ev2 is not None
    assert ev1.evidence_hash == ev2.evidence_hash


def test_voice_adapter_evidence_hash_differs_by_drop_id() -> None:
    drop_a = _drop("She held eye contact for 4 seconds.", ident="drop-a")
    drop_b = _drop("She held eye contact for 4 seconds.", ident="drop-b")
    ev_a = extract_eye_tracking(drop_a, dim_id=5)
    ev_b = extract_eye_tracking(drop_b, dim_id=5)
    assert ev_a is not None and ev_b is not None
    assert ev_a.evidence_hash != ev_b.evidence_hash


# ---------------------------------------------------------------------------
# 8. PHI safety
# ---------------------------------------------------------------------------
def test_voice_adapter_does_not_log_phi(caplog: pytest.LogCaptureFixture) -> None:
    sensitive_text = "Patient-marker ABC-99 had no notable activity today."
    drop = _drop(sensitive_text, ident="drop-phi-test")
    with caplog.at_level(logging.WARNING, logger="brain.belief.adapters.voice_note"):
        adapt_voice_note(drop, dimension_loader=_full_loader)
    combined = "\n".join(rec.message for rec in caplog.records)
    assert "Patient-marker ABC-99" not in combined
    assert "no notable activity" not in combined


def test_voice_adapter_log_warnings_only_carry_field_name_and_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    drop = _drop("Generic transcript without any pattern matches.", ident="drop-id-7")
    with caplog.at_level(logging.WARNING, logger="brain.belief.adapters.voice_note"):
        adapt_voice_note(drop, dimension_loader=_full_loader)
    for rec in caplog.records:
        # Field name + drop id are allowed; transcript body fragments are not
        assert "Generic transcript" not in rec.message


# ---------------------------------------------------------------------------
# 9. Catalog-gap handling
# ---------------------------------------------------------------------------
def test_voice_adapter_skips_when_dimension_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    drop = _drop(
        "She held eye contact for 5 seconds. Held her head for 7 seconds. "
        "HINE 32. Ate pureed food."
    )
    with caplog.at_level(logging.WARNING, logger="brain.belief.adapters.voice_note"):
        evidences = adapt_voice_note(drop, dimension_loader=_missing_loader)
    assert evidences == []
    catalog_warnings = [r for r in caplog.records if "not in catalog" in r.message]
    assert len(catalog_warnings) == 4
