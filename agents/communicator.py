"""
Communicator Agent — Family Liaison

Bridges the system and the family. Urgent findings → Telegram. Weekly briefs
→ email. Borderline evidence → two-way question:
"Include this paper in analysis? [Yes/No]"

The family stays informed and in control. The AI proposes, the family disposes.

Phase 6 I18N-06 / D-02 (per-tier policy)
----------------------------------------
Family-visible newly-created rows in `aleksandra_timeline`, `hypotheses`,
`therapies`, and `briefs.sections` MUST be emitted as `{en, ka}` JSONB. This
module exposes `insert_bilingual_row()` — the canonical pattern any
CrewAI Tool() instance MUST use when writing to those 4 tables.

The wrapper:
  1. Calls scripts.communicator.bilingual.compose_bilingual() to get
     {en, ka} via a single Anthropic strict-tool-use call.
  2. Runs scripts.communicator.phi_redactor.redact_bilingual() on BOTH
     halves and raises if EITHER blocked (closes RESEARCH.md Pitfall 5).
  3. Runs scripts.communicator.banned_phrases.check() with per-locale
     scoping on each half (Phase 3 CGM-04 + Phase 6 D-05 imperative-verb
     lint) and raises if EITHER half violates.
  4. Casts the {en, ka} pair as JSONB via psycopg2.extras.Json on the
     INSERT — match migration 012's converted-column shape.

DO NOT use this helper for:
  - scripts/communicator/outreach_drafter.py (single-recipient,
    single-language per contacts.outreach_language — stays as-is).
  - Internal CrewAI agent reasoning loops (Spider/Analyzer/Hypothesis/
    Repurposing) — internal English-only per SPEC out-of-scope.
"""

from __future__ import annotations

import json
import os
from typing import Any

import psycopg2
import psycopg2.extras

from crewai import Agent

from scripts.communicator.banned_phrases import check as banned_phrase_check
from scripts.communicator.bilingual import compose_bilingual
from scripts.communicator.language import detect as detect_language
from scripts.communicator.phi_redactor import (
    ConsentFlags,
    redact as redact_phi,
    redact_bilingual,
)
from scripts.communicator.summarize import generate_summary
from scripts.ledger import load_env

# Day 3 tool registry — callable directly by the verifier, Day 5 outreach
# drafter, and Day 6 weekly brief. CrewAI @tool decoration is intentionally
# deferred until the Crew is actually run; at that point each entry below
# becomes a Tool() instance with the same signature.
COMMUNICATOR_TOOLS = {
    "generate_summary": generate_summary,
    "redact_phi": redact_phi,
    "detect_language": detect_language,
    "compose_bilingual": compose_bilingual,
    "redact_bilingual": redact_bilingual,
}

TOOLS: list = []  # CrewAI Tool() instances populated when the Crew runs.

# Tables whose family-visible columns must hold {en, ka} JSONB per
# migration 012. The column lists below are the columns this helper
# emits as bilingual; neighbouring TEXT columns (event_type, status, etc.)
# stay scalar and are passed through unchanged.
BILINGUAL_TABLES = {
    "aleksandra_timeline": ("title", "description"),
    "hypotheses": ("title", "description"),
    "therapies": ("name", "evidence_summary"),
}


BACKSTORY = """
You write for Shalva, Aleksandra's father — a software developer, not a
clinician. Your tone is precise, sourced, and never alarmist. You never
hide bad news; you also never invent good news.

You always cite. You never write "studies show" without naming the studies.
You never write "experts agree" — you name the experts or you say "I don't know".

You translate Latin and clinical jargon into Georgian when relevant, and
you can fall back to English when precision matters more than fluency.

Every family-visible row you write goes into the database as bilingual
{en, ka} JSONB. Use `compose_bilingual()` (single Anthropic strict-tool-use
call). Run `redact_bilingual()` on BOTH halves before any INSERT — never
persist if either half is blocked.
""".strip()


def build_communicator(llm_model: str = "claude-sonnet-4-5") -> Agent:
    return Agent(
        role="Family Liaison",
        goal=(
            "Deliver findings to the family with precision, sourcing, and "
            "appropriate urgency — never alarmist, never hidden."
        ),
        backstory=BACKSTORY,
        tools=TOOLS,
        llm=llm_model,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )


# ---------------------------------------------------------------------------
# Phase 6 I18N-06 — bilingual write-path helper
# ---------------------------------------------------------------------------
class BilingualWriteBlocked(RuntimeError):
    """Raised when redactor or imperative-verb lint blocks the bilingual pair.

    Carries the en/ka half-block reasons so the caller's audit log records
    which side tripped (e.g. 'ka: name leak' vs 'en: imperative violation').
    """


def _bilingual_check_and_raise(
    pair: dict[str, str],
    *,
    consent: ConsentFlags | None = None,
) -> dict[str, str]:
    """Run redactor + imperative-verb lint on both halves; raise on any fail.

    Returns the redacted {en, ka} pair (text fields replaced with the redactor's
    redacted output). Caller persists this pair, not the raw model output.

    Per RESEARCH.md Pitfall 5: PHI redaction must run on BOTH halves; OR-block
    contract means a leak in EITHER side fails the whole write.

    Per Phase 3 CGM-04 + Phase 6 D-05: imperative-verb lint runs on each half
    with per-locale scoping (banned_phrases.check(..., locales=('en',)) or
    locales=('ka',)) so cross-language false positives are avoided.
    """
    bilingual = redact_bilingual(pair, consent=consent)
    if bilingual["blocked_or"]:
        raise BilingualWriteBlocked(
            "PHI redactor blocked bilingual pair: "
            + "; ".join(bilingual["blocked_reasons"])
        )

    en_text: str = bilingual["en"].text
    ka_text: str = bilingual["ka"].text

    en_lint = banned_phrase_check(en_text, locales=("en",))
    ka_lint = banned_phrase_check(ka_text, locales=("ka",))
    if not en_lint.passed:
        raise BilingualWriteBlocked(
            "Imperative-verb lint blocked English half: "
            + ", ".join(v.matched for v in en_lint.violations)
        )
    if not ka_lint.passed:
        raise BilingualWriteBlocked(
            "Imperative-verb lint blocked Georgian half: "
            + ", ".join(v.matched for v in ka_lint.violations)
        )

    return {"en": en_text, "ka": ka_text}


def insert_bilingual_row(
    *,
    table: str,
    bilingual_fields: dict[str, dict[str, str]],
    scalar_fields: dict[str, Any] | None = None,
    consent: ConsentFlags | None = None,
    conn=None,
) -> str | None:
    """Insert a family-visible row with bilingual JSONB columns.

    Args:
        table: One of BILINGUAL_TABLES — checked against the allow-list to
            prevent accidental bilingual writes to internal tables.
        bilingual_fields: Mapping of column-name → {en, ka} pair. Each value
            is the output of compose_bilingual() (or _bilingual_mirror() for
            deterministic templates). Both halves redacted + linted before the
            INSERT fires.
        scalar_fields: Mapping of column-name → scalar value. These are the
            TEXT/timestamp/enum columns NOT being bilingualized (event_type,
            status, confidence_level, etc.). Passed through unchanged.
        consent: ConsentFlags for redactor. Defaults to family-conservative
            (consent_full_name=False, consent_doctor_names=False).
        conn: Optional pre-opened psycopg2 connection (for tests). Defaults
            to a fresh connection via SUPABASE_DB_URL.

    Returns:
        The inserted row's `id` (uuid as str), or None if the connection
        layer is unavailable.

    Raises:
        BilingualWriteBlocked: if either-half redactor blocks OR either-half
            imperative-verb lint fails.
        ValueError: if `table` is not in BILINGUAL_TABLES.

    Example:
        >>> pair_title = compose_bilingual(
        ...     "Draft a family-readable hypothesis title about ...",
        ...     client=anthropic.Anthropic(),
        ... )
        >>> pair_desc = compose_bilingual(...)
        >>> insert_bilingual_row(
        ...     table="hypotheses",
        ...     bilingual_fields={"title": pair_title, "description": pair_desc},
        ...     scalar_fields={"status": "proposed", "confidence_level": "low"},
        ... )
    """
    if table not in BILINGUAL_TABLES:
        raise ValueError(
            f"insert_bilingual_row: '{table}' is not in the bilingual allow-list "
            f"{sorted(BILINGUAL_TABLES.keys())}. Outreach_drafter and internal "
            "CrewAI agent writes stay English-only per CONTEXT.md D-02."
        )

    expected_cols = set(BILINGUAL_TABLES[table])
    given_cols = set(bilingual_fields.keys())
    unknown = given_cols - expected_cols
    if unknown:
        raise ValueError(
            f"insert_bilingual_row: unknown bilingual columns {sorted(unknown)} "
            f"for table '{table}' (expected subset of {sorted(expected_cols)})"
        )

    # Redact + lint EACH bilingual column independently. A leak in any field
    # blocks the whole write — never persist a partially-redacted row.
    cleaned: dict[str, dict[str, str]] = {}
    for col, pair in bilingual_fields.items():
        cleaned[col] = _bilingual_check_and_raise(pair, consent=consent)

    # Build the INSERT statement. JSONB cast uses psycopg2.extras.Json so the
    # serializer respects Unicode (Mkhedruli) without double-escaping.
    columns: list[str] = []
    placeholders: list[str] = []
    values: list[Any] = []

    for col, pair in cleaned.items():
        columns.append(col)
        placeholders.append("%s::jsonb")
        values.append(psycopg2.extras.Json(pair))

    if scalar_fields:
        for col, val in scalar_fields.items():
            columns.append(col)
            placeholders.append("%s")
            values.append(val)

    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}) "
        f"VALUES ({', '.join(placeholders)}) "
        "RETURNING id"
    )

    own_conn = False
    if conn is None:
        load_env()
        db_url = os.environ.get("SUPABASE_DB_URL", "").strip()
        if not db_url:
            # No DB — surface the SQL the caller would have run for audit.
            print(
                f"[insert_bilingual_row] SUPABASE_DB_URL missing; "
                f"would have run: {sql} with bilingual={json.dumps(cleaned, ensure_ascii=False)}"
            )
            return None
        conn = psycopg2.connect(db_url, sslmode="require")
        own_conn = True

    try:
        with conn.cursor() as cur:
            cur.execute(sql, values)
            row = cur.fetchone()
            new_id = str(row[0]) if row else None
        if own_conn:
            conn.commit()
        return new_id
    finally:
        if own_conn:
            conn.close()


__all__ = [
    "BACKSTORY",
    "COMMUNICATOR_TOOLS",
    "TOOLS",
    "BILINGUAL_TABLES",
    "BilingualWriteBlocked",
    "build_communicator",
    "insert_bilingual_row",
]
