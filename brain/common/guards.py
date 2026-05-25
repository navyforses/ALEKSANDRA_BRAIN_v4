"""Phase 7.5 Constitutional layer - consolidated import surface.

Single entry point for callers that need any of the 13-rule
enforcement primitives. Prefer:

    from brain.common.guards import (
        require_bilingual_parity,
        redact_phi,
        check_budget_or_raise,
        assert_min_primary_sources,
        issue_override,
    )

over per-module imports, so a future internal reshuffle of brain/common
does not break call sites.

Rule -> primitive table:

    Rule #3  Recommendation / BilingualRecommendation (schemas)
    Rule #4  MissingCIError / format_recommendation_text /
             reject_output_without_ci (formatter)
    Rule #5  BilingualParityError / require_bilingual_parity /
             verify_jsonb_bilingual (i18n_guard)
    Rule #6  PHIDetectedError / redact_phi / assert_no_phi (phi_guard)
    Rule #7  BudgetError / check_budget_before_call /
             check_budget_or_raise / query_current_spend (budget_guard)
    Rule #8  BeliefWithoutEvidenceError (re-export from brain.belief.update)
    Rule #10 BudgetGuardError +
             check_simulation_uncertainty_constitutional
             (re-export from brain.sim.api)
    Rule #12 InsufficientSourcesError / count_primary_sources /
             assert_min_primary_sources (pdf_guard)
    meta     OverrideRecord / issue_override /
             is_rule_currently_overridden / list_active_overrides
             (overrides)

Rules #1, #2, #9, #11, #13 live outside the Python surface (TS
middleware, DB triggers, CI yaml) and are not re-exported here.
"""

from __future__ import annotations

# Schemas (Rule #3, parity backbone for Rule #5)
from brain.common.schemas import (
    ALLOWED_CITATION_MARKERS,
    BilingualRecommendation,
    Recommendation,
)

# Formatter (Rule #4)
from brain.common.formatter import (
    MissingCIError,
    format_recommendation_text,
    reject_output_without_ci,
)

# i18n parity (Rule #5)
from brain.common.i18n_guard import (
    BilingualParityError,
    TEXT_LEAF_KEYS,
    require_bilingual_parity,
    verify_jsonb_bilingual,
)

# PHI (Rule #6)
from brain.common.phi_guard import (
    PHI_PATTERNS,
    PHIDetectedError,
    assert_no_phi,
    redact_phi,
)

# Budget (Rule #7)
from brain.common.budget_guard import (
    BudgetError,
    DAILY_BUDGET_USD,
    MONTHLY_BUDGET_USD,
    check_budget_before_call,
    check_budget_or_raise,
    query_current_spend,
)

# Belief (Rule #8) - re-export from existing module
from brain.belief.update import BeliefWithoutEvidenceError

# PDF (Rule #12)
from brain.common.pdf_guard import (
    DEFAULT_MIN_PRIMARY_SOURCES,
    InsufficientSourcesError,
    PRIMARY_SOURCE_PATTERNS,
    assert_min_primary_sources,
    count_primary_sources,
)

# Overrides (meta)
from brain.common.overrides import (
    DEFAULT_TTL_HOURS,
    OverrideRecord,
    is_rule_currently_overridden,
    issue_override,
    list_active_overrides,
)


__all__ = [
    # Rule #3
    "ALLOWED_CITATION_MARKERS",
    "BilingualRecommendation",
    "Recommendation",
    # Rule #4
    "MissingCIError",
    "format_recommendation_text",
    "reject_output_without_ci",
    # Rule #5
    "BilingualParityError",
    "TEXT_LEAF_KEYS",
    "require_bilingual_parity",
    "verify_jsonb_bilingual",
    # Rule #6
    "PHI_PATTERNS",
    "PHIDetectedError",
    "assert_no_phi",
    "redact_phi",
    # Rule #7
    "BudgetError",
    "DAILY_BUDGET_USD",
    "MONTHLY_BUDGET_USD",
    "check_budget_before_call",
    "check_budget_or_raise",
    "query_current_spend",
    # Rule #8
    "BeliefWithoutEvidenceError",
    # Rule #12
    "DEFAULT_MIN_PRIMARY_SOURCES",
    "InsufficientSourcesError",
    "PRIMARY_SOURCE_PATTERNS",
    "assert_min_primary_sources",
    "count_primary_sources",
    # meta
    "DEFAULT_TTL_HOURS",
    "OverrideRecord",
    "is_rule_currently_overridden",
    "issue_override",
    "list_active_overrides",
]
