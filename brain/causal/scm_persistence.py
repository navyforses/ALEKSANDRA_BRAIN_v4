"""Phase 7.2 Days 12-13 — SCM persistence (CRUD + audit + revert).

Reads / writes the three migration-018 tables (``scms``,
``scm_audit_log``, ``causal_estimates``) via sync ``psycopg2``,
mirroring the Phase 7.0 ``brain.belief.persistence`` convention:

  * env loaded via ``scripts.ledger.load_env``
  * per-call short-lived connections (no module-level pool)
  * service-role DSN from ``os.environ["SUPABASE_DB_URL"]``,
    ``sslmode="require"``

Versioning model (immutable history):

    Every mutation appends a NEW row at ``version = prev_max + 1``;
    no UPDATE-in-place. This keeps the audit lineage reconstructible
    from a single ``SELECT * FROM scms WHERE name = ? ORDER BY version``.
    "delete" is a soft delete that writes ``graph_json={'_deleted': True}``
    at the new head; "revert" copies an older version's payload to a
    new head row. The audit ledger (``scm_audit_log``) carries the
    per-mutation JSONB diff for fast queries without re-deriving from
    the row sequence.

Code-complete-without-infra contract (mirrors
``brain/causal/cross_link.py``): every public CRUD function checks
``SUPABASE_DB_URL``; when unset it returns a deterministic
``"DRY_RUN:<sha256>"`` sentinel and logs to stderr instead of touching
the DB. Unit tests run end-to-end without Supabase.

Hard rule — citation preservation on round-trip: SCM graphs carry
``citation`` / ``confidence`` / ``mechanism`` / ``time_lag_days`` per
the Phase 7.1 taxonomy. ``scm_to_graph_json`` + ``graph_json_to_scm``
use ``nx.node_link_data`` / ``nx.node_link_graph`` which preserve all
edge / node attributes losslessly.

Reference:
    - scripts/migrations/018_scm_tables.sql (schema contract)
    - brain/causal/cross_link.py (DRY_RUN-when-DSN-unset pattern)
    - brain/belief/persistence.py (psycopg2 + RealDictCursor pattern)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Any, Literal, Optional

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from brain.causal.scm import SCM, build_scm_from_graph


# ---------------------------------------------------------------------------
# Lazy psycopg2 import (matches brain/belief/persistence.py)
# ---------------------------------------------------------------------------
try:
    import psycopg2
    import psycopg2.extras
except Exception:  # pragma: no cover — keeps module importable if psycopg2 missing
    psycopg2 = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Env loader fallback (mirrors brain/belief/persistence.py)
# ---------------------------------------------------------------------------
try:
    from scripts.ledger import load_env  # type: ignore
except Exception:  # pragma: no cover

    def load_env() -> None:  # noqa: D401
        """No-op fallback when scripts.ledger is not on sys.path."""
        return None


# ---------------------------------------------------------------------------
# Allowed audit operations (matches migration 018 CHECK)
# ---------------------------------------------------------------------------
ALLOWED_OPERATIONS = frozenset({"create", "update", "delete", "revert"})


# ---------------------------------------------------------------------------
# Pydantic models — match the migration-018 schema
# ---------------------------------------------------------------------------
class SCMRecord(BaseModel):
    """One row of ``scms``. Matches migration 018 §Part 1."""

    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None  # UUID
    name: str = Field(..., min_length=1)
    version: int = Field(..., ge=1)
    description: Optional[str] = None
    graph_json: dict[str, Any]
    created_by: str = Field(..., min_length=1)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SCMAuditEntry(BaseModel):
    """One row of ``scm_audit_log``. Matches migration 018 §Part 2."""

    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None  # UUID
    scm_id: Optional[str] = None  # UUID
    operation: Literal["create", "update", "delete", "revert"]
    diff: dict[str, Any]
    actor: str = Field(..., min_length=1)
    occurred_at: Optional[datetime] = None

    @field_validator("operation")
    @classmethod
    def _op_allowed(cls, v: str) -> str:
        if v not in ALLOWED_OPERATIONS:
            raise ValueError(
                f"operation must be one of {sorted(ALLOWED_OPERATIONS)}, got {v!r}"
            )
        return v


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------
def _get_conn():
    """Return a service-role psycopg2 connection. Raise if DSN missing."""
    if psycopg2 is None:
        raise RuntimeError(
            "psycopg2 is not installed in the active venv; "
            "brain.causal.scm_persistence requires it for DB-mode operation."
        )
    load_env()
    dsn = os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError(
            "SUPABASE_DB_URL is not set. brain.causal.scm_persistence requires "
            "a service-role Postgres connection string."
        )
    return psycopg2.connect(dsn, sslmode="require")


def _supabase_url_set() -> bool:
    """True iff ``SUPABASE_DB_URL`` is set in the environment."""
    load_env()
    return bool(os.environ.get("SUPABASE_DB_URL"))


# ---------------------------------------------------------------------------
# Graph <-> JSON round-trip
# ---------------------------------------------------------------------------
def _normalise_edges_for_diff(graph_json: dict[str, Any]) -> set[tuple[str, str]]:
    """Project a graph_json payload to its directed edge set.

    Used by :func:`compute_diff`. Tolerates the two NetworkX node-link
    schemas: ``"links"`` (pre-3.4 default) and ``"edges"`` (modern).
    Source / target may be node id (int) or string; always coerced to
    string for set comparability.
    """
    if not isinstance(graph_json, dict):
        return set()
    raw_edges = graph_json.get("links") or graph_json.get("edges") or []
    out: set[tuple[str, str]] = set()
    for e in raw_edges:
        if isinstance(e, dict) and "source" in e and "target" in e:
            out.add((str(e["source"]), str(e["target"])))
    return out


def _normalise_nodes_for_diff(graph_json: dict[str, Any]) -> set[str]:
    """Project a graph_json payload to its node-id set (stringified)."""
    if not isinstance(graph_json, dict):
        return set()
    raw_nodes = graph_json.get("nodes") or []
    out: set[str] = set()
    for n in raw_nodes:
        if isinstance(n, dict) and "id" in n:
            out.add(str(n["id"]))
    return out


def scm_to_graph_json(scm: SCM) -> dict[str, Any]:
    """Serialise an :class:`~brain.causal.scm.SCM` to JSON-safe dict.

    Uses ``nx.node_link_data`` which preserves every node + edge
    attribute (including ``citation``, ``confidence``, ``mechanism``,
    ``time_lag_days``, ``edge_type``, ``dimension_ref``, ``labels``).
    The SCM's spec fields (``name``, ``treatment``, ``outcome``,
    ``confounders``, ``mediators``, ``description``) are nested under a
    top-level ``"scm_spec"`` key alongside the standard ``nodes``,
    ``edges``, ``directed``, ``multigraph`` keys.

    ``scm.graph`` MUST be set; otherwise raises ``ValueError``.

    NOTE: ``edges`` key may be named ``"links"`` on older networkx
    versions. The downstream :func:`graph_json_to_scm` accepts both.
    """
    if scm.graph is None:
        raise ValueError("scm.graph is None; cannot serialise to graph_json")
    # ``edges="edges"`` forces the modern key; default in nx 3.x is
    # ``edges="links"`` for backward compat. We standardise on "edges"
    # for forward-compat with networkx >= 3.6.
    try:
        payload = nx.node_link_data(scm.graph, edges="edges")
    except TypeError:  # pragma: no cover — older networkx fallback
        payload = nx.node_link_data(scm.graph)
    payload["scm_spec"] = {
        "name": scm.name,
        "description": scm.description,
        "treatment": scm.treatment,
        "outcome": scm.outcome,
        "confounders": list(scm.confounders),
        "mediators": list(scm.mediators),
    }
    return payload


def graph_json_to_scm(payload: dict[str, Any]) -> SCM:
    """Round-trip the JSON payload back into an :class:`SCM` instance.

    Inverse of :func:`scm_to_graph_json`. Reads the ``scm_spec`` sub-dict
    for the SCM-level fields and rebuilds the underlying ``nx.DiGraph``
    via ``nx.node_link_graph``, preserving all edge / node attributes.

    Raises:
        ValueError: if ``payload`` is missing ``scm_spec`` or graph
            structure keys, or if the graph rebuild fails.
    """
    if not isinstance(payload, dict):
        raise ValueError(f"payload must be a dict, got {type(payload).__name__}")
    if "scm_spec" not in payload:
        raise ValueError("payload missing 'scm_spec' sub-dict")
    spec = payload["scm_spec"]

    # Reconstruct the graph; tolerate both "edges" and "links" key names.
    # Defensive: networkx mutates its input dict; deep-copy via JSON.
    graph_payload = {k: v for k, v in payload.items() if k != "scm_spec"}
    try:
        graph = nx.node_link_graph(graph_payload, edges="edges", directed=True)
    except (TypeError, KeyError):
        # Older nx default key is "links"; try without forcing.
        graph = nx.node_link_graph(graph_payload, directed=True)
    if not isinstance(graph, nx.DiGraph):
        graph = nx.DiGraph(graph)

    return SCM(
        name=spec["name"],
        description=spec.get("description"),
        treatment=spec["treatment"],
        outcome=spec["outcome"],
        confounders=list(spec.get("confounders", []) or []),
        mediators=list(spec.get("mediators", []) or []),
        graph=graph,
    )


# ---------------------------------------------------------------------------
# Diff helper
# ---------------------------------------------------------------------------
def compute_diff(
    prev_graph_json: dict[str, Any],
    new_graph_json: dict[str, Any],
) -> dict[str, list]:
    """Symmetric-difference diff between two graph_json payloads.

    Returns a dict with four lists::

        {
            "added_edges":   [(src, tgt), ...],  # in new but not prev
            "removed_edges": [(src, tgt), ...],  # in prev but not new
            "added_nodes":   [id, ...],
            "removed_nodes": [id, ...],
        }

    All ids are stringified for stable JSON output. Lists are sorted.
    """
    prev_edges = _normalise_edges_for_diff(prev_graph_json)
    new_edges = _normalise_edges_for_diff(new_graph_json)
    prev_nodes = _normalise_nodes_for_diff(prev_graph_json)
    new_nodes = _normalise_nodes_for_diff(new_graph_json)

    return {
        "added_edges": sorted(list(new_edges - prev_edges)),
        "removed_edges": sorted(list(prev_edges - new_edges)),
        "added_nodes": sorted(list(new_nodes - prev_nodes)),
        "removed_nodes": sorted(list(prev_nodes - new_nodes)),
    }


# ---------------------------------------------------------------------------
# DRY_RUN sentinel
# ---------------------------------------------------------------------------
def _dry_run_sentinel(payload: dict[str, Any]) -> str:
    """Deterministic ``"DRY_RUN:<sha256_hex>"`` for the given payload.

    Mirrors the convention from ``brain/causal/cross_link.py`` so callers
    can dedup-test would-be writes without DB access.
    """
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return f"DRY_RUN:{digest}"


def _stderr(msg: str) -> None:
    print(f"[scm_persistence] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CRUD — create
# ---------------------------------------------------------------------------
def create_scm(
    scm: SCM,
    *,
    actor: str,
    description: Optional[str] = None,
) -> str:
    """Create a new SCM at version 1.

    Args:
        scm: the SCM to persist (``scm.graph`` must be set).
        actor: identifier of the user / agent making the change
            (recorded in the audit ledger).
        description: optional human description; falls back to
            ``scm.description``.

    Returns:
        * Real SCM UUID (string) when ``SUPABASE_DB_URL`` is set and
          the INSERT succeeds.
        * ``"DRY_RUN:<sha256>"`` sentinel otherwise.
    """
    if not actor or not actor.strip():
        raise ValueError("actor is required for audit lineage")
    payload = scm_to_graph_json(scm)
    desc = description if description is not None else scm.description

    if not _supabase_url_set():
        sentinel = _dry_run_sentinel(
            {"op": "create", "name": scm.name, "graph_json": payload}
        )
        _stderr(
            f"SUPABASE_DB_URL unset; create_scm({scm.name!r}) -> {sentinel}"
        )
        return sentinel

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scms
                    (name, version, description, graph_json, created_by)
                VALUES (%s, 1, %s, %s::jsonb, %s)
                RETURNING id
                """,
                (scm.name, desc, json.dumps(payload), actor),
            )
            row = cur.fetchone()
            scm_uuid = str(row[0])

            cur.execute(
                """
                INSERT INTO scm_audit_log
                    (scm_id, operation, diff, actor)
                VALUES (%s, 'create', %s::jsonb, %s)
                """,
                (
                    scm_uuid,
                    json.dumps(
                        {"created": scm.name, "initial_version": 1}
                    ),
                    actor,
                ),
            )
        conn.commit()
        return scm_uuid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CRUD — read
# ---------------------------------------------------------------------------
def get_scm(
    name: str, version: Optional[int] = None
) -> Optional[SCMRecord]:
    """Fetch one SCM row. Defaults to the latest version when ``version`` is None.

    Returns ``None`` if the name is not found, or in DRY_RUN mode.
    """
    if not _supabase_url_set():
        _stderr(
            f"SUPABASE_DB_URL unset; get_scm({name!r}, version={version}) "
            "-> None (DRY_RUN)"
        )
        return None

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if version is None:
                cur.execute(
                    """
                    SELECT id, name, version, description, graph_json,
                           created_by, created_at, updated_at
                    FROM scms
                    WHERE name = %s
                    ORDER BY version DESC
                    LIMIT 1
                    """,
                    (name,),
                )
            else:
                cur.execute(
                    """
                    SELECT id, name, version, description, graph_json,
                           created_by, created_at, updated_at
                    FROM scms
                    WHERE name = %s AND version = %s
                    """,
                    (name, version),
                )
            row = cur.fetchone()
            if row is None:
                return None
            d = dict(row)
            d["id"] = str(d["id"]) if d.get("id") is not None else None
            return SCMRecord(**d)
    finally:
        conn.close()


def _max_version(cur, name: str) -> int:
    """Return MAX(version) for the given name; 0 if no rows."""
    cur.execute(
        "SELECT COALESCE(MAX(version), 0) FROM scms WHERE name = %s",
        (name,),
    )
    return int(cur.fetchone()[0])


# ---------------------------------------------------------------------------
# CRUD — update
# ---------------------------------------------------------------------------
def update_scm(name: str, scm: SCM, *, actor: str) -> str:
    """Append a new SCM version with the updated payload.

    Does NOT mutate the previous row; the head pointer is the row with
    the highest ``version``. The audit ledger entry carries the
    symmetric-difference diff of edges + nodes between the prior head
    and the new version.
    """
    if not actor or not actor.strip():
        raise ValueError("actor is required for audit lineage")
    new_payload = scm_to_graph_json(scm)

    if not _supabase_url_set():
        sentinel = _dry_run_sentinel(
            {"op": "update", "name": name, "graph_json": new_payload}
        )
        _stderr(
            f"SUPABASE_DB_URL unset; update_scm({name!r}) -> {sentinel}"
        )
        return sentinel

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Fetch prior head
            cur.execute(
                """
                SELECT id, version, graph_json
                FROM scms
                WHERE name = %s
                ORDER BY version DESC
                LIMIT 1
                """,
                (name,),
            )
            prev = cur.fetchone()
            if prev is None:
                raise ValueError(
                    f"SCM {name!r} not found; call create_scm() first"
                )
            prev_payload = prev["graph_json"]
            if isinstance(prev_payload, str):
                prev_payload = json.loads(prev_payload)
            new_version = int(prev["version"]) + 1
            diff = compute_diff(prev_payload, new_payload)

            cur.execute(
                """
                INSERT INTO scms
                    (name, version, description, graph_json, created_by)
                VALUES (%s, %s, %s, %s::jsonb, %s)
                RETURNING id
                """,
                (
                    name,
                    new_version,
                    scm.description,
                    json.dumps(new_payload),
                    actor,
                ),
            )
            new_uuid = str(cur.fetchone()["id"])

            cur.execute(
                """
                INSERT INTO scm_audit_log
                    (scm_id, operation, diff, actor)
                VALUES (%s, 'update', %s::jsonb, %s)
                """,
                (new_uuid, json.dumps(diff), actor),
            )
        conn.commit()
        return new_uuid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CRUD — delete (soft)
# ---------------------------------------------------------------------------
def delete_scm(name: str, *, actor: str, soft: bool = True) -> int:
    """Soft-delete an SCM by appending a tombstone version.

    The tombstone is a new row with ``graph_json = {"_deleted": True}``.
    Audit log records operation='delete'. Returns ``1`` (the count of
    rows newly added, which is always 1 in soft mode).

    Hard delete (``soft=False``) is intentionally NOT implemented in
    Phase 7.2; immutable history is a hard rule. Pass ``soft=False`` to
    raise ``NotImplementedError`` as an explicit guard against accidental
    destructive use.
    """
    if not actor or not actor.strip():
        raise ValueError("actor is required for audit lineage")
    if not soft:
        raise NotImplementedError(
            "Hard delete is not supported in Phase 7.2 — pass soft=True "
            "for tombstone-style deletion."
        )
    tombstone = {"_deleted": True, "scm_spec": {"name": name}}

    if not _supabase_url_set():
        sentinel = _dry_run_sentinel(
            {"op": "delete", "name": name, "graph_json": tombstone}
        )
        _stderr(
            f"SUPABASE_DB_URL unset; delete_scm({name!r}) -> {sentinel} (count=1)"
        )
        return 1

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            new_version = _max_version(cur, name) + 1
            if new_version == 1:
                # Nothing to delete; abort with a clear error
                raise ValueError(
                    f"SCM {name!r} not found; nothing to soft-delete"
                )
            cur.execute(
                """
                INSERT INTO scms
                    (name, version, description, graph_json, created_by)
                VALUES (%s, %s, %s, %s::jsonb, %s)
                RETURNING id
                """,
                (
                    name,
                    new_version,
                    f"soft-delete tombstone (v{new_version})",
                    json.dumps(tombstone),
                    actor,
                ),
            )
            new_uuid = str(cur.fetchone()[0])

            cur.execute(
                """
                INSERT INTO scm_audit_log
                    (scm_id, operation, diff, actor)
                VALUES (%s, 'delete', %s::jsonb, %s)
                """,
                (
                    new_uuid,
                    json.dumps({"soft_delete": True, "tombstone_version": new_version}),
                    actor,
                ),
            )
        conn.commit()
        return 1
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CRUD — revert
# ---------------------------------------------------------------------------
def revert_scm(name: str, target_version: int, *, actor: str) -> str:
    """Revert an SCM head to an earlier version by appending a copy.

    Reads the row at ``(name, target_version)``, then INSERTs that
    payload at ``version = prev_max + 1`` so the head moves forward
    without losing intervening history. Audit ledger records
    operation='revert' with a diff between the prior head and the
    target.
    """
    if not actor or not actor.strip():
        raise ValueError("actor is required for audit lineage")
    if target_version < 1:
        raise ValueError(f"target_version must be >= 1, got {target_version}")

    if not _supabase_url_set():
        sentinel = _dry_run_sentinel(
            {"op": "revert", "name": name, "target_version": target_version}
        )
        _stderr(
            f"SUPABASE_DB_URL unset; revert_scm({name!r}, v={target_version}) "
            f"-> {sentinel}"
        )
        return sentinel

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT graph_json, description
                FROM scms
                WHERE name = %s AND version = %s
                """,
                (name, target_version),
            )
            target = cur.fetchone()
            if target is None:
                raise ValueError(
                    f"SCM {name!r} version {target_version} not found"
                )
            target_payload = target["graph_json"]
            if isinstance(target_payload, str):
                target_payload = json.loads(target_payload)

            cur.execute(
                """
                SELECT version, graph_json
                FROM scms
                WHERE name = %s
                ORDER BY version DESC
                LIMIT 1
                """,
                (name,),
            )
            head = cur.fetchone()
            head_payload = head["graph_json"]
            if isinstance(head_payload, str):
                head_payload = json.loads(head_payload)
            new_version = int(head["version"]) + 1

            diff = compute_diff(head_payload, target_payload)

            cur.execute(
                """
                INSERT INTO scms
                    (name, version, description, graph_json, created_by)
                VALUES (%s, %s, %s, %s::jsonb, %s)
                RETURNING id
                """,
                (
                    name,
                    new_version,
                    f"revert to v{target_version}: "
                    f"{target['description'] or ''}",
                    json.dumps(target_payload),
                    actor,
                ),
            )
            new_uuid = str(cur.fetchone()["id"])

            cur.execute(
                """
                INSERT INTO scm_audit_log
                    (scm_id, operation, diff, actor)
                VALUES (%s, 'revert', %s::jsonb, %s)
                """,
                (
                    new_uuid,
                    json.dumps(
                        {
                            "reverted_to_version": target_version,
                            "new_head_version": new_version,
                            **diff,
                        }
                    ),
                    actor,
                ),
            )
        conn.commit()
        return new_uuid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CRUD — list
# ---------------------------------------------------------------------------
def list_scms() -> list[SCMRecord]:
    """Return the latest version of every named SCM.

    DRY_RUN mode returns an empty list (no DB to read from).
    """
    if not _supabase_url_set():
        _stderr("SUPABASE_DB_URL unset; list_scms() -> [] (DRY_RUN)")
        return []

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Window-function approach: pick the row with max(version) per name.
            cur.execute(
                """
                SELECT id, name, version, description, graph_json,
                       created_by, created_at, updated_at
                FROM (
                    SELECT *,
                           ROW_NUMBER() OVER (PARTITION BY name ORDER BY version DESC) AS rn
                    FROM scms
                ) ranked
                WHERE rn = 1
                ORDER BY name
                """
            )
            rows = cur.fetchall()
        out: list[SCMRecord] = []
        for row in rows:
            d = dict(row)
            d.pop("rn", None)
            d["id"] = str(d["id"]) if d.get("id") is not None else None
            out.append(SCMRecord(**d))
        return out
    finally:
        conn.close()


def list_scm_audit(name: str) -> list[SCMAuditEntry]:
    """Return chronological audit entries for one SCM name.

    DRY_RUN mode returns an empty list.
    """
    if not _supabase_url_set():
        _stderr(
            f"SUPABASE_DB_URL unset; list_scm_audit({name!r}) -> [] (DRY_RUN)"
        )
        return []

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT a.id, a.scm_id, a.operation, a.diff, a.actor, a.occurred_at
                FROM scm_audit_log a
                JOIN scms s ON s.id = a.scm_id
                WHERE s.name = %s
                ORDER BY a.occurred_at ASC
                """,
                (name,),
            )
            rows = cur.fetchall()
        out: list[SCMAuditEntry] = []
        for row in rows:
            d = dict(row)
            d["id"] = str(d["id"]) if d.get("id") is not None else None
            d["scm_id"] = (
                str(d["scm_id"]) if d.get("scm_id") is not None else None
            )
            # Tolerate diff stored as JSON string by older drivers.
            if isinstance(d.get("diff"), str):
                d["diff"] = json.loads(d["diff"])
            if d.get("diff") is None:
                d["diff"] = {}
            out.append(SCMAuditEntry(**d))
        return out
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Re-export for round-trip helpers used by tests + verifier
# ---------------------------------------------------------------------------
__all__ = [
    "SCMRecord",
    "SCMAuditEntry",
    "scm_to_graph_json",
    "graph_json_to_scm",
    "compute_diff",
    "create_scm",
    "get_scm",
    "update_scm",
    "delete_scm",
    "revert_scm",
    "list_scms",
    "list_scm_audit",
]


# Helper retained for tests that want to round-trip a graph-only payload
# (without the scm_spec sub-dict) through build_scm_from_graph.
def _build_scm_from_round_trip(payload: dict[str, Any]) -> SCM:
    """Round-trip via graph_json_to_scm + build_scm_from_graph for parity.

    Internal helper; not exported. Verifies the rebuild path is
    equivalent to the auto-builder when treatment/outcome are already
    in the graph.
    """
    scm = graph_json_to_scm(payload)
    if scm.graph is None:  # pragma: no cover — graph_json_to_scm sets graph
        raise ValueError("graph_json_to_scm returned SCM with no graph")
    rebuilt = build_scm_from_graph(
        scm.graph,
        treatment_name=scm.treatment,
        outcome_name=scm.outcome,
        name=scm.name,
        description=scm.description,
    )
    return rebuilt
