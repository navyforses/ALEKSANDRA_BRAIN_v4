# Phase 4 Operator Runbook — Step B Activation

**For:** Shako · მხოლოდ შენი ხელით
**Time budget:** ~1.5 hours total
**Output:** `verify_phase4 --mode production` 9/9 PASS; 14-day acceptance window opens at first Weekly Brief delivery (Sunday 2026-05-24 09:00 ET)
**Pre-condition:** `verify_phase4 --mode code-complete` is already 9/9 (Day 7 close)
**Cross-refs:** [PHASE_4_EXIT_REPORT.md](PHASE_4_EXIT_REPORT.md) · [PHASE_4_COMPLETION_KA_FINAL.md](PHASE_4_COMPLETION_KA_FINAL.md) · [RUNBOOK-notion-api.md](RUNBOOK-notion-api.md)

---

## Why this runbook is separate from the engineering sprint

Phase 4 engineering closed Day 7 with `verify_phase4 --mode code-complete` 9/9. Five gates (BOOTSTRAP, FFV-01, FFV-03, FFV-04, FFV-05) are RED in production mode because production deliveries require **operator activation** — credentials only Shako can paste, n8n workflows only Shako should activate, real Telegram/Gmail sends that go to real recipients. The runbook below is the explicit list.

After Step B, the system is live. Day 1 of the 14-day acceptance window begins at the first Weekly Brief on Sunday 2026-05-24 09:00 ET.

---

## Step 1 — Notion bootstrap (~30 min)

**What it does:** creates a Notion database under the "Aleksandra Brain Family" page, gives the `ALEKSANDRA_BRAIN` integration access, captures the secret key + database ID so the archiver can write rows.

**Prerequisite:** A Notion workspace where you can create a database. The page that will be the parent should already be shared with the `ALEKSANDRA_BRAIN` integration. The runbook for the integration setup is [docs/RUNBOOK-notion-api.md](RUNBOOK-notion-api.md).

```powershell
# from repo root, with .venv activated
.venv\Scripts\Activate.ps1
python scripts/notion_bootstrap.py
```

The script prompts for:
- the **parent page URL or ID** (the page that hosts the new database)
- the **integration secret** (paste from Notion → Integrations → ALEKSANDRA_BRAIN → Internal Integration Secret)

On success it prints two lines:

```
NOTION_API_KEY=secret_XXXX...
NOTION_DATABASE_ID=YYYY-YYYY-YYYY-YYYY...
```

Paste both lines into `.env` (do **not** commit `.env`; it is gitignored).

Sanity check:
```powershell
python -c "import os; from scripts.ledger import load_env; load_env(); print('API_KEY set:', bool(os.environ.get('NOTION_API_KEY'))); print('DB_ID set:', bool(os.environ.get('NOTION_DATABASE_ID')))"
```
Both should print `True`.

Run the BOOTSTRAP gate only:
```powershell
.venv\Scripts\python.exe -X utf8 -m scripts.verify_phase4 --gate bootstrap --mode production
```
Expected: `BOOTSTRAP PASS database_id=YYYY...  title='Aleksandra Brain Findings'` (or whatever you named the database).

---

## Step 2 — Import + activate 5 n8n workflows (~1 hour)

**What it does:** loads 5 workflow JSON files into n8n, attaches the right credentials, and toggles each to Active.

Open n8n web UI (URL from `.env` `N8N_URL`). Log in.

For each of the 5 files below, in n8n:

1. Workflows → Import from File → select the JSON
2. After import, click "..." → Edit
3. For each `n8n-nodes-base.httpRequest` node that uses `$env.PERCEPTION_WORKER_URL` → confirm the env var is populated in n8n Settings → Environment Variables. (It should already be from Phase 2.5B.)
4. For `n8n-nodes-base.telegram` or Telegram HTTP nodes → attach the **Telegram Bot API** credential (`aleksandra_brain_bot`).
5. For Gmail nodes → attach the **Gmail OAuth2** credential (the family Gmail you bootstrapped in Phase 3 Day 5).
6. Toggle the workflow Active (top-right switch).

| # | File | Cron / trigger | Credentials needed |
| --- | --- | --- | --- |
| 2.1 | `workflows/daily_digest.json` | Daily 09:00 ET | Telegram |
| 2.2 | `workflows/urgent_alerts.json` | Every 5 min poll | Telegram |
| 2.3 | `workflows/weekly_brief.json` | Sunday 09:00 ET | Telegram + Gmail |
| 2.4 | `workflows/outreach_review_queue.json` | Daily 08:30 ET | (none — internal n8n only) |
| 2.5 | `workflows/daily_spend_report.json` | Daily 08:00 ET (12:00 UTC) | (none — Telegram via Railway worker) |

After each is Active, run a manual test trigger from n8n's workflow editor ("Execute Workflow" button). Watch the execution log:

- 2.1 — should send a test Telegram message to family channel summarising any T2/T3 alerts queued (likely empty today; that's fine — message is "no notable updates").
- 2.2 — should run, find no pending T1 alerts, complete in <1 s.
- 2.3 — Sunday-only cron; manual fire will render a brief for the current week. Expected: Telegram link to Notion page + Gmail draft + Notion archive page.
- 2.4 — should query outreach_log, find Duke DTRI draft from Phase 3 Day 5, log it.
- 2.5 — should POST to Railway worker `/daily-spend-report`, produce the same 3-line Georgian Telegram message you already saw Day 5.

---

## Step 3 — Clean up n8n duplicates (~5 min)

n8n currently contains 3 copies of `daily-budget-gate`. Only one is wired correctly:

| ID | Status | Action |
| --- | --- | --- |
| `sxybeuJEkttHsvAH` | Active ✅ | Keep |
| `DzfpbJV7sdxMgiDD` | Inactive | Delete |
| `WNugyqUu3sfrHQR4` | Inactive | Delete |

Right-click each inactive copy → Delete.

---

## Step 4 — Production smoke drill (~15 min)

Once Steps 1-3 are done:

```powershell
# Force-trigger one daily_digest fire
# (n8n: Workflows → daily-digest → Execute Workflow)

# Verify it landed:
.venv\Scripts\python.exe -X utf8 -c "
import os, psycopg2
from scripts.ledger import load_env
load_env()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'], sslmode='require')
cur = conn.cursor()
cur.execute('SELECT id, tier, delivered_at, originating_run_id FROM alerts_log ORDER BY created_at DESC LIMIT 3')
for r in cur.fetchall():
    print(r)
"
```

Confirm the most recent alerts_log row has:
- `delivered_at` populated
- `originating_run_id` non-NULL (links back to the n8n trigger row)

Force-trigger one `weekly_brief` execution. Confirm:
- New Gmail draft visible in Drafts folder (don't send — Shako sends manually)
- New Notion page in the Aleksandra Brain Findings database
- Telegram message with link to the Notion page

---

## Step 5 — Verify Step B closed

```powershell
.venv\Scripts\python.exe -X utf8 -m scripts.verify_phase4 --mode production
```

Expected output:
```
  1  BOOTSTRAP   PASS    database_id=... title=...
  2  FFV-01      PASS    workflow=True smoke=True prod_t1_delivered=1
  3  FFV-02      PASS    (quiet hours)
  4  FFV-03      PASS    smoke=True workflow_extended=True prod_weekly_drafts=1
  5  FFV-04      PASS    notion_pages=1
  6  FFV-05      PASS    smoke=True prod_clinician_drafts=1
  7  OBS-02      PASS    recent_linked_digests>=1
  8  OBS-03      PASS    latest_spend_report=<today>
  9  REGR        PASS    11/11
  9/9 PASS  —  ALL GREEN
```

If any gate is still RED, re-check the corresponding workflow in n8n — most likely cause is the credential attachment didn't take.

---

## Step 6 — Open the 14-day acceptance window

Run once, just to record the milestone:

```powershell
.venv\Scripts\python.exe -X utf8 -c "
import os, psycopg2
from datetime import datetime, timezone
from scripts.ledger import load_env
load_env()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'], sslmode='require')
conn.autocommit = True
cur = conn.cursor()
now = datetime.now(timezone.utc)
cur.execute(\"\"\"INSERT INTO runs (kind, agent_id, start_time, end_time, token_cost, tokens_input, tokens_output, exit_status, exit_reason)
                VALUES ('phase_4_acceptance_window_opened', 'operator', %s, %s, 0, 0, 0, 'sent', 'Step B complete; 14-day window opens at first Weekly Brief 2026-05-24 09:00 ET') RETURNING id\"\"\", (now, now))
print('window opened:', cur.fetchone()[0])
"
```

---

## During the 14-day window (no engineering work, only observation)

What to watch:

- **Telegram daily 09:00 ET digest** lands every morning
- **T1 urgent alerts** break through quiet hours when they happen
- **Sunday Weekly Brief** with PDF in Gmail drafts + Notion page + Telegram link
- **08:00 ET daily spend report** in Telegram
- **Outreach drafts** for clinicians appear in Gmail drafts — review and send manually

What to flag for Shako review:
- Any digest that surfaces a **credible treatment lead** you would not have found via ChatGPT + Google Scholar in the same window
- Any draft that wants to go to a real clinician — your manual send only
- Any spend day > $5 (cap is $1.50/day; rare exceptions are fine, run a check)

What to NOT do:
- ❌ Do not modify `data/patient_context.yaml` mid-window (changes patient context version, breaks PDF reproducibility)
- ❌ Do not auto-send any Gmail draft — manual review is the trust gate
- ❌ Do not approve any draft that suggests a specific medical action ("should take X") — every draft must be informational only

---

## After the 14-day window closes (~2026-06-07)

One of three outcomes — your call:

| Outcome | What it means | Phase 5 routing |
| --- | --- | --- |
| 🟢 **PASS** | ≥ 1 credible treatment lead surfaced, with full source provenance, that ChatGPT + Google Scholar would not have produced in the same window. Total spend < $30. | Phase 5 = **VIS-*** (3D NiiVue digital twin) |
| 🟡 **PARTIAL** | Daily/weekly digests fire reliably, sources are clean, but no real "I would not have found this" moment occurred. | Phase 5 = **CGF-*** (cross-disease pattern + Adaptive GoT falsifier) |
| 🔴 **FAIL** | Workflows not delivering reliably, PHI bleed, budget breach, or other systemic failure. | Diagnose first; no Phase 5 |

Whatever the outcome, append a one-paragraph human note to `.handoffs/` with the verdict and any anecdotal observations. That becomes the Phase 5 plan-phase input.
