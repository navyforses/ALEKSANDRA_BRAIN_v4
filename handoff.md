# Handoff — ALEKSANDRA_BRAIN v7.0 closure batch

> **დათარიღება:** 2026-05-15 (per user explicit instruction; system wall clock during this session read 2026-05-25, see §6)
> **Model:** `claude-opus-4-7` (Claude Opus 4.7, Fast mode)
> **Session ID:** `70b0b944-c452-403d-96ec-ffc81c75e08f`
> **Transcript path:** `C:\Users\jinch\.claude\projects\c--Users-jinch-OneDrive--------------aleksandra-brane\70b0b944-c452-403d-96ec-ffc81c75e08f.jsonl`
> **Previous handoff archived to:** `.handoffs/handoff-2026-05-15-2230.md`
> **Branch:** `v7-phases-7-0-to-7-5-closure` (15 commits ahead of `main`, HEAD `5bd97f7`)
> **Resume update (2026-05-28):** §9 confirmation commands re-run from a fresh shell surfaced 5 small bugs (stale Hagmann assertion in `test_load_default_connectome_metadata_shape`, missing `sys.path` guard in verifiers 7.0/7.1/7.2, undersized pytest timeout in `verify_phase_7_2` check 12, stale `middleware.ts` path in `verify_phase_7_5` check 1). All five fixed in commit `6f8e05e fix(v7): post-handoff verifier + test hygiene (8/8 GREEN)`. All 8 verifiers now GREEN, pytest 658 PASS, viewer build PASS. The 11 staged design/AGENTS files (§3) committed separately in `5bd97f7 docs(design): fresh-site concept brief + 8 specialist inputs + AGENTS.md` after user approval. PR strategy confirmed by Shako: keep 14 atomic commits, do **not** squash.

---

## 1. Goal

**Objective (1-2 sentences):** drive ALEKSANDRA_BRAIN v7.0 (digital twin medical AI for Aleksandra — severe HIE, cystic encephalomalacia, preserved brainstem) from the post-compact state (Phase 7.0/7.1 closed pre-compact, Phase 7.2 Days 1-10 done) through ALL remaining phase closures (7.2 Days 11-15, 7.3 A+C, 7.3 Layer B TVB, 7.4, 7.5, 7.6, 7.7 scaffold) and commit them to a single feature branch ready for Shako's PR review.

**Definition of done (explicit):**
- 13 commits on `v7-phases-7-0-to-7-5-closure` covering all 8 phases (7.0 foundation + 7.1 memory + 7.2 causal + 7.3 A+C + 7.3 Layer B + 7.4 active + 7.5 constitutional + 7.6 site + 7.7 scaffold) + 5 maintenance/fix commits
- `pytest brain/ -m "not slow"` ≥ 658 PASS, exit 0 modulo 1 known flake
- `cd viewer && npx tsc --noEmit` exit 0
- `cd viewer && npm run build` exit 0 (all 8 routes incl. 4 new from 7.6)
- All 8 phase verifier scripts `--mode code-complete` exit 0 (PASS or SKIP, never FAIL)
- All carry-forwards from each phase either resolved or explicitly assigned in the todo list
- `main` branch UNTOUCHED — PR merge is Shako's call

**Scope boundaries (NOT in this session):**
- ❌ Production database migrations (016/017/018/019/020/021/022/022b/023) — all written + runbooks authored; Shako applies in operator session
- ❌ Live Telegram bot send (Phase 7.4 outbound) — dry-run only
- ❌ Live Anthropic / LiteLLM API calls — zero LLM spend session-wide
- ❌ Real Aleksandra MRI segmentation server-side (CLAUDE.md client-only rule)
- ❌ Browser visual rendering of Plotly / vis-network / react-flow (no browser; structural-complete only — Shako runs `npm run dev`)
- ❌ Real wife/doctor sessions (Phase 7.7 templates only; live sessions late-Dec 2026 → early-Jan 2027)
- ❌ Vercel deploy / git push to origin / GitHub PR / GitHub Actions trigger
- ❌ `npm install` of new packages (deps from Phase 6 already in `viewer/node_modules/`)
- ❌ Docker image pull (TVB image already local; tag `latest`)
- ❌ Phase 7.6 frontend visual review / Lighthouse perf budget verification

---

## 2. Current state

### What works (verified, with verification command)
| Surface | Status | Verified via |
|---|---|---|
| `pytest brain/ -m "not slow"` | **658 PASS · 1 skip (reportlab missing) · 4 deselected (slow)** | `.venv-v7/Scripts/python.exe -m pytest brain/ -m "not slow" -q --tb=no` (last run ~424s) |
| `pytest brain/` test count | **660/664 collected** | `.venv-v7/Scripts/python.exe -m pytest brain/ -m "not slow" --collect-only -q` (81s) |
| TypeScript baseline (viewer) | **tsc --noEmit exit 0** | `cd viewer && npx tsc --noEmit` |
| Next.js production build | **npm run build exit 0** — all 8 routes (incl. /[locale]/{twin,causal,simulate,drift}) compile | `cd viewer && npm run build` (post middleware/proxy merge) |
| Verifier 7.0 code-complete | 10/11 PASS · 1 SKIP (RLS migration-gated) · 0 FAIL · GREEN | `.venv-v7/Scripts/python.exe scripts/verify_phase_7_0.py --mode code-complete` |
| Verifier 7.1 code-complete | 2/9 PASS · 7 SKIP (Neo4j-gated) · 0 FAIL · GREEN | `python scripts/verify_phase_7_1.py --mode code-complete` |
| Verifier 7.2 code-complete | **12/12 PASS · 0 SKIP · 0 FAIL · GREEN** | `python scripts/verify_phase_7_2.py --mode code-complete` |
| Verifier 7.3 code-complete | **13/13 PASS · 0 SKIP · 0 FAIL · GREEN** (Layer B TVB live 1s sim 16.3s wall) | `python scripts/verify_phase_7_3.py --mode code-complete` |
| Verifier 7.4 code-complete | **10/10 PASS · 0 SKIP · 0 FAIL · GREEN** | `python scripts/verify_phase_7_4.py --mode code-complete` |
| Verifier 7.5 code-complete | 11/3 PASS · 3 SKIP (DB-trigger-gated for migrations 021/022/022b/023) · 0 FAIL · GREEN | `python scripts/verify_phase_7_5.py --mode code-complete` |
| Verifier 7.6 code-complete | 11/12 PASS · 1 SKIP (next build now actually PASSes post-merge — re-run to flip SKIP→PASS) · 0 FAIL · GREEN | `python scripts/verify_phase_7_6.py --mode code-complete` |
| Verifier 7.7 code-complete | 1/10 PASS · 9 SKIP (human sessions late-Dec → Jan) · 0 FAIL · GREEN exit 0 | `python scripts/verify_phase_7_7.py --mode code-complete` |
| Docker daemon | Docker Desktop 4.73.1 reachable; TVB image `thevirtualbrain/tvb-run:latest` (10.6GB-on-disk / 3.54GB content) local | `docker version && docker images thevirtualbrain/tvb-run` |
| TVB live 1-second sim | Completes in 16.3s wall via `run_tvb_simulation(TVBSimulationRequest(duration_ms=1000, ...))` | brain/sim/tests/test_tvb_adapter.py::test_live_tvb_simulation_1_second_completes (conditional skip if Docker unavailable) |
| Reference SCM (Vigabatrin → Seizure freq, 5 nodes / 6 edges, Age confounder + GABA-T mediator + Neuroplasticity moderator) | DoWhy `identify_effect` returns `NONPARAMETRIC_ATE` with `backdoor=['Age (months)']` | brain/causal/tests/test_dowhy_bootstrap.py |
| Refute pass-rate | 2/2 PASS on reference SCM (`random_common_cause + placebo_treatment_refuter`) | verify_phase_7_3 check 7 |
| Structure learning F1 | 0.55 (P=0.60 / R=0.50) on n=1000 synthetic reference | verify_phase_7_2 check 11 |
| 13-dim catalog citation completeness | 13/13 dimensions cite real PubMed PMIDs (Phase 7.0 Days 7-9 librarian work) | brain/belief/tests/test_schema.py::test_live_catalog_has_zero_stubs |
| Hagmann PMID grounded | PMID 18597554 (real, PubMed-verified post-Phase-7.3-Layer-B); TVB framework PMID 23781198 | brain/sim/tvb_adapter.py docstrings (last commit `e55ef6a`) |

### What's broken or partial
| Item | Status | Severity |
|---|---|---|
| `test_higher_confidence_level_widens_ci` (brain/causal/tests/test_estimators.py) | Passes in isolation (77s); FLAKES ~5% of the time in cumulative `pytest brain/` runs. DoWhy 0.14 bootstrap CI variance on small samples. | LOW · documented carry-forward; verifier check 12_7_3_12 / 13_7_4_10 etc. tolerate it |
| TVB upstream image `thevirtualbrain/tvb-run` | DockerHub readme flags "Updates discontinued after version 26.7.x" | MEDIUM · use `:latest` (TVB 2.11.0) for now; build custom anaconda/miniconda replacement before next major dependency churn |
| `viewer/middleware.ts` | DELETED in commit `1073cec`; logic merged into `viewer/proxy.ts`. Phase 7.5 constitutional test repointed in commit `61b1729`. | RESOLVED |
| Phase 7.5 migrations 021/022/022b/023 | Written + runbooks authored; NOT applied. Verifier checks SKIP in code-complete. | EXPECTED · operator-pending |
| 9 Phase 7.7 doc templates with `<TO BE FILLED IN BY SHAKO>` placeholders | Code-complete scaffold; live wife/doctor sessions late-Dec 2026 → early-Jan 2027 | EXPECTED · calendar-gated |
| Phase 7.0 production verifier check 11 (RLS smoke) | SKIP-gated on migration 016 apply | EXPECTED · operator-pending |
| Phase 7.1 production verifier (7 checks) | SKIP-gated on Neo4j 017 cypher + classify + backfill + cross_link | EXPECTED · operator-pending |
| Phase 7.4 live Telegram outbound | dry-run only; live gated on Shako bot-token env vars + n8n perception_tick restart (v6.1 op #3 still pending) + Phase 4 acceptance window closure | EXPECTED · operator-pending |

### Branch + last commits (git snapshot)
- **Current branch:** `v7-phases-7-0-to-7-5-closure`
- **HEAD SHA:** `e55ef6ac1a923d03373073e66e885f11f0305d5b` (short `e55ef6a`)
- **Commits ahead of `main`:** 13
- **Total diff vs main:** 261 files changed · 53,871 insertions(+) · 17 deletions(-)
- **`main` last commit:** `c38c856 feat(viewer): move /audit + /brain under [locale]/ for full bilingual support`

**Last 15 commits on feature branch (chronological, oldest → newest):**
```
86e1a3c  feat(v7): Phase 7.0 Belief Foundation + v7 architecture seed         73 files
3ae9415  feat(v7): Phase 7.1 Memory Refactor — Pearl 5-type SCM edge taxonomy 21 files
90438db  feat(v7): Phase 7.2 Causal Layer — DoWhy SCM + do() API + SCM editor 30 files
c8adb43  feat(v7): Phase 7.3 Simulation Engine Layers A+C (Monte Carlo + Studio) 24 files
76668a0  feat(v7): Phase 7.4 Active Learning — EIG + question gen + Telegram dry-run 28 files
c5ffe20  feat(v7): Phase 7.5 Constitutional Code — 13 inviolable rules        31 files
44a5e35  feat(v7): Phase 7.7 Acceptance Window — code-complete scaffold       15 files
452a060  fix(verifier): recognize [locale]/brain/ path in MNG-01 check         1 file
1073cec  fix(viewer): merge Phase 7.5 middleware.ts into proxy.ts (Next.js 16)  2 files
5b4cff6  feat(v7): Phase 7.6 Site Refactor — 4 NEW routes + 4 widget refactors 34 files
bbcfcbb  feat(v7): Phase 7.3 Layer B — TVB Docker integration (Days 6-10)      6 files
61b1729  fix(test): point Rule #1 constitutional test at proxy.ts (post-merge) 1 file
e55ef6a  chore(v7): ground Hagmann PMID + ignore verifier run logs             3 files
6f8e05e  fix(v7): post-handoff verifier + test hygiene (8/8 GREEN)             5 files  [2026-05-28]
5bd97f7  docs(design): fresh-site concept brief + 8 specialist inputs + AGENTS.md 11 files  [2026-05-28]
```

### Dirty files (`git status --short`)
**Resolved 2026-05-28** — working tree clean after `M handoff.md` lands in the next commit. All 11 design/AGENTS files committed in `5bd97f7` as a single `docs(design):` commit per Shako's choice (option 1 of AskUserQuestion).

Original snapshot (pre-resume):
```
M  .planning/design/briefs/2026-05-25-fresh-site-concept.md           [staged, NOT MINE — design-director agent output]
A  .planning/design/concept-inputs/01-08-*.md                         [8 specialist inputs, NOT MINE]
A  .planning/design/concept/2026-05-25-fresh-site-concept-v1.md       [staged, NOT MINE]
A  AGENTS.md                                                           [staged, NOT MINE — Codex companion to CLAUDE.md]
```
Resolution: bundled into one `docs(design): fresh-site concept brief + 8 specialist inputs + AGENTS.md` commit (`5bd97f7`).

### Services / ports / background processes
- **Docker Desktop 4.73.1** running (Windows desktop-linux context). TVB image local. No long-running containers; every `run_tvb_simulation` call uses ephemeral `--rm --name tvb-aleksandra-<uuid>`.
- **Postgres / Supabase**: NOT touched this session. `SUPABASE_DB_URL` env var unset → all CRUD modules took DRY_RUN-sentinel path.
- **Neo4j AuraDB**: NOT touched this session (Phase 7.1 production-pending).
- **Railway services**: NOT touched. n8n `daily-budget-gate` workflow restart still pending (v6.1 carry-over).
- **Vercel**: NOT touched. Phase 6.1 push pending; Phase 7.6 + middleware/proxy fix bundled in.
- **Next.js dev server**: NOT running. Only `npm run build` exercised post-merge.
- **No background pytest** or other long-running processes left at session end.

---

## 3. Active files

### Files edited this session that may need follow-up

| Path | Purpose (1-line) | Pending change / next action |
|---|---|---|
| `brain/sim/tvb_adapter.py` | TVB Docker adapter (Days 6-10 of Phase 7.3 Layer B) | None — Hagmann PMID grounded in commit `e55ef6a`. Carry-forward: replace upstream `tvb-run` image with anaconda/miniconda custom build. |
| `brain/sim/tests/test_tvb_adapter.py` | 27 tests for TVB adapter (26 mocked + 1 conditional-live) | None |
| `brain/common/tests/test_constitutional.py` | 14 constitutional rule tests | Repoint complete (commit `61b1729`); if any future test renames middleware→proxy elsewhere, mirror pattern |
| `viewer/proxy.ts` | next-intl proxy + Phase 7.5 Rule #1 CSP + DICOM rejector (merged from deleted middleware.ts) | None — `npm run build` PASS confirmed |
| `viewer/middleware.ts` | DELETED (commit `1073cec`) | None |
| `scripts/verify_phase_7_2.py` | 12-check verifier | Refute fix landed (raw DoWhy objects passed instead of Pydantic wrapper) |
| `scripts/verify_phase_7_3.py` | 13-check verifier (Layer A+C+B) | Checks 7/8/9 flipped SKIP→PASS post Layer B |
| `scripts/verify_phase_7_6.py` | 12-check verifier | Check 7_6_07 (`next build`) now PASSes since middleware/proxy merge — re-run will flip SKIP→PASS (not regenerated this session) |
| `.gitignore` | + verifier JSON glob + graphify-out/ + .codex/ | None |
| `docs/PHASE_7_3_LAYER_B_EXIT_REPORT.md` | Layer B closure | Hagmann PMID deviation #3 + middleware deviation #6 both marked RESOLVED |

### Files PENDING decision (staged by another tool/agent — NOT MINE)
| Path | Owner | Recommended action |
|---|---|---|
| `.planning/design/briefs/2026-05-25-fresh-site-concept.md` | `design-director` agent | ask user — separate `docs(design): fresh-site concept` commit OR discard |
| `.planning/design/concept-inputs/01-08-*.md` (8 files) | `design-director` agent sub-agents (a11y / dataviz / IA / motion / visual-tokens / voice / audience / 3D-MRI) | same — bundle with brief, separate commit |
| `.planning/design/concept/2026-05-25-fresh-site-concept-v1.md` | `design-director` agent | same |
| `AGENTS.md` (root, NOT viewer/AGENTS.md which is committed) | unknown — check `git log -p --all -- AGENTS.md` first | ask user |

### Files SHAKO will edit during production-apply
| Path | Trigger |
|---|---|
| `scripts/migrations/016_runbook.md` → execute commands | Phase 7.0 production session |
| `scripts/migrations/017_runbook.md` → execute Neo4j cypher | Phase 7.1 production session |
| `scripts/migrations/018_runbook.md` → execute psql | Phase 7.2 production session |
| `scripts/migrations/019_runbook.md` → execute psql | Phase 7.3 production session |
| `scripts/migrations/020_runbook.md` → execute psql + n8n restart | Phase 7.4 production session |
| `scripts/migrations/021_runbook.md` + `022_*_runbook.md` + `022b_*_runbook.md` + `023_runbook.md` | Phase 7.5 production session (4 migrations) |
| `docs/SHAKO_HANDOFF_2026-05-25.md` | Phase 7.0 6-step session |
| `docs/PHASE_7_7_*` template fills | Phase 7.7 live sessions late-Dec → Jan |

### Mirror of active TodoWrite list
```
✓ Phase 7.0 / 7.1 / 7.2 / 7.3 A+C / 7.3 Layer B / 7.4 / 7.5 / 7.6 / 7.7 scaffold closure
✓ Hagmann + TVB PMID grounded (18597554 + 23781198)
✓ .gitignore cleanup (verifier JSON logs + graphify-out + .codex)
✓ Middleware/proxy merge + constitutional test repoint
✓ FULL v7 CODE-COMPLETE — 13 commits / ~265 files / ~54.5k insertions / 658 tests / 8/8 verifiers GREEN / npm build PASS

PENDING:
□ [shako BROWSER SMOKE] npm run dev + 8 routes
□ [shako] merge v7-phases-7-0-to-7-5-closure → main (13 commits)
□ [shako/wife] v6.1 op #2 — wife rebuild 7 blank rows
□ [shako ACTIONS] docs/SHAKO_HANDOFF_2026-05-25.md — Phase 7.0 + v6.1/P2 closure
□ [passive] Phase 4 acceptance window closure ~2026-06-07
□ [shako APPLIES] Phase 7.1 production (Neo4j + 017 cypher)
□ [shako APPLIES] Phase 7.2 production (migration 018 + tag v7.2.0)
□ [shako APPLIES] Phase 7.3 production (migration 019 + tag v7.3.0)
□ [shako APPLIES] Phase 7.4 production (migration 020 + n8n restart + bot tokens + tag v7.4.0)
□ [shako APPLIES] Phase 7.5 production (migrations 021+022+022b+023 + GitHub Actions push + tag v7.5.0)
□ [shako runs] Phase 7.7 acceptance window late-Dec 2026 → early-Jan 2027
□ [carry-forward] Replace deprecated tvb-run image with custom anaconda/miniconda build
□ Flaky-test carry-forward: test_higher_confidence_level_widens_ci
□ [DECIDE] 11 staged design files — commit separately or discard?
```

---

## 4. Decisions & tradeoffs

### Architectural choices this session (with rationale)

1. **Sequential phase dispatch via general-purpose agent (not custom v7-* subagent_type).** The 11 v7-* agent definitions in `.claude/agents/` were created in a prior session but the Claude Code runtime in THIS session did NOT resolve them as valid `subagent_type` values. Workaround: dispatch via `subagent_type: "general-purpose"` and tell the agent to read its role file (e.g. `.claude/agents/v7-bayes.md`) as part of its FIRST-context. This worked reliably for all 7 dispatches.
2. **Code-complete-without-infra discipline.** Every CRUD module (`brain/{causal,sim,active,common}/persistence`, `cross_link`, `overrides`, etc.) mirrors the Phase 7.0 DRY_RUN-when-`SUPABASE_DB_URL`-unset pattern from `brain/causal/cross_link.py`. Returns `"DRY_RUN:<sha256>"` sentinel + logs to stderr when no DB. Lets every verifier exit 0 in code-complete mode without a live Supabase.
3. **FastAPI handlers framework-agnostic.** Phase 7.2 spec called for `POST /api/causal/do`; this session shipped `handle_do_query(req)` as a pure Pydantic-typed function with NO FastAPI mount. Same pattern for 7.3 (`brain/sim/api.py`), 7.4 (telegram_flow / response_parser handlers). Reason: FastAPI not installed in `.venv-v7`, and the framework choice is a Phase 7.6+ frontend bootstrap concern.
4. **matplotlib for Phase 7.3 Layer C PNG export, not Plotly + Kaleido.** Plotly only in viewer/ (npm), not Python venv. matplotlib already used in `brain/belief/viz.py`. Substitution preserves the deliverable (13-PNG histogram export) without adding a Python dep.
5. **Single-file `brain/sim/tvb_adapter.py` for all 5 days of Layer B** (561 LOC vs spec's 320 LOC budget) — dispatch explicitly asked for one module; splitting would have required maintaining a separate `tvb_feedback.py` for Day 10 only.
6. **`viewer/middleware.ts` + `proxy.ts` → merged into `proxy.ts`.** Phase 7.5 agent created middleware.ts without realizing Next.js 16 + next-intl 4.x mandate exactly one of {middleware.ts, proxy.ts}. `npm run build` refused. Fix (commit `1073cec`): merge into proxy.ts as a wrapper around `createMiddleware(routing)` with Rule #1 inspector + CSP layered on. ZERO constitutional surface change.
7. **Migration 018-023 + Cypher 017 all written PURELY ADDITIVE.** `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `DROP POLICY IF EXISTS; CREATE POLICY`, `NOT VALID` constraints. Zero `DROP TABLE` / `ALTER COLUMN`. Mirrors Phase 7.0 016 pattern.
8. **Phase 7.6 "structural-complete" claim, not "fully validated".** TS compiles + Next.js builds + i18n parity 100% + dynamic-import patterns asserted. Visual rendering of Plotly histograms / vis-network 571-node graph / react-flow DnD requires browser. Honest deviation in EXIT_REPORT.
9. **`viewer/lib/flags.ts` GO-state defaults.** Phase 7.7 §5.2 NO-GO rollback is "flip the relevant flag to false"; default = all `true`. Each flag's comment documents both the phase that owns the surface AND the NO-GO action.
10. **Refute pass-rate bug fix (Phase 7.2 verifier check 7).** Original `check_refutation` passed `Pydantic EstimateResult` wrapper to `refute_estimate_all`; DoWhy `model.refute_estimate(...)` expects raw `CausalEstimate`. sensitivity module silently caught the exception + returned `passed=False` for all refuters; verifier check 7 PASSed the "2 reports returned without throw" contract but the actual pass-rate was 0/2. Patch: verifier passes raw DoWhy objects. Now `random_common_cause + placebo_treatment_refuter` both PASS (2/2). EXIT_REPORT carry-forward #3 rewritten from false-claim to honest "FutureWarnings noise floor".
11. **Hagmann + TVB PMID grounded via PubMed WebFetch** (commit `e55ef6a`). Spec's `23781175` was a zebrafish behavioural-analysis paper. Real PMIDs: Hagmann 2008 = `18597554`, Sanz Leon 2013 = `23781198`. Both verified before commit.

### Alternatives rejected (to prevent rediscovery)

| Considered | Rejected because | Use instead |
|---|---|---|
| Custom `subagent_type: "v7-bayes"` etc. via Agent tool | Runtime doesn't load `.claude/agents/v7-*.md` mid-session | Dispatch `general-purpose` + have agent read its role file as FIRST-context |
| Single mega-commit for Phase 7.0-7.7 | Less reviewable for Shako; harder to bisect | 13 atomic commits one per phase + 4 per-fix |
| Hard-delete `viewer/middleware.ts` via plain `rm` | Auto-mode classifier blocks (constitutional security control) | `git rm` after explicit user confirmation via AskUserQuestion |
| Add Plotly server-side rendering (kaleido) for Phase 7.3 Layer C | Plotly not in .venv-v7; adds heavy dep | matplotlib (already used by Phase 7.0 brain/belief/viz.py) |
| Install reportlab in .venv-v7 for Phase 7.7 PDF builder | Dispatch forbade new installs | xfail/skipif pattern on `REPORTLAB_AVAILABLE`; Shako installs later |
| Run Phase 7.6 frontend in this session via headless browser | No browser in environment; risk of producing untested visual code | "Structural-complete" deliverable + Shako runs `npm run dev` later |
| Run TVB simulation at full Hagmann 998-region scale in verifier | 60-second sim takes ~5min wall through Docker startup overhead — would blow check 13 regression budget | 1-second sim (proxy) + 5-min hard cap via `TVB_SIMULATION_TIMEOUT_S=300` |
| Use spec's `23781175` PMID for Hagmann citation | Verified wrong via PubMed (zebrafish paper) | Grounded as `TODO(citation)` until WebFetch resolved real PMID |
| Push to origin / open PR | CLAUDE.md hard rule: don't push without user authorization | Branch stays local, PR creation deferred to user |
| `git rebase -i` to clean up 13 commits into fewer | Interactive editor unsupported; risk of losing work | 13 commits stand; Shako can squash if desired during PR review |

### Mid-session discovered constraints

| Constraint | Discovery context | Impact |
|---|---|---|
| **DoWhy 0.14 `CausalRefutation.estimated_effect` exists** but `EstimateResult.value` (Pydantic wrapper) does not — they're different objects | Verifier check 7 caught it via `passed=False` everywhere; live probe via test_sensitivity.py showed real behaviour | Fix in commit batch; refute pass-rate honest now |
| **pgmpy 1.1.2 `BIC` class rejects scoring_method=instance** in HillClimbSearch; string registry token `'bic-g'` required | Phase 7.2 Day 11 agent live error | Document + use string tokens; class import kept for forward-compat |
| **pgmpy `bic-g` patsy backend trips on column names with spaces/parens** (e.g. "Seizure frequency") | Same Phase 7.2 Day 11 dispatch | `_sanitize_column_name` + inverse `node_name_mapping` for round-trip |
| **Next.js 16 + next-intl 4.x mandate one of {middleware.ts, proxy.ts}**, never both | Phase 7.6 dispatch `npm run build` failure | Merge logic into single file; see decision #6 above |
| **TVB image bundles connectivity_998.zip** (Hagmann) — spec was pessimistic | Day 6 smoke probe `docker run --rm tvb-run python -c "import tvb_data; ..."` | Adapter defaults to 998 not 76; deviation #2 in Layer B EXIT_REPORT |
| **AuraDB Free can't enforce range constraints on relationship properties** (e.g. `confidence >= 0`) | Phase 7.1 cypher schema design | Moved to Pydantic application-layer validation in `brain/memory/edge_taxonomy.py` |
| **CLAUDE.md banned bigrams in KA**: never `ცარიელი/ცამეტი/ფარული/ცდილია` 2× per paragraph; use digit `13` not the word `ცამეტი`; no em-dashes | Phase 6.1 lesson carry-over | Hand-authored all KA templates (Phase 7.4) + closure docs; anti-loop scan in verifier 7_4_05 |
| **`mcp__claude_ai_PubMed__*` MCP server intermittently disconnected** during the session | WebFetch + direct PubMed URL used as fallback for Hagmann PMID grounding | None — WebFetch sufficed |
| **Aleksandra's MRI is client-side-only per CLAUDE.md** — must NOT touch server for any TVB lesion mask | Phase 7.3 Layer B Day 8 | `synthetic_hie_lesion_mask_for_aleksandra` is hash-deterministic placeholder; docstring forbids per-patient masks server-side |

---

## 5. Tried and failed

| Attempt | Why it failed | Exact symptom |
|---|---|---|
| Dispatch agent with `subagent_type: "v7-devops"` (first try, early in pre-compact era) | Claude Code runtime doesn't load `.claude/agents/v7-*.md` mid-session | Agent tool rejected the subagent_type as unknown. Workaround: use `general-purpose` + tell agent to read its role file. |
| `python scripts/verify_phase_7_2.py --mode code-complete` (bare path, first try) | `sys.path.insert(0, '.')` only fires when cwd = project root AND `python` resolves project; bare invocation in some shells missed module path | `ModuleNotFoundError: No module named 'brain'` on 10 of 12 checks. Workaround: `.venv-v7/Scripts/python.exe -m scripts.verify_phase_7_2 --mode code-complete` (module form). Subsequent verifiers (7.3+) added explicit `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))` at top so bare-path invocation works. |
| `git commit` of middleware/proxy merge — first attempt landed only the deletion, not the proxy.ts modification | The earlier `git add` staged proxy.ts BEFORE the Edit; the Edit modified working tree but didn't re-stage | Commit message correct but `1 file changed, 95 deletions(-)` only (no proxy.ts insertions). Workaround: `git add viewer/proxy.ts && git commit --amend --no-edit` (commit not yet pushed; amend safe). |
| `rm viewer/middleware.ts` plain bash delete | Auto-mode classifier blocked — "Deleting a pre-existing tracked file containing Phase 7.5 Rule #1 CSP enforcement constitutes Irreversible Local Destruction" | Permission error from classifier. Workaround: `AskUserQuestion` to confirm + then `git rm viewer/middleware.ts` (cleaner than plain `rm`). |
| `cd viewer && npx tsc --noEmit` (after shell already inside viewer/) | shell cwd persistence across Bash tool calls confused — already-inside-viewer made `cd viewer` fail | `cd: viewer: No such file or directory` then `tsc exit=1` (because the cd failed, npm couldn't find package.json). Workaround: bare `npx tsc --noEmit` when already inside viewer/. |
| Phase 7.6 agent committed an unrelated bug fix outside its declared scope (`fix(verifier): recognize [locale]/brain/ path in MNG-01 check`, commit `452a060`) | Agent saw the Phase 5 verifier bug while inspecting routes, fixed it inline. Useful, but scope violation. | Commit landed; let stand. Document: agents may quietly fix small unrelated bugs even when told not to — verify by inspecting commit list. |
| Tried to read `pubmed.ncbi.nlm.nih.gov/23781175/` assuming it was Hagmann | Spec was wrong — PMID is a zebrafish paper | WebFetch returned "ZebraZoom: an automated program for high-throughput behavioral analysis and categorization". Workaround: searched PubMed for Hagmann title + got real PMID 18597554. |
| Initial Phase 7.7 agent claim that `viewer/lib/flags.ts` "didn't exist before" | Misleading — earlier ls listing was post-creation snapshot; couldn't have seen pre-state | Confirmed via `git log -- viewer/lib/flags.ts` showing single entry = commit 44a5e35 (Phase 7.7 commit). Agent was correct, ls timing fooled me. |
| Tried `g++` compile for some pgmpy / pymc / JAX backend pathway | g++ not available on Windows venv | Warning surfaces at import (`g++ not available, if using conda: 'conda install gxx'`). Non-blocking; tests pass via fallback. Don't try to fix unless perf becomes a real issue. |
| Phase 7.5 agent's MVP carry-forward #1 claim that DoWhy refuter `passed=False` was caused by `EstimateResult.value` removal | Misdiagnosis — `CausalEstimate.value` (the raw DoWhy object) DOES exist in 0.14. Real bug was verifier check 7 passing the wrong wrapper object. | Live probe via `getattr(causal_estimate, 'value', None)` returned `-0.825...` (truthy). Fix landed; closure docs patched to remove false claim. |
| Phase 7.3 Layer C verifier check 7 actual claim "2/2 passed" rate of 0% | Same bug as above — verifier passed Pydantic wrapper instead of raw DoWhy | Refuter pass-rate documented as "100% after verifier check 7 patched". |

---

## 6. Environment & tools state

### MCP servers + state (last observed)
| Server | State at session end |
|---|---|
| `claude_ai_AWS_Marketplace` / `Benevity` / `Booking.com` / `CData` / `Candid` / `Canva` / `Clarity_AI` | Available (deferred tools) — none used |
| `claude_ai_Cloudflare_Developer_Platform` + `_2` | Available — none used |
| `claude_ai_Consensus` / `Docusign` / `Figma` / `Gmail` / `Google_Calendar` / `Google_Cloud_BigQuery` / `Google_Compute_Engine` / `Google_Drive` | Available — none used |
| `claude_ai_Granted` / `Higgsfield` / `Indeed` / `Invideo` / `Kiwi.com` / `Meta_ads` / `Moody's` / `Netlify` / `PDF_Viewer` | Available — none used |
| `claude_ai_PubMed` | **Disconnected** mid-session; fell back to `WebFetch` for Hagmann + TVB PMID lookup |
| `claude_ai_Scholar_Gateway` / `Vercel` / `Zapier` / `n8n` | Available — none used |
| `code-review-graph` | **Disconnected then reconnected** mid-session — none used |
| `context7` | **Disconnected then reconnected then disconnected then reconnected** — none used |
| `qdrant` | Disconnected then reconnected — none used |
| `tavily` | Disconnected (multiple times) — none used |
| `Hugging_Face` / `Microsoft_365` | Available (auth-pending) — none used |

### Skills activated this session
- `update-config` (mentioned in available-skills list; not invoked)
- `caveman*` / `cavecrew*` family (available; not invoked)
- `gsd-*` family (available; not invoked — session pre-dates GSD adoption for this project)
- `graphify` (mentioned in `~/.claude/CLAUDE.md`; output appears in `graphify-out/` which I just gitignored)
- `claude-mem:*` family (available; not invoked, but claude-mem may have generated `.planning/design/` background activity — see §3 staged files)
- `loop`, `schedule`, `claude-api`, `init`, `review`, `security-review`, `run`, `verify`, `simplify`, `fewer-permission-prompts`, `keybindings-help`, `statusline-setup` — none invoked
- **`design-director` / `design-*` subagents** — likely active in background (account for staged `.planning/design/` files); NOT invoked by me

### Sub-agents dispatched this session + their outputs
| Agent ID | Purpose | Output location |
|---|---|---|
| `ae5bef83b327ae5b8` | Phase 7.2 Days 6-10 build | `brain/causal/{estimators,counterfactual,sensitivity,api,cross_link}.py` + 35 tests |
| `a94117e95ea2774c5` | Phase 7.2 Days 11-15 build | `brain/causal/{structure_learning,scm_persistence}.py` + 32 tests + migration 018 + verifier 7.2 + closure trilogy |
| `a0cbcb123af85dccf` | Phase 7.3 Layer A build (left mid-stream awaiting Monitor) | `brain/sim/{scenario,trajectory,aggregator,compare,cache}.py` + 38 tests |
| `ab6fa4e05549c9061` | Phase 7.3 Layer A continuation (resumed agent, also left mid-stream) | Verification reports only |
| `abc25860f9b3d9526` | Phase 7.3 Layer C build | `brain/sim/{persistence,api,viz}.py` + 44 tests + migration 019 + verifier 7.3 + closure trilogy |
| `ada33ddc0aaebed44` | Phase 7.4 Active Learning build | `brain/active/` 10 modules + 63 tests + migration 020 + verifier 7.4 + closure trilogy |
| `acbb1a2fba5522b81` | Phase 7.5 Constitutional build | `brain/common/` 9 modules + 63 tests + 4 migrations (021/022/022b/023) + verifier 7.5 + closure trilogy + viewer/middleware.ts (later merged) |
| `a7447bd531b59ef6f` | Phase 7.7 acceptance scaffold | `brain/docs/pdf_builder.py` + verifier 7.7 + 9 doc templates + viewer/lib/flags.ts |
| `a1292bf41fda888de` | Phase 7.6 Site Refactor | `viewer/app/[locale]/{twin,causal,simulate,drift}/` + 4 widget components + 4 API clients + 244 i18n keys + verifier 7.6 + closure trilogy |
| `a372df3c02ad18d5e` | Phase 7.3 Layer B TVB build | `brain/sim/tvb_adapter.py` + 27 tests + infra/tvb-docker-compose.yml + verifier 7.3 updates |

All agents returned to main thread cleanly. None left background processes.

### Hooks
- `SessionStart:compact hook success` — no behavioural modification observed
- `claude-mem` background memory injection — observed `.planning/design/` staged files mid-session (see §3) — likely a design-director skill auto-writing planning artifacts
- No pre-commit / pre-push hooks in the repo (all `git commit --no-verify` invocations honoured)

### Env vars / secrets the next session needs (names only, NEVER values)
- `SUPABASE_DB_URL` — service-role Postgres connection string. Currently UNSET in this session → all CRUD took DRY_RUN path. Next session needs it set ONLY for production-apply verifier runs.
- `NEO4J_URI` + `NEO4J_USER` + `NEO4J_PASSWORD` — for Phase 7.1 production cypher
- `ANTHROPIC_API_KEY` — Phase 5/7.4 LLM calls (NOT used this session due to zero LLM dispatch design)
- `OPENAI_API_KEY` — Phase 5 Whisper transport (NOT used this session)
- `TELEGRAM_BOT_TOKEN` + `MANAGER_USER_ID` — Phase 7.4 live outbound (dry-run only this session)
- `NEXT_PUBLIC_API_URL` + `NEXT_PUBLIC_MOCK_MODE` — Phase 7.6 frontend API clients (MOCK_MODE used this session)

### Open dev servers / watchers / tunnels
- **None.** Every `npm run build` / `pytest` / `docker run` invocation finished cleanly. No `npm run dev` background process. No `docker run -d` (every TVB container `--rm`).

---

## 7. Open questions

### To ask user before continuing
1. ~~**11 staged `.planning/design/` + root `AGENTS.md` files**~~ — **ANSWERED 2026-05-28:** single `docs(design):` commit chosen (option 1). Landed in `5bd97f7`.
2. **Date confusion**: user requested handoff "dated 2026-05-15" but system reminders during session repeatedly said today is 2026-05-25 (and one said 2026-05-28). Honoured the explicit 2026-05-15 instruction. Confirm preferred date.
3. ~~**PR strategy**~~ — **ANSWERED 2026-05-28:** keep 14 atomic commits as-is, do **not** squash (option 1). Shako can squash during merge if desired.
4. **TVB image replacement** (deprecated upstream): is this Phase 7.5.1 maintenance scope, or wait for v7.1.0?
5. **Phase 7.7 wife/doctor session dates** — calendar window is late-Dec 2026 → early-Jan 2027. Confirm Shako has booked Dr. Maypole + Dr. August/Hien slots.

### Needs investigation or external input
1. **GitHub Actions verify_all.yml** (Phase 7.5 Rule #13) — workflow YAML written but not pushed. First push will trigger the workflow on its own commit. Verify the workflow file syntax against GitHub Actions current schema before push (or accept that first run will fail and iterate).
2. **TVB simulation perf on real Hagmann 998-region** — current 1-second sim is 16.3s wall on Docker Desktop / Windows. 60-second sim is unmeasured. If a doctor wants to demo a 60s sim live, latency budget may need TVB-C++ backend (Wiley 2026 paper).
3. **Phase 7.6 Lighthouse perf** — bundle size budgets not measured. Vercel preview deploy needed.
4. **Wife opt-in for Phase 7.4 active-question Telegram outbound** — required Day 0 before any live send. Currently unwilling-state assumed.

### Stated assumptions that need validation
1. `causal_estimate` is in `ALLOWED_EVIDENCE_SOURCES` (Phase 7.0 frozenset) — confirmed by `grep`
2. `tvb_sim` is in `ALLOWED_EVIDENCE_SOURCES` — confirmed by `grep`
3. Phase 6 next-intl 4.x file convention is `proxy.ts` not `middleware.ts` — confirmed via `npm run build` error message + Next.js docs link
4. `reportlab` not in `.venv-v7` — confirmed via `import reportlab` ImportError; conditional skip pattern used
5. `viewer/node_modules` has `@xyflow/react` + `plotly.js-dist-min` + `vis-network` from Phase 6.1 install — confirmed via `cat viewer/package.json`
6. Phase 7.0 `dimensions.toml` has 13 dims with real PubMed PMIDs (no TBD stubs) — confirmed via `test_live_catalog_has_zero_stubs` test
7. Phase 7.5 Rule #11 weekly cap = 3 — confirmed in `brain/active/rate_limiter.py` + `verify_phase_7_4` check 7_4_06

---

## 8. Next step (single, concrete, runnable)

**Resume update (2026-05-28):** §9 confirmation re-ran clean (after 5 small bugs were fixed and committed in `6f8e05e`). Staged design files committed in `5bd97f7`. Working tree is clean except `M handoff.md` (this very file — commit after this section is updated). Branch is 15 commits ahead of `main`, HEAD `5bd97f7`.

**Next concrete action** — Shako-action queue item #1: **browser smoke for Phase 7.6 routes.**

```bash
cd "/c/Users/jinch/OneDrive/სამუშაო დაფა/aleksandra brane/viewer"
npm run dev    # http://localhost:3000
# Open in browser and walk through:
#   /en/today        (existing)
#   /en/twin         (Phase 7.6 NEW — Twin Status histograms)
#   /en/causal       (Phase 7.6 NEW — vis-network 571-node graph)
#   /en/simulate     (Phase 7.6 NEW — react-flow scenario builder)
#   /en/drift        (Phase 7.6 NEW — Plotly belief-drift timeline)
#   /ka/today        (i18n check — verify dictionary loads + LanguageSwitcher works)
#   /en/timeline     (refactored widget)
#   /en/therapies    (refactored widget)
```

Watch for: blank pages, hydration mismatch warnings, dynamic-import 404s, Plotly bundle errors, missing KA strings. None of those will surface in the headless `npm run build` that this session already confirmed.

After browser smoke: proceed sequentially down the Shako-action queue (see §3 "Mirror of active TodoWrite list" — items prefixed `[shako *]`).

**PR creation** is gated on browser smoke. Once smoke passes:
```bash
git push -u origin v7-phases-7-0-to-7-5-closure
gh pr create --title "v7 closure batch: Phase 7.0-7.7 + maintenance" --body "..."
```
PR strategy confirmed by Shako: keep 14 atomic commits, do **not** squash. Bisection wins over PR-diff readability for a 261-file, ~54.5K-line change.

---

## 9. Confirmation commands

Run these FIRST in the next session to verify the state described above is still accurate:

```bash
# === Verify branch + commit position (updated 2026-05-28) ===
cd "/c/Users/jinch/OneDrive/სამუშაო დაფა/aleksandra brane"
git branch --show-current
# expected: v7-phases-7-0-to-7-5-closure

git log --oneline main..HEAD | wc -l
# expected: 15  (was 13 before the 2026-05-28 resume; +2 commits: 6f8e05e fixes, 5bd97f7 design)

git rev-parse --short HEAD
# expected: 5bd97f7  (was e55ef6a before the 2026-05-28 resume)

git status --short | grep -v "^??" | wc -l
# expected: 0  (working tree clean)

# === Verify pytest count (updated 2026-05-28) ===
.venv-v7/Scripts/python.exe -m pytest brain/ -m "not slow" -q --tb=no
# expected: 658 passed, 2 skipped, 4 deselected
# (was: 658 passed, 1 skipped — Docker-down adds a 2nd skip for the conditional live TVB test)
# wall time: 6–14 minutes depending on hardware
# tolerated: 657 passed + 1 failed in test_higher_confidence_level_widens_ci (DoWhy bootstrap flake)
# run in isolation to confirm flake: .venv-v7/Scripts/python.exe -m pytest brain/causal/tests/test_estimators.py::test_higher_confidence_level_widens_ci -v

# === Verify viewer TypeScript + Next.js build ===
cd viewer
npx tsc --noEmit
# expected: exit 0, no output

npm run build
# expected: exit 0, all 8 routes incl. /[locale]/{twin,causal,simulate,drift} listed

cd ..

# === Verify all 8 phase verifiers ===
for phase in 7_0 7_1 7_2 7_3 7_4 7_5 7_6 7_7; do
    echo "=== Phase $phase ==="
    .venv-v7/Scripts/python.exe scripts/verify_phase_${phase}.py --mode code-complete 2>&1 | tail -3
    echo
done
# expected: every phase ends with "GREEN" + exit 0
# Phase 7.0: 10/11 PASS · 1 SKIP
# Phase 7.1: 2/9 PASS · 7 SKIP
# Phase 7.2: 12/12 PASS  (1200s pytest timeout now; was 600s in pre-resume verifier)
# Phase 7.3: 13/13 PASS (if Docker + TVB image present) OR 11/13 PASS · 2 SKIP (Docker-down: 1 TVB check still PASSes via DRY_RUN sentinel)
# Phase 7.4: 10/10 PASS
# Phase 7.5: 11/14 PASS · 3 SKIP  (check 1 now points at viewer/proxy.ts after middleware merge)
# Phase 7.6: 12/12 PASS  (the 1 historical SKIP for `next build` now flips to PASS — middleware/proxy merge is in)
# Phase 7.7: 1/10 PASS · 9 SKIP

# === Verify Docker + TVB image (for Phase 7.3 Layer B) ===
docker version | grep -E "(Client|Server)" | head -2
# expected: Client + Server both reported (Docker Desktop running)

docker images thevirtualbrain/tvb-run | head -2
# expected: 1 image entry, tag latest, ~3.5GB content size
# if missing: docker pull thevirtualbrain/tvb-run:latest  (~3GB download)

# === Quick TVB live sanity (optional, ~20s wall) ===
.venv-v7/Scripts/python.exe -c "
from brain.sim.tvb_adapter import run_tvb_simulation, TVBSimulationRequest
import time
t0 = time.perf_counter()
r = run_tvb_simulation(TVBSimulationRequest(duration_ms=1000, region_count=76))
print(f'TVB 1-second sim: {time.perf_counter()-t0:.1f}s wall')
print(f'Container: {r.container_id}; regions: {len(r.region_activity)}')
"
# expected: ~15-20s wall (mostly Docker startup); container_id starts with 'tvb-aleksandra-' OR 'DRY_RUN' if Docker missing

# === Container hygiene ===
docker ps -a --filter "name=tvb-aleksandra-"
# expected: empty (every TVB sim uses --rm; nothing left behind)
```

If any of the above fails, refer to §5 "Tried and failed" first — most footguns are documented there.

---

**End of handoff.**
