# tests/test_phi_redactor_georgian.py
"""I18N-10 — PHI redactor must survive into Georgian content.

Loads the 10 Georgian PHI fixtures from tests/fixtures/phase6/phi_ka.yaml
(authored in 06-02) and asserts each `must_not_appear_in_output` token is
absent from the redacted text. Hard-block fixtures (must_block: true) assert
RedactionResult.blocked == True.

Plus three smoke tests for the new redact_bilingual({en, ka}, consent)
helper — covers the canonical RESEARCH.md Pitfall 5 case where the Georgian
half of a bilingual pair contains an MRI artifact reference and the redactor
must block.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.communicator.phi_redactor import (
    ConsentFlags,
    RedactionResult,
    redact,
    redact_bilingual,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "phase6" / "phi_ka.yaml"

with open(FIXTURE_PATH, encoding="utf-8") as _f:
    FIXTURES = yaml.safe_load(_f)

assert len(FIXTURES) == 10, f"expected 10 Georgian PHI fixtures, got {len(FIXTURES)}"


# ---------------------------------------------------------------------------
# 10 parametrized fixture tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda f: f["name"])
def test_georgian_phi_redaction(fixture):
    """Each fixture's must_not_appear_in_output strings must be absent from
    the redacted text. Hard-block fixtures must return blocked=True."""
    result: RedactionResult = redact(fixture["input"], consent=ConsentFlags())

    if fixture.get("must_block"):
        assert (
            result.blocked
        ), f"{fixture['name']}: expected blocked=True, got blocked={result.blocked}"
        return

    for forbidden in fixture.get("must_not_appear_in_output", []):
        assert forbidden not in result.text, (
            f"{fixture['name']}: forbidden token {forbidden!r} survived "
            f"redaction. Output: {result.text!r}"
        )


# ---------------------------------------------------------------------------
# redact_bilingual smoke tests (3) — closes RESEARCH.md Pitfall 5
# ---------------------------------------------------------------------------
def test_redact_bilingual_clean_pair():
    """Clean pair: both halves redact patient name, no half blocks."""
    r = redact_bilingual(
        {
            "en": "Aleksandra was treated.",
            "ka": "ალექსანდრამ მკურნალობა მიიღო.",
        },
        ConsentFlags(),
    )
    assert r["blocked_or"] is False
    assert r["blocked_reasons"] == []
    assert "Aleksandra" not in r["en"].text
    # Georgian half: 'ალექსანდრამ' is the ergative form; the name root
    # 'ალექსანდრა' must be substituted with 'A.J.'.
    assert "ალექსანდრა" not in r["ka"].text or "A.J." in r["ka"].text


def test_redact_bilingual_blocks_on_english_mri_ref():
    """English half contains an MRI artifact ref → blocked_or=True."""
    r = redact_bilingual(
        {
            "en": "see viewer/scans/aleksandra.nii.gz",
            "ka": "გამარჯობა",
        },
        ConsentFlags(),
    )
    assert r["blocked_or"] is True
    assert any(reason.startswith("en:") for reason in r["blocked_reasons"])


def test_redact_bilingual_blocks_on_georgian_mri_ref():
    """Pitfall 5: Georgian half contains an MRI artifact ref → blocked_or=True.

    This is the canonical failure mode the bilingual helper was created to
    catch. Pre-06-10 the redactor was called only on the English half so a
    PHI leak in the Georgian half passed through silently.
    """
    r = redact_bilingual(
        {
            "en": "ok",
            "ka": "ხედე ფაილი viewer/scans/aleksandra.nii.gz",
        },
        ConsentFlags(),
    )
    assert r["blocked_or"] is True
    assert any(reason.startswith("ka:") for reason in r["blocked_reasons"])
