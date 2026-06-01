r"""ensure_family_contact.py — find-or-create the family-self contact row.

The weekly Gmail digest is delivered to the family's own inbox (Shako). The
worker needs FAMILY_CONTACT_ID set to a `contacts.id` row that:
  - has consent_full_name = TRUE (the digest goes to the father himself, so
    identity redaction is intentionally off for this one recipient), and
  - is the FK target for the outreach_log row the digest insert writes.

This script reads FAMILY_GMAIL_ADDRESS from the environment, looks for an
existing contact with that email, creates one if absent, and guarantees
consent_full_name = TRUE. It writes ONLY the resulting UUID to
`.secrets/family_contact_id.txt` (no PII), then prints the Railway command.

Run LOCALLY (PowerShell, repo root):

    .venv\Scripts\python.exe scripts\communicator\ensure_family_contact.py
"""

from __future__ import annotations

import os
import sys

import psycopg2

from scripts.ledger import load_env

OUT_PATH = ".secrets/family_contact_id.txt"


def main() -> int:
    load_env()
    email = os.environ.get("FAMILY_GMAIL_ADDRESS", "").strip()
    if not email:
        print("ERROR: FAMILY_GMAIL_ADDRESS not set in .env", file=sys.stderr)
        return 2

    db = os.environ.get("SUPABASE_DB_URL", "").strip()
    if not db:
        print("ERROR: SUPABASE_DB_URL not set in .env", file=sys.stderr)
        return 2

    conn = psycopg2.connect(db, sslmode="require")
    try:
        with conn.cursor() as cur:
            # Find an existing contact by email (case-insensitive).
            cur.execute(
                "SELECT id, consent_full_name FROM contacts WHERE email ILIKE %s "
                "ORDER BY consent_full_name DESC NULLS LAST LIMIT 1",
                (email,),
            )
            row = cur.fetchone()
            if row:
                contact_id, consent = str(row[0]), bool(row[1])
                if not consent:
                    cur.execute(
                        "UPDATE contacts SET consent_full_name = TRUE, "
                        "updated_at = NOW() WHERE id = %s",
                        (contact_id,),
                    )
                    print("reused existing contact; set consent_full_name=TRUE")
                else:
                    print("reused existing contact (consent already TRUE)")
            else:
                cur.execute(
                    """
                    INSERT INTO contacts (
                      full_name, email, contact_type, relationship_status,
                      consent_full_name, outreach_language, aleksandra_relevance
                    ) VALUES (
                      %s, %s, 'family_support', 'active',
                      TRUE, 'en', %s
                    )
                    RETURNING id
                    """,
                    (
                        "Family (self) — weekly digest recipient",
                        email,
                        "The family's own inbox; weekly brief is delivered here.",
                    ),
                )
                contact_id = str(cur.fetchone()[0])
                print("created new family-self contact")
        conn.commit()
    finally:
        conn.close()

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(contact_id)
    print(f"FAMILY_CONTACT_ID -> {contact_id}")
    print(f"written -> {OUT_PATH}")
    print("\nNext: set it on the Railway worker (no deploy yet), then tell Claude:")
    print(
        '  railway variables --set "FAMILY_CONTACT_ID=$(Get-Content '
        '.secrets/family_contact_id.txt -Raw)" -s aleksandra-worker --skip-deploys'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
