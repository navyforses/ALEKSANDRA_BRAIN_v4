"""Phase 7.1 Day 6 — bulk re-classification of all legacy edges.

Walks every (CO_OCCURS_WITH | RELATED_TO) edge in the live AuraDB and
rewrites it as a typed Pearl-SCM edge (CAUSES / INHIBITS / MEDIATES /
CONFOUNDS / MODERATES). MEDIATES / CONFOUNDS / MODERATES are NEVER assigned
by this script (their third-variable context exceeds lexicon + single-call
LLM scope); only CAUSES, INHIBITS, SKIP, and DELETE are produced here. The
remaining three types are populated by manual triage in Day 9 + clinician
review (`causal_review_queue`).

Strategy:
    1. Deterministic rules (Day 2 decision tree, imported from
       pilot_classify.deterministic_suggest) catch the bulk of edges.
    2. LLM fallback (Anthropic claude-haiku-4-5) is invoked ONLY for
       SKIP-classified edges, capped at --max-llm calls (default ~48 calls
       at ~$0.025/call ≈ $1.20 — matches the Phase 7.1 plan §4 budget).
    3. Each LLM call costs ≈$0.025 by conservative estimate. The budget cap
       is enforced before every API call; remaining budget is logged after
       every 10 calls and at exit.
    4. Each classified edge is replaced inside a single Neo4j transaction —
       the new typed edge gets the 4 mandatory properties (confidence
       default 0.7 for re-classified, citation 'TBD-Day-7-backfill',
       mechanism carried forward from the legacy properties when present,
       time_lag_days -1 if unknown) and the legacy edge is DELETEd in the
       same transaction. Partial-write risk minimized.

Idempotency:
    - Already-classified edges leave NO CO_OCCURS_WITH / RELATED_TO behind.
    - Re-running the script after a successful pass finds 0 legacy edges and
      exits cleanly with counts = {everything 0}. Safe to re-run on a
      partially-completed run too — only legacy-typed edges are touched.

REQUIRES backup_neo4j.py already run + migration 017 applied + Day 4 + Day 5 pilot.

Usage:
    NEO4J_URI=... NEO4J_PASSWORD=... ANTHROPIC_API_KEY=... \\
        .venv-v7/Scripts/python.exe scripts/refactor/classify_edges.py \\
            [--dry-run] [--max-llm 48]

    --dry-run    classify everything but write NOTHING. Audit JSONL is still
                 emitted so you can review pre-flight.
    --max-llm N  hard cap on LLM-fallback calls. Default chosen so estimated
                 spend <= $1.20. Set 0 to disable LLM fallback entirely.

Output:
    .planning/phase_7_1/bulk_classifications_<UTC-ts>.jsonl  (one row per edge)
    .planning/phase_7_1/bulk_summary_<UTC-ts>.json           (totals + cost)

Exit code:
    0 — completed; SKIP rate < 15% (acceptable; remaining go to causal_review_queue)
    1 — env-var missing, connection failure, or SKIP rate >= 15% (decision tree needs retuning)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from neo4j import GraphDatabase  # type: ignore
except ImportError:  # pragma: no cover — neo4j missing only blocks runtime, not import
    GraphDatabase = None  # type: ignore[assignment]

# Day 6 reuses Day 5's deterministic rule set verbatim so pilot calibration
# carries over. Tests mock this import boundary, not the rules themselves.
sys.path.insert(0, str(Path(__file__).parent))
from pilot_classify import deterministic_suggest  # noqa: E402


OUTPUT_DIR = Path(".planning/phase_7_1")

# Conservative per-call cost estimate for claude-haiku-4-5 with the short
# prompt + 100-token cap below: prompt ~300 tokens in, ~30 tokens out.
# Haiku 4.5 priced ~$1/MTok in + $5/MTok out (2026-05 anthropic pricing).
# (300 * 1 + 30 * 5) / 1_000_000 ≈ $0.00045 actual, but we keep a 50x
# safety margin so the cap fires well before any genuine $1.20 overrun.
HAIKU_COST_PER_CALL_USD = 0.025
DEFAULT_LLM_BUDGET_USD = 1.20
DEFAULT_LLM_CALL_CAP = int(DEFAULT_LLM_BUDGET_USD / HAIKU_COST_PER_CALL_USD)  # 48

# Types Day 6 can actually produce. MEDIATES / CONFOUNDS / MODERATES are
# explicitly out of scope and re-routed to SKIP if the LLM returns them.
PRODUCIBLE_TYPES = {"CAUSES", "INHIBITS"}
DECISION_TYPES = PRODUCIBLE_TYPES | {"SKIP", "DELETE"}

# SKIP rate at which we declare the run a failure (decision tree needs retuning).
SKIP_RATE_ABORT_THRESHOLD = 0.15

# Fetch every legacy edge in one shot; ~307 is well within driver result size.
FETCH_LEGACY_EDGES = """
MATCH (s)-[r:CO_OCCURS_WITH|RELATED_TO]->(t)
RETURN id(r)                AS rel_id,
       type(r)              AS legacy_type,
       coalesce(s.name, '') AS source_name,
       coalesce(t.name, '') AS target_name,
       properties(r)        AS rel_props
"""


# ---------------------------------------------------------------------------
# LLM fallback
# ---------------------------------------------------------------------------

def classify_with_llm(edge: dict, anthropic_client) -> tuple[str, str, float]:
    """Single Anthropic Haiku call returning (causal_type, rationale, est_cost_usd).

    Returns ('SKIP', reason, cost) on any parsing failure rather than raising —
    we don't want a malformed LLM response to abort a 307-edge run. Same
    treatment if the LLM picks MEDIATES / CONFOUNDS / MODERATES (out of Day 6 scope).
    """
    src = edge["source_name"] or "<unknown>"
    tgt = edge["target_name"] or "<unknown>"
    props_json = json.dumps(edge["rel_props"] or {}, default=str, ensure_ascii=False)

    prompt = (
        "Classify this directed edge into ONE Pearl-SCM causal type:\n"
        "  CAUSES   — source directly increases / produces / induces target\n"
        "  INHIBITS — source directly decreases / suppresses / blocks target\n"
        "  NONE     — non-causal (mere correlation, no mechanism)\n"
        "\n"
        f"Edge: ({src}) -[{edge['legacy_type']}]-> ({tgt})\n"
        f"Properties: {props_json}\n"
        "\n"
        "Reply with EXACTLY one line in this format:\n"
        "  TYPE | brief mechanism rationale (<=80 chars)\n"
        "Example: CAUSES | drug A elevates serum metabolite B via CYP3A4"
    )

    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # noqa: BLE001 — log + carry on, don't crash the run
        return "SKIP", f"LLM API error: {type(exc).__name__}: {exc}", HAIKU_COST_PER_CALL_USD

    text = ""
    if response.content:
        first = response.content[0]
        text = getattr(first, "text", "").strip()

    if "|" not in text:
        return "SKIP", f"LLM response unparseable: {text[:60]!r}", HAIKU_COST_PER_CALL_USD

    raw_type, _, rationale = text.partition("|")
    causal_type = raw_type.strip().upper()
    rationale = rationale.strip()

    if causal_type == "NONE":
        return "DELETE", f"LLM marked non-causal: {rationale}", HAIKU_COST_PER_CALL_USD
    if causal_type in PRODUCIBLE_TYPES:
        return causal_type, f"LLM: {rationale}", HAIKU_COST_PER_CALL_USD
    # MEDIATES / CONFOUNDS / MODERATES from the LLM -> defer.
    return "SKIP", f"LLM returned out-of-scope type {causal_type!r}: {rationale}", HAIKU_COST_PER_CALL_USD


# ---------------------------------------------------------------------------
# Graph mutation
# ---------------------------------------------------------------------------

def apply_classification(
    session,
    edge: dict,
    causal_type: str,
    rationale: str,
) -> None:
    """Replace one legacy edge with a typed causal edge.

    Behaviour:
      - SKIP   -> no mutation; legacy edge stays for manual triage.
      - DELETE -> remove the legacy edge entirely (correlation-only).
      - CAUSES / INHIBITS -> CREATE new typed edge with 4 mandatory props,
        DELETE legacy edge, all in one transaction. Mechanism carries
        forward from the legacy properties if present; confidence defaults
        to 0.7 (re-classified, not human-verified); citation set to
        'TBD-Day-7-backfill' so backfill_properties.py can find + fill it.

    Idempotency: only edges with type IN ['CO_OCCURS_WITH','RELATED_TO']
    are eligible for replacement. Already-classified edges (any of the
    Pearl-5 types) are silently ignored even if id matches.
    """
    if causal_type == "SKIP":
        return
    if causal_type == "DELETE":
        session.run(
            "MATCH ()-[r]-() WHERE id(r) = $rid "
            "AND type(r) IN ['CO_OCCURS_WITH','RELATED_TO'] "
            "DELETE r",
            rid=edge["rel_id"],
        )
        return
    if causal_type not in PRODUCIBLE_TYPES:
        raise ValueError(
            f"apply_classification: cannot produce edge type {causal_type!r} "
            f"(only {PRODUCIBLE_TYPES} or SKIP / DELETE accepted)"
        )

    # Two-step transactional swap. The relationship-type label cannot be
    # parameterised, so it is interpolated from PRODUCIBLE_TYPES — safe
    # because that set is closed.
    query = f"""
        MATCH (s)-[r_old]->(t)
        WHERE id(r_old) = $rid
          AND type(r_old) IN ['CO_OCCURS_WITH','RELATED_TO']
        WITH s, t, r_old, properties(r_old) AS old_props
        CREATE (s)-[r_new:{causal_type} {{
            confidence: 0.7,
            citation: 'TBD-Day-7-backfill',
            mechanism: coalesce(old_props.mechanism, ''),
            time_lag_days: coalesce(old_props.time_lag_days, -1),
            classified_by: 'phase_7_1_day_6',
            classified_at: datetime(),
            classified_rationale: $rationale,
            legacy_type: $legacy
        }}]->(t)
        DELETE r_old
    """
    session.run(
        query,
        rid=edge["rel_id"],
        legacy=edge["legacy_type"],
        rationale=rationale[:200],  # cap stored rationale length
    )


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
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="classify everything but write nothing to Neo4j (audit JSONL still written)",
    )
    parser.add_argument(
        "--max-llm",
        type=int,
        default=DEFAULT_LLM_CALL_CAP,
        help=(
            f"hard cap on LLM-fallback calls (default {DEFAULT_LLM_CALL_CAP}, "
            f"≈ ${DEFAULT_LLM_BUDGET_USD:.2f} estimated spend). Set 0 to disable LLM."
        ),
    )
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if GraphDatabase is None:
        print("[FAIL] neo4j driver not installed in .venv-v7", file=sys.stderr)
        print("[fix]  .venv-v7/Scripts/python.exe -m pip install neo4j", file=sys.stderr)
        return 1

    uri = _env_or_fail("NEO4J_URI")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = _env_or_fail("NEO4J_PASSWORD")

    use_llm = bool(os.environ.get("ANTHROPIC_API_KEY")) and args.max_llm > 0
    anthropic_client = None
    if use_llm:
        try:
            from anthropic import Anthropic  # type: ignore
            anthropic_client = Anthropic()
        except ImportError:
            print("[warn] anthropic SDK not installed — running deterministic-only")
            use_llm = False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    audit_path = OUTPUT_DIR / f"bulk_classifications_{timestamp}.jsonl"
    summary_path = OUTPUT_DIR / f"bulk_summary_{timestamp}.json"

    driver = GraphDatabase.driver(uri, auth=(user, password))

    # Fetch all legacy edges in one session.
    try:
        with driver.session() as session:
            edges = [dict(r) for r in session.run(FETCH_LEGACY_EDGES)]
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Neo4j fetch failed: {exc}", file=sys.stderr)
        driver.close()
        return 1

    print("=== Bulk re-classification ===")
    print(f"Mode: {'DRY-RUN (no writes)' if args.dry_run else 'LIVE writes'}")
    print(
        "LLM:  " + (
            f"enabled (max {args.max_llm} calls ≈ ${args.max_llm * HAIKU_COST_PER_CALL_USD:.2f} cap)"
            if use_llm else "disabled (deterministic-only)"
        )
    )
    print(f"Legacy edges to classify: {len(edges)}")
    print(f"Audit JSONL: {audit_path}")
    print(f"Summary:     {summary_path}")
    print()

    counts: dict[str, int] = {t: 0 for t in DECISION_TYPES}
    llm_used = 0
    llm_cost = 0.0
    write_failures = 0

    for i, edge in enumerate(edges, 1):
        # Deterministic first.
        d_type, d_rationale = deterministic_suggest(
            edge["source_name"] or "",
            edge["target_name"] or "",
            edge["legacy_type"],
            edge["rel_props"] or {},
        )

        # LLM fallback ONLY on SKIP and ONLY if budget remains.
        if d_type == "SKIP" and use_llm and llm_used < args.max_llm:
            final_type, final_rationale, call_cost = classify_with_llm(edge, anthropic_client)
            llm_used += 1
            llm_cost += call_cost
            decided_by = "llm"
            time.sleep(0.1)  # gentle rate-limit
        else:
            final_type, final_rationale = d_type, d_rationale
            decided_by = "deterministic"

        # Defensive: if classify_with_llm returned an out-of-scope type we
        # never saw before, treat it as SKIP rather than mis-counting.
        if final_type not in DECISION_TYPES:
            final_rationale = f"unexpected type {final_type!r} -> SKIP: {final_rationale}"
            final_type = "SKIP"

        counts[final_type] += 1

        record = {
            "rel_id": edge["rel_id"],
            "legacy_type": edge["legacy_type"],
            "source_name": edge["source_name"],
            "target_name": edge["target_name"],
            "deterministic_suggestion": d_type,
            "deterministic_rationale": d_rationale,
            "final_type": final_type,
            "final_rationale": final_rationale,
            "decided_by": decided_by,
            "dry_run": args.dry_run,
            "classified_at": datetime.now(timezone.utc).isoformat(),
        }
        with audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # Apply mutation unless dry-run.
        if not args.dry_run:
            try:
                with driver.session() as session:
                    apply_classification(session, edge, final_type, final_rationale)
            except Exception as exc:  # noqa: BLE001
                print(f"[FAIL] edge {edge['rel_id']} ({final_type}): {exc}", file=sys.stderr)
                write_failures += 1

        # Progress + budget heartbeat.
        if i % 50 == 0:
            remaining_budget = max(0.0, args.max_llm * HAIKU_COST_PER_CALL_USD - llm_cost)
            print(
                f"  ...{i}/{len(edges)} processed  "
                f"(LLM {llm_used}/{args.max_llm}, ${llm_cost:.2f} used, "
                f"${remaining_budget:.2f} remaining)"
            )

    # ---------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------
    print()
    print("=" * 78)
    print("=== Summary ===")
    for t in ("CAUSES", "INHIBITS", "SKIP", "DELETE"):
        print(f"  {t:10s} {counts.get(t, 0)}")
    print(f"  LLM calls:      {llm_used} / {args.max_llm}")
    print(f"  LLM est. cost:  ${llm_cost:.4f}")
    print(f"  Write failures: {write_failures}")
    print()
    print(f"Audit:   {audit_path}")
    print(f"Summary: {summary_path}")

    total = max(len(edges), 1)
    skip_rate = counts["SKIP"] / total

    summary = {
        "timestamp": timestamp,
        "total_edges": len(edges),
        "counts": counts,
        "skip_rate": skip_rate,
        "llm_calls": llm_used,
        "llm_call_cap": args.max_llm,
        "llm_est_cost_usd": round(llm_cost, 4),
        "llm_budget_cap_usd": round(args.max_llm * HAIKU_COST_PER_CALL_USD, 4),
        "write_failures": write_failures,
        "dry_run": args.dry_run,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if skip_rate > 0.05:
        print(
            f"\n[warn] SKIP rate {skip_rate:.1%} > 5% — review skipped edges "
            f"+ retune docs/PHASE_7_1_TAXONOMY.md §3 decision tree."
        )
    if skip_rate >= SKIP_RATE_ABORT_THRESHOLD:
        print(
            f"\n[FAIL] SKIP rate {skip_rate:.1%} >= {SKIP_RATE_ABORT_THRESHOLD:.0%} "
            f"abort threshold — exiting 1.",
            file=sys.stderr,
        )
        driver.close()
        return 1

    driver.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
