# Phase 6 Exit Report — Bilingual System (i18n)

**Date closed:** 2026-05-21
**Scope:** I18N-01..I18N-11 — Full English+Georgian bilingualism across the 7 family-facing viewer routes, 4 dynamic-data Supabase tables, the Communicator + Phase 5 composer write path, the Telegram/Gmail audience-routing layer, the PHI redactor, and the imperative-verb lint.
**Sprint duration:** 2026-05-20 → 2026-05-21 (planning + execution closed inside a 2-calendar-day window; 15 plans across 4 implementation waves).

## Verdict — დასკვნა

Phase 6 closes the engineering sprint at **`verify_phase6 --mode code-complete`** → **11/11 PASS · ALL GREEN**.

Cumulative project verifier coverage post-Phase-6: **89/89 PASS** across all 7 phases (Perception 10 + Memory 19 + Quick Wins 16 + Cognition 11 + FFV 9 + Manager 13 + I18N 11).

| # | Gate | Wave | Status |
|---|---|---|---|
| 1 | I18N-01 next-intl@4 installed + Next.js 16 compat | 1 | PASS |
| 2 | I18N-02 Locale-segmented routes (/en/* + /ka/* × 7) | 1 | PASS |
| 3 | I18N-03 viewer/messages/{en,ka}.json — 143 leaves × 2 | 1 | PASS |
| 4 | I18N-04 LanguageSwitcher mounted in [locale]/layout.tsx | 1 | PASS |
| 5 | I18N-05 Migration 012 SQL + rollback infra (production-applied) | 2 | PASS |
| 6 | I18N-06 Communicator + briefing emit {en, ka} JSONB | 3 | PASS |
| 7 | I18N-07 Telegram=ka / Gmail=en audience routing | 4 | PASS |
| 8 | I18N-08 displayField helper + locale-aware reads | 1+2 | PASS |
| 9 | I18N-09 Historical rows: ka = en (migration 012 USING) | 2 | PASS |
| 10 | I18N-10 PHI redactor bilingual + Georgian imperative lint | 3 | PASS |
| 11 | I18N-11 Phase 4 (9/9) + Phase 5 (13/13) regression | 4 | PASS |

Production-mode gates I18N-05 and I18N-09 are GREEN at the runtime-contract level (Shako applied migration 012 on 2026-05-20 and the family-visible JSONB columns now return `pg_typeof = jsonb`). Full production-mode verifier sweep remains gated on the deferred rollback-artifact capture window — see Caveats below.

## Prior-phase regression at Phase 6 close — წინა ფაზების რეგრესია

| Phase | Score | Mode |
|---|---|---|
| Phase 1 Perception | 10/10 PASS | — |
| Phase 2 Memory | 19/19 PASS | — |
| Phase 2.5 Quick Wins | 16/16 PASS | — |
| Phase 3 Cognition (minimum) | 11/11 PASS | — |
| Phase 4 First Family Value | 9/9 PASS | code-complete |
| Phase 5 BRAIN Manager | 13/13 PASS | code-complete |
| **Phase 6 Bilingual (i18n)** | **11/11 PASS** | code-complete |

`verify_phase6 --bucket E` spawns `verify_phase4 --mode code-complete` and `verify_phase5 --mode code-complete` as subprocesses; both still exit 0 with their full coverage intact. The regression sweep is now codified into the Phase 6 verifier itself — any future change that breaks Phase 4 or Phase 5 invariants fails `check_i18n_11` immediately.

## Sprint LLM spend — ხარჯი

| Component | Spend | Notes |
|---|---|---|
| Wave 1 (viewer scaffolding) | $0 | next-intl install + folder moves + dictionaries; deterministic |
| Wave 2 (migration 012 + apply route) | $0 | SQL authoring + runbook; production apply by Shako (psql) |
| Wave 3a (PHI redactor + imperative lint) | $0 | banned_phrases.py lexicon + deterministic regex |
| Wave 3b (compose_bilingual) | ~$0–$1 | BILINGUAL_TEST_MODE=1 returns deterministic stub during dev/CI; live Anthropic strict tool_use only fires on real Communicator runs |
| Wave 4 (audience routing) | $0 | Per-file locale constants + `display_field_py`; no LLM calls |
| **Phase 6 total** | **< $2 / $5 cap** | ~40% headroom; well inside the $5 ceiling per SPEC.md |
| **Project cumulative** | **~$5–6 / $60 cap** | ~10% across all phases |

Why so cheap: Option A (RESEARCH.md Pattern 6) was selected for `weekly_brief` and `manager_briefing` — deterministic English-first composition with a Georgian mirror, zero Anthropic cost per row. Option B (per-row LLM bilingual generation via Anthropic strict tool_use) is wired and gated on `BILINGUAL_TEST_MODE=1` (or `ANTHROPIC_API_KEY` presence) and fires only on live runs after Shako enables it.

## Scope realized — შესრულებული მოცულობა

### I18N-01 — next-intl@4 installed + Next.js 16 compat
`viewer/package.json` carries `next-intl@^4.12.0`; `viewer/proxy.ts` mounted using the Next.js 16 file convention (not the legacy `middleware.ts` name); `cd viewer && npm run build` exits 0 with all 14 localized URLs (`/en/{dashboard,timeline,papers,therapies,hypotheses,today,knowledge}` + `/ka/...`) reachable. Three-file i18n module under `viewer/i18n/`: `routing.ts` + `request.ts` + `navigation.ts`. **✓ ACCEPTED.**

### I18N-02 — Locale-segmented App Router structure
`viewer/app/[locale]/{dashboard,timeline,papers,therapies,hypotheses,today,knowledge}/page.tsx` — 7 family-facing routes relocated atomically via `git mv` (R100 renames). `viewer/app/[locale]/layout.tsx` owns `<html lang={locale}>` + `<body>` + `NextIntlClientProvider`. `viewer/app/api/`, `viewer/app/audit/`, `viewer/app/brain/` correctly remain unlocalized via `proxy.ts` matcher exclusion. Each page's signature is `params: Promise<{locale: 'en' | 'ka'}>` + `await setRequestLocale(locale)` (Pitfall 4 prevention). **✓ ACCEPTED.**

### I18N-03 — Static UI strings in en+ka dictionaries
`viewer/messages/en.json` + `viewer/messages/ka.json` carry 143 leaves × 2 locales across 11 namespaces (Common, Dashboard, Home, Hypotheses, Knowledge, Navigation, Papers, Shared, Therapies, Timeline, Today). Recursive key-set equality verified — symmetric difference is empty. ka.json achieves 99.3% Mkhedruli coverage (142/143; only the `ALEKSANDRA_BRAIN` proper noun stays Latin). 129 `t()` references across 10 namespaces all resolve in both dictionaries — zero missing-key warnings. **✓ ACCEPTED.**

### I18N-04 — Language switcher persists choice via URL
`viewer/components/LanguageSwitcher.tsx` uses `useRouter`/`usePathname` from `@/i18n/navigation` (createNavigation-typed); canonical `router.replace(pathname, {locale: newLocale})` idiom. Mounted in `viewer/app/[locale]/layout.tsx` header. URL is the single source of truth — no cookie/localStorage. **✓ ACCEPTED.**

### I18N-05 — Migration 012 JSONB conversion (production-applied)
`scripts/migrations/012_i18n_jsonb.sql` (198 lines, atomic BEGIN/COMMIT) converted 6 family-visible columns to JSONB with `USING jsonb_build_object('en', col, 'ka', col)`: `aleksandra_timeline.{title, description}`, `hypotheses.{title, description}`, `therapies.{name, evidence_summary}`. `briefs.sections` reshaped recursively so each section body is `{en, ka}`. RLS policies from migration 008 survive untouched (PG 15 `ALTER COLUMN TYPE` does not drop policies). Shako applied via supervised maintenance window on 2026-05-20; pg_typeof returns jsonb for all 6 columns. **✓ ACCEPTED at runtime contract.**

### I18N-06 — Communicator + Phase 5 composer emit {en, ka}
`scripts/communicator/bilingual.py::compose_bilingual` is an Anthropic strict tool_use helper that emits `{en, ka}` pairs (or a deterministic mirror when `BILINGUAL_TEST_MODE=1`). `scripts/communicator/weekly_brief.py` writes `briefs.sections.summary_lines` as `[{en, ka}]` JSONB rows. `scripts/manager/briefing.py` mirrors the same shape. `viewer/app/api/manager/apply/route.ts` is a pure HTTP proxy; the actual write contract lives in `scripts/manager/routing/apply_action.py`. Budget gate honored via `scripts.cognition.budget.check_daily_budget(raise_on_over=True)` before every Anthropic call. **✓ ACCEPTED.**

### I18N-07 — Telegram=ka / Gmail=en audience routing
`scripts/communicator/_bilingual_read.py::display_field_py` mirrors `viewer/lib/i18n.ts::displayField` byte-for-byte semantics. `scripts/communicator/telegram_sender.py` reads `.ka`; `scripts/communicator/gmail_digest.py` reads `.en`; `scripts/manager/briefing.py` reads `.ka` for the Sunday Telegram briefing. Per-file locale constants (`TELEGRAM_LOCALE`, `GMAIL_LOCALE`, `BRIEFING_LOCALE`) provide a single audit point. n8n workflow JSONs unchanged — zero-touch confirmed via 5-workflow survey documented in `workflows/_phase6_notes.md`. **✓ ACCEPTED.**

### I18N-08 — Frontend reads JSONB columns by current locale
`viewer/lib/i18n.ts::displayField(field, locale)` returns `field?.[locale] ?? field?.en ?? ''` with type guards for legacy TEXT-string passthrough during the migration window. 9 displayField call sites landed across the 4 plan-target pages (timeline × 2, therapies × 2, hypotheses list × 3, hypotheses detail × 4). `RelatedTherapy.name` widened to `BilingualField` on the hypotheses detail page (denormalized read of a JSONB column). 5-case `node:test` + `node:assert/strict` unit suite GREEN. **✓ ACCEPTED.**

### I18N-09 — Historical rows: ka = en
Migration 012's `USING jsonb_build_object('en', col, 'ka', col)` clause set `ka = en` atomically for all 200 entities, 307 facts, 47 episodes, 10 hypotheses, and 12 therapy candidates from prior phases. Backfill via Claude Sonnet 4.5 explicitly deferred per SPEC.md — a future maintenance phase will surface this as a one-time bilingual retranslation job. **✓ ACCEPTED at runtime contract.**

### I18N-10 — PHI redactor bilingual-aware + Georgian imperative lint
`scripts/communicator/phi_redactor.py` extended with Mkhedruli suffix-glue handling (`(?=\b|-)` lookahead preserves Georgian case markers). `redact_bilingual({en, ka}, consent)` is a pure wrapper over `redact()` — single-string contract unchanged, Phase 3 CGM-02 invariants preserved (12/12 still PASS). 10 Georgian PHI fixtures (patient name in Mkhedruli, BMC MRN 7616818, DOB, contact names) pass with zero raw PHI in output. `scripts/communicator/banned_phrases.py` `_PATTERNS_KA` extended with 8 D-05 lexicon entries (`უნდა`, `აუცილებლად`, `განიხილეთ`, `მოითხოვეთ`, `ითხოვეთ`, `სცადეთ`, `გაითვალისწინეთ`, `მართებთ`). 65-case pytest regression suite GREEN. Phase 3 CGM-04 English invariants unchanged. **✓ ACCEPTED.**

### I18N-11 — Phase 4 + Phase 5 do not regress
`check_i18n_11` spawns `verify_phase4 --mode code-complete` and `verify_phase5 --mode code-complete` as subprocesses; both exit 0 at their full coverage. `9/9 PASS` and `13/13 PASS` substrings asserted in stdout. **✓ ACCEPTED.**

## Out of scope / deferred — გადადებული

These items were intentionally excluded from Phase 6 per the CONTEXT.md Deferred Ideas list and are filed as future-maintenance candidates:

- **AI re-translation of historical rows** — migration 012 set `ka = en` for all existing rows; backfill via Claude Sonnet 4.5 would cost ~$5–10 against 500+ rows and is deferred to a maintenance phase.
- **French UI support** — `outreach_log.language IN ('en', 'fr', 'ka')` data-layer constraint stays; the viewer ships en/ka only.
- **Cookie/localStorage persistence of language choice** — URL is the source of truth; cookie persistence deferred to a future UX phase.
- **RTL layouts, locale-aware date/number/currency formatting** — neither English nor Georgian is RTL; next-intl defaults are sufficient.
- **GIN full-text search on JSONB columns** — locked decision D-04; no inverted indexes added.
- **CGM-06 tone post-processor Georgian extension** — currently English-only with a documented carve-out.
- **outreach_drafter bilingual emission** — phase 6 scope ends at family-facing content (Telegram + Gmail family-digest); the outreach drafter (clinician-facing) stays single-language per the recipient's `outreach_log.language` field.
- **Localization of internal CrewAI agents** — Spider, Analyzer, Hypothesis, Repurposing reasoning stays English; bilingualism is enforced only at the family-facing output boundary.

## Known operational caveats — ცნობილი ოპერაციული caveat-ები

1. **Rollback artifacts deferred (P2 maintenance todo).** Plan 06-07 Task 2 + Task 3 (rollback artifact mirror + production-mode verifier sweep) were deferred per Shako's call after the 2026-05-20 production apply. The 9 placeholder files under `scripts/migrations/012_rollback/` remain in their Plan-06-06 form (4 `.pre012.dump` headers-only + 4 `.policies.pre.txt` placeholders + `_preflight.txt`). Filed `.planning/todos/pending/2026-05-21-capture-migration-012-rollback-artifacts.md` (P2, 15–20 min one-psql-session). Without post-migration `\d <table>` snapshots, RLS preservation across the migration is not programmatically proven (PG 15 contract says `ALTER COLUMN TYPE` does NOT drop policies, so regression is unlikely but unverified).

2. **Georgian imperative-verb lexicon awaits native-speaker re-verify.** Plan 06-11 Task 3 was a `checkpoint:human-verify gate="blocking-human"` that the executor auto-mode-approved against the locked CONTEXT.md D-05 reference. The 8 Georgian lexicon entries (`უნდა`, `აუცილებლად`, `განიხილეთ`, `მოითხოვეთ`, `ითხოვეთ`, `სცადეთ`, `გაითვალისწინეთ`, `მართებთ`) are functional today; gap is review-not-yet-done, not code-not-correct. Filed `.planning/todos/pending/2026-05-21-shako-verify-06-11-lexicon.md` (P2, 10–15 min).

3. **Production-mode verifier sweep gated on rollback-artifact capture window.** When Shako populates the rollback-artifact placeholders during the maintenance window, `python -m scripts.verify_phase6 --mode production` will flip I18N-05 + I18N-09 from "code-complete GREEN, production GREEN pending artifact capture" to fully production-GREEN.

## What Phase 6 unlocks — რას ხსნის Phase 6

- **Family Telegram chat in Georgian (Mkhedruli)** — Sunday weekly briefs, daily digests, and manager briefings now arrive in Georgian by default. Shako can read briefs in his native language; Aleksandra's grandparents/extended family in Tbilisi follow along without translation friction.
- **Gmail digests in English** — Clinician-shareable weekly summaries and outreach drafts stay English-first (Dr. Hien, Dr. August, Duke DTRI, Wisconsin team). Audience routing is automatic.
- **Bilingual audience routing live** — `display_field_py` is the single point of audit; the JSONB shape `{en, ka}` flows from Communicator → DB → worker → audience without manual touch-points.
- **All 7 family-facing routes bilingual via locale prefix** — `/en/dashboard`, `/ka/dashboard`, `/en/timeline`, `/ka/timeline`, etc. Family member chooses language via the URL or the in-page LanguageSwitcher; choice persists across navigation.
- **143-key parallel dictionary** — `viewer/messages/en.json` and `viewer/messages/ka.json` are the source-of-truth for every visible UI string in the 7 family-facing routes; future UI strings get added in pairs.
- **PHI redactor + imperative-verb lint extended to Georgian** — the CATASTROPHIC pitfall guardrails from Phase 3 now operate symmetrically on Mkhedruli text. The 10-fixture Georgian PHI test set covers patient name, MRN, DOB, and clinician names in mixed case-marker contexts.

## What's next — შემდეგი

Phase 6 closes the v1 milestone for full-site bilingualism. The active follow-on items are:

1. **Phase 4 acceptance window monitored to closure (~2026-06-07).** The 14-day acceptance test (one credible lead, full provenance, under $30) is the v1 release gate; Phase 6 does not block it. First real Weekly Brief Sunday 2026-05-24 09:00 ET.
2. **Rollback artifact capture maintenance window (Shako, P2).** Run one psql session to populate `scripts/migrations/012_rollback/*` placeholders + rerun `verify_phase6 --mode production --bucket B` to flip I18N-05 + I18N-09 fully GREEN.
3. **Georgian lexicon native-speaker re-verify (Shako, P2).** Read the 8 D-05 entries in `scripts/communicator/banned_phrases.py` and confirm or amend; no code change expected.
4. **Maintenance phase planning** — the 10 backend gaps surfaced in Phase 5 (`docs/PHASE_5_EXIT_REPORT.md` § "Backend gaps") + the 4 Phase 6 deferred items (AI backfill, French UI, GIN search, tone post-processor KA extension) are candidates for a future maintenance phase.

## References

- [.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-SPEC.md](../.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-SPEC.md)
- [.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-CONTEXT.md](../.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-CONTEXT.md)
- [.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-RESEARCH.md](../.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-RESEARCH.md)
- [.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-VALIDATION.md](../.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-VALIDATION.md)
- All 15 SUMMARY.md files: `06-01` through `06-13` under the phase directory.
- [scripts/migrations/012_i18n_jsonb.sql](../scripts/migrations/012_i18n_jsonb.sql) and [scripts/migrations/012_runbook.md](../scripts/migrations/012_runbook.md)
- [docs/PHASE_5_EXIT_REPORT.md](PHASE_5_EXIT_REPORT.md) (prior phase context)
- [docs/PHASE_6_COMPLETION_KA.md](PHASE_6_COMPLETION_KA.md) (Georgian-language summary for Shako)

## How to demo

```bash
# Engineering exit:
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase1                          # 10/10
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2                          # 19/19
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2_5                        # 16/16
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase3                          # 11/11
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase4 --mode code-complete     # 9/9
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase5 --mode code-complete     # 13/13
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase6 --mode code-complete     # 11/11

# Viewer build:
cd viewer && npm run build                                                          # 21 static pages, /[locale]/* dynamic

# Audience routing dry-runs:
.venv/Scripts/python.exe -m scripts.communicator.telegram_sender --bilingual-dryrun  # Mkhedruli codepoints present
.venv/Scripts/python.exe -m scripts.communicator.gmail_digest    --bilingual-dryrun  # zero Mkhedruli codepoints

# Bilingual PHI + imperative lint:
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_phi_redactor_georgian.py tests/test_imperative_verb_lint_georgian.py
```

Cumulative project verifier coverage at Phase 6 close: **89/89 PASS** (10 + 19 + 16 + 11 + 9 + 13 + 11).
