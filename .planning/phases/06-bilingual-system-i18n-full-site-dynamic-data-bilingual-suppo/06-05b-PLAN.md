---
phase: 06-bilingual-system-i18n
plan: 05b
type: execute
wave: 1
depends_on:
  - 06-03a
  - 06-03b
  - 06-05a
files_modified:
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
requirements:
  - I18N-03
autonomous: true
must_haves:
  truths:
    - "Every t('Key.path') call in viewer/app/[locale]/** + viewer/components/** resolves in BOTH viewer/messages/en.json and viewer/messages/ka.json (06-05a delivered both)"
    - "No hardcoded English string literal remains in JSX render output of any [locale]/ page (configuration/constants like enum keys may stay)"
    - "TopNav uses the typed createNavigation Link so locale prefix is auto-applied across the navigation"
    - "Each page calls getTranslations('Namespace') (Server Component) or useTranslations('Namespace') (Client Component) AFTER setRequestLocale(locale) (RESEARCH.md Pitfall 4)"
    - "No new remote fetch/axios.post/XMLHttpRequest from viewer/ to non-self origins introduced by this plan (FND-02 trust boundary lint must continue to pass)"
  artifacts:
    - path: viewer/components/layout/TopNav.tsx
      provides: "Locale-aware nav — typed Link from @/i18n/navigation; getTranslations or useTranslations for labels"
      contains: "@/i18n/navigation"
  key_links:
    - from: viewer/app/[locale]/**/page.tsx
      to: viewer/messages/{en,ka}.json
      via: "getTranslations('Namespace') + t('Key.path')"
      pattern: "getTranslations\\(['\\\"]"
---

<objective>
Page-side wiring step (split from former 06-05): replace hardcoded JSX string literals with `t('Key.path')` references across the 9 [locale]/ page.tsx files + TopNav, consuming the dictionaries 06-05a authored. Update viewer/components/layout/TopNav.tsx to import the typed Link from @/i18n/navigation so locale prefix is auto-applied on every nav item. The dictionaries are already in place (key-set equal) — this plan delivers the consumer-side wiring.

Critical: every emitted `t(...)` key MUST resolve in both en.json and ka.json — the verifier check_i18n_03 (06-13) does a grep+jq sweep over the emitted call sites and fails if any path is missing. Because 06-05a guarantees structural equality, the only failure mode is calling a key that doesn't exist in EITHER dictionary.

Purpose: Complete I18N-03 — every visible string in the 7 family-facing routes goes through next-intl resolution.
Output: 9 pages + TopNav wired through `t(...)` / typed Link; verifier check_i18n_03 fully GREEN.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-SPEC.md
@.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-CONTEXT.md
@.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-RESEARCH.md
@viewer/messages/en.json
@viewer/messages/ka.json
@viewer/app/[locale]/page.tsx
@viewer/app/[locale]/dashboard/page.tsx
@viewer/app/[locale]/timeline/page.tsx
@viewer/app/[locale]/papers/page.tsx
@viewer/app/[locale]/therapies/page.tsx
@viewer/app/[locale]/hypotheses/page.tsx
@viewer/app/[locale]/hypotheses/[id]/page.tsx
@viewer/app/[locale]/today/page.tsx
@viewer/app/[locale]/knowledge/page.tsx
@viewer/components/layout/TopNav.tsx
@viewer/i18n/navigation.ts

<interfaces>
<!-- next-intl 4 server-side translation hook -->
import {getTranslations, setRequestLocale} from 'next-intl/server';
const t = await getTranslations('Dashboard');
// t('title') reads messages/{locale}.json key Dashboard.title

<!-- Client-side equivalent -->
import {useTranslations} from 'next-intl';
const t = useTranslations('Shared');

<!-- Typed Link from createNavigation -->
import {Link} from '@/i18n/navigation';
<Link href="/dashboard">...</Link>  // auto-prefixes /en/ or /ka/
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Per-page sweep — replace hardcoded JSX strings in 9 page.tsx files with `t('Namespace.key')` references</name>
  <files>viewer/app/[locale]/page.tsx, viewer/app/[locale]/dashboard/page.tsx, viewer/app/[locale]/timeline/page.tsx, viewer/app/[locale]/papers/page.tsx, viewer/app/[locale]/therapies/page.tsx, viewer/app/[locale]/hypotheses/page.tsx, viewer/app/[locale]/hypotheses/[id]/page.tsx, viewer/app/[locale]/today/page.tsx, viewer/app/[locale]/knowledge/page.tsx</files>
  <read_first>
    - viewer/messages/en.json (06-05a output — target keys)
    - Each of the 9 page.tsx files (06-05a Task 1 already grepped them; this task applies the rewrites)
    - .planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-RESEARCH.md (Code Examples / Example: Page consuming async locale params — `const t = await getTranslations('Dashboard'); ... <h1>{t('title')}</h1>`)
  </read_first>
  <action>
    For each of the 9 [locale]/ page.tsx files:

    (a) Add `import {getTranslations} from 'next-intl/server';` (if Server Component — most pages are) or `import {useTranslations} from 'next-intl';` (if Client Component, marked `'use client'`).

    (b) Inside the component, after `setRequestLocale(locale)` (already added by 06-03b Task 2), add:
        const t = await getTranslations('Dashboard');   // for dashboard/page.tsx
        const tShared = await getTranslations('Shared');  // shared keys (loading/empty/error)

    (c) Replace every user-visible JSX string literal with `{t('keyPath')}` referencing the appropriate key from 06-05a's en.json. Examples:
        `<h1>Dashboard</h1>` → `<h1>{t('title')}</h1>`
        `<p>No timeline entries</p>` → `<p>{tShared('empty')}</p>` (or page-specific `t('empty')` if more contextual copy exists)
        `placeholder="Search papers..."` → `placeholder={t('searchPlaceholder')}`

    (d) For client components (e.g., chart components), use `useTranslations` instead of `getTranslations` and drop the `await`.

    (e) Do NOT translate enum/status keys that are used in switch statements or as DB column values (`'new' | 'validating' | 'confirmed'`). Translate ONLY the display labels rendered in JSX. The status keys themselves map to Hypotheses.status.{new,validating,confirmed,refuted} message keys.

    (f) Every page MUST still import `setRequestLocale` and call it before `getTranslations` (RESEARCH.md Pitfall 4).

    (g) After all 9 pages are updated, `cd viewer && npx tsc --noEmit -p tsconfig.json` MUST exit 0. If TypeScript complains about unused imports (because some pages may not need `useTranslations`), remove them.
  </action>
  <acceptance_criteria>
    - `grep -rE "getTranslations|useTranslations" viewer/app/\[locale\]/ | wc -l` returns ≥ 9 (every page has at least one translation hook).
    - No new hardcoded user-visible string regression: a grep for representative remaining strings (e.g., `>Dashboard<` literal in dashboard/page.tsx outside attribute contexts) returns 0 hits in [locale]/ pages.
    - `cd viewer && npx tsc --noEmit -p tsconfig.json` exits 0.
  </acceptance_criteria>
  <verify>
    <automated>cd viewer && for f in dashboard timeline papers therapies hypotheses today knowledge; do grep -q "getTranslations\|useTranslations" "app/[locale]/$f/page.tsx" || { echo "MISS $f"; exit 1; }; done; grep -q "getTranslations\|useTranslations" "app/[locale]/page.tsx" && grep -q "getTranslations\|useTranslations" "app/[locale]/hypotheses/[id]/page.tsx"</automated>
  </verify>
  <done>9 [locale]/ pages use getTranslations / useTranslations; no hardcoded English literals remain in JSX render output.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Update viewer/components/layout/TopNav.tsx — typed Link from @/i18n/navigation + getTranslations('Navigation') labels</name>
  <files>viewer/components/layout/TopNav.tsx</files>
  <read_first>
    - viewer/components/layout/TopNav.tsx (current — uses `import Link from 'next/link'` + hardcoded English labels)
    - viewer/i18n/navigation.ts (06-01 — exports typed Link with auto-locale-prefix)
    - viewer/messages/en.json (06-05a — Navigation namespace keys)
  </read_first>
  <action>
    Edit viewer/components/layout/TopNav.tsx:

    (a) Replace `import Link from 'next/link';` with `import {Link} from '@/i18n/navigation';`. The typed Link auto-applies the active locale prefix on every nav item.

    (b) Replace hardcoded label strings (`Dashboard`, `Timeline`, `Papers`, etc.) with `{t('dashboard')}` / `{t('timeline')}` / etc. — using `useTranslations('Navigation')` (if TopNav is Client) or `getTranslations('Navigation')` (if Server).

    (c) If TopNav is currently NOT a Client Component AND it imports any client-only hook (e.g., usePathname from next/navigation), it's already client-flagged; add `useTranslations` directly. If it's a Server Component (no `'use client'` directive), convert to async and use `getTranslations`. Choose whichever pattern requires fewer changes.

    (d) Verify the existing nav structure is preserved (links to /dashboard, /timeline, /papers, /therapies, /hypotheses, /today, /knowledge). The typed Link will rewrite hrefs to /en/dashboard or /ka/dashboard automatically.
  </action>
  <acceptance_criteria>
    - viewer/components/layout/TopNav.tsx contains `from '@/i18n/navigation'`.
    - File contains `useTranslations` or `getTranslations`.
    - File no longer contains `from 'next/link'` (replaced by `@/i18n/navigation`).
    - `cd viewer && npx tsc --noEmit -p tsconfig.json` exits 0.
  </acceptance_criteria>
  <verify>
    <automated>grep -q "from '@/i18n/navigation'" viewer/components/layout/TopNav.tsx && (grep -q "useTranslations\|getTranslations" viewer/components/layout/TopNav.tsx) && ! grep -q "from 'next/link'" viewer/components/layout/TopNav.tsx</automated>
  </verify>
  <done>TopNav uses typed Link + getTranslations('Navigation'); locale prefix auto-applied across the nav.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Final missing-key grep verifier + npm run build smoke + I18N-03 verifier sweep</name>
  <files>(no source files modified — verification only)</files>
  <read_first>
    - viewer/messages/en.json
    - viewer/messages/ka.json
    - scripts/verify_phase6.py (06-02 — check_i18n_03 implementation)
  </read_first>
  <action>
    (a) Run a missing-key grep verifier: extract every `t('Namespace.key')` / `t('key')` / `useTranslations('NS')` call from viewer/app/[locale]/** + viewer/components/**, build the full set of dotted key paths actually used at runtime, then look each up in both en.json and ka.json. If any path is missing from EITHER dictionary, FAIL — either add the key to both dictionaries (loop back to 06-05a) or fix the call site.

    Python verifier (run inline):

        python -c "
        import json, re, pathlib
        en = json.load(open('viewer/messages/en.json', encoding='utf-8'))
        ka = json.load(open('viewer/messages/ka.json', encoding='utf-8'))

        # Walk t('...') calls — naive but sufficient for the {Namespace}.{key} convention used here
        used = set()
        for p in pathlib.Path('viewer').rglob('*.tsx'):
          src = p.read_text(encoding='utf-8')
          for m in re.finditer(r\"t\\(\\s*['\\\"]([\\w.]+)['\\\"]\", src):
            used.add(m.group(1))
          for m in re.finditer(r\"(?:get|use)Translations\\(\\s*['\\\"](\\w+)['\\\"]\", src):
            used.add(m.group(1) + '.*')   # namespace mark; just verify the namespace exists

        def resolve(d, path):
          parts = path.split('.')
          for p in parts:
            if not isinstance(d, dict) or p not in d:
              return False
            d = d[p]
          return True

        missing_en = [p for p in used if not p.endswith('.*') and not resolve(en, p)]
        missing_ka = [p for p in used if not p.endswith('.*') and not resolve(ka, p)]
        if missing_en or missing_ka:
          print(f'MISSING en: {missing_en}')
          print(f'MISSING ka: {missing_ka}')
          raise SystemExit(1)
        print(f'OK: {len(used)} translation references all resolve in both dictionaries')
        "

    (b) Run `cd viewer && npm run build`. Build MUST exit 0 — any missing key at runtime would not break the build (next-intl substitutes `[Namespace.key]` for missing entries), but the verifier in (a) gives the deterministic check.

    (c) Run the Phase 6 verifier gate I18N-03:

        python -m scripts.verify_phase6 --mode code-complete --gate I18N-03

    Expected: exit 0; check_i18n_03 marked PASS.
  </action>
  <acceptance_criteria>
    - Inline Python missing-key verifier prints `OK: N translation references all resolve in both dictionaries`.
    - `cd viewer && npm run build` exits 0.
    - `python -m scripts.verify_phase6 --mode code-complete --gate I18N-03` exits 0 (check_i18n_03 PASS).
  </acceptance_criteria>
  <verify>
    <automated>cd viewer && npm run build 2>&1 | tee /tmp/i18n-05b-build.log | grep -qE "compiled successfully|Compiled successfully" && cd .. && python -m scripts.verify_phase6 --mode code-complete --gate I18N-03</automated>
  </verify>
  <done>Every `t(...)` reference resolves in both dictionaries; build clean; check_i18n_03 GREEN.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| viewer build → messages/{locale}.json | Static assets bundled at build time |
| viewer/ → external origins | FND-02 trust boundary lint — this plan touches JSX + nav rewiring only; no new fetch sites |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-06-05 | Information Disclosure (low) | viewer pages emitting unresolvable keys | mitigate | Task 3 missing-key verifier extracts every `t(...)` call and asserts resolution in both dictionaries. CI gate before merge. |
| T-06-MISSING-LOCALE-FILE | Denial of Service | viewer/i18n/request.ts | mitigate | Both en.json and ka.json bundled at build time (verified by 06-05a). |
| T-06-FND-02 (carry-over) | Information Disclosure | viewer/ remote-origin fetches | mitigate | This plan touches JSX render output + nav Link import; no new fetch call sites. FND-02 lint regression continues to pass (covered by 06-13 sweep). |
</threat_model>

<verification>
- `cd viewer && npm run build` exits 0
- Inline missing-key Python verifier prints OK
- `python -m scripts.verify_phase6 --mode code-complete --gate I18N-03` PASSES
</verification>

<success_criteria>
- 9 pages + TopNav all use getTranslations / useTranslations + typed Link
- Zero hardcoded user-visible English literals remain in [locale]/ tree
- Every `t(...)` reference resolves in both en.json and ka.json
- I18N-03 verifier check GREEN
</success_criteria>

<output>
Create `.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-05b-SUMMARY.md` when done. Record:
- Total `t(...)` and `useTranslations` references inserted across [locale]/
- Whether TopNav switched to Client or stayed Server (and why)
- Any namespace decisions (e.g., merging Dashboard chart strings into Shared)
- Missing-key verifier output (must show OK with N references)
</output>
