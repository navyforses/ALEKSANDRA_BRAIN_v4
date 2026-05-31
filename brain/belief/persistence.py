"""
brain/belief/persistence.py — Phase 7.0 Day 5a Postgres adapter.

Persists Bayesian update results (`belief_traces`) and incoming evidence
(`belief_evidence`), plus reads `belief_dimensions` definitions, against
the Supabase Postgres backend that v6 migrations already secured under
RLS (service-role full access; authenticated SELECT).

Conventions intentionally mirror Phase 5 (`scripts/manager/activity/log_action.py`):

  - sync `psycopg2` (matches every other write path in the repo)
  - connection string from `os.environ["SUPABASE_DB_URL"]`, `sslmode="require"`
  - env loaded via `scripts.ledger.load_env()`
  - per-call short-lived connections (no module-level pool — Supabase pgbouncer
    handles pooling upstream; matches `log_action.py` / `routing/apply_action.py`)

Hard rules (from `.claude/agents/v7-bayes.md` + Phase 7.0 spec):

  1. `evidence_hash` is the deterministic SHA-256 of
     `{dimension_id, source, source_ref, value}` with `json.dumps(sort_keys=True)`
     so duplicate evidence collapses to a single row regardless of dict order.
  2. Idempotency on write_evidence: `ON CONFLICT (evidence_hash) DO UPDATE SET
     ingested_at = EXCLUDED.ingested_at RETURNING id` — always returns the
     row id (existing or new) without inserting a duplicate.
  3. Idempotency on write_trace: `ON CONFLICT (dimension_id, evidence_id) DO
     UPDATE SET created_at = EXCLUDED.created_at RETURNING id`.
  4. Citation REQUIRED on every BeliefDimension write — `upsert_dimension`
     refuses an empty citation with `ValueError("citation required")`.
  5. No PHI in code — values flow through `BeliefEvidence.value` (JSONB),
     never hardcoded.

The adapter assumes `scripts/migrations/016_belief_tables.sql` (a SQL
migration distinct from the pre-existing `016_restore_hypotheses.py`
Phase 6.1 data-restore script) has been applied. Until that migration
lands on Supabase, every function will raise `psycopg2.errors.
UndefinedTable`. Tests below stay schema-agnostic by mocking the
connection.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Optional

import psycopg2
import psycopg2.extras
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Env loader — same convention as scripts/ledger.py / scripts/manager/*
# ---------------------------------------------------------------------------
try:
    from scripts.ledger import load_env  # type: ignore
except Exception:  # pragma: no cover — keeps the module importable in v7 venv

    def load_env() -> None:  # noqa: D401
        """No-op fallback when scripts.ledger isn't on sys.path."""
        return None


# ---------------------------------------------------------------------------
# Pydantic models (mirror the SQL schema v7-devops will create)
# ---------------------------------------------------------------------------
ALLOWED_DISTRIBUTIONS = frozenset(
    {
        "beta",
        "normal",
        "poisson",
        "categorical",
        "gamma",
        "bernoulli",
        "vector",
        "exp_decay",
    }
)

ALLOWED_EVIDENCE_SOURCES = frozenset(
    {
        "mri_report",
        "voice_note",
        "research_paper",
        "manual",
        "tvb_sim",
        "causal_estimate",
    }
)


class BeliefDimension(BaseModel):
    """One row of `belief_dimensions`. Matches Phase 7.0 §3 13-D table."""

    model_config = ConfigDict(extra="forbid")

    id: Optional[int] = None
    name: str
    distribution: str  # 'beta'|'normal'|'poisson'|'categorical'|'gamma'|'bernoulli'|'vector'|'exp_decay'
    prior_params: dict[str, Any]
    units: Optional[str] = None
    valid_min: Optional[float] = None
    valid_max: Optional[float] = None
    citation: str = Field(
        ..., min_length=1
    )  # PubMed/DOI/github URL — Phase 7.0 hard rule

    @field_validator("distribution")
    @classmethod
    def _dist_allowed(cls, v: str) -> str:
        if v not in ALLOWED_DISTRIBUTIONS:
            raise ValueError(
                f"distribution must be one of {sorted(ALLOWED_DISTRIBUTIONS)}, got {v!r}"
            )
        return v


class BeliefEvidence(BaseModel):
    """One row of `belief_evidence`. Idempotent on `evidence_hash`."""

    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None  # UUID
    dimension_id: int
    source: str  # 'mri_report' | 'voice_note' | 'research_paper' | 'manual' | 'tvb_sim' | 'causal_estimate'
    source_ref: str
    value: dict[str, Any]  # JSONB
    evidence_hash: str  # SHA-256 hex of (dimension_id, source, source_ref, value)
    confidence: float = Field(..., ge=0.0, le=1.0)
    observed_at: datetime
    ingested_at: Optional[datetime] = None

    @field_validator("source")
    @classmethod
    def _source_allowed(cls, v: str) -> str:
        if v not in ALLOWED_EVIDENCE_SOURCES:
            raise ValueError(
                f"source must be one of {sorted(ALLOWED_EVIDENCE_SOURCES)}, got {v!r}"
            )
        return v


class BeliefTrace(BaseModel):
    """One row of `belief_traces`. Idempotent on (dimension_id, evidence_id)."""

    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None
    dimension_id: int
    evidence_id: str
    posterior_mean: float
    posterior_sd: float
    hdi_3: float
    hdi_97: float
    n_samples: int
    rhat: float
    ess_bulk: float
    arviz_summary: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------
def _get_conn():
    """Return a service-role psycopg2 connection. Raise if env missing."""
    load_env()
    dsn = os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError(
            "SUPABASE_DB_URL is not set. brain/belief/persistence.py requires a "
            "service-role Postgres connection string (see scripts/manager/activity/"
            "log_action.py for the canonical pattern)."
        )
    return psycopg2.connect(dsn, sslmode="require")


# ---------------------------------------------------------------------------
# Hashing — deterministic, locale-independent
# ---------------------------------------------------------------------------
def compute_evidence_hash(
    dimension_id: int,
    source: str,
    source_ref: str,
    value: dict[str, Any],
) -> str:
    """SHA-256 hex of the canonical JSON form of (dim, source, ref, value)."""
    payload = json.dumps(
        {
            "dimension_id": dimension_id,
            "source": source,
            "source_ref": source_ref,
            "value": value,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,  # tolerate datetime / numpy scalars in `value`
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------
def list_dimensions() -> list[BeliefDimension]:
    """Return every row of `belief_dimensions`."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, name, distribution, prior_params,
                       units, valid_min, valid_max, citation
                FROM belief_dimensions
                ORDER BY id
                """
            )
            return [BeliefDimension(**dict(row)) for row in cur.fetchall()]
    finally:
        conn.close()


def get_dimension(name: str) -> Optional[BeliefDimension]:
    """Look up one dimension by its unique `name`."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, name, distribution, prior_params,
                       units, valid_min, valid_max, citation
                FROM belief_dimensions
                WHERE name = %s
                """,
                (name,),
            )
            row = cur.fetchone()
            return BeliefDimension(**dict(row)) if row else None
    finally:
        conn.close()


# Phase 7.0 Day 13-14 — id-keyed lookup needed by update.py.
# `get_dimension` (above) stays untouched (it keys by `name` — Day 5 contract).
get_dimension_by_name = get_dimension  # alias for update.py import-clarity


def get_dimension_by_id(dim_id: int) -> Optional[BeliefDimension]:
    """Look up one dimension by primary key. Mirrors `get_dimension(name)`."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, name, distribution, prior_params,
                       units, valid_min, valid_max, citation
                FROM belief_dimensions
                WHERE id = %s
                """,
                (dim_id,),
            )
            row = cur.fetchone()
            return BeliefDimension(**dict(row)) if row else None
    finally:
        conn.close()


def upsert_dimension(dim: BeliefDimension) -> int:
    """Insert or update a dimension by `name`. Returns the row id.

    Refuses to write if `citation` is empty — Phase 7.0 prior-research rule.
    """
    if not dim.citation or not dim.citation.strip():
        raise ValueError("citation required (every prior must carry a PubMed/DOI/URL)")
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO belief_dimensions
                    (name, distribution, prior_params,
                     units, valid_min, valid_max, citation)
                VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    distribution = EXCLUDED.distribution,
                    prior_params = EXCLUDED.prior_params,
                    units = EXCLUDED.units,
                    valid_min = EXCLUDED.valid_min,
                    valid_max = EXCLUDED.valid_max,
                    citation = EXCLUDED.citation
                RETURNING id
                """,
                (
                    dim.name,
                    dim.distribution,
                    json.dumps(dim.prior_params),
                    dim.units,
                    dim.valid_min,
                    dim.valid_max,
                    dim.citation,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return int(row[0])
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------
def write_evidence(ev: BeliefEvidence) -> str:
    """Insert a `belief_evidence` row. Idempotent on `evidence_hash`.

    Returns the row UUID (string) whether the row was new or existing.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO belief_evidence
                    (dimension_id, source, source_ref, value,
                     evidence_hash, confidence, observed_at)
                VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s)
                ON CONFLICT (evidence_hash) DO UPDATE SET
                    ingested_at = belief_evidence.ingested_at
                RETURNING id
                """,
                (
                    ev.dimension_id,
                    ev.source,
                    ev.source_ref,
                    json.dumps(ev.value, default=str),
                    ev.evidence_hash,
                    ev.confidence,
                    ev.observed_at,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return str(row[0])
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_evidence_by_hash(evidence_hash: str) -> Optional[BeliefEvidence]:
    """Look up evidence by its deterministic hash (idempotency probe)."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, dimension_id, source, source_ref, value,
                       evidence_hash, confidence, observed_at, ingested_at
                FROM belief_evidence
                WHERE evidence_hash = %s
                """,
                (evidence_hash,),
            )
            row = cur.fetchone()
            if not row:
                return None
            d = dict(row)
            d["id"] = str(d["id"])
            return BeliefEvidence(**d)
    finally:
        conn.close()


def list_evidence(
    dimension_id: Optional[int] = None,
    limit: int = 100,
) -> list[BeliefEvidence]:
    """List evidence rows, optionally filtered by `dimension_id`, newest first."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if dimension_id is None:
                cur.execute(
                    """
                    SELECT id, dimension_id, source, source_ref, value,
                           evidence_hash, confidence, observed_at, ingested_at
                    FROM belief_evidence
                    ORDER BY observed_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            else:
                cur.execute(
                    """
                    SELECT id, dimension_id, source, source_ref, value,
                           evidence_hash, confidence, observed_at, ingested_at
                    FROM belief_evidence
                    WHERE dimension_id = %s
                    ORDER BY observed_at DESC
                    LIMIT %s
                    """,
                    (dimension_id, limit),
                )
            out = []
            for row in cur.fetchall():
                d = dict(row)
                d["id"] = str(d["id"])
                out.append(BeliefEvidence(**d))
            return out
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Traces
# ---------------------------------------------------------------------------
def write_trace(trace: BeliefTrace) -> str:
    """Insert a `belief_traces` row. Idempotent on (dimension_id, evidence_id).

    Returns the row UUID (string) whether new or existing.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO belief_traces
                    (dimension_id, evidence_id,
                     posterior_mean, posterior_sd, hdi_3, hdi_97,
                     n_samples, rhat, ess_bulk, arviz_summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (dimension_id, evidence_id) DO UPDATE SET
                    posterior_mean = EXCLUDED.posterior_mean,
                    posterior_sd = EXCLUDED.posterior_sd,
                    hdi_3 = EXCLUDED.hdi_3,
                    hdi_97 = EXCLUDED.hdi_97,
                    n_samples = EXCLUDED.n_samples,
                    rhat = EXCLUDED.rhat,
                    ess_bulk = EXCLUDED.ess_bulk,
                    arviz_summary = EXCLUDED.arviz_summary
                RETURNING id
                """,
                (
                    trace.dimension_id,
                    trace.evidence_id,
                    trace.posterior_mean,
                    trace.posterior_sd,
                    trace.hdi_3,
                    trace.hdi_97,
                    trace.n_samples,
                    trace.rhat,
                    trace.ess_bulk,
                    json.dumps(trace.arviz_summary) if trace.arviz_summary else None,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return str(row[0])
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_traces(
    dimension_id: Optional[int] = None,
    since: Optional[datetime] = None,
    limit: int = 100,
) -> list[BeliefTrace]:
    """List trace rows, optionally filtered by dimension and/or `since` cutoff."""
    where = []
    params: list[Any] = []
    if dimension_id is not None:
        where.append("dimension_id = %s")
        params.append(dimension_id)
    if since is not None:
        where.append("created_at >= %s")
        params.append(since)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)
    sql = (
        "SELECT id, dimension_id, evidence_id, posterior_mean, posterior_sd, "
        "hdi_3, hdi_97, n_samples, rhat, ess_bulk, arviz_summary, created_at "
        "FROM belief_traces" + where_sql + " ORDER BY created_at DESC LIMIT %s"
    )
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, tuple(params))
            out = []
            for row in cur.fetchall():
                d = dict(row)
                d["id"] = str(d["id"])
                d["evidence_id"] = str(d["evidence_id"])
                out.append(BeliefTrace(**d))
            return out
    finally:
        conn.close()


def latest_trace(dimension_id: int) -> Optional[BeliefTrace]:
    """Return the most recent trace for a dimension (or None)."""
    rows = list_traces(dimension_id=dimension_id, limit=1)
    return rows[0] if rows else None


__all__ = [
    "BeliefDimension",
    "BeliefEvidence",
    "BeliefTrace",
    "compute_evidence_hash",
    "list_dimensions",
    "get_dimension",
    "get_dimension_by_name",
    "get_dimension_by_id",
    "upsert_dimension",
    "write_evidence",
    "get_evidence_by_hash",
    "list_evidence",
    "write_trace",
    "list_traces",
    "latest_trace",
]
