# ALEKSANDRA_BRAIN — Master Execution Plan

**Agent:** S1 (Wave 3 — synthesizer)
**Date:** 2026-05-19
**Inputs synthesized:** `.planning/AUDIT_2026-05-18.md`, `.planning/team/INVESTIGATION-OPS.md` (R1), `.planning/team/INVESTIGATION-CGM01.md` (R2), `.planning/team/INVESTIGATION-PHASE6.md` (R3), `.planning/team/REPAIR_PLAN.md` (D1), `.planning/team/COMPLETION_PLAN.md` (D2).
**Banned reads honored:** No `.handoffs/*` or `PHASE_*_EXIT_REPORT.md` opened.
**S1 verified:** `grep -nE "fire-daily-batch|render-weekly-brief" scripts/perception_worker.py` returns **0 hits** — D1's Q7 finding is correct; the two endpoints referenced by `telegram_daily_digest.json` and `weekly_brief.json` do NOT exist in the worker.

---

## §1. Executive summary

This plan replaces all prior phase-by-phase narratives in `CLAUDE.md` "მიმდინარე ეტაპი" and supersedes the standalone REPAIR_PLAN + COMPLETION_PLAN. Its single reader is **Shako Jincharadze**, who executes it as the operational owner. "Done" means: (a) Vercel `/brain` returns a working Next.js shell from a real `viewer/`-rooted build (audit §4.6 ERROR cascade closed); (b) the Railway `n8n` service runs n8n (not `perception_worker.py` masquerading per audit §4.5) and fires all 11 workflows on schedule; (c) the two missing worker endpoints `/fire-daily-batch` and `/render-weekly-brief` either exist or have been routed around so Phase 4 acceptance (briefs ≥ 2 by ~2026-06-07) succeeds; (d) `verify_phase{1..6}` produce a cumulative ~91/91 PASS at `--mode production`; (e) the 3D viewer at `viewer/app/brain/page.tsx` renders Aleksandra's MRI from a local file picker via `@niivue/nvreact`. Total wall-clock: ~25 days from R0 start, dominated by the 14-day Phase 4 acceptance soak (C2) which runs in parallel with engineering tracks C3/C4/C5.

---

## §2. The single executable order

The numbered list below is the **only** sequencing artifact Shako needs. Each row cites the source plan's task ID. Items marked PARALLEL can be run concurrently with the immediately-preceding item.

1. **R0 — Tier 0 Repair, part A (infra-side)** (REPAIR_PLAN §3, tasks R0.1 → R0.6).
   - Sub-order: R0.1 (Vercel root-dir) → R0.2 (Vercel redeploy) → R0.3 (.env worker URLs) → R0.4 (Vercel env vars) → R0.5 (Vercel redeploy after env) → **R0.6 (n8n Docker swap with volume snapshot pre-flight)**.
   - ETA: ~40 min wall-clock (Shako-driven UI work + n8n container pull).
   - Owner: Shako.
   - Gate: each task's individual `Verify` block in REPAIR_PLAN §3.

2. **D1-Q7 RESOLUTION — Digest endpoints decision** (NEW phase, inserted between R0 part A and R0 part B). See §5 Branch A.
   - Without this decision, activating `telegram_daily_digest` and `weekly_brief` workflows in R1 fires them against non-existent worker endpoints — Phase 4 acceptance (C2) silently fails.
   - ETA: 15 min decision + 30-60 min implementation depending on branch chosen.
   - Owner: Shako decides branch; Claude implements.
   - Gate: §5 Branch A "Verify" sub-row.

3. **R0 — Tier 0 Repair, part B (code-side)** (REPAIR_PLAN §3, tasks R0.7 → R0.9).
   - Sub-order: R0.7 (CGM-01 patch on `scripts/rag/retrieve.py` per INVESTIGATION-CGM01) → R0.8 (commit 7 files including the new patch + previously-staged Qdrant drift fixes — explicit-path `git add`, NEVER `git add .`) → R0.9 (`verify_phase3` rerun).
   - ETA: ~15 min.
   - Owner: Claude (Edit + commit) + Shako (review).
   - Gate: REPAIR_PLAN §4 — all 6 verification probes PASS (Vercel /brain, /, worker healthz, n8n REST list, CGM-01 PASS, remote main advanced).

4. **R1 — Workflow activation + first daily-digest fire** (REPAIR_PLAN §6 R1.1 + R1.2, expanded from INVESTIGATION-OPS T1-1/T1-2).
   - Activate the 6 currently-inactive workflows in the n8n UI (`perception_6h`, `daily_digest`, `daily_spend_report`, `chunking_trigger`, `extraction_trigger`, `urgent_alerts`).
   - Manually fire `daily_digest` once to clear the Phase 2.5 C.3 cascade — this single fire flips REGR → PASS in Phase 3/4/5 verifiers.
   - ETA: ~10 min UI work + 5 min smoke.
   - Owner: Shako.
   - Gate: `curl -H "X-N8N-API-KEY: $N8N_API_KEY" .../api/v1/workflows | jq '[.data[] | select(.active==true)] | length'` returns 11; `verify_phase2_5 --json` C.3 → `recent_fire ≥ 1`.

5. **C1 — Phase 5 production smoke** (COMPLETION_PLAN §2 C1).
   - Shako drops one real PDF or photo into BrainPanel intake; records one voice clip via the BrainPanel VoiceRecorder; drafts one email via "write to X about Y".
   - ETA: ~1 hr.
   - Owner: Shako.
   - Gate: `manager_actions count > 0` AND `intake_drops count > 0` AND `runs.kind='whisper_call' count > 0` AND Telegram audit message visible.

6. **R2 — Tier 2 hardening** (REPAIR_PLAN §6 R2.1..R2.7).
   - **PARALLEL** with C2 acceptance soak below.
   - R2.1 truth up CLAUDE.md, R2.2 fresh Railway token, R2.3 alias decision (see §5 Branch B), R2.4 6 missing tables (see §5 Branch C), R2.5 reconnect `ANTHROPIC_USAGE_API_KEY`, R2.6 reprocess ~200 ledger papers, R2.7 delete stale CF Worker.
   - ETA: ~90 min (most items 5-15 min each; R2.6 LLM work bounded by $1 cap).
   - Owner: Claude (most items) + Shako (Railway token).
   - Gate: each item's individual verify per INVESTIGATION-OPS Tier 2 table.

7. **C2 — Phase 4 acceptance soak** (COMPLETION_PLAN C2, calendar-bound).
   - 14-day window. First milestone: Sunday 2026-05-24 13:00 UTC (first Weekly Brief + Manager Briefing). Second milestone: Sunday 2026-05-31 13:00 UTC. Closes ~2026-06-07.
   - **PARALLEL** with R2, C3, C4, parts of C5 — engineering work uses the soak calendar.
   - ETA: 14 days wall-clock (zero engineering hours).
   - Owner: Shako (passive monitoring).
   - Gate: `briefs ≥ 2`, `prod_t1_delivered ≥ 3`, `prod_weekly_drafts ≥ 2`, `prod_clinician_drafts ≥ 1`, zero panic-stop events, daily-spend ≤ $0.50/day.

8. **C3 — Phase 6 cleanup** (COMPLETION_PLAN §3, tasks C3.1..C3.9).
   - **PARALLEL** with C2 (cleanup is pure-edit; no dependency on soak).
   - Per INVESTIGATION-PHASE6 classification: 1 verify-noop (C3.1) + 1 palette port (C3.2) + 12-file archive move (C3.3) + nibabel bug fix (C3.4) + delete fabricated value (C3.5) + MCP-INVENTORY row (C3.6) + swarm-boundary ADR (C3.7) + drop Celery branch (C3.8) + stdio gate (C3.9).
   - ETA: ~75 min engineering.
   - Owner: Claude.
   - Gate: C3.1..C3.9 individual probes per COMPLETION_PLAN §3 (12 archived demos, `img.affine` in MCP, no `0.85` fabrication, MCP row present, no `celery*` files, stdio assertion present).

9. **C4 — Phase 6 NiiVue integration** (COMPLETION_PLAN §4, sketch → spec).
   - **PARALLEL** with C2 second week (engineering proceeds while Sunday 2026-05-31 brief fires).
   - Mount `@niivue/nvreact` at `viewer/app/brain/page.tsx:51-62`; wire `load_nifti` via MCP boundary defined in C3.7 ADR; swarm via multiprocessing path (Celery dropped per C3.8); enforce PHI/stdio gate (already added in C3.9 — verify end-to-end).
   - ETA: 3-5 days.
   - Owner: Claude (Phase-spec via `gsd-spec-phase` first; then `gsd-execute-phase`).
   - Gate: new `scripts/verify_phase6.py` GREEN on VIS-01..05 (family loads NIfTI in <10s; provenance fields present in lesion output; stdio-only transport; 128³ fixture <60s; clinician PDF includes brain view).

10. **C5 — Backend gap closure** (COMPLETION_PLAN §5, gaps G1..G10 + 6 missing tables).
    - **PARALLEL** with C2 (most gaps) and C3/C4 (G1/G2/G7/G9/G10 are independent; G3/G4 pure-backend; G5/G8 serialize after C4 because they touch viewer).
    - ETA: ~5 days engineering distributed across the soak window.
    - Owner: Claude.
    - Gate: each gap's per-item verifier per COMPLETION_PLAN §5 table.

11. **C6 — Phase 6 acceptance + final drift watch** (COMPLETION_PLAN C6).
    - Runs after C4 + C5 complete; opens ~2026-06-04 (within the soak tail) or ~2026-06-07 (soak close).
    - 3-day family acceptance window (subjective UAT on brain viewer) + 7-day drift watch (no new Vercel ERRORs, no inactive workflows regressed).
    - ETA: 10 days wall-clock; ~4 hrs engineering for final verifier + master roll-up.
    - Owner: Shako (UAT) + Claude (verifier).
    - Gate: `verify_phase{1..6} --mode production` returns 91/91 cumulative; family signs off on viewer.

---

## §3. Critical-path Gantt

Week-by-week visualization. `[X]` marks tasks running on that day. `(p)` marks PARALLEL with the row(s) above.

```
Week  | Mon (5/18) | Tue (5/19) | Wed (5/20) | Thu (5/21) | Fri (5/22) | Sat (5/23) | Sun (5/24)
------+------------+------------+------------+------------+------------+------------+------------
W0    | R0-A       | D1-Q7      | R0-B + R1  | C1 smoke   | C3.1-9     | R2 hardening | FIRST Sun brief
      | R0.1-R0.6  | decide +   | R0.7-R0.9  | (Shako)    | (Claude)   | (mostly C3.1-Q1)| C2 milestone 1
      | n8n swap   | implement  | + activate |            |            |              | briefs+=1
      |            |            | 6 wfs +    |            |            |              | (Manager brief
      |            |            | daily_dig  |            |            |              |  also fires)
      |            |            | fire       |            |            |              |

Week  | Mon (5/25) | Tue (5/26) | Wed (5/27) | Thu (5/28) | Fri (5/29) | Sat (5/30) | Sun (5/31)
------+------------+------------+------------+------------+------------+------------+------------
W1    | C5/G1+G9   | C5/G2+G10  | C5/G3      | C5/G7      | C5/G4 stub | C5 buffer  | SECOND brief
      |  calendar  |  realtime+ |  pattern   |  Whisper   |  + missing |            | C2 milestone 2
      |  + ENUM    |  observ    |  recog     |  audit     |  tables    |            | briefs+=1 (≥2)
      | (p)C2 soak | (p)C2      | (p)C2      | (p)C2      | (p)C2      | (p)C2      | (p)C2

Week  | Mon (6/1)  | Tue (6/2)  | Wed (6/3)  | Thu (6/4)  | Fri (6/5)  | Sat (6/6)  | Sun (6/7)
------+------------+------------+------------+------------+------------+------------+------------
W2    | C4 spec    | C4 mount   | C4 MCP     | C4 swarm   | C5/G5 mob  | C5/G8 PHI  | C2 SOAK CLOSE
      | gsd-spec   | nvreact    | wiring +   | wiring +   |  + C6 spec |  expansion | acceptance
      | -phase     |            | verifier   |  PDF       |            |            | rollup
      | (p)C2 soak | (p)C2      | (p)C2      | (p)C2      | (p)C2      | (p)C2      |

Week  | Mon (6/8)  | Tue (6/9)  | Wed (6/10) | Thu (6/11) | Fri (6/12) | Sat (6/13) | Sun (6/14)
------+------------+------------+------------+------------+------------+------------+------------
W3    | C6 UAT     | C6 drift   | C6 drift   | C6 drift   | C6 drift   | C6 drift   | DONE
      | family     | watch d1   | watch d2   | watch d3   | watch d4   | watch d5   | 91/91 verifier
      | reviews    | (Vercel +  |            |            |            |            | + family sign-off
      | /brain     |  workflow  |            |            |            |            |
      |            |  regr      |            |            |            |            |
      |            |  monitor)  |            |            |            |            |
```

Notes on the Gantt:
- W0 Mon: R0 part A (~40 min) leaves headroom Monday for D1-Q7 decision review.
- W0 Tue: D1-Q7 implementation (Branch A.1 if endpoints are added — ~1 hr Claude) followed by R0 part B (15 min).
- **W0 Wed is the linchpin** — workflow activation + first daily-digest fire happens here so Sunday 5/24 sees its first real Weekly Brief.
- W0 Thu (C1 smoke) is a Shako-driven hour to prove the Phase 5 cockpit works end-to-end.
- W0 Fri (C3 cleanup) is pure engineering — no dependency on C2 soak yet.
- W1 spreads C5 backend gaps across the soak's first full week.
- W2 is C4 (NiiVue integration). Spec → mount → wire → verify across 4 days.
- W3 is C6 acceptance + drift watch.

---

## §4. Hand-offs and dependencies

```
R0-A (R0.1..R0.6) ───────────►  D1-Q7 decision ───►  R0-B (R0.7..R0.9)  ───►  R1 activation
                                                                                  │
                                                                                  ▼
                                                                              C1 smoke
                                                                                  │
                                                          ┌───────────────────────┼───────────────────────┐
                                                          ▼                       ▼                       ▼
                                                       R2 hardening       C3 Phase 6 cleanup       C5 partial (G1/G2/G7/G9/G10)
                                                          │                       │                       │
                                                          └───────────────────────┼───────────────────────┤
                                                                                  ▼                       │
                                                                              C4 NiiVue integration  ◄────┤
                                                                                  │                       │
                                                                                  ▼                       ▼
                                                                              C5 G5/G8 serialize   C5 remainder
                                                                                  │                       │
                                                                                  └───────────┬───────────┘
                                                                                              ▼
                                                                                          C6 acceptance + drift watch

(C2 — Phase 4 14-day soak — runs from R1 fire ➜ ~2026-06-07, in PARALLEL with R2/C3/C4/C5 above)
```

Hand-off rules:
- **R0-A → D1-Q7:** R0 closes Vercel + worker URLs + n8n live, after which the digest-endpoint question can be reasoned about with real probes. D1-Q7 cannot be skipped — it gates Phase 4 acceptance success.
- **D1-Q7 → R0-B:** The chosen implementation (per §5 Branch A) must land before R0.8's atomic commit so all CGM-01 + Qdrant + digest-endpoint changes ship together.
- **R0-B → R1:** Verifiers must rerun GREEN before workflow activation, otherwise activation amplifies bad state.
- **R1 → C1:** Workflows must be live so the C1 smoke exercises the real production path, not a local dry-run.
- **C1 → C2:** The smoke proves the path. C2 then proves the duration (14-day soak).
- **R0 → C3:** Cleanup needs a stable repo (no `M` lines in `scripts/`) to land cleanly without colliding with R0.8's commit.
- **C3 → C4:** Integration mounts on the cleaned-up MCP + ADR boundary defined in C3.7.
- **C4 → C5 (G5/G8 only):** Mobile responsive (G5) and voice-PHI redactor (G8) touch viewer components — serialize after C4 to avoid merge conflicts.
- **C4 + C5 → C6:** Acceptance only runs after both engineering tracks close.
- **C2 ⊥ (R2 + C3 + C4 + C5):** The 14-day calendar window is orthogonal — it runs alongside engineering. The calendar dictates milestone dates, not engineering throughput.

---

## §5. Decision points and branches

### Branch A — D1-Q7 (digest worker endpoints)

**The problem:** Two active workflow JSONs POST to endpoints that don't exist:
- `telegram_daily_digest.json` → `{{$env.PHASE4_DIGEST_WORKER_URL}}/fire-daily-batch`
- `weekly_brief.json` → `{{$env.PHASE4_DIGEST_WORKER_URL}}/render-weekly-brief`

S1 confirmed (re-running D1's probe): `grep -nE "fire-daily-batch|render-weekly-brief" scripts/perception_worker.py` returns **0 hits**. The 9 existing endpoints (audit §4.4) are `/perception-tick`, `/chunking-tick`, `/extraction-tick`, `/daily-spend-report`, `/voice-transcribe`, `/apply-actions`, `/undo-action`, `/morning-briefing`, `/email-intent`.

**Branches:**

| Branch | Action | ETA | Pros | Cons | Verify |
|---|---|---|---|---|---|
| **A.1 (RECOMMENDED)** Add the 2 endpoints to `perception_worker.py` | Append two routes modeled on `/daily-spend-report`. `/fire-daily-batch` calls the existing `scripts/render_daily_digest.py` / Telegram batch path; `/render-weekly-brief` calls existing weekly brief renderer (logic already exists in `scripts/communicator/weekly_brief.py` per repo grep). Add as R0.10 (appended to R0). | ~1 hr code + 15 min smoke | Single worker stays the model; no new infra; legacy code reused | Worker becomes a bit more polyglot (perception + digest under one process) | After deploy: `curl -fsS https://aleksandra-worker-production.up.railway.app/fire-daily-batch -X POST -H "Authorization: Bearer $PHASE5_WORKER_AUTH_TOKEN"` returns 200 with JSON body. Same for `/render-weekly-brief`. |
| **A.2** Deploy a separate digest worker | New Railway service `aleksandra-digest-worker` with its own Dockerfile; new env var `PHASE4_DIGEST_WORKER_URL=https://aleksandra-digest-worker-production.up.railway.app` overrides the all-pointing-at-perception-worker .env value | ~3 hrs | Cleaner separation of concerns | +$5/mo Railway; deploy complexity; deferable | n/a — defer to Phase 7. **Disable workflows in the meantime per A.3.** |
| **A.3** Disable + re-route | Edit `telegram_daily_digest.json` to call `/daily-spend-report` (different semantics — only sends spend, not full digest) and disable `weekly_brief.json` entirely; surface a manual `scripts/communicator/weekly_brief.py` invocation Sunday | ~10 min | Fastest unblock | Phase 4 acceptance becomes manual — defeats the unattended promise | Weekly brief manual script generates PDF + Gmail draft; counted as `prod_clinician_drafts += 1` |

**S1 recommendation: A.1.** It costs an extra hour vs. A.3's 10 min but earns the "site complete = unattended" exit criterion in COMPLETION_PLAN §1.

**Append to R0 as R0.10:**
- File: `scripts/perception_worker.py`
- Add: 2 FastAPI routes `@app.post("/fire-daily-batch")` and `@app.post("/render-weekly-brief")` modeled on the existing `/daily-spend-report` route at perception_worker.py:120-128.
- Each route: bearer-token check against `PHASE5_WORKER_AUTH_TOKEN`, import + invoke the existing `scripts/communicator/` rendering function, write a row to `runs` with the right `kind` value, return JSON status.
- Ship in R0.8's atomic commit alongside the CGM-01 patch.

### Branch B — Vercel SSO gate (D2 open #1, audit §4.6)

**The problem:** `viewer-git-main-shakos-projects-82dad3f2.vercel.app` returns 401 (SSO required). Family members cannot access without seats.

**Branches:**

| Branch | Action | ETA | Pros | Cons |
|---|---|---|---|---|
| **B.1** Disable SSO for production alias | Vercel UI → Project `viewer` → Settings → Deployment Protection → set to "None" for production | 2 min | Free; instant; family-friendly | Production alias becomes world-readable. The viewer UI shows Aleksandra's name in BrainPanel metadata + page titles; mitigations needed before flipping (audit no PHI exposure but does expose patient name) |
| **B.2 (RECOMMENDED for MVP)** Add 3-4 Vercel team-seat invites | Vercel UI → Team Members → Invite Shako + Sopo + (optional) Dr. Maypole + Dr. Hien | 5 min | Stays auth-gated; HIPAA-aware posture | Each invitee needs a Vercel account; minor friction; Hobby tier allows up to 3 team members per Vercel ToS (may need Pro at $20/mo if >3 — escapes $20-30 MVP cap) |
| **B.3** Migrate to Cloudflare Pages | Move static export to CF Pages; keep `/api/manager/*` routes as CF Workers OR move them to the Railway worker as additional endpoints | 1 day eng | Egress-free; no SSO friction; aligned with stack's CF preference | Loses Vercel Edge functions; rewrites of `/api/manager/*` routes; one-day refactor; risk of regression |

**S1 recommendation: B.2 for MVP, with B.1 as a fallback if Vercel free-tier seats run out.** B.3 is a Phase 7 candidate — its work would be undone if Vercel adds a per-seat free option later.

**Append to R2.3 (already covers the alias question) — combine with SSO decision:** in R2.3, also resolve Branch B before C1 smoke (because C1 requires Shako to access the viewer).

### Branch C — 6 missing Supabase tables (D2 open #4, R2.4)

**The problem:** Tables `llm_call`, `citations`, `digest_to_run_link`, `telegram_history`, `email_log`, `firecrawl_calls` are referenced (or implied) by code but do not exist in Supabase (audit §4.1).

**Branches:**

| Branch | Action | ETA | Pros | Cons |
|---|---|---|---|---|
| **C.1 (RECOMMENDED — D2's recommendation)** Create migration `012_missing_tables.sql` | Write SQL to create all 6 tables; cite which code paths reference each via `git grep`; ship per RLS-strict policy | ~2 hrs (audit grep + schema + RLS + apply) | Restores observability/audit value implied by table names; future-proofs without code rewrites | 6 new tables sitting empty initially; small Supabase row-quota impact (negligible at free tier) |
| **C.2** Remove the code references | `git grep` each name; delete or stub call sites | ~2 hrs (mostly grep + edits) | Smaller surface; less dead weight | Silent loss of capability; some references may activate in future and re-break |

**S1 recommendation: C.1 — write migration 012.** D2's reasoning holds: each table name suggests legitimate value. The audit cost is identical either way; the schema-creation path lets the code references find their target instead of degrading silently.

**Append to R2.4 as the chosen implementation path.**

---

## §6. Acceptance criteria — site is complete when:

Checklist of objective probes that prove "done". Mapped to COMPLETION_PLAN §1 exit criteria plus S1 additions.

**Family-visible:**
- [ ] Voice intake button in BrainPanel records → Whisper → `intake_drops` row → entity router → preview card visible.
- [ ] Sunday weekly digest fires unattended at 13:00 UTC (2 consecutive Sundays minimum: 2026-05-24 + 2026-05-31).
- [ ] Clinician PDF auto-generates without manual `--mode code-complete` workaround (`prod_clinician_drafts ≥ 1`).
- [ ] `/brain` route renders Aleksandra's MRI volume via NiiVue from a local file picker (no server upload — confirmed by network tab showing no NIfTI uploads).
- [ ] Layout works at iPad-mini width (768px) — BrainPanel collapses to bottom-sheet.
- [ ] Telegram audit message visible in family chat for at least 5 manager actions (`manager_actions count ≥ 5`).

**Operator-visible:**
- [ ] All 11 n8n workflow JSONs are `active=True` AND fire on schedule against a real n8n process (not `perception_worker.py` masquerading per audit §4.5).
- [ ] All 6 verifiers GREEN at `--mode production` (new flag added in C2/C4).
- [ ] Cumulative coverage = 91/91 (10 + 19 + 16 + 11 + 9 + 13 + ~13 VIS).
- [ ] `briefs ≥ 2`, `prod_t1_delivered ≥ 3`, `prod_weekly_drafts ≥ 2`, `prod_clinician_drafts ≥ 1`, `manager_actions ≥ 5`, `intake_drops ≥ 5`.
- [ ] `manager_briefing.json` writes a row to `runs` every Sunday 13:00 UTC.
- [ ] `outreach_log` count climbs from 1 across the 14-day soak.

**Backend closed:**
- [ ] All 10 backend gaps from `.planning/phase-5/` resolved (verifier check per gap).
- [ ] 6 missing Supabase tables created via migration 012 (Branch C.1) OR code references removed (Branch C.2); choice executed and probe-verified.
- [ ] `/fire-daily-batch` and `/render-weekly-brief` worker endpoints exist (Branch A.1) OR routes re-mapped (Branch A.3); probe returns 200.
- [ ] Vercel SSO posture resolved (Branch B.1, B.2, or B.3); family can access from logged-in browser.
- [ ] CGM-01 PASS in `verify_phase3` (Qdrant 403 closed); no remaining Qdrant call site lacks `QDRANT_API_KEY` propagation.

**Phase 6 specific:**
- [ ] `aleksandra-niivue-mcp` registered in `MCP-INVENTORY.csv` (C3.6).
- [ ] Swarm orchestrator callable from Communicator agent via the MCP tool boundary, not direct Python import (C3.7 ADR).
- [ ] Banned-gradient HTML demos deleted or archived (C3.3 — 12 files moved to `.planning/research/visualization-demos/`).
- [ ] nibabel 3.x bug at `mcp/aleksandra_niivue_mcp.py:31` patched (C3.4 — `img.affine` not `header.get_affine()`).
- [ ] `scripts/brain_builder_swarm.py` fabricated value removed (C3.5 — file deleted).
- [ ] Celery branch deleted (C3.8); `agents/swarm/celery_*.py` not present.
- [ ] PHI/stdio-only gate on niivue MCP (C3.9 — RuntimeError raised on HTTP/SSE transport).

**Drift watch:**
- [ ] Re-running the audit's §8 methodology trail produces 91/91 PASS with zero new doc-vs-reality deltas in §6.
- [ ] 7-day drift watch (W3 Tue → Sat) confirms no new Vercel ERROR deploys and no workflows regressed to `active=False`.

---

## §7. Token / cost budget for execution

| Line item | Cost | Notes |
|---|---|---|
| Vercel | $0/mo | Hobby tier; if Branch B.2 needs 4+ seats, upgrade to Pro ~$20/mo (escapes $20-30 cap — fallback to Branch B.1 if so) |
| Railway | +$5/mo (worker) | n8n already paid for; worker is new ongoing cost. If Branch A.2 chosen, +$5/mo for digest worker (rejected) |
| LLM (Anthropic Sonnet 4.5) | ~$0.30 rehydration (R2.6 paper backfill, capped at $1) + ~$1.50/mo ongoing (~$0.05/day for family interactions) | Capped at $10/mo via Anthropic console budget per CLAUDE.md cost section; well below $40/mo full-tier cap |
| Whisper (OpenAI) | <$0.50/mo | Voice transcription ~$0.006/min; ~10 min/day intake estimated |
| **Total monthly** | **~$10-15/mo** | Within $20-30 MVP ceiling per CLAUDE.md project constraint |

Sprint-cost during execution (one-time):
- R0 + R1 + R2 + C1 LLM: ~$0.50 (verify reruns + smoke).
- R2.6 paper backfill: ~$0.30 (capped at $1).
- C3 + C4 + C5: ~$0 (engineering work; no LLM calls except spec drafts ~$0.50).
- C2 soak: ~$0.05/day × 14 days = $0.70.
- **Total sprint LLM:** ~$2 (well under monthly cap).

---

## §8. What this plan does NOT cover

Carried forward from COMPLETION_PLAN §7 plus S1 additions:

- **TVB whole-brain simulation** — only the stub lands in C5/G4; actual Docker-driven simulations are Phase 7+.
- **brain2print STL export pipeline** — nii2mesh → meshlab/pymeshfix watertight pass; Phase 7+.
- **Multi-tenant Supabase Auth** — single-operator scope locked (Shako = MANAGER_USER_ID). Phase 7+.
- **Hindsight self-improving memory** — Phase 3+ post-MVP.
- **Prism MCP HIPAA-hardened on-device memory** — defer until a clinician needs read access.
- **Anything that breaks the $20-30/mo MVP budget cap** — implies Firecrawl Pro, Anthropic over $40/mo, Railway over $25/mo, or new SaaS.
- **Deep-clinical viewer features** (radiologist tracing, ROI measurement, DICOM windowing) — Phase 7+.
- **R3F v10 migration** — stick with R3F 9.6.x stable per CLAUDE.md stack notes.
- **`plan_brain_swarm_architecture` MCP tool** — explicitly killed in C3.7 (recursive LLM self-planning has unbounded cost).
- **Branch A.2 separate digest worker** — explicitly deferred to Phase 7 (S1 chose A.1).
- **Branch B.3 Cloudflare Pages migration** — explicitly deferred to Phase 7+ (S1 chose B.2).
- **Multi-region Railway worker (RISK-15)** — single-replica is acceptable for single-patient MVP; Phase 7 candidate if Railway availability becomes a concern.
- **Anthropic content-filter remediation for the ~200 stalled papers beyond the R2.6 $1 cap** — if backlog persists past R2.6, defer remaining items to Phase 7 chunk-rework.
- **Calendar of n8n maintenance windows** — `daily-budget-gate` JSON-body expression bug code-side fix is already in; the deployed workflow restart will land naturally with R0.6's n8n container swap.

---

*End of MASTER_PLAN. Owner: Shako Jincharadze. Next action: review §5 branches → make 3 decisions (A, B, C) → start R0.1.*
