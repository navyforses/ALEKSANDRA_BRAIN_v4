# Runbook — Gmail API OAuth (Phase 3 outreach drafts)

**Last updated:** 2026-05-16
**Scope:** `https://www.googleapis.com/auth/gmail.compose` — drafts only,
**no send capability**. Send action stays manual via the Gmail UI for the
first 6 months per the 2026-05-16 owner-locked decision.

## Why compose-only

The compose scope lets the script create a Gmail draft on the user's behalf.
It does **not** include `gmail.send`, `gmail.modify`, or any inbox read
capability. Even if the script is compromised, it cannot send mail or read
existing messages.

Hard rule (months 1–6): never add `gmail.send` to `GMAIL_SCOPES` in
`scripts/communicator/outreach_drafter.py`.

## One-time setup (do this once per machine)

### 1. Create a Google Cloud project + OAuth client

1. Go to <https://console.cloud.google.com/>.
2. Create a project (or reuse an existing one — e.g. `aleksandra-brain`).
3. Enable the **Gmail API** for that project.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID.**
5. Application type: **Desktop app**.
6. Name: `aleksandra-brain outreach drafter`.
7. Click **Create**, then **Download JSON**.

### 2. Place the credentials file

Save the downloaded JSON as:

```
.secrets/gmail_oauth_credentials.json
```

`.secrets/` must be in `.gitignore`. Verify:

```powershell
Get-Content .gitignore | Select-String -Pattern "\.secrets"
```

If the entry is missing, add it before continuing.

### 3. Configure consent screen (one-off)

1. **APIs & Services → OAuth consent screen.**
2. User type: **External** (Google Workspace optional).
3. Add scope: `https://www.googleapis.com/auth/gmail.compose` (only this one).
4. Add the family's Gmail address as a **Test user**.
5. Save.

### 4. Run the first auth flow

The first `draft_outreach()` call (without `dry_run=True`) opens a browser
window for OAuth consent. After approval the token is written to
`.secrets/gmail_oauth_token.json` and reused on subsequent runs.

```powershell
.\.venv\Scripts\python.exe -X utf8 -c "
from scripts.communicator.outreach_drafter import _gmail_service
service = _gmail_service()
print('Gmail OAuth ok, profile:', service.users().getProfile(userId='me').execute().get('emailAddress'))
"
```

Expected: a browser window opens, you grant consent for the configured
account, the script prints the Gmail address.

If the script raises `FileNotFoundError`, the credentials JSON is not at the
expected path.

## Token refresh

The token JSON contains a refresh token. The library refreshes
automatically once the access token expires. If the refresh fails (e.g.
after a long idle period or revoked consent), delete
`.secrets/gmail_oauth_token.json` and re-run the bootstrap above.

## Revocation (panic procedure)

If you suspect the token is compromised:

1. Open <https://myaccount.google.com/permissions>.
2. Find **aleksandra-brain outreach drafter** in the third-party list.
3. Click **Remove Access**.
4. Delete the local file: `Remove-Item .secrets/gmail_oauth_token.json`.

The script will then refuse all Gmail calls until a fresh consent flow is
run.

## What the script never does

- Never sends email — there is no `gmail.send` in `GMAIL_SCOPES`.
- Never reads inbox — no `gmail.readonly`.
- Never modifies messages — no `gmail.modify`.
- Never accesses contacts or other Google services — only Gmail.
- Never logs the OAuth token or credentials JSON.

These restrictions are enforced by the OAuth scope itself, not just by code
convention. A bug in the script cannot grant itself send capability without
re-running the consent flow with an expanded scope, which requires a
human-in-the-loop browser approval.

## Sending an approved draft

The Communicator script creates drafts; **Shako sends them manually**:

1. Open Gmail in a browser (the same account used during OAuth).
2. Click **Drafts** in the sidebar.
3. The new draft appears with the subject + body the script composed.
4. Review and edit as needed.
5. Click **Send**.

A row in `outreach_log` is inserted with `gmail_draft_id=<id>` and
`sent_at=NULL` at creation time. A future automation hook may detect when
the message has been actually sent and update `sent_at`, but that's
deferred to month 7+.

## Daily cap

The script refuses to create more than `MAX_DAILY_DRAFTS=5` drafts per UTC
day. If you need to exceed this, change the constant in
`scripts/communicator/outreach_drafter.py` and document the change in a new
SCOPE_DECISIONS entry. Do not increase the cap silently.
