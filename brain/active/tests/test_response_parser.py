"""Phase 7.4 Day 8 — response_parser tests."""

from __future__ import annotations

import pytest

from brain.active.response_parser import ParsedResponse, parse_response


def test_integer_seconds_with_unit() -> None:
    """Verifier check 7 sample 1."""
    r = parse_response("8 წამი", expected_format="integer_seconds")
    assert r.parsed_value == 8
    assert r.confidence >= 0.9


def test_integer_seconds_range_picks_largest() -> None:
    """Verifier check 7 sample 2: '5-6 seconds, let's say 8' -> largest (8)."""
    r = parse_response(
        "ხუთი-ექვსი წამი დაიჭირა", expected_format="integer_seconds"
    )
    # KA number words map to 5 + 6 = max 6
    assert r.parsed_value == 6
    assert r.confidence < 0.9  # range -> confidence drops


def test_boolean_ka_yes() -> None:
    r = parse_response("კი", expected_format="boolean")
    assert r.parsed_value is True
    assert r.confidence >= 0.9


def test_boolean_en_yes() -> None:
    r = parse_response("yes", expected_format="boolean")
    assert r.parsed_value is True


def test_integer_seconds_en() -> None:
    r = parse_response("12 seconds", expected_format="integer_seconds")
    assert r.parsed_value == 12
    assert r.confidence >= 0.9


def test_scale_in_range() -> None:
    r = parse_response("3", expected_format="scale_0_5")
    assert r.parsed_value == 3


def test_scale_out_of_range_rejected() -> None:
    r = parse_response("6", expected_format="scale_0_5")
    assert r.parsed_value is None
    assert r.confidence == 0.0


def test_boolean_ka_no() -> None:
    r = parse_response("არა", expected_format="boolean")
    assert r.parsed_value is False


def test_float_value_with_comma() -> None:
    r = parse_response("5,5", expected_format="float_value")
    assert r.parsed_value == pytest.approx(5.5)


def test_categorical_fuzzy() -> None:
    r = parse_response(
        "partial oral",
        expected_format="categorical_choice",
        options=["NG-tube", "partial-oral", "full-oral-puree", "full-oral-solid"],
    )
    assert r.parsed_value is not None
    assert "partial" in r.parsed_value.lower()


def test_unknown_format_returns_zero_confidence() -> None:
    r = parse_response("anything", expected_format="bogus_format_xyz")
    assert r.parsed_value is None
    assert r.confidence == 0.0


def test_parsed_response_pydantic_validated() -> None:
    with pytest.raises(Exception):
        ParsedResponse(
            expected_format="x",
            raw_text="y",
            parsed_value=1,
            confidence=1.5,  # out of [0,1]
        )
