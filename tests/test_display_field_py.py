"""tests/test_display_field_py.py — Phase 6 Plan 06-12 Task 1.

Verifies scripts.communicator._bilingual_read.display_field_py is symmetric
with viewer/lib/i18n.ts displayField (RESEARCH.md Pitfall 6).

The 7 assertions cover every input shape the worker layer can receive from
psycopg2-decoded JSONB columns (post-migration 012) plus the legacy TEXT
tolerance contract:

  1. None                              -> ''  (empty string, never None)
  2. legacy TEXT (str)                 -> passthrough (en locale)
  3. legacy TEXT (str)                 -> passthrough (ka locale; no translation)
  4. {'en': ..., 'ka': ...} + 'en'     -> .en
  5. {'en': ..., 'ka': ...} + 'ka'     -> .ka
  6. {'en': ...}            + 'ka'     -> English fallback
  7. {}                                -> ''  (defensive empty case)

Run:
    .venv/Scripts/python.exe -X utf8 -m pytest tests/test_display_field_py.py -v
"""

from __future__ import annotations

from scripts.communicator._bilingual_read import display_field_py


def test_display_field_py_none_returns_empty_string() -> None:
    # Assertion 1: None tolerance — never returns None
    assert display_field_py(None, "en") == ""


def test_display_field_py_legacy_text_en_passthrough() -> None:
    # Assertion 2: legacy TEXT row (pre-migration-012) passes through unchanged
    assert display_field_py("legacy text", "en") == "legacy text"


def test_display_field_py_legacy_text_ka_passthrough_no_translation() -> None:
    # Assertion 3: a plain string is returned regardless of locale —
    # display_field_py is NOT a translator; it is a locale-resolver
    assert display_field_py("legacy text", "ka") == "legacy text"


def test_display_field_py_bilingual_dict_en() -> None:
    # Assertion 4: normal en read from {en, ka} dict
    field = {"en": "Hello", "ka": "გამარჯობა"}
    assert display_field_py(field, "en") == "Hello"


def test_display_field_py_bilingual_dict_ka() -> None:
    # Assertion 5: normal ka read from {en, ka} dict
    field = {"en": "Hello", "ka": "გამარჯობა"}
    assert display_field_py(field, "ka") == "გამარჯობა"


def test_display_field_py_en_only_dict_falls_back_to_en_for_ka() -> None:
    # Assertion 6: {en} without ka — English fallback per RESEARCH.md Pitfall 6
    field = {"en": "Only en"}
    assert display_field_py(field, "ka") == "Only en"


def test_display_field_py_empty_dict_returns_empty_string() -> None:
    # Assertion 7: {} defensive case — empty string, not KeyError
    assert display_field_py({}, "en") == ""
