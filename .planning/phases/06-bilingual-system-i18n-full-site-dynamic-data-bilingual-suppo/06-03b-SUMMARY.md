---
phase: 06-bilingual-system-i18n
plan: 03b
subsystem: ui
tags: [next-intl, next.js, i18n, app-router, async-params, layout, react]

requires:
  - phase: 06-01
    provides: routing.ts + request.ts + navigation.ts + proxy.ts + messages/{en,ka}.json
  - phase: 06-03a
    provides: viewer/app/[locale]/* directory topology (7 family routes + index page moved under [locale])
  - phase: 06-04
    provides: viewer/components/LanguageSwitcher.tsx using createNavigation-typed router
provides:
  - viewer/app/[locale]/layout.tsx — locale-scoped layout with setRequestLocale + NextIntlClientProvider + hasLocale validation + generateStaticParams
  - 9 family-facing page.tsx files with Next.js 16 async-params signature (params: Promise<{locale: 'en'|'ka'}>) + setRequestLocale(locale) call
  - Sibling root layouts under viewer/app/audit/ and viewer/app/brain/ (Rule 3 deviation — required for valid HTML once root layout was reduced to children pass-through)
affects: 06-05b (consumes locale-scoped layout for t() refs), 06-08 (consumes async-params signature for JSONB read), 06-13 (verifier I18N-02 GREEN)

tech-stack:
  added: []
  patterns:
    - "Locale-owned <html lang={locale}> shell pattern — RESEARCH.md Pattern 2"
    - "Children pass-through root layout + multiple sibling root layouts for non-locale subtrees (api excluded, audit + brain each have own root layout)"
    - "setRequestLocale(locale) called from BOTH layout and every page — layout for the locale subtree boundary, page for per-page static-rendering opt-in"
    - "NextIntlClientProvider wraps EVERYTHING that uses next-intl client hooks — including LanguageSwitcher in the header, not just main+aside"

key-files:
  created:
    - viewer/app/[locale]/layout.tsx
    - viewer/app/audit/layout.tsx
    - viewer/app/brain/layout.tsx
  modified:
    - viewer/app/layout.tsx
    - viewer/app/[locale]/page.tsx
    - viewer/app/[locale]/dashboard/page.tsx
    - viewer/app/[locale]/timeline/page.tsx
    - viewer/app/[locale]/papers/page.tsx
    - viewer/app/[locale]/therapies/page.tsx
    - viewer/app/[locale]/hypotheses/page.tsx
    - viewer/app/[locale]/hypotheses/[id]/page.tsx
    - viewer/app/[locale]/today/page.tsx
    - viewer/app/[locale]/knowledge/page.tsx

key-decisions:
  - "Locked decision from PLAN: locale-owned <html lang={locale}> in [locale]/layout.tsx; root layout returns just {children} per RESEARCH.md Pattern 2 — accessibility/SEO correctness over the simpler-but-static fallback."
  - "NextIntlClientProvider placement: ABOVE the <header> so LanguageSwitcher (client component using useLocale()) is inside the provider's React context. Static prerender of /en/knowledge + /en/today fails without this — the useLocale hook throws on null context."
  - "Sibling root layouts created at viewer/app/audit/layout.tsx and viewer/app/brain/layout.tsx (Rule 3 deviation, files outside PLAN's files_modified). Necessary because the children-pass-through root layout produces invalid HTML for any subtree not under [locale]/, and audit + brain are explicitly excluded from the next-intl proxy matcher."
  - "All 9 family-facing pages call setRequestLocale(locale) immediately after awaiting params (RESEARCH.md Pitfall 4 prevention) — enables static rendering opt-in per page, not only at the layout boundary."
  - "Nested dynamic route [locale]/hypotheses/[id]/page.tsx widens params type to Promise<{locale: 'en'|'ka'; id: string}> per PLAN Task 2(b)."

patterns-established:
  - "Locale-scoped layout pattern (Pattern 2): [locale]/layout.tsx owns <html lang={locale}> + <body> + provider; root layout.tsx is a pass-through. Non-locale subtrees (audit, brain) each become their own root layout."
  - "Async-params + setRequestLocale pair: every page under [locale]/ takes `params: Promise<{locale: 'en'|'ka'}>` and immediately awaits + setRequestLocale(locale). Pattern repeats verbatim across 9 pages — future i18n pages copy this preamble."

requirements-completed:
  - I18N-02

duration: 25min
completed: 2026-05-21
---

# Phase 6 Plan 06-03b: Locale-scoped layout + async-params plumbing Summary

**viewer/app/[locale]/layout.tsx with setRequestLocale + NextIntlClientProvider + LanguageSwitcher chrome; 9 family pages take Next.js 16 async-params and call setRequestLocale; root layout reduced to children pass-through; build green at 21 static pages.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-21T02:15Z
- **Completed:** 2026-05-21T02:40Z
- **Tasks:** 2 (per-PLAN structure) → 3 commits with deviations folded into Task 2 commit
- **Files modified:** 10 (+ 2 new sibling root layouts as Rule 3 deviation = 12 changed)

## Accomplishments

- **Locale-scoped layout authored.** `viewer/app/[locale]/layout.tsx` owns the `<html lang={locale}>` + `<body>` document shell, calls `setRequestLocale(locale)` after `hasLocale(routing.locales, locale)` allow-list validation (T-06-LOCALE-INJECTION mitigated), exports `generateStaticParams()` for build-time static rendering of `/en` and `/ka` index pages, and mounts the `LanguageSwitcher` inside `NextIntlClientProvider` in the header.
- **Root layout reduced.** `viewer/app/layout.tsx` no longer renders `<html>` or `<body>`; it is now a `return children` pass-through plus metadata export. Locale-owned shell pattern locked.
- **9 family-facing pages now async-params-aware.** Every `page.tsx` under `viewer/app/[locale]/` accepts `params: Promise<{locale: 'en' | 'ka'}>`, awaits, and calls `setRequestLocale(locale)` (RESEARCH.md Pitfall 2 + Pitfall 4 prevention). Nested `[id]/page.tsx` widens to `Promise<{locale; id: string}>`.
- **Build green: `cd viewer && npm run build` exits 0; 21 static pages generated.** Routes manifest shows 8 dynamic entries under `/[locale]/*` (acceptance floor ≥7); `/en` and `/ka` index pages prerendered as SSG; `/en/knowledge`, `/ka/knowledge`, `/en/today`, `/ka/today` prerendered as SSG; force-dynamic routes (dashboard/timeline/papers/therapies/hypotheses) addressable via the dynamic [locale] segment.
- **14 URLs addressable.** `/en/<route>` + `/ka/<route>` for the 7 family routes + `/en` + `/ka` index = 16 distinct URLs reachable.
- **TypeScript clean.** `cd viewer && npx tsc --noEmit -p tsconfig.json` exits 0.

## Task Commits

1. **Task 1: Author [locale]/layout.tsx + refactor root layout** — `c49199e` (feat)
2. **Task 2: Async-params + setRequestLocale on 9 pages + Rule 1 layout fix + Rule 3 sibling root layouts** — `56eeaf8` (feat)

**Plan metadata:** _added by final commit after SUMMARY/STATE/ROADMAP write_

## Files Created/Modified

- `viewer/app/[locale]/layout.tsx` — NEW. Locale-scoped layout: setRequestLocale + NextIntlClientProvider + hasLocale + notFound + generateStaticParams + html/body shell + TopNav + LanguageSwitcher.
- `viewer/app/layout.tsx` — Reduced from 38-line full shell to 19-line metadata + children pass-through. No `<html>`/`<body>`, no `next-intl` import.
- `viewer/app/[locale]/page.tsx` — `Home` is now `async`, takes `params: Promise<{locale: 'en' | 'ka'}>`, calls `setRequestLocale(locale)`.
- `viewer/app/[locale]/dashboard/page.tsx` — async-params + setRequestLocale.
- `viewer/app/[locale]/timeline/page.tsx` — async-params + setRequestLocale.
- `viewer/app/[locale]/papers/page.tsx` — async-params + setRequestLocale.
- `viewer/app/[locale]/therapies/page.tsx` — async-params + setRequestLocale.
- `viewer/app/[locale]/hypotheses/page.tsx` — async-params + setRequestLocale.
- `viewer/app/[locale]/hypotheses/[id]/page.tsx` — params widened to `Promise<{locale; id: string}>` + setRequestLocale.
- `viewer/app/[locale]/today/page.tsx` — async-params + setRequestLocale (placeholder body unchanged).
- `viewer/app/[locale]/knowledge/page.tsx` — async-params + setRequestLocale (placeholder body unchanged).
- `viewer/app/audit/layout.tsx` — NEW. Sibling root layout (Rule 3 deviation) — own `<html lang="en">`/`<body>` shell + TopNav for the /audit subtree that lives outside the proxy matcher.
- `viewer/app/brain/layout.tsx` — NEW. Sibling root layout (Rule 3 deviation) — own `<html lang="en">`/`<body>` shell + TopNav for the /brain subtree that lives outside the proxy matcher.

## Decisions Made

- **Locale-owned `<html lang={locale}>` over root-owned `<html lang="en">` fallback.** PLAN locked decision: `[locale]/layout.tsx` owns the document shell because `lang={locale}` is correct for accessibility/SEO; root layout returns just `{children}`.
- **NextIntlClientProvider placement above the header, not below.** The PLAN's example snippet placed the provider AFTER the header. Followed canonical RESEARCH.md Pattern 2 placement (provider wraps everything including header) because `LanguageSwitcher` is a client component calling `useLocale()`; without the provider wrapping it, static prerender of any SSG page (`/en/knowledge`, `/ka/knowledge`, `/en/today`, `/ka/today`, `/en`, `/ka` index) crashes at `useLocale` → null context → throw Error.
- **Sibling root layouts for audit + brain.** Per Next.js 16 docs ("Any layout without a layout.js above it is a root layout. ... Omitting app/layout.js so layouts in subdirectories each become root layouts") — the children-pass-through root layout strips `<html>`/`<body>` from all subtrees; audit + brain need their own document shells. Authored minimal `<html lang="en">` + `<body>` + `TopNav` wrappers for both.
- **No `Link from '@/i18n/navigation'` migration for TopNav in this plan.** TopNav still uses `next/link` with bare paths (`/`, `/hypotheses`, etc.). Locale-aware Link conversion lands in 06-05b per PLAN explicit scope; this plan only mounts the switcher in the layout chrome.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] NextIntlClientProvider placement caused static prerender crash**

- **Found during:** Task 2 (`npm run build` smoke check after page edits)
- **Issue:** PLAN-suggested provider placement put `<NextIntlClientProvider>` AFTER `<header>` — but `LanguageSwitcher` (rendered inside `<header>`) is a `'use client'` component calling `useLocale()`. Static prerender of `/en/knowledge`, `/ka/knowledge`, `/en/today`, `/ka/today`, `/en`, `/ka` all crashed in `use-intl/react` at `useContext(IntlContext) → null → throw Error(undefined)`. Error reproducible with single line: `"Error occurred prerendering page '/en/knowledge'"` pointing at the minified `useLocale` hook in `.next/server/chunks/ssr/_0nh.cao._.js:3:3975`.
- **Fix:** Moved `<NextIntlClientProvider>` to wrap the entire body content including `<header>` (RESEARCH.md Pattern 2 canonical shape — provider is the outermost JSX child of `<body>`).
- **Files modified:** `viewer/app/[locale]/layout.tsx`
- **Verification:** `cd viewer && npm run build` went from "Export encountered an error on /[locale]/knowledge/page" → "✓ Generating static pages using 7 workers (21/21) in 509ms".
- **Committed in:** 56eeaf8 (folded into Task 2 commit).

**2. [Rule 3 - Blocking] Root layout as children-pass-through produces invalid HTML for audit/brain subtrees**

- **Found during:** Task 2 (`npm run build` succeeded but `head -c 500 .next/server/app/audit.html` revealed missing `<html>` and `<body>` — only a stray `<head>` survived; brain.html identically broken).
- **Issue:** Per Next.js 16 file conventions, a root layout MUST render `<html>` and `<body>` for any subtree it covers. By reducing `app/layout.tsx` to `return children`, the locale subtree gets its shell from `[locale]/layout.tsx`, but `/audit` and `/brain` (both excluded from the next-intl proxy matcher per `viewer/proxy.ts`) inherit a no-op root and end up with no document shell — invalid HTML in production.
- **Fix:** Added two new sibling root layouts: `viewer/app/audit/layout.tsx` and `viewer/app/brain/layout.tsx`. Each renders `<html lang="en">` + `<body>` + minimal `TopNav` chrome + `<main>` for their respective subtree. Per Next.js 16 docs ("Any layout without a layout.js above it is a root layout"), this is the canonical multi-root-layout pattern.
- **Files modified:** `viewer/app/audit/layout.tsx` (new), `viewer/app/brain/layout.tsx` (new).
- **Verification:** `grep -o "<html\|<body" viewer/.next/server/app/audit.html → 1×<html, 1×<body`; same for brain.html, en.html, ka.html.
- **Committed in:** 56eeaf8 (folded into Task 2 commit).

---

**Total deviations:** 2 auto-fixed (1 Rule 1 bug, 1 Rule 3 blocking).
**Impact on plan:** Both auto-fixes essential for build correctness and HTML validity. PLAN files_modified list expanded by 2 files (audit/layout.tsx, brain/layout.tsx) to keep non-locale subtrees rendering valid HTML — strictly additive, no behavior change to family routes. Locale subtree behavior matches PLAN locked decision exactly.

## Issues Encountered

- **Static prerender crash on placeholder pages (resolved):** `/en/knowledge` + `/en/today` + `/en` + `/ka` variants crashed during `next build` static page generation. Root cause traced via minified chunk inspection to `useLocale()` throwing on null `IntlContext`. Fix above (Rule 1 deviation). Build time: error path 13.4s → success path 13.9s total.
- **No live Supabase needed:** All page edits are pure-signature work; runtime data fetching (`getRows`, `getCount`) is unchanged. Build verified via Next.js's standalone static rendering — no DB queries fire at build time for these pages (they all have `export const dynamic = "force-dynamic"` except the placeholders).

## User Setup Required

None — no external service configuration required for this plan.

## Next Phase Readiness

- **I18N-02 verifier check should now flip GREEN.** The file-presence half flipped in 06-03a; this plan completes the layout/params half. `verify_phase6 --mode code-complete --gate I18N-02` should pass.
- **06-05b unblocked.** Pages now have the `setRequestLocale + locale` plumbing required to wire `getTranslations` / `useTranslations` calls.
- **06-08 unblocked.** Hypotheses + Timeline + Therapies + Briefs JSONB read via `displayField(field, locale)` (from 06-04) now has a typed `locale` value at the page boundary.
- **No blockers.** Next plan in Wave 1 is 06-05b (t() refs across pages + locale-aware TopNav).

---
*Phase: 06-bilingual-system-i18n*
*Plan: 06-03b*
*Completed: 2026-05-21*

## Self-Check: PASSED

- viewer/app/[locale]/layout.tsx — FOUND
- viewer/app/layout.tsx — FOUND
- viewer/app/audit/layout.tsx — FOUND
- viewer/app/brain/layout.tsx — FOUND
- commit c49199e (Task 1) — FOUND
- commit 56eeaf8 (Task 2 + deviations) — FOUND
