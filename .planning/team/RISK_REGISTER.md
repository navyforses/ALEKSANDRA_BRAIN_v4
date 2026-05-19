# ALEKSANDRA_BRAIN — Cross-Cutting Risk Register

**Agent:** S1 (Wave 3 — synthesizer)
**Date:** 2026-05-19
**Companion to:** `.planning/team/MASTER_PLAN.md`
**Inputs synthesized:** REPAIR_PLAN §7, COMPLETION_PLAN §8, INVESTIGATION-OPS open questions, INVESTIGATION-PHASE6 open questions, INVESTIGATION-CGM01, audit §1/§4/§5/§7.

Legend:
- **Likelihood:** L (<25%) / M (25-65%) / H (>65%)
- **Impact:** L (cosmetic/recoverable) / M (1+ phase regresses but recoverable in ≤2 hrs) / H (multi-day outage or data loss)
- **Status:** OPEN / MITIGATED-IN-PLAN / DEFERRED / RESOLVED-BY-INVESTIGATION

---

| ID | Risk | Likelihood | Impact | Owner | Mitigation | Source |
|---|---|---|---|---|---|---|
| RISK-01 | n8n encryption-key loss during R0.6 Docker swap → all stored credentials (Supabase service key, Telegram bot, Gmail OAuth, NCBI key) become unreadable → 11 workflows + OAuth need re-import | M | H | Shako | Pre-flight: Railway service → Volumes → "Create snapshot" BEFORE source swap (R0.6 step 1). Preserve `N8N_ENCRYPTION_KEY` env var unchanged across swap. Post-swap smoke: login + test-run one workflow; if credentials dimmed, restore snapshot. | REPAIR_PLAN §7.1, MASTER_PLAN R0.6 |
| RISK-02 | Worker endpoints `/fire-daily-batch` and `/render-weekly-brief` do not exist in `scripts/perception_worker.py` → workflows `telegram_daily_digest.json` + `weekly_brief.json` POST to dead routes → Phase 4 acceptance (C2) silently fails (briefs stays 0 through 2026-06-07) | H | H | D1-Q7 must resolve before R1 activation. S1 chose **Branch A.1** in MASTER_PLAN §5: add 2 routes to `perception_worker.py` modeled on `/daily-spend-report`; ship in R0.8 atomic commit; verify both endpoints return 200 via curl before R1.1. | D1 finding §7.2 (S1-verified: grep returns 0 hits) |
| RISK-03 | Vercel SSO gate (401 on `viewer-git-main-…`) blocks family access to viewer entirely → C1 smoke cannot happen → C2 cannot deliver family value | H (current state) | H | Shako + S1 | Branch B in MASTER_PLAN §5. Recommended: **B.2** — add team-seat invites for Shako + Sopo + (optional) clinicians, free at Hobby tier up to 3 seats. Fallback B.1 if seat limit hit. Decision required in R2.3 before C1. | D2 open #1, audit §4.6 |
| RISK-04 | `MANAGER_USER_ID=shako-jincharadze` is a string, not a uuid → if Supabase `manager_actions.user_id` column is `uuid` type, every Phase 5 action returns 500 → Phase 5 production traffic impossible | M | H | Claude (probe) + Shako (decide) | Before R0.4, run: `select column_name, data_type from information_schema.columns where table_name='manager_actions' and column_name='user_id';`. If uuid, generate a real UUID for Shako, update `.env` line 124 + Vercel env. R2 hardening item — verify pre-C1. | REPAIR_PLAN §7.5, INVESTIGATION-OPS Q5 |
| RISK-05 | 6 missing Supabase tables (`llm_call`, `citations`, `digest_to_run_link`, `telegram_history`, `email_log`, `firecrawl_calls`) — code may reference them and fail silently or insert into nowhere | M | M | Claude | Branch C.1 in MASTER_PLAN §5: write migration `012_missing_tables.sql` to create all 6 (S1's recommendation per D2). Apply during R2.4 / C5. Verify via Supabase REST `count='exact'` returns row counts (even if 0). | D2 open #4, audit §4.1 |
| RISK-06 | `viewer/vercel.json` or `viewer/next.config.ts` may override or conflict with Root Directory fix → R0.2 redeploy still fails after R0.1 | L | M | Claude | Pre-R0.2: Glob `viewer/vercel.json` (confirmed-absent in INVESTIGATION-OPS) AND Read `viewer/next.config.ts` for any `../` or repo-root-relative paths. If exists, edit before redeploy. R0.2 build logs surface any remaining error. | REPAIR_PLAN §7.3, INVESTIGATION-OPS |
| RISK-07 | nibabel 3.x bug at `mcp/aleksandra_niivue_mcp.py:31` (`header.get_affine()` removed in nibabel 3.x) → silent failure or `AttributeError` on first MCP `load_nifti` call in C4 | M | L | Claude | C3.4 fix scheduled — replace with `img.affine` (canonical nibabel 3+ API). Probe: `python -c "import nibabel as nib; img=nib.load('tests/fixtures/test_brain_128.nii.gz'); print(img.affine.shape)"` returns `(4, 4)`. | INVESTIGATION-PHASE6 R3 finding |
| RISK-08 | Fabricated `vulnerability_to_hie: 0.85` in `scripts/brain_builder_swarm.py` violates CLAUDE.md "ფაქტი არ გამოიგონო" principle → if file ever executes, fabricated number leaks into outputs | L | M | Claude | C3.5 deletes the file outright (already classified REFERENCE-ONLY by R3; no integration path). Probe: `git ls-files scripts/brain_builder_swarm.py` returns empty after C3.5. | INVESTIGATION-PHASE6 R3 finding |
| RISK-09 | 2 banned-gradient HTML files (`viewer/brain_voxels.html`, `viewer/neuron_3d.html`) violate DESIGN.md §2 → if anyone navigates to them in `viewer/`, they break the design system | L | L | Claude | C3.3 archives both to `.planning/research/visualization-demos/`. Probe: `ls viewer/*.html 2>/dev/null` returns 0 lines. | INVESTIGATION-PHASE6 R3 finding |
| RISK-10 | Phase 4 acceptance window closes ~2026-06-07 with `briefs=0` — if RISK-02 unresolved, both Sundays 2026-05-24 + 2026-05-31 see workflows fire against dead endpoints → C2 fails | H if RISK-02 not resolved | H | Shako | RISK-02 mitigation (Branch A.1) is the only fix. If Branch A.1 work slips past 2026-05-23, fall back to Branch A.3 (manual weekly brief) for the first Sunday to capture `prod_clinician_drafts += 1`, then complete A.1 for the second Sunday. | MASTER_PLAN §3, calendar |
| RISK-11 | Re-deploy after Vercel root-dir fix (R0.1 → R0.2) may STILL fail for other reasons (e.g., next.config.ts path issues, missing build deps, stale lockfile swc warning) | M | M | Shako | R0.2 verify probe captures HTTP code; if !=200/401, escalate to fallback Branch B.3 (Cloudflare Pages migration, deferred Phase 7+). Build log analysis: capture verbatim error and route to S1 for diagnosis. | REPAIR_PLAN §7.3, MASTER_PLAN R0 |
| RISK-12 | Phase 6 integration needs Redis decision — `agents/swarm/celery_app.py` is wired but never connects (no `REDIS_URL` in `.env`) → silent latent dependency | L | L | Claude | C3.8 deletes Celery branch per R3 + PHASE_5_INPUTS item 8 recommendation. Multiprocessing-only path in `swarm_orchestrator.py` is the production path. Saves ~$5/mo Railway. | INVESTIGATION-PHASE6, PHASE_5_INPUTS item 8 |
| RISK-13 | PHI/stdio gate for `aleksandra-niivue-mcp` not enforced — risk of accidental SSE/HTTP exposure of MRI data if MCP is invoked with wrong transport | L | H | Claude | C3.9 — add docstring + RuntimeError on HTTP/SSE transport instantiation; document stdio-only requirement in MCP-INVENTORY row (C3.6). Verify end-to-end in C4: attempt `mcp.client.http_client` → RuntimeError; `mcp.client.stdio_client` → succeeds. | INVESTIGATION-PHASE6, PHASE_5_INPUTS item 9 |
| RISK-14 | C2 acceptance window is calendar-bound (14 days, two Sundays) — cannot compress regardless of engineering parallelism | H (will happen) | M | Shako | MASTER_PLAN Gantt makes R2/C3/C4/C5 run in PARALLEL with C2 soak so engineering throughput isn't lost to wall-clock. Calendar dictates milestones, not throughput. | Calendar constraint |
| RISK-15 | Railway worker `aleksandra-worker-production` is single-replica → any Railway outage = no Phase 5 service → manager_actions write path dies | M | M | DEFERRED to Phase 7+ per MASTER_PLAN §8 out-of-scope. Single-patient MVP tolerates short outages; multi-region adds infra cost outside $20-30 cap. Monitoring: panic-stop workflow alerts on healthz failure. | MASTER_PLAN §8 |
| RISK-16 | Bulk `git add` could pull in 33 untracked Phase 6 scaffold files (5,073 LOC) into R0.8's atomic commit → unreviewed code lands on main | L | M | Claude | R0.8 mandates explicit path-list staging (7 paths). DO NOT use `git add .` or `git add -A`. R0.8 step 1 in REPAIR_PLAN §3 enumerates exact paths. | REPAIR_PLAN §7.6, audit §3 |
| RISK-17 | `aleksandra-brain-v4.vercel.app` referenced by `docs/PHASE_5_OPERATOR_RUNBOOK.md` + `.claude/plans/5-warm-crown.md` Phase E does NOT exist as a Vercel alias → operators hit DEPLOYMENT_NOT_FOUND | M | L | Shako + Claude | R2.3 resolves via Branch B (also fixes alias question simultaneously). Either create alias OR sweep docs to use stable alias (`viewer-sigma-two.vercel.app`). Not blocking for R0 but creates onboarding friction. | REPAIR_PLAN §7.8, audit §4.6 |
| RISK-18 | `tests/fixtures/healthy_brain_points.json` (~15MB) + `damaged_brain_points.json` (~25MB) too large for plain git → repo bloat or commit rejection | L | L | Claude | D2 open #6: choose Git LFS (B.1) vs gitignore+regenerate (B.2). S1 leans **regenerate-on-demand** per R3 recommendation — source `.nii.gz` already committed, `nifti_to_pointcloud.py` regenerates deterministically. Address during C3.3 archive move. | INVESTIGATION-PHASE6 R3, D2 open #6 |
| RISK-19 | `enhanced_detector.py` lesion output lacks provenance fields → if it feeds clinical PDFs without `model_version`, `reference_dataset`, `source: "model"` tag, it violates VIS-* analog of CGM-01 → fabricated clinical claims | M (if C4 ships without C3.9 follow-through) | H | Claude | C3.9 adds stdio gate; C4 adds provenance schema (VIS-02). VIS-02 must block any Communicator PDF that lacks the 3 fields. Probe: clinician PDF export contains `[Model output: BIBSnet v1.x, BONBID-HIE 2024 ref]` label visibly. | INVESTIGATION-PHASE6 R3 item 10 |
| RISK-20 | Anthropic content-filter 400 errors on ~200 stalled papers may not all resolve under the $1 cap during R2.6 → Neo4j growth stalls below the ~900-node target | M | L | Claude | R2.6 hard-cap at $1 spend; remaining items roll to Phase 7+ chunk-rework. Not blocking for C6 acceptance (Neo4j size is informational, not a verifier gate). | REPAIR_PLAN R2.6 |
| RISK-21 | n8n `daily-budget-gate` workflow JSON-body expression bug (code-side fix already in repo) won't take effect until n8n deployment restart in R0.6 → `ANTHROPIC_USAGE_API_KEY` placeholder leaves daily-spend reads at $0 → false budget headroom for any code that consults this fallback | L | M | Shako | R2.5 reconnects `ANTHROPIC_USAGE_API_KEY` after R0.6 brings n8n alive. Code-side `check_daily_budget()` is the live backstop until then (per CLAUDE.md operational caveat). | CLAUDE.md known caveat, REPAIR_PLAN R2.5 |
| RISK-22 | `gsd-spec-phase` for C4 (NiiVue integration) may surface unknown unknowns about `@niivue/nvreact` API compatibility, requiring spec rework → C4 ETA slips beyond Gantt W2 | M | M | Claude | `viewer/AGENTS.md` warning ("read `node_modules/next/dist/docs/` before writing") must be honored before authoring component. Spec drafted W2 Mon, mount W2 Tue — if spec slips, push mount to W2 Wed (Gantt has 4 days, 1 day buffer). | INVESTIGATION-PHASE6 open Q, MASTER_PLAN §3 |
| RISK-23 | Vercel Hobby tier free-team-seat limit (Branch B.2) may force upgrade to Pro at $20/mo → escapes $20-30 MVP budget cap | M | M | Shako | Mitigation: keep team to 3 (Shako + Sopo + 1 clinician). If 4+ needed, fall back to Branch B.1 (public alias) with PHI-name redaction sweep on page titles. | MASTER_PLAN §5 Branch B, CLAUDE.md $20-30 cap |
| RISK-24 | Phase 6 verifier (`verify_phase6.py`) doesn't exist yet → cumulative 91/91 cannot be measured at C6 until verifier is authored | H (current state) | M | Claude | C4 deliverable includes `scripts/verify_phase6.py` with VIS-01..05 + REGR. Skeleton modeled on `verify_phase5.py --mode code-complete`. C6 gate cannot fire without this. | COMPLETION_PLAN §6 |
| RISK-25 | "78/78 cumulative coverage" claim in CLAUDE.md is currently false (audit §6: actual 73/78 due to CGM-01 + 4 REGR cascades) → R2.1 must truth-up before C6 master verifier runs | H (verified) | L (doc-only) | Claude | R2.1 edits CLAUDE.md "მიმდინარე ეტაპი" after R0.7 lands so CGM-01 is genuinely PASS; update entity count 568 → 641 to match Neo4j reality; surface Vercel-broken + n8n-broken caveats until R0 closes them. | Audit §6, REPAIR_PLAN R2.1 |

---

## Risk summary by impact

**High-impact open risks (require Shako decision BEFORE execution starts):**
1. RISK-02 (D1-Q7 digest endpoints — MASTER_PLAN §5 Branch A.1 recommended)
2. RISK-03 (Vercel SSO gate — MASTER_PLAN §5 Branch B.2 recommended)
3. RISK-05 (6 missing Supabase tables — MASTER_PLAN §5 Branch C.1 recommended)

**High-impact risks mitigated by plan:**
- RISK-01 (n8n encryption key) — mitigated by mandatory volume snapshot in R0.6
- RISK-04 (MANAGER_USER_ID type) — mitigated by pre-R0.4 column-type probe
- RISK-10 (Phase 4 acceptance) — depends on RISK-02 resolution
- RISK-13 (PHI/stdio gate) — mitigated by C3.9 + C4 end-to-end check
- RISK-19 (lesion provenance) — mitigated by C3.9 + C4 VIS-02 schema

**Medium-impact tracking items:**
- RISK-11 (Vercel redeploy may still fail post-root-dir) — fallback to Branch B.3
- RISK-14 (calendar-bound C2 soak) — accepted; engineering runs in parallel
- RISK-22 (C4 spec surprises) — 1-day buffer in Gantt
- RISK-23 (Vercel free-tier seat cap) — fallback to Branch B.1

**Low-impact, plan-mitigated:**
- RISK-06/07/08/09/12/16/17/18/20/21/24/25 — all have explicit plan tasks or are doc-only

---

## Risks deferred (out of scope per MASTER_PLAN §8)

- RISK-15 (single-replica worker resilience) — Phase 7+
- (Branch A.2 separate digest worker) — Phase 7+
- (Branch B.3 Cloudflare Pages migration) — Phase 7+
- (TVB, brain2print, multi-tenant Auth, Hindsight, Prism) — Phase 7+

---

*End of RISK_REGISTER. Owner: Shako Jincharadze. Companion to MASTER_PLAN.md.*
