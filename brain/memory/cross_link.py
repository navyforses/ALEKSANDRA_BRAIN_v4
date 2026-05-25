"""Phase 7.1 Day 9 — belief ↔ causal cross-link.

Populates CausalNode.dimension_ref from belief_dimensions.name match.
Lets Phase 7.2 DoWhy queries pull posterior distributions for any
CausalNode that corresponds to one of the 13 Phase 7.0 dimensions.

Run AFTER:
  - Phase 7.0 migration 016 applied + bootstrap.py UPSERTed 13 dims
  - Phase 7.1 migration 017 applied + upgrade_to_causal_nodes.cypher ran

Match strategy:
  1. Exact case-insensitive name match (toLower(n.name) = toLower($dim_name))
  2. Case-insensitive substring fallback (toLower(n.name) CONTAINS toLower($dim_name))
  3. Ambiguous (>1 match) — skipped, audit-logged for manual review
  4. Unmatched (0 matches) — skipped, audit-logged

Usage:
  NEO4J_URI=... NEO4J_PASSWORD=... SUPABASE_DB_URL=... \\
    .venv-v7/Scripts/python.exe -m brain.memory.cross_link [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Callable, Optional

from brain.belief.persistence import list_dimensions


def link_causal_nodes_to_dimensions(
    neo4j_driver: Any,
    *,
    dimension_loader: Optional[Callable[[], list]] = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """For each Phase 7.0 dimension, find any CausalNode where name matches
    (case-insensitive, common-prefix tolerant) and set dimension_ref.

    Args:
        neo4j_driver: a neo4j GraphDatabase driver (real or mock)
        dimension_loader: optional override for brain.belief.persistence.list_dimensions
                          (tests inject a no-op stub to avoid Supabase calls)
        dry_run: when True, skip the SET cypher but still walk every dim

    Returns:
        dict with keys {"counts", "audit"}:
          counts: {"linked": N, "ambiguous": N, "unmatched": N}
          audit:  list of per-dim records {"dim", "status", ...}
    """
    loader = dimension_loader or list_dimensions
    dims = loader()

    counts = {"linked": 0, "ambiguous": 0, "unmatched": 0}
    audit: list[dict[str, Any]] = []

    with neo4j_driver.session() as session:
        for dim in dims:
            # Try exact name match first; fall back to lowercase substring
            result = session.run(
                """
                MATCH (n:CausalNode)
                WHERE toLower(n.name) = toLower($dim_name)
                   OR toLower(n.name) CONTAINS toLower($dim_name)
                RETURN id(n) AS nid, n.name AS name
                """,
                dim_name=dim.name,
            )
            matches = [dict(r) for r in result]

            if len(matches) == 0:
                counts["unmatched"] += 1
                audit.append({"dim": dim.name, "status": "unmatched"})
                continue
            if len(matches) > 1:
                counts["ambiguous"] += 1
                audit.append(
                    {
                        "dim": dim.name,
                        "status": "ambiguous",
                        "candidates": [m["name"] for m in matches],
                    }
                )
                continue

            # Single match — link (or skip if dry-run)
            if not dry_run:
                session.run(
                    "MATCH (n:CausalNode) WHERE id(n) = $nid "
                    "SET n.dimension_ref = $dim_id",
                    nid=matches[0]["nid"],
                    dim_id=dim.id,
                )
            counts["linked"] += 1
            audit.append(
                {
                    "dim": dim.name,
                    "status": "linked",
                    "causal_node_id": matches[0]["nid"],
                    "causal_node_name": matches[0]["name"],
                }
            )

    return {"counts": counts, "audit": audit}


def main() -> int:
    """CLI entrypoint. Connects to live Neo4j + Supabase and runs the linker."""
    # Reconfigure stdout BEFORE argparse so --help can render any Unicode chars
    # on Windows consoles (cp1252 default codec can't encode Mkhedruli).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

    parser = argparse.ArgumentParser(
        description="Phase 7.1 Day 9 belief-to-causal cross-link"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="walk dimensions and print audit without writing dimension_ref",
    )
    args = parser.parse_args()

    import os

    uri = os.environ.get("NEO4J_URI")
    password = os.environ.get("NEO4J_PASSWORD")
    if not uri or not password:
        print("[FAIL] NEO4J_URI + NEO4J_PASSWORD required")
        return 1

    # Import neo4j lazily so --help / env-check paths don't require the dep.
    from neo4j import GraphDatabase  # type: ignore[import-not-found]

    driver = GraphDatabase.driver(
        uri,
        auth=(os.environ.get("NEO4J_USERNAME", "neo4j"), password),
    )
    try:
        result = link_causal_nodes_to_dimensions(driver, dry_run=args.dry_run)
        mode_label = "dry-run" if args.dry_run else "live"
        print(f"=== Cross-link summary ({mode_label}) ===")
        for k, v in result["counts"].items():
            print(f"  {k}: {v}")
        if result["counts"]["ambiguous"] > 0:
            print("\n[warn] ambiguous matches need manual review:")
            for a in result["audit"]:
                if a["status"] == "ambiguous":
                    print(f"  {a['dim']}: candidates={a['candidates']}")
        if result["counts"]["unmatched"] > 0:
            print("\n[info] unmatched dimensions (no CausalNode yet):")
            for a in result["audit"]:
                if a["status"] == "unmatched":
                    print(f"  {a['dim']}")
        return 0
    finally:
        driver.close()


__all__ = ["link_causal_nodes_to_dimensions", "main"]


if __name__ == "__main__":
    sys.exit(main())
