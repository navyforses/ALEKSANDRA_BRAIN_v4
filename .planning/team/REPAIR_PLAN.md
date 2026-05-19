# ALEKSANDRA_BRAIN — System Repair Plan (R0..R3)

**Agent:** D1 (Wave 2)
**Date:** 2026-05-18
**Inputs:** `.planning/AUDIT_2026-05-18.md`, `.planning/team/INVESTIGATION-OPS.md`, `.planning/team/INVESTIGATION-CGM01.md`, `git status --short` (run 2026-05-18)
**Out of scope:** Phase 6 (Visualization) — that is D2's `COMPLETION_PLAN.md`.

---

## §1. Context

Per audit §1 (executive summary matrix), the system is in a four-way broken state simultaneously: (a) the Vercel viewer has been in `ERROR` on every deploy since `f4b8d72` removed the root `package.json` — `Build error: Couldn't find any 'pages' or 'app' directory` — because the Vercel project's "Root Directory" still points at the repo root while the Next.js app lives in `viewer/` (audit §4.6); (b) the Railway `n8n` service is no longer running n8n — `GET /` returns `{"service":"perception_worker"}` and `GET /api/v1/workflows` returns 404 (audit §4.5), so all 11 cron workflows on disk are inert; (c) `verify_phase3` CGM-01 fails with a Qdrant 403 because `scripts/rag/retrieve.py:139-143` is the one remaining Qdrant call site that does not pass `QDRANT_API_KEY` (INVESTIGATION-CGM01 call stack + drift audit); (d) four worker-URL env vars consumed by 5 of the 11 workflows are missing from `.env` and Vercel (audit §5).

"Repaired" means, in order of priority: (R0) audit cell column "Production traffic" turns from 🔴/🟡 to 🟢 for Phases 1–5 — Vercel returns a valid Next.js shell on `/brain`, n8n serves its REST API and lists all 11 workflows, `verify_phase3` reports CGM-01 PASS, and the 6 modified-but-uncommitted files in `git status` land cleanly; (R1) the Phase 4 14-day acceptance window (closes ~2026-06-07) sees its first Sunday Weekly Brief write to `briefs` (currently 0 rows per audit §4.1) and Telegram T1 deliveries climb above zero; (R2) audit §6 doc-vs-reality deltas close and CLAUDE.md's "78/78 cumulative coverage" claim becomes true again; (R3) a re-run of the same audit produces 78/78 PASS with no new drift surfaced.

---

## §2. Repair roadmap

| Phase | Headline | Success criteria (objective, verifiable) | Dependency | ETA |
|---|---|---|---|---|
| **R0** | Tier 0 — unblock production | Vercel `/brain` returns 200 or 401-SSO with valid Next.js HTML shell (not build-error); n8n `/api/v1/workflows` lists 11 workflows; `verify_phase3 --json` shows CGM-01 PASS and total ≥ 10/11; `.env` contains 4 missing worker URLs; `git status --short` shows zero `M` lines under `scripts/`; one new commit on `main` advances HEAD | — | ~3 hrs Shako + ~1 hr Claude |
| **R1** | Tier 1 — Phase 4 acceptance window | 6 inactive workflows toggled active in n8n; daily_digest fires once; Supabase `select count(*) from briefs` ≥ 1 after Sunday 2026-05-24 13:00 UTC; `prod_t1_delivered ≥ 1`, `prod_weekly_drafts ≥ 1`, `prod_clinician_drafts ≥ 1` (Phase 4 OBS-02/OBS-03 counters from verify_phase4) | R0 complete | 14-day soak window (~2026-05-18 → 2026-06-07) |
| **R2** | Tier 2 — hardening | All 7 audit Tier 2 items closed; CLAUDE.md "მიმდინარე ეტაპი" reflects audit reality; 6 missing-table decisions made; fresh `RAILWAY_API_TOKEN` returns `me { name email }` over GraphQL; stale CF Worker `aleksandrabrane4` deleted | R0 | ~1.5 hrs |
| **R3** | Drift watch — re-audit | Re-running the same probes from audit §8 methodology trail produces 78/78 PASS (10+19+16+11+9+13) on the 6 verifiers and 0 new doc-vs-reality deltas in §6 | R0 + R1 + R2 | continuous, formal re-audit at 2026-06-07 |

---

## §3. R0 executable plan

Each task below is atomic — ONE git commit or ONE infra-side UI action with no commit. Multi-step tasks have been split.

### Task R0.1 — Set Vercel project Root Directory to `viewer`
- **From:** INVESTIGATION-OPS T0-1; AUDIT §4.6
- **File / location:** Vercel UI → Project `viewer` (`prj_pOGHJR8Hr3ACxFr2IOzAi8S1lkhm`) → Settings → General → Root Directory
- **Exact action:** Set value to `viewer` (no leading slash, no trailing slash). Click Save. No root `vercel.json` exists at the repo root (confirmed via Glob in this investigation — only `external-skills/open-design/vercel.json` exists, scoped to that subdir); no `viewer/vercel.json` either (confirmed via Glob). Root Directory is the sole authoritative knob.
- **Time:** 2 min
- **Commit:** none (Vercel UI change)
- **Verify:** field shows `viewer` after save + reload of Settings page
- **Owner:** Shako

### Task R0.2 — Trigger fresh Vercel deploy
- **From:** INVESTIGATION-OPS T0-2; AUDIT §4.6
- **File / location:** Vercel UI → Project `viewer` → Deployments → most recent ERROR deploy → "⋯" menu → Redeploy. Alternative: `git commit --allow-empty -m "chore(deploy): bump for root-dir fix" && git push origin main`.
- **Exact action:** Click Redeploy. Watch build logs — expect `npm run vercel-build` to run inside `viewer/` and succeed (Next.js will now find `viewer/app/`).
- **Time:** ~6 min wall-clock (5 min build + 1 min UI)
- **Commit:** optional empty commit if redeploy via push
- **Verify:** `curl -fsS -o /dev/null -w "%{http_code}" https://viewer-git-main-shakos-projects-82dad3f2.vercel.app/brain` returns `200` or `401` (SSO). API probe: `GET https://api.vercel.com/v6/deployments?projectId=prj_pOGHJR8Hr3ACxFr2IOzAi8S1lkhm&limit=1` shows `state: READY`. Body sample contains Next.js HTML shell (`<div id="__next">` or equivalent), **not** the current `DEPLOYMENT_NOT_FOUND` / build-error page.
- **Owner:** Shako

### Task R0.3 — Add 4 worker-URL env vars to local `.env`
- **From:** INVESTIGATION-OPS T0-3; AUDIT §5, §4.7
- **File:** `c:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\.env`
- **Exact action:** Append below line 141 (`PHASE5_WORKER_AUTH_TOKEN=…`):
  ```
  PHASE5_MANAGER_WORKER_URL=https://aleksandra-worker-production.up.railway.app
  PERCEPTION_WORKER_URL=https://aleksandra-worker-production.up.railway.app
  PHASE4_DIGEST_WORKER_URL=https://aleksandra-worker-production.up.railway.app
  PHASE5_VOICE_WORKER_URL=https://aleksandra-worker-production.up.railway.app
  ```
- **Time:** 2 min
- **Commit:** none (`.env` is gitignored per the modified `.gitignore` line that R0.8 will commit)
- **Verify:** `grep -cE "^(PHASE5_MANAGER_WORKER_URL|PERCEPTION_WORKER_URL|PHASE4_DIGEST_WORKER_URL|PHASE5_VOICE_WORKER_URL)=" .env` returns `4`
- **Owner:** Claude (via Edit tool at execution time) or Shako manually

### Task R0.4 — Add 5 env vars to Vercel project
- **From:** INVESTIGATION-OPS T0-4; AUDIT §5, §4.6
- **File / location:** Vercel UI → Project `viewer` → Settings → Environment Variables → Add
- **Exact action:** Add the 3 keys the viewer code actually reads at runtime (per INVESTIGATION-OPS row T0-4: `viewer/lib/supabase.ts:53-54`, `viewer/app/api/manager/{apply,voice,email,audit,undo}/route.ts`): `PHASE5_MANAGER_WORKER_URL`, `PHASE5_VOICE_WORKER_URL`, `PHASE5_WORKER_AUTH_TOKEN`. Scope = Production (and optionally Preview). Values: the worker URLs go to `https://aleksandra-worker-production.up.railway.app`; `PHASE5_WORKER_AUTH_TOKEN` is the hex64 value already in `.env` line 141. Also confirm `MANAGER_USER_ID`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` are present from earlier deploys (audit §5 confirms they're in local `.env` lines 11, 13, 124 — add if missing in Vercel).
- **Time:** 7 min
- **Commit:** none (Vercel UI)
- **Verify:** After redeploy in R0.5: `curl -fsS https://viewer-git-main-…/api/manager/audit` returns 200 JSON (not 500 "MANAGER_USER_ID missing" or "PHASE5_WORKER_AUTH_TOKEN undefined")
- **Owner:** Shako

### Task R0.5 — Redeploy Vercel after env-var addition
- **From:** INVESTIGATION-OPS T0-4 (consequence of); AUDIT §4.6
- **File / location:** Vercel UI → Project `viewer` → Deployments → "⋯" → Redeploy
- **Exact action:** Trigger redeploy so the new env vars are baked into the build (Vercel does NOT pick up env-var changes automatically for an already-built deployment).
- **Time:** ~5 min wall-clock
- **Commit:** none
- **Verify:** New deploy `state: READY`; `curl -fsS https://viewer-git-main-…/api/manager/audit` → 200
- **Owner:** Shako

### Task R0.6 — Swap Railway `n8n` service source to Docker Image
- **From:** INVESTIGATION-OPS T0-5; AUDIT §4.5
- **File / location:** Railway UI → project owning `n8n-production-48c7` subdomain → service `n8n` → Settings → Source
- **Exact action:**
  1. **Pre-flight (mandatory):** verify the service has a persistent volume mounted at `/home/node/.n8n` and snapshot it (Railway → service → Volumes → "Create snapshot"). This volume holds n8n's SQLite/postgres + encryption key + credentials.
  2. Click "Change source" → choose "Docker Image" → enter `n8nio/n8n:latest`.
  3. Confirm Build section no longer references `Dockerfile.worker`. Root `railway.json` declares `"builder":"DOCKERFILE", "dockerfilePath":"Dockerfile.worker"` project-wide; Railway service-level Source overrides repo `railway.json` for that service only, so the `aleksandra-worker` service is unaffected. If the swap UI still shows the Dockerfile path, set it to blank or delete `railway.json` and use service-level configs everywhere.
  4. Set service env vars: `N8N_HOST=n8n-production-48c7.up.railway.app`, `N8N_PROTOCOL=https`, `WEBHOOK_URL=https://n8n-production-48c7.up.railway.app/`, `GENERIC_TIMEZONE=UTC`. Preserve any existing `N8N_ENCRYPTION_KEY` (this is the make-or-break secret; if it changes, credentials become unreadable).
  5. Deploy.
- **Time:** ~13 min (3 min snapshot + 5 min config + 5 min container pull/start)
- **Commit:** none
- **Verify:** `curl -sI https://n8n-production-48c7.up.railway.app/` returns HTML with `n8n` login markup (not `{"service":"perception_worker"}`). With `N8N_API_KEY` from `.env` line 68: `curl -H "X-N8N-API-KEY: $N8N_API_KEY" https://n8n-production-48c7.up.railway.app/api/v1/workflows | jq '.data | length'` returns `11`.
- **Owner:** Shako
- **Open Q (escalate to S1):** Was a volume mounted before the worker rebuild took over the service? If no, all 11 workflows + Telegram/Gmail OAuth credentials need re-import (audit §A.5 + INVESTIGATION-OPS open Q #3).

### Task R0.7 — Apply CGM-01 patch to `scripts/rag/retrieve.py`
- **From:** INVESTIGATION-CGM01 §"Proposed patch"; AUDIT §Phase 3
- **File:** `c:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\scripts\rag\retrieve.py`
- **Exact action:** Apply the Edit-tool patch from INVESTIGATION-CGM01.md lines 67-109 — modify `_qdrant_search` (lines 130-145) to read `api_key = os.environ.get("QDRANT_API_KEY")`, build `headers = {"api-key": api_key} if api_key else {}`, pass `headers=headers` into the `httpx.post(...)` call. `import os` is already on line 46 — no import change. This matches the HTTP-pattern fix already applied (uncommitted) in `verify_phase2.py` lines 95-100 and 299-309.
- **Time:** 3 min
- **Commit:** part of R0.8 (single batched commit covering all Qdrant API-key drift)
- **Verify:** `.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase3 --json | jq '.checks.cgm_01.passed'` → `true`. Manual probe: `.venv/Scripts/python.exe -c "from qdrant_client import QdrantClient; import os; q=QdrantClient(url=os.environ['QDRANT_URL'], api_key=os.environ['QDRANT_API_KEY']); print(q.search('papers', [0.0]*384, limit=1))"` returns a list (currently raises 403).
- **Owner:** Claude

### Task R0.8 — Commit Qdrant API-key drift fix
- **From:** INVESTIGATION-OPS T0-7; `git status --short` (verified 2026-05-18)
- **File / location:** local git working tree at repo root
- **Exact action:**
  1. Stage the 6 already-modified files + the new R0.7 patch — explicit paths only (do **NOT** `git add .` — 33 untracked Phase 6 scaffold files would enter this commit per audit §3):
     ```
     git add .gitignore scripts/setup_qdrant.py scripts/chunking/embedder.py scripts/chunking/retrofit_qdrant_stamps.py scripts/verify_phase2.py scripts/verify_phase2_5.py scripts/rag/retrieve.py
     ```
  2. Commit with Conventional Commits:
     ```
     fix(qdrant): propagate QDRANT_API_KEY across all scripts (closes CGM-01)
     ```
     Body: cite audit §Phase 3, INVESTIGATION-CGM01 drift-audit table.
  3. `git push origin main`.
- **Time:** 5 min
- **Commit:** YES — 1 commit, 7 files (6 modified + 1 new patch)
- **Verify:** `git status --short` shows zero `M` lines (untracked `??` lines stay; that's the Phase 6 backlog for D2). `git log -1 --stat` lists the 7 expected files. `git log -1 --format=%H` advances remote `main` by one commit.
- **Owner:** Claude

### Task R0.9 — Re-run verify_phase3 to confirm CGM-01 closed
- **From:** AUDIT §Phase 3; INVESTIGATION-CGM01 §"Verification"
- **File / location:** local terminal
- **Exact action:** `.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase3`
- **Time:** 3 min
- **Commit:** none (read-only verification)
- **Verify:** stdout includes `[PASS] CGM-01`. Total either **10/11** (if Phase 2.5 C.3 daily_digest dry-window still cascades into REGR — which is expected pre-R1) or **11/11** (if T1.2 has already fired). Either is acceptable for R0 exit.
- **Owner:** Claude

---

## §4. R0 end-to-end verification sequence

After R0.1 through R0.9 complete, run this sequence and capture each result. All five must pass for R0 done.

```bash
# 1. Vercel viewer alive on root
curl -fsS -o /dev/null -w "HTTP %{http_code}\n" https://viewer-git-main-shakos-projects-82dad3f2.vercel.app/
# Expected: HTTP 200 or HTTP 401 (SSO). NOT 500/404/build-error.

# 2. Vercel viewer alive on /brain
curl -fsS -o /dev/null -w "HTTP %{http_code}\n" https://viewer-git-main-shakos-projects-82dad3f2.vercel.app/brain
# Expected: HTTP 200 or HTTP 401.

# 3. Railway worker healthz (regression check — should still work)
curl -fsS https://aleksandra-worker-production.up.railway.app/healthz
# Expected: {"status": "ok", "service": "perception_worker"}

# 4. n8n restored (the big test)
curl -fsS https://n8n-production-48c7.up.railway.app/ | head -20
# Expected: HTML containing "n8n" (login page). NOT the JSON {"service":"perception_worker"}.
curl -fsS -H "X-N8N-API-KEY: $N8N_API_KEY" https://n8n-production-48c7.up.railway.app/api/v1/workflows | jq '.data | length'
# Expected: 11

# 5. CGM-01 fixed
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase3
# Expected: [PASS] CGM-01; total 10/11 or 11/11.

# 6. Commit landed on remote
git log --oneline origin/main -3
# Expected: top commit is "fix(qdrant): propagate QDRANT_API_KEY ..."
```

R0 is "done" only when all 6 probes pass. Capture stdout for each as the R0 exit evidence (analogous to audit §8 methodology trail).

---

## §5. Rollback strategies

| Task | If it breaks something, do this | Risk owner |
|---|---|---|
| **R0.1** Vercel Root Directory | Vercel UI → Settings → General → Root Directory → clear field (revert to blank/repo-root). Redeploy. Returns to current ERROR state but doesn't break anything new. | Shako |
| **R0.2** Vercel redeploy | Vercel UI → Deployments → previous deployment → "Promote to Production". Aliases re-point. | Shako |
| **R0.3** `.env` edits | Edit tool to remove the 4 appended lines, or `git checkout .env` (file is gitignored, but Shako keeps a manual backup). | Claude |
| **R0.4** Vercel env vars | Vercel UI → Settings → Environment Variables → delete the added rows. Redeploy. | Shako |
| **R0.5** Vercel redeploy | Same as R0.2 — promote previous good deploy. | Shako |
| **R0.6** n8n Docker swap | Railway service → Settings → Source → change back to GitHub repo + `Dockerfile.worker`. **Postgres volume retains workflow definitions regardless**; risk is **only** if `N8N_ENCRYPTION_KEY` is lost during the swap — credentials need re-auth. **Mitigation:** the pre-flight snapshot in R0.6 step 1 lets you restore the volume to its pre-swap state if anything goes wrong; verify the `N8N_ENCRYPTION_KEY` env var is the same value pre- and post-swap. | Shako (this is the highest-risk R0 task) |
| **R0.7** CGM-01 patch | `git revert HEAD` (assuming R0.8 has committed; otherwise `git checkout scripts/rag/retrieve.py`). Verifier returns to 9/11 baseline. | Claude |
| **R0.8** commit | `git revert HEAD` + `git push origin main`. All 7 files return to their pre-commit state. | Claude |
| **R0.9** verifier rerun | Read-only — nothing to roll back. | — |

---

## §6. R1 + R2 sketches

### R1 — Phase 4 acceptance window (depends on R0)

| ID | Headline | Success criterion | Dependency |
|---|---|---|---|
| R1.1 | Activate 6 inactive n8n workflows (`perception_6h`, `daily_digest`, `daily_spend_report`, `chunking_trigger`, `extraction_trigger`, `urgent_alerts`) | n8n REST `/api/v1/workflows` shows all 11 with `active=true` | R0.6 (n8n alive) |
| R1.2 | Manually fire `daily_digest` once | `verify_phase2_5 --json` C.3 → `recent_fire ≥ 1`; Phase 3/4/5 REGR → PASS | R1.1 |
| R1.3 | Sunday 2026-05-24 13:00 UTC first Weekly Brief | `select count(*) from briefs` ≥ 1 by 13:30 UTC Sunday | R1.1, R0.4 |
| R1.4 | Manager briefing fires Sunday 13:00 UTC | New `runs` row with `kind` matching manager_briefing + Telegram delivered | R1.1, R0.3 |
| R1.5 | `outreach_log` daily growth | Count climbs from 1; `max(created_at)` advances daily over 14 days | R0.6 (n8n active) |

### R2 — Hardening (depends on R0)

| ID | Headline | Success criterion | Dependency |
|---|---|---|---|
| R2.1 | Truth up CLAUDE.md "მიმდინარე ეტაპი" | `git diff CLAUDE.md` reflects audit §6 deltas: Phase 3 11/11 (post-R0.7), 641 entities (not 568), Vercel/n8n status accurate | R0 complete |
| R2.2 | Refresh `RAILWAY_API_TOKEN` | GraphQL `query { me { name email } }` returns 200 with name+email | — |
| R2.3 | Resolve `aleksandra-brain-v4.vercel.app` alias question | Either alias exists (`curl -I` → 200/401, not `DEPLOYMENT_NOT_FOUND`) or zero hits for `git grep "aleksandra-brain-v4"` after doc sweep | R0.5 |
| R2.4 | Triage 6 missing tables (`llm_call`, `citations`, `digest_to_run_link`, `telegram_history`, `email_log`, `firecrawl_calls`) | Each table either exists in Supabase via new migration `012_missing_tables.sql` OR has zero `git grep` references after dead-code removal | — |
| R2.5 | Reconnect `ANTHROPIC_USAGE_API_KEY` | n8n `daily-budget-gate` execution log shows real spend (not placeholder zero) | R0.6 |
| R2.6 | Reprocess ~200 ledger papers blocked by Anthropic 400 content-filter | Neo4j `MATCH (n) RETURN count(n)` ≥ 900 (currently 792); LLM spend ≤ $1 cap | R0.8 |
| R2.7 | Delete stale CF Worker `aleksandrabrane4` | CF dashboard no longer lists the worker | — |

---

## §7. Risk callouts

(S1 will materialize these into `RISK_REGISTER.md`.)

1. **HIGH — n8n encryption-key loss during R0.6 Docker swap.** If `N8N_ENCRYPTION_KEY` env var changes during the source swap or the volume detaches, all stored credentials inside n8n (Supabase service key, Telegram bot token, Gmail OAuth, NCBI key) become unreadable. **Mitigation:** R0.6 step 1 mandates a volume snapshot before changing source; R0.6 step 4 mandates preserving the existing key value. **Verification before swap:** confirm `N8N_ENCRYPTION_KEY` is set as a service env var and copy its value to a safe location. If post-swap n8n login page loads but credentials are dimmed/error on test execution, restore from snapshot.

2. **HIGH — `PHASE4_DIGEST_WORKER_URL` points at a worker that does not implement the expected endpoints.** Audit §4.7 inventory shows `telegram_daily_digest.json` POSTs to `{{$env.PHASE4_DIGEST_WORKER_URL}}/fire-daily-batch` and `weekly_brief.json` POSTs to `{{$env.PHASE4_DIGEST_WORKER_URL}}/render-weekly-brief`. The worker's actual endpoint inventory (confirmed by enumerating `scripts/perception_worker.py` lines 120-128 during this investigation) is exactly 9 routes: `/perception-tick`, `/chunking-tick`, `/extraction-tick`, `/daily-spend-report`, `/voice-transcribe`, `/apply-actions`, `/undo-action`, `/morning-briefing`, `/email-intent`. **Neither `/fire-daily-batch` nor `/render-weekly-brief` exists in the worker.** After R0.6 + R1.1 these two workflows will fire and return 404 from the worker — Phase 4 T1/Weekly Brief will silently fail. **Mitigation:** before R1.1 activation, either (a) add the two missing endpoints to `perception_worker.py` as a follow-up patch (~30 LOC each, both already implemented in the legacy `scripts/render_weekly_brief.py` etc.) or (b) deploy a separate digest worker. Escalate to S1.

3. **MEDIUM — `viewer/next.config.ts` may need rewrites/redirects updates after Root Directory change.** Glob confirms `viewer/next.config.ts` exists; if it currently references paths relative to the repo root (e.g. `../something`) those will now resolve incorrectly. **Mitigation:** R0.2 build logs will surface any such error; R0.7 read of the file pre-deploy is cheap.

4. **MEDIUM — Vercel viewer-side env vars must include both `PHASE5_*` and `NEXT_PUBLIC_*` variants for any value read client-side.** Audit §5 lines 11-16 already shows `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are duplicated. INVESTIGATION-OPS row T0-4 confirms the 3 keys read at runtime by viewer code are server-only (`PHASE5_MANAGER_WORKER_URL`, `PHASE5_VOICE_WORKER_URL`, `PHASE5_WORKER_AUTH_TOKEN` — all in `app/api/manager/*/route.ts`), so no `NEXT_PUBLIC_` variant is needed. **Mitigation:** none required; this is documented for completeness.

5. **MEDIUM — `MANAGER_USER_ID=shako-jincharadze` is a string, not a UUID.** Audit §5 line 124 shows the literal value. Phase 5 `manager_actions` table writes user_id; if the column is `uuid` type, R0.4 inserting this into Vercel will produce 500 errors on every Phase 5 action. **Mitigation:** before R0.4 commit, query Supabase `\d manager_actions` (or `select column_name, data_type from information_schema.columns where table_name='manager_actions' and column_name='user_id'`) — if `uuid`, generate a real UUID for Shako and update `.env` line 124 + Vercel env. Escalate to S1.

6. **LOW — Bulk `git add` could pull in 33 untracked Phase 6 scaffold files.** Audit §3 shows 5,073 LOC across 33 untracked files. **Mitigation:** R0.8 mandates explicit path-list staging (7 paths). Do NOT use `git add .` or `git add -A`.

7. **LOW — Vercel SSO gate on `viewer-git-main-…` makes external smoke probes return 401 instead of a real 200.** The 401 with a valid Next.js HTML shell IS the success signal (audit §4.6 confirms this is the production alias behaviour). External CI cannot distinguish SSO-401 from auth-failure-401 without browser-side login. **Mitigation:** the §4 verification sequence accepts 401 as PASS; for definitive verification Shako opens the URL in a logged-in browser.

8. **LOW — `aleksandra-brain-v4.vercel.app` referenced in `docs/PHASE_5_OPERATOR_RUNBOOK.md` and `.claude/plans/5-warm-crown.md` Phase E does not exist as a Vercel alias** (audit §4.6 confirms `DEPLOYMENT_NOT_FOUND`). Operators following the runbook will hit a dead URL. **Mitigation:** R2.3 — either add the alias or sweep all doc references to the actual stable alias. Not blocking for R0 but creates onboarding friction.

---

## §8. Open questions (escalate to S1)

Carrying forward INVESTIGATION-OPS open questions §"Open questions for Wave 2" plus 2 new from this plan:

1. **(OPS Q1)** `aleksandra-brain-v4.vercel.app` — assign as real alias (R2.3 path a) or sweep all docs to actual alias (R2.3 path b)? S1 to decide.
2. **(OPS Q2)** `railway.json` scope vs Docker Image source for R0.6 — Railway service-level source overrides repo `railway.json` per public docs, but worth a 1-line confirmation from Railway support or a test before flipping the n8n service. S1 to flag for Shako.
3. **(OPS Q3)** Does the existing Railway `n8n` service have a persistent volume at `/home/node/.n8n` from before the worker rebuild? If yes, credentials may survive; if no, all 11 workflows + Telegram/Gmail OAuth need re-import. S1 to ask Shako to check Railway service → Volumes tab before R0.6.
4. **(OPS Q4)** Missing-tables triage (R2.4): are `llm_call` / `citations` / `digest_to_run_link` / `telegram_history` / `email_log` / `firecrawl_calls` aspirational (need migration `012_missing_tables.sql`) or vestigial (need code removal)? Out of scope for R0; flag for R2 owner.
5. **(OPS Q5)** `MANAGER_USER_ID=shako-jincharadze` (string, not UUID) — confirm `manager_actions.user_id` column type before R0.4 to avoid Phase 5 500s. See risk §7.5.
6. **(OPS Q6)** CGM-01 patch site confirmed — `scripts/rag/retrieve.py:139-143`, INVESTIGATION-CGM01 drift-audit table shows this is the ONLY remaining unfixed Qdrant call path in `scripts/`. No further drift sites. **Resolved.**
7. **(D1-new Q7)** Workflow→worker endpoint mismatch (risk §7.2) — `/fire-daily-batch` and `/render-weekly-brief` referenced by 2 workflows do not exist in `scripts/perception_worker.py`. Before R1.1, add the endpoints to the worker OR deploy a separate digest worker OR delete/disable those two workflows. Critical decision — without it, Phase 4 acceptance window (R1.3) cannot succeed. Escalate to S1.
8. **(D1-new Q8)** Is the operational owner of the n8n service swap (R0.6) comfortable with the 13-min downtime window between source-swap-save and n8n container ready? `daily-budget-gate` is the only currently-active workflow (audit §4.5) and it's already inert because n8n isn't running; downtime impact is therefore zero. Confirm with Shako.

---

*End of REPAIR_PLAN. Owner: D1 (Wave 2). Next step: S1 synthesizer ingests this plus D2's COMPLETION_PLAN into the executable run-sheet; Shako executes R0 in the order R0.1 → R0.2 → R0.3 → R0.4 → R0.5 → R0.6 (with snapshot pre-flight) → R0.7 → R0.8 → R0.9.*
