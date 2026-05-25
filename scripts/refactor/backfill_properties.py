"""Phase 7.1 Day 7 — backfill edge properties (confidence, citation, mechanism, time_lag_days).

Day 6 (classify_edges.py) wrote new typed edges with placeholder values:
    confidence    = 0.7  (default for re-classified, not human-verified)
    citation      = 'TBD-Day-7-backfill'
    mechanism     = carried forward from legacy props (often empty)
    time_lag_days = -1 if not present on the legacy edge

This script joins those edges to Phase 2.5 evidence in Supabase
(`papers` + `hypotheses.supporting_papers`) and:

    1. Promotes citation from 'TBD-Day-7-backfill' to a real PMID when a
       matching paper is found for the (source.name, target.name) entity
       pair via the `supporting_papers` JSONB column on `hypotheses`.
    2. Bumps confidence to 0.8 if at least one supporting paper is found
       (still below the 0.9 human-verified bar).
    3. Leaves mechanism + time_lag_days unchanged if no paper text yields
       a stronger value (mechanism extraction proper is v7-librarian's job
       in a later sweep; this script only handles structured-field joins).
    4. Records EVERY edge with citation still == 'TBD-Day-7-backfill' after
       the run in the audit JSONL so Day 10 verifier can flag the gap.

REQUIRES backup_neo4j.py already run + migration 017 applied + Day 6 bulk classify completed.

Usage:
    NEO4J_URI=... NEO4J_PASSWORD=... SUPABASE_DB_URL='postgresql://...' \\
        .venv-v7/Scripts/python.exe scripts/refactor/backfill_properties.py [--dry-run]

Output:
    .planning/phase_7_1/backfill_<UTC-ts>.jsonl       (one row per edge touched/inspected)
    .planning/phase_7_1/backfill_summary_<UTC-ts>.json

Exit code:
    0 — completed; remaining-TBD count <= 25% of typed edges (acceptable)
    1 — env-var missing, connection failure, or remaining-TBD > 25% (Day 10 gap)
"""

from __future__ import annotations

import argparse
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

try:
    import psycopg  # psycopg3 — already a Phase 2 dep
except ImportError:  # pragma: no cover — Phase 2 venv has psycopg
    try:
        import psycopg2 as psycopg  # type: ignore
    except ImportError:
        psycopg = None  # type: ignore[assignment]


OUTPUT_DIR = Path(".planning/phase_7_1")

# Find every typed causal edge still wearing the Day-6 placeholder citation.
FETCH_TBD_EDGES = """
MATCH (s)-[r:CAUSES|INHIBITS|MEDIATES|CONFOUNDS|MODERATES]->(t)
WHERE r.citation = 'TBD-Day-7-backfill'
RETURN id(r)                 AS rel_id,
       type(r)               AS edge_type,
       coalesce(s.name, '')  AS source_name,
       coalesce(t.name, '')  AS target_name,
       r.confidence          AS confidence,
       r.mechanism           AS mechanism,
       r.time_lag_days       AS time_lag_days
"""

# Phase 2.5 evidence join: pull every (entity-pair-> PMID) the literature
# pipeline saw. supporting_papers is JSONB on hypotheses, so we unnest it.
# Conservative match: ANY hypothesis whose entities array includes BOTH the
# source and target name (case-insensitive) lends its papers as evidence.
FETCH_EVIDENCE = """
SELECT h.id                                             AS hypothesis_id,
       lower(coalesce(h.title, ''))                     AS title_lower,
       coalesce(h.entities, '[]'::jsonb)                AS entities,
       coalesce(h.supporting_papers, '[]'::jsonb)       AS supporting_papers
FROM   hypotheses h
WHERE  jsonb_typeof(h.supporting_papers) = 'array'
  AND  jsonb_array_length(h.supporting_papers) > 0
"""


def _env_or_fail(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        print(f"[FAIL] {name} env var required", file=sys.stderr)
        sys.exit(1)
    return val


def _entities_contains_pair(entities, source_name: str, target_name: str) -> bool:
    """JSONB `entities` is typically a list of strings or list of dicts with
    a 'name' field. Return True iff BOTH source + target are present
    (case-insensitive substring match either direction)."""
    src = (source_name or "").lower().strip()
    tgt = (target_name or "").lower().strip()
    if not src or not tgt:
        return False
    flat: list[str] = []
    try:
        for item in entities or []:
            if isinstance(item, str):
                flat.append(item.lower())
            elif isinstance(item, dict):
                name = item.get("name") or item.get("entity") or ""
                if name:
                    flat.append(str(name).lower())
    except TypeError:
        return False
    hay = " || ".join(flat)
    return src in hay and tgt in hay


def _pmid_from_paper(paper) -> Optional[str]:
    """Extract a 'PMID:NNNN' string from a supporting-paper entry.

    Accepts:
        - dict with 'pmid' or 'PMID' key
        - dict with 'id' that looks like '12345678'
        - bare string '12345678' or 'PMID:12345678'
    """
    if isinstance(paper, str):
        s = paper.strip()
        if s.upper().startswith("PMID:"):
            return s.upper()
        if s.isdigit():
            return f"PMID:{s}"
        return None
    if isinstance(paper, dict):
        for key in ("pmid", "PMID", "id", "pubmed_id"):
            v = paper.get(key)
            if not v:
                continue
            sv = str(v).strip()
            if sv.upper().startswith("PMID:"):
                return sv.upper()
            if sv.isdigit():
                return f"PMID:{sv}"
    return None


def build_evidence_index(pg_conn) -> list[dict]:
    """Pre-fetch all hypothesis evidence rows. Returns a flat list of
    {entities, papers (list[str pmid])} dicts for fast in-memory matching."""
    with pg_conn.cursor() as cur:
        cur.execute(FETCH_EVIDENCE)
        rows = cur.fetchall()
        col_names = [d[0] for d in cur.description]
    index: list[dict] = []
    for row in rows:
        rec = dict(zip(col_names, row))
        papers = rec.get("supporting_papers") or []
        # Many drivers return JSONB as already-parsed lists/dicts; some return
        # raw JSON strings depending on type registration. Handle both.
        if isinstance(papers, str):
            try:
                papers = json.loads(papers)
            except json.JSONDecodeError:
                papers = []
        entities = rec.get("entities") or []
        if isinstance(entities, str):
            try:
                entities = json.loads(entities)
            except json.JSONDecodeError:
                entities = []
        pmids = [p for p in (_pmid_from_paper(x) for x in papers) if p]
        if pmids:
            index.append({"entities": entities, "pmids": pmids})
    return index


def find_pmids_for_pair(
    evidence_index: list[dict],
    source_name: str,
    target_name: str,
) -> list[str]:
    """Return unique PMIDs found across all hypothesis rows whose entity
    list includes both source + target."""
    found: list[str] = []
    seen: set[str] = set()
    for rec in evidence_index:
        if _entities_contains_pair(rec["entities"], source_name, target_name):
            for pmid in rec["pmids"]:
                if pmid not in seen:
                    seen.add(pmid)
                    found.append(pmid)
    return found


def apply_backfill(
    session,
    rel_id: int,
    edge_type: str,
    new_citation: str,
    new_confidence: float,
) -> None:
    """Update a single edge's citation + confidence transactionally.

    edge_type is interpolated (closed set; not parameterisable in Cypher) so
    we restrict it to the 5 Pearl types.
    """
    if edge_type not in {"CAUSES", "INHIBITS", "MEDIATES", "CONFOUNDS", "MODERATES"}:
        raise ValueError(f"apply_backfill: invalid edge_type {edge_type!r}")
    query = f"""
        MATCH ()-[r:{edge_type}]->()
        WHERE id(r) = $rid
        SET r.citation        = $cit,
            r.confidence      = $conf,
            r.backfilled_at   = datetime(),
            r.backfilled_by   = 'phase_7_1_day_7'
    """
    session.run(query, rid=rel_id, cit=new_citation, conf=new_confidence)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="inspect everything but write nothing back to Neo4j",
    )
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if GraphDatabase is None:
        print("[FAIL] neo4j driver not installed in .venv-v7", file=sys.stderr)
        return 1
    if psycopg is None:
        print("[FAIL] psycopg / psycopg2 not installed", file=sys.stderr)
        return 1

    neo_uri = _env_or_fail("NEO4J_URI")
    neo_user = os.environ.get("NEO4J_USERNAME", "neo4j")
    neo_pw = _env_or_fail("NEO4J_PASSWORD")
    pg_url = _env_or_fail("SUPABASE_DB_URL")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    audit_path = OUTPUT_DIR / f"backfill_{timestamp}.jsonl"
    summary_path = OUTPUT_DIR / f"backfill_summary_{timestamp}.json"

    driver = GraphDatabase.driver(neo_uri, auth=(neo_user, neo_pw))

    # Fetch Neo4j edges needing backfill.
    try:
        with driver.session() as session:
            edges = [dict(r) for r in session.run(FETCH_TBD_EDGES)]
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Neo4j fetch failed: {exc}", file=sys.stderr)
        driver.close()
        return 1

    print("=== Backfill ===")
    print(f"Mode:                  {'DRY-RUN (no writes)' if args.dry_run else 'LIVE writes'}")
    print(f"Edges with TBD citation: {len(edges)}")
    if not edges:
        print("[OK] no TBD-citation edges remaining — nothing to backfill.")
        summary_path.write_text(
            json.dumps({"timestamp": timestamp, "tbd_edges": 0, "backfilled": 0, "still_tbd": 0,
                        "dry_run": args.dry_run}, indent=2),
            encoding="utf-8",
        )
        driver.close()
        return 0

    # Build evidence index from Supabase.
    print("Building evidence index from Supabase hypotheses.supporting_papers ...")
    try:
        pg_conn = psycopg.connect(pg_url)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Supabase connection failed: {exc}", file=sys.stderr)
        driver.close()
        return 1

    try:
        evidence_index = build_evidence_index(pg_conn)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] evidence index build failed: {exc}", file=sys.stderr)
        pg_conn.close()
        driver.close()
        return 1
    finally:
        pg_conn.close()

    print(f"Evidence index: {len(evidence_index)} hypothesis rows carrying ≥1 PMID")
    print(f"Audit JSONL: {audit_path}")
    print()

    backfilled = 0
    still_tbd = 0
    write_failures = 0

    for i, edge in enumerate(edges, 1):
        pmids = find_pmids_for_pair(
            evidence_index, edge["source_name"], edge["target_name"]
        )
        if pmids:
            new_citation = ",".join(pmids)
            # Confidence bump: 0.7 (Day 6 default) -> 0.8 (paper-backed).
            new_confidence = max(0.8, float(edge.get("confidence") or 0.0))
            action = "backfilled"
            if not args.dry_run:
                try:
                    with driver.session() as session:
                        apply_backfill(
                            session,
                            edge["rel_id"],
                            edge["edge_type"],
                            new_citation,
                            new_confidence,
                        )
                except Exception as exc:  # noqa: BLE001
                    print(f"[FAIL] edge {edge['rel_id']}: {exc}", file=sys.stderr)
                    write_failures += 1
                    action = "write_failed"
                else:
                    backfilled += 1
            else:
                backfilled += 1
        else:
            new_citation = "TBD-Day-7-backfill"
            new_confidence = float(edge.get("confidence") or 0.0)
            action = "no_evidence_found"
            still_tbd += 1

        record = {
            "rel_id": edge["rel_id"],
            "edge_type": edge["edge_type"],
            "source_name": edge["source_name"],
            "target_name": edge["target_name"],
            "old_citation": "TBD-Day-7-backfill",
            "new_citation": new_citation,
            "old_confidence": edge.get("confidence"),
            "new_confidence": new_confidence,
            "pmids_found": pmids,
            "action": action,
            "dry_run": args.dry_run,
            "backfilled_at": datetime.now(timezone.utc).isoformat(),
        }
        with audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        if i % 50 == 0:
            print(f"  ...{i}/{len(edges)} processed  ({backfilled} backfilled, {still_tbd} still TBD)")

    # ---------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------
    print()
    print("=" * 78)
    print("=== Summary ===")
    print(f"  Total TBD edges:   {len(edges)}")
    print(f"  Backfilled:        {backfilled}")
    print(f"  Still TBD:         {still_tbd}")
    print(f"  Write failures:    {write_failures}")
    print()
    print(f"Audit:   {audit_path}")
    print(f"Summary: {summary_path}")

    total = max(len(edges), 1)
    remaining_rate = still_tbd / total

    summary = {
        "timestamp": timestamp,
        "tbd_edges": len(edges),
        "backfilled": backfilled,
        "still_tbd": still_tbd,
        "remaining_tbd_rate": remaining_rate,
        "write_failures": write_failures,
        "evidence_index_size": len(evidence_index),
        "dry_run": args.dry_run,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if remaining_rate > 0.25:
        print(
            f"\n[FAIL] {remaining_rate:.1%} of TBD edges remain without PMIDs "
            "(> 25% gap) — Day 10 verifier will block. Consider running "
            "v7-librarian PubMed backfill OR widen entity-matching in this script.",
            file=sys.stderr,
        )
        driver.close()
        return 1

    driver.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
