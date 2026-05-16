# Phase 3 handoff — 2026-05-16

## Current state

Phase 3 is green. Final verifier result:

`python -X utf8 -m scripts.verify_phase3 --gate all`

Result: `11/11 PASS — ALL GREEN`

Regression result included in verifier:

`verify_phase2_5: 16/16 PASS`

## What was fixed

- `scripts/import_contacts_from_notion.py`
  - Fixed the live import transaction error.
  - Added invalid email skip/warnings.
  - Added `outreach_language` inference.
  - Added safer CSV parsing flow.

- `scripts/verify_phase3.py`
  - CGM-10 now requires real imported contacts, schema, RLS, and anon REST smoke checks.
  - CGM-04 now requires at least one pending Gmail draft, not only structural setup.

- `scripts/communicator/outreach_drafter.py`
  - Daily draft limit now fails closed on database errors.
  - DB helpers load environment variables reliably.
  - Outreach log insert also updates `contacts.last_contacted_at`, `outreach_count`, and `updated_at`.
  - Compose-only Gmail behavior was verified.

- `scripts/communicator/weekly_brief.py`
  - Fixed live schema bug where code used nonexistent `papers.ledger_id`.
  - Weekly brief now links papers to evidence ledger through real identifiers: PMID, CT ID, DOI, and URL.

- `TRIAGE_PLAN_PHASE_3.md`
  - Corrected documentation error: confidence below `0.50` routes to `T4`, not `T3`.

- `.gitignore`
  - Added generated/secret-adjacent outputs:
    - `briefs/*.pdf`
    - `data/notion_contacts.csv`
  - `.secrets/` was already ignored and verified.

## Contacts import

Correct contact file:

`data/notion_contacts.csv`

Import result:

- Parsed rows: `96`
- Inserted contacts: `96`
- Skipped rows: `0`

Safety defaults verified:

- Total contacts: `96`
- `consent_email = false`: `96`
- `consent_social = false`: `96`
- `consent_research = false`: `96`
- English outreach language inferred: `78`

CGM-10 result:

- PASS
- Evidence: `contacts=96/75`
- Anon REST smoke checks returned HTTP 200 with zero visible rows, as expected under RLS.

## Gmail setup and first draft

OAuth was completed for:

`jincharadzeshako@gmail.com`

Local files:

- `.secrets/gmail_oauth_credentials.json`
- `.secrets/gmail_oauth_token.json`

Both are protected by `.gitignore`.

First Gmail draft was created only as a draft. It was not sent.

Recipient:

- Name: `DTRI Cord Blood Therapy Info`
- Email: `cordbloodtherapyinfo@dm.duke.edu`
- Institution: `Duke University`
- Contact ID: `487942d7-8e41-48d7-9ea8-639383010f52`

Draft metadata:

- Gmail draft ID: `r-1111876243842625585`
- Outreach log ID: `062cdb71-f2b7-4853-b7a3-eff23fdf9a5d`
- Subject: `Question about HIE research context`
- Confidence: `0.15`
- Citations: `5`

CGM-04 result:

- PASS
- Evidence included `pending_drafts=1`

## Final gate results

- CGM-01: PASS
- CGM-02: PASS
- CGM-03: PASS
- CGM-04: PASS
- CGM-05: PASS
- CGM-06: PASS
- CGM-07: PASS
- CGM-08: PASS
- CGM-09: PASS
- CGM-10: PASS
- REGR: PASS

## Important next actions

1. Open Gmail Drafts and manually review the Duke draft before sending.
2. Do not press Send until the text is personally checked.
3. Keep Claude's parallel edits separate. Avoid touching unrelated frontend files unless that becomes the next task.
4. Before any commit, review `git status` carefully because there may be Claude/user files in the working tree.
