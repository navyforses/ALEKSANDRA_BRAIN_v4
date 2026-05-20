---
phase: 06-bilingual-system-i18n
plan: 01
subsystem: ui
tags: [next-intl, next.js-16, i18n, app-router, proxy-convention]

# Dependency graph
requires:
  - phase: 06-context
    provides: D-01 locked decision (next-intl@4 + locale-prefix routing); D-04 (no GIN); RESEARCH Pattern 1 file layout
provides:
  - next-intl 4.12.0 installed and verified on Next.js 16.2.6 + React 19.2.4
  - viewer/i18n/ module surface (routing.ts / request.ts / navigation.ts) per next-intl 4 API
  - viewer/proxy.ts mounted with createMiddleware(routing) — Next.js 16 file convention adopted
  - viewer/messages/{en,ka}.json relocated from repo root (canonical next-intl path)
  - createNextIntlPlugin wired in viewer/next.config.ts so message dictionaries resolve at build/render time
affects: [06-02 layout-segmentation, 06-03 messages-expansion, 06-04 LanguageSwitcher-mount, 06-05 displayField, all Wave-1 frontend plans]

# Tech tracking
tech-stack:
  added:
    - next-intl@4.12.0 (i18n for Next.js 16 App Router; recommended in Next.js's own i18n guide)
  patterns:
    - "Three-file next-intl module: routing.ts (defineRouting) + request.ts (getRequestConfig requestLocale) + navigation.ts (createNavigation)"
    - "Next.js 16 proxy.ts file convention (replaces middleware.ts) with createMiddleware(routing) import"
    - "Locale-prefix routing (D-01): defaultLocale 'en', supported ['en','ka']; URL is source of truth"
    - "Proxy matcher excludes api / audit / brain / _next / _vercel / static files (per 06-SPEC.md out-of-scope clause)"

key-files:
  created:
    - viewer/i18n/routing.ts
    - viewer/i18n/request.ts
    - viewer/i18n/navigation.ts
    - viewer/proxy.ts
    - viewer/messages/en.json
    - viewer/messages/ka.json
    - .planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-01-SUMMARY.md
  modified:
    - viewer/package.json
    - viewer/package-lock.json
    - viewer/next.config.ts
  deleted:
    - viewer/i18n.ts (legacy ({locale}) shape; superseded by viewer/i18n/request.ts)
    - viewer/middleware.ts (Next.js 16 file convention renamed it to proxy.ts)
    - en.json (root; moved to viewer/messages/en.json)
    - ka.json (root; moved to viewer/messages/ka.json)

key-decisions:
  - "Used the recommended Next.js 16 file name proxy.ts (NOT middleware.ts) per 06-RESEARCH.md Pitfall 1 — the next-intl/middleware library import path is unchanged but the file convention is new."
  - "Used `export default createMiddleware(routing)` so the function symbol is anonymous — the codemod's `middleware → proxy` rename is moot for default-anonymous exports. Skipped invoking the codemod npx package (avoids unverified-package install per the no-package-substitution rule)."
  - "Wrapped NextConfig with withNextIntl(nextConfig) using double-quoted string literal createNextIntlPlugin(\"./i18n/request.ts\") — TypeScript-style consistent with the existing single-import file."
  - "Did NOT create an empty smoke-only commit for Task 5 (verification only, no source changes); folded the build-pass evidence into this summary instead per GSD-executor 'do not create empty commits' rule."

patterns-established:
  - "i18n module split: routing/request/navigation lives under viewer/i18n/ — single source of truth for locale list"
  - "Proxy convention (Next.js 16) — every future Next.js middleware in this project goes in viewer/proxy.ts"
  - "Messages relocated under viewer/messages/ — future locale additions (e.g. fr.json post-v2) drop in alongside"

requirements-completed: [I18N-01]

# Metrics
duration: 7m 26s
completed: 2026-05-20
---

# Phase 6 Plan 01: i18n Foundation Summary

**next-intl@4.12.0 installed, viewer/proxy.ts (Next.js 16 file convention) wired with createMiddleware(routing), three-file i18n module surface authored, and root-level en/ka dictionaries relocated under viewer/messages/ — Wave-0 foundation for every other Phase 6 frontend plan**

## Performance

- **Duration:** 7m 26s
- **Started:** 2026-05-20T23:35:12Z
- **Completed:** 2026-05-20T23:42:38Z
- **Tasks:** 5 (4 with source changes + 1 build-verification-only)
- **Files modified/created:** 9 (3 new i18n module files + 1 proxy.ts + 2 relocated message files + 3 modified: package.json, package-lock.json, next.config.ts)
- **Files deleted:** 4 (legacy i18n.ts, legacy middleware.ts, root en.json, root ka.json)

## Accomplishments

- next-intl@4.12.0 installed in viewer/ with zero ERESOLVE conflicts against next@16.2.6 + react@19.2.4
- Three-file i18n module surface (viewer/i18n/{routing,request,navigation}.ts) authored exactly per 06-RESEARCH.md Pattern 1 — uses next-intl 4's `getRequestConfig({requestLocale})` API (NOT the legacy v3 `({locale})` shape the seed file had)
- viewer/proxy.ts created with `createMiddleware(routing)` per Next.js 16 file convention (replaces middleware.ts); matcher correctly excludes api / audit / brain / _next / _vercel / static files
- viewer/messages/en.json and viewer/messages/ka.json now exist at the canonical next-intl path; root copies deleted
- viewer/next.config.ts wraps export with `withNextIntl(nextConfig)` using `createNextIntlPlugin('./i18n/request.ts')` — without this, message lookups would silently 404 at runtime (RESEARCH.md Pitfall 1)
- `npm run build` exits 0 in 34.1s; build output shows `ƒ Proxy (Middleware)` confirming Next.js 16 detected proxy.ts; zero deprecation warnings; all 7 family-facing routes still build (top-level, [locale] folder lands in 06-02/06-03a)

## Task Commits

Each task was committed atomically:

1. **Task 1: Install next-intl@^4 + verify peer-deps** — `10fbdee` (feat: install next-intl@4.12.0 in viewer; refresh package-lock.json)
2. **Task 2: Author 3-file i18n module surface; delete legacy i18n.ts** — `2b0124a` (feat: viewer/i18n/{routing,request,navigation}.ts; tsc noEmit passes)
3. **Task 3: Rename middleware.ts → proxy.ts (Next.js 16 convention)** — `5a073e7` (feat: viewer/proxy.ts with createMiddleware(routing), audit/brain matcher exclusions)
4. **Task 4: Relocate messages + wire createNextIntlPlugin** — `a945f55` (feat: viewer/messages/{en,ka}.json + createNextIntlPlugin('./i18n/request.ts') in next.config.ts)
5. **Task 5: Smoke-build verification** — no commit (verification-only task, no source changes; build-pass evidence folded into this SUMMARY)

**Plan metadata commit:** to be created next (docs: 06-01 SUMMARY + STATE/ROADMAP updates).

## Files Created/Modified

**Created:**
- `viewer/i18n/routing.ts` — `defineRouting({locales: ['en', 'ka'], defaultLocale: 'en'})`
- `viewer/i18n/request.ts` — `getRequestConfig(async ({requestLocale}) => {...})` with hasLocale guard + dynamic messages/${locale}.json import
- `viewer/i18n/navigation.ts` — `createNavigation(routing)` exporting `{Link, redirect, usePathname, useRouter, getPathname}`
- `viewer/proxy.ts` — Next.js 16 file convention; `createMiddleware(routing)` + matcher excluding api/audit/brain/_next/_vercel/static
- `viewer/messages/en.json` — English static-string dictionary (Common + Navigation, 7 keys; expansion lands in 06-03)
- `viewer/messages/ka.json` — Georgian static-string dictionary (Common + Navigation, 7 keys; expansion lands in 06-03)

**Modified:**
- `viewer/package.json` — added `"next-intl": "^4.0.0"` to dependencies (preserves existing dep order)
- `viewer/package-lock.json` — refreshed via `npm install` (19 new packages including next-intl + its transitive deps)
- `viewer/next.config.ts` — imports `createNextIntlPlugin from "next-intl/plugin"`, builds `withNextIntl` with `'./i18n/request.ts'`, wraps NextConfig export

**Deleted:**
- `viewer/i18n.ts` — legacy seed using outdated next-intl v3 `({locale})` API
- `viewer/middleware.ts` — legacy seed; Next.js 16 file convention is `proxy.ts`
- `en.json` (repo root) — moved to `viewer/messages/en.json`
- `ka.json` (repo root) — moved to `viewer/messages/ka.json`

## Decisions Made

1. **Manual rename instead of `npx @next/codemod@canary middleware-to-proxy .`** — The plan offered both paths. Manual rename was chosen because (a) the seed file was untracked so the codemod would have rejected it as not-in-git, (b) `export default createMiddleware(routing)` makes the function symbol anonymous so the codemod's function-rename step is moot, and (c) the no-package-substitution / no-`npx --yes` rule from the executor protocol discourages auto-pulling a canary npm package when an equivalent two-file manual edit will do.
2. **Wrap NextConfig with `withNextIntl(nextConfig)` using a separate `withNextIntl` const** — Matches the canonical next-intl 4 docs example. Preserves any future config keys cleanly without needing to refactor.
3. **Skipped a marker commit for Task 5** — Task 5 is verification-only ("no source files modified — build verification only" per the plan task header). GSD-executor rule says "if there are no changes to commit … do not create an empty commit". The 34.1s clean build is documented in this SUMMARY instead.

## Deviations from Plan

**None - plan executed exactly as written.**

The plan offered two paths in Task 3 (codemod vs. manual `git mv`); I chose manual rename (which is a sanctioned plan alternative, not a deviation). Every task's acceptance grep / file-existence / exit-code check passed on the first attempt. No Rule 1/2/3 auto-fixes were needed.

The seed files (en.json, ka.json, viewer/middleware.ts, viewer/i18n.ts) were all untracked in git, so they were moved/deleted with plain shell `mv`/`rm` rather than `git mv`/`git rm`. This matches the executor's per-task commit protocol of staging new locations individually with `git add` rather than relying on rename-detection on untracked paths.

## Issues Encountered

**Pre-commit hook auto-fixed end-of-file on freshly-relocated JSON files (Task 4)** — On the first attempt to commit Task 4, the `fix end of files` pre-commit hook added a trailing newline to viewer/messages/en.json and ka.json (the seed files had no trailing newline). The hook left the working tree dirty and the commit was rejected. Per the destructive-git protocol, I did **not** `--amend` — I re-staged the auto-fixed files and created a fresh commit. The resulting commit `a945f55` contains both the file moves and the hook's whitespace fix as one atomic change. No data was lost; the JSON keys are byte-for-byte identical to the seed.

## User Setup Required

None - no external service configuration required. The viewer dev server can be started locally with `cd viewer && npm run dev` and will serve `/dashboard` etc. with the next-intl proxy active. Once plan 06-03a introduces `viewer/app/[locale]/`, the proxy's 308-redirects (`/dashboard` → `/en/dashboard`) will activate; until then, the existing top-level routes pass through unchanged.

## Next Phase Readiness

**Ready for Wave-1 plans (06-02 through 06-04):**
- next-intl@4 is installed and the build is green
- The locked `routing` object is available at `@/i18n/routing` for all subsequent layout/page imports
- The locked `Link` / `redirect` / `usePathname` / `useRouter` are available at `@/i18n/navigation` for the LanguageSwitcher polish (06-04) and any locale-aware in-app links
- `viewer/messages/{en,ka}.json` is in place at the canonical path so plan 06-03 can expand the key set without touching paths

**No blockers.** No concerns. Production Supabase migration 012 (Wave-2, plan 06-08) still requires Shako-applied psql per CLAUDE.md's Phase 6 readiness note — that is unchanged by this plan.

## Self-Check

All claimed artifacts and commits verified post-write:

- `viewer/package.json` declares `"next-intl": "^4.0.0"` (grep verified)
- `viewer/package-lock.json` declares `next-intl@4.12.0` (npm ls verified)
- `viewer/i18n/routing.ts`, `viewer/i18n/request.ts`, `viewer/i18n/navigation.ts` all exist (test -f verified)
- `viewer/proxy.ts` exists with `createMiddleware(routing)` and `audit|brain` in matcher (grep verified)
- `viewer/middleware.ts` does not exist (test ! -f verified)
- `viewer/messages/en.json` and `viewer/messages/ka.json` exist (test -f verified); root `en.json`/`ka.json` deleted (test ! -f verified)
- `viewer/next.config.ts` contains both `createNextIntlPlugin` and `withNextIntl(` (grep verified)
- `cd viewer && npm run build` exits 0 in 34.1s with no `middleware is deprecated` and no `Cannot find module` strings (build log verified)
- All four task commits present in git log (10fbdee, 2b0124a, 5a073e7, a945f55 — git log verified)

## Self-Check: PASSED

---
*Phase: 06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo*
*Completed: 2026-05-20*
