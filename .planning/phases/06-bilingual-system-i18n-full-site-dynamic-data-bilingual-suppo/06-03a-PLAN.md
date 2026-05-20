---
phase: 06-bilingual-system-i18n
plan: 03a
type: execute
wave: 1
depends_on:
  - 06-01
  - 06-02
files_modified:
  - viewer/app/[locale]/dashboard
  - viewer/app/[locale]/timeline
  - viewer/app/[locale]/papers
  - viewer/app/[locale]/therapies
  - viewer/app/[locale]/hypotheses
  - viewer/app/[locale]/today
  - viewer/app/[locale]/knowledge
  - viewer/app/[locale]/page.tsx
requirements:
  - I18N-02
autonomous: true
must_haves:
  truths:
    - "viewer/app/[locale]/ directory exists and contains the 7 family-facing route folders + viewer/app/[locale]/page.tsx (Today root) relocated from viewer/app/*"
    - "viewer/app/{dashboard,timeline,papers,therapies,hypotheses,today,knowledge}/ no longer exists at top level (file moves are recorded as git renames)"
    - "viewer/app/{api,audit,brain}/ remain at top level (NOT moved under [locale]/) per SPEC Out of Scope"
    - "viewer/app/layout.tsx is UNCHANGED by this plan (locale-aware layout refactor lands in 06-03b)"
    - "Page.tsx file contents are UNCHANGED by this plan — only their parent directories moved; param-signature updates land in 06-03b"
    - "cd viewer && npm run build exits 0 with the new route tree (build may emit runtime warnings about missing locale layout — that is fine; 06-03b lands the layout)"
    - "No new remote fetch/axios.post/XMLHttpRequest from viewer/ to non-self origins introduced by this plan (FND-02 trust boundary lint must continue to pass)"
  artifacts:
    - path: viewer/app/[locale]/dashboard/page.tsx
      provides: "Relocated dashboard page (file body unchanged)"
    - path: viewer/app/[locale]/page.tsx
      provides: "Relocated Today root page (file body unchanged)"
  key_links:
    - from: viewer/app/[locale]
      to: viewer/proxy.ts
      via: "next-intl matcher rewrites /dashboard to /[locale]/dashboard via createMiddleware(routing) from 06-01"
      pattern: "createMiddleware\\(routing\\)"
---

<objective>
Atomic locale folder move: relocate the 7 family-facing route directories (`dashboard`, `timeline`, `papers`, `therapies`, `hypotheses`, `today`, `knowledge`) from `viewer/app/*` to `viewer/app/[locale]/*`, plus relocate `viewer/app/page.tsx` (Today root) to `viewer/app/[locale]/page.tsx`. Uses 8 `git mv` operations so renames are tracked. Page.tsx file CONTENTS are unchanged here — async-params updates and layout refactor land in 06-03b. Routes under `viewer/app/{api,audit,brain}/` STAY at top level (matcher in proxy.ts excludes them).

This split (formerly part of 06-03) isolates the file-move step so the diff is reviewable as a pure rename, and so 06-03b's layout/params work happens on top of a clean tree.

Purpose: Begin I18N-02 — locale-segmented App Router structure (folder topology).
Output: 14 route URLs route-resolvable post-build (server may still 404 on rendering until 06-03b adds the [locale]/layout.tsx); `cd viewer && npm run build` exits 0.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-SPEC.md
@.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-CONTEXT.md
@.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-RESEARCH.md
@viewer/AGENTS.md
@viewer/app/layout.tsx
@viewer/app/page.tsx
@viewer/app/dashboard/page.tsx
@viewer/proxy.ts
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Move 7 family-facing route directories + root page.tsx under viewer/app/[locale]/ via git mv (8 operations)</name>
  <files>viewer/app/{dashboard,timeline,papers,therapies,hypotheses,today,knowledge}/**, viewer/app/page.tsx, viewer/app/[locale]/{dashboard,timeline,papers,therapies,hypotheses,today,knowledge}/**, viewer/app/[locale]/page.tsx</files>
  <read_first>
    - viewer/app/page.tsx (root — currently the "Today" overview)
    - viewer/app/dashboard/page.tsx (confirm current signature has no `params`)
    - viewer/app/hypotheses/page.tsx and viewer/app/hypotheses/[id]/page.tsx (nested dynamic route — must move as a unit)
    - .planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-SPEC.md (Out of Scope clause: `api`, `audit`, `brain` STAY at top level)
  </read_first>
  <action>
    Create directory `viewer/app/[locale]/`. Use `git mv` to relocate each of the 7 family-facing folders + the root page.tsx (8 operations total):

        git mv viewer/app/dashboard   "viewer/app/[locale]/dashboard"
        git mv viewer/app/timeline    "viewer/app/[locale]/timeline"
        git mv viewer/app/papers      "viewer/app/[locale]/papers"
        git mv viewer/app/therapies   "viewer/app/[locale]/therapies"
        git mv viewer/app/hypotheses  "viewer/app/[locale]/hypotheses"
        git mv viewer/app/today       "viewer/app/[locale]/today"
        git mv viewer/app/knowledge   "viewer/app/[locale]/knowledge"
        git mv viewer/app/page.tsx    "viewer/app/[locale]/page.tsx"

    DO NOT move: viewer/app/api/, viewer/app/audit/, viewer/app/brain/, viewer/app/layout.tsx, viewer/app/globals.css, viewer/app/favicon.ico. These stay at top level — proxy.ts matcher excludes their segments from locale rewriting.

    On Windows / PowerShell, the `[` and `]` characters in the destination path MUST be quoted. Use double quotes around the destination (shown above).

    After all 8 `git mv` calls, do NOT modify any page.tsx contents. The async-params signature update + layout refactor are intentionally split out into 06-03b — this plan delivers a pure rename diff that can be reviewed as a topology change without conflating it with code edits.
  </action>
  <acceptance_criteria>
    - `test -d "viewer/app/[locale]/dashboard" && test -d "viewer/app/[locale]/timeline" && test -d "viewer/app/[locale]/papers" && test -d "viewer/app/[locale]/therapies" && test -d "viewer/app/[locale]/hypotheses" && test -d "viewer/app/[locale]/today" && test -d "viewer/app/[locale]/knowledge"` succeeds.
    - `test -f "viewer/app/[locale]/page.tsx"` succeeds.
    - `test ! -d viewer/app/dashboard && test ! -d viewer/app/timeline && test ! -d viewer/app/papers && test ! -d viewer/app/therapies && test ! -d viewer/app/hypotheses && test ! -d viewer/app/today && test ! -d viewer/app/knowledge` succeeds.
    - `test ! -f viewer/app/page.tsx` succeeds.
    - `test -d viewer/app/api && test -d viewer/app/audit && test -d viewer/app/brain` succeeds (NOT moved).
    - `git status --porcelain | grep -E '^R' | wc -l` is at least 7 (renames recorded).
    - viewer/app/layout.tsx and viewer/app/globals.css UNCHANGED by this plan (verified via `git diff --name-only HEAD -- viewer/app/layout.tsx viewer/app/globals.css` returning empty).
  </acceptance_criteria>
  <verify>
    <automated>test -d "viewer/app/[locale]/dashboard" && test -d "viewer/app/[locale]/timeline" && test -d "viewer/app/api" && test ! -d "viewer/app/dashboard" && test ! -f "viewer/app/page.tsx"</automated>
  </verify>
  <done>8 directories/files relocated under [locale]/; api/audit/brain untouched; renames tracked in git.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Smoke build — confirm `npm run build` exits 0 with the renamed tree (route resolution verified)</name>
  <files>(no source files modified — build verification only)</files>
  <read_first>
    - viewer/proxy.ts (next-intl middleware — must still match the relocated routes)
    - viewer/next.config.ts
  </read_first>
  <action>
    Run `cd viewer && npm run build`. The build MUST exit 0. The tree now has page.tsx files under `viewer/app/[locale]/*` whose contents still use the pre-move signatures (sync `params` or no `params`). Next.js 16 will accept this at build time (the [locale] segment becomes part of the route pattern; pages without async params just don't read the locale yet). Runtime rendering may emit warnings about missing setRequestLocale or unhandled params — that is expected and resolved in 06-03b.

    The 14 URLs (7 routes × 2 locales) must be **route-resolvable** in the build output. Inspect the build manifest:

        grep -E "/\\[locale\\]/(dashboard|timeline|papers|therapies|hypotheses|today|knowledge)" viewer/.next/routes-manifest.json

    Expected: at least 7 dynamic-route entries matching the new tree.

    If build fails with "Cannot find module" or "params is not defined" — 06-03b is needed to land the async params; if build fails with a Next.js routing error (e.g., conflicting [locale]/page.tsx at multiple roots), STOP and surface — that is a topology problem this plan must fix before handing off to 06-03b.
  </action>
  <acceptance_criteria>
    - `cd viewer && npm run build` exit code 0.
    - viewer/.next directory exists post-build.
    - Build output / routes-manifest.json registers the 7 family routes under /[locale]/* (grep above returns ≥7 matches).
    - No build error mentioning "duplicate page" or "cannot resolve route".
  </acceptance_criteria>
  <verify>
    <automated>cd viewer && npm run build 2>&1 | tee /tmp/i18n-03a-build.log && grep -qE "compiled successfully|Compiled successfully" /tmp/i18n-03a-build.log</automated>
  </verify>
  <done>Build clean with new tree; 14 URLs route-resolvable; ready for 06-03b layout + params work.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| family browser → viewer/app/[locale]/** | locale URL segment crosses untrusted-input boundary (locale validation lands in 06-03b layout) |
| viewer/ → external origins | FND-02 trust boundary lint — this plan adds no new fetch sites; verified by lint regression sweep |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-06-LOCALE-FOLDER-DRIFT | Tampering | viewer/app/[locale]/** vs viewer/app/* | mitigate | Task 1 acceptance grep confirms api/audit/brain are NOT moved; verifier check_i18n_02 (post-06-03b) re-confirms file presence. |
| T-06-FND-02 (carry-over) | Information Disclosure | viewer/ remote-origin fetches | mitigate | This plan adds NO new fetch call sites; the existing FND-02 trust boundary lint regression continues to pass (no new must_haves truth required at this plan's verify gate — the lint runs in 06-13 alongside the full Phase 4/5 regression sweep). |
</threat_model>

<verification>
- 7 family-facing route directories exist under viewer/app/[locale]/
- viewer/app/[locale]/page.tsx exists
- viewer/app/{api,audit,brain}/ remain at top level
- `cd viewer && npm run build` exits 0
- TypeScript compiles cleanly (any signature warnings from pre-move sync params are acceptable — 06-03b fixes them)
</verification>

<success_criteria>
- 8 git mv operations recorded as renames
- 14 URLs (7 routes × 2 locales) route-resolvable in build output
- I18N-02 verifier check (file-presence half) flips PARTIAL-GREEN at this plan boundary; full I18N-02 GREEN after 06-03b
- No regression in api/audit/brain routes (verifier check_i18n_11 spawns verify_phase4/5 in 06-13 to confirm)
</success_criteria>

<output>
Create `.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-03a-SUMMARY.md` when done. Record:
- 8 git rename operations (one per directory/file)
- Build elapsed time
- routes-manifest.json grep evidence (7 matches)
- Confirmation that viewer/app/layout.tsx is UNCHANGED (handoff promise to 06-03b)
</output>
