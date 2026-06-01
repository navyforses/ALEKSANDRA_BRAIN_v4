r"""bootstrap_gmail_oauth.py — re-mint the Gmail compose-only OAuth token.

Run this LOCALLY (on the family machine, where a browser is available) when
the refresh token has expired or been revoked — e.g. the worker render fails
with `invalid_grant: Token has been expired or revoked`.

Background
----------
Google expires refresh tokens after 7 days for OAuth apps still in **Testing**
publishing status. For an unattended worker this is fatal: the Sunday Weekly
Brief draft stops being created. The durable fix is to set the OAuth consent
screen to **In production** in Google Cloud Console (one-time) BEFORE running
this script, so the freshly minted refresh token is long-lived.

What this does
--------------
1. Backs up any existing (dead) token to `*.bak`.
2. Opens a browser for the gmail.compose consent (you click "Allow").
3. Writes the fresh token to `.secrets/gmail_oauth_token.json`.
4. Verifies the new token is valid.
5. Writes the base64 of the fresh token to `.secrets/gmail_token_b64.txt`
   so it can be copied into the Railway `GMAIL_OAUTH_TOKEN_B64` variable.

Usage (PowerShell, from repo root):

    .venv\Scripts\python.exe scripts\communicator\bootstrap_gmail_oauth.py
"""

from __future__ import annotations

import base64
import os
import shutil
import sys

# Compose-only — must match outreach_drafter.GMAIL_SCOPES exactly.
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
CREDENTIALS_PATH = os.environ.get(
    "GMAIL_OAUTH_CREDENTIALS_PATH", ".secrets/gmail_oauth_credentials.json"
)
TOKEN_PATH = os.environ.get("GMAIL_OAUTH_TOKEN_PATH", ".secrets/gmail_oauth_token.json")
B64_OUT_PATH = ".secrets/gmail_token_b64.txt"


def main() -> int:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not os.path.exists(CREDENTIALS_PATH):
        print(f"ERROR: missing {CREDENTIALS_PATH}", file=sys.stderr)
        print(
            "Download the OAuth client JSON per docs/RUNBOOK-gmail-api.md.",
            file=sys.stderr,
        )
        return 2

    # Back up the old (likely dead) token so we never silently lose it.
    if os.path.exists(TOKEN_PATH):
        bak = TOKEN_PATH + ".bak"
        shutil.copy2(TOKEN_PATH, bak)
        print(f"backed up old token -> {bak}")
        os.remove(TOKEN_PATH)

    print("Opening browser for Gmail consent (scope: gmail.compose) ...")
    print("Sign in as the family account and click Allow.")
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, GMAIL_SCOPES)
    creds = flow.run_local_server(port=0)

    os.makedirs(os.path.dirname(TOKEN_PATH) or ".", exist_ok=True)
    with open(TOKEN_PATH, "w", encoding="utf-8") as fh:
        fh.write(creds.to_json())
    print(f"fresh token written -> {TOKEN_PATH}")

    # Sanity: confirm the token can mint an access token right now.
    check = Credentials.from_authorized_user_file(TOKEN_PATH, GMAIL_SCOPES)
    if not check.valid and check.expired and check.refresh_token:
        check.refresh(Request())
    print(
        "token valid:", check.valid, "| has refresh_token:", bool(check.refresh_token)
    )

    # Emit base64 for the Railway GMAIL_OAUTH_TOKEN_B64 variable.
    raw = open(TOKEN_PATH, "rb").read()
    b64 = base64.b64encode(raw).decode("ascii")
    with open(B64_OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(b64)
    print(f"base64 written -> {B64_OUT_PATH} (length {len(b64)})")
    print("\nNext: update the Railway worker variable, then redeploy:")
    print(
        '  railway variables --set "GMAIL_OAUTH_TOKEN_B64=$(Get-Content .secrets/gmail_token_b64.txt -Raw)" -s aleksandra-worker --skip-deploys'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
