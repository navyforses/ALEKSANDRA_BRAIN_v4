---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Phase 6 plan 06-05a complete — viewer/messages/{en,ka}.json expanded from 7-key seed to 143-leaf parallel dictionaries across 11 namespaces (Common, Navigation, Shared, Home, Dashboard, Timeline, Papers, Therapies, Hypotheses, Today, Knowledge). Recursive key-set equality verified; 99.3% Mkhedruli coverage on ka.json (only ALEKSANDRA_BRAIN proper noun stays Latin). `cd viewer && npm run build` exits 0 (17 routes). Dictionary half of I18N-03 ready — page-side t(...) rewrite + TopNav update lands in 06-05b (Wave 3).
last_updated: "2026-05-21T02:00:00.000Z"
last_activity: 2026-05-21 -- Phase 6 plan 06-05a complete (en.json + ka.json bilingual dictionaries; 143 leaves × 2 locales; 11 namespaces)
progress:
  total_phases: 8
  completed_phases: 0
  total_plans: 15
  completed_plans: 5
  percent: 33
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-13)

**Core value:** Never miss a credible treatment lead for Aleksandra.
**Current focus:** Phase 0 — Foundation

## Current Position

Phase: 6 of 8 (Bilingual System i18n)
Plan: 5 of 15 in current phase (06-05a complete — bilingual dictionaries authored; 11 namespaces × 143 leaves × 2 locales; 06-05b next to consume them via t(...) rewrite + TopNav update)
Status: executing
Last activity: 2026-05-21 -- Phase 6 plan 06-05a complete (en.json + ka.json bilingual dictionaries; 143 leaves × 2 locales; 11 namespaces; 99.3% Mkhedruli coverage)

Progress: [███░░░░░░░] 33%

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
| Phase 06 P06-04 | 15m     | 3 tasks | 4 files (viewer/lib/i18n.ts +helper, __tests__/i18n.test.ts, LanguageSwitcher.tsx, tsconfig.json) |
| Phase 06 P06-05a | 20m     | 3 tasks | 2 files (viewer/messages/en.json +139 leaves, viewer/messages/ka.json +139 leaves; 11 namespaces × 143 leaves × 2 locales) |

## Accumulated Context

### Roadmap Evolution

- 2026-05-21: Phase 6 plan 06-05a executed — viewer/messages/{en,ka}.json bilingual dictionaries authored. Expanded both files from the 7-key Phase 5 seed (3 Common + 4 Navigation each) to 143-leaf parallel dictionaries across 11 namespaces: Common (3), Dashboard (19), Home (15), Hypotheses (32), Knowledge (3), Navigation (10), Papers (18), Shared (10), Therapies (22), Timeline (8), Today (3). Recursive key-set equality verified (en_set == ka_set; symmetric difference empty); ka.json achieves 99.3% Mkhedruli coverage (142/143; only the ALEKSANDRA_BRAIN proper noun stays Latin per CONTEXT.md guidance). D-05 banned-imperative lexicon (`უნდა`, `აუცილებლად`, `განიხილეთ`, `მოითხოვეთ`, `ითხოვეთ`) deliberately avoided in translations; `Shared.errorRetry = "სცადეთ ხელახლა"` ("Try again" button) flagged as INTENTIONAL UI label outside the CGM-04 lint scope (which targets Communicator digests, not static UI dictionaries). `cd viewer && npm run build` exits 0 (17 routes preserved, all `/[locale]/*` dynamic). One Rule 2 deviation: added 11th `Home` namespace (15 leaves) covering [locale]/page.tsx landing strings — PLAN's 10-namespace catalog did not name `Home` but the 10 required namespaces are all present; superset is permissible. Dictionary half of I18N-03 ready; full GREEN after 06-05b wires the t(...) calls in Wave 3. 2 commits: d292774, e0acd56. See 06-05a-SUMMARY.md.
- 2026-05-21: Phase 6 plan 06-04 executed — `viewer/lib/i18n.ts` landed with the locked CONTEXT.md-D-03 `displayField(field, locale)` helper (10 lines, ≤15 anti-creep gate). `viewer/lib/__tests__/i18n.test.ts` ships a 5-case `node:test` + `node:assert/strict` unit suite covering null/undef, legacy TEXT string passthrough (both locales), `{en, ka}` object normal read, English fallback when locale missing, empty object. Runner pinned to `npx tsx --test` to match the exact subprocess invocation in `scripts/verify_phase6.py::check_i18n_08` (eliminates dual-runner ambiguity from PLAN WARNING 4). `viewer/components/LanguageSwitcher.tsx` polished: `useRouter`/`usePathname` now imported from `@/i18n/navigation` (createNavigation-typed) instead of `next/navigation`; manual `pathname.replace('/${locale}', '')` + `router.push(newPath)` replaced with canonical next-intl 4 idiom `router.replace(pathname, {locale: newLocale})`; bilingual button labels `English`/`ქართული` (Mkhedruli) per CONTEXT.md Claude's Discretion; aria-labels preserved for deterministic screen-reader intent. One Rule-3 deviation: added `**/__tests__/**` to `viewer/tsconfig.json` exclude — `node:test` ESM convention requires `.ts` extension in imports but viewer's bundler-mode tsconfig rejects this; surgically excluding the test dir keeps Next.js build clean while letting tsx run tests at runtime. `cd viewer && npm run build` exits 0 (17 routes generated); verifier flips from 3/11→4/11 PASS (I18N-08 GREEN; I18N-04 still PENDING — waits on 06-03b to mount the switcher in `[locale]/layout.tsx`). Commits: 55eee7d, 2301c0e, c2a49e3. See 06-04-SUMMARY.md.
- 2026-05-21: Phase 6 plan 06-03a executed — viewer/app/[locale]/ structural folder move. Eight `git mv` operations relocated the 7 family-facing route directories (dashboard, timeline, papers, therapies, hypotheses, today, knowledge) + the root page.tsx (former Today landing) under viewer/app/[locale]/. All 10 file moves tracked as R100 (100% similar) renames — zero content drift, pure topology change. viewer/app/{api,audit,brain}/ and viewer/app/layout.tsx preserved at top level per SPEC Out of Scope + proxy.ts matcher exclusions. `cd viewer && npm run build` exits 0 (Turbopack, 27s wall); routes-manifest.json shows 8 dynamic /[locale]/* entries (acceptance floor ≥7). I18N-02 PARTIAL-GREEN at this plan boundary; full GREEN after 06-03b lands the locale layout + async-params signature. Wave-1 06-03b unblocked. Commit: 731b601. See 06-03a-SUMMARY.md.
- 2026-05-20: Phase 6 plan 06-02 executed — scripts/verify_phase6.py (1060 lines, 11 check_i18n_NN functions, 5-bucket dispatch A/B/C/D/E per CONTEXT.md D-06) + tests/fixtures/phase6/phi_ka.yaml (10 Georgian PHI fixtures across 5 categories + 1 hard-block) + tests/fixtures/phase6/bilingual_samples.json (30 samples: 25 clean + 5 positive-catch covering D-05 banned phrases). `python -X utf8 -m scripts.verify_phase6 --mode code-complete` emits 11-row Phase-5-style table; 2/11 PASS at Wave-0 baseline (I18N-01 + I18N-10). Wave 0 closed. 3 commits: b3cc2ff, a7dbdc8, fa1708e. See 06-02-SUMMARY.md.
- 2026-05-20: Phase 6 plan 06-01 executed — next-intl@4.12.0 installed, viewer/proxy.ts mounted (Next.js 16 file convention), three-file i18n module (routing/request/navigation), viewer/messages/{en,ka}.json relocated, createNextIntlPlugin wired in next.config.ts. `npm run build` green (34.1s). 4 commits: 10fbdee, 2b0124a, 5a073e7, a945f55. See 06-01-SUMMARY.md.
- 2026-05-20: Phase 6 added — Bilingual System (i18n): full site + dynamic data bilingual support (en/ka). Frontend static localization, Supabase JSONB for dynamic content, AI agents emit en+ka pairs, Telegram/Gmail audience routing. Seed: docs/I18N_PLAN.md.
- 2026-05-20: Phase 5 retro-added to Phase Details section (engineering closed 2026-05-18, 13/13 PASS); Progress table refreshed to reflect Phase 4 + 5 closure.

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Phase 6 (plan 06-04, 2026-05-21): `displayField` helper lives in `viewer/lib/i18n.ts` (NOT under `viewer/i18n/`) — distinct concerns: `viewer/i18n/{routing,request,navigation}.ts` holds next-intl wiring; `viewer/lib/i18n.ts` is consumer-facing utility code that downstream page/worker components import via `@/lib/i18n`.
- Phase 6 (plan 06-04, 2026-05-21): Helper is EXACTLY the 10-line shape locked in CONTEXT.md §D-03 — no JSDoc body, no extra exports, no logic creep. The 5-case behavior contract lives in the unit test file, not in code comments. Anti-creep gate enforces ≤15 lines.
- Phase 6 (plan 06-04, 2026-05-21): Test runner pinned to `npx tsx --test` (NOT vitest, NOT jest) — the verifier `check_i18n_08` production-mode path subprocess-invokes this exact command, so the runner is the contract, not the framework.
- Phase 6 (plan 06-04, 2026-05-21): LanguageSwitcher swap uses `router.replace(pathname, {locale: newLocale})` from the createNavigation-typed router — canonical next-intl 4 idiom. Manual `pathname.replace + router.push` pattern removed entirely.
- Phase 6 (plan 06-04, 2026-05-21): `viewer/tsconfig.json` excludes `**/__tests__/**` from compilation — node:test's required `.ts` import extension is incompatible with the viewer's bundler-mode tsc; the test dir runs under tsx at runtime, never compiled by next build.
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

Last session: 2026-05-21T02:00:00.000Z
Stopped at: Phase 6 plan 06-05a complete — bilingual dictionaries (en.json + ka.json) at 143 leaves × 2 locales across 11 namespaces; recursive key-set equality verified; 99.3% Mkhedruli coverage on ka.json. 06-05b next (page-side t(...) rewrite + TopNav update, Wave 3).
Resume file: None
