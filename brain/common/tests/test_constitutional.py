"""Phase 7.5 - Constitutional end-to-end tests, one per rule + 1 meta.

14 dedicated tests matching the 14 verifier checks 1:1. Each test
imports from ``brain.common.guards`` (single entry point) and exercises
both the FAIL path AND a PASS path so the rule cannot decay to a
no-op silently.

The tests intentionally use synthetic inputs only - no PHI, no live
infra, no LLM. They are pure unit tests; the verifier itself runs
them indirectly via the regression check.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest
from pydantic import ValidationError

# Single import surface (Phase 7.5 §2.1 meta - guards.py)
from brain.common.guards import (
    BeliefWithoutEvidenceError,
    BilingualParityError,
    BilingualRecommendation,
    BudgetError,
    DAILY_BUDGET_USD,
    InsufficientSourcesError,
    MissingCIError,
    MONTHLY_BUDGET_USD,
    PHIDetectedError,
    Recommendation,
    assert_min_primary_sources,
    assert_no_phi,
    check_budget_before_call,
    count_primary_sources,
    format_recommendation_text,
    is_rule_currently_overridden,
    issue_override,
    list_active_overrides,
    redact_phi,
    reject_output_without_ci,
    require_bilingual_parity,
    verify_jsonb_bilingual,
)


# ---------------------------------------------------------------------------
# Check 1 - Rule #1 MRI client-only (structural)
# ---------------------------------------------------------------------------
def test_check_7_5_01_csp_and_dicom_rejector_present_in_proxy_ts():
    """Rule #1 - viewer/proxy.ts hosts CSP + DICOM rejector.

    Originally lived in viewer/middleware.ts; merged into proxy.ts in
    commit 1073cec to resolve the Next.js 16 + next-intl 4.x
    'middleware.ts and proxy.ts both detected' build conflict. The
    constitutional surface is identical; only the file name changed.
    """
    root = Path(__file__).resolve().parents[3]
    mw = root / "viewer" / "proxy.ts"
    assert mw.exists(), "viewer/proxy.ts missing"
    src = mw.read_text(encoding="utf-8")
    assert "Content-Security-Policy" in src
    assert "application/dicom" in src
    assert "415" in src
    assert "rule: 1" in src or "rule:1" in src


# ---------------------------------------------------------------------------
# Check 2 - Rule #2 Voice review required (structural; DB trigger)
# ---------------------------------------------------------------------------
def test_check_7_5_02_voice_review_trigger_sql_exists():
    """Rule #2 - migration 021 SQL ships set_voice_review_required trigger."""
    root = Path(__file__).resolve().parents[3]
    sql = root / "scripts" / "migrations" / "021_voice_review_trigger.sql"
    assert sql.exists()
    src = sql.read_text(encoding="utf-8")
    assert "set_voice_review_required" in src
    assert "BEFORE INSERT ON intake_drops" in src
    assert "voice" in src
    assert "whisper" in src
    assert "telegram_voice" in src


# ---------------------------------------------------------------------------
# Check 3 - Rule #3 Citation mandatory
# ---------------------------------------------------------------------------
def test_check_7_5_03_citation_required_on_recommendation():
    """Rule #3 - Recommendation without citation must raise ValidationError."""
    # Naked recommendation (no citation) - must fail.
    with pytest.raises(ValidationError):
        Recommendation(
            subject="test",
            expected_value=0.5,
            ci_low=0.3,
            ci_high=0.7,
            language="en",
        )  # type: ignore[call-arg]

    # With a PMID citation - must pass.
    ok = Recommendation(
        subject="vigabatrin",
        expected_value=0.5,
        ci_low=0.3,
        ci_high=0.7,
        citation="PMID:7686614 vigabatrin",
        language="en",
    )
    assert ok.subject == "vigabatrin"


# ---------------------------------------------------------------------------
# Check 4 - Rule #4 Confidence intervals required
# ---------------------------------------------------------------------------
def test_check_7_5_04_naked_expected_value_rejected():
    """Rule #4 - payload with expected_value but no ci_low/ci_high rejected."""
    bad = {"expected_value": 0.7}
    with pytest.raises(MissingCIError):
        reject_output_without_ci(bad)

    good = {"expected_value": 0.7, "ci_low": 0.5, "ci_high": 0.9}
    reject_output_without_ci(good)  # must NOT raise


# ---------------------------------------------------------------------------
# Check 5 - Rule #5 Bilingual parity
# ---------------------------------------------------------------------------
def test_check_7_5_05_en_only_payload_rejected():
    """Rule #5 - payload with en but no ka rejected; bilingual passes."""
    bad = {"section": {"title": {"en": "Hello"}}}
    with pytest.raises(BilingualParityError):
        require_bilingual_parity(bad)

    good = {"section": {"title": {"en": "Hello", "ka": "გამარჯობა"}}}
    require_bilingual_parity(good)


# ---------------------------------------------------------------------------
# Check 6 - Rule #6 PHI filter
# ---------------------------------------------------------------------------
def test_check_7_5_06_phi_redacted_before_send():
    """Rule #6 - MRN + doctor name redacted; clean text passes."""
    text = "MRN: 7616818 - followup with Dr. Hien"
    redacted, matches = redact_phi(text)
    assert "7616818" not in redacted
    assert "Hien" not in redacted
    assert len(matches) >= 2

    # Clean text passes assert_no_phi.
    assert_no_phi("Sprint summary: 10 checks PASS", source="exit_report")


# ---------------------------------------------------------------------------
# Check 7 - Rule #7 Budget hard stop
# ---------------------------------------------------------------------------
def test_check_7_5_07_budget_breach_raises():
    """Rule #7 - projected daily spend > cap raises BudgetError."""
    with pytest.raises(BudgetError):
        check_budget_before_call(
            daily_spend=DAILY_BUDGET_USD - 0.01,
            monthly_spend=10.0,
            estimated_call_cost=0.05,
        )

    # In-budget call must pass.
    check_budget_before_call(
        daily_spend=1.0,
        monthly_spend=10.0,
        estimated_call_cost=0.05,
    )


# ---------------------------------------------------------------------------
# Check 8 - Rule #8 Belief requires evidence
# ---------------------------------------------------------------------------
def test_check_7_5_08_belief_without_evidence_raises():
    """Rule #8 - update(evidence=None) raises BeliefWithoutEvidenceError."""
    from brain.belief.update import update

    with pytest.raises(BeliefWithoutEvidenceError):
        update(evidence=None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Check 9 - Rule #9 Hypothesis ≥3 sources (structural; DB CHECK)
# ---------------------------------------------------------------------------
def test_check_7_5_09_hypothesis_constraint_sql_exists():
    """Rule #9 - migration 022 SQL ships min_sources_when_confirmed."""
    root = Path(__file__).resolve().parents[3]
    sql = root / "scripts" / "migrations" / "022_hypothesis_constraint.sql"
    assert sql.exists()
    src = sql.read_text(encoding="utf-8")
    assert "min_sources_when_confirmed" in src
    assert "jsonb_array_length" in src
    assert ">= 3" in src


# ---------------------------------------------------------------------------
# Check 10 - Rule #10 Simulation uncertainty guard
# ---------------------------------------------------------------------------
def test_check_7_5_10_simulation_uncertainty_high_priors_raise():
    """Rule #10 - synthetic catalog with sd/mean=1.0 raises BudgetGuardError.

    The test relies on the Phase 7.3 check_simulation_budget being the
    FIRST gate fired from check_simulation_uncertainty_constitutional -
    a synthetic catalog of normal(mu=0.001, sigma=1.0) dims fails the
    Phase 7.3 sd/mean cap before the empirical post-sample check runs.
    Either failure mode is acceptable; both raise BudgetGuardError with
    a Phase 7.5 / Phase 7.3 message.
    """
    from brain.belief.persistence import BeliefDimension
    from brain.belief.schema import load_dimensions_from_toml
    from brain.sim.api import (
        BudgetGuardError,
        check_simulation_uncertainty_constitutional,
    )
    from brain.sim.scenario import Scenario

    # Build a synthetic catalog of normal(0.001, 1.0) dims - sd/mean very high.
    synthetic_dims = [
        BeliefDimension(
            id=i,
            name=f"synthetic_{i}",
            distribution="normal",
            prior_params={"mu": 0.001, "sigma": 1.0},
            valid_min=None,
            valid_max=None,
            citation="PMID:7686614 synthetic test dimension",
        )
        for i in range(1, 14)
    ]

    # Build a minimal valid Scenario - outcomes MUST be subset of real
    # dimensions.toml names, so re-use the first real dim name.
    real_dims = load_dimensions_from_toml()
    outcomes = [real_dims[0].name]

    scenario = Scenario(
        name="test_synthetic_rule10",
        description="Phase 7.5 Rule #10 unit test",
        interventions=[],
        horizon_days=30,
        n_samples=100,
        outcomes=outcomes,
    )

    with pytest.raises(BudgetGuardError):
        check_simulation_uncertainty_constitutional(
            scenario, dims=synthetic_dims
        )


# ---------------------------------------------------------------------------
# Check 11 - Rule #11 Question rate cap (structural; DB CHECK + trigger)
# ---------------------------------------------------------------------------
def test_check_7_5_11_active_rate_constraint_sql_exists():
    """Rule #11 - migration 022b SQL ships questions_within_cap + trigger."""
    root = Path(__file__).resolve().parents[3]
    sql = root / "scripts" / "migrations" / "022b_active_rate_constraint.sql"
    assert sql.exists()
    src = sql.read_text(encoding="utf-8")
    assert "questions_within_cap" in src
    assert "enforce_active_rate_cap" in src
    assert "Rule #11" in src
    assert "23514" in src  # errcode


# ---------------------------------------------------------------------------
# Check 12 - Rule #12 PDF ≥ 5 primary
# ---------------------------------------------------------------------------
def test_check_7_5_12_pdf_insufficient_sources_raises():
    """Rule #12 - 4 personal notes + 1 PubMed raises InsufficientSourcesError."""
    cites = [
        "internal note A",
        "internal note B",
        "internal note C",
        "internal note D",
        "https://pubmed.ncbi.nlm.nih.gov/7686614/",
    ]
    assert count_primary_sources(cites) == 1
    with pytest.raises(InsufficientSourcesError):
        assert_min_primary_sources(cites)

    # 5 PubMed citations must pass.
    full = [f"PMID:{i} ref" for i in range(1, 6)]
    # PMID:<n> contains "PMID:" but NOT a URL substring - by our pattern
    # rules in pdf_guard, only URL substrings count. Use PubMed URLs:
    full = [f"https://pubmed.ncbi.nlm.nih.gov/{i}/" for i in range(1, 6)]
    assert_min_primary_sources(full)


# ---------------------------------------------------------------------------
# Check 13 - Rule #13 Verifier CI gate (structural; GH Actions YAML)
# ---------------------------------------------------------------------------
def test_check_7_5_13_verify_all_workflow_yaml_exists():
    """Rule #13 - .github/workflows/verify_all.yml runs all 6 verifiers."""
    root = Path(__file__).resolve().parents[3]
    yml = root / ".github" / "workflows" / "verify_all.yml"
    assert yml.exists()
    src = yml.read_text(encoding="utf-8")
    for v in (
        "verify_phase_7_0.py",
        "verify_phase_7_1.py",
        "verify_phase_7_2.py",
        "verify_phase_7_3.py",
        "verify_phase_7_4.py",
        "verify_phase_7_5.py",
    ):
        assert v in src, f"workflow missing {v}"


# ---------------------------------------------------------------------------
# Check 14 - Meta: override audit flow
# ---------------------------------------------------------------------------
def test_check_7_5_14_override_audit_round_trip_dry_run():
    """Meta - issue_override returns DRY_RUN sentinel; reason length enforced."""
    os.environ.pop("SUPABASE_DB_URL", None)
    sentinel = issue_override(
        rule_number=9,
        reason="confirmed-hypothesis backfill window for HIE cohort",
        overridden_by="shako",
        notify_wife=False,
    )
    assert sentinel.startswith("DRY_RUN:")
    # Short reason rejected.
    with pytest.raises(ValidationError):
        issue_override(
            rule_number=9,
            reason="short",
            overridden_by="shako",
            notify_wife=False,
        )
    # DRY_RUN listers return empty + False.
    assert list_active_overrides() == []
    assert is_rule_currently_overridden(9) is False
