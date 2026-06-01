r"""cleanup_weekly_drafts.py — remove duplicate weekly-brief Gmail drafts.

A render that creates the Gmail draft (step 7) but then fails on the
outreach_log insert (step 8) leaves an orphan draft behind with no DB row.
Repeated retries pile up identical drafts. This tool lists every draft whose
subject begins with the weekly-brief prefix and (with --apply) deletes them,
using the same compose-only OAuth credentials as the drafter.

By default it is DRY-RUN: it only counts. Pass --apply to actually delete.

Run LOCALLY (PowerShell, repo root):

    .venv\Scripts\python.exe scripts\communicator\cleanup_weekly_drafts.py            # count only
    .venv\Scripts\python.exe scripts\communicator\cleanup_weekly_drafts.py --apply    # delete
"""

from __future__ import annotations

import sys

SUBJECT_PREFIX = "ALEKSANDRA_BRAIN Weekly Brief"


def main(argv: list[str]) -> int:
    apply = "--apply" in argv
    from scripts.communicator.outreach_drafter import _gmail_service

    service = _gmail_service()
    drafts_api = service.users().drafts()

    # Page through all drafts; read each draft's Subject header.
    matched: list[str] = []
    page_token = None
    while True:
        resp = drafts_api.list(
            userId="me", maxResults=100, pageToken=page_token
        ).execute()
        for d in resp.get("drafts", []):
            did = d["id"]
            meta = drafts_api.get(userId="me", id=did, format="metadata").execute()
            headers = meta.get("message", {}).get("payload", {}).get("headers", [])
            subject = next(
                (h["value"] for h in headers if h.get("name", "").lower() == "subject"),
                "",
            )
            if subject.startswith(SUBJECT_PREFIX):
                matched.append(did)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"weekly-brief drafts found: {len(matched)}")
    if not apply:
        print("DRY-RUN — pass --apply to delete them.")
        return 0

    deleted = 0
    for did in matched:
        drafts_api.delete(userId="me", id=did).execute()
        deleted += 1
    print(f"deleted: {deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
