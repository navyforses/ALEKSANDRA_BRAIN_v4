"""scripts/restore_neo4j.py — OPS-5 — restore a Neo4j AuraDB graph from a JSON snapshot.

Round-trip partner of `scripts/backup_neo4j.py`. That script exports every node +
relationship to JSON (AuraDB Free has no `neo4j-admin dump`, APOC is off); this one
reads that JSON back and rebuilds the graph, preserving the original topology.

Design (so the parser is unit-testable WITHOUT a live database or the neo4j driver):
  - `load_snapshot(path)`     — pure: read + validate JSON shape. Raises ValueError.
  - `_build_statements(snap)` — pure: snapshot -> ordered list of (cypher, params).
                                NO neo4j import. Validates every label / rel-type
                                against a safe-identifier pattern (they cannot be
                                parameterized in Cypher, so we whitelist them).
  - `restore(path, ...)`      — reads NEO4J_* env directly and RAISES on missing
                                (never sys.exit, to keep the import path pure); the
                                neo4j driver is lazy-imported only when actually
                                writing (`not dry_run`).

Topology is rebuilt with a temporary `_restore_id` property: every node is created
carrying its original internal id, relationships MATCH source/target by that id, then
the temp property is stripped. The whole thing runs inside ONE managed write
transaction via `session.execute_write(...)` — the neo4j 6.x API (`write_transaction`
was removed) — so a transient retry rolls back and replays cleanly.

Usage
-----
    # offline sanity (no DB, no neo4j import beyond None) — prints the plan:
    python -m scripts.restore_neo4j .planning/backups/pre_71/neo4j_snapshot_*.json --dry-run

    # real restore into an EMPTY instance:
    NEO4J_URI=neo4j+s://<id>.databases.neo4j.io NEO4J_PASSWORD=<pw> \
        python -m scripts.restore_neo4j <snapshot.json>

    # restore over a populated instance (DESTRUCTIVE — wipes first, opt-in):
    ... python -m scripts.restore_neo4j <snapshot.json> --wipe

Exit code: 0 on success / dry-run, 1 on failure or bad env.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

# Cypher cannot parameterize labels or relationship types, so they are string
# interpolated. A snapshot is our own trusted backup, but we still gate every
# identifier through this pattern so a corrupted / hand-edited file can never
# smuggle a Cypher fragment into the rebuild.
_SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Temporary property used to re-wire relationships to the right nodes, then removed.
_RESTORE_KEY = "_restore_id"


def _utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Pure parser — no neo4j import, no env, no I/O beyond reading the given file.
# ---------------------------------------------------------------------------
def load_snapshot(path: str | Path) -> dict:
    """Read + validate a backup_neo4j.py JSON snapshot. Raise ValueError if malformed."""
    raw = Path(path).read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"snapshot is not valid JSON: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("snapshot root must be a JSON object")

    nodes = data.get("nodes")
    rels = data.get("relationships")
    if not isinstance(nodes, list) or not isinstance(rels, list):
        raise ValueError("snapshot must contain 'nodes' and 'relationships' lists")

    seen_ids: set = set()
    for i, n in enumerate(nodes):
        if not isinstance(n, dict) or "internal_id" not in n:
            raise ValueError(f"node[{i}] missing required 'internal_id'")
        nid = n["internal_id"]
        if nid in seen_ids:
            # Duplicate ids make the relationship MATCH bind >1 node -> a cartesian
            # fan-out of edges. Reject up front rather than silently corrupt topology.
            raise ValueError(f"duplicate node internal_id: {nid!r}")
        seen_ids.add(nid)
        labels = n.get("labels")
        if labels is not None and not isinstance(labels, list):
            raise ValueError(f"node[{i}] 'labels' must be a list when present")
        props = n.get("properties")
        if props is not None and not isinstance(props, dict):
            raise ValueError(f"node[{i}] 'properties' must be an object when present")

    for i, r in enumerate(rels):
        if not isinstance(r, dict):
            raise ValueError(f"relationship[{i}] must be an object")
        for field in ("source_internal_id", "target_internal_id", "type"):
            if field not in r:
                raise ValueError(f"relationship[{i}] missing required '{field}'")
        if (
            r["source_internal_id"] not in seen_ids
            or r["target_internal_id"] not in seen_ids
        ):
            # A dangling edge would be silently dropped by the MATCH; fail loudly so a
            # truncated/corrupt snapshot is caught before we touch the database.
            raise ValueError(
                f"relationship[{i}] references an unknown node internal_id"
            )
        props = r.get("properties")
        if props is not None and not isinstance(props, dict):
            raise ValueError(
                f"relationship[{i}] 'properties' must be an object when present"
            )

    return data


def _build_statements(
    snapshot: dict, *, wipe: bool = False, key: str = _RESTORE_KEY
) -> list[tuple[str, dict]]:
    """Snapshot -> ordered list of (cypher, params). Pure; raises ValueError on unsafe ids.

    `key` is the temporary wiring property used to re-link relationships to the right
    nodes, then stripped. restore() passes an UNGUESSABLE per-run nonce so the key can
    never (a) collide with a real node property — preserving round-trip fidelity and
    avoiding a stray strip — nor (b) bind a foreign pre-existing node during a non-wipe
    restore. The default is only for deterministic unit tests.

    Order matters: optional wipe, then all nodes (carrying `key`), then all
    relationships (matched by `key`), then strip `key` from the restored nodes.
    """
    if not _SAFE_IDENT.match(key):
        raise ValueError(f"unsafe wiring key: {key!r}")
    statements: list[tuple[str, dict]] = []

    if wipe:
        statements.append(("MATCH (n) DETACH DELETE n", {}))

    for n in snapshot["nodes"]:
        labels = n.get("labels") or []
        for lbl in labels:
            if not _SAFE_IDENT.match(str(lbl)):
                raise ValueError(f"unsafe node label in snapshot: {lbl!r}")
        label_str = "".join(f":{lbl}" for lbl in labels)
        # Set the wiring key AFTER `+= $props` so a snapshot property that happens to
        # share the key name can never clobber the id relationships are matched on.
        cypher = f"CREATE (n{label_str}) SET n += $props, n.{key} = $rid"
        statements.append(
            (cypher, {"rid": n["internal_id"], "props": n.get("properties") or {}})
        )

    for r in snapshot["relationships"]:
        rtype = r["type"]
        if not _SAFE_IDENT.match(str(rtype)):
            raise ValueError(f"unsafe relationship type in snapshot: {rtype!r}")
        cypher = (
            f"MATCH (s {{{key}: $sid}}), (t {{{key}: $tid}}) "
            f"CREATE (s)-[rel:{rtype}]->(t) SET rel += $props"
        )
        statements.append(
            (
                cypher,
                {
                    "sid": r["source_internal_id"],
                    "tid": r["target_internal_id"],
                    "props": r.get("properties") or {},
                },
            )
        )

    # Strip the temporary wiring key. With a per-run nonce key this can only ever match
    # the nodes this run just created.
    statements.append((f"MATCH (n) WHERE n.{key} IS NOT NULL REMOVE n.{key}", {}))
    return statements


# ---------------------------------------------------------------------------
# Live restore — env read here (raise, not sys.exit), neo4j lazy-imported.
# ---------------------------------------------------------------------------
def _neo4j_creds() -> tuple[str, str, str]:
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")
    if not uri or not password:
        raise RuntimeError(
            "NEO4J_URI and NEO4J_PASSWORD env vars are required for a live restore"
        )
    return uri, user, password


def restore(path: str | Path, *, dry_run: bool = False, wipe: bool = False) -> dict:
    """Restore a snapshot into Neo4j. Returns a summary dict.

    dry_run=True builds + counts the statements WITHOUT importing neo4j or touching
    the database — safe to run anywhere. wipe=True is destructive (DETACH DELETE all
    nodes first); it is opt-in and never the default.
    """
    snapshot = load_snapshot(path)
    # Unguessable per-run wiring key for the live restore (collision- and
    # foreign-bind-proof); the deterministic default is fine for the dry-run plan.
    key = _RESTORE_KEY if dry_run else f"{_RESTORE_KEY}_{uuid.uuid4().hex}"
    statements = _build_statements(snapshot, wipe=wipe, key=key)
    summary = {
        "nodes": len(snapshot["nodes"]),
        "relationships": len(snapshot["relationships"]),
        "statements": len(statements),
        "wipe": wipe,
        "dry_run": dry_run,
        "applied": False,
    }
    if dry_run:
        return summary

    uri, user, password = _neo4j_creds()
    from neo4j import GraphDatabase  # lazy: keep the import path pure for tests

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:

        def _apply(tx):
            # The whole graph restores in one managed write transaction. At the
            # project scale (~600 nodes / ~300 edges) this is well within AuraDB
            # limits; a much larger future snapshot should chunk via UNWIND.
            for cypher, params in statements:
                tx.run(cypher, **params)

        with driver.session() as session:
            if not wipe:
                # CREATE never MERGEs, so a non-wipe restore into a populated graph
                # would silently duplicate everything. Refuse unless the target is
                # empty; --wipe is the explicit overwrite path.
                existing = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
                if existing:
                    raise RuntimeError(
                        f"target graph already has {existing} nodes; refusing a "
                        f"non-wipe restore (would duplicate). Re-run with --wipe to "
                        f"replace the existing graph."
                    )
            # neo4j 6.x managed write API; write_transaction was removed in 6.0.
            session.execute_write(_apply)
    finally:
        driver.close()

    summary["applied"] = True
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Restore a Neo4j graph from a JSON snapshot."
    )
    ap.add_argument("snapshot", help="path to neo4j_snapshot_*.json")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="parse + plan only; no neo4j import, no DB write",
    )
    ap.add_argument(
        "--wipe",
        action="store_true",
        help="DETACH DELETE every node before restoring (DESTRUCTIVE, opt-in)",
    )
    args = ap.parse_args(argv)

    _utf8()
    try:
        summary = restore(args.snapshot, dry_run=args.dry_run, wipe=args.wipe)
    except (ValueError, RuntimeError, OSError) as e:
        print(f"[FAIL] {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # live driver / Cypher errors
        print(f"[FAIL] {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    mode = "dry-run (no DB write)" if args.dry_run else "applied"
    print(
        f"[ok] restore {mode}: {summary['nodes']} nodes, "
        f"{summary['relationships']} relationships, "
        f"{summary['statements']} statements" + ("  [WIPED first]" if args.wipe else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
