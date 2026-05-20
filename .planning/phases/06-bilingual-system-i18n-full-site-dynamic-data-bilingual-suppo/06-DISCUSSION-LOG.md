# Phase 6: Bilingual System (i18n) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in [06-CONTEXT.md](./06-CONTEXT.md) — this log preserves the alternatives considered.

**Date:** 2026-05-20
**Phase:** 6-bilingual-system-i18n
**Areas discussed:** next-intl + Next.js 16 compat, Communicator bilingual emission strategy, JSONB backend read pattern, Migration 012 GIN index policy, Imperative-verb lint extension for Georgian, Phase 6 verifier coverage map
**Mode:** --auto (Auto Mode session-wide — recommended defaults selected without interactive AskUserQuestion)

---

## D-01 · next-intl + Next.js 16 compatibility

| Option | Description | Selected |
|---|---|---|
| `next-intl@4` | Latest v4.x; prepared explicitly for Next.js 15+/16 features (PPR, dynamicIO, rootParams); active Next.js 16 boilerplate exists at `amuradesign/next.js-16-next-intl-boilerplate`; uses `getRequestConfig({requestLocale})` API. | ✓ |
| Downgrade viewer to Next.js 15 | Avoids the "is next-intl Next.js 16 ready?" question entirely. | |
| `paraglide-js` | Alternative i18n library; smaller ecosystem; would require re-authoring scaffolding. | |
| Custom shim | Hand-rolled locale routing + translation; brittle; reinvents next-intl. | |

**Auto-selected:** next-intl@4 (recommended default — confirmed compatible via context7 query against the official Next.js 16 + next-intl boilerplate).
**Notes:** Existing [viewer/i18n.ts](../../../viewer/i18n.ts) uses outdated v3 API (`{locale}`); migrate to `{requestLocale}` per the next-intl 3.22 → 4 migration guide.

---

## D-02 · Bilingual emission strategy in Communicator

| Option | Description | Selected |
|---|---|---|
| Single structured-output call | Anthropic tool_use schema returns `{en: "...", ka: "..."}` in one shot; one prompt, one round-trip; consistent terminology. | ✓ |
| English-first + follow-up translation | Two calls per draft; risks translation drift; extra latency and cost. | |

**Auto-selected:** Single structured-output call.
**Notes:** Per-tier policy locked in CONTEXT.md — Communicator weekly_brief + Phase 5 composer emit bilingual; CrewAI internal agents stay English-only; outreach_drafter respects `contacts.outreach_language` per recipient (not changed by Phase 6).

---

## D-03 · JSONB backend read pattern

| Option | Description | Selected |
|---|---|---|
| Whole-JSONB read; viewer extracts locale | Backend returns `{en, ka}`; `displayField(field, locale)` helper picks the right one. Same backend serves both locales. | ✓ |
| `select=title->>en` server-side projection | Backend per-locale projection; smaller payload; multiplies code paths. | |

**Auto-selected:** Whole-JSONB read.
**Notes:** Single-patient low-traffic app — payload size is irrelevant; simplicity wins. Helper signature documented in CONTEXT.md (D-03) including a legacy-string-tolerance branch for the brief gap between viewer deploy and migration 012 application.

---

## D-04 · Migration 012 GIN index policy

| Option | Description | Selected |
|---|---|---|
| No GIN indexes in 012 | Migration only converts TYPE; existing B-tree / event_date indexes survive because they index different columns. Add GIN only if/when a feature needs full-text JSONB search. | ✓ |
| GIN on `aleksandra_timeline.title` + `hypotheses.title` | Pre-emptive performance optimization. | |
| GIN on all 6 converted columns | Defensive. | |

**Auto-selected:** No GIN indexes.
**Notes:** Plan-phase research must grep `ilike` / `to_tsvector` / `fts` patterns on the 4 tables; if hits exist, revisit decision. Current intuition: no caller does text search on these columns.

---

## D-05 · Imperative-verb lint extension for Georgian

| Option | Description | Selected |
|---|---|---|
| Minimal literal-string lexicon (6 entries) | Banned-phrase table maps 6 English imperatives to their Georgian polite-imperative forms; literal match in `banned_phrases.py`. Shako sanity-checks list in execute-phase. | ✓ |
| Morphological regex over verb stems | Catches declined forms automatically; higher implementation cost; needs Georgian NLP lib. | |
| Skip Georgian extension entirely | Imperative-verb lint runs on English only; Georgian content not gated. | |

**Auto-selected:** Minimal literal-string lexicon.
**Notes:** Initial 6-entry table drafted in CONTEXT.md D-05. Shako review required before lint goes live during execute-phase. If false-negative rate is high in early production digests, plan a follow-up to upgrade to regex matching.

---

## D-06 · Phase 6 verifier coverage map

| Option | Description | Selected |
|---|---|---|
| 5 capability buckets mirroring Phase 5 verifier style | A. Frontend / B. Database / C. Agent output / D. Delivery routing / E. Regression — one check per I18N-* requirement plus a regression bucket spawning verify_phase4 + verify_phase5. | ✓ |
| Flat list of 11 independent checks | One I18N-* per check; no buckets; simpler to read. | |

**Auto-selected:** 5 capability buckets.
**Notes:** Coverage map in CONTEXT.md D-06. Target = 11/11 PASS; cumulative project verifier total after Phase 6 ships = 89.

---

## Claude's Discretion

Per Auto Mode, Claude has latitude on:
- Exact regex shape of the Georgian imperative-verb lint (literal vs morphological) — plan-phase decides
- Whether `viewer/i18n.ts` is renamed to `viewer/i18n/request.ts` or kept flat — plan-phase decides
- Whether LanguageSwitcher gets translated labels (`EN | GE` vs `English | ქართული`) — UI polish detail
- `scripts/migrations/012_rollback/` layout (one dump per table vs single multi-table dump) — plan-phase picks cheapest

## Deferred Ideas

(See CONTEXT.md `<deferred>` section for full list)

- French (`fr`) UI translation — future phase
- AI re-translation of historical rows — separate maintenance phase
- Cookie/localStorage language persistence — UX polish phase
- RTL / locale-aware formatting beyond next-intl defaults — only relevant if Arabic added
- Full-text search on bilingual columns — needs UI feature first
- Tone post-processor (CGM-06) Georgian extension — separate language-engineering phase
- `outreach_drafter` bilingual emission — outreach is single-recipient single-language by design
