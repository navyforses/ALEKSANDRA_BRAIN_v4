"""
import_contacts_from_notion.py — Phase 3 Day 1 contacts seeder.

Reads a Notion-exported CSV of contacts and inserts new rows into the
Supabase `contacts` table. Idempotent: rows are deduped by email
(case-insensitive); when email is missing, by lowercased full_name.

Phase 3 maximally-protective defaults are enforced for every imported row:
  consent_full_name        = FALSE
  consent_doctor_names     = FALSE
  consent_hospital_names   = FALSE
  outreach_language        = 'en'
  outreach_count           = 0
  last_contacted_at        = NULL

Shako (or a follow-up sprint) flips consent_* flags per-contact only after
an explicit consent conversation. The redactor reads these flags at draft
time; default FALSE means the redactor will use "A.J., 8-month-old infant
with severe HIE" as the default identity.

Expected CSV columns (case-insensitive; missing optional fields are OK):
  full_name        (REQUIRED)
  short_name
  title
  role
  institution
  department
  city
  country
  email
  phone
  website
  research_focus   (semicolon-separated list)
  orcid
  contact_type     (researcher|clinician|coordinator|...)
  relationship_status
  outreach_language    (en|fr|ka; optional, inferred when missing)
  first_contact_date  (YYYY-MM-DD)
  last_contact_date   (YYYY-MM-DD)
  next_followup_date  (YYYY-MM-DD)
  communication_notes
  aleksandra_relevance

Usage:
  .venv/Scripts/python.exe -X utf8 -m scripts.import_contacts_from_notion \\
      --input data/notion_contacts.csv --dry-run

  .venv/Scripts/python.exe -X utf8 -m scripts.import_contacts_from_notion \\
      --input data/notion_contacts.csv --confirm
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg2
import psycopg2.extras

from scripts.ledger import load_env


VALID_CONTACT_TYPES = {
    "researcher",
    "clinician",
    "coordinator",
    "social_worker",
    "navigator",
    "funder",
    "mentor",
    "family_support",
    "institution",
    "other",
}

VALID_RELATIONSHIP_STATUSES = {
    "active",
    "pending_response",
    "cold",
    "warm",
    "hot",
    "lost_contact",
    "declined",
    "completed",
}

VALID_LANGUAGES = {"en", "fr", "ka"}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GEORGIAN_RE = re.compile(r"[\u10A0-\u10FF]")

FR_HINTS = {
    "france",
    "belgium",
    "switzerland",
    "quebec",
    "montreal",
    "paris",
    "lyon",
    "marseille",
    "toulouse",
    "strasbourg",
    "universite",
    "hopital",
    "chu ",
}

KA_HINTS = {
    "georgia",
    "sakartvelo",
    "tbilisi",
    "batumi",
    "kutaisi",
}


@dataclass
class ContactRow:
    full_name: str
    short_name: str | None
    title: str | None
    role: str | None
    institution: str | None
    department: str | None
    city: str | None
    country: str | None
    email: str | None
    phone: str | None
    website: str | None
    research_focus: list[str]
    orcid: str | None
    contact_type: str | None
    relationship_status: str | None
    outreach_language: str
    first_contact_date: str | None
    last_contact_date: str | None
    next_followup_date: str | None
    communication_notes: str | None
    aleksandra_relevance: str | None

    def dedupe_key(self) -> str:
        if self.email:
            return f"email::{self.email.strip().lower()}"
        return f"name::{self.full_name.strip().lower()}"


def _g(row: dict, key: str) -> str | None:
    """Case-insensitive get; returns None for empty/blank strings."""
    for k, v in row.items():
        if k.strip().lower() == key.lower():
            if v is None:
                return None
            s = str(v).strip()
            return s if s else None
    return None


def _date_or_none(s: str | None) -> str | None:
    """Pass through YYYY-MM-DD; return None otherwise."""
    if not s:
        return None
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s
    return None


def _enum_or_none(s: str | None, allowed: set[str]) -> str | None:
    if not s:
        return None
    s_low = s.strip().lower()
    return s_low if s_low in allowed else None


def _email_or_none(s: str | None) -> str | None:
    if not s:
        return None
    email = s.strip().lower()
    return email if EMAIL_RE.match(email) else None


def _infer_outreach_language(raw: dict) -> str:
    explicit = _enum_or_none(_g(raw, "outreach_language"), VALID_LANGUAGES)
    if explicit:
        return explicit

    haystack = " ".join(
        v
        for v in (
            _g(raw, "full_name"),
            _g(raw, "short_name"),
            _g(raw, "institution"),
            _g(raw, "department"),
            _g(raw, "city"),
            _g(raw, "country"),
            _g(raw, "email"),
        )
        if v
    )
    hay_low = haystack.lower()
    if GEORGIAN_RE.search(haystack) or any(h in hay_low for h in KA_HINTS):
        return "ka"
    if any(h in hay_low for h in FR_HINTS) or ".fr" in hay_low:
        return "fr"
    return "en"


def parse_csv_with_warnings(path: Path) -> tuple[list[ContactRow], list[str]]:
    rows: list[ContactRow] = []
    warnings: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_no, raw in enumerate(reader, start=2):
            full_name = _g(raw, "full_name")
            if not full_name:
                continue
            email_raw = _g(raw, "email")
            email = _email_or_none(email_raw)
            if email_raw and not email:
                warnings.append(
                    f"line {line_no}: skipped {full_name!r}; invalid email {email_raw!r}"
                )
                continue
            focus_raw = _g(raw, "research_focus") or ""
            focus = [
                t.strip() for t in focus_raw.replace(",", ";").split(";") if t.strip()
            ]
            rows.append(
                ContactRow(
                    full_name=full_name,
                    short_name=_g(raw, "short_name"),
                    title=_g(raw, "title"),
                    role=_g(raw, "role"),
                    institution=_g(raw, "institution"),
                    department=_g(raw, "department"),
                    city=_g(raw, "city"),
                    country=_g(raw, "country"),
                    email=email,
                    phone=_g(raw, "phone"),
                    website=_g(raw, "website"),
                    research_focus=focus,
                    orcid=_g(raw, "orcid"),
                    contact_type=_enum_or_none(
                        _g(raw, "contact_type"), VALID_CONTACT_TYPES
                    ),
                    relationship_status=_enum_or_none(
                        _g(raw, "relationship_status"), VALID_RELATIONSHIP_STATUSES
                    ),
                    outreach_language=_infer_outreach_language(raw),
                    first_contact_date=_date_or_none(_g(raw, "first_contact_date")),
                    last_contact_date=_date_or_none(_g(raw, "last_contact_date")),
                    next_followup_date=_date_or_none(_g(raw, "next_followup_date")),
                    communication_notes=_g(raw, "communication_notes"),
                    aleksandra_relevance=_g(raw, "aleksandra_relevance"),
                )
            )
    return rows, warnings


def parse_csv(path: Path) -> list[ContactRow]:
    rows, _warnings = parse_csv_with_warnings(path)
    return rows


def existing_dedupe_keys(conn) -> set[str]:
    """Build the dedupe-key set from rows already in contacts."""
    keys: set[str] = set()
    with conn.cursor() as cur:
        cur.execute("SELECT email, full_name FROM contacts")
        for email, full_name in cur.fetchall():
            if email:
                keys.add(f"email::{email.strip().lower()}")
            if full_name:
                keys.add(f"name::{full_name.strip().lower()}")
    return keys


def insert_contact(conn, row: ContactRow) -> None:
    """Insert a single contact with Phase 3 maximally-protective defaults."""
    sql = """
    INSERT INTO contacts (
      full_name, short_name, title, role,
      institution, department, city, country,
      email, phone, website,
      research_focus, orcid,
      contact_type, relationship_status,
      first_contact_date, last_contact_date, next_followup_date,
      communication_notes, aleksandra_relevance,
      consent_full_name, consent_doctor_names, consent_hospital_names,
      outreach_language, outreach_count
    ) VALUES (
      %(full_name)s, %(short_name)s, %(title)s, %(role)s,
      %(institution)s, %(department)s, %(city)s, %(country)s,
      %(email)s, %(phone)s, %(website)s,
      %(research_focus)s, %(orcid)s,
      %(contact_type)s, %(relationship_status)s,
      %(first_contact_date)s, %(last_contact_date)s, %(next_followup_date)s,
      %(communication_notes)s, %(aleksandra_relevance)s,
      FALSE, FALSE, FALSE,
      %(outreach_language)s, 0
    )
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            {
                "full_name": row.full_name,
                "short_name": row.short_name,
                "title": row.title,
                "role": row.role,
                "institution": row.institution,
                "department": row.department,
                "city": row.city,
                "country": row.country,
                "email": row.email,
                "phone": row.phone,
                "website": row.website,
                "research_focus": row.research_focus or None,
                "orcid": row.orcid,
                "contact_type": row.contact_type,
                "relationship_status": row.relationship_status,
                "outreach_language": row.outreach_language,
                "first_contact_date": row.first_contact_date,
                "last_contact_date": row.last_contact_date,
                "next_followup_date": row.next_followup_date,
                "communication_notes": row.communication_notes,
                "aleksandra_relevance": row.aleksandra_relevance,
            },
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to Notion-exported contacts CSV.",
    )
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Print would-import counts but do not write to DB.",
    )
    mode.add_argument(
        "--confirm",
        action="store_true",
        help="Actually INSERT new rows. Idempotent — re-runs only add new dedupe keys.",
    )
    args = ap.parse_args()

    load_env()
    if not args.input.exists():
        print(f"[ERROR] input file not found: {args.input}", file=sys.stderr)
        return 2

    rows, warnings = parse_csv_with_warnings(args.input)
    print(f"Parsed {len(rows)} CSV rows from {args.input}")
    if warnings:
        print(f"Skipped invalid rows: {len(warnings)}")
        for msg in warnings[:10]:
            print(f"  WARN: {msg}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more warnings")

    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        seen = existing_dedupe_keys(conn)
        print(f"DB already has {len(seen)} dedupe keys")

        new_rows: list[ContactRow] = []
        skipped_dups = 0
        skipped_in_batch = 0
        batch_keys: set[str] = set()
        for r in rows:
            k = r.dedupe_key()
            if k in seen:
                skipped_dups += 1
                continue
            if k in batch_keys:
                skipped_in_batch += 1
                continue
            batch_keys.add(k)
            new_rows.append(r)

        print(f"New rows to import:  {len(new_rows)}")
        print(f"Skipped (in DB):     {skipped_dups}")
        print(f"Skipped (in CSV):    {skipped_in_batch}")

        if args.dry_run:
            for r in new_rows[:10]:
                print(
                    f"  WOULD INSERT: {r.full_name} <{r.email or 'no-email'}> "
                    f"lang={r.outreach_language}"
                )
            if len(new_rows) > 10:
                print(f"  ... and {len(new_rows) - 10} more")
            print("[DRY-RUN] no rows written")
            return 0

        # --confirm path: one transaction, all-or-nothing
        conn.autocommit = False
        try:
            for r in new_rows:
                insert_contact(conn, r)
            conn.commit()
            print(f"[CONFIRMED] inserted {len(new_rows)} new contacts")
            return 0
        except Exception as e:
            conn.rollback()
            print(
                f"[FAILED] rolled back; no rows inserted. Error: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
