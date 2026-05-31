"""Phase 7.4 Day 3 — catalog tests."""

from __future__ import annotations

import pytest

from brain.active.catalog import (
    CANDIDATE_CATALOG,
    CandidateObservation,
    all_dim_names,
    get_catalog_for_dimension,
    total_entries,
)


EXPECTED_DIM_NAMES = {
    "cyst_volume_pct",
    "brainstem_function",
    "seizure_freq_per_day",
    "muscle_tone_hammersmith",
    "eye_tracking_seconds",
    "head_control_seconds",
    "gmfcs_level",
    "bayley_cognitive",
    "feeding_stage",
    "respiratory_apnea_per_day",
    "csf_biomarkers",
    "neuroplasticity_resource",
    "family_readiness",
}


def test_all_13_dims_covered() -> None:
    """Verifier check 4 precondition: every dim has >= 1 candidate observation."""
    names = set(all_dim_names())
    assert names == EXPECTED_DIM_NAMES, f"missing: {EXPECTED_DIM_NAMES - names}; extra: {names - EXPECTED_DIM_NAMES}"


def test_every_entry_has_bilingual_descriptions() -> None:
    for c in CANDIDATE_CATALOG:
        assert c.description_en.strip(), f"empty en for {c.dim_name}/{c.observation_type}"
        assert c.description_ka.strip(), f"empty ka for {c.dim_name}/{c.observation_type}"
        # Mkhedruli sanity: at least one Georgian codepoint
        assert any("Ⴀ" <= ch <= "ჿ" for ch in c.description_ka), (
            f"description_ka not Mkhedruli for {c.dim_name}"
        )


def test_wife_time_minutes_in_range() -> None:
    for c in CANDIDATE_CATALOG:
        assert 0.0 < c.wife_time_minutes <= 15.0, (
            f"wife_time out of range for {c.dim_name}: {c.wife_time_minutes}"
        )


def test_candidate_observation_validates() -> None:
    # Pydantic rejects wife_time_minutes <= 0
    with pytest.raises(Exception):
        CandidateObservation(
            dim_name="x",
            observation_type="y",
            description_en="x",
            description_ka="ა",
            expected_format="integer_count",
            wife_time_minutes=0.0,
        )


def test_get_catalog_for_unknown_dim_empty() -> None:
    assert get_catalog_for_dimension("nonexistent_dim_xyz") == []


def test_total_entries_at_least_13() -> None:
    assert total_entries() >= 13
