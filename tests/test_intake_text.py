"""
tests/test_intake_text.py — Phase 5 Day 2 text entity extractor tests.

Default-suite tests are PHI-redactor-only — no LLM cost. The real
``extract(...)`` smoke test is opt-in via PHASE5_LLM_TESTS=1 (one
~$0.02 Claude Sonnet 4.5 call).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.manager.intake._shared import (
    BlockedByRedactor,
    MedicationEntity,
    redact_or_block,
)
from scripts.manager.intake.text_extractor import _coerce_entity, _strip_code_fence


FIXTURES = Path(__file__).parent / "fixtures" / "phase5"


def test_redact_or_block_strips_phi():
    text = (
        "Aleksandra Jincharadze (DOB 28.08.2025) visited Boston Medical Center "
        "yesterday. Vigabatrin started."
    )
    r = redact_or_block(text)
    assert "Aleksandra" not in r.text
    assert "Jincharadze" not in r.text
    assert "Boston Medical Center" not in r.text
    assert "Vigabatrin" in r.text
    assert r.redactions_count >= 2


def test_redact_or_block_raises_on_mri_filename():
    with pytest.raises(BlockedByRedactor):
        redact_or_block("see viewer/brain.nii.gz for the latest scan")


def test_strip_code_fence_handles_plain_json():
    assert _strip_code_fence('{"entities": []}') == '{"entities": []}'


def test_strip_code_fence_strips_markdown_fences():
    body = '```json\n{"entities": []}\n```'
    assert _strip_code_fence(body) == '{"entities": []}'


def test_coerce_medication_entity():
    raw = {
        "kind": "medication",
        "name": "Vigabatrin",
        "dose": "50 mg",
        "confidence": 0.92,
    }
    ent = _coerce_entity(raw)
    assert isinstance(ent, MedicationEntity)
    assert ent.name == "Vigabatrin"
    assert ent.dose == "50 mg"
    assert ent.confidence == pytest.approx(0.92)


def test_coerce_rejects_unknown_kind():
    assert _coerce_entity({"kind": "xray_finding"}) is None
    assert _coerce_entity({"kind": "medication"}) is None  # missing 'name'


@pytest.mark.skipif(
    os.environ.get("PHASE5_LLM_TESTS", "0") != "1",
    reason="set PHASE5_LLM_TESTS=1 to exercise the Claude entity extraction ($ cost)",
)
def test_extract_real_text_smoke():
    from scripts.manager.intake.text_extractor import extract

    sample = (FIXTURES / "sample_obs.txt").read_text(encoding="utf-8")
    entities = extract(sample)
    # Sample mentions Vigabatrin, weight observation, a BMC follow-up.
    # The LLM may surface 1-4 entities; we only insist on shape.
    assert isinstance(entities, list)
    for e in entities:
        assert hasattr(e, "confidence")
