---
phase: 06-bilingual-system-i18n
plan: 04
subsystem: ui
tags: [next-intl, i18n, displayField, language-switcher, typed-navigation, jsonb-helper]

# Dependency graph
requires:
  - phase: 06-01
    provides: viewer/i18n/navigation.ts (createNavigation-typed Link/redirect/usePathname/useRouter)
  - phase: 06-02
    provides: scripts/verify_phase6.py::check_i18n_08 + check_i18n_04 (verifier targets)
provides:
  - viewer/lib/i18n.ts → BilingualField type + displayField(field, locale) helper (locked CONTEXT.md D-03 shape)
  - viewer/lib/__tests__/i18n.test.ts → 5-case node:test suite (pinned `npx tsx --test` runner)
  - viewer/components/LanguageSwitcher.tsx → typed @/i18n/navigation router + bilingual labels
affects:
  - 06-08 (Wave-2 viewer reads consume displayField on Timeline/Therapies/Hypotheses pages)
  - 06-09/06-10 (Wave-3 worker reads consume displayField when emitting bilingual rows back to viewer)
  - I18N-04 (LanguageSwitcher uses typed router; final mount in [locale]/layout.tsx happens in 06-03b)

# Tech tracking
tech-stack:
  added: []   # no new deps — node:test + tsx already available via npx
  patterns:
    - "Single-file pure helper for JSONB locale extraction (D-03): `if (field == null) return '';` → `typeof string` passthrough → `field[locale] ?? field.en ?? ''`"
    - "Pinned test runner: `npx tsx --test` (matches scripts/verify_phase6.py::check_i18n_08 production-mode subprocess invocation — eliminates dual-runner ambiguity)"
    - "Typed createNavigation router idiom: `router.replace(pathname, {locale: newLocale})` instead of manual `pathname.replace('/${locale}', '')` + `router.push(newPath)` (canonical next-intl 4 swap)"
    - "tsconfig exclude `__tests__/` from viewer/tsconfig.json bundler-mode compilation — node:test imports need explicit `.ts` extension; viewer build doesn't compile tests"

key-files:
  created:
    - viewer/lib/i18n.ts (10 lines — ≤15 anti-creep gate per D-03)
    - viewer/lib/__tests__/i18n.test.ts (31 lines, 5 test blocks)
    - viewer/components/LanguageSwitcher.tsx (was untracked at plan start — committed in Task 3 with typed-nav rewrite)
    - .planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-04-SUMMARY.md
  modified:
    - viewer/tsconfig.json (added `**/__tests__/**` to exclude — Rule 3 deviation, see below)
  deleted: []

key-decisions:
  - "displayField lives in viewer/lib/i18n.ts (NOT viewer/i18n/) — the helper is consumer-facing utility code, while viewer/i18n/{routing,request,navigation}.ts holds next-intl wiring. Distinct concerns; distinct directories."
  - "Helper is EXACTLY the 10-line shape locked in CONTEXT.md D-03 — no JSDoc, no extra exports, no logic creep. The 5-case behavior contract lives in the test file, not in code comments."
  - "Test runner pinned to `npx tsx --test` (NOT vitest, NOT jest) — RESEARCH.md Validation Architecture says viewer has no test framework, and `node:test` keeps Wave-0 dependency-free. The verifier check_i18n_08 production-mode path invokes this exact command via subprocess.run(['npx', 'tsx', '--test', ...]) — pinning eliminates dual-runner ambiguity (PLAN.md WARNING 4)."
  - "LanguageSwitcher rewrite uses `router.replace(pathname, {locale: newLocale})` — the canonical next-intl 4 idiom on the typed createNavigation router. Manual `pathname.replace('/${locale}', '')` + `router.push(newPath)` removed (the typed router strips/applies the locale prefix internally)."
  - "Bilingual button labels per CONTEXT.md Claude's Discretion: `English` / `ქართული` (Mkhedruli). aria-labels kept for screen-reader determinism (English: 'Switch to English'; Georgian: 'გადართვა ქართულზე')."
  - "viewer/tsconfig.json: added `**/__tests__/**` to exclude. Rationale: node:test ESM convention requires `.ts` extension in import (`from '../i18n.ts'`); viewer's bundler-mode tsconfig rejects this without `allowImportingTsExtensions`. Excluding __tests__ from viewer build compilation is the minimal surgical fix — tests run under tsx, not next build."

patterns-established:
  - "BilingualField shape (`string | {en?, ka?} | null | undefined`) is the canonical type for any column post-migration-012; both server-side row constructors and viewer reads should converge on this union."
  - "viewer test files live under `__tests__/` subdirectories adjacent to the code under test (e.g., viewer/lib/__tests__/, viewer/components/__tests__/ when those land); test files use the `.test.ts` suffix and are run via `npx tsx --test <path>`."

requirements-completed:
  - I18N-08   # displayField helper landed; verifier flips PASS
  # I18N-04 NOT marked complete here — verifier looks for the switcher import inside viewer/app/[locale]/layout.tsx,
  # which is created by 06-03b. 06-04 lands the switcher with the typed nav; 06-03b mounts it.

# Metrics
metrics:
  duration: ~15m
  completed: "2026-05-21"

---

# Phase 06 Plan 06-04: displayField helper + LanguageSwitcher typed-nav polish — Summary

**One-liner:** Land the locked CONTEXT.md-D-03 `displayField(field, locale)` JSONB read helper under viewer/lib/i18n.ts with a 5-case node:test suite, and switch viewer/components/LanguageSwitcher.tsx to the createNavigation-typed router (`router.replace(pathname, {locale})`) with bilingual `English`/`ქართული` button labels.

## What changed

### Task 1 — viewer/lib/i18n.ts (displayField helper)

- File created with EXACTLY the 10-line shape locked in CONTEXT.md §D-03.
- Pure function, zero imports — usable from both Server Components and Client Components.
- Behavior contract:
  1. `null | undefined` → `''`
  2. `typeof string` → passthrough (legacy TEXT row tolerance for pre-migration-012 window)
  3. `{en, ka}` object → `field[locale] ?? field.en ?? ''` (strict locale → English fallback)
- `cd viewer && npx tsc --noEmit` exits 0.
- Helper line count = 10 (≤15 anti-creep gate per acceptance criteria).
- Commit: `55eee7d`

### Task 2 — viewer/lib/__tests__/i18n.test.ts (5-case unit suite)

- 5 `test(...)` blocks covering: null/undef, string passthrough (both locales), object both-locales (en + ka), English fallback when locale missing, empty object.
- Runner: `node:test` + `node:assert/strict`, executed via `npx tsx --test` (matches the exact subprocess invocation in scripts/verify_phase6.py::check_i18n_08 production-mode path — see verify_phase6.py:676).
- Test output: `tests 5 / pass 5 / fail 0 / duration ~830ms` (Node v24.15.0, tsx 4.22.3).
- Verifier check_i18n_08 flipped from PENDING → PASS (`exports_displayField=True test_file=ok mode=code-complete`).
- Commit: `2301c0e`

### Task 3 — viewer/components/LanguageSwitcher.tsx (typed-nav polish)

- Import line switched: `from 'next/navigation'` → `from '@/i18n/navigation'`.
- `switchLocale` rewritten to the canonical next-intl 4 idiom:
  ```ts
  const switchLocale = (newLocale: 'en' | 'ka') => {
    router.replace(pathname, {locale: newLocale});
  };
  ```
- Manual `pathname.replace('/${locale}', '')` + `router.push(newPath)` removed entirely (typed router strips/applies the locale prefix automatically).
- Button labels: `EN`/`GE` → `English`/`ქართული` (Mkhedruli) per CONTEXT.md Claude's Discretion.
- `aria-label` set on each button for deterministic screen-reader intent (`"Switch to English"` / `"გადართვა ქართულზე"`).
- `'use client'` directive preserved as first line.
- Commit: `c2a49e3`

## Acceptance criteria

| Criterion | Status |
|---|---|
| viewer/lib/i18n.ts exists with `displayField(field, locale)` matching D-03 semantics exactly | ✅ |
| viewer/lib/i18n.ts contains `export type BilingualField` and `export function displayField` | ✅ |
| viewer/lib/i18n.ts ≤15 lines (anti-creep gate) | ✅ (10 lines) |
| viewer/lib/__tests__/i18n.test.ts exists with ≥5 test blocks (plan says 5) | ✅ (5 blocks) |
| All 5 tests pass under `npx tsx --test` | ✅ |
| LanguageSwitcher imports useRouter/usePathname from `@/i18n/navigation` (NOT `next/navigation`) | ✅ |
| LanguageSwitcher uses `router.replace(pathname, {locale: newLocale}` canonical idiom | ✅ |
| LanguageSwitcher contains Mkhedruli label `ქართული` | ✅ |
| `cd viewer && npx tsc --noEmit -p tsconfig.json` exits 0 | ✅ |
| `cd viewer && npm run build` exits 0 (no regression) | ✅ |
| Verifier `check_i18n_08` flips PASS | ✅ |

## Deviations from Plan

### Rule 3 — Blocking issue: tsc rejects `.ts` extension in test import

- **Found during:** Task 3 verification (`npx tsc --noEmit -p tsconfig.json`)
- **Issue:** The test file imports `from '../i18n.ts'` (per the explicit Task 2 template — required by `node:test` / `tsx --test` ESM conventions). viewer's tsconfig.json is in bundler-mode without `allowImportingTsExtensions`, so tsc raised TS5097 on the test file.
- **Fix:** Added `**/__tests__/**` to `viewer/tsconfig.json` `exclude` array. The test directory is run by tsx at runtime, not compiled by next build — excluding it from viewer's tsc pass is the minimal surgical change.
- **Alternatives considered:**
  - `allowImportingTsExtensions: true` globally — broader impact on Next.js build; rejected as architectural drift.
  - Drop the `.ts` extension in the test import — would break `node:test` / `tsx --test` ESM resolution; rejected.
- **Files modified:** viewer/tsconfig.json (1 line: `"exclude": ["node_modules"]` → `"exclude": ["node_modules", "**/__tests__/**"]`)
- **Commit:** Folded into Task 3's commit `c2a49e3`.
- **Pattern established:** Future viewer test files live under `__tests__/` subdirectories adjacent to code under test, run via `npx tsx --test`, and are excluded from viewer's bundler-mode tsc compilation.

No other deviations. The plan's Task 1 + Task 2 + Task 3 ran exactly as written.

## Verification evidence

### check_i18n_08 (PRIMARY GATE)
```
  8  I18N-08     PASS    viewer/lib/i18n.ts exports displayField with en-fallback
                          →  exports_displayField=True test_file=ok mode=code-complete
```

### check_i18n_04 (still PENDING — not this plan's gate)
```
  4  I18N-04     FAIL    LanguageSwitcher mounted in viewer/app/[locale]/layout.tsx
                          →  PENDING — implemented in Wave 1 / plan 06-03b (layout) + 06-04 (mount)
```
The switcher itself is now typed-nav-correct (06-04 done); the verifier looks for the import string inside `viewer/app/[locale]/layout.tsx`, which is **06-03b's** responsibility. STATE.md line 31 confirms 06-03b has not yet executed. When 06-03b lands the locale layout and imports LanguageSwitcher there, I18N-04 will flip PASS automatically.

### Build + test reproducibility

```bash
cd viewer && npx tsc --noEmit -p tsconfig.json   # exits 0
cd viewer && npx tsx --test lib/__tests__/i18n.test.ts   # tests 5 / pass 5 / fail 0
cd viewer && npm run build                       # exits 0, 17 routes generated
python -X utf8 -m scripts.verify_phase6 --mode code-complete   # 4/11 PASS (was 3/11 — I18N-08 flipped)
```

## Notes for downstream plans

- **06-03b** must add `import LanguageSwitcher from '@/components/LanguageSwitcher'` to `viewer/app/[locale]/layout.tsx` and render it inside the layout shell. The switcher is already typed-nav-correct; 06-03b only mounts it.
- **06-08** (Wave-2 viewer reads) imports `displayField` from `@/lib/i18n` and applies it on every JSONB-read field after migration 012. Example: `<h1>{displayField(timeline.title, locale)}</h1>`.
- **06-09/06-10** (Wave-3 worker bilingual emission) — once the Communicator + Phase 5 composer emit `{en, ka}` rows, the same displayField helper is the canonical read path on the viewer side; no further helper changes needed.

## Output (per PLAN.md <output>)

| Question | Answer |
|---|---|
| displayField helper line count | **10** (≤15 D-03 anti-creep gate) |
| Node version used | **v24.15.0** (tsx v4.22.3) |
| check_i18n_08 invocation matches pinned `npx tsx --test` | **Yes** — verify_phase6.py:676 `subprocess.run(["npx", "tsx", "--test", "viewer/lib/__tests__/i18n.test.ts"], cwd=VIEWER)`. Test file imports `from '../i18n.ts'` matching that resolution. |

## Self-Check: PASSED

- File viewer/lib/i18n.ts: FOUND
- File viewer/lib/__tests__/i18n.test.ts: FOUND
- File viewer/components/LanguageSwitcher.tsx: FOUND (with `@/i18n/navigation` import)
- File viewer/tsconfig.json: MODIFIED (exclude list extended)
- Commit 55eee7d: FOUND
- Commit 2301c0e: FOUND
- Commit c2a49e3: FOUND
- Verifier check_i18n_08: PASS
- npm run build: exit 0
- 5/5 unit tests: pass
