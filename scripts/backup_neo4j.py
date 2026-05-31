"""Phase 7.1 Day 1 — Neo4j AuraDB backup helper.

Exports all nodes + relationships + properties to a JSON file before any
Phase 7.1 schema mutation runs.

Why JSON not neo4j-admin dump:
  - AuraDB Free does NOT support neo4j-admin database dump (cloud-only)
  - APOC plugin is OFF by default on AuraDB Free (apoc.export.cypher unavailable)
  - JSON via py2neo/neo4j-driver works on every tier

Usage:
  NEO4J_URI='neo4j+s://<your-aura-instance>.databases.neo4j.io' \\
  NEO4J_USERNAME='neo4j' \\
  NEO4J_PASSWORD='<your-password>' \\
    .venv-v7/Scripts/python.exe scripts/backup_neo4j.py

Outputs:
  .planning/backups/pre_71/neo4j_snapshot_YYYY-MM-DDTHHMMSS.json
  .planning/backups/pre_71/manifest.txt (counts + size + timestamp)

Exit code: 0 on success, 1 on connection failure or empty export.

Restore (manual, after authoring restore_neo4j.py in a future maintenance window):
  - Read JSON, iterate nodes → CREATE; iterate relationships → MATCH+CREATE
  - Restore script intentionally NOT shipped in this phase (rollback is via Aura Console snapshot)
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from neo4j import GraphDatabase  # type: ignore
except ImportError:
    print("[FAIL] neo4j driver not installed in .venv-v7", file=sys.stderr)
    print("[fix]  .venv-v7/Scripts/python.exe -m pip install neo4j", file=sys.stderr)
    sys.exit(1)


BACKUP_DIR = Path(".planning/backups/pre_71")


def _utf8():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _check_env() -> tuple[str, str, str]:
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")
    if not uri or not password:
        print("[FAIL] NEO4J_URI and NEO4J_PASSWORD env vars required", file=sys.stderr)
        print("       Get them from https://console.neo4j.io/ -> your instance -> Connection details",
              file=sys.stderr)
        sys.exit(1)
    return uri, user, password


def export_graph(driver) -> dict:
    """Return {nodes: [...], relationships: [...]} as plain-JSON."""
    nodes = []
    rels = []
    with driver.session() as session:
        # Nodes
        result = session.run("MATCH (n) RETURN n, id(n) AS internal_id, labels(n) AS labels")
        for record in result:
            n = record["n"]
            nodes.append({
                "internal_id": record["internal_id"],
                "labels": list(record["labels"]),
                "properties": dict(n),
            })
        # Relationships
        result = session.run("""
            MATCH (s)-[r]->(t)
            RETURN id(s) AS source_id, id(t) AS target_id,
                   type(r) AS rel_type, properties(r) AS rel_props,
                   id(r) AS internal_id
        """)
        for record in result:
            rels.append({
                "internal_id": record["internal_id"],
                "source_internal_id": record["source_id"],
                "target_internal_id": record["target_id"],
                "type": record["rel_type"],
                "properties": dict(record["rel_props"]),
            })
    return {"nodes": nodes, "relationships": rels}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="connect + count only; no export written")
    parser.add_argument("--min-nodes", type=int, default=100,
                        help="abort if fewer nodes than this (sanity)")
    parser.add_argument("--min-rels", type=int, default=50,
                        help="abort if fewer relationships than this (sanity)")
    args = parser.parse_args()

    _utf8()
    print(f"=== scripts/backup_neo4j.py ({datetime.now(timezone.utc).isoformat()}) ===")
    print(f"Mode: {'dry-run' if args.dry_run else 'full export'}")

    uri, user, password = _check_env()
    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        # Verify connection + count nodes
        with driver.session() as session:
            res = session.run("MATCH (n) RETURN count(n) AS n").single()
            node_count = res["n"]
            res = session.run("MATCH ()-[r]->() RETURN count(r) AS r").single()
            rel_count = res["r"]
            res = session.run("CALL db.labels() YIELD label RETURN label").data()
            labels = sorted(set(row["label"] for row in res))
            res = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType").data()
            rel_types = sorted(set(row["relationshipType"] for row in res))

        print(f"\n[connected] {uri}")
        print(f"  Nodes:             {node_count}")
        print(f"  Relationships:     {rel_count}")
        print(f"  Node labels:       {labels}")
        print(f"  Relationship types:{rel_types}")

        if node_count < args.min_nodes:
            print(f"[FAIL] node count {node_count} < min {args.min_nodes}; aborting", file=sys.stderr)
            return 1
        if rel_count < args.min_rels:
            print(f"[FAIL] rel count {rel_count} < min {args.min_rels}; aborting", file=sys.stderr)
            return 1

        if args.dry_run:
            print("\n[dry-run] connection + counts OK; skipping export (no file written)")
            return 0

        # Full export
        print("\n[exporting] this may take 30-90s for ~600 nodes + 300 edges...")
        graph = export_graph(driver)

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
        snapshot_path = BACKUP_DIR / f"neo4j_snapshot_{timestamp}.json"
        snapshot_path.write_text(
            json.dumps(graph, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )

        # Manifest
        manifest_path = BACKUP_DIR / "manifest.txt"
        manifest_text = (
            f"Phase 7.1 Day 1 Neo4j backup\n"
            f"Generated:        {datetime.now(timezone.utc).isoformat()}\n"
            f"Snapshot file:    {snapshot_path.name}\n"
            f"Snapshot bytes:   {snapshot_path.stat().st_size}\n"
            f"Source URI:       {uri.split('@')[-1] if '@' in uri else uri}\n"
            f"Source user:      {user}\n"
            f"Nodes:            {len(graph['nodes'])}\n"
            f"Relationships:    {len(graph['relationships'])}\n"
            f"Node labels:      {labels}\n"
            f"Relationship types:{rel_types}\n"
        )
        manifest_path.write_text(manifest_text, encoding="utf-8")

        print(f"\n[ok] export complete")
        print(f"  Snapshot:  {snapshot_path}  ({snapshot_path.stat().st_size} bytes)")
        print(f"  Manifest:  {manifest_path}")
        print(f"\nNext: review counts above match expected Phase 2/2.5 state")
        print(f"      then proceed to Phase 7.1 Day 3 (apply migration 017)")
        return 0
    except Exception as e:
        print(f"[FAIL] {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
