"""
apply_batch.py — Phase 5 Day 4 batch executor with all-or-nothing semantics.

Wraps N ProposedAction calls in a single Postgres transaction:

  - If every apply succeeds, commit once at the end. All target writes
    AND all manager_actions rows land together.
  - If any apply raises, rollback everything. Half-applied state is
    never persisted.

Public surface
--------------
    apply_many(actions, *, manager_user_id) -> BatchResult
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import psycopg2

from scripts.ledger import load_env
from scripts.manager.routing._shared import ProposedAction
from scripts.manager.routing.apply_action import (
    AppliedActionResult,
    _apply_with_cursor,
)


@dataclass
class BatchResult:
    results: list[AppliedActionResult] = field(default_factory=list)
    committed: bool = False
    error: str | None = None


def apply_many(actions: list[ProposedAction], *, manager_user_id: str) -> BatchResult:
    """Apply N actions atomically. Returns a BatchResult with per-action ids."""
    out = BatchResult()
    if not actions:
        return out

    load_env()
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        with conn.cursor() as cur:
            for a in actions:
                result = _apply_with_cursor(a, cur, manager_user_id=manager_user_id)
                out.results.append(result)
        conn.commit()
        out.committed = True
    except Exception as e:
        conn.rollback()
        out.error = f"{type(e).__name__}: {e}"
        out.results = []
        out.committed = False
    finally:
        conn.close()
    return out


__all__ = ["apply_many", "BatchResult"]
