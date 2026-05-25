"""Tests for brain.common guards (Phase 7.5 Rules #5, #6, #7, #12)."""

from __future__ import annotations

import os
from unittest import mock

import pytest


# ---------------------------------------------------------------------------
# Rule #5 - bilingual parity
# ---------------------------------------------------------------------------
from brain.common.i18n_guard import (
    BilingualParityError,
    require_bilingual_parity,
    verify_jsonb_bilingual,
)


def test_parity_passes_on_jsonb_shape():
    payload = {
        "section": {
            "title": {"en": "Weekly Brief", "ka": "კვირის რეპორტი"},
        }
    }
    require_bilingual_parity(payload)


def test_parity_passes_on_parallel_keys():
    payload = {
        "title_en": "Weekly Brief",
        "title_ka": "კვირის რეპორტი",
        "title": "Weekly Brief",  # legal because _en + _ka companions present
    }
    require_bilingual_parity(payload)


def test_parity_rejects_en_only_jsonb():
    payload = {
        "section": {
            "title": {"en": "Weekly Brief"},  # missing ka
        }
    }
    with pytest.raises(BilingualParityError) as exc_info:
        require_bilingual_parity(payload)
    assert "Rule #5" in str(exc_info.value)


def test_parity_rejects_bare_string_without_siblings():
    payload = {
        "title": "Weekly Brief",  # no _en + _ka, no JSONB shape
    }
    with pytest.raises(BilingualParityError):
        require_bilingual_parity(payload)


def test_verify_jsonb_bilingual_strict_shape():
    assert verify_jsonb_bilingual({"en": "a", "ka": "ბ"}) is True
    assert verify_jsonb_bilingual({"en": "a"}) is False
    assert verify_jsonb_bilingual({"en": "", "ka": "ბ"}) is False
    assert verify_jsonb_bilingual({"en": "a", "ka": "ბ", "fr": "x"}) is False
    assert verify_jsonb_bilingual("not a dict") is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Rule #6 - PHI guard
# ---------------------------------------------------------------------------
from brain.common.phi_guard import (
    PHIDetectedError,
    PHI_PATTERNS,
    assert_no_phi,
    redact_phi,
)


def test_phi_guard_redacts_mrn():
    text = "Patient MRN: 7616818 follows up Tuesday."
    out, matches = redact_phi(text)
    assert "7616818" not in out
    assert "[REDACTED:" in out
    # At least one of the two MRN patterns fires.
    names = [m.split(":", 1)[0] for m in matches]
    assert any(n.startswith("mrn") for n in names)


def test_phi_guard_redacts_aleksandra_bmc_mrn_unlabeled():
    # No "MRN:" prefix; safety net must catch the 76168xx pattern.
    text = "Reference 7616818 in the chart."
    out, matches = redact_phi(text)
    assert "7616818" not in out
    assert any("mrn_bmc_aleksandra" in m for m in matches)


def test_phi_guard_redacts_doctor_name():
    text = "Followup with Dr. Hien on Friday."
    out, matches = redact_phi(text)
    assert "Hien" not in out
    assert any(m.startswith("doctor_name:") for m in matches)


def test_phi_guard_pattern_catalog_nonempty():
    assert len(PHI_PATTERNS) >= 5
    assert "mrn_labeled" in PHI_PATTERNS
    assert "doctor_name" in PHI_PATTERNS


def test_assert_no_phi_raises_with_pattern_names_only():
    with pytest.raises(PHIDetectedError) as exc_info:
        assert_no_phi("MRN: 7616818", source="weekly_brief")
    msg = str(exc_info.value)
    assert "Rule #6" in msg
    assert "weekly_brief" in msg
    # Raw MRN digits must NOT appear in the exception message.
    assert "7616818" not in msg


def test_assert_no_phi_passes_on_clean_text():
    # Must NOT raise.
    assert_no_phi(
        "Sprint summary: 10 verifier checks PASS. No incidents.",
        source="exit_report",
    )


# ---------------------------------------------------------------------------
# Rule #7 - budget guard
# ---------------------------------------------------------------------------
from brain.common.budget_guard import (
    BudgetError,
    DAILY_BUDGET_USD,
    MONTHLY_BUDGET_USD,
    check_budget_before_call,
    check_budget_or_raise,
    query_current_spend,
)


def test_budget_passes_well_under_caps():
    check_budget_before_call(
        daily_spend=1.0,
        monthly_spend=10.0,
        estimated_call_cost=0.05,
    )


def test_budget_raises_on_daily_cap_breach():
    with pytest.raises(BudgetError) as exc_info:
        check_budget_before_call(
            daily_spend=DAILY_BUDGET_USD - 0.01,
            monthly_spend=10.0,
            estimated_call_cost=0.10,
        )
    assert "daily cap" in str(exc_info.value)


def test_budget_raises_on_monthly_cap_breach():
    with pytest.raises(BudgetError) as exc_info:
        check_budget_before_call(
            daily_spend=0.0,
            monthly_spend=MONTHLY_BUDGET_USD - 0.01,
            estimated_call_cost=0.10,
        )
    assert "monthly cap" in str(exc_info.value)


def test_budget_rejects_negative_cost():
    with pytest.raises(ValueError):
        check_budget_before_call(
            daily_spend=0.0,
            monthly_spend=0.0,
            estimated_call_cost=-0.01,
        )


def test_query_current_spend_dry_run_returns_zeros():
    # Ensure SUPABASE_DB_URL is NOT set for this test.
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SUPABASE_DB_URL", None)
        daily, monthly = query_current_spend()
        assert daily == 0.0
        assert monthly == 0.0


def test_check_budget_or_raise_dry_run_allows():
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SUPABASE_DB_URL", None)
        # Must NOT raise (DRY_RUN spend = 0).
        check_budget_or_raise(estimated_call_cost=0.05)


# ---------------------------------------------------------------------------
# Rule #12 - PDF primary-source count (Day 10 guard; tests added here per spec)
# ---------------------------------------------------------------------------
from brain.common.pdf_guard import (
    InsufficientSourcesError,
    assert_min_primary_sources,
    count_primary_sources,
)


def test_pdf_guard_passes_with_five_pubmed_citations():
    cites = [
        "https://pubmed.ncbi.nlm.nih.gov/7686614/",
        "https://pubmed.ncbi.nlm.nih.gov/32713850/",
        "https://pubmed.ncbi.nlm.nih.gov/19489084/",
        "https://pubmed.ncbi.nlm.nih.gov/0000001/",
        "https://pubmed.ncbi.nlm.nih.gov/0000002/",
    ]
    assert count_primary_sources(cites) == 5
    assert_min_primary_sources(cites)  # default minimum=5


def test_pdf_guard_raises_on_four_mixed_plus_one_primary():
    cites = [
        "personal note A",
        "personal note B",
        "personal note C",
        "personal note D",
        "https://pubmed.ncbi.nlm.nih.gov/7686614/",
    ]
    assert count_primary_sources(cites) == 1
    with pytest.raises(InsufficientSourcesError) as exc_info:
        assert_min_primary_sources(cites)
    assert "Rule #12" in str(exc_info.value)


def test_pdf_guard_raises_on_empty_list():
    with pytest.raises(InsufficientSourcesError):
        assert_min_primary_sources([], doc_id="empty_doc")
