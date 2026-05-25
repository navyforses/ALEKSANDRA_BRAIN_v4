"""Phase 7.1 Day 5 — pilot edge classification (10 samples).

Loads 10 representative CO_OCCURS_WITH / RELATED_TO edges from the live
AuraDB, shows Shako each edge (source / target / properties /
deterministic-rule suggestion), asks for confirm / correct / skip, and
writes the audit trail to .planning/phase_7_1/pilot_classifications.jsonl.

The intent is to *calibrate* the deterministic decision tree (docs/PHASE_7_1_TAXONOMY.md §3)
BEFORE the bulk classifier (Day 6, scripts/refactor/classify_edges.py)
mutates the whole graph. Day 6 imports `deterministic_suggest` from this
file as the canonical rule set; Day 5 acceptance rate < 70% means tune the
lexicon here before running Day 6.

REQUIRES backup_neo4j.py already run + migration 017 applied + Day 4 upgrade applied.

Usage:
    NEO4J_URI='neo4j+s://<your-aura>.databases.neo4j.io' \\
    NEO4J_USERNAME='neo4j' \\
    NEO4J_PASSWORD='<password>' \\
        .venv-v7/Scripts/python.exe scripts/refactor/pilot_classify.py

Output:
    .planning/phase_7_1/pilot_classifications.jsonl (one JSON record per edge)

Exit code:
    0 — pilot completed (regardless of acceptance rate; that's an advisory)
    1 — env-var missing, connection failure, or zero legacy edges found
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from neo4j import GraphDatabase  # type: ignore
except ImportError:  # pragma: no cover — neo4j missing only blocks runtime, not import
    GraphDatabase = None  # type: ignore[assignment]


OUTPUT_PATH = Path(".planning/phase_7_1/pilot_classifications.jsonl")

# Pull 10 random samples weighted by edge type so both legacy labels surface.
SAMPLE_QUERY = """
MATCH (s)-[r:CO_OCCURS_WITH|RELATED_TO]->(t)
RETURN id(r)                       AS rel_id,
       type(r)                     AS legacy_type,
       coalesce(s.name, '')        AS source_name,
       labels(s)                   AS source_labels,
       coalesce(t.name, '')        AS target_name,
       labels(t)                   AS target_labels,
       properties(r)               AS rel_props,
       rand()                      AS sort_key
ORDER BY sort_key
LIMIT 10
"""

# Valid responses from the operator. SKIP = leave the legacy edge in place for
# manual review later; DELETE = drop the edge (correlation-only, no mechanism).
CAUSAL_TYPES = ["CAUSES", "INHIBITS", "MEDIATES", "CONFOUNDS", "MODERATES", "DELETE", "SKIP"]


# ---------------------------------------------------------------------------
# Deterministic rule set (Day 2 taxonomy decision tree, §3)
# ---------------------------------------------------------------------------
# Imported by classify_edges.py (Day 6) so the same rules govern pilot + bulk.

INHIBIT_KEYWORDS = [
    "inhibit", "block", "antagonize", "antagonise", "suppress",
    "decrease", "reduce", "downregulate", "down-regulate",
]
CAUSE_KEYWORDS = [
    "cause", "produce", "induce", "result in", "lead to", "trigger",
    "upregulate", "up-regulate", "elevate", "increase", "release",
]
# Target-name patterns that strongly imply a downstream disease/injury outcome.
DISEASE_OUTCOME_TARGETS = [
    "encephalomalacia", "cyst", "atrophy", "damage", "injury", "lesion",
    "necrosis", "apoptosis", "neuronal death",
]


def _scan(text: str, keywords: list[str]) -> list[str]:
    """Return all matching keywords (lower-cased) found anywhere in `text`."""
    if not text:
        return []
    low = text.lower()
    return [kw for kw in keywords if kw in low]


def deterministic_suggest(
    source: str,
    target: str,
    legacy_type: str,
    props: dict,
) -> tuple[str, str]:
    """Apply Day 2 decision tree's 6 steps to a single edge.

    Returns (suggested_type, rationale). `suggested_type` is one of
    CAUSES / INHIBITS / SKIP / DELETE. MEDIATES, CONFOUNDS, MODERATES are
    deferred to manual review (Phase 7.1 Day 9 + clinician triage) because
    they need third-variable knowledge the lexicon can't safely infer.

    `SKIP` is the deterministic fallback when no rule fires — Day 6
    escalates SKIP edges to the LLM fallback (budget-capped).
    """
    src = source or ""
    tgt = target or ""
    mechanism_text = (props or {}).get("mechanism") or ""
    # Many Phase 2 facts kept the human-readable claim in `fact` or `summary`.
    claim_text = (props or {}).get("fact") or (props or {}).get("summary") or ""
    haystack = f"{mechanism_text} || {claim_text}"

    # Step 1 (mechanism existence) and Step 3 (sign) collapsed: if a keyword
    # fires, mechanism exists AND we know the sign.
    inhibit_hits = _scan(haystack, INHIBIT_KEYWORDS)
    if inhibit_hits:
        return "INHIBITS", f"mechanism keyword: {','.join(inhibit_hits)}"

    cause_hits = _scan(haystack, CAUSE_KEYWORDS)
    if cause_hits:
        return "CAUSES", f"mechanism keyword: {','.join(cause_hits)}"

    # Step 2 / time-lag CAUSES: a Phase 2 RELATED_TO edge whose target is a
    # disease/injury concept is almost always a downstream causal outcome
    # (e.g. HIE -> encephalomalacia). CO_OCCURS_WITH lacks direction; do not
    # promote it here without keyword evidence.
    if legacy_type == "RELATED_TO":
        outcome_hits = [t for t in DISEASE_OUTCOME_TARGETS if t in tgt.lower()]
        if outcome_hits:
            return "CAUSES", f"legacy RELATED_TO + disease-outcome target: {','.join(outcome_hits)}"

    # No rule fired -> defer to manual / LLM fallback.
    return "SKIP", "no deterministic rule matched (manual review / LLM fallback in bulk)"


# ---------------------------------------------------------------------------
# Interactive operator prompt
# ---------------------------------------------------------------------------

def prompt_user(edge: dict, suggestion: tuple[str, str]) -> tuple[str, str]:
    """Print one edge's details and read Shako's classification + rationale."""
    sugg_type, sugg_rationale = suggestion
    print()
    print("=" * 78)
    print(f"Edge id {edge['rel_id']}")
    print(f"  source: {edge['source_name']!r}  labels={edge['source_labels']}")
    print(f"    -[{edge['legacy_type']}]->")
    print(f"  target: {edge['target_name']!r}  labels={edge['target_labels']}")
    print(f"  rel properties: {json.dumps(edge['rel_props'], default=str, ensure_ascii=False)}")
    print()
    print(f"Deterministic suggestion: {sugg_type}")
    print(f"  rationale: {sugg_rationale}")
    print(f"Options: {', '.join(CAUSAL_TYPES)}")

    raw = input("Your call [Enter=accept suggestion, or type one of the options]: ").strip().upper()
    if not raw:
        decision = sugg_type
    elif raw in CAUSAL_TYPES:
        decision = raw
    else:
        print(f"  invalid input {raw!r} — defaulting to SKIP")
        decision = "SKIP"

    rationale = input("Brief rationale (optional, blank to reuse suggestion's): ").strip()
    if not rationale:
        rationale = sugg_rationale
    return decision, rationale


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _env_or_fail(name: str, default: Optional[str] = None) -> str:
    val = os.environ.get(name, default)
    if not val:
        print(f"[FAIL] {name} env var required", file=sys.stderr)
        sys.exit(1)
    return val


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if GraphDatabase is None:
        print("[FAIL] neo4j driver not installed in .venv-v7", file=sys.stderr)
        print("[fix]  .venv-v7/Scripts/python.exe -m pip install neo4j", file=sys.stderr)
        return 1

    uri = _env_or_fail("NEO4J_URI")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = _env_or_fail("NEO4J_PASSWORD")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            result = session.run(SAMPLE_QUERY)
            edges = [dict(record) for record in result]
    except Exception as exc:  # noqa: BLE001 — surface every driver failure
        print(f"[FAIL] Neo4j query failed: {exc}", file=sys.stderr)
        driver.close()
        return 1

    if not edges:
        print(
            "[FAIL] no legacy edges (CO_OCCURS_WITH / RELATED_TO) found — "
            "nothing to classify. Confirm Phase 2 data is loaded.",
            file=sys.stderr,
        )
        driver.close()
        return 1

    print(f"=== Pilot classification: {len(edges)} sample edges ===")
    print(f"Audit JSONL: {OUTPUT_PATH}")

    audit_records: list[dict] = []
    for i, edge in enumerate(edges, 1):
        print(f"\n--- Sample {i}/{len(edges)} ---")
        suggestion = deterministic_suggest(
            edge["source_name"] or "<no name>",
            edge["target_name"] or "<no name>",
            edge["legacy_type"],
            edge["rel_props"] or {},
        )
        decision, rationale = prompt_user(edge, suggestion)
        record = {
            "rel_id": edge["rel_id"],
            "legacy_type": edge["legacy_type"],
            "source_name": edge["source_name"],
            "target_name": edge["target_name"],
            "deterministic_suggestion": suggestion[0],
            "deterministic_rationale": suggestion[1],
            "final_decision": decision,
            "final_rationale": rationale,
            "classified_at": datetime.now(timezone.utc).isoformat(),
            "classified_by": "shako_pilot",
        }
        audit_records.append(record)
        with OUTPUT_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Summary — acceptance rate against deterministic suggestion is the gate
    # signal for Day 6. >= 70% = decision tree calibrated; < 70% = retune.
    matched = sum(
        1 for r in audit_records
        if r["final_decision"] == r["deterministic_suggestion"]
    )
    acceptance = matched / len(audit_records) if audit_records else 0.0
    print()
    print("=" * 78)
    print(f"Pilot complete: {len(audit_records)} edges classified")
    print(f"Deterministic-suggestion acceptance rate: {acceptance:.0%} ({matched}/{len(audit_records)})")
    print(f"Audit JSONL: {OUTPUT_PATH}")
    print()
    if acceptance >= 0.70:
        print("[OK] Acceptance rate >= 70% — Day 6 bulk run is calibrated.")
    else:
        print("[WARN] Acceptance rate < 70% — review docs/PHASE_7_1_TAXONOMY.md")
        print("       §3 decision tree + tune deterministic_suggest() before Day 6.")

    driver.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
