"""
notion_bootstrap.py — Phase 4 Day 1 one-shot Notion database provisioner.

Creates the family knowledge-base database under a parent page Shako
provides via `NOTION_PARENT_PAGE_ID`. Prints the new database ID for
Shako to copy into `.env` as `NOTION_DATABASE_ID`.

The schema this script creates is the contract `notion_archiver.py`
writes against. If you change one, change both — the constants at the
top of `notion_archiver.py` document the canonical names.

Idempotency: if `NOTION_DATABASE_ID` is already set in `.env`, the
script exits with a notice rather than creating a duplicate database.
A `--force` flag exists for the rare case where the original DB was
deleted and a fresh one is genuinely wanted.

Usage:
    .venv/Scripts/python.exe -X utf8 -m scripts.notion_bootstrap
    .venv/Scripts/python.exe -X utf8 -m scripts.notion_bootstrap --force
"""

from __future__ import annotations

import argparse
import os
import sys

from notion_client import Client

from scripts.ledger import load_env


def _client() -> Client:
    token = os.environ.get("NOTION_API_KEY", "").strip()
    if not token:
        print(
            "[ERROR] NOTION_API_KEY missing — see docs/RUNBOOK-notion-api.md",
            file=sys.stderr,
        )
        sys.exit(2)
    return Client(auth=token)


def _parent_page_id() -> str:
    parent = os.environ.get("NOTION_PARENT_PAGE_ID", "").strip()
    if not parent:
        print(
            "[ERROR] NOTION_PARENT_PAGE_ID missing — set the parent page ID "
            "in .env. See docs/RUNBOOK-notion-api.md for how to find it.",
            file=sys.stderr,
        )
        sys.exit(2)
    return parent


SCHEMA = {
    "Title": {"title": {}},
    "Date": {"date": {}},
    "Tier": {
        "select": {
            "options": [
                {"name": "T0", "color": "red"},
                {"name": "T1", "color": "orange"},
                {"name": "T2", "color": "yellow"},
                {"name": "T3", "color": "blue"},
                {"name": "T4", "color": "gray"},
            ]
        }
    },
    "Confidence": {"number": {"format": "number"}},
    "Run ID": {"rich_text": {}},
    "Citations": {"multi_select": {"options": []}},
    "Source": {"rich_text": {}},
    "PHI Redacted": {"checkbox": {}},
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--force",
        action="store_true",
        help="Create a new database even if NOTION_DATABASE_ID is already set.",
    )
    args = ap.parse_args(argv)

    load_env()

    existing = os.environ.get("NOTION_DATABASE_ID", "").strip()
    if existing and not args.force:
        print(
            f"NOTION_DATABASE_ID already set to {existing!r}. "
            "Skipping (use --force to create a fresh database)."
        )
        return 0

    notion = _client()
    parent_id = _parent_page_id()

    db = notion.databases.create(
        parent={"type": "page_id", "page_id": parent_id},
        title=[
            {
                "type": "text",
                "text": {"content": "ALEKSANDRA_BRAIN — Findings"},
            }
        ],
        properties=SCHEMA,
    )
    db_id = db["id"]
    db_url = db.get("url", "")

    print()
    print("Notion database created.")
    print()
    print(f"  Database ID : {db_id}")
    print(f"  URL         : {db_url}")
    print()
    print("Next step: add this line to .env (do NOT commit .env):")
    print()
    print(f"  NOTION_DATABASE_ID={db_id}")
    print()
    print("Then re-run `python -m scripts.verify_phase4 --gate ffv-04` to confirm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
