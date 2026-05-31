"""Phase 7.3 Layer C Day 11 — Simulation Studio CRUD persistence.

Reads / writes the three migration-019 tables (``scenarios``,
``simulation_runs``, ``simulation_comparisons``) via sync ``psycopg2``,
mirroring the Phase 7.2 ``brain.causal.scm_persistence`` convention:

  * env loaded via ``scripts.ledger.load_env``
  * per-call short-lived connections (no module-level pool)
  * service-role DSN from ``os.environ["SUPABASE_DB_URL"]``,
    ``sslmode="require"``

Idempotency model:

    ``scenarios.scenario_hash`` is the UNIQUE idempotency key. Saving a
    Scenario whose hash already exists returns the existing row id
    (no duplicate INSERT). ``simulation_runs`` and
    ``simulation_comparisons`` are append-only — each Monte Carlo or
    TVB rerun gets its own row.

Code-complete-without-infra contract (mirrors
``brain/causal/scm_persistence.py``): every public CRUD function checks
``SUPABASE_DB_URL``; when unset it returns a deterministic
``"DRY_RUN:<sha256>"`` sentinel and logs to stderr instead of touching
the DB. Unit tests run end-to-end without Supabase.

Hard rule: scenarios are **user input**, not audit data. ``delete_scenario``
performs a HARD DELETE (and cascades to runs + comparisons via the
``ON DELETE CASCADE`` FK in migration 019). This deviates from the
SCM persistence design where ``delete_scm(soft=False)`` raises — the
Studio UX needs hard delete and audit lineage lives on the
``simulation_runs.summary_json`` payload + ``completed_at`` rather than
the scenario row itself.

Reference:
    - scripts/migrations/019_sim_tables.sql (schema contract)
    - brain/causal/scm_persistence.py (DRY_RUN-when-DSN-unset pattern)
    - brain/sim/scenario.py (Scenario / Intervention / compute_scenario_hash)
    - brain/sim/aggregator.py (ScenarioSummary)
    - brain/sim/compare.py (ScenarioComparison)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from brain.sim.aggregator import ScenarioSummary
from brain.sim.compare import ScenarioComparison
from brain.sim.scenario import (
    Intervention,
    Scenario,
    compute_scenario_hash,
)


# ---------------------------------------------------------------------------
# Lazy psycopg2 import (matches brain/causal/scm_persistence.py)
# ---------------------------------------------------------------------------
try:
    import psycopg2
    import psycopg2.extras
except Exception:  # pragma: no cover — keeps module importable if psycopg2 missing
    psycopg2 = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Env loader fallback (mirrors brain/causal/scm_persistence.py)
# ---------------------------------------------------------------------------
try:
    from scripts.ledger import load_env  # type: ignore
except Exception:  # pragma: no cover

    def load_env() -> None:  # noqa: D401
        """No-op fallback when scripts.ledger is not on sys.path."""
        return None


# ---------------------------------------------------------------------------
# Allowed engine values (matches migration 019 CHECK)
# ---------------------------------------------------------------------------
ALLOWED_ENGINES = frozenset({"monte_carlo", "tvb", "combined"})
EngineLiteral = Literal["monte_carlo", "tvb", "combined"]


# ---------------------------------------------------------------------------
# Pydantic models — match the migration-019 schema
# ---------------------------------------------------------------------------
class ScenarioRecord(BaseModel):
    """One row of ``scenarios``. Matches migration 019 §Part 1."""

    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None  # UUID
    name: str = Field(..., min_length=1)
    scenario_json: dict[str, Any]
    scenario_hash: str = Field(..., min_length=64, max_length=64)
    created_by: str = Field(..., min_length=1)
    created_at: Optional[datetime] = None


class SimulationRunRecord(BaseModel):
    """One row of ``simulation_runs``. Matches migration 019 §Part 2."""

    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None  # UUID
    scenario_id: Optional[str] = None  # UUID (None in DRY_RUN)
    engine: EngineLiteral
    n_samples: Optional[int] = None
    duration_ms_sim: Optional[int] = None
    elapsed_seconds: Optional[float] = Field(default=None, ge=0.0)
    summary_json: dict[str, Any]
    completed_at: Optional[datetime] = None


class ScenarioComparisonRecord(BaseModel):
    """One row of ``simulation_comparisons``. Matches migration 019 §Part 3."""

    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None  # UUID
    scenario_a_id: Optional[str] = None  # UUID (None in DRY_RUN)
    scenario_b_id: Optional[str] = None  # UUID
    delta_json: dict[str, Any]
    p_a_better_json: dict[str, Any]
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------
def _get_conn():
    """Return a service-role psycopg2 connection. Raise if DSN missing."""
    if psycopg2 is None:
        raise RuntimeError(
            "psycopg2 is not installed in the active venv; "
            "brain.sim.persistence requires it for DB-mode operation."
        )
    load_env()
    dsn = os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError(
            "SUPABASE_DB_URL is not set. brain.sim.persistence requires "
            "a service-role Postgres connection string."
        )
    return psycopg2.connect(dsn, sslmode="require")


def _supabase_url_set() -> bool:
    """True iff ``SUPABASE_DB_URL`` is set in the environment."""
    load_env()
    return bool(os.environ.get("SUPABASE_DB_URL"))


# ---------------------------------------------------------------------------
# Scenario <-> JSON round-trip helpers
# ---------------------------------------------------------------------------
def scenario_to_json(scenario: Scenario) -> dict[str, Any]:
    """Serialise a :class:`~brain.sim.scenario.Scenario` to JSON-safe dict.

    Uses Pydantic ``model_dump`` so the payload mirrors the canonical
    schema enforced by the round-trip target ``json_to_scenario``. All
    nested ``Intervention`` objects flatten to dicts; ``effect_per_dim``
    stays as dict[str, float].
    """
    return scenario.model_dump()


def json_to_scenario(payload: dict[str, Any]) -> Scenario:
    """Round-trip the JSON payload back into a :class:`Scenario` instance.

    Inverse of :func:`scenario_to_json`. Pydantic re-validates every
    field (name, interventions, horizon_days, n_samples, outcomes).

    Raises:
        ValueError: if ``payload`` is not a dict.
        pydantic.ValidationError: if the payload violates the Scenario
            schema (unknown outcome, missing dose_mg_kg on a drug
            intervention, etc.).
    """
    if not isinstance(payload, dict):
        raise ValueError(
            f"payload must be a dict, got {type(payload).__name__}"
        )
    return Scenario.model_validate(payload)


# ---------------------------------------------------------------------------
# DRY_RUN sentinel (mirrors brain/causal/scm_persistence.py)
# ---------------------------------------------------------------------------
def _dry_run_sentinel(payload: dict[str, Any]) -> str:
    """Deterministic ``"DRY_RUN:<sha256_hex>"`` for the given payload."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return f"DRY_RUN:{digest}"


def _stderr(msg: str) -> None:
    print(f"[sim.persistence] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CRUD — scenarios.save
# ---------------------------------------------------------------------------
def save_scenario(
    scenario: Scenario,
    *,
    created_by: str = "system",
) -> str:
    """Insert a scenario (or return the existing row id on hash collision).

    Args:
        scenario: the Scenario to persist.
        created_by: identifier of the user / agent creating the row.

    Returns:
        * Real scenarios.id UUID (string) when ``SUPABASE_DB_URL`` is set
          and the INSERT succeeds. If a row with the same
          ``scenario_hash`` already exists, returns the existing id
          (idempotent dedup).
        * ``"DRY_RUN:<sha256>"`` sentinel otherwise.
    """
    if not created_by or not created_by.strip():
        raise ValueError("created_by must be a non-empty string")
    payload = scenario_to_json(scenario)
    scenario_hash = compute_scenario_hash(scenario)

    if not _supabase_url_set():
        sentinel = _dry_run_sentinel(
            {
                "op": "save_scenario",
                "name": scenario.name,
                "scenario_hash": scenario_hash,
                "scenario_json": payload,
            }
        )
        _stderr(
            f"SUPABASE_DB_URL unset; save_scenario({scenario.name!r}) -> {sentinel}"
        )
        return sentinel

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # Idempotent INSERT via ON CONFLICT (scenario_hash) DO UPDATE
            # so the RETURNING clause always emits a row.
            cur.execute(
                """
                INSERT INTO scenarios
                    (name, scenario_json, scenario_hash, created_by)
                VALUES (%s, %s::jsonb, %s, %s)
                ON CONFLICT (scenario_hash) DO UPDATE
                    SET name = EXCLUDED.name
                RETURNING id
                """,
                (
                    scenario.name,
                    json.dumps(payload),
                    scenario_hash,
                    created_by,
                ),
            )
            row = cur.fetchone()
            scenario_uuid = str(row[0])
        conn.commit()
        return scenario_uuid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CRUD — scenarios.read
# ---------------------------------------------------------------------------
def get_scenario(name: str) -> Optional[ScenarioRecord]:
    """Fetch one scenario row by name. Returns None if not found / DRY_RUN."""
    if not _supabase_url_set():
        _stderr(
            f"SUPABASE_DB_URL unset; get_scenario({name!r}) -> None (DRY_RUN)"
        )
        return None

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, name, scenario_json, scenario_hash,
                       created_by, created_at
                FROM scenarios
                WHERE name = %s
                """,
                (name,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            d = dict(row)
            d["id"] = str(d["id"]) if d.get("id") is not None else None
            if isinstance(d.get("scenario_json"), str):
                d["scenario_json"] = json.loads(d["scenario_json"])
            return ScenarioRecord(**d)
    finally:
        conn.close()


def get_scenario_by_hash(scenario_hash: str) -> Optional[ScenarioRecord]:
    """Fetch one scenario row by ``scenario_hash``. DRY_RUN -> None."""
    if not _supabase_url_set():
        _stderr(
            f"SUPABASE_DB_URL unset; get_scenario_by_hash({scenario_hash[:16]}...) "
            "-> None (DRY_RUN)"
        )
        return None

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, name, scenario_json, scenario_hash,
                       created_by, created_at
                FROM scenarios
                WHERE scenario_hash = %s
                """,
                (scenario_hash,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            d = dict(row)
            d["id"] = str(d["id"]) if d.get("id") is not None else None
            if isinstance(d.get("scenario_json"), str):
                d["scenario_json"] = json.loads(d["scenario_json"])
            return ScenarioRecord(**d)
    finally:
        conn.close()


def list_scenarios() -> list[ScenarioRecord]:
    """Return every scenario row, ordered by name. DRY_RUN -> [] empty list."""
    if not _supabase_url_set():
        _stderr("SUPABASE_DB_URL unset; list_scenarios() -> [] (DRY_RUN)")
        return []

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, name, scenario_json, scenario_hash,
                       created_by, created_at
                FROM scenarios
                ORDER BY name
                """
            )
            rows = cur.fetchall()
        out: list[ScenarioRecord] = []
        for row in rows:
            d = dict(row)
            d["id"] = str(d["id"]) if d.get("id") is not None else None
            if isinstance(d.get("scenario_json"), str):
                d["scenario_json"] = json.loads(d["scenario_json"])
            out.append(ScenarioRecord(**d))
        return out
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CRUD — scenarios.delete (HARD delete)
# ---------------------------------------------------------------------------
def delete_scenario(name: str) -> int:
    """Hard-delete a scenario by name. Cascades to runs + comparisons.

    Scenarios are user input (not audit data) — the Studio UX needs hard
    delete. Migration 019's ON DELETE CASCADE foreign keys reap dependent
    ``simulation_runs`` and ``simulation_comparisons`` rows.

    Returns:
        Number of rows deleted (1 on success, 0 if not found).
        DRY_RUN mode always returns 0 (nothing to delete in-memory).
    """
    if not _supabase_url_set():
        _stderr(
            f"SUPABASE_DB_URL unset; delete_scenario({name!r}) -> 0 (DRY_RUN)"
        )
        return 0

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM scenarios WHERE name = %s", (name,))
            count = cur.rowcount
        conn.commit()
        return int(count)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CRUD — simulation_runs.save
# ---------------------------------------------------------------------------
def save_simulation_run(
    *,
    scenario_id: str,
    engine: str,
    n_samples: Optional[int],
    duration_ms_sim: Optional[int],
    elapsed_seconds: Optional[float],
    summary: ScenarioSummary,
) -> str:
    """Append one Monte Carlo / TVB / combined run record.

    Args:
        scenario_id: UUID of the parent scenarios row, OR a
            ``"DRY_RUN:<hash>"`` sentinel returned by
            :func:`save_scenario` when no DB is configured.
        engine: one of ``{"monte_carlo", "tvb", "combined"}``.
        n_samples: Monte Carlo sample count (None for TVB).
        duration_ms_sim: TVB simulated duration in milliseconds
            (None for Monte Carlo).
        elapsed_seconds: wall-clock elapsed seconds (>= 0).
        summary: aggregated ScenarioSummary for the run.

    Returns:
        Real simulation_runs.id UUID (string) when ``SUPABASE_DB_URL`` is
        set; otherwise ``"DRY_RUN:<sha256>"`` sentinel.

    Raises:
        ValueError: when ``engine`` is not in ``ALLOWED_ENGINES`` or
            ``elapsed_seconds`` is negative.
    """
    if engine not in ALLOWED_ENGINES:
        raise ValueError(
            f"engine must be one of {sorted(ALLOWED_ENGINES)}, got {engine!r}"
        )
    if elapsed_seconds is not None and elapsed_seconds < 0:
        raise ValueError(
            f"elapsed_seconds must be >= 0 (CHECK constraint), got {elapsed_seconds}"
        )
    summary_payload = summary.model_dump()

    if not _supabase_url_set():
        sentinel = _dry_run_sentinel(
            {
                "op": "save_simulation_run",
                "scenario_id": scenario_id,
                "engine": engine,
                "n_samples": n_samples,
                "duration_ms_sim": duration_ms_sim,
                "elapsed_seconds": elapsed_seconds,
                "summary": summary_payload,
            }
        )
        _stderr(
            f"SUPABASE_DB_URL unset; save_simulation_run(scenario_id={scenario_id!r}) "
            f"-> {sentinel}"
        )
        return sentinel

    if scenario_id.startswith("DRY_RUN:"):
        raise ValueError(
            "save_simulation_run requires a real scenario_id UUID, "
            f"got DRY_RUN sentinel: {scenario_id}"
        )

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO simulation_runs
                    (scenario_id, engine, n_samples, duration_ms_sim,
                     elapsed_seconds, summary_json)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id
                """,
                (
                    scenario_id,
                    engine,
                    n_samples,
                    duration_ms_sim,
                    elapsed_seconds,
                    json.dumps(summary_payload),
                ),
            )
            run_uuid = str(cur.fetchone()[0])
        conn.commit()
        return run_uuid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CRUD — simulation_comparisons.save
# ---------------------------------------------------------------------------
def save_scenario_comparison(
    *,
    scenario_a_id: str,
    scenario_b_id: str,
    comparison: ScenarioComparison,
) -> str:
    """Append one (A, B) pairwise comparison record.

    ``delta_json`` carries the list of OutcomeDelta (mean_delta +
    interpretation per (outcome, day)); ``p_a_better_json`` carries the
    list of p_a_better values keyed the same way.

    Args:
        scenario_a_id: scenarios.id UUID for side A, OR a DRY_RUN sentinel.
        scenario_b_id: scenarios.id UUID for side B, OR a DRY_RUN sentinel.
        comparison: ScenarioComparison object.

    Returns:
        Real simulation_comparisons.id UUID (string) when
        ``SUPABASE_DB_URL`` is set; otherwise ``"DRY_RUN:<sha256>"``.
    """
    deltas = comparison.deltas
    delta_payload = {
        "scenario_a_hash": comparison.scenario_a_hash,
        "scenario_b_hash": comparison.scenario_b_hash,
        "n_samples_a": comparison.n_samples_a,
        "n_samples_b": comparison.n_samples_b,
        "deltas": [
            {
                "dim_name": d.dim_name,
                "day": d.day,
                "mean_delta": d.mean_delta,
                "interpretation": d.interpretation,
            }
            for d in deltas
        ],
    }
    p_a_better_payload = {
        "scenario_a_hash": comparison.scenario_a_hash,
        "scenario_b_hash": comparison.scenario_b_hash,
        "p_a_better": [
            {
                "dim_name": d.dim_name,
                "day": d.day,
                "p_a_better": d.p_a_better,
            }
            for d in deltas
        ],
    }

    if not _supabase_url_set():
        sentinel = _dry_run_sentinel(
            {
                "op": "save_scenario_comparison",
                "scenario_a_id": scenario_a_id,
                "scenario_b_id": scenario_b_id,
                "delta_json": delta_payload,
                "p_a_better_json": p_a_better_payload,
            }
        )
        _stderr(
            f"SUPABASE_DB_URL unset; save_scenario_comparison "
            f"({scenario_a_id!r}, {scenario_b_id!r}) -> {sentinel}"
        )
        return sentinel

    if scenario_a_id.startswith("DRY_RUN:") or scenario_b_id.startswith(
        "DRY_RUN:"
    ):
        raise ValueError(
            "save_scenario_comparison requires real scenario_id UUIDs, "
            f"got DRY_RUN sentinels: a={scenario_a_id}, b={scenario_b_id}"
        )

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO simulation_comparisons
                    (scenario_a_id, scenario_b_id, delta_json, p_a_better_json)
                VALUES (%s, %s, %s::jsonb, %s::jsonb)
                RETURNING id
                """,
                (
                    scenario_a_id,
                    scenario_b_id,
                    json.dumps(delta_payload),
                    json.dumps(p_a_better_payload),
                ),
            )
            cmp_uuid = str(cur.fetchone()[0])
        conn.commit()
        return cmp_uuid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


__all__ = [
    "ALLOWED_ENGINES",
    "EngineLiteral",
    "ScenarioRecord",
    "SimulationRunRecord",
    "ScenarioComparisonRecord",
    "scenario_to_json",
    "json_to_scenario",
    "save_scenario",
    "get_scenario",
    "get_scenario_by_hash",
    "list_scenarios",
    "delete_scenario",
    "save_simulation_run",
    "save_scenario_comparison",
]
