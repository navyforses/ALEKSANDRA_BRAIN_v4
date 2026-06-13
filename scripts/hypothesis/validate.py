"""scripts/hypothesis/validate.py — COG-3 deterministic hypothesis sanity rules.

The 5-rule check used to live only inside the CrewAI @tool
`agents.tools.hypothesis_tools.validate_hypothesis`, which nothing on the live
path calls — so hypotheses reached the weekly brief unvalidated. This extracts
the rule logic into a PURE function so two callers can share it:

  * the @tool (which still does the Supabase/Neo4j fetches), and
  * got_pipeline._insert_hypotheses, which gates a freshly-generated row to
    status='under_review' (vs 'new') before it can surface.

The two I/O-dependent rules take pre-fetched inputs (`ledger_ids`,
`entity_match`) so this is unit-testable with no DB/Neo4j. A None input means
"could not evaluate" and the rule is False — we never vacuously pass a rule we
could not check (Core Value: an unverifiable hypothesis must not look verified).
"""

from __future__ import annotations

from typing import Any

# Statuses that surface to humans (weekly brief / cockpit). 'new' is held back
# until the validator promotes a row to 'under_review'.
SURFACED_STATUSES = ("under_review", "promising", "pursuing", "tested", "confirmed")


def validate(
    h: dict[str, Any],
    *,
    ledger_ids: set[str] | None = None,
    entity_match: bool | None = None,
) -> dict[str, Any]:
    """Run the 5 deterministic rules on one hypothesis dict.

    ledger_ids: the set of evidence_ledger ids known to exist (for the citation
        round-trip rule). None => rule cannot be evaluated => False.
    entity_match: True if the title grounds in a real Neo4j entity. None => False.

    Returns {checks, passing (>=3/5), passing_count}.
    """
    checks: dict[str, bool] = {}

    title = h.get("title") or ""
    checks["title_present"] = bool(title) and len(title) >= 8

    conf = h.get("confidence_level")
    novelty = h.get("novelty_score") or 0
    checks["confidence_not_overconfident"] = conf in (
        "moderate",
        "low",
        "very_low",
        None,
    ) or (conf == "high" and novelty < 0.9)

    # Rule 3: every supporting_paper resolves in evidence_ledger. Empty list or
    # un-fetched ids => False (not vacuously True).
    sp = h.get("supporting_papers") or []
    if sp and ledger_ids is not None:
        checks["citations_round_trip"] = all(str(i) in ledger_ids for i in sp)
    else:
        checks["citations_round_trip"] = False

    # Rule 4: title grounds in a real graph entity.
    checks["title_grounds_in_graph"] = bool(entity_match)

    # Rule 5: recommended_action is concrete (non-empty, not "consider", >=20ch).
    rec = (h.get("recommended_action") or "").lower()
    checks["action_concrete"] = bool(rec) and "consider" not in rec and len(rec) >= 20

    passing_count = sum(1 for v in checks.values() if v)
    return {
        "checks": checks,
        "passing": passing_count >= 3,
        "passing_count": passing_count,
    }


__all__ = ["validate", "SURFACED_STATUSES"]
