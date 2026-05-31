"""Phase 7.5 Meta - Constitutional Overrides API.

Application surface for the `constitutional_overrides` audit table
(migration 023). Every escape-hatch use of any of the 13 rules MUST go
through ``issue_override`` so the audit ledger captures rule_number,
justification, actor, 24-hour TTL, and wife-notification timestamp.

DRY_RUN fallback: when ``SUPABASE_DB_URL`` is unset, ``issue_override``
returns ``"DRY_RUN:<sha>"`` (no DB write) so unit tests and code-complete
verifiers stay infra-free. Same pattern as
``brain.causal.cross_link.record_causal_estimate_as_evidence``.

Wife notification: the ``notify_wife`` parameter (default True) wires
the call to ``_telegram_notify_wife_stub`` which is a no-op for
Phase 7.5. Phase 7.6 replaces the stub with the real Telegram bot
call; the call signature is stable.

Reference:
    scripts/migrations/023_constitutional_overrides.sql
    docs/PHASE_7_5_ESCAPE_HATCHES.md
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

try:
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]


DEFAULT_TTL_HOURS = 24


# ---------------------------------------------------------------------------
# Pydantic record
# ---------------------------------------------------------------------------
class OverrideRecord(BaseModel):
    """Typed row of the constitutional_overrides table.

    Field constraints mirror the DDL constraints in migration 023.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    id: Optional[str] = None
    rule_number: int = Field(..., ge=1, le=13)
    reason: str = Field(..., min_length=20)
    overridden_by: str = Field(..., min_length=1)
    expires_at: datetime
    created_at: Optional[datetime] = None
    notified_wife_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# DRY_RUN detection
# ---------------------------------------------------------------------------
def _dsn() -> Optional[str]:
    return os.environ.get("SUPABASE_DB_URL")


def _is_dry_run() -> bool:
    return not _dsn()


# ---------------------------------------------------------------------------
# Telegram notification - Phase 7.5 stub (real wire-up in Phase 7.6)
# ---------------------------------------------------------------------------
def _telegram_notify_wife_stub(rec: OverrideRecord) -> Optional[datetime]:
    """Phase 7.5 stub. Returns the timestamp that WOULD be written.

    Phase 7.6 frontend will replace this with the live Telegram bot
    call (jincharadzeshako@gmail.com chat). The signature is stable:
    same input, same return type.
    """
    # No-op for Phase 7.5. Returning UTC now lets the caller still
    # populate notified_wife_at with a sensible timestamp.
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def issue_override(
    *,
    rule_number: int,
    reason: str,
    overridden_by: str,
    ttl_hours: int = DEFAULT_TTL_HOURS,
    notify_wife: bool = True,
) -> str:
    """Issue a constitutional override; INSERT into the audit ledger.

    Args:
        rule_number: 1..13. ValidationError if out of range.
        reason: ≥20 chars. ValidationError if shorter.
        overridden_by: actor identifier (typically "shako").
        ttl_hours: hours until auto-expiry (default 24).
        notify_wife: if True, call the (stubbed) Telegram notifier.

    Returns:
        UUID string of the inserted row when DSN is set; else
        ``"DRY_RUN:<sha>"`` where ``sha`` is a deterministic hash of
        the (rule_number, reason, overridden_by, ttl) tuple.

    Raises:
        pydantic.ValidationError: rule_number out of [1..13], reason too short.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    rec = OverrideRecord(
        rule_number=rule_number,
        reason=reason,
        overridden_by=overridden_by,
        expires_at=expires_at,
    )

    notified_at: Optional[datetime] = None
    if notify_wife:
        notified_at = _telegram_notify_wife_stub(rec)
    rec = rec.model_copy(update={"notified_wife_at": notified_at})

    if _is_dry_run():
        seed = (
            f"{rec.rule_number}|{rec.reason}|{rec.overridden_by}|{ttl_hours}"
        )
        sha = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
        return f"DRY_RUN:{sha}"

    if psycopg2 is None:  # pragma: no cover
        print(
            "[overrides] psycopg2 not importable; falling back to DRY_RUN",
            file=sys.stderr,
        )
        seed = (
            f"{rec.rule_number}|{rec.reason}|{rec.overridden_by}|{ttl_hours}"
        )
        sha = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
        return f"DRY_RUN:{sha}"

    conn = psycopg2.connect(_dsn(), sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO constitutional_overrides
                  (rule_number, reason, overridden_by, expires_at,
                   notified_wife_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    rec.rule_number,
                    rec.reason,
                    rec.overridden_by,
                    rec.expires_at,
                    rec.notified_wife_at,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return str(row[0]) if row else "INSERT_FAILED"
    finally:
        conn.close()


def is_rule_currently_overridden(rule_number: int) -> bool:
    """Return True iff a non-expired override row exists for `rule_number`."""
    if not (1 <= rule_number <= 13):
        raise ValueError(
            f"rule_number must be in [1..13]; got {rule_number}"
        )
    if _is_dry_run():
        return False
    if psycopg2 is None:  # pragma: no cover
        return False

    conn = psycopg2.connect(_dsn(), sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                  SELECT 1 FROM constitutional_overrides
                  WHERE rule_number = %s AND expires_at > NOW()
                )
                """,
                (rule_number,),
            )
            row = cur.fetchone()
            return bool(row[0]) if row else False
    finally:
        conn.close()


def list_active_overrides() -> list[OverrideRecord]:
    """Return non-expired override rows (rule_number, expires_at, reason, etc.)."""
    if _is_dry_run():
        return []
    if psycopg2 is None:  # pragma: no cover
        return []

    conn = psycopg2.connect(_dsn(), sslmode="require")
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, rule_number, reason, overridden_by,
                       expires_at, created_at, notified_wife_at
                FROM constitutional_overrides
                WHERE expires_at > NOW()
                ORDER BY created_at DESC
                """
            )
            rows = cur.fetchall() or []
        return [OverrideRecord(**dict(r, id=str(r["id"]))) for r in rows]
    finally:
        conn.close()


__all__ = [
    "DEFAULT_TTL_HOURS",
    "OverrideRecord",
    "issue_override",
    "is_rule_currently_overridden",
    "list_active_overrides",
]
