# Phase 5 Operator Runbook — BRAIN AI Manager Assistant activation

> **Audience:** Shako (non-programmer operator).
> **Goal:** Take Phase 5 from "engineering complete" to "live in production".
> **Time:** ~45 minutes total, split into 4 independent steps. Steps 1 and 2 are required; 3 unlocks voice; 4 is recommended for accuracy.

---

## Prerequisites (already done in Phase 4 Step B)

- ✅ Supabase project + `.env` with `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_URL`
- ✅ Telegram bot + `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- ✅ Notion integration + `NOTION_API_KEY`, `NOTION_DATABASE_ID`
- ✅ Migration 011 applied (intake_drops + manager_actions tables exist)

Run this sanity check from the repo root before continuing:

```bash
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase5 --mode code-complete
# Expected: 13/13 PASS — ALL GREEN
```

---

## Step 1 — Add `MANAGER_USER_ID` to `.env` (required)

The BRAIN panel needs to know who the single operator is so every `manager_actions` row tags the right person. Phase 5 ships with a hardcoded default (`shako-jincharadze`) — you only need to override if you want a different id.

**Open `.env`** in your editor and add the line:

```
# Phase 5 single-operator id (Phase 5 plan §"Pre-decisions §4")
MANAGER_USER_ID=shako-jincharadze
```

No restart needed for any service that reads from `.env` directly (scripts/manager/*).

---

## Step 2 — Deploy the Python manager worker on Railway (required)

Phase 5's voice transcription, apply-actions, undo, morning briefing, and email-intent all live in `scripts/perception_worker.py`. The Next.js routes forward to it via `PHASE5_MANAGER_WORKER_URL`. Until you deploy, those routes return `HTTP 503 manager_worker_not_deployed` — the BRAIN panel surfaces this as a friendly message.

**Option A — reuse the existing `perception_worker` Railway service:**

If you already have `perception_worker` deployed on Railway (Phase 2.5B), it now serves the Phase 5 endpoints too. Just add these env vars in the Railway → Variables panel:

```
OPENAI_API_KEY=sk-...                  # for voice transcription
MANAGER_USER_ID=shako-jincharadze      # matches your .env
PHASE5_WORKER_AUTH_TOKEN=<random 32-char hex>   # optional but recommended
```

Then in Vercel (or wherever the Next.js viewer is hosted) add:

```
PHASE5_MANAGER_WORKER_URL=https://<your-railway-app>.up.railway.app
PHASE5_WORKER_AUTH_TOKEN=<same as Railway>
```

**Option B — spin up a fresh Railway service:**

Same `perception_worker.py` codebase, separate service. Railway → New Service → Deploy from GitHub → select this repo → Start Command: `python -m scripts.perception_worker`. Add the env vars above plus the Phase 2.5B ones (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, etc.).

**Smoke test from your laptop:**

```bash
curl -X POST https://<railway-url>/morning-briefing \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: <PHASE5_WORKER_AUTH_TOKEN>" \
  -d '{"dry_run": true}'

# Expected: JSON body with "word_count" <= 50 and "telegram_message_id": null
```

---

## Step 3 — Enable voice input (optional but high-value)

Voice is the single highest-leverage Phase 5 feature for clinic visits. Setup is two env vars.

### 3a — OpenAI API key

1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the `sk-...` string

### 3b — Add to `.env` AND Railway

```
OPENAI_API_KEY=sk-...
```

Add the same line to Railway → Variables and redeploy.

**Smoke test (~$0.0001 per call):**

```bash
PHASE5_LLM_TESTS=1 OPENAI_API_KEY=sk-... \
  .venv/Scripts/python.exe -X utf8 -m pytest tests/test_intake_voice.py::test_whisper_silent_clip_smoke -v

# Expected: PASSED — Whisper accepts the synthetic silent WAV.
```

**Voice budget:** $0.006/minute. 50 minutes of voice per month = $0.30. Well inside the $15 Phase 5 cap.

---

## Step 4 — Install Tesseract OCR (recommended but optional)

Tesseract is the FAST path for medication-label photos. Without it, the system falls back to Claude vision (works but costs ~$0.005 per photo vs $0).

**Windows install:**

1. Download installer from https://github.com/UB-Mannheim/tesseract/wiki
2. Run `tesseract-ocr-w64-setup-5.x.x.exe`
3. Install to the default location: `C:\Program Files\Tesseract-OCR\`
4. Add this line to your `.env`:

```
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

**macOS install:**

```bash
brew install tesseract
# No TESSERACT_PATH needed — Homebrew puts tesseract on PATH.
```

**Linux install:**

```bash
sudo apt-get install tesseract-ocr  # Debian/Ubuntu
# or
sudo yum install tesseract           # RHEL/CentOS
```

**Smoke test:**

```bash
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_intake_ocr.py::test_tesseract_reads_med_label -v

# Expected: PASSED — Tesseract reads "VIGABATRIN" from the synthetic label.
```

If you skip Tesseract: nothing breaks. Set `PHASE5_LLM_TESTS=1` and the vision-fallback OCR test will exercise the Claude path instead.

---

## Health checks

Once Steps 1, 2 (and optionally 3 + 4) are done, walk through this checklist to confirm everything is wired:

```bash
# 1. Local verifier still green
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase5 --mode code-complete
# Expected: 13/13 PASS

# 2. Worker reachable
curl -s https://<railway-url>/healthz
# Expected: {"status": "ok", "service": "perception_worker"}

# 3. Voice round-trip (only if Step 3 done)
PHASE5_LLM_TESTS=1 .venv/Scripts/python.exe -X utf8 -m pytest tests/test_intake_voice.py -v
# Expected: 7/7 PASS

# 4. Morning briefing dry-run
curl -X POST https://<railway-url>/morning-briefing \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $PHASE5_WORKER_AUTH_TOKEN" \
  -d '{"dry_run": true}'
# Expected: JSON body with text starting "Good morning. • Today:"

# 5. Email-intent dry-run
curl -X POST https://<railway-url>/email-intent \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $PHASE5_WORKER_AUTH_TOKEN" \
  -d '{"text": "write to Sydney about Duke timing", "dry_run": true}'
# Expected: JSON body with "matched": true, "intent": {...}
```

---

## What to expect after activation

| Trigger | Expected outcome |
|---|---|
| Open the viewer in browser | BRAIN panel mounts on every page; activity feed shows recent actions |
| Type "write to Sydney about Duke timing" in BRAIN input | Gmail draft staged within ~3 s; never auto-sent |
| Hold the voice button + speak | ≤ 2 s after release: transcript appears; no audio uploaded |
| Drop a BMC discharge PDF into BRAIN | Preview cards (typically 3-5 actions) appear; "Apply selected" writes to timeline + therapies |
| Click "Undo" on an action ≤ 24 h old | Pre-image restored; audit log shows the reverse row |
| Sunday 09:00 ET arrives | Telegram pings with a 3-bullet ≤ 50-word briefing |

---

## Troubleshooting

| Symptom | Diagnosis | Fix |
|---|---|---|
| "voice_worker_not_deployed" in BRAIN | `PHASE5_MANAGER_WORKER_URL` empty in Vercel | Set the env var, redeploy |
| "manager_worker_not_deployed" on Apply | Same | Same |
| Voice button shows "Retry" | OpenAI key invalid OR audio MIME unsupported | Re-paste key, check browser console for the MIME |
| Tesseract test SKIPPED | Tesseract binary not on PATH and `TESSERACT_PATH` empty | Step 4 |
| Morning briefing didn't fire Sunday | n8n workflow not activated in n8n cloud | Activate `manager-morning-briefing` workflow in n8n UI |
| Activity feed shows "unreachable" | Supabase REST credentials missing in viewer env | Re-paste `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` in Vercel |

---

## When this runbook is "done"

You'll know Phase 5 is fully live when:

1. Step 1 + Step 2 are done.
2. The BRAIN panel renders without "503" banners.
3. A real morning briefing lands in your Telegram on the next Sunday at 09:00 ET.
4. `verify_phase5 --mode production` (default) flips from "RED on natural-data gates" to "all 13 PASS" — typically after the first real PDF drop / voice memo / email intent / Sunday briefing.

That last step is **not engineering work**. It happens organically as you use the system.
