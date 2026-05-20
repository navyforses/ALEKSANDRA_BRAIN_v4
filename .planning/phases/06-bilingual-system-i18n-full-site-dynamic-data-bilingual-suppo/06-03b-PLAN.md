---
phase: 06-bilingual-system-i18n
plan: 03b
type: execute
wave: 1
depends_on:
  - 06-01
  - 06-03a
files_modified:
  - viewer/app/layout.tsx
  - viewer/app/[locale]/layout.tsx
  - viewer/app/[locale]/page.tsx
  - viewer/app/[locale]/dashboard/page.tsx
  - viewer/app/[locale]/timeline/page.tsx
  - viewer/app/[locale]/papers/page.tsx
  - viewer/app/[locale]/therapies/page.tsx
  - viewer/app/[locale]/hypotheses/page.tsx
  - viewer/app/[locale]/hypotheses/[id]/page.tsx
  - viewer/app/[locale]/today/page.tsx
  - viewer/app/[locale]/knowledge/page.tsx
requirements:
  - I18N-02
autonomous: true
must_haves:
  truths:
    - "viewer/app/[locale]/layout.tsx exists and calls setRequestLocale(locale) after awaiting params + validating with hasLocale(routing.locales, locale)"
    - "viewer/app/layout.tsx no longer renders <html> or <body> (those move to [locale]/layout.tsx); root layout is a minimal children-passthrough or static SEO fallback"
    - "Every moved page.tsx accepts `params: Promise<{locale: 'en' | 'ka'}>` per Next.js 16 async-params shape (RESEARCH.md Pitfall 2 prevention)"
    - "Nested dynamic route viewer/app/[locale]/hypotheses/[id]/page.tsx accepts `params: Promise<{locale: 'en' | 'ka'; id: string}>`"
    - "cd viewer && npm run build exits 0; build manifest lists 7 routes under /[locale]/*"
    - "Bare /dashboard 308-redirects to /en/dashboard (next-intl default behavior via proxy.ts matcher from 06-01)"
    - "No new remote fetch/axios.post/XMLHttpRequest from viewer/ to non-self origins introduced by this plan (FND-02 trust boundary lint must continue to pass)"
  artifacts:
    - path: viewer/app/[locale]/layout.tsx
      provides: "Locale-scoped layout — setRequestLocale + NextIntlClientProvider + hasLocale validation + html/body shell"
      contains: "setRequestLocale"
    - path: viewer/app/[locale]/dashboard/page.tsx
      provides: "Dashboard page with async locale params signature"
      contains: "params: Promise"
  key_links:
    - from: viewer/app/[locale]/layout.tsx
      to: viewer/i18n/routing.ts
      via: "import {routing} from '@/i18n/routing'"
      pattern: "from\\s+['\\\"]@/i18n/routing"
    - from: viewer/app/[locale]/layout.tsx
      to: next-intl
      via: "setRequestLocale + hasLocale + NextIntlClientProvider"
      pattern: "setRequestLocale\\("
---

<objective>
Continuation of 06-03a's locale topology work: author the new `viewer/app/[locale]/layout.tsx` (setRequestLocale + NextIntlClientProvider + hasLocale validation + html/body shell + TopNav + LanguageSwitcher chrome), refactor `viewer/app/layout.tsx` to a minimal root layout (drop `<html>` / `<body>` — locale-owned shell pattern per RESEARCH.md Pattern 2), and add the Next.js 16 async-params signature to all 9 page.tsx files now living under `viewer/app/[locale]/` (RESEARCH.md Pitfall 2 prevention — async-params miss causes silent locale fallback).

This plan deliberately separates "code-level refactor" from 06-03a's "directory rename" so the diff is reviewable as a coherent code change rather than mixed with rename noise.

Purpose: Complete I18N-02 — locale-scoped layout + async params plumbing.
Output: 14 URLs (7 routes × 2 locales) addressable; bare `/dashboard` 308-redirects to `/en/dashboard`; verifier check_i18n_02 flips fully GREEN.
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
@viewer/app/[locale]/page.tsx
@viewer/app/[locale]/dashboard/page.tsx
@viewer/i18n/routing.ts
@viewer/proxy.ts
@viewer/components/LanguageSwitcher.tsx

<interfaces>
<!-- From RESEARCH.md Pattern 2 — the exact LocaleLayout signature -->
export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{locale: string}>;  // Next.js 16 async-params
}): Promise<React.ReactElement>

<!-- From RESEARCH.md Pattern 2 — every moved page signature -->
export default async function FooPage({
  params,
}: {
  params: Promise<{locale: 'en' | 'ka'}>;
}): Promise<React.ReactElement>

<!-- For the nested dynamic route -->
export default async function HypothesisDetailPage({
  params,
}: {
  params: Promise<{locale: 'en' | 'ka'; id: string}>;
}): Promise<React.ReactElement>

<!-- From CONTEXT.md D-03 — landing in 06-04 -->
export function displayField(field: BilingualField, locale: 'en' | 'ka'): string;
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Author viewer/app/[locale]/layout.tsx with setRequestLocale + NextIntlClientProvider + hasLocale validation; refactor viewer/app/layout.tsx to a minimal root layout</name>
  <files>viewer/app/[locale]/layout.tsx, viewer/app/layout.tsx</files>
  <read_first>
    - viewer/app/layout.tsx (current — contains html/body, font, header, TopNav, BrainPanel; we move locale-aware chrome under [locale]/layout.tsx)
    - .planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-RESEARCH.md (Pattern 2 — exact LocaleLayout body, plus the generateStaticParams snippet)
    - viewer/i18n/routing.ts (06-01 — exports `routing.locales`)
    - viewer/components/LanguageSwitcher.tsx (to be mounted in the new layout)
  </read_first>
  <action>
    (a) Create `viewer/app/[locale]/layout.tsx`. Copy the layout body verbatim from 06-RESEARCH.md Pattern 2 ("Locale-segmented layout"), with these specifics:
        - imports: `notFound` from 'next/navigation'; `NextIntlClientProvider, hasLocale` from 'next-intl'; `setRequestLocale` from 'next-intl/server'; `routing` from '@/i18n/routing'; `TopNav` from '@/components/layout/TopNav'; `BrainPanel` from '@/components/layout/BrainPanel'; `LanguageSwitcher` from '@/components/LanguageSwitcher'; `Inter` from 'next/font/google'; CSS import from '../globals.css'.
        - export `generateStaticParams()` returning `routing.locales.map((locale) => ({locale}))`.
        - signature: `export default async function LocaleLayout({children, params}: {children: React.ReactNode; params: Promise<{locale: string}>;})`.
        - body: `const {locale} = await params; if (!hasLocale(routing.locales, locale)) notFound(); setRequestLocale(locale);` then return the JSX shell with `<html lang={locale} className={...}>`, `<body>`, `<header><TopNav /><LanguageSwitcher /></header>`, `<NextIntlClientProvider>...</NextIntlClientProvider>` wrapping the main+aside.
        - Move the existing html/body/font wiring from viewer/app/layout.tsx into this file (so `<html lang={locale}>` is correct per RESEARCH.md Pattern 2 note).

    (b) Refactor `viewer/app/layout.tsx` to a minimal root layout that does NOT render `<html>` or `<body>` (those move to [locale]/layout.tsx). Keep `export const metadata`. Body becomes: `export default function RootLayout({children}: {children: React.ReactNode}) { return children; }` — Next.js requires a root layout to exist but a child layout may own the document shell. (Alternative if Next.js 16 complains: keep `<html lang="en">` here as a static SEO fallback, and DROP the `<html>` from [locale]/layout.tsx. Decision: prefer the locale-owned `<html lang={locale}>` because it is correct for accessibility/SEO; the root layout returns just `{children}`.)

    (c) Tailwind 4 / postcss config: confirm the move does not break `viewer/app/globals.css` — its import path moves from `viewer/app/layout.tsx` to `viewer/app/[locale]/layout.tsx` as `'../globals.css'`.

    (d) The existing top-level `<header><TopNav /></header>` chrome is now under [locale]/layout.tsx; mount the LanguageSwitcher inside that header. Layout updates that affect TopNav itself (locale-aware Link conversion) land in 06-05b; this task only mounts the switcher.
  </action>
  <acceptance_criteria>
    - File `viewer/app/[locale]/layout.tsx` exists.
    - It contains: `setRequestLocale`, `hasLocale(routing.locales`, `notFound()`, `generateStaticParams`, `NextIntlClientProvider`, `<LanguageSwitcher`, `params: Promise<{locale`, `await params`.
    - File `viewer/app/layout.tsx` no longer contains `<html` or `<body` tags (locale-owned shell pattern).
    - File `viewer/app/layout.tsx` still exports `metadata` and `RootLayout` default.
    - No `import 'next-intl'` appears in `viewer/app/layout.tsx` (root layout is locale-agnostic).
    - `cd viewer && npx tsc --noEmit -p tsconfig.json` exits 0.
  </acceptance_criteria>
  <verify>
    <automated>grep -q "setRequestLocale" "viewer/app/[locale]/layout.tsx" && grep -q "hasLocale(routing.locales" "viewer/app/[locale]/layout.tsx" && ! grep -q "<html" viewer/app/layout.tsx</automated>
  </verify>
  <done>Locale-scoped layout exists with setRequestLocale + provider + switcher; root layout reduced to children pass-through.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Add Next.js 16 async-params signature + setRequestLocale call to all 9 moved page.tsx files (RESEARCH.md Pitfall 2 prevention)</name>
  <files>viewer/app/[locale]/page.tsx, viewer/app/[locale]/dashboard/page.tsx, viewer/app/[locale]/timeline/page.tsx, viewer/app/[locale]/papers/page.tsx, viewer/app/[locale]/therapies/page.tsx, viewer/app/[locale]/hypotheses/page.tsx, viewer/app/[locale]/hypotheses/[id]/page.tsx, viewer/app/[locale]/today/page.tsx, viewer/app/[locale]/knowledge/page.tsx</files>
  <read_first>
    - .planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-RESEARCH.md (Pattern 2 last block — exact TimelinePage shape; Pitfall 2 — async-params miss causes silent locale fallback)
    - viewer/app/[locale]/dashboard/page.tsx (post-06-03a — current signature has no `params`; we add one)
    - viewer/app/[locale]/hypotheses/[id]/page.tsx (nested dynamic — params now carries BOTH locale and id)
  </read_first>
  <action>
    For each of the 9 family-facing page.tsx files (the root [locale]/page.tsx + 7 routes × page.tsx + the nested [locale]/hypotheses/[id]/page.tsx), update the default export:

    (a) For pages with ONLY `[locale]` in their path (8 of them: page.tsx, dashboard/page.tsx, timeline/page.tsx, papers/page.tsx, therapies/page.tsx, hypotheses/page.tsx, today/page.tsx, knowledge/page.tsx):

        export default async function FooPage({
          params,
        }: {
          params: Promise<{locale: 'en' | 'ka'}>;
        }) {
          const {locale} = await params;
          setRequestLocale(locale);
          /* existing body */
        }

        Add at the top: `import {setRequestLocale} from 'next-intl/server';`

    (b) For the nested dynamic route `[locale]/hypotheses/[id]/page.tsx`, the param shape is `Promise<{locale: 'en' | 'ka'; id: string}>`:

        export default async function HypothesisDetailPage({
          params,
        }: {
          params: Promise<{locale: 'en' | 'ka'; id: string}>;
        }) {
          const {locale, id} = await params;
          setRequestLocale(locale);
          /* existing body uses id */
        }

    (c) If a page previously took a sync `params` (the existing hypotheses/[id]/page.tsx may already), upgrade to the Promise shape per RESEARCH.md Pitfall 2 — Next.js 16 made `params` Promise-only.

    (d) Do NOT yet replace any string literal with `t('...')` calls — string extraction lands in 06-05b. Pages are still bilingual-unaware at the content level after this task; only the layout/params plumbing is in place.

    (e) Pages that currently are Server Components and use `getTranslations` — none yet, but for any page that imports `next-intl/server`, ensure `setRequestLocale(locale)` is called BEFORE `getTranslations`. This prevents the silent-dynamic-rendering warning from RESEARCH.md Pitfall 4.
  </action>
  <acceptance_criteria>
    - All 9 page.tsx files contain `params: Promise<{locale` substring.
    - All 9 page.tsx files contain `const {locale} = await params` substring.
    - All 9 page.tsx files contain `setRequestLocale(locale)`.
    - The nested dynamic file `viewer/app/[locale]/hypotheses/[id]/page.tsx` contains `id: string` in its params type.
    - `cd viewer && npx tsc --noEmit -p tsconfig.json` exits 0.
    - `cd viewer && npm run build` exits 0; build output includes `Generated /[locale]/dashboard`, `Generated /[locale]/timeline`, etc. (build log shows the 7 routes registered).
  </acceptance_criteria>
  <verify>
    <automated>for f in dashboard timeline papers therapies hypotheses today knowledge; do grep -q "params: Promise<{locale" "viewer/app/[locale]/$f/page.tsx" || { echo "MISS $f"; exit 1; }; done; grep -q "params: Promise<{locale" "viewer/app/[locale]/page.tsx" && grep -q "id: string" "viewer/app/[locale]/hypotheses/[id]/page.tsx"</automated>
  </verify>
  <done>All 9 page.tsx files take async params; setRequestLocale called on every page; viewer builds clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| family browser → viewer/app/[locale]/layout.tsx | locale URL param crosses untrusted-input boundary |
| viewer/ → external origins | FND-02 trust boundary lint — this plan adds no new fetch sites |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-06-LOCALE-INJECTION | Tampering | viewer/app/[locale]/layout.tsx | mitigate | `hasLocale(routing.locales, locale)` strict allow-list before any downstream use; `notFound()` on miss. RESEARCH.md V5 Input Validation. Task 1 acceptance grep confirms presence. |
| T-06-SILENT-FALLBACK | Information Disclosure | viewer/app/[locale]/**/page.tsx | mitigate | Pitfall 2 — async-params miss causes silent en fallback on /ka/* URLs. Task 2 enforces `params: Promise<{locale}>` signature on all 9 pages; `cd viewer && npx tsc --noEmit` catches misses at compile time. |
| T-06-FND-02 (carry-over) | Information Disclosure | viewer/ remote-origin fetches | mitigate | This plan adds NO new fetch call sites; existing FND-02 trust boundary lint regression continues to pass (covered by Phase 4/5 regression sweep in 06-13). |
</threat_model>

<verification>
- viewer/app/[locale]/layout.tsx exists with required imports and setRequestLocale
- viewer/app/layout.tsx no longer owns <html>/<body>
- All 9 page.tsx files use async params + setRequestLocale
- `cd viewer && npm run build` exits 0
- Build output lists 7 routes under `/[locale]/...`
- TypeScript compiles cleanly
- `python -m scripts.verify_phase6 --mode code-complete --gate I18N-02` PASSES (the file-presence half flipped GREEN in 06-03a; this plan completes the layout/params half)
</verification>

<success_criteria>
- 14 URLs (7 routes × 2 locales) addressable; bare `/dashboard` 308-redirects to `/en/dashboard`
- I18N-02 verifier check fully GREEN
- No regression in api/audit/brain routes (verifier check_i18n_11 spawns verify_phase4/5 in 06-13)
</success_criteria>

<output>
Create `.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-03b-SUMMARY.md` when done. Record:
- 9 page.tsx files updated with async-params signature
- Layout-shell ownership decision (locale-owned `<html lang={locale}>` preferred; root layout returns just `{children}`)
- Any TS compile fix-ups required
- Confirmation that viewer/app/[locale]/layout.tsx mounts LanguageSwitcher (consumed by 06-04 Task 3)
</output>
