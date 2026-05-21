---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Phase 6 plan 06-03a complete — viewer/app/[locale]/ shell landed via 10 R100 git renames (7 family-facing route directories + root page.tsx relocated; api/audit/brain/layout.tsx preserved at top level). npm run build green; 8 /[locale]/* dynamic routes resolve. 06-03b unblocked.
last_updated: "2026-05-21T00:30:00.000Z"
last_activity: 2026-05-21 -- Phase 6 plan 06-03a complete (viewer/app/[locale]/ structural folder move — 10 R100 renames)
progress:
  total_phases: 8
  completed_phases: 0
  total_plans: 15
  completed_plans: 3
  percent: 20
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-13)

**Core value:** Never miss a credible treatment lead for Aleksandra.
**Current focus:** Phase 0 — Foundation

## Current Position

Phase: 6 of 8 (Bilingual System i18n)
Plan: 3 of 15 in current phase (06-03a complete — viewer/app/[locale]/ folder move landed; 06-03b next)
Status: executing
Last activity: 2026-05-21 -- Phase 6 plan 06-03a complete (viewer/app/[locale]/ structural folder move — 10 R100 renames)

Progress: [██░░░░░░░░] 20%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 0. Foundation | 0/TBD | — | — |
| 1. Perception | 0/TBD | — | — |
| 2. Memory | 0/TBD | — | — |
| 3. Cognition (min) | 0/TBD | — | — |
| 4. First Family Value | 0/TBD | — | — |

**Recent Trend:**

- Last 5 plans: none yet
- Trend: —

*Updated after each plan completion.*
| Phase 06 P06-01 | 7m 26s | 5 tasks | 9 files |
| Phase 06 P06-02 | 16m     | 3 tasks | 3 files |
| Phase 06 P06-03a | 10m     | 2 tasks | 10 files (R100 renames; 0 content modifications) |

## Accumulated Context

### Roadmap Evolution

- 2026-05-21: Phase 6 plan 06-03a executed — viewer/app/[locale]/ structural folder move. Eight `git mv` operations relocated the 7 family-facing route directories (dashboard, timeline, papers, therapies, hypotheses, today, knowledge) + the root page.tsx (former Today landing) under viewer/app/[locale]/. All 10 file moves tracked as R100 (100% similar) renames — zero content drift, pure topology change. viewer/app/{api,audit,brain}/ and viewer/app/layout.tsx preserved at top level per SPEC Out of Scope + proxy.ts matcher exclusions. `cd viewer && npm run build` exits 0 (Turbopack, 27s wall); routes-manifest.json shows 8 dynamic /[locale]/* entries (acceptance floor ≥7). I18N-02 PARTIAL-GREEN at this plan boundary; full GREEN after 06-03b lands the locale layout + async-params signature. Wave-1 06-03b unblocked. Commit: 731b601. See 06-03a-SUMMARY.md.
- 2026-05-20: Phase 6 plan 06-02 executed — scripts/verify_phase6.py (1060 lines, 11 check_i18n_NN functions, 5-bucket dispatch A/B/C/D/E per CONTEXT.md D-06) + tests/fixtures/phase6/phi_ka.yaml (10 Georgian PHI fixtures across 5 categories + 1 hard-block) + tests/fixtures/phase6/bilingual_samples.json (30 samples: 25 clean + 5 positive-catch covering D-05 banned phrases). `python -X utf8 -m scripts.verify_phase6 --mode code-complete` emits 11-row Phase-5-style table; 2/11 PASS at Wave-0 baseline (I18N-01 + I18N-10). Wave 0 closed. 3 commits: b3cc2ff, a7dbdc8, fa1708e. See 06-02-SUMMARY.md.
- 2026-05-20: Phase 6 plan 06-01 executed — next-intl@4.12.0 installed, viewer/proxy.ts mounted (Next.js 16 file convention), three-file i18n module (routing/request/navigation), viewer/messages/{en,ka}.json relocated, createNextIntlPlugin wired in next.config.ts. `npm run build` green (34.1s). 4 commits: 10fbdee, 2b0124a, 5a073e7, a945f55. See 06-01-SUMMARY.md.
- 2026-05-20: Phase 6 added — Bilingual System (i18n): full site + dynamic data bilingual support (en/ka). Frontend static localization, Supabase JSONB for dynamic content, AI agents emit en+ka pairs, Telegram/Gmail audience routing. Seed: docs/I18N_PLAN.md.
- 2026-05-20: Phase 5 retro-added to Phase Details section (engineering closed 2026-05-18, 13/13 PASS); Progress table refreshed to reflect Phase 4 + 5 closure.

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Phase 6 (plan 06-03a, 2026-05-21): Whole-directory `git mv` (NOT per-file) for each of the 7 family-facing routes — git rename-detection collapses nested children (hypotheses/[id]/page.tsx + hypotheses/actions.ts) to R100 atomically, keeping the diff reviewable as a single topology change.
- Phase 6 (plan 06-03a, 2026-05-21): Did NOT add a placeholder viewer/app/[locale]/layout.tsx in this plan — npm run build is already green without one (Next.js 16 composes the root viewer/app/layout.tsx over /[locale]/* pages), and adding a placeholder would force a content-modification commit and break this plan's pure-rename invariant. 06-03b owns the real locale layout.
- Phase 6 (plan 06-03a, 2026-05-21): Preserved viewer/app/{api,audit,brain}/ + viewer/app/layout.tsx + viewer/app/globals.css at top level per 06-SPEC.md Out of Scope + the matcher `'/((?!api|audit|brain|_next|_vercel|.*\\..*).*)'` in viewer/proxy.ts.
- Phase 6 (plan 06-02, 2026-05-20): Mirror scripts/verify_phase5.py structurally in scripts/verify_phase6.py — same Check + Report dataclasses, same --mode {production,code-complete} flag, same table printer. Cumulative project verifier idiom preserved (78 → 89 once Phase 6 closes).
- Phase 6 (plan 06-02, 2026-05-20): Default check_i18n_NN to RED with `evidence="PENDING — implemented in Wave N plan NN"` rather than crashing on missing implementation modules — Wave-0 scaffold runs end-to-end so downstream plans can incrementally flip checks to GREEN.
- Phase 6 (plan 06-02, 2026-05-20): Annotate every positive-catch bilingual sample with `triggered_phrase` field — lets plan 06-11's banned_phrases.py extension test grep for the exact phrase that each canary fires.
- Phase 6 (plan 06-01, 2026-05-20): Use next-intl@4.12.0 on Next.js 16.2.6 + the proxy.ts file convention (NOT middleware.ts) — locked decision D-01 in 06-CONTEXT.md, validated against 06-RESEARCH.md Pitfall 1.
- Phase 6 (plan 06-01, 2026-05-20): Three-file i18n module (routing.ts / request.ts / navigation.ts) under viewer/i18n/ + dictionaries under viewer/messages/{en,ka}.json — canonical next-intl 4 layout per RESEARCH.md Pattern 1.
- Phase 0: Foundation comes first — pitfalls 9 (MCP sprawl) and 13 (cost runaway) are catastrophically expensive to retrofit.
- Phase 0: MRI-leak countermeasure split — import-lint half (FND-01, FND-02) lands in v1 Phase 0; viewer half (VIS-*) is v2.
- Phase 2: Citation tuple is a first-class type before any agent runs (CATASTROPHIC fabrication defense, half-1).
- Phase 3: Verifier agent must reject ≥99 of 100 synthetic fabrications before Communicator drafts publish (CATASTROPHIC fabrication defense, half-2).
- Phase 4: v1 release gate is the 14-day acceptance test (one credible lead, full provenance, under $30 total cost).

### Pending Todos

None yet.

### Blockers/Concerns

- AuraDB Free node-count ceiling — confirm live limit (200K vs 50K) on day 1 of Phase 2.
- NCBI E-utilities `api_key` registration is a Phase 0 task — required before Phase 1.
- Vigabatrin washout duration is patient-specific — Phase 6 Calendar (v2) reads from a family-editable field.
- FreeBrowse fork licensing review — v2 Phase 7 prerequisite, not v1 blocking.

## Deferred Items

Items acknowledged and carried forward:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v2 | Cognition (full) — Spider + Hypothesis + Repurposing | Documented in REQUIREMENTS.md v2 (CGF-*) | 2026-05-13 |
| v2 | Action interactivity — Telegram ask_user, Calendar, Booking/Kiwi, bilingual | Documented in REQUIREMENTS.md v2 (ACI-*) | 2026-05-13 |
| v2 | Visualization — viewer, segmentation, simulation, 3D print | Documented in REQUIREMENTS.md v2 (VIS-*, SIM-*) | 2026-05-13 |
| v2 | HIPAA posture — Prism MCP, Hindsight | Documented in REQUIREMENTS.md v2 (HPA-*) | 2026-05-13 |

## Session Continuity

Last session: 2026-05-21T00:30:00.000Z
Stopped at: Phase 6 plan 06-03a complete — viewer/app/[locale]/ shell landed via 10 R100 git renames; npm run build green; 8 /[locale]/* dynamic routes resolve. 06-03b unblocked.
Resume file: None
