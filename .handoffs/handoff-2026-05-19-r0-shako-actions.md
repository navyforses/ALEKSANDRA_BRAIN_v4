# Handoff — R0 Shako Actions (2026-05-19)

**Status:** R0 code/commits ✅ DONE (5 atomic commits landed on `main` locally).
Remaining R0 work is UI-only and needs you in Vercel + Railway dashboards.
After your 5 actions below, the system goes from 73/78 verifier coverage and
🔴 Vercel down + 🔴 n8n dead → 78/78 + Phase 4 acceptance window unblocked.

---

## What I (Claude) did in this session

Five atomic commits on `main` (local, NOT pushed yet — see "Push decision" below):

1. **`de4469a`** — `fix(qdrant): propagate QDRANT_API_KEY across all scripts (closes CGM-01)`
   - 7 files: 5 already-modified + `scripts/rag/retrieve.py` new patch
   - **Re-ran `verify_phase3` → CGM-01 PASS, total 10/11** (REGR still cascades — auto-resolves after T-1 below)

2. **`5cd97ef`** — `feat(worker): add /fire-daily-batch + /render-weekly-brief endpoints`
   - Closes **RISK-02** (HIGH/HIGH from RISK_REGISTER.md): the 2 missing endpoints that Phase 4 workflows POST to. Without this, the Sunday Weekly Brief would silently 404.
   - Worker code lands BUT not yet deployed to Railway (your T-4 below)

3. **`7ae5358`** — `feat(phase-6): introduce Visualization MCP + swarm + archive sci-fi demos`
   - 33 files: `mcp/aleksandra_niivue_mcp.py` (with nibabel 3.x fix), `mcp/swarm_orchestrator.py`, `agents/swarm/*.py`, 13 archived HTML/JS demos moved to `.planning/research/visualization-demos/`, DESIGN.md, 3 small swarm fixtures, gitignored 3 large fixtures (>1 MB)

4. **`5d61f34`** — `docs(planning): land 2026-05-18 audit + AI agent team output`
   - The audit + 6-agent team output: REPAIR_PLAN, COMPLETION_PLAN, MASTER_PLAN, RISK_REGISTER, 3 INVESTIGATION-*, BRANCH_C_RESOLUTION + supporting docs

5. **`45a20a8`** — `feat(phase-6): introduce neuroimaging swarm scripts + brain_builder`
   - 18 files in `scripts/neuroimaging/` + `scripts/brain_builder_swarm.py` (with fabricated `vulnerability_to_hie` value replaced by `mock_intensity_factor: 0.0` placeholder + comment)

Also applied **without commit** (`.env` is gitignored):
- `.env` lines 142-145: added the 4 missing worker URL vars (all → `https://aleksandra-worker-production.up.railway.app`)

---

## What you (Shako) do next — 5 UI tasks (~60 min total)

### T-1. Vercel Root Directory fix (`viewer/`) → unblocks the viewer (2 min)

1. https://vercel.com/shakos-projects-82dad3f2/viewer/settings/general
2. Scroll to **Root Directory**. Currently blank.
3. Type `viewer` (no leading slash, no trailing slash). Save.
4. Wait 10 sec for Vercel to register the change.

### T-2. Add 3 env vars to Vercel viewer (~5 min)

1. https://vercel.com/shakos-projects-82dad3f2/viewer/settings/environment-variables
2. Add each, scope **Production** (plus Preview if you want):

   | Key | Value |
   |---|---|
   | `PHASE5_MANAGER_WORKER_URL` | `https://aleksandra-worker-production.up.railway.app` |
   | `PHASE5_VOICE_WORKER_URL` | `https://aleksandra-worker-production.up.railway.app` |
   | `PHASE5_WORKER_AUTH_TOKEN` | (copy from local `.env` line 141 — the 64-hex value) |

3. Confirm `MANAGER_USER_ID`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` are already set (from earlier deploys); add them if missing using values from local `.env`.

### T-3. Trigger Vercel redeploy (5 min wall-clock)

1. https://vercel.com/shakos-projects-82dad3f2/viewer/deployments
2. Most-recent ERROR deploy → **⋯** → "Redeploy"
3. Watch build log — expect `npm run vercel-build` to succeed (Next.js will now find `viewer/app/`)
4. After deploy READY, smoke test:
   - Open https://viewer-git-main-shakos-projects-82dad3f2.vercel.app/brain
   - Should show Next.js shell (logged-in via SSO). NOT `DEPLOYMENT_NOT_FOUND` or build-error page.

### T-4. Push 5 commits to `main` so Railway worker rebuilds (1 min Claude or 1 min Shako)

The worker code now has the 2 new endpoints. Railway auto-rebuilds on push to `main`.

**Option A (you):** `git push origin main` from the project dir.
**Option B (Claude):** ask Claude to push. It will wait for your green light because pushing to `main` is shared state.

After push:
- Railway will pull `45a20a8`, build new image, rotate the worker.
- Wait ~3 min, then smoke:
  ```
  curl -fsS https://aleksandra-worker-production.up.railway.app/healthz
  curl -fsS -X POST -H "Content-Type: application/json" -d '{"telegram":false}' \
       https://aleksandra-worker-production.up.railway.app/fire-daily-batch
  curl -fsS -X POST -H "Content-Type: application/json" -d '{"dry_run":true,"fixture":true}' \
       https://aleksandra-worker-production.up.railway.app/render-weekly-brief
  ```
  All three should return 200 JSON.

### T-5. n8n service Docker swap (~15 min, **HIGHEST-RISK** task)

This restores n8n itself. Currently the `n8n` Railway service is running our Python worker by mistake.

1. **PRE-FLIGHT (mandatory):** snapshot the postgres volume that holds workflow definitions.
   - https://railway.com/project/lucky-ambition
   - `postgres` service → Volumes tab → "Create snapshot"
   - Wait until snapshot is ready (~2 min). This is your safety net.

2. **Check the n8n service for its volume too:**
   - `n8n` service → Volumes tab — if a volume is mounted at `/home/node/.n8n`, snapshot it.
   - If NO volume is mounted there, n8n's encryption key is lost — workflows survive in postgres but credentials (Telegram/Gmail OAuth) will need re-auth after the swap.

3. **Verify the encryption-key env var exists** (CRITICAL):
   - `n8n` service → Variables tab → look for `N8N_ENCRYPTION_KEY`
   - If set: write down the value (safely) so you can re-paste after swap.
   - If unset: credentials in postgres are encrypted with a key only the running n8n process knows; the swap will lose this. n8n will fail to read credentials and you'll need to re-add them post-swap.

4. **The swap itself:**
   - `n8n` service → Settings → Source → "Change source" → choose "Docker Image"
   - Enter `n8nio/n8n:latest`
   - In the "Build" section, clear `Dockerfile.worker` if it's still referenced.
   - Save.
   - Variables tab: ensure these are set:
     - `N8N_HOST=n8n-production-48c7.up.railway.app`
     - `N8N_PROTOCOL=https`
     - `WEBHOOK_URL=https://n8n-production-48c7.up.railway.app/`
     - `GENERIC_TIMEZONE=UTC`
     - `N8N_ENCRYPTION_KEY=<the value from step 3>`
   - Deploy.

5. **Verify (~5 min after deploy):**
   ```
   curl -sI https://n8n-production-48c7.up.railway.app/
   ```
   Should return HTML with n8n login markup (NOT `{"service":"perception_worker"}`).

   ```
   curl -H "X-N8N-API-KEY: $N8N_API_KEY" \
        https://n8n-production-48c7.up.railway.app/api/v1/workflows | jq '.data | length'
   ```
   Should return `11`.

6. **Activate the inactive workflows** (n8n UI):
   - Log into https://n8n-production-48c7.up.railway.app
   - Workflows tab → toggle ON for: `perception_6h`, `daily_digest`, `daily_spend_report`, `chunking_trigger`, `extraction_trigger`, `urgent_alerts`
   - (4 are already active per disk flag: `daily-budget-gate`, `manager_briefing`, `outreach_review_queue`, `telegram_daily_digest`, `weekly_brief`. Verify they're alive.)

7. **Fire `daily_digest` manually once** (closes Phase 2.5 C.3 cascade → verify_phase3 goes from 10/11 to 11/11, verify_phase4/5 REGR also clears):
   - Workflows → `daily_digest` → "Execute Workflow" once.

8. **Verify the resolution end-to-end:**
   ```
   .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase3
   ```
   Expected: **11/11 PASS** (CGM-01 + REGR both GREEN now).

---

## After T-1 through T-5 done

Run this from the project dir for the full R0 close-out:

```bash
# Verifiers — expect 10/10 + 19/19 + 16/16 + 11/11 + 9/9 + 13/13 = 78/78
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase1
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2_5
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase3
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase4 --mode code-complete
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase5 --mode code-complete

# Cloud probes
curl -fsS https://aleksandra-worker-production.up.railway.app/healthz
curl -sI https://n8n-production-48c7.up.railway.app/ | head -3
curl -fsS -o /dev/null -w "%{http_code}\n" https://viewer-git-main-shakos-projects-82dad3f2.vercel.app/brain
```

If all 6 verifiers GREEN + all 3 curls return expected values → **R0 done.** Phase 4 acceptance window starts ticking from there. C2 soak is the next ~14 days.

---

## Push decision (for T-4 and beyond)

The 5 commits are LOCAL only. They won't trigger Railway/Vercel rebuilds until pushed. **I held back on pushing because pushes to `main` are shared-state and I want your explicit OK first.**

When you're ready: tell Claude "push the commits" or run `git push origin main` yourself.

---

## Decision B (Vercel SSO gate) — separate question

Per MASTER_PLAN.md §5 Branch B, the family currently CAN'T see the viewer because of Vercel SSO (returns 401 to non-logged-in browsers). After T-3 succeeds, you'll see the same 401 for your wife / clinician.

S1 recommended **B.2 — Vercel team-seat invites** (free on Hobby tier, up to 3 seats):
1. https://vercel.com/teams/shakos-projects-82dad3f2/settings/members
2. Invite: Sopo's Gmail + clinician's Gmail. Role = "Member".
3. They sign in with Google to view the viewer.

Alternative: **B.1 make project public** — Vercel UI → Settings → Deployment Protection → Disable. Risk: world-readable Aleksandra metadata. Use ONLY if SSO is unacceptable AND no PHI/identifying data appears in the viewer.

---

## Open follow-ups (NOT R0; defer to R2/C-phases)

| ID | Item | Phase |
|---|---|---|
| R2.1 | Update CLAUDE.md "მიმდინარე ეტაპი" to reflect 78/78 truth + repair commits | R2 |
| R2.2 | Refresh `RAILWAY_API_TOKEN` (current returns Not Authorized) | R2 |
| R2.3 | Decide `aleksandra-brain-v4.vercel.app` alias question — runbook references it but it doesn't exist | R2 |
| C1 | Phase 5 production smoke (voice/PDF/email-intent on the viewer) | next-day after T-1..T-5 |
| C2 | 14-day Phase 4 acceptance soak | calendar-bound |
| - | Decide Git LFS vs regenerate-on-demand for 3 large fixture JSONs (24M + 15M + 1.4M) | low priority |

---

*Handoff written by Claude after R0 code+commit execution, 2026-05-19. Next step: Shako runs T-1 through T-5; verify; push commits.*
