"""Phase 7.3 Day 1 — scenario.py tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from brain.sim.scenario import (
    Intervention,
    Scenario,
    build_reference_scenario,
    compute_scenario_hash,
)


# ---------------------------------------------------------------------------
# Intervention validation
# ---------------------------------------------------------------------------
def test_drug_without_dose_rejected():
    with pytest.raises(ValidationError, match="dose_mg_kg"):
        Intervention(type="drug", name="vigabatrin", start_day=200)


def test_cell_therapy_without_any_day_rejected():
    # start_day is required by Field(..., ge=0); model_validator never fires
    # without it. Use the start_day/infusion_day disagreement instead to
    # cover the "no day" branch via mismatch.
    with pytest.raises(ValidationError, match="disagree"):
        Intervention(
            type="cell_therapy",
            name="cord_blood",
            start_day=100,
            infusion_day=200,
        )


def test_manual_dimension_shift_requires_target_and_delta():
    with pytest.raises(ValidationError, match="target_dimension"):
        Intervention(
            type="manual_dimension_shift",
            name="manual_seizure_drop",
            start_day=10,
        )


def test_manual_dimension_shift_unknown_dimension_rejected():
    with pytest.raises(ValidationError, match="not in"):
        Intervention(
            type="manual_dimension_shift",
            name="bad_dim",
            start_day=10,
            target_dimension="not_a_real_dimension",
            dimension_delta=1.0,
        )


def test_mechanism_citation_must_contain_pmid_or_doi():
    with pytest.raises(ValidationError, match="mechanism_citation"):
        Intervention(
            type="drug",
            name="vigabatrin",
            start_day=10,
            dose_mg_kg=50.0,
            mechanism_citation="just a free-text mention without identifier",
        )


# ---------------------------------------------------------------------------
# Scenario validation
# ---------------------------------------------------------------------------
def test_horizon_days_zero_rejected():
    with pytest.raises(ValidationError):
        Scenario(
            name="bad",
            interventions=[],
            horizon_days=0,
            n_samples=100,
            outcomes=["seizure_freq_per_day"],
        )


def test_n_samples_above_cap_rejected():
    with pytest.raises(ValidationError):
        Scenario(
            name="bad",
            interventions=[],
            horizon_days=100,
            n_samples=10_001,
            outcomes=["seizure_freq_per_day"],
        )


def test_outcomes_unknown_dimension_rejected():
    with pytest.raises(ValidationError, match="unknown outcome"):
        Scenario(
            name="bad",
            interventions=[],
            horizon_days=100,
            n_samples=100,
            outcomes=["not_a_dim"],
        )


def test_reference_scenario_round_trip():
    s = build_reference_scenario()
    payload = s.model_dump()
    s2 = Scenario.model_validate(payload)
    assert s2.name == s.name
    assert len(s2.interventions) == len(s.interventions)
    assert s2.horizon_days == 400
    assert s2.n_samples == 100
    assert "seizure_freq_per_day" in s2.outcomes


# ---------------------------------------------------------------------------
# compute_scenario_hash
# ---------------------------------------------------------------------------
def test_compute_scenario_hash_deterministic():
    s1 = build_reference_scenario()
    s2 = build_reference_scenario()
    assert compute_scenario_hash(s1) == compute_scenario_hash(s2)


def test_compute_scenario_hash_ignores_name_description_seed():
    s1 = build_reference_scenario()
    s2 = s1.model_copy(
        update={
            "name": "different_name",
            "description": "different_description",
            "random_seed": 123,
        }
    )
    assert compute_scenario_hash(s1) == compute_scenario_hash(s2)


def test_compute_scenario_hash_intervention_order_matters():
    base = build_reference_scenario()
    reversed_interventions = list(reversed(base.interventions))
    s_reversed = base.model_copy(update={"interventions": reversed_interventions})
    assert compute_scenario_hash(base) != compute_scenario_hash(s_reversed)


def test_compute_scenario_hash_outcome_change_busts_hash():
    base = build_reference_scenario()
    fewer = base.model_copy(update={"outcomes": ["seizure_freq_per_day"]})
    assert compute_scenario_hash(base) != compute_scenario_hash(fewer)
