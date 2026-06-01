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

import json
import os
import sys
import urllib.parse
import urllib.request

from scripts.ledger import load_env

OUT_PATH = ".secrets/family_contact_id.txt"


def _rest(
    method: str, path: str, base: str, key: str, body: dict | None = None
) -> list:
    """Minimal Supabase PostgREST call (IPv4; service-role bypasses RLS).

    Used instead of a direct psycopg2 connection because the Supavisor pooler
    password can drift in local .env, whereas the REST endpoint authenticates
    with the service-role key we already hold.
    """
    url = base.rstrip("/") + "/rest/v1/" + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("apikey", key)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
    return json.loads(raw) if raw else []


def main() -> int:
    load_env()
    email = os.environ.get("FAMILY_GMAIL_ADDRESS", "").strip()
    if not email:
        print("ERROR: FAMILY_GMAIL_ADDRESS not set in .env", file=sys.stderr)
        return 2

    base = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not base or not key:
        print(
            "ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set", file=sys.stderr
        )
        return 2

    enc = urllib.parse.quote(email)
    found = _rest(
        "GET",
        f"contacts?email=ilike.{enc}&select=id,consent_full_name"
        "&order=consent_full_name.desc&limit=1",
        base,
        key,
    )
    if found:
        contact_id = str(found[0]["id"])
        if not found[0].get("consent_full_name"):
            _rest(
                "PATCH",
                f"contacts?id=eq.{contact_id}",
                base,
                key,
                {"consent_full_name": True},
            )
            print("reused existing contact; set consent_full_name=TRUE")
        else:
            print("reused existing contact (consent already TRUE)")
    else:
        created = _rest(
            "POST",
            "contacts?select=id",
            base,
            key,
            {
                "full_name": "Family (self) — weekly digest recipient",
                "email": email,
                "contact_type": "family_support",
                "relationship_status": "active",
                "consent_full_name": True,
                "outreach_language": "en",
                "aleksandra_relevance": "The family's own inbox; weekly brief is delivered here.",
            },
        )
        contact_id = str(created[0]["id"])
        print("created new family-self contact")

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
