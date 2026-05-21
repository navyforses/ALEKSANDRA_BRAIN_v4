---
phase: 06-bilingual-system-i18n
plan: 05b
subsystem: viewer/app/[locale] + viewer/components/layout
tags: [i18n, next-intl-4, typed-link, server-components, getTranslations]
dependency_graph:
  requires:
    - 06-01 (next-intl@4 + proxy.ts + i18n module)
    - 06-03a (route topology under [locale]/)
    - 06-03b (locale layout + setRequestLocale on every page)
    - 06-05a (dictionaries en.json + ka.json, 143 leaves × 11 namespaces)
  provides:
    - "I18N-03 full GREEN — every visible static label in 7 family-facing routes goes through next-intl resolution"
    - "Locale-aware TopNav typed Link auto-prefixes /en/ or /ka/ across navigation"
    - "Consumer baseline for Wave 3a (06-08 displayField for JSONB columns)"
  affects:
    - viewer/app/[locale]/page.tsx
    - viewer/app/[locale]/dashboard/page.tsx
    - viewer/app/[locale]/timeline/page.tsx
    - viewer/app/[locale]/papers/page.tsx
    - viewer/app/[locale]/therapies/page.tsx
    - viewer/app/[locale]/hypotheses/page.tsx
    - viewer/app/[locale]/hypotheses/[id]/page.tsx
    - viewer/app/[locale]/today/page.tsx
    - viewer/app/[locale]/knowledge/page.tsx
    - viewer/components/layout/TopNav.tsx
tech-stack:
  added: []
  patterns:
    - "getTranslations(namespace) inside async Server Components (after setRequestLocale)"
    - "Typed Link from @/i18n/navigation for in-locale routes; plain <a> for /audit (outside [locale]/ tree)"
    - "Multi-namespace consumption pattern: single page binds 2-4 namespaces (e.g., t / tNav / tShared / tTherapies) to keep variable names short"
key-files:
  created: []
  modified:
    - viewer/app/[locale]/page.tsx
    - viewer/app/[locale]/dashboard/page.tsx
    - viewer/app/[locale]/timeline/page.tsx
    - viewer/app/[locale]/papers/page.tsx
    - viewer/app/[locale]/therapies/page.tsx
    - viewer/app/[locale]/hypotheses/page.tsx
    - viewer/app/[locale]/hypotheses/[id]/page.tsx
    - viewer/app/[locale]/today/page.tsx
    - viewer/app/[locale]/knowledge/page.tsx
    - viewer/components/layout/TopNav.tsx
decisions:
  - "Server Components only — every page (including TopNav) uses getTranslations (async) over useTranslations (hook). All nine pages were already async Server Components per 06-03b; TopNav converted to async to match."
  - "Multi-namespace bindings — when a page renders strings from multiple semantic domains, bind each domain to its own variable (t, tNav, tPapers, tShared, tTherapies). The hypotheses detail page binds the largest set (5) because it surfaces therapy + paper + hypothesis labels in one view."
  - "/audit uses a plain <a> tag — it lives outside the [locale]/ tree (proxy.ts matcher excludes it) and the typed Link would prepend /en/ or /ka/ and 404. Single intentional non-typed link in the nav."
  - "Hardcoded literal `ALEKSANDRA_BRAIN` stays in JSX as a proper noun (per 06-05a Mkhedruli coverage decision — 142/143 leaves are Mkhedruli; the brand name keeps Latin in both dicts). Not added to any namespace; rendered verbatim."
metrics:
  duration: 22m
  completed: 2026-05-21
  tasks: 3
  files_modified: 10
  commits: 3
---

# Phase 6 Plan 05b: Page t() refs + locale-aware TopNav Summary

One-liner: Wired 129 next-intl `t('Namespace.key')` calls across 9 [locale]/ pages and TopNav so every static UI label resolves from the 06-05a dictionaries, swapped `next/link` for the createNavigation-typed Link to auto-prefix locale on every nav item, and confirmed dictionary alignment via inline missing-key verifier (10 namespaces × 129 refs all resolve in en.json AND ka.json).

## What landed

### Task 1 — 9 [locale]/ pages

**Simple pages (5)** — straightforward header/body label swap:

- `viewer/app/[locale]/page.tsx` (Home) — 11 t() calls into `Home` namespace; typed Link replaces `next/link` for /dashboard + /hypotheses cards.
- `viewer/app/[locale]/dashboard/page.tsx` — 15 t() calls split across `Dashboard` (12) + `Navigation` (5) + `Shared` (2); inline top-of-page nav rewritten with typed Link so /en/dashboard's nav points to /en/papers (not /papers).
- `viewer/app/[locale]/knowledge/page.tsx` — 3 t() calls into `Knowledge`.
- `viewer/app/[locale]/today/page.tsx` — 3 t() calls into `Today`.
- `viewer/app/[locale]/papers/page.tsx` — 14 t() calls split across `Papers` (12) + `Shared` (2 — `na`, `sourcePending`).

**Data-driven pages (4)** — KPIs, status pills, action buttons; dynamic row text (paper.title, therapy.name, etc.) intentionally left as pass-through reads because the underlying columns are still TEXT in 8/9 production tables until 06-08 runs:

- `viewer/app/[locale]/timeline/page.tsx` — 8 t() calls into `Timeline` (title/subtitle/phaseLabel/shown/latest/events/locationPending/emptyList) + 1 into `Shared` for the date fallback.
- `viewer/app/[locale]/therapies/page.tsx` — 18 t() calls into `Therapies` + 6 into `Shared` (`yes`/`no`/`unknown`/`na`/`notListed`). The status-pill literal mapping (`aleksandra_status || t('statusNotConsidered')`) keeps enum keys ungated; only the display fallback flows through next-intl.
- `viewer/app/[locale]/hypotheses/page.tsx` — 18 t() calls into `Hypotheses` + 5 into `Navigation` + 1 into `Shared`. Typed Link replaces `next/link` for the inline page-top nav AND for the per-row detail link `/hypotheses/${hypothesis.id}` — so the locale prefix propagates through the dynamic [id] route.
- `viewer/app/[locale]/hypotheses/[id]/page.tsx` — 22 t() calls split across 5 namespaces: `Hypotheses` (16) + `Navigation` (2) + `Papers` (3) + `Therapies` (4 — Related therapies card) + `Shared` (4). Largest namespace set in the project; necessary because the detail page surfaces therapy + paper + hypothesis labels in one view.

### Task 2 — TopNav.tsx

- Replaced `import Link from 'next/link'` with `import { Link } from '@/i18n/navigation'`.
- Converted to `async function` Server Component (was sync) and called `await getTranslations('Navigation')`.
- All 5 family-facing tab labels (Today / Hypotheses / Therapies / Timeline / Audit) + the "Doctor Mode" badge now flow through the Navigation namespace.
- `/audit` is the single intentional non-typed link — uses plain `<a href="/audit">` because the route lives outside the `[locale]/` tree (per `proxy.ts` matcher exclusion). The typed Link would prepend `/en/` and 404.

### Task 3 — Verification gates

- **Inline missing-key verifier:** Custom Python pass walks every `*.tsx` under `viewer/`, builds a variable→namespace map from each `getTranslations('NS')` / `useTranslations('NS')` site, then for every `varName('key')` call composes `{namespace}.{key}` and looks it up in both `en.json` and `ka.json`. Result: **OK — 129 translation references across 10 namespaces all resolve in both dictionaries** (one namespace, `Common`, is reserved but unused at this plan boundary; 06-05a authored it for a future Cancel/Save dialog).
- **Build smoke:** `cd viewer && npm run build` exits 0 in 12.7s — 21 static pages generated, all 8 dynamic `/[locale]/*` routes preserved.
- **Phase 6 verifier:** `python -X utf8 -m scripts.verify_phase6 --mode code-complete` → **I18N-03 PASS** (`en_leaves=143 ka_leaves=143 diff_count=0`); 8/11 PASS overall (same as prior Wave-1 baseline — Plan 06-05b's job was to keep dictionary-alignment GREEN, not flip new gates, which are gated on Wave 3a/4 plans).

## Deviations from Plan

### Auto-fixed

**1. [Rule 1 - Bug] Used wrong namespace key `Hypotheses.aleksandraFor`**
- **Found during:** Task 3 inline missing-key verifier
- **Issue:** Initial hypotheses detail page rewrite used `t('aleksandraFor')` inside the Hypotheses namespace binding, but the dictionary key lives in `Therapies.aleksandraFor` (06-05a placed it there because the label semantically describes a therapy row). Verifier output: `MISSING en (1): ['Hypotheses.aleksandraFor']`.
- **Fix:** Added `const tTherapies = await getTranslations('Therapies')` to the detail page and rewrote the Related therapies row to use `tTherapies('aleksandraFor')`, `tTherapies('evidenceLabel')`, `tTherapies('evidenceUnknown')`, `tTherapies('typePending')`, `tTherapies('statusNotConsidered')`. Net effect: no key added to en.json/ka.json; the existing Therapies namespace now resolves cleanly from the detail page.
- **Files modified:** viewer/app/[locale]/hypotheses/[id]/page.tsx
- **Commit:** folded into 9cf0b6e (data-driven pages) — caught at verifier time, fixed inline before commit.

**2. [Rule 3 - Blocking] `/audit` typed Link would 404**
- **Found during:** Task 2 TopNav rewrite
- **Issue:** The plan's acceptance criterion `! grep -q "from 'next/link'"` could be satisfied by routing all 5 tabs through the typed Link, but `/audit` lives outside the `[locale]/` tree (per `proxy.ts` matcher exclusion). Routing it through the typed Link would prepend `/en/` or `/ka/` and produce `/en/audit` → 404.
- **Fix:** Used a plain `<a href="/audit">` element for the audit tab — satisfies both "no `next/link` import" (acceptance grep) AND correct routing (no 404). The 4 family-facing routes (/, /hypotheses, /therapies, /timeline) still use the typed Link.
- **Files modified:** viewer/components/layout/TopNav.tsx
- **Commit:** faa0ca0

**3. [Rule 2 - Critical] Acceptance-grep collision with comment text**
- **Found during:** Task 2 verifier
- **Issue:** A code comment in TopNav.tsx referenced the literal string `'next/link'` to explain WHY the file avoids that import. The plan's acceptance grep `! grep -q "from 'next/link'"` matched the comment text and failed the gate even though there was no actual import.
- **Fix:** Reworded the comment to say "framework Link import" instead of `'next/link'`. The grep is now satisfied.
- **Files modified:** viewer/components/layout/TopNav.tsx
- **Commit:** folded into faa0ca0.

## Scope notes

### Dynamic row content NOT touched

This plan intentionally leaves the following JSX expressions as direct reads of TEXT columns:

- `{event.title}`, `{event.description}` (timeline rows)
- `{paper.title}`, `{paper.ai_summary}` (paper rows)
- `{therapy.name}`, `{therapy.mechanism_of_action}`, `{therapy.evidence_summary}`, `{therapy.ai_assessment}`, `{therapy.aleksandra_notes}` (therapy rows)
- `{hypothesis.title}`, `{hypothesis.description}`, `{hypothesis.recommended_action}`, `{hypothesis.ai_reasoning}`, `{hypothesis.outcome}` (hypothesis rows)

These columns are now JSONB in production (Shako applied migration 012 on 2026-05-20), but the page render code still expects TEXT. Plan 06-08 (Wave 3a) owns the wrapper: every dynamic read becomes `displayField(value, locale)` so the JSONB-to-locale resolution happens at the rendering boundary. If 06-08 is skipped, these reads will render `[object Object]` against live production data — that's the next-action item, not a regression introduced here.

### `Common` namespace unused

`viewer/messages/en.json` exposes a `Common` namespace (Cancel / Loading / Save) authored by 06-05a as forward-looking scaffold for future dialog UI. No page in this plan touches it. The inline verifier confirms 10 namespaces are touched (Dashboard, Home, Hypotheses, Knowledge, Navigation, Papers, Shared, Therapies, Timeline, Today); `Common` and `Common.cancel/loading/save` are dormant. Not a deviation — expected per 06-05a's Rule 2 superset decision.

## Verification

- `cd viewer && npx tsc --noEmit -p tsconfig.json` → exits 0
- `cd viewer && npm run build` → exits 0; 21 static pages generated; all 8 `/[locale]/*` dynamic routes preserved
- Inline missing-key verifier → `OK: 129 translation references across 10 namespaces all resolve in both dictionaries`
- `grep -rn -E ">[A-Z][a-z][^<>{}\"']{3,}<" viewer/app/[locale]/ | grep -v '{' | head -20` → 0 hits
- `python -m scripts.verify_phase6 --mode code-complete` → I18N-03 PASS (en_leaves=143 ka_leaves=143 diff_count=0); 8/11 overall PASS

## Commits

| Hash | Description |
|------|-------------|
| ce3557f | feat(06-05b): wire t() calls in 5 simple [locale]/ pages |
| 9cf0b6e | feat(06-05b): wire t() calls in 4 data-driven [locale]/ pages |
| faa0ca0 | feat(06-05b): TopNav uses typed Link + getTranslations('Navigation') |

## Self-Check: PASSED

Verified:

- viewer/app/[locale]/page.tsx → exists, imports `getTranslations` from `next-intl/server` and `Link` from `@/i18n/navigation`
- viewer/app/[locale]/dashboard/page.tsx → exists, multi-namespace bind (Dashboard + Navigation + Shared)
- viewer/app/[locale]/timeline/page.tsx → exists, Timeline + Shared
- viewer/app/[locale]/papers/page.tsx → exists, Papers + Shared
- viewer/app/[locale]/therapies/page.tsx → exists, Therapies + Shared
- viewer/app/[locale]/hypotheses/page.tsx → exists, Hypotheses + Navigation + Shared, typed Link for per-row detail href
- viewer/app/[locale]/hypotheses/[id]/page.tsx → exists, Hypotheses + Navigation + Papers + Therapies + Shared (5 namespaces)
- viewer/app/[locale]/today/page.tsx → exists, Today
- viewer/app/[locale]/knowledge/page.tsx → exists, Knowledge
- viewer/components/layout/TopNav.tsx → exists, typed Link + getTranslations('Navigation'); plain `<a>` for /audit
- Commits ce3557f, 9cf0b6e, faa0ca0 all present in `git log --oneline -10`
