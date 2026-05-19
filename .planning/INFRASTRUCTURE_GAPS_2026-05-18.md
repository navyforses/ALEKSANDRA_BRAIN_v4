# Infrastructure Gaps — 2026-05-18

> Audit triggered by Phase 5 operator activation. Discovered while preparing
> Railway env var copy: several `.env` entries are empty or `localhost`-pinned,
> which means some plan-committed capabilities are NOT actually running even
> though the code that needs them is shipped.
>
> This document is the single source of truth for "what's missing" until each
> row is closed.

---

## Why this audit exists

While walking Shako through copying `.env` to Railway, we discovered that the
list of env vars he was about to paste contains:

1. **Real, working keys** (Supabase, Anthropic, Telegram, n8n, Notion, R2,
   Vercel, GitHub) — those are fine
2. **Empty placeholders** (`NCBI_API_KEY=`, `OPENAI_API_KEY=`, `FIRECRAWL_API_KEY=`)
3. **localhost-pinned URLs** (`QDRANT_URL=http://localhost:6333`,
   `NEO4J_URI=bolt://localhost:7687`) — these only work on Shako's laptop,
   NOT on Railway / Vercel
4. **Half-filled tokens** (`ANTHROPIC_USAGE_API_KEY=sk-ant-admin-` — 13 chars,
   incomplete)
5. **Commented-out config** (`TESSERACT_PATH`, `PHASE5_MANAGER_WORKER_URL`)

Shako asked the right question: *"so the empty env vars you're telling me to
skip — those mean the corresponding infrastructure was never actually set up?"*
The answer is: **partially yes, and we should make that explicit.**

---

## Phase → infrastructure → env var → status matrix

| Phase | Requirement | Capability | Env var(s) | Plan reference | Current state | Operational impact |
|---|---|---|---|---|---|---|
| **0** | FND-04 | n8n daily-budget-gate calls Anthropic Usage API to check today's $ spend | `ANTHROPIC_USAGE_API_KEY` | `docs/PHASE_0_MANUAL_STEPS.md §3` — "Create Admin Key → aleksandra-brain-usage-readonly" | **placeholder `sk-ant-admin-`** | The n8n workflow that's supposed to halt downstream Anthropic nodes at $1.50/day **does not get real spend data** from Anthropic. Code-side `check_daily_budget()` still works as a backstop (reads `runs.token_cost`), so we are not unprotected — but the n8n half of the defense is inoperative. **CLAUDE.md already flags this:** "n8n daily-budget-gate JSON-body expression bug" |
| **0** | FND-03 | n8n `/stop` webhook URL filled in after n8n deploy | `PANIC_STOP_WEBHOOK_URL` | `.env` line 83 comment — "filled after n8n is deployed in workflows/daily-budget-gate.json" | **empty** | Code references it 0 times right now (Phase 0 ships kill-switch via direct Telegram `/stop` polling in `mcp/panic_stop.py`, not via a webhook). Webhook is a v2 pattern. **Non-blocking.** |
| **1** | PRC-01 | PubMed E-utilities pulls with NCBI API key → 10 req/sec instead of 3 | `NCBI_API_KEY` | `.planning/REQUIREMENTS.md` PRC-01; `docs/PHASE_1_EXIT_REPORT.md §4 row 7` — "Functional with anon rate; user registers when comfortable" | **empty** | `scripts/fetch_pubmed.py` calls Entrez without an api_key → throttled to 3 req/sec. 6-hour cron still works; just slower per tick. **Non-blocking but cheap to fix** (free registration at `ncbi.nlm.nih.gov/account/settings`) |
| **1** | PRC-05 | Firecrawl fallback when Crawl4AI fails 2× on the same URL | `FIRECRAWL_API_KEY` | REQUIREMENTS.md PRC-05; PHASE_1_EXIT_REPORT.md `firecrawl_spend=$0.00` (gates never tripped) | **empty** | `scripts/gap_filler.py` `_firecrawl_under_cap` gate just skips Firecrawl. Phase 1 drill ran 0 Firecrawl calls anyway → not a real bottleneck. **Optional.** Costs $16/mo if enabled. |
| **2** | MEM-02, MEM-04, MEM-08 | Qdrant vector store for paper embeddings | `QDRANT_URL` | REQUIREMENTS.md MEM-04; STACK.md "Run Qdrant Docker on Railway ≈ $5/mo" | **`http://localhost:6333`** | Works on Shako's laptop with Docker running. On Railway, `localhost` resolves to the worker container itself → connection refused → any code path that touches Qdrant fails. **Phase 5 worker endpoints do NOT need Qdrant** (verified via grep). **Phase 1 `perception_tick` calls `scripts.chunking.embedder` which DOES need Qdrant.** So: Phase 5 deploy can defer this; Phase 1 cron deploy cannot. |
| **2** | MEM-02, MEM-03, MEM-07 | Neo4j AuraDB for Graphiti temporal graph | `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` | REQUIREMENTS.md MEM-01..MEM-07; PHASE_0_MANUAL_STEPS.md §5 | **password is a real AuraDB password (`mJRU...nq`), but URI is `bolt://localhost:7687`** | **Contradiction.** The password looks like a real AuraDB instance was provisioned at some point, but the URI was never updated from the local-Docker default. Either (a) AuraDB instance exists and URI needs to be repointed to `neo4j+s://xxxx.databases.neo4j.io`, or (b) the password is stale and a fresh AuraDB Free instance needs to be created. **Must resolve before any Phase 2 retrieval runs on Railway.** |
| **2** | MEM-04 | Qdrant API key (cloud) | `QDRANT_API_KEY` | (only needed if QDRANT_URL points to Qdrant Cloud) | **empty** | Only relevant once `QDRANT_URL` flips from localhost to a Cloud URL. Defer until that decision is made. |
| **5** | MNG-04 | OpenAI Whisper voice transcription | `OPENAI_API_KEY` | `.claude/plans/5-warm-crown.md` Day 3; PHASE_5_OPERATOR_RUNBOOK.md | **empty** | Voice button in BRAIN panel → Whisper call → 401 Unauthorized. Voice intake feature is **inoperative** until this is filled. Other intake paths (PDF, photo, email, text) work. **Blocks MNG-04 verifier in production mode.** |
| **5** | MNG-03 | Tesseract OCR binary path for photo medication labels | `TESSERACT_PATH` | `.env` line 129 comment — "Without this, photo intake falls back to Claude vision (~$0.005/photo)"; PHASE_5_OPERATOR_RUNBOOK.md | **commented out** | Photo intake still works via Claude vision fallback. Trade-off: ~$0.005/photo instead of free. **Non-blocking for activation.** Tesseract install is Windows-only (`UB-Mannheim/tesseract`) — once installed, uncomment + fill in path. |
| **5** | MNG-04, MNG-07, MNG-09, MNG-10, MNG-11 | Railway-hosted Python worker base URL | `PHASE5_MANAGER_WORKER_URL` | SPEC_DRAFT.md; PHASE_5_OPERATOR_RUNBOOK.md | **commented out** | Every n8n workflow that fires a Phase 5 endpoint (`workflows/manager_briefing.json`, future voice/apply/undo workflows) currently points at `https://placeholder.invalid` and fails gracefully (`onError: continueRegularOutput`). **No Phase 5 capability that's triggered by a workflow can actually run** until the worker is deployed and this URL filled. The voice and apply paths called directly from the Next.js route handlers ALSO need this URL — they just have different fail modes. |
| **5** | MNG-12 | Shared secret between Railway worker and Vercel viewer | `PHASE5_WORKER_AUTH_TOKEN` | `.env` line 140 comment — "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\"" | **filled** (64 hex chars, written earlier this session) | OK. Must be copied identically to Railway AND Vercel env vars before either side will accept requests. |
| 5 | MNG-01 (Single-operator scope) | manager_user_id for `manager_actions` row scoping + RLS | `MANAGER_USER_ID` | `.planning/phase-5/SPEC_DRAFT.md`; `.claude/plans/5-warm-crown.md` "Pre-decisions resolved §4" | **filled** (`shako-jincharadze`) | OK. |
| Optional MCP | — | Firecrawl MCP, Perplexity MCP, Exa MCP, Tavily MCP | `PERPLEXITY_API_KEY`, `EXA_API_KEY`, `TAVILY_API_KEY` | STACK.md "Alternatives Considered"; not wired into any agent loop yet | **empty** | None of these are integrated into Phase 0-5 code paths (verified via grep). **Non-blocking.** Pick them up only when a CrewAI agent loop needs them. |
| Optional MCP | — | Future OpenAI usage outside Whisper (embeddings, etc.) | `OPENAI_API_KEY` (second use) | — | covered above | Same key as MNG-04. |

---

## Architectural reality check (from Claude-extension Railway audit)

What's actually deployed right now in the Railway project `lucky-ambition`:

- **n8n service** — runs the 5 Phase 4 workflows + the 1 Phase 5 briefing workflow.
  Source repo was pointed at our repo at some point (not Shinyduo upstream) — that's
  why Railway tried to build our `Dockerfile.worker` against the n8n service. Fixed
  by renaming `Dockerfile` → `Dockerfile.worker` so n8n's auto-detect ignores it.
  Status: **running**.
- **Postgres service** — Railway-managed Postgres, presumably n8n's internal DB.
  Status: **running**.
- **(missing) perception_worker service** — Phase 1 mini-phase-1.1 was supposed
  to deploy this. PHASE_1_EXIT_REPORT.md §4 row 8: "Railway Python worker exposing
  `/perception-tick` — deferred to mini-phase 1.1". Mini-phase 1.1 was **never
  executed**. The 6-hour Phase 1 perception cron does NOT run in production right
  now — it only ran in `perception_tick --small --no-telegram` drill mode on Shako's
  laptop on 2026-05-15.
- **(missing) aleksandra-worker service** — Phase 5 voice/apply/undo/briefing/email
  endpoints. PHASE_5_OPERATOR_RUNBOOK.md step 2: "Railway worker deploy" — pending.
- **(present, useless) Cloudflare Worker `aleksandrabrane4`** — stale prototype.
  Has been failing on `@niivue/nvreact@^0.6.0` (nonexistent version) and `next@14.2.18`
  CVE. Already partially fixed by deleting root `package.json`. Action: **delete
  this Worker** unless someone can explain what it serves.

So the honest situation is:
- **Phase 5 production activation** = needs Railway `aleksandra-worker` service +
  OPENAI_API_KEY + PHASE5_MANAGER_WORKER_URL filled. ~45 min of Shako work per
  PHASE_5_OPERATOR_RUNBOOK.md. Code is shipped and tested.
- **Phase 1 6-hour cron** = needs Railway `aleksandra-worker` (same service, different
  endpoint `/perception-tick`) + Qdrant Cloud (or Railway Qdrant service) +
  Neo4j AuraDB URI repoint. Code is shipped but the worker never deployed and
  Qdrant/Neo4j were never moved off `localhost`.
- **n8n daily-budget-gate** = needs real `ANTHROPIC_USAGE_API_KEY` (Anthropic
  Admin Key, separate from the inference key). Code-side spend gate still works
  as backstop. Already on the CLAUDE.md operational caveat list.

---

## Priority-ordered remediation plan

### Tier 0 — Blocks Phase 5 production activation (operator-critical)

1. **`OPENAI_API_KEY`** — register at `platform.openai.com/api-keys`, generate a
   key, paste into local `.env` AND Railway env vars. Cost: ~$0.0001 per 5-sec
   voice clip → ~$0.0036/month at 60 clips/month.
2. **Deploy `aleksandra-worker` Railway service** — new service in `lucky-ambition`
   project, source = our GitHub repo, Dockerfile = `Dockerfile.worker`, healthcheck
   = `/healthz`. After deploy, copy the public URL into `PHASE5_MANAGER_WORKER_URL`
   in both local `.env` and Vercel env vars.
3. **Copy filtered env var subset to Railway** — the 21-var Phase-5-only list
   (drops `QDRANT_URL`, `NEO4J_URI/USERNAME/PASSWORD`, `OPENAI_API_KEY` until
   filled, `NCBI_API_KEY` empty, `FIRECRAWL_API_KEY` empty, all
   `PERPLEXITY/EXA/TAVILY/CLOUDFLARE_*KV/CLOUDFLARE_KV_NAMESPACE_ID` not used
   by Phase 5 endpoints).
4. **Copy `PHASE5_WORKER_AUTH_TOKEN` + `PHASE5_MANAGER_WORKER_URL` to Vercel**
   env vars — Vercel-hosted viewer needs both to talk to the worker.

### Tier 1 — Blocks Phase 1 perception cron (separate decision)

5. **Decide: Qdrant Cloud vs Railway Qdrant service vs defer.**
   - Qdrant Cloud free tier exists (1 GB, 1 cluster) — fastest path.
   - Railway Qdrant service ≈ $5/mo, same auth model as everything else.
   - Defer = Phase 1 6-hour cron does not run in production until next plan.
6. **Decide: Neo4j AuraDB URI repoint vs fresh instance.**
   - If the existing AuraDB password works, log into `console.neo4j.io`, find
     the instance URI, paste into `NEO4J_URI`. ~5 min.
   - If the instance is gone, create a free instance + update all 3 vars. ~15 min.
7. **Add `/perception-tick` endpoint to `aleksandra-worker`** — the worker
   service from step 2 already has the source for `scripts/perception_worker.py`;
   it just needs to be exposed. Then the n8n `workflows/perception_6h.json`
   template can be activated.

### Tier 2 — Hardening (no immediate user impact)

8. **`ANTHROPIC_USAGE_API_KEY`** — `console.anthropic.com` → Settings → Admin
   Keys → "Create Admin Key" → name: `aleksandra-brain-usage-readonly`. Paste
   into local `.env` AND Railway env vars (for n8n service that runs the
   daily-budget-gate workflow). Fixes the operational caveat that's been on the
   CLAUDE.md list since Phase 2.5.
9. **`NCBI_API_KEY`** — free registration at
   `ncbi.nlm.nih.gov/account/settings → API Key Management`. Gets us 10 req/sec
   instead of 3. Phase 1 throughput improvement.
10. **Delete stale Cloudflare Worker `aleksandrabrane4`** — unless someone can
    explain what it served, it's a dead surface and Cloudflare keeps trying to
    deploy it on every push.

### Tier 3 — Optional / out-of-scope until a feature needs them

11. `FIRECRAWL_API_KEY` — $16/mo. Only valuable if Crawl4AI starts failing
    repeatedly on the same source set. Defer until measured.
12. `PERPLEXITY_API_KEY`, `EXA_API_KEY`, `TAVILY_API_KEY` — none integrated into
    code. Pick up when a CrewAI agent needs them.
13. `TESSERACT_PATH` + Tesseract binary install — saves ~$0.005/photo. Total
    monthly OCR spend at current volume is <$0.50. Low ROI.
14. `PANIC_STOP_WEBHOOK_URL` — webhook pattern not used by current kill-switch.
    Only relevant if we move `mcp/panic_stop.py` polling onto an n8n trigger.

---

## What this plan replaces / restores

This document is the missing link between three things that previously lived in
separate places:

1. **`docs/PHASE_5_OPERATOR_RUNBOOK.md`** told Shako "do these 4 steps to
   activate Phase 5" but didn't surface the architectural gaps (Qdrant/Neo4j
   localhost, no perception worker, etc.).
2. **`.claude/plans/5-warm-crown.md` §"Backend gaps surfaced by this plan"**
   listed 10 forward-looking items but framed them as "next plan after Phase 5",
   not as "you need to decide which ones to fill BEFORE Phase 5 endpoints work
   in production."
3. **`CLAUDE.md` operational caveat** mentions the n8n budget-gate bug but
   doesn't enumerate the other gaps.

The remediation tiers above are the operational sequencing for closing all
three lists simultaneously.

---

## Cost projection for closing Tier 0 + Tier 1

| Item | One-time | Recurring |
|---|---|---|
| OpenAI API account + initial $5 credit | $5 | ~$0.01/mo at 60 voice clips |
| Railway `aleksandra-worker` service | — | ~$5/mo |
| Qdrant Cloud Free tier | — | $0 (1 GB / 1 cluster) |
| Neo4j AuraDB Free tier | — | $0 (200K nodes) |
| Anthropic Admin Key | — | $0 |
| NCBI API key | — | $0 |
| **Total to fully unblock Phase 1 + 5** | **$5** | **~$5/mo** |

Stays well inside the $20-30/mo MVP ceiling from PROJECT.md.

---

## Decision needed from Shako before next step

**A. Phase 5 only (fastest path to working voice/email/briefing for the family):**
- Tier 0 items 1-4
- Skip Tier 1 entirely
- ~1 hour of Shako work
- Result: voice intake works, email drafting works, morning briefing fires
- Phase 1 6-hour perception cron continues to NOT run in production

**B. Phase 5 + Phase 1 (full ingestion + family value):**
- Tier 0 + Tier 1
- ~2-3 hours of Shako work
- Result: above, plus the 6-hour cron starts ingesting new papers to the ledger
- Requires Qdrant + Neo4j decisions

**C. Just file this and continue with what we have:**
- Mark all tiers as backlog
- Phase 5 stays in code-complete mode (verifier 13/13 PASS, no production
  endpoints actually serving traffic)
- Family continues to receive Phase 4 weekly digest (already activated)
- This document becomes the input to the next plan

---

*Document created: 2026-05-18 by Claude during Phase 5 operator activation walkthrough*
*Owner: Shako Jincharadze*
*Next action: pick A/B/C above*
