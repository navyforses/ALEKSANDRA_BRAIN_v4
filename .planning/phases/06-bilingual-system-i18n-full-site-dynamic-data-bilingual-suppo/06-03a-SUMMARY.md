---
phase: 06-bilingual-system-i18n
plan: 03a
subsystem: ui
tags: [next-intl, next.js-16, i18n, app-router, locale-segment, structural-move]

# Dependency graph
requires:
  - phase: 06-01
    provides: next-intl@4.12.0 installed; viewer/proxy.ts matcher excludes api|audit|brain|_next|_vercel|static
  - phase: 06-02
    provides: verify_phase6.py scaffold (check_i18n_02 pending file-presence verification)
provides:
  - viewer/app/[locale]/ shell containing the 7 relocated family-facing route directories + relocated root page.tsx
  - Pure-rename git diff (R100 across all 10 file moves) — file contents byte-identical to pre-move
  - npm run build clean on the relocated tree (9 dynamic routes resolve under /[locale]/* — exceeds ≥7 floor in PLAN)
affects:
  - 06-03b (layout authoring + async params signature on top of the moved tree)
  - 06-04 (LanguageSwitcher mount under [locale]/layout.tsx)
  - 06-05a/b (messages expansion + t() refs target [locale]/* paths)
  - All Wave-1 frontend work post this plan

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Locale-shell pattern (06-RESEARCH.md Pattern 2): family-facing routes live under app/[locale]/*; internal/API routes (api, audit, brain) remain at top level matching proxy.ts matcher exclusions"
    - "Atomic structural move via `git mv` — every relocation tracked as R100 rename (no content drift, reviewable as a topology change in isolation)"
    - "Pure-rename plan separation: 06-03a delivers the topology, 06-03b lands the layout + async-params code edits on top of the clean tree"

key-files:
  created:
    - viewer/app/[locale]/dashboard/page.tsx (relocated from viewer/app/dashboard/page.tsx)
    - viewer/app/[locale]/timeline/page.tsx (relocated from viewer/app/timeline/page.tsx)
    - viewer/app/[locale]/papers/page.tsx (relocated from viewer/app/papers/page.tsx)
    - viewer/app/[locale]/therapies/page.tsx (relocated from viewer/app/therapies/page.tsx)
    - viewer/app/[locale]/hypotheses/page.tsx (relocated from viewer/app/hypotheses/page.tsx)
    - viewer/app/[locale]/hypotheses/[id]/page.tsx (relocated from viewer/app/hypotheses/[id]/page.tsx)
    - viewer/app/[locale]/hypotheses/actions.ts (relocated from viewer/app/hypotheses/actions.ts)
    - viewer/app/[locale]/today/page.tsx (relocated from viewer/app/today/page.tsx)
    - viewer/app/[locale]/knowledge/page.tsx (relocated from viewer/app/knowledge/page.tsx)
    - viewer/app/[locale]/page.tsx (relocated from viewer/app/page.tsx — former Today root landing)
    - .planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-03a-SUMMARY.md
  modified: []
  deleted: []  # 8 source-side paths gone (their content moved under [locale]/) — git tracks as renames, not deletes

key-decisions:
  - "Created viewer/app/[locale]/ explicitly with `mkdir -p` before issuing the 8 `git mv` commands so the destination existed (Windows PowerShell + literal-bracket path requirement). The `[` `]` are NOT glob metacharacters in our PowerShell context — they are literal directory-name characters and must be quoted."
  - "Whole-directory `git mv` per folder (NOT per-file) so nested children (e.g. hypotheses/[id]/page.tsx and hypotheses/actions.ts) move atomically and git rename-detection collapses each file to R100."
  - "Did NOT modify viewer/app/layout.tsx or viewer/app/globals.css — those stay at the app root and are 06-03b's domain. This preserves the pure-rename invariant of this plan and keeps the diff reviewable in isolation."
  - "Did NOT touch viewer/app/api/, viewer/app/audit/, viewer/app/brain/ — they remain unlocalized per 06-SPEC.md Out of Scope clause and proxy.ts matcher exclusions (api|audit|brain|_next|_vercel|.*\\..*)."
  - "Decided NOT to add a layout.tsx under viewer/app/[locale]/ in this plan — the build is already green without it and 06-03b owns the locale layout work. Inserting a placeholder layout here would force a content-modification commit and break the pure-rename invariant this split was designed to preserve."

patterns-established:
  - "From now on, family-facing routes belong under viewer/app/[locale]/; internal-only routes belong at viewer/app/<segment>/."
  - "Whenever a plan is split into <N>a + <N>b, <N>a delivers the structural/topology change and <N>b delivers the code-edit change on top — reviewable in isolation."

requirements-completed: []   # I18N-02 is PARTIAL-GREEN; full GREEN after 06-03b lands the layout + params signature

# Metrics
duration: 10m
completed: 2026-05-21
---

# Phase 6 Plan 03a: Locale Folder Move Summary

**Eight `git mv` operations relocate the 7 family-facing route directories + the root Today page under `viewer/app/[locale]/`; the topology change lands as a 10-file R100 pure-rename commit and the next-intl@4 + Next.js 16 build is verified clean (9 dynamic routes resolve under `/[locale]/*`).**

## Performance

- **Duration:** ~10 min (planning context read + 8 git mv + verification + build + summary)
- **Tasks:** 2 (1 source-mutating + 1 build-verification)
- **Commits (pre-metadata):** 1 (`731b601` — the rename batch)
- **Files relocated:** 10 (7 directories collapsed to 10 individual page/action files + 1 root page.tsx)
- **Files modified in content:** 0 (acceptance criterion: zero content drift)

## Accomplishments

### Task 1 — 8 `git mv` operations (commit `731b601`)

Executed in a single bash chain so a failure on any move would have surfaced before commit:

```
git mv viewer/app/dashboard   "viewer/app/[locale]/dashboard"
git mv viewer/app/timeline    "viewer/app/[locale]/timeline"
git mv viewer/app/papers      "viewer/app/[locale]/papers"
git mv viewer/app/therapies   "viewer/app/[locale]/therapies"
git mv viewer/app/hypotheses  "viewer/app/[locale]/hypotheses"   # nested [id]/ + actions.ts moved atomically
git mv viewer/app/today       "viewer/app/[locale]/today"
git mv viewer/app/knowledge   "viewer/app/[locale]/knowledge"
git mv viewer/app/page.tsx    "viewer/app/[locale]/page.tsx"
```

`git diff --cached --name-status` confirmed **all 10 file moves tracked as R100 (100% similar) renames** before commit — no D+A pairs, no content drift.

Pre-commit hooks ran clean: gitleaks, trailing-whitespace, end-of-files, merge-conflict, private-key, large-files, `no remote fetch in viewer/ (FND-02)` all passed.

### Task 2 — Smoke build verification (no source changes; folded into this summary)

`cd viewer && npm run build` exit code **0**. Build manifest (Next.js 16.2.6 Turbopack):

```
Route (app)
┌ ○ /_not-found
├ ƒ /[locale]
├ ƒ /[locale]/dashboard
├ ƒ /[locale]/hypotheses
├ ƒ /[locale]/hypotheses/[id]
├ ƒ /[locale]/knowledge
├ ƒ /[locale]/papers
├ ƒ /[locale]/therapies
├ ƒ /[locale]/timeline
├ ƒ /[locale]/today
├ ƒ /api/manager/apply
├ ƒ /api/manager/audit
├ ƒ /api/manager/email
├ ƒ /api/manager/undo/[id]
├ ƒ /api/manager/voice
├ ○ /audit
└ ○ /brain

ƒ Proxy (Middleware)
```

The `Proxy (Middleware)` row confirms next-intl's createMiddleware from 06-01 is still mounted via `viewer/proxy.ts` and is now matching the new `/[locale]/*` tree.

`routes-manifest.json` grep evidence (acceptance floor ≥7; actual 8 unique entries — passes):

```
/[locale]/dashboard
/[locale]/hypotheses
/[locale]/hypotheses/[id]
/[locale]/knowledge
/[locale]/papers
/[locale]/therapies
/[locale]/timeline
/[locale]/today
```

(`/[locale]` index page is in the manifest separately as `ƒ /[locale]` — the grep filter intentionally only counts the family-facing slugs from the SPEC.)

## Decisions Made

| # | Decision | Rationale |
|---|---|---|
| 1 | `mkdir -p "viewer/app/[locale]"` BEFORE the 8 `git mv` calls | On Windows PowerShell, the literal `[locale]` directory must exist before git mv can target it as a destination. Quoted to keep `[` `]` literal. |
| 2 | Whole-directory moves, not per-file moves | One `git mv viewer/app/hypotheses ...` atomically moves the nested `[id]/page.tsx` + `actions.ts` together. Git's rename-detection then collapses each child to R100. |
| 3 | viewer/app/layout.tsx untouched in this plan | 06-03b owns the layout refactor (locale-aware shell + html lang + locale validation). Touching layout.tsx here would break the pure-rename invariant. |
| 4 | viewer/app/{api,audit,brain}/ untouched at top level | 06-SPEC.md Out of Scope + `viewer/proxy.ts` matcher `'/((?!api|audit|brain|_next|_vercel|.*\\..*).*)'` explicitly excludes these segments from locale rewriting. |
| 5 | NO `viewer/app/[locale]/layout.tsx` placeholder added | Build is already green without one (Next.js 16 happily composes the root `viewer/app/layout.tsx` over `/[locale]/*` pages). Adding a placeholder would require a content-modification commit and break the pure-rename invariant that this plan was split out to preserve. 06-03b authors the real locale layout. |

## Files Created

```
viewer/app/[locale]/dashboard/page.tsx           (R100 from viewer/app/dashboard/page.tsx)
viewer/app/[locale]/timeline/page.tsx            (R100 from viewer/app/timeline/page.tsx)
viewer/app/[locale]/papers/page.tsx              (R100 from viewer/app/papers/page.tsx)
viewer/app/[locale]/therapies/page.tsx           (R100 from viewer/app/therapies/page.tsx)
viewer/app/[locale]/hypotheses/page.tsx          (R100 from viewer/app/hypotheses/page.tsx)
viewer/app/[locale]/hypotheses/[id]/page.tsx     (R100 from viewer/app/hypotheses/[id]/page.tsx)
viewer/app/[locale]/hypotheses/actions.ts        (R100 from viewer/app/hypotheses/actions.ts)
viewer/app/[locale]/today/page.tsx               (R100 from viewer/app/today/page.tsx)
viewer/app/[locale]/knowledge/page.tsx           (R100 from viewer/app/knowledge/page.tsx)
viewer/app/[locale]/page.tsx                     (R100 from viewer/app/page.tsx)
.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-03a-SUMMARY.md
```

## Files Modified

None. (This is a pure-rename plan — that's the whole point of the split.)

## Files Deleted

None. The 8 source-side paths (`viewer/app/dashboard/`, etc.) are no longer present at the top level, but git records each as a R100 rename, not a D+A pair.

## Verification Evidence

Run on the post-Task-1 working tree:

1. **`git diff --cached --name-status` (pre-commit):** 10 R100 entries; zero modify/delete/add entries.
2. **`git log --diff-filter=R -1 --stat`** on `731b601`: 10 files changed, 0 insertions, 0 deletions.
3. **`ls viewer/app`** post-commit: `[locale]`, `api`, `audit`, `brain`, `favicon.ico`, `globals.css`, `layout.tsx` — none of the seven moved folder names remain, and the kept-at-top-level routes (api/audit/brain) are intact.
4. **`ls "viewer/app/[locale]"`:** `dashboard`, `hypotheses`, `knowledge`, `page.tsx`, `papers`, `therapies`, `timeline`, `today`.
5. **`cd viewer && npm run build`:** exit code 0; manifest shows 9 dynamic routes under `/[locale]/*` (including `ƒ /[locale]` index) + 5 `/api/*` + `/audit` + `/brain` + `/_not-found`.
6. **`routes-manifest.json` grep `/[locale]/(dashboard|timeline|papers|therapies|hypotheses|today|knowledge)`:** 8 unique matches (acceptance floor ≥7 — exceeds).
7. **Build duration:** TypeScript 10.8s + compile 12.4s + static 4.1s ≈ ~27s wall.

## Deviations from Plan

None — the plan was followed exactly. No bug fixes, no auto-additions, no architectural changes. The split (06-03 → 06-03a + 06-03b) was a planning decision recorded upstream; this executor honored that split by NOT touching layout.tsx or page contents.

## Known Stubs

None — this plan does not introduce stubs. The post-move tree has page.tsx files whose contents still use pre-move signatures (sync `params` or no `params`). That is **not** a stub; it is the handoff state to 06-03b which will update each signature to `params: Promise<{locale: string}>` and add the `viewer/app/[locale]/layout.tsx` shell.

## Handoff Promises to 06-03b

- `viewer/app/[locale]/` exists with the 7 family routes + `[locale]/page.tsx` already in place.
- `viewer/app/layout.tsx` is unchanged from pre-06-03a — 06-03b can refactor it (or move it under `[locale]/`) without conflict.
- `viewer/app/{api,audit,brain}/` are untouched and remain unlocalized.
- `viewer/proxy.ts` matcher is unchanged (already excludes api/audit/brain since 06-01).
- `npm run build` is green — 06-03b can rely on a working baseline before it edits files.

## Self-Check: PASSED

- `viewer/app/[locale]/dashboard/page.tsx` — FOUND
- `viewer/app/[locale]/timeline/page.tsx` — FOUND
- `viewer/app/[locale]/papers/page.tsx` — FOUND
- `viewer/app/[locale]/therapies/page.tsx` — FOUND
- `viewer/app/[locale]/hypotheses/page.tsx` — FOUND
- `viewer/app/[locale]/hypotheses/[id]/page.tsx` — FOUND
- `viewer/app/[locale]/hypotheses/actions.ts` — FOUND
- `viewer/app/[locale]/today/page.tsx` — FOUND
- `viewer/app/[locale]/knowledge/page.tsx` — FOUND
- `viewer/app/[locale]/page.tsx` — FOUND
- `viewer/app/dashboard` — ABSENT (correctly relocated)
- `viewer/app/page.tsx` — ABSENT (correctly relocated)
- `viewer/app/api` — PRESENT (correctly preserved)
- `viewer/app/audit` — PRESENT (correctly preserved)
- `viewer/app/brain` — PRESENT (correctly preserved)
- `viewer/app/layout.tsx` — PRESENT and UNCHANGED (06-03b owns its refactor)
- commit `731b601` — FOUND in `git log`
