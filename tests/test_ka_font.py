"""tests/test_ka_font.py — W2 Georgian font provisioner (offline).

No network: _download is monkeypatched. The fake payload is ReportLab's own
bundled Vera.ttf — a REAL parseable TTF — because TTFont() parses in its
constructor and would raise TTFError on synthetic bytes before registration.
We compute Vera's sha256 at runtime and pin it, so the checksum-enforcement
path is exercised against a genuine file.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import pytest

import brain.common.ka_font as kf


def _vera_ttf() -> Path:
    import reportlab

    return Path(reportlab.__file__).resolve().parent / "fonts" / "Vera.ttf"


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    # Never touch the real cache dir, never leak registration across tests.
    monkeypatch.setattr(kf, "CACHE_DIR", tmp_path / "fonts")
    monkeypatch.setattr(kf, "_REGISTERED", False)
    for env in (
        "ALEKSANDRA_KA_FONT_SHA256",
        "ALEKSANDRA_KA_FONT_URL",
        "ALEKSANDRA_FONT_DOWNLOAD",
    ):
        monkeypatch.delenv(env, raising=False)


def _fake_download(data: bytes, calls: list):
    def _dl(url, dest):
        calls.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    return _dl


def test_download_disabled_cold_cache_raises(monkeypatch):
    monkeypatch.setenv("ALEKSANDRA_FONT_DOWNLOAD", "0")
    with pytest.raises(kf.FontProvisionError):
        kf.ensure_ka_font(strict=True)


def test_provisions_and_registers_with_pinned_checksum(monkeypatch):
    data = _vera_ttf().read_bytes()
    monkeypatch.setenv("ALEKSANDRA_KA_FONT_SHA256", hashlib.sha256(data).hexdigest())
    calls: list = []
    monkeypatch.setattr(kf, "_download", _fake_download(data, calls))

    assert kf.ensure_ka_font(strict=True) == kf.FONT_FAMILY

    from reportlab.pdfbase import pdfmetrics

    assert kf.FONT_FAMILY in pdfmetrics.getRegisteredFontNames()
    assert len(calls) == 1


def test_checksum_mismatch_raises_and_unlinks(monkeypatch):
    data = _vera_ttf().read_bytes()
    monkeypatch.setenv("ALEKSANDRA_KA_FONT_SHA256", "0" * 64)  # deliberately wrong
    monkeypatch.setattr(kf, "_download", _fake_download(data, []))

    with pytest.raises(kf.FontProvisionError):
        kf.ensure_ka_font(strict=True)
    # the corrupt download must be removed (and no .part left behind)
    assert not (kf.CACHE_DIR / kf._REGULAR_FILENAME).exists()


def test_warm_cache_skips_download(monkeypatch):
    data = _vera_ttf().read_bytes()
    kf.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (kf.CACHE_DIR / kf._REGULAR_FILENAME).write_bytes(data)

    def _boom(url, dest):
        raise AssertionError("must not download when the cache is warm")

    monkeypatch.setattr(kf, "_download", _boom)
    assert kf.ensure_ka_font(strict=True) == kf.FONT_FAMILY


def test_strict_false_returns_none_on_failure(monkeypatch, caplog):
    monkeypatch.setenv("ALEKSANDRA_FONT_DOWNLOAD", "0")
    caplog.set_level(logging.WARNING, logger="brain.common.ka_font")
    assert kf.ensure_ka_font(strict=False) is None
    assert any("KA font unavailable" in r.message for r in caplog.records)


def test_idempotent_registration(monkeypatch):
    data = _vera_ttf().read_bytes()
    monkeypatch.setenv("ALEKSANDRA_KA_FONT_SHA256", hashlib.sha256(data).hexdigest())
    calls: list = []
    monkeypatch.setattr(kf, "_download", _fake_download(data, calls))

    kf.ensure_ka_font(strict=True)
    kf.ensure_ka_font(strict=True)  # second call short-circuits on _REGISTERED
    assert len(calls) == 1


def test_family_handover_pdf_wires_ka_font(monkeypatch, tmp_path):
    # End-to-end through the real renderer (dry_run=False): the KA handover
    # must register and use the Georgian family. Font download is mocked with
    # Vera bytes; we assert the PDF builds and the family is registered (glyph
    # correctness is the real Noto font's job, covered by the opt-in net test).
    data = _vera_ttf().read_bytes()
    monkeypatch.setenv("ALEKSANDRA_KA_FONT_SHA256", hashlib.sha256(data).hexdigest())
    monkeypatch.setattr(kf, "_download", _fake_download(data, []))

    from brain.docs.pdf_builder import build_family_handover_pdf

    out = tmp_path / "handover.pdf"
    result = build_family_handover_pdf(
        summary_sections=[
            {"heading": "გამარჯობა", "body": "ქართული ტექსტი აქ.", "level": 1}
        ],
        citations=[f"https://pubmed.ncbi.nlm.nih.gov/{20000 + i}/" for i in range(5)],
        out_path=out,
        dry_run=False,
    )
    assert result == out
    assert out.exists() and out.stat().st_size > 0

    from reportlab.pdfbase import pdfmetrics

    assert kf.FONT_FAMILY in pdfmetrics.getRegisteredFontNames()
