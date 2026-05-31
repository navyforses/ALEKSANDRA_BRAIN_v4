# Handoff — Phase 5 + Phase 1 Production Activation (Option B)

**Session start:** 2026-05-18 ~14:00 UTC
**Session end:** 2026-05-18 ~22:00 UTC (paused mid-execution)
**Plan file:** `C:\Users\jinch\.claude\plans\5-warm-crown.md` (approved)
**Gap doc:** `.planning/INFRASTRUCTURE_GAPS_2026-05-18.md`
**Operator:** Shako Jincharadze
**Status:** ⏸ paused — Phase C in progress, Phase D/E/F pending, ⚠ critical n8n discovery needs decision

---

## TL;DR for next-session Claude (read first)

1. Phase A (credentials), Phase B (rehydration + verifiers) — DONE
2. Phase C (Railway worker deploy) — Shako created `aleksandra-worker` service, it was BUILDING when session paused. **Verify build completed + healthz works first thing on resume.**
3. **CRITICAL DISCOVERY:** the existing `n8n` service in `lucky-ambition` is actually running our Python `perception_worker.py`, NOT n8n. The URL `https://n8n-production-48c7.up.railway.app/healthz` returns `{"status":"ok","service":"perception_worker"}`. n8n itself is dead. This needs to be fixed before Phase D (workflow activation) can succeed — no n8n means no crons.
4. The 5 Phase-4 workflows + the 1 Phase-5 manager_briefing workflow are still in the n8n Postgres DB (`postgres` service in `lucky-ambition`, attached to `postgres-volume`). They aren't lost; they just have no n8n process consuming them.
5. Code-side: 5 Python files were modified to fix `QDRANT_API_KEY` propagation. Uncommitted. Need to commit + push before next deploy.

---

## What got done

### Phase A — credentials (Shako → .env, Claude → smoke verify)

| Step | Service | Status | Evidence |
|---|---|---|---|
| A1 | OpenAI API key | ✅ | `sk-proj-kFBn...85CMA` written to .env line 93; smoke `models.list()` returned 120 models incl. whisper-1 + gpt-realtime-whisper |
| A2 | Qdrant Cloud Free cluster | ✅ | URL `https://2e7a3efd-...:6333` + JWT API key (`eyJhbGc...l6Qwk`) on .env lines 35-36; `get_collections()` returned [] then setup populated 3 collections |
| A3 | Neo4j AuraDB Free instance | ✅ | URI `neo4j+s://29204819.databases.neo4j.io` on .env line 26; download file at `Neo4j-29204819-Created-2026-05-18.txt` (now gitignored); password starts `2y59kDn4...` |
| A4 | Anthropic Admin Key | ⏭ skipped | UI in new Claude Console pushed admin keys behind "Service accounts" which is harder for non-programmer; code-side `check_daily_budget()` is sufficient backstop; n8n daily-budget-gate workflow caveat remains on CLAUDE.md |
| A5 | NCBI API key | ✅ | `9f2693f16d88ecf92d23a88a8138c22fd108` on .env line 110; smoke esearch returned 12761 HIE hits + 3 PMIDs |

### Phase B — local rehydration + verifiers (Claude)

| Step | What | Result |
|---|---|---|
| B2 | `scripts/setup_qdrant.py` against Cloud cluster | 3 collections (`papers`, `therapies`, `hypotheses`) created; smoke point upserted with score 0.744 |
| B2 | `scripts/setup_neo4j.py` against Aura | 9 uniqueness constraints + Patient(Aleksandra) + 9 BrainRegion + 9 HAS_BRAIN_REGION rels |
| B3a | `scripts.chunking.backfill_embeddings` rehydration | 5301 vectors uploaded to Qdrant Cloud `papers` collection in 1502 sec, 0 errors |
| B3b | `scripts.extraction.batch_ingest --force` rehydration | 125 / 326 papers processed (HARD STOP at 3 Anthropic 400 errors — content-filter triggers on edge papers); 792 nodes (428 Entity, 141 Episodic, 83 Drug, 55 BrainRegion, 36 Pathway, 34 Gene, 14 Trial, 1 Patient) + 1932 relationships in Aura |
| B4 | `verify_phase1` | 10/10 PASS |
| B4 | `verify_phase2` | 19/19 PASS (MEM-04 needed `QDRANT_API_KEY` fix → patched) |
| B4 | `verify_phase2_5` | 15/16 (C.3 daily_digest 24h dry — pre-existing latent caveat, resolves when n8n fires the workflow once) |
| B4 | `verify_phase3` | 10/11 (cascades from 2.5 C.3) |
| B4 | `verify_phase4 --mode code-complete` | 8/9 (cascades) |
| B4 | `verify_phase5 --mode code-complete` | 12/13 (cascades) |

Net: real failures = 0. The cascade is all rooted in C.3 which resolves by firing daily_digest once in Phase D.

### Phase C — Railway worker deploy (in progress when session paused)

| Sub | Status | Notes |
|---|---|---|
| C1-C6 | ✅ | Shako created `aleksandra-worker` service in `lucky-ambition`, source = `navyforses/ALEKSANDRA_BRAIN_v4` main branch, builder = Dockerfile, dockerfilePath = `Dockerfile.worker`, generated domain |
| C7 | ✅ | Pasted 24-line env block via Raw Editor (Shako confirmed "24 Service Variables") |
| C8 | 🔄 BUILDING | At session pause: status BUILDING (02:19 elapsed) |
| C9 | ⏸ | Build expected to finish ~5min; needs verification curl + redeploy if first deploy crashes |
| C10 | ⏸ | Healthcheck not yet confirmed |

**aleksandra-worker public URL:** `https://aleksandra-worker-production-XXXX.up.railway.app` — exact subdomain not captured (Shako has it).

---

## ⚠ Critical discovery — n8n service is broken

While probing the n8n URL to fire daily_digest (to close C.3 cascade), discovered:

```
GET https://n8n-production-48c7.up.railway.app/         → {"status":"ok","service":"perception_worker"}
GET https://n8n-production-48c7.up.railway.app/healthz → {"status":"ok","service":"perception_worker"}
GET https://n8n-production-48c7.up.railway.app/rest/workflows → 404 not_found
POST .../perception-tick → 500 LocalProtocolError: Illegal header value (broken Supabase auth header)
POST .../morning-briefing → 401 unauthorized (Phase 5 auth check works)
```

**Conclusion:** the `n8n` service in `lucky-ambition` is currently running an OLD version of our Python `perception_worker.py`, not n8n. n8n itself is not serving traffic.

**Why this happened (most likely):**
1. Original deploy: n8n service used `n8nio/n8n:latest` Docker image — worked, ran 5 workflows
2. At some point, Source was changed to "GitHub Repo" pointing at our repo
3. Railway auto-detected `railway.json` → built `Dockerfile.worker` → replaced n8n with our worker
4. Commit `bfe6b78 chore(deploy): hide Python Dockerfile from n8n service auto-detect` was an attempted fix but didn't prevent this (railway.json still pointed at Dockerfile.worker for both services)
5. Latest deploys: n8n service runs the worker; n8n process is gone; postgres-volume still holds the workflow definitions

**Impact:**
- 6 n8n workflows can't fire (no n8n process)
- Daily spend reports stopped (last one 2026-05-17 22:06)
- Phase 4 acceptance window in jeopardy (no Sunday digests will fire)
- Phase D (workflow activation) blocks until n8n service restored

**Recovery options for next session (pick one):**

**Option R1 — Restore n8n service to actual n8n** (recommended)
- Railway → `n8n` service → Settings → Source → switch from "GitHub Repo" to "Docker Image" with image `n8nio/n8n:latest`
- Redeploy
- Postgres volume retains workflow definitions → they reactivate automatically
- All existing DB_POSTGRESDB_*, N8N_*, WEBHOOK_URL env vars are already correct for n8n
- ~10 min restore time

**Option R2 — Create new n8n service** (safer, costs +$5/mo)
- Create new service `aleksandra-n8n` in `lucky-ambition`
- Source = Docker Image = `n8nio/n8n:latest`
- Connect to existing postgres service
- Copy DB_POSTGRESDB_* + N8N_* env vars
- Update n8n_url in .env + workflow JSONs

**Option R3 — Skip n8n entirely** (NOT recommended)
- Replace n8n with pure-Python cron in worker
- Phase 4 + 5 workflow logic ported to worker endpoints
- Loses visual debugging surface
- Significant code change

R1 is the right answer — n8n's DB volume retains state, Docker image swap is reversible, and the 6 workflows resume automatically.

---

## Files modified this session (uncommitted)

```
M .gitignore                                  ← added Neo4j-*-Created-*.txt + .planning/RAILWAY_ENV_BLOCK.txt + .planning/VERCEL_ENV_BLOCK.txt
M scripts/chunking/embedder.py                ← pass QDRANT_API_KEY to QdrantClient
M scripts/chunking/retrofit_qdrant_stamps.py  ← same fix
M scripts/setup_qdrant.py                     ← same fix
M scripts/verify_phase2.py                    ← MEM-04 check uses api-key header on POST /scroll
M scripts/verify_phase2_5.py                  ← _qdrant_collection_info uses api-key header
?? .planning/INFRASTRUCTURE_GAPS_2026-05-18.md ← gap audit (committed below)
```

Plus many untracked files from earlier work (`.planning/phase-5/`, `mcp/`, `agents/swarm/`, `briefs/`, `tests/fixtures/brain_*.json`, `viewer/brain_*.html`, etc.) — those are existing untracked work from prior sessions and NOT part of this session's scope.

**Suggested commit for this session's bug fixes** (before next deploy):

```
chore(infra): fix QDRANT_API_KEY propagation across 5 cloud-aware scripts

Cloud Qdrant requires auth header. setup_qdrant.py, embedder.py,
retrofit_qdrant_stamps.py, verify_phase2.py, verify_phase2_5.py all
silently used localhost-only client init — fine for Docker, 403 on Cloud.
Each now reads QDRANT_API_KEY from env when present.

Also: ignore Neo4j Aura download files + per-deploy raw-paste blocks.
```

---

## Credentials state (.env reality check)

```
SUPABASE_URL=https://redsinfzadkyrsnwcznu.supabase.co       (was: same)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...4do                     (was: same)
SUPABASE_DB_URL=postgresql://...:5432/postgres              (was: same)
NEO4J_URI=neo4j+s://29204819.databases.neo4j.io             (was: bolt://localhost:7687)
NEO4J_USERNAME=neo4j                                         (was: same)
NEO4J_PASSWORD=2y59kDn4...sn4                               (was: mJRU...nq — unknown account)
NEO4J_DATABASE=neo4j                                         (NEW)
QDRANT_URL=https://2e7a3efd-...:6333                         (was: http://localhost:6333)
QDRANT_API_KEY=eyJhbGc...Qwk                                (NEW)
ANTHROPIC_API_KEY=sk-ant-api03-vNPW...QAA                   (was: same)
ANTHROPIC_USAGE_API_KEY=sk-ant-admin-                       (still placeholder — A4 skipped)
OPENAI_API_KEY: configured in local env only (redacted)     (NEW)
TELEGRAM_BOT_TOKEN=8854347079:AAGl...3LP8                   (was: same)
TELEGRAM_CHAT_ID=-1003525421564                             (was: same)
NCBI_API_KEY=9f2693f16...22fd108                            (NEW)
NCBI_EMAIL=jincharadzeshako@gmail.com                       (was: same)
NCBI_TOOL=aleksandra_brain                                  (was: same)
N8N_URL=https://n8n-production-48c7.up.railway.app          (⚠ MISNAMED — this URL serves worker, not n8n)
N8N_API_KEY: redacted (orphaned — no n8n at that URL)
MANAGER_USER_ID=shako-jincharadze                           (was: same)
PHASE5_WORKER_AUTH_TOKEN=b28721...495cf                     (was: same — 64 hex)
DAILY_BUDGET_USD=5.00                                       (was: same)
PHASE5_MANAGER_WORKER_URL=(still commented)                 (needs aleksandra-worker URL)
PERCEPTION_WORKER_URL=(not yet added)                       (needs aleksandra-worker URL)
```

Empty/optional/unused: `FIRECRAWL_API_KEY`, `PERPLEXITY_API_KEY`, `EXA_API_KEY`, `TAVILY_API_KEY`, `TESSERACT_PATH` (commented), `PANIC_STOP_WEBHOOK_URL`, `FIRECRAWL_MONTHLY_CAP_USD=10`. All non-blocking.

---

## Cloud backend live state

| Backend | URL | Counts |
|---|---|---|
| Supabase | `redsinfzadkyrsnwcznu.supabase.co` | 326 evidence_ledger, 5301 paper_chunks (all embedded), 255 papers, 96 contacts, 10 hypotheses, 12 therapies |
| Qdrant Cloud | `2e7a3efd-...aws.cloud.qdrant.io:6333` | papers=5302 vectors (dim=384), therapies=0, hypotheses=0 |
| Neo4j Aura | `29204819.databases.neo4j.io` | 792 nodes (428 Entity, 141 Episodic, 83 Drug, 55 BrainRegion, 36 Pathway, 34 Gene, 14 Trial, 1 Patient), 1932 relationships |

---

## Railway services state (per Shako's screenshot)

```
lucky-ambition project
 ├─ aleksandra-worker       (NEW — created this session, BUILDING at session pause)
 │   ├─ Source: github navyforses/ALEKSANDRA_BRAIN_v4 @ main
 │   ├─ Builder: Dockerfile @ Dockerfile.worker
 │   ├─ Region: EU West, 1 replica
 │   ├─ 24 Service Variables set (per Shako confirmation)
 │   └─ Domain: aleksandra-worker-production-XXXX.up.railway.app (exact subdomain not captured)
 │
 ├─ n8n                     (Online — but actually runs our worker code, NOT n8n)
 │   ├─ Source: github navyforses/ALEKSANDRA_BRAIN_v4 @ main (probably)
 │   ├─ URL: https://n8n-production-48c7.up.railway.app
 │   ├─ Currently returns {"service":"perception_worker"} (broken state)
 │   ├─ ⚠ env vars include n8n-specific (DB_POSTGRESDB_*, N8N_*, WEBHOOK_URL) — vestigial
 │   └─ Volume: n8n-volume (still has workflow definitions in attached postgres)
 │
 └─ Postgres                (Online — n8n's database, still holds workflow JSON)
     └─ Volume: postgres-volume
```

---

## Next-session resume sequence

When you (next-session Claude) come back, run these in order:

### Step 1 — Read this handoff + plan
```
Read C:\Users\jinch\.claude\plans\5-warm-crown.md
Read .handoffs/handoff-2026-05-18-phase5-railway-activation.md
Read .planning/INFRASTRUCTURE_GAPS_2026-05-18.md
```

### Step 2 — Check `aleksandra-worker` build status
Ask Shako for the URL (subdomain `aleksandra-worker-production-XXXX`).

```bash
# Verify worker is alive
curl -fsS https://aleksandra-worker-production-XXXX.up.railway.app/healthz
# Expects: {"status":"ok","service":"perception_worker"}
```

If 200 OK → worker is live, proceed.
If 500 / connection refused → check Railway deploy logs with Shako.

### Step 3 — Decide on n8n recovery (Option R1 vs R2)
Present options to Shako. R1 (revert n8n service to `n8nio/n8n:latest` Docker image) is the recommended path.

Walk Shako through:
- Railway → `n8n` service → Settings → Source → "Change source" → "Docker Image" → enter `n8nio/n8n:latest` → Save
- Trigger redeploy
- Wait 2-3 min
- Verify `https://n8n-production-48c7.up.railway.app/` shows n8n login UI (not JSON)

### Step 4 — Update .env with the two URLs
Once both services are healthy:
```
PHASE5_MANAGER_WORKER_URL=https://aleksandra-worker-production-XXXX.up.railway.app
PERCEPTION_WORKER_URL=https://aleksandra-worker-production-XXXX.up.railway.app
N8N_URL=https://n8n-production-48c7.up.railway.app   (now actually n8n again)
```

### Step 5 — Add the same two URLs to Railway env vars
- aleksandra-worker service: no change needed (worker is self-referential — doesn't need its own URL)
- n8n service: add `PHASE5_MANAGER_WORKER_URL` + `PERCEPTION_WORKER_URL` (so n8n workflows can POST to worker)
- Vercel viewer project: add `PHASE5_MANAGER_WORKER_URL` + `PHASE5_WORKER_AUTH_TOKEN`

### Step 6 — Phase D: Activate workflows + fire daily_digest
- n8n UI → Workflows → `perception-6h` → toggle "Active" on → "Execute Workflow" once
- n8n UI → Workflows → `daily-digest` → "Execute Workflow" (this resolves verify_phase2_5 C.3 + all cascading REGR failures)
- Verify Telegram receives both summaries

### Step 7 — Phase E: production smoke
- Voice intake at https://aleksandra-brain-v4.vercel.app/brain
- Email intent "write to Sydney about Duke timing"
- PDF drop
- Undo most recent action
- Confirm Gmail Drafts has draft, manager_actions row written, Telegram audit message dispatched

### Step 8 — Phase F: docs commit
1. Commit script fixes: `chore(infra): fix QDRANT_API_KEY propagation across 5 cloud-aware scripts`
2. Update CLAUDE.md "მიმდინარე ეტაპი" — mark Phase 5 production live + Phase 1 cron live
3. Note n8n service-fix in commit history

---

## Open caveats

| # | Caveat | Severity | Resolution |
|---|---|---|---|
| 1 | n8n service runs worker code, not n8n | 🔴 Blocking Phase D | Step 3 in resume sequence above |
| 2 | batch_ingest stopped at 125/326 papers (Anthropic 400 errors) | 🟡 Acceptable | 792 Neo4j nodes > 500 threshold; defer remaining ~200 papers until next maintenance |
| 3 | verify_phase2_5 C.3 daily_digest 24h dry | 🟡 Acceptable | Resolves automatically after Step 6 fires daily_digest |
| 4 | A4 Anthropic Admin Key skipped | 🟢 Documented | Code-side `check_daily_budget()` is the real backstop; n8n usage-API integration is hardening, not blocking |
| 5 | TESSERACT_PATH commented out | 🟢 Documented | Claude vision fallback at ~$0.005/photo |
| 6 | FIRECRAWL_API_KEY empty | 🟢 Documented | Crawl4AI handles all sources in current set |
| 7 | Neo4j-29204819-Created-2026-05-18.txt in working dir | ✅ Resolved | Added to .gitignore this session |
| 8 | `.planning/RAILWAY_ENV_BLOCK.txt` generated with all secrets | ✅ Resolved | Added to .gitignore this session |

---

## Source of truth for resume

- **Plan:** `C:\Users\jinch\.claude\plans\5-warm-crown.md`
- **Gap audit:** `.planning/INFRASTRUCTURE_GAPS_2026-05-18.md`
- **This handoff:** `.handoffs/handoff-2026-05-18-phase5-railway-activation.md`
- **CLAUDE.md "მიმდინარე ეტაპი":** still shows Phase 5 code-complete; needs update once Phase E demo passes

---

*Handoff written 2026-05-18 by Claude during paused Phase 5+1 activation. Next session: pick up at Step 1 above.*
