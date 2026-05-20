# Phase 6: Bilingual System (i18n) - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning
**Mode:** --auto (Auto Mode session-wide; decisions selected via recommended defaults, logged in DISCUSSION-LOG.md)

<domain>
## Phase Boundary

This phase delivers full English+Georgian bilingualism across the family-facing viewer, the 4 dynamic-content tables (`aleksandra_timeline`, `hypotheses`, `therapies`, `briefs`), the Communicator + Phase 5 composer write path, and the n8n delivery routing. Scope is fixed by [06-SPEC.md](./06-SPEC.md) — 11 requirements, 14 acceptance checkboxes.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**11 requirements are locked.** See [06-SPEC.md](./06-SPEC.md) for full requirements (I18N-01 .. I18N-11), boundaries, and acceptance criteria.

Downstream agents MUST read [06-SPEC.md](./06-SPEC.md) before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
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

**Out of scope (from SPEC.md):**
- `viewer/app/api/`, `viewer/app/audit/`, `viewer/app/brain/` localization
- French (`fr`) UI support (data layer keeps the existing CHECK constraint)
- AI re-translation of historical rows (migration 012 sets `ka = en`; future backlog item handles bilingual backfill)
- Cookie or localStorage persistence of language choice (URL is the source of truth)
- RTL layouts, locale-aware date/number formatting beyond next-intl defaults
- Schema refactors beyond TYPE conversion in migration 012
- Localization of the 5 CrewAI internal agents (Spider, Analyzer, Hypothesis, Repurposing) — internal English stays
- Translating REQUIREMENTS.md / PROJECT.md / ROADMAP.md or any `.planning/` documentation

</spec_lock>

<decisions>
## Implementation Decisions

### D-01 · next-intl version + Next.js 16 compatibility

**Decision:** Use `next-intl@4` (latest v4.x). Add to `viewer/package.json` as `"next-intl": "^4.0.0"`.

**Rationale (research-backed via context7):**
- `next-intl@4` was prepared explicitly for Next.js 15+/16 features (PPR, dynamicIO, rootParams) — confirmed in the official upgrade blog post.
- An active "Next.js 16 + next-intl multi-locale boilerplate" exists at [`amuradesign/next.js-16-next-intl-boilerplate`](https://github.com/amuradesign/next.js-16-next-intl-boilerplate) — concrete proof that the pairing works on Next.js 16.x.
- Falls back to the API the SPEC anticipates: `getRequestConfig({requestLocale})` (Next.js 15+) **not** the older `({locale})` shape currently in [viewer/i18n.ts](../../../viewer/i18n.ts).

**Files that change as a consequence:**
- [viewer/package.json](../../../viewer/package.json) — add dep
- [viewer/i18n.ts](../../../viewer/i18n.ts) → rename to `viewer/i18n/request.ts`; migrate to `requestLocale` API
- New file `viewer/i18n/routing.ts` — `defineRouting({locales: ['en', 'ka'], defaultLocale: 'en'})` + `createNavigation(routing)` exports
- [viewer/middleware.ts](../../../viewer/middleware.ts) — switch to importing the `routing` object instead of inlining locales

**Rejected alternatives:**
- ❌ Downgrade viewer to Next.js 15 — costs more than it saves; Next.js 16 features (improved RSC streaming, async params) already adopted in viewer code.
- ❌ `paraglide-js` — smaller ecosystem, would require re-authoring the 3 existing scaffolding files; no clear win.
- ❌ Custom shim — reinvents next-intl's well-tested middleware + RSC integration; brittle.

### D-02 · Bilingual emission strategy in Communicator

**Decision:** Single Anthropic structured-output call returning `{"en": "...", "ka": "..."}` simultaneously (Claude tool_use schema). The Communicator prompt is updated to request both languages in one shot.

**Rationale:**
- 1 call vs 2 = lower per-draft cost (one prompt, one network round-trip).
- Single-context generation keeps medical terminology consistent across `en` and `ka` (no translation drift between a primary draft and a follow-up translation pass).
- PHI redactor ordering becomes simpler: scan the structured output once before any write.
- Within the $5 Phase 6 LLM cost ceiling (Communicator output ≈ 30–50% larger, but total call count unchanged).

**Per-tier policy:**
- Communicator weekly_brief — emit `{en, ka}` per section.
- Phase 5 composer (`scripts/communicator/weekly_brief.py` + manager_briefing assembler) — emit `{en, ka}` per inserted row.
- Internal CrewAI agents (Spider, Analyzer, Hypothesis, Repurposing) — stay English-only (out of scope per SPEC).
- Communicator clinician outreach drafter (`outreach_drafter.py`) — respects `contacts.outreach_language` per recipient; bilingual emission is NOT mandatory here because outreach is single-recipient single-language. Phase 6 leaves this surface alone.

**Rejected alternative:**
- ❌ English-first draft + follow-up translation call — extra latency, extra cost, translation drift risk.

### D-03 · JSONB backend read patterns

**Decision:** Read the whole JSONB column over the wire; the **viewer** extracts the locale via the `displayField(field, locale)` utility specified by I18N-08. Backend APIs (Supabase JS client + manager API routes) do **not** project locale fields server-side.

**Rationale:**
- Single-patient app, low traffic → payload size of "two short strings instead of one" is irrelevant.
- Backend stays locale-agnostic — same query serves both `/en/*` and `/ka/*` viewers.
- The viewer already has `locale` from `useLocale()` (next-intl); applying it client-side is one helper call.
- Easier to debug: a JSONB blob in network tab shows both languages; missing-key bugs surface immediately.

**Utility shape (locked here, code lives in `viewer/lib/i18n.ts`):**
```ts
type BilingualField = string | { en?: string; ka?: string } | null | undefined;
export function displayField(field: BilingualField, locale: 'en' | 'ka'): string {
  if (field == null) return '';
  if (typeof field === 'string') return field;        // legacy TEXT row tolerance
  return field[locale] ?? field.en ?? '';              // strict locale → English fallback
}
```

The `typeof field === 'string'` branch handles the brief window between deploying viewer code and running migration 012 in production. After migration 012 lands, every read returns the object shape — the legacy branch is a safety net, not load-bearing.

**Rejected alternative:**
- ❌ `select=title->>en` projection per query — pushes locale awareness into every backend route, multiplies code paths, no measurable payload win.

### D-04 · Migration 012 GIN index policy

**Decision:** **No GIN indexes** in migration 012. JSONB columns are converted in place; the existing B-tree / event_date / event_type indexes survive because they index different columns. If full-text search on bilingual titles is added in a future phase, GIN can be added then.

**Rationale:**
- Current query patterns on these 4 tables are: order by `event_date` (timeline), filter by `status` / `priority` / `created_at` (hypotheses, therapies, briefs). None filter on `title`, `description`, or `evidence_summary` text content.
- GIN indexes have insertion-time overhead and disk cost; they're a poor default when no query needs them.
- Plan-phase research can re-check current viewer queries to confirm.

**Sanity check** — Re-check during plan-phase research:
- `grep -r "ilike" viewer/app/ scripts/` to confirm no fuzzy-search on these columns
- `grep -r "to_tsvector\|fts" .` to confirm no text-search infrastructure exists

If either grep returns hits on the 4 target tables → revisit decision in plan-phase.

### D-05 · Imperative-verb lint extension for Georgian

**Decision:** Extend [scripts/communicator/banned_phrases.py](../../../scripts/communicator/banned_phrases.py) with a minimal Georgian lexicon mapping to the 6 English imperative verbs already banned by CGM-04. Plan-phase produces the file; execute-phase asks Shako to sanity-check the list before the lint goes live.

**Initial Georgian lexicon (draft — Shako to confirm in execute-phase):**

| English imperative | Georgian forms to ban | Notes |
|---|---|---|
| `should` (giving advice) | `უნდა` (unda), `მართებთ` (martebt) | "unda" is the most common — also benign in subordinate clauses; rule must check it's directed AT the family, not embedded in a quoted source. |
| `must` | `აუცილებლად` (autsileblad), `აუცილებელია` (autsilebelia) | |
| `consider` | `განიხილეთ` (ganikhilet), `გაითვალისწინეთ` (gaitvalistsinet) | Imperative 2nd person plural polite. |
| `try` | `სცადეთ` (stsadet) | |
| `ask for` | `მოითხოვეთ` (moitkhovet) | |
| `request` | `ითხოვეთ` (itkhovet) | |

**Caveat:** Georgian's polite-imperative 2nd person plural is morphologically marked — the lint can run a regex over the verb stems plus suffix `-ეთ` to catch declined forms. Plan-phase decides whether to use a regex or a curated stem list. Initial pass: literal-string match against the table above (cheapest, lowest false-positive rate).

**Acceptance ties:** I18N-10 acceptance test (30 sample digests → imperative-verb count 0) must pass on both en and ka outputs.

### D-06 · Phase 6 verifier coverage map (`scripts/verify_phase6.py`)

**Decision:** Mirror Phase 5's `verify_phase5.py` style. Structure: `--mode code-complete` (default) runs all checks; capability buckets group requirements.

**Coverage map:**

| Bucket | Requirement IDs covered | Check kind |
|---|---|---|
| **A. Frontend bilingual** | I18N-01, I18N-02, I18N-03, I18N-04, I18N-08 | `npm run build` exit code · curl all 14 localized URLs · missing-key grep · LanguageSwitcher smoke test · displayField unit tests |
| **B. Database** | I18N-05, I18N-09 | `pg_typeof = jsonb` per converted column · RLS policy presence · rollback artifact existence · post-migration smoke SELECT |
| **C. Agent output** | I18N-06, I18N-10 | Run weekly_brief composer in dry-run mode → assert JSONB rows have `{en, ka}` keys non-empty · PHI fixture run on Georgian phrases · imperative-verb count = 0 across 30 sample bilingual digests |
| **D. Delivery routing** | I18N-07 | Dry-run weekly_brief.json n8n workflow → assert Telegram body contains Georgian codepoints (U+10A0..U+10FF or U+1C90..U+1CBF) and Gmail body contains zero |
| **E. Regression** | I18N-11 | Spawn `verify_phase4 --mode code-complete` and `verify_phase5 --mode code-complete`; assert both 9/9 + 13/13 PASS |

**Target coverage:** 11/11 PASS (one explicit check per I18N-* requirement, plus regression bucket).

**Cumulative project verifier total** after Phase 6 ships: 78 (existing) + 11 (Phase 6) = **89/89**.

### Claude's Discretion

The user gave Claude latitude (via Auto Mode) on:
- The exact regex shape of the Georgian imperative-verb lint (plan-phase decides between literal string match vs morphological regex)
- Whether `viewer/i18n.ts` is renamed to `viewer/i18n/request.ts` or kept flat (next-intl's docs show both forms work; plan-phase picks one)
- Whether the LanguageSwitcher gets a translated label (`EN | GE` or `English | ქართული`) — UI polish detail
- Whether `scripts/migrations/012_rollback/` is a directory of per-table dumps or a single multi-table dump file (plan-phase picks the cheaper option)

### Folded Todos

No GSD todos matched Phase 6 scope (`gsd-sdk query todo.match-phase 6` → 0 matches).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (gsd-phase-researcher, gsd-planner, gsd-executor) MUST read these before planning or implementing.**

### Phase 6 spec (locked requirements)
- [.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-SPEC.md](./06-SPEC.md) — **Locked requirements — MUST read before planning.** 11 I18N-* requirements with Current/Target/Acceptance triplets; 14 acceptance checkboxes; 9-item in-scope + 8-item out-of-scope.
- [docs/I18N_PLAN.md](../../../docs/I18N_PLAN.md) — Seed plan from Shako; SPEC.md is the canonical version but this preserves the original Georgian-language framing the user articulated.

### Project + roadmap
- [.planning/PROJECT.md](../../PROJECT.md) — Core value, constraints, privacy posture, decision authority.
- [.planning/ROADMAP.md](../../ROADMAP.md) §"Phase 6" — Phase entry; Phase 5 retro-documentation now adjacent for dependency-checking.
- [.planning/REQUIREMENTS.md](../../REQUIREMENTS.md) — Existing FND/PRC/MEM/CGM/ACD/OBS surfaces; note CGM-04 (imperative-verb lint) and CGM-06 (tone post-processor) are the structures Phase 6 extends.
- [.planning/STATE.md](../../STATE.md) — Roadmap Evolution entry for Phase 6 dated 2026-05-20.
- [CLAUDE.md](../../../CLAUDE.md) — Project brain; current phase position; "language: კოდი ინგლისურად, docs ქართულად + ინგლისურად, commits ინგლისურად" convention.

### Phase 4 + Phase 5 dependencies (regression surface)
- [docs/PHASE_5_EXIT_REPORT.md](../../../docs/PHASE_5_EXIT_REPORT.md) — 13/13 PASS reference state; Phase 6 must not regress.
- [docs/PHASE_4_EXIT_REPORT.md](../../../docs/PHASE_4_EXIT_REPORT.md) — 9/9 PASS reference state.
- [docs/PHASE_5_OPERATOR_RUNBOOK.md](../../../docs/PHASE_5_OPERATOR_RUNBOOK.md) — Phase 5 production activation steps; Phase 6 does not block on its completion.

### Database schema + RLS
- [scripts/schema.sql](../../../scripts/schema.sql) — `hypotheses` (~lines 275–332) and `therapies` (~lines 118–176) CREATE TABLE — TEXT columns targeted by migration 012.
- [scripts/migrations/002_aleksandra_timeline.sql](../../../scripts/migrations/002_aleksandra_timeline.sql) — `aleksandra_timeline` CREATE TABLE; `title TEXT NOT NULL`, `description`, `institution`, `location`.
- [scripts/migrations/008_phase3_tables_and_rls.sql](../../../scripts/migrations/008_phase3_tables_and_rls.sql) — RLS policies that migration 012 must preserve; `outreach_log.language IN ('en','fr','ka')` CHECK constraint that stays untouched; `briefs.sections` JSONB definition.
- [scripts/migrations/011_manager_actions_and_intake_drops.sql](../../../scripts/migrations/011_manager_actions_and_intake_drops.sql) — Most recent migration; 012 is next.

### Frontend scaffolding (existing, partial)
- [viewer/i18n.ts](../../../viewer/i18n.ts) — Outdated `getRequestConfig({locale})` shape; migrate to `({requestLocale})` per D-01.
- [viewer/middleware.ts](../../../viewer/middleware.ts) — Inline locales array; will switch to importing `routing` from new `viewer/i18n/routing.ts`.
- [viewer/components/LanguageSwitcher.tsx](../../../viewer/components/LanguageSwitcher.tsx) — Functional today (uses `useLocale`); will work as-is once next-intl is installed and routing is wired.
- [viewer/package.json](../../../viewer/package.json) — Add `next-intl@^4.0.0`.
- [viewer/AGENTS.md](../../../viewer/AGENTS.md) — Critical warning: "This is NOT the Next.js you know" — researcher MUST consult Next.js 16 docs (under `viewer/node_modules/next/dist/docs/`) before writing routing code.
- [en.json](../../../en.json) + [ka.json](../../../ka.json) — Currently at repo root; move to `viewer/messages/`.

### Agent + Communicator code
- [agents/communicator.py](../../../agents/communicator.py) — CrewAI wrapper for Communicator role; uses `scripts/communicator/*` modules.
- [scripts/communicator/language.py](../../../scripts/communicator/language.py) — Input language detector (en/fr/ka); stays as-is; complements Phase 6 output bilingualism.
- [scripts/communicator/weekly_brief.py](../../../scripts/communicator/weekly_brief.py) — Brief composer (Phase 5); target of D-02 bilingual emission.
- [scripts/communicator/phi_redactor.py](../../../scripts/communicator/phi_redactor.py) — PHI redactor; extend to scan Georgian per I18N-10.
- [scripts/communicator/banned_phrases.py](../../../scripts/communicator/banned_phrases.py) — Imperative-verb lint source; extend per D-05.

### n8n workflows
- [workflows/](../../../workflows/) — Inspect `telegram_daily_digest.json`, `daily_digest.json`, `weekly_brief.json`, `manager_briefing.json`, `outreach_review_queue.json` for Telegram/Gmail node bodies that read content fields.

### Library docs (refresh during plan-phase research)
- next-intl v4 — https://next-intl.dev/blog/next-intl-4-0 — version 4 prep for Next.js 16 features.
- next-intl 3.22 → 4 migration — https://next-intl.dev/blog/next-intl-3-22 — `requestLocale` API.
- Next.js 16 + next-intl boilerplate — https://github.com/amuradesign/next.js-16-next-intl-boilerplate — concrete file layout reference.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`scripts/communicator/language.py`** — Deterministic en/fr/ka detector. Phase 6 keeps it untouched; complements (not replaces) bilingual output emission.
- **`scripts/communicator/phi_redactor.py`** — Already PHI-aware; extending it for Georgian is additive (same regex/lexicon pattern).
- **`scripts/communicator/banned_phrases.py`** — Already implements imperative-verb lint for English; Georgian extension is a lexicon append.
- **[viewer/components/LanguageSwitcher.tsx](../../../viewer/components/LanguageSwitcher.tsx)** — Already authored correctly against `useLocale()` + `useRouter()`; works as-is once next-intl is installed.
- **`scripts/verify_phase5.py`** style — Model for `scripts/verify_phase6.py`: capability buckets, `--mode code-complete`, exit code 0 on all PASS.
- **`scripts/migrations/008_phase3_tables_and_rls.sql`** RLS pattern — service-role-only-write + family-read policies that migration 012 must preserve.

### Established Patterns
- **Per-table RLS on every base table** — Migration 008 set this for 10 base tables. Migration 012 changes column TYPE, not policies; policies survive but plan-phase must include a `\d table_name` policy-block check to prove preservation.
- **Migrations are atomic per file, numbered sequentially** — 001..011 with no re-numbering. 012 is the next slot; no other migrations are in flight per `ls scripts/migrations/`.
- **Verifier pattern** — Each phase has a `scripts/verify_phase{N}.py`. Phase 0/1/2/2.5/3/4/5 = 78 cumulative checks; Phase 6 adds 11 → 89.
- **Single-language outreach per contact** — `contacts.outreach_language` + `outreach_log.language` allow per-recipient English/French/Georgian. This existing structure is NOT replaced; bilingual JSONB is for family-internal artifacts only.
- **Auto-redirect on bare path** — next-intl middleware default 308-redirects `/dashboard` → `/en/dashboard`; matches the desired "default-en" behavior in SPEC AC.

### Integration Points
- **Migration 012 ↔ existing JSONB columns** — `briefs.sections` is already JSONB; migration 012 changes the *shape* of the values inside (each section body becomes `{en, ka}`). This is a data migration on top of a TYPE-already-JSONB column — different from the TEXT→JSONB conversions for the other 5 columns.
- **Communicator → DB write path** — Communicator's draft writes flow through `briefs` and (post-Phase-5) `aleksandra_timeline` + `hypotheses` + `therapies`. Bilingual emission per D-02 must land at this boundary; the DB layer is dumb.
- **n8n delivery ↔ JSONB read** — Workflows currently extract a single string field. Plan-phase changes the JSONB extraction expression: Telegram nodes read `field.ka`, Gmail nodes read `field.en`. Falls back to `field.en` if `.ka` is missing.
- **Viewer ↔ Supabase JS client** — `displayField(field, locale)` helper hides the JSONB shape from page components. New write paths (api/manager/apply/route.ts) accept the same `{en, ka}` shape when inserting timeline / therapy rows by the manager.

</code_context>

<specifics>
## Specific Ideas

- **Family-language ergonomics:** `/ka/*` is the family's natural reading state for the Aleksandra-facing pages; English is the clinician-facing fallback. The default URL (no prefix) 308-redirects to `/en/*` because Boston-area English browsers default to `accept-language: en-*`. Manual override via LanguageSwitcher persists via URL only.
- **PHI redaction order for Georgian** — Run redactor on the structured `{en, ka}` output *before* persistence and *before* delivery; do not run it on Telegram-side strings because by then the content is committed.
- **Translation provenance** — Each bilingual row carries provenance in adjacent metadata columns where they exist (e.g., `runs.id` for Communicator-produced rows). Plan-phase confirms whether an explicit `translation_source` field is needed; SPEC says no, so default to no.
- **Migration backup naming** — `scripts/migrations/012_rollback/{aleksandra_timeline,hypotheses,therapies,briefs}.pre012.dump` — one file per table for selective restore.

</specifics>

<deferred>
## Deferred Ideas

These came up during analysis and explicitly belong to future phases:

- **French (`fr`) UI translation** — outreach layer keeps fr; viewer ships en/ka only. Future Phase: extend `viewer/messages/` with `fr.json` if French clinician engagement grows.
- **AI re-translation of the 200 entities / 307 facts / 47 episodes / 10 hypotheses / 12 therapies** — migration 012 mirrors `en` to `ka`; a separate maintenance phase runs a Claude Sonnet bilingual backfill job at ~$3 estimated cost.
- **Cookie/localStorage language persistence** — URL is source of truth in Phase 6. If family asks for "remember my language across new tabs," that's a UX polish in a future phase.
- **RTL support / locale-aware date and number formatting beyond next-intl defaults** — neither English nor Georgian is RTL; basic next-intl handling is sufficient. Arabic (per v2 ACI-04 timezone-stamp idea) would re-open this.
- **Full-text search on bilingual title/description columns** — would require GIN indexes; not in Phase 6. Add when a search UI is actually shipped.
- **Tone post-processor (`taxonomy/tone.yaml`) Georgian extension** — Phase 6 extends only the imperative-verb lint (CGM-04); the broader CGM-06 tone post-processor stays English-only with a documented carve-out. Georgian tone tuning is a separate language-engineering phase.
- **`outreach_drafter` bilingual emission** — clinician outreach is single-recipient single-language; Phase 6 leaves it on the existing `outreach_language` rail. If a family-readable cc'd version is ever desired, that's its own phase.

### Reviewed Todos (not folded)

None — no GSD todos matched Phase 6 scope.

</deferred>

---

*Phase: 6-bilingual-system-i18n*
*Context gathered: 2026-05-20*
