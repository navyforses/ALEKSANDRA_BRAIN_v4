# Runbook — Notion API integration (Phase 4 ACD-04)

**Last updated:** 2026-05-16
**Scope:** Write-only append into the family knowledge-base database.
The integration token grants access to **one parent page** in Shako's
Notion workspace; everything else stays private.

## One-time setup

### 1. Create an internal integration token

1. Go to <https://www.notion.so/profile/integrations>.
2. Click **+ New integration**.
3. Name: `aleksandra-brain-archiver`.
4. Associated workspace: the family workspace.
5. Capabilities — check ONLY:
   - Read content
   - Insert content
   - Update content
   Leave **No user information** checked. Do NOT grant read/write for
   comments or user emails.
6. Save. Copy the `Internal Integration Token` (starts with `secret_…` or
   `ntn_…` for newer integrations).
7. Add to `.env`:
   ```
   NOTION_API_KEY=ntn_xxxxxxxxxxxxxxxxxxxxxxxx
   ```

### 2. Create a parent page in Notion

1. In the family workspace, create a page titled e.g. **"ALEKSANDRA_BRAIN"**.
2. Click the **`…`** menu in the top-right of that page → **Connections** →
   **Add connection** → select `aleksandra-brain-archiver`.
3. Copy the page ID from the URL. A Notion URL looks like:
   ```
   https://www.notion.so/Family-Page-Title-abc123def456...
                                            ^^^^^^^^^^^^^^
   ```
   The trailing 32-character hex string is the page ID. Add to `.env`:
   ```
   NOTION_PARENT_PAGE_ID=abc123def456...
   ```

### 3. Bootstrap the findings database

Run once:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.notion_bootstrap
```

Expected output:

```
Notion database created.

  Database ID : 11223344-5566-7788-99aa-bbccddeeff00
  URL         : https://www.notion.so/abc.../11223344...

Next step: add this line to .env (do NOT commit .env):

  NOTION_DATABASE_ID=11223344-5566-7788-99aa-bbccddeeff00
```

Copy the `NOTION_DATABASE_ID` line into `.env` exactly as printed.

### 4. Verify

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.verify_phase4 --gate ffv-04
```

Expected: PASS — Notion bootstrap state resolves.

## Database schema

`scripts/notion_bootstrap.py:SCHEMA` defines:

- **Title** (title) — one-line factual finding
- **Date** (date) — when archived
- **Tier** (select T0/T1/T2/T3/T4) — alert tier router output
- **Confidence** (number 0..1) — confidence_classifier score
- **Run ID** (rich_text) — originating `runs.id` for OBS-02 trace
- **Citations** (multi_select) — PMID/DOI/NCT identifiers
- **Source** (rich_text) — Communicator audience + query
- **PHI Redacted** (checkbox) — always TRUE for safety net

If you change the schema in Notion, update the constants at the top of
`scripts/communicator/notion_archiver.py` to match.

## Idempotency

Every page carries the originating `runs.id` in the **Run ID** property.
`notion_archiver.archive_finding()` queries by Run ID before creating a
new page. Re-running the archiver on the same finding is safe — the
function returns `NotionArchiveResult(created=False, ...)` for the
duplicate.

## Revocation

If the token is compromised:

1. Go to <https://www.notion.so/profile/integrations>.
2. Click `aleksandra-brain-archiver` → **Settings** → **Delete integration**.
3. Remove `NOTION_API_KEY` from `.env`.
4. Re-do the bootstrap from step 1 with a fresh token.

The existing pages in the database are unaffected by token rotation.

## What the integration cannot do

- It cannot read pages outside the connected parent page.
- It cannot list workspace users.
- It cannot read or write comments unless explicitly granted (we do not
  grant that capability).
- It cannot delete pages — Notion's API supports archive, not destroy.
  An accidentally-created page can be manually trashed by Shako.

These restrictions are enforced by Notion itself based on the integration's
declared capabilities and the connected-pages scope, not just by code
convention. A bug in `notion_archiver.py` cannot grant itself broader
access without re-running the consent flow under a new integration with
expanded capabilities.

## Hard rule

`scripts/communicator/notion_archiver.py:archive_finding()` only writes
pages whose underlying `SummaryDraft.persistable()` is True (banned-phrase
passed, redaction not blocked, ≥1 cited claim). The archiver also stamps
**PHI Redacted = TRUE** on every page. Inserting a page with the checkbox
False is structurally absent — there is no code path that produces it.
