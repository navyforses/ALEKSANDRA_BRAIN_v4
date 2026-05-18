"""
scripts.manager.intake._shared — Phase 5 Day 2 entity schema + helpers.

Single source of truth for:

  - The 5 entity dataclasses every intake parser returns
  - The PHI redactor adapter (redact_or_block)
  - Persistence helpers (persist_intake_drop)

Trust boundaries enforced here:

  1. ``redact_or_block(text)`` raises ``BlockedByRedactor`` if the
     PHI redactor's hard-block pattern fires (e.g., a .nii/.dcm
     filename appears in the parsed text). The Phase 5 intake path
     refuses to persist a drop when blocked.

  2. ``persist_intake_drop`` always writes phi_redacted=TRUE — the
     ``intake_drops_must_redact`` CHECK constraint enforces this at
     the database boundary too.

  3. ``RAW_CONTENT_LIMIT`` truncates raw_content to 100 kB. Phase 5
     never stores a full PDF or full email — only the redacted
     parsed text. PDFs/photos go to R2 via ``upload_artifact`` and
     ``r2_artifact_path`` is the cold-copy reference.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

import psycopg2

from scripts.communicator.phi_redactor import ConsentFlags, RedactionResult, redact
from scripts.ledger import load_env

# --- raw_content storage cap ------------------------------------------------
RAW_CONTENT_LIMIT = 100 * 1024  # 100 kB — anything bigger goes to R2 only.


# ---------------------------------------------------------------------------
# Public entity dataclasses
# ---------------------------------------------------------------------------
@dataclass
class MedicationEntity:
    """Drug + dose + frequency extracted from a label or note."""

    name: str
    dose: str | None = None
    frequency: str | None = None
    confidence: float = 0.0
    source_span: tuple[int, int] | None = None


@dataclass
class CalendarEntity:
    """Appointment / event with optional clinician + location."""

    title: str
    date: str | None = None
    time: str | None = None
    clinician: str | None = None
    location: str | None = None
    confidence: float = 0.0


@dataclass
class ContactEntity:
    """Person mentioned by name + role (clinician / researcher / family)."""

    full_name: str
    role: str | None = None
    email: str | None = None
    institution: str | None = None
    confidence: float = 0.0


@dataclass
class TimelineEntity:
    """Observation / milestone with a date + free-text note."""

    when: str
    note: str
    category: str | None = None  # 'observation' | 'milestone' | 'feeding' | ...
    confidence: float = 0.0


@dataclass
class PHIBlock:
    """Marker that the redactor caught and removed a PHI span."""

    category: str
    replacement: str


Entity = MedicationEntity | CalendarEntity | ContactEntity | TimelineEntity | PHIBlock


# ---------------------------------------------------------------------------
# Redactor adapter
# ---------------------------------------------------------------------------
class BlockedByRedactor(RuntimeError):
    """Raised when the PHI redactor's hard-block pattern fires.

    Phase 5 drops MUST refuse to persist when this fires — the operator
    sees a UI error and the file is left on the local machine.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"intake blocked by PHI redactor: {reason}")


@dataclass
class RedactedText:
    """Output of ``redact_or_block``."""

    text: str
    redactions_count: int
    redactions: list[Any] = field(default_factory=list)


def redact_or_block(text: str, *, consent: ConsentFlags | None = None) -> RedactedText:
    """Run the PHI redactor and either return the redacted text or raise.

    The default ``ConsentFlags()`` keeps every flag False — Phase 5 intake
    parsers assume no recipient consent has been collected, so the strictest
    redaction set is applied. (Per-recipient consent only matters at the
    outreach surface, not the intake surface.)
    """
    result: RedactionResult = redact(text, consent=consent or ConsentFlags())
    if result.blocked:
        raise BlockedByRedactor(result.block_reason or "PHI block pattern fired")
    return RedactedText(
        text=result.text,
        redactions_count=len(result.redactions),
        redactions=list(result.redactions),
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _entity_to_jsonable(e: Entity) -> dict[str, Any]:
    """asdict() that also tags the entity kind so the JSON round-trips."""
    return {"_kind": type(e).__name__, **asdict(e)}


def persist_intake_drop(
    *,
    manager_user_id: str,
    input_type: Literal["pdf", "photo", "voice", "email", "text"],
    raw_content: str,
    entities: list[Entity],
    redactions_count: int,
    filename: str | None = None,
    r2_artifact_path: str | None = None,
    content_hash: str | None = None,
    proposed_actions: list[dict[str, Any]] | None = None,
    status: Literal[
        "pending", "approved", "rejected", "applied", "expired"
    ] = "pending",
) -> str:
    """Append one ``intake_drops`` row + return its uuid.

    Always writes ``phi_redacted=TRUE`` — the caller MUST have run
    ``redact_or_block`` on every text field before reaching this point.
    The ``intake_drops_must_redact`` CHECK constraint will reject the
    INSERT otherwise.

    Returns the new row's id (uuid string).
    """
    load_env()
    truncated = raw_content[:RAW_CONTENT_LIMIT]
    parsed_json = json.dumps([_entity_to_jsonable(e) for e in entities])
    proposed_json = json.dumps(proposed_actions or [])

    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO intake_drops (
                    manager_user_id, input_type, filename, r2_artifact_path,
                    content_hash, raw_content, parsed_entities, proposed_actions,
                    status, phi_redacted, redactions_count
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb,
                        %s, TRUE, %s)
                RETURNING id
                """,
                (
                    manager_user_id,
                    input_type,
                    filename,
                    r2_artifact_path,
                    content_hash,
                    truncated,
                    parsed_json,
                    proposed_json,
                    status,
                    redactions_count,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    return str(row[0])


# ---------------------------------------------------------------------------
# Helpers for tests + callers
# ---------------------------------------------------------------------------
def get_manager_user_id() -> str:
    """Resolve the hardcoded single-operator id from env.

    Defaults to 'shako-jincharadze' if MANAGER_USER_ID is unset — Phase 5
    plan §"Pre-decisions §4" pinned this as the env-var design.
    """
    load_env()
    return os.environ.get("MANAGER_USER_ID", "shako-jincharadze").strip()


def now_iso() -> str:
    return datetime.now().isoformat()
