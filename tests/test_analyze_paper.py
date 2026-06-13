"""
test_analyze_paper.py — Evidence Refinery Stage 2 (per-paper deep analysis).

No network: the LLM call (call_llm) and the Supabase I/O (_fetch_paper /
_patch_paper) are all patched. Covers parsing/coercion, the anti-fabrication
"never raises" contract, the relevance funnel write path, and the patch body.
"""

from __future__ import annotations

import json
from unittest import mock

import pytest

from scripts.analysis import analyze_paper as ap


# --------------------------------------------------------------------------- #
# _plain — bilingual / JSON / scalar flattening
# --------------------------------------------------------------------------- #
def test_plain_handles_bilingual_dict():
    assert ap._plain({"en": "hello", "ka": "გამარჯობა"}) == "hello"
    # falls back to ka when en is empty
    assert ap._plain({"en": "", "ka": "მხოლოდ ქართული"}) == "მხოლოდ ქართული"


def test_plain_handles_json_string_and_scalars():
    assert ap._plain('{"en": "x", "ka": "y"}') == "x"
    assert ap._plain("  plain text  ") == "plain text"
    assert ap._plain(None) == ""


def _clean_payload(**overrides) -> str:
    base = {
        "summary": "A small cohort study of melatonin in neonatal HIE.",
        "key_findings": ["Population: 40 neonates with HIE", "Outcome: reduced seizures"],
        "evidence_level": 3,
        "confidence_level": "moderate",
        "aleksandra_implications": "Evidence suggests a clinician discussion about melatonin adjuncts.",
        "insufficient_evidence": False,
    }
    base.update(overrides)
    return json.dumps(base)


# --------------------------------------------------------------------------- #
# analyze() — parsing + coercion
# --------------------------------------------------------------------------- #
def test_empty_paper_short_circuits_without_llm(monkeypatch):
    spy = mock.Mock()
    monkeypatch.setattr(ap, "call_llm", spy)
    result = ap.analyze("", "")
    assert result.summary is None
    assert result.insufficient_evidence is True
    spy.assert_not_called()


def test_parses_clean_json(monkeypatch):
    monkeypatch.setattr(ap, "call_llm", lambda **k: _clean_payload())
    r = ap.analyze("Melatonin in HIE", "We studied 40 neonates...")
    assert r.is_writable()
    assert r.evidence_level == 3
    assert r.confidence_level == "moderate"
    assert len(r.key_findings) == 2
    assert r.implications and "clinician" in r.implications
    assert r.insufficient_evidence is False


def test_strips_code_fence(monkeypatch):
    fenced = "```json\n" + _clean_payload() + "\n```"
    monkeypatch.setattr(ap, "call_llm", lambda **k: fenced)
    r = ap.analyze("t", "a")
    assert r.is_writable() and r.evidence_level == 3


def test_salvages_embedded_json(monkeypatch):
    noisy = "Here is the analysis you asked for:\n" + _clean_payload() + "\nThanks!"
    monkeypatch.setattr(ap, "call_llm", lambda **k: noisy)
    r = ap.analyze("t", "a")
    assert r.is_writable() and r.confidence_level == "moderate"


def test_clamps_evidence_level(monkeypatch):
    monkeypatch.setattr(ap, "call_llm", lambda **k: _clean_payload(evidence_level=9))
    assert ap.analyze("t", "a").evidence_level == 7
    monkeypatch.setattr(ap, "call_llm", lambda **k: _clean_payload(evidence_level=0))
    assert ap.analyze("t", "a").evidence_level == 1


def test_drops_invalid_confidence(monkeypatch):
    monkeypatch.setattr(ap, "call_llm", lambda **k: _clean_payload(confidence_level="medium"))
    assert ap.analyze("t", "a").confidence_level is None


def test_caps_and_truncates_key_findings(monkeypatch):
    long_finding = "x" * 500
    payload = _clean_payload(key_findings=[f"f{i}" for i in range(20)] + [long_finding])
    monkeypatch.setattr(ap, "call_llm", lambda **k: payload)
    r = ap.analyze("t", "a")
    assert len(r.key_findings) == ap.MAX_KEY_FINDINGS
    assert all(len(f) <= ap.MAX_FINDING_CHARS for f in r.key_findings)


def test_never_raises_on_llm_failure(monkeypatch):
    def boom(**_k):
        raise RuntimeError("provider 502")

    monkeypatch.setattr(ap, "call_llm", boom)
    r = ap.analyze("t", "a")
    assert r.summary is None
    assert not r.is_writable()
    assert "RuntimeError" in r.note


def test_non_json_response_is_not_writable(monkeypatch):
    monkeypatch.setattr(ap, "call_llm", lambda **k: "I cannot help with that.")
    r = ap.analyze("t", "a")
    assert r.summary is None and not r.is_writable()


def test_insufficient_evidence_flag_passthrough(monkeypatch):
    payload = _clean_payload(
        insufficient_evidence=True,
        summary="Abstract too limited to analyse",
        evidence_level=7,
        confidence_level="very_low",
    )
    monkeypatch.setattr(ap, "call_llm", lambda **k: payload)
    r = ap.analyze("t", "")
    assert r.insufficient_evidence is True
    assert r.is_writable()  # still has an honest summary to persist


# --------------------------------------------------------------------------- #
# _build_patch_body — never NULL a column we couldn't fill
# --------------------------------------------------------------------------- #
def test_patch_body_summary_only():
    r = ap.AnalysisResult(summary="just a summary")
    body = ap._build_patch_body(r)
    assert body == {"ai_summary": "just a summary"}


def test_patch_body_full():
    r = ap.AnalysisResult(
        summary="s",
        key_findings=["a", "b"],
        implications="impl",
        evidence_level=2,
        confidence_level="high",
    )
    body = ap._build_patch_body(r)
    assert body["ai_summary"] == "s"
    assert body["ai_key_findings"] == ["a", "b"]
    assert body["ai_aleksandra_implications"] == "impl"
    assert body["evidence_level"] == 2
    assert body["confidence_level"] == "high"


# --------------------------------------------------------------------------- #
# analyze_and_write — relevance funnel write path
# --------------------------------------------------------------------------- #
def test_analyze_and_write_persists_when_writable(monkeypatch):
    monkeypatch.setattr(ap, "load_env", lambda: None)
    monkeypatch.setattr(
        ap, "_fetch_paper", lambda pid: {"id": pid, "title": "T", "abstract": "A"}
    )
    monkeypatch.setattr(ap, "call_llm", lambda **k: _clean_payload())
    patched = mock.Mock(return_value=True)
    monkeypatch.setattr(ap, "_patch_paper", patched)

    r = ap.analyze_and_write("paper-1")

    assert r.is_writable()
    patched.assert_called_once()
    pid_arg, body_arg = patched.call_args.args
    assert pid_arg == "paper-1"
    assert body_arg["ai_summary"]
    assert body_arg["evidence_level"] == 3


def test_analyze_and_write_skips_write_when_not_writable(monkeypatch):
    monkeypatch.setattr(ap, "load_env", lambda: None)
    monkeypatch.setattr(
        ap, "_fetch_paper", lambda pid: {"id": pid, "title": "T", "abstract": "A"}
    )
    monkeypatch.setattr(ap, "call_llm", lambda **k: "not json")
    patched = mock.Mock()
    monkeypatch.setattr(ap, "_patch_paper", patched)

    r = ap.analyze_and_write("paper-2")

    assert not r.is_writable()
    patched.assert_not_called()


def test_analyze_and_write_paper_not_found(monkeypatch):
    monkeypatch.setattr(ap, "load_env", lambda: None)
    monkeypatch.setattr(ap, "_fetch_paper", lambda pid: None)
    spy = mock.Mock()
    monkeypatch.setattr(ap, "call_llm", spy)
    r = ap.analyze_and_write("missing")
    assert r.summary is None and r.note == "paper not found"
    spy.assert_not_called()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
