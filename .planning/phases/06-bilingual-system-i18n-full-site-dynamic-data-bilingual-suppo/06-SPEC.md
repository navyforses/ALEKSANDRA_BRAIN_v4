# Phase 6: Bilingual System (i18n) — Specification

**Created:** 2026-05-20
**Ambiguity score:** 0.17 (gate: ≤ 0.20)
**Requirements:** 11 locked
**Seed plan:** [docs/I18N_PLAN.md](../../docs/I18N_PLAN.md)
**Mode:** auto (Auto Mode active; spec written without interactive interview — all decisions documented in Interview Log)

## Goal

By the end of this phase, every family-facing viewer route is reachable under `/en/*` and `/ka/*` URL segments and renders fully in the matching language; the 4 family-visible dynamic tables (`aleksandra_timeline`, `hypotheses`, `therapies`, `briefs`) store en+ka pairs in JSONB columns with English fallback; the Communicator and Phase 5 composer emit `{en, ka}` pairs for all newly-created family-visible content; and Telegram delivery uses `.ka` while Gmail delivery uses `.en`.

## Background

Current state (verified 2026-05-20 against the codebase):

- **Viewer scaffolding is half-baked.** [viewer/i18n.ts](../../viewer/i18n.ts), [viewer/middleware.ts](../../viewer/middleware.ts), and [viewer/components/LanguageSwitcher.tsx](../../viewer/components/LanguageSwitcher.tsx) all import from `next-intl`, but `next-intl` is **not** listed in [viewer/package.json](../../viewer/package.json) dependencies — the viewer currently does not build with those files referenced. [en.json](../../en.json) and [ka.json](../../ka.json) sit at the **repo root**, not under `viewer/messages/`. The `viewer/messages/` directory does not exist. None of the 11 routes in [viewer/app/](../../viewer/app/) sit under an `app/[locale]/` segment.
- **Existing scaffolding uses outdated next-intl API.** [viewer/i18n.ts:6](../../viewer/i18n.ts#L6) uses `getRequestConfig(async ({locale}) => ...)` — the next-intl 3.22+ / Next.js 15+ API is `getRequestConfig(async ({requestLocale}) => ...)`.
- **Next.js 16.2.6 + React 19.2.4** per [viewer/package.json:13-14](../../viewer/package.json#L13-L14). [viewer/AGENTS.md](../../viewer/AGENTS.md) explicitly warns: *"This is NOT the Next.js you know."* next-intl 4.x compatibility with Next.js 16 must be verified during /gsd-plan-phase research.
- **Phase 5 already has input language detection.** [scripts/communicator/language.py](../../scripts/communicator/language.py) is a deterministic detector for en/fr/ka **input**. It writes the detected code into [outreach_log.language](../../scripts/migrations/008_phase3_tables_and_rls.sql#L168) (CHECK constraint already allows `'en', 'fr', 'ka'`). This is a per-outreach routing decision; it is NOT bilingual storage. Phase 6 adds **output** bilingualism alongside it; the detector stays.
- **Target tables:**
  - [aleksandra_timeline](../../scripts/migrations/002_aleksandra_timeline.sql#L7-L20) — `title text NOT NULL`, `description text`, `institution text`, `location text` (all TEXT today).
  - `hypotheses` (in [scripts/schema.sql](../../scripts/schema.sql)) — `title`, `description` TEXT NOT NULL, plus `ai_reasoning`, `discovery_method`, `recommended_action` TEXT nullable; already has JSONB array columns (`supporting_papers`, `contradicting_papers`).
  - `therapies` (in [scripts/schema.sql](../../scripts/schema.sql)) — `name` NOT NULL, `mechanism_of_action`, `evidence_summary`, `aleksandra_notes`, `ai_assessment` TEXT.
  - [briefs.sections](../../scripts/migrations/008_phase3_tables_and_rls.sql#L277-L314) — **already JSONB** (current shape is `{section_id, body, ...}`; needs `{en, ka}` keyed shape per section).
- **Migrations 001–011 exist.** Next migration number is **012**. Migration 008 applied RLS tighten on 10 base tables (read-restrict to family identity, write-restrict to service-role). Migration 012 must preserve all of that.
- **n8n workflows touching delivery:** `telegram_daily_digest.json`, `daily_digest.json`, `weekly_brief.json`, `manager_briefing.json`, `outreach_review_queue.json` per scout. These currently consume single-language fields.

The delta from today to the target state is sweeping but bounded — the SPEC defines exactly which routes, columns, agents, and workflows are touched.

## Requirements

1. **I18N-01 — next-intl installed and compatible with Next.js 16.2.6**: The viewer can build with locale routing enabled.
   - Current: `next-intl` is NOT in [viewer/package.json](../../viewer/package.json); existing `i18n.ts`, `middleware.ts`, `LanguageSwitcher.tsx` reference an uninstalled module
   - Target: a `next-intl` version (or equivalent shim if no compatible version exists) is added to `viewer/package.json` such that `npm run build` succeeds with `/en/dashboard` and `/ka/dashboard` reachable; the compatibility decision is documented in the phase CONTEXT.md
   - Acceptance: `cd viewer && npm install && npm run build` exits 0; the build artifact serves `/en/dashboard` and `/ka/dashboard` as distinct pre-rendered routes

2. **I18N-02 — Locale-segmented App Router structure**: Family-facing routes live under `app/[locale]/*`.
   - Current: `viewer/app/{dashboard, timeline, papers, therapies, hypotheses, today, knowledge}` are at top level; no `[locale]` segment exists
   - Target: those 7 family-facing route directories are moved under `viewer/app/[locale]/`; `viewer/app/api/`, `viewer/app/audit/`, `viewer/app/brain/` remain unlocalized (see Out of Scope)
   - Acceptance: Visiting `/en/dashboard`, `/ka/dashboard`, `/en/timeline`, `/ka/timeline`, `/en/therapies`, `/ka/therapies`, `/en/papers`, `/ka/papers`, `/en/hypotheses`, `/ka/hypotheses`, `/en/today`, `/ka/today`, `/en/knowledge`, `/ka/knowledge` each return HTTP 200; visiting bare `/dashboard` redirects to `/en/dashboard` (defaultLocale)

3. **I18N-03 — Static UI strings exist in en+ka dictionaries under viewer/messages/**: The static dictionary lives where next-intl expects it.
   - Current: [en.json](../../en.json) and [ka.json](../../ka.json) at repo root contain only 7 keys each; `viewer/messages/` does not exist
   - Target: `viewer/messages/en.json` and `viewer/messages/ka.json` exist; each contains keys for **every** visible string in the 7 family-facing routes (navigation, page titles, button labels, empty states, loading states, common dates/counts). Root-level `en.json`/`ka.json` are deleted to remove ambiguity
   - Acceptance: a verifier script asserts every `useTranslations(...)('...')` / `t('...')` reference in `viewer/app/[locale]/**` and `viewer/components/**` resolves to a key present in BOTH `en.json` and `ka.json` — zero missing-key warnings

4. **I18N-04 — Language switcher persists choice via URL**: User language toggles cleanly.
   - Current: [viewer/components/LanguageSwitcher.tsx](../../viewer/components/LanguageSwitcher.tsx) exists with `EN | GE` buttons but cannot work until I18N-01 lands
   - Target: the switcher is mounted in the layout header of `viewer/app/[locale]/layout.tsx`; clicking `EN` or `GE` swaps the URL locale prefix and re-renders the page; the choice is reflected in the URL (no cookie/localStorage required — URL is the source of truth)
   - Acceptance: From `/en/dashboard`, clicking `GE` navigates to `/ka/dashboard` and the visible labels change to Georgian; the inverse also works; refresh preserves locale via URL

5. **I18N-05 — Migration 012 converts 4 family-visible TEXT columns to JSONB with en+ka shape, preserving existing data**: The DB schema admits bilingual content without data loss.
   - Current: `aleksandra_timeline.{title, description}` are TEXT; `hypotheses.{title, description}` are TEXT; `therapies.{name, evidence_summary}` are TEXT; `briefs.sections` is JSONB but section bodies are single-language strings
   - Target: [scripts/migrations/012_i18n_jsonb.sql](../../scripts/migrations/012_i18n_jsonb.sql) (new file) converts those 6 columns to JSONB with shape `{"en": <prior text>, "ka": <prior text>}`; for `briefs.sections`, each section body is rewritten to `{"en": <prior body>, "ka": <prior body>}`; RLS policies from migration 008 are preserved untouched; the migration includes a documented rollback path (pre-migration `pg_dump` of the 4 tables stored in `scripts/migrations/012_rollback/`)
   - Acceptance: a pre-migration `pg_dump --table` of the 4 tables exists at the rollback path; after migration, `SELECT title->>'en' FROM aleksandra_timeline LIMIT 5` returns non-NULL values matching pre-migration content; a follow-up dry-run `psql -c "ROLLBACK" -f 012_rollback.sql` succeeds on a copy

6. **I18N-06 — Communicator + Phase 5 composer emit `{en, ka}` for family-visible newly-created content**: The write path produces bilingual payloads.
   - Current: [agents/communicator.py](../../agents/communicator.py) + scripts under [scripts/communicator/](../../scripts/communicator/) (notably `weekly_brief.py`, `summarize.py`) emit single-language strings, with input language detected via [language.py](../../scripts/communicator/language.py)
   - Target: when the Communicator drafts a brief section, hypothesis row, therapy row, or timeline row that is **family-visible**, it emits a `{en: <english>, ka: <georgian>}` object; the existing English-first writing path stays — the Georgian is added by either (a) prompting the LLM for both languages in a single structured-output call, or (b) a single Anthropic translation call afterward, decision deferred to /gsd-plan-phase
   - Acceptance: a smoke test runs the weekly brief composer end-to-end and asserts every JSONB column in the newly-written `briefs` and `aleksandra_timeline` rows has both `en` and `ka` keys with non-empty strings; the [scripts/communicator/phi_redactor.py](../../scripts/communicator/phi_redactor.py) flow is exercised with Georgian text and still redacts PHI (MRN, DOB, names per policy)

7. **I18N-07 — Telegram → ka, Gmail → en audience routing**: Delivery channels split by language.
   - Current: 5 n8n workflows under [workflows/](../../workflows/) (`telegram_daily_digest.json`, `daily_digest.json`, `weekly_brief.json`, `manager_briefing.json`, `outreach_review_queue.json`) reference single-language content
   - Target: Telegram-sending nodes read `*.ka`; Gmail-sending nodes read `*.en`; outreach_review_queue continues to honor `outreach_log.language` per-contact (English/French/Georgian) — that pre-existing per-contact routing is NOT overridden by Phase 6
   - Acceptance: a dry-run of `weekly_brief.json` produces a Telegram message body that contains Georgian characters (codepoints in U+10A0–U+10FF range) and a Gmail draft body that contains zero Georgian characters; the run ID is logged

8. **I18N-08 — Frontend reads JSONB columns by current locale with English fallback**: The viewer renders the right language.
   - Current: viewer code (where it reads these tables) consumes plain strings
   - Target: a small client/server utility `viewer/lib/i18n.ts` exposes `displayField(field, locale)` returning `field?.[locale] ?? field?.en ?? ''` (with type guards for legacy non-JSONB rows during migration window); all Timeline, Dashboard, and Therapies components read JSONB fields through this utility
   - Acceptance: rendering Timeline at `/ka/timeline` with mixed-locale rows shows Georgian where present and falls back to English where `.ka` is missing; rendering at `/en/timeline` shows English; no `[object Object]` strings appear; a test row with only `{en: "X"}` (no `ka` key) renders `X` at both locales

9. **I18N-09 — Historical row JSONB shape is set by migration 012 only; AI re-translation of existing rows is OUT of this phase**: We do not block on AI translating prior content.
   - Current: 200 entities, 307 facts, 47 episodes, 10 hypotheses, 12 therapy candidates exist from Phase 2.5; their `.ka` slot will mirror their `.en` slot post-migration (per the I18N_PLAN.md USING clause)
   - Target: migration 012 sets `ka = en` for all existing rows; no AI translation job runs during this phase
   - Acceptance: post-migration, every existing row has identical `.en` and `.ka` content; a follow-up backlog item is filed (not implemented) to run a one-time bilingual backfill against Claude Sonnet 4.5 in a future maintenance phase

10. **I18N-10 — PHI redactor remains bilingual-aware and PHI-leak free**: The CGM-04 / CGM-06 guarantees survive into Georgian output.
    - Current: [scripts/communicator/phi_redactor.py](../../scripts/communicator/phi_redactor.py) operates on English text; banned phrases live in `banned_phrases.py`
    - Target: the redactor runs on both `.en` and `.ka` strings before any Telegram/Gmail/Notion write; the imperative-verb lint (CGM-04) is extended with Georgian equivalents of `should/must/consider/try/ask for/request` (minimal lexicon, decision in /gsd-plan-phase); the tone post-processor (CGM-06) is extended for Georgian or left English-only with a documented carve-out
    - Acceptance: a fixture set of 10 known-PHI Georgian phrases (patient name in Mkhedruli, BMC MRN 7616818, DOB) passes through the redactor and emerges with PHI replaced by neutral tokens; the imperative-verb lint count remains 0 across 30 newly-generated bilingual sample digests

11. **I18N-11 — Phase 5 + Phase 4 do not regress**: i18n changes do not break already-shipped capabilities.
    - Current: `verify_phase4 --mode code-complete` = 9/9 PASS, `verify_phase5 --mode code-complete` = 13/13 PASS, cumulative 78/78 verifier coverage
    - Target: after Phase 6 lands, both verifiers still pass at the same scores; Phase 5 operator activation (the ~45min Shako task in docs/PHASE_5_OPERATOR_RUNBOOK.md) is unblocked — it does not need to be completed before Phase 6, but Phase 6 must not make it harder
    - Acceptance: `python -m scripts.verify_phase4 --mode code-complete` exits 0 with 9/9 PASS, `python -m scripts.verify_phase5 --mode code-complete` exits 0 with 13/13 PASS, and a new `python -m scripts.verify_phase6` will be authored during /gsd-execute-phase that exits 0 with all I18N-* requirements PASS

## Boundaries

**In scope:**
- next-intl (or equivalent) install + Next.js 16 compatibility resolution
- Locale segmentation of 7 family-facing routes: `dashboard`, `timeline`, `papers`, `therapies`, `hypotheses`, `today`, `knowledge`
- `viewer/messages/{en,ka}.json` dictionaries covering all static UI strings in those 7 routes + shared components
- LanguageSwitcher mounted in localized layout header
- Migration 012: JSONB conversion of 6 columns (4 tables) with rollback artifact
- Communicator + Phase 5 composer emitting `{en, ka}` pairs for newly-created family-visible rows
- n8n Telegram/Gmail routing by `.ka` / `.en` for 5 workflows
- `viewer/lib/i18n.ts` utility for locale-aware field read with English fallback
- PHI redactor + imperative-verb lint extension to Georgian (minimal lexicon)
- Phase-6 verifier script (`scripts/verify_phase6.py`)

**Out of scope:**
- `viewer/app/api/`, `viewer/app/audit/`, `viewer/app/brain/` localization — APIs have no UI; `/audit` is internal admin tooling that operator runs in English; `/brain` is the MRI viewer (NiiVue) where medical labels stay clinical-English by convention. These remain top-level routes.
- French (`fr`) UI support — the existing `outreach_log.language IN ('en', 'fr', 'ka')` constraint stays, but the viewer ships en/ka only. fr is preserved at the data layer for outbound clinician French emails per Phase 3 CGM-07.
- AI re-translation of the 200 entities / 307 facts / 47 episodes / 10 hypotheses / 12 therapies — migration 012 sets `ka = en` for existing rows; a separate future backlog item handles bilingual backfill (cost reason: an AI translation pass against 500+ rows is a Claude budget hit that doesn't belong in this phase's $5/mo cap).
- Cookie or localStorage persistence of language choice — URL is the source of truth; deferred to a future UX phase.
- RTL layouts, locale-aware date/number formatting beyond next-intl defaults, currency formatting, plural rules beyond next-intl defaults — neither English nor Georgian is RTL; basic next-intl handling is sufficient.
- Renaming columns or restructuring tables beyond the JSONB type conversion — migration 012 is a TYPE change, not a SCHEMA refactor.
- Localization of the 5 CrewAI internal agents (Spider, Analyzer, Hypothesis, Repurposing) — their internal reasoning stays English; bilingualism is only at the family-facing output boundary (Communicator + Phase 5 composer).
- Translating REQUIREMENTS.md, PROJECT.md, ROADMAP.md, or any `.planning/` documentation — engineering docs stay English per CLAUDE.md language convention.

## Constraints

- **Next.js 16.2.6 compatibility**: next-intl must compile and run on Next.js 16.2.6 + React 19.2.4; if the latest stable next-intl does not support Next.js 16, /gsd-plan-phase must choose between (a) downgrading viewer to Next.js 15, (b) using `paraglide-js`, or (c) writing a thin custom locale shim. Decision belongs to plan-phase research, not SPEC.
- **Migration 012 must preserve RLS from migration 008**: the family-only read + service-role-only write policies for `aleksandra_timeline`, `hypotheses`, `therapies`, `briefs` must remain intact after the TYPE conversion. `ALTER COLUMN ... TYPE` does not drop policies, but it does invalidate indexes — any TEXT-based indexes on these columns must be rebuilt as GIN indexes on JSONB.
- **No data loss**: migration 012 uses `USING jsonb_build_object('en', col, 'ka', col)` so existing English text is preserved in both slots; a pre-migration `pg_dump` of the 4 tables is written to `scripts/migrations/012_rollback/` before any `ALTER` runs.
- **Cost ceiling**: Phase 6 LLM cost ceiling is $5 (additional to running budget). Bilingual generation in Communicator may add ~30–50% to per-draft Anthropic spend; this stays within the project $60 cap (currently $4.22 / $60).
- **Privacy non-negotiable**: PHI redactor must pass Georgian fixtures (MRN, DOB, patient name in Mkhedruli) — see I18N-10. No Georgian PHI may appear in Telegram messages, Gmail drafts, or Notion archive.
- **Phase 5 operator activation is not blocked by Phase 6**: the two run independently; Shako can complete Phase 5 activation before, during, or after Phase 6.

## Acceptance Criteria

- [ ] `cd viewer && npm install && npm run build` exits 0 with `next-intl` (or chosen equivalent) installed
- [ ] `/en/dashboard`, `/ka/dashboard`, `/en/timeline`, `/ka/timeline`, `/en/therapies`, `/ka/therapies`, `/en/papers`, `/ka/papers`, `/en/hypotheses`, `/ka/hypotheses`, `/en/today`, `/ka/today`, `/en/knowledge`, `/ka/knowledge` all return HTTP 200
- [ ] Bare `/dashboard` 308-redirects to `/en/dashboard`
- [ ] `viewer/messages/en.json` and `viewer/messages/ka.json` exist; root `en.json` and `ka.json` deleted
- [ ] Every `t(...)` / `useTranslations(...)('...')` reference in `viewer/app/[locale]/**` + `viewer/components/**` resolves to a key in both message files (verifier check zero missing-keys)
- [ ] LanguageSwitcher toggles `/en/*` ↔ `/ka/*` on all 7 family-facing routes
- [ ] [scripts/migrations/012_i18n_jsonb.sql](../../scripts/migrations/012_i18n_jsonb.sql) exists, applies cleanly to the production schema, and rollback artifact `scripts/migrations/012_rollback/*.dump` is present
- [ ] After migration 012, `SELECT title->>'en', title->>'ka' FROM aleksandra_timeline LIMIT 5` returns matching non-NULL values; `SELECT pg_typeof(title) FROM aleksandra_timeline LIMIT 1` returns `jsonb`
- [ ] Migration 008 RLS policies remain attached after migration 012 (verified by `\d aleksandra_timeline` policies block)
- [ ] Running the weekly_brief composer produces a `briefs` row whose `sections` JSONB contains `{en, ka}` keys per section with non-empty strings
- [ ] PHI fixture test (10 Georgian PHI phrases) passes — redactor outputs zero raw PHI tokens
- [ ] `weekly_brief.json` n8n dry-run: Telegram body contains Georgian codepoints; Gmail draft body contains zero Georgian codepoints
- [ ] `python -m scripts.verify_phase4 --mode code-complete` 9/9 PASS (no regression)
- [ ] `python -m scripts.verify_phase5 --mode code-complete` 13/13 PASS (no regression)
- [ ] `python -m scripts.verify_phase6` exits 0 with all I18N-01 .. I18N-11 PASS

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                          |
|--------------------|-------|------|--------|--------------------------------------------------------------------------------|
| Goal Clarity       | 0.85  | 0.75 | ✓      | Single-sentence goal lists 4 outcomes (routes, JSONB, agents, routing)         |
| Boundary Clarity   | 0.85  | 0.70 | ✓      | 9-item in-scope + 8-item out-of-scope with reason per exclusion                |
| Constraint Clarity | 0.75  | 0.65 | ✓      | Next.js 16 compat deferred to plan-phase with named fallbacks                  |
| Acceptance Criteria| 0.85  | 0.70 | ✓      | 14 pass/fail checkboxes, all observable                                        |
| **Ambiguity**      | 0.17  | ≤0.20| ✓      |                                                                                |

## Interview Log

Auto Mode active — no interactive interview. Decisions documented from pre-flight codebase scout + the seed plan in [docs/I18N_PLAN.md](../../docs/I18N_PLAN.md).

| Round | Perspective       | Question summary                                              | Decision locked                                                                                          |
|-------|-------------------|---------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| 1     | Researcher        | What i18n code exists today?                                  | Half-baked scaffolding (uninstalled next-intl); root-level dictionaries; outdated `i18n.ts` API           |
| 1     | Researcher        | What language-handling already exists in agents?              | Phase 3 CGM-07 input-detector in `scripts/communicator/language.py` (en/fr/ka); stays as-is               |
| 2     | Simplifier        | Minimum viable scope?                                         | Rejected — user's intent is "full site"; in-scope is 7 family-facing routes + 4 tables + Communicator   |
| 3     | Boundary Keeper   | What's NOT in this phase?                                     | `/api`, `/audit`, `/brain` not localized; French stays at data layer only; AI re-translation deferred    |
| 3     | Boundary Keeper   | What does "done" look like?                                   | Both locales reachable, 4 tables JSONB, Communicator emits {en,ka}, audience routing splits, Phase 4+5 do not regress |
| 4     | Failure Analyst   | What breaks if requirements are wrong?                        | Data loss in migration 012; RLS dropped; PHI leak in Georgian; Phase 4/5 verifier regression             |
| 4     | Failure Analyst   | What would cause verifier rejection?                          | Build error, missing locale keys, JSONB shape drift, raw Georgian PHI in delivered message               |
| 5     | Seed Closer       | Lock the next-intl + Next.js 16 compat question               | Deferred to plan-phase research with three documented fallbacks (downgrade, paraglide-js, custom shim)   |
| 5     | Seed Closer       | Persistence model for language choice                         | URL is the source of truth; no cookie/localStorage in this phase                                         |
| 6     | Seed Closer       | Historical row translation policy                             | Set `ka = en` in migration 012; AI re-translation deferred to a future backlog item                      |

---

*Phase: 06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo*
*Spec created: 2026-05-20*
*Next step: /gsd-discuss-phase 6 — implementation decisions (next-intl version pick + Next.js 16 compat, JSONB query patterns in backend code, bilingual prompt strategy for Communicator)*
