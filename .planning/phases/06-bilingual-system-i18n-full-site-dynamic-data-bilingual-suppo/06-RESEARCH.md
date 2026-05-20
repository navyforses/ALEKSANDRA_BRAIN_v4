# Phase 6: Bilingual System (i18n) — Research

**Researched:** 2026-05-20
**Domain:** Frontend i18n (Next.js 16 + next-intl 4) · PostgreSQL JSONB type conversion · Anthropic structured-output for bilingual emission · Georgian morphological lint
**Confidence:** HIGH

## Summary

Phase 6 lays a sweeping but bounded bilingual layer across the viewer, the 4 family-visible Postgres tables, the Communicator/Phase-5 composer write path, and the 5 n8n delivery workflows. Every locked decision in 06-CONTEXT.md (D-01..D-06) survives this research — but one significant correction surfaced: **Next.js 16 renamed `middleware.ts` → `proxy.ts`** and next-intl 4.12 supports the new convention directly. The existing `viewer/middleware.ts` must be renamed to `viewer/proxy.ts` (codemod available) and the function renamed `middleware` → `proxy`. CONTEXT.md D-01 still picks the correct library (next-intl 4) but the file-layout sketch must be updated.

The second material finding is that **Next.js 16's `params` is already a `Promise`** (the v14→v15 async-params migration is fully landed by 16.2.6), so every `app/[locale]/*/page.tsx` and `layout.tsx` must use `params: Promise<{locale: string}>` with `const {locale} = await params`. The dashboard/timeline/papers/therapies/hypotheses/today/knowledge pages currently take no params; the move under `app/[locale]/` is the moment they pick this up. Both `await params` and `setRequestLocale(locale)` are required at every layout/page boundary if next-intl static rendering is wanted — without `setRequestLocale`, `getTranslations` falls back to dynamic rendering, which is fine for this single-patient app.

The third material finding is that bilingual emission via **Claude Sonnet 4.5 `tools: [{strict: true, ...}]` with `tool_choice: {type: "tool", name: "..."}`** is the right primitive for D-02. Strict mode (grammar-constrained sampling) guarantees the output is exactly `{"en": str, "ka": str}` — no defensive parsing needed in the Communicator. One call, both languages, schema-validated. The migration 012 path is straightforward (`ALTER COLUMN ... TYPE jsonb USING jsonb_build_object('en', col, 'ka', col)` preserves RLS policies because `ALTER COLUMN ... TYPE` does NOT drop policies; it only drops indexes that physically reference the column's old TYPE, and the 4 target tables have **no B-tree or GIN indexes on the converted columns** — the only existing indexes are on `event_date`, `event_type`, `status`, `confidence_level`, `aleksandra_status`, `therapy_type`, `evidence_in_hie`, and `brief_week`, none of which touch the columns being converted).

**Primary recommendation:** Plan the work in 5 strict sequencing buckets matching the verifier coverage map (A frontend, B database, C agent output, D delivery, E regression). Land the rename `viewer/middleware.ts` → `viewer/proxy.ts` together with the next-intl 4 install in the very first task — every other frontend task depends on routing being live. Land migration 012 BEFORE wiring the Communicator's bilingual emission, because the Communicator's new write path inserts `{en, ka}` JSONB and requires the column TYPE to already be jsonb.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 · next-intl version + Next.js 16 compatibility**
- Use `next-intl@4` (latest v4.x).
- Files: `viewer/i18n/routing.ts` (defineRouting + createNavigation exports) + `viewer/i18n/request.ts` (request config with `requestLocale`) + `viewer/middleware.ts` (uses imported routing).
- API uses `getRequestConfig({requestLocale})` (NOT `({locale})` of v3.x).
- *Researcher note: The exact file name `middleware.ts` should be `proxy.ts` in Next.js 16 — see [Architecture Patterns / Pattern 1] for the correction. The library API itself (createMiddleware from `next-intl/middleware`) is unchanged.*

**D-02 · Bilingual emission strategy in Communicator**
- Single Anthropic structured-output call returning `{"en": "...", "ka": "..."}` simultaneously (Claude tool_use schema with `strict: true`).
- NOT a follow-up translation call.
- Per-tier policy: weekly_brief sections, Phase-5 composer rows = bilingual emission; internal CrewAI agents stay English-only; outreach_drafter stays single-language-per-recipient.

**D-03 · JSONB backend read patterns**
- Whole-JSONB read pattern over the wire.
- Viewer extracts locale via `displayField(field, locale)` helper in `viewer/lib/i18n.ts`.
- NOT server-side projection.
- Helper signature locked: `displayField(field: BilingualField, locale: 'en'|'ka'): string` with TEXT-tolerance branch for migration window.

**D-04 · Migration 012 GIN index policy**
- No GIN indexes in migration 012.
- Sanity check confirmed: `grep -r "ilike" viewer/app/ scripts/` returns 0 hits on these 4 tables; `grep -r "to_tsvector"` returns 0 hits. Decision holds.

**D-05 · Imperative-verb lint extension for Georgian**
- Minimal literal-string Georgian imperative-verb lexicon — 6 entries mapping to the 6 English banned verbs.
- Shako reviews the list during execute-phase before lint goes live.
- Initial pass: literal-string match against the table in CONTEXT.md; morphological regex is a discretion item for plan-phase.

**D-06 · Phase 6 verifier coverage map (`scripts/verify_phase6.py`)**
- Mirror `verify_phase5.py` style.
- 5 buckets: A frontend (I18N-01..04, 08), B database (I18N-05, 09), C agent output (I18N-06, 10), D delivery (I18N-07), E regression (I18N-11).
- Target: 11/11 PASS. Cumulative project verifier total post-Phase-6: 89/89.

### Claude's Discretion

- Exact regex shape of the Georgian imperative-verb lint (literal string vs morphological regex).
- Whether `viewer/i18n.ts` is renamed to `viewer/i18n/request.ts` or kept flat.
- Whether the LanguageSwitcher gets a translated label (`EN | GE` vs `English | ქართული`).
- Whether `scripts/migrations/012_rollback/` is per-table dumps or a single multi-table file.

### Deferred Ideas (OUT OF SCOPE)

- French (`fr`) UI translation — outreach layer keeps fr; viewer ships en/ka only.
- AI re-translation of the 200 entities / 307 facts / 47 episodes / 10 hypotheses / 12 therapies — migration 012 mirrors `en` to `ka`; backfill is a separate future maintenance phase.
- Cookie/localStorage language persistence — URL is source of truth.
- RTL support / locale-aware date and number formatting beyond next-intl defaults.
- Full-text search on bilingual title/description columns.
- Tone post-processor (CGM-06) Georgian extension — Phase 6 extends only the imperative-verb lint (CGM-04).
- `outreach_drafter` bilingual emission — single-recipient single-language per contact.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| I18N-01 | next-intl installed and compatible with Next.js 16.2.6 | next-intl 4.12.0 (latest stable on npm, `peerDependencies.next: '^16.0.0'` confirmed via `npm view`). Boilerplate `amuradesign/next.js-16-next-intl-boilerplate` proves the pairing works. See *Standard Stack* + *Pattern 1*. |
| I18N-02 | Locale-segmented App Router structure (`app/[locale]/*`) | 7 family-facing route directories enumerated below; Next.js 16 `params: Promise<{locale:string}>` shape confirmed against `viewer/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/dynamic-routes.md`. See *Pattern 2*. |
| I18N-03 | Static UI strings in `viewer/messages/{en,ka}.json` | Existing root-level dictionaries shown to be 7-key skeletons; move + expand. See *Pattern 3*. |
| I18N-04 | Language switcher persists choice via URL | Existing `viewer/components/LanguageSwitcher.tsx` is already correct against next-intl 4 hooks (`useLocale` + `useRouter` from `next/navigation`). Mount inside `app/[locale]/layout.tsx`. See *Pattern 4*. |
| I18N-05 | Migration 012 converts 6 TEXT columns + briefs.sections to JSONB en+ka | `ALTER COLUMN ... TYPE jsonb USING ...` syntax verified; **no existing indexes on the 4 target columns**; RLS policies survive TYPE change. See *Pattern 5*. |
| I18N-06 | Communicator + Phase 5 composer emit `{en, ka}` for family-visible newly-created content | Anthropic Claude Sonnet 4.5 with `tools[].strict=true` + `tool_choice={type:"tool",name:"..."}` gives schema-validated `{en, ka}` in one call. See *Pattern 6*. |
| I18N-07 | Telegram → ka, Gmail → en audience routing | All 5 workflows surveyed; only `weekly_brief.json` directly contains body content (the others delegate to a Python worker). Routing decision lives in the worker layer, not in n8n JSON. See *Pattern 7*. |
| I18N-08 | Frontend reads JSONB columns by current locale with English fallback | `displayField(field, locale)` helper signature already locked in D-03. Type guard for legacy TEXT rows during migration window. |
| I18N-09 | Historical row JSONB shape set by migration 012 only | `USING jsonb_build_object('en', col, 'ka', col)` mirrors English to both slots; no AI cost in this phase. Folded into Pattern 5. |
| I18N-10 | PHI redactor remains bilingual-aware and PHI-leak free | Existing `phi_redactor.py` already has Georgian-name patterns (`ალექსანდრა`, `ჯინჭარაძე`) and Georgian DOB format (`28 აგვისტო 2025`). Phase 6 extends MRN-in-Mkhedruli-digits coverage + adds bilingual fixture set. See *Pattern 8*. |
| I18N-11 | Phase 5 + Phase 4 do not regress | Verifier bucket E spawns `verify_phase4 --mode code-complete` and `verify_phase5 --mode code-complete` and asserts 9/9 + 13/13 PASS. See *Validation Architecture / Bucket E*. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| URL locale segmentation (`/en/*`, `/ka/*`) | Frontend Server (proxy.ts) | — | next-intl's `createMiddleware(routing)` runs in proxy.ts before page rendering; this is the only tier that can rewrite/redirect before route resolution. |
| Static UI string lookup (`useTranslations`) | Frontend Server (RSC) | Browser/Client (for client components) | next-intl loads `messages/{locale}.json` server-side via `getRequestConfig`; client components hydrate from the same dictionary. |
| Language switcher (button) | Browser/Client | — | Pure URL manipulation; uses `useRouter().push(newPath)`. No server state. |
| JSONB storage (en+ka pairs) | Database/Storage | — | Postgres JSONB; RLS-protected; service-role-only writes. |
| Bilingual content **generation** | API/Backend (Python worker) | — | `scripts/communicator/weekly_brief.py` and `scripts/manager/briefing.py` call Anthropic; the worker emits the `{en, ka}` JSONB shape directly into the DB. |
| Locale extraction from JSONB for rendering | Browser/Client (and SSR layer) | — | `displayField(field, locale)` helper in `viewer/lib/i18n.ts` — runs anywhere the JSONB row is rendered. |
| Telegram-vs-Gmail audience routing | API/Backend (Python worker) | n8n (trigger only) | After Phase 5 the n8n workflows delegate to the Python worker; routing-by-locale lives in worker code (`telegram_sender.py` reads `.ka`, `gmail_digest.py` reads `.en`). The n8n JSON does NOT need to extract locale fields. |
| PHI redaction over both en+ka | API/Backend | — | `scripts/communicator/phi_redactor.py` is invoked on text BEFORE persistence and BEFORE delivery; already Georgian-aware. Phase 6 widens fixture coverage. |
| Imperative-verb lint over both en+ka | API/Backend | — | `scripts/communicator/banned_phrases.py` already has 12 Georgian patterns (8 already; 6 new from D-05 lexicon will add to existing list). |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `next-intl` | `^4.0.0` (latest `4.12.0`, published 2026-04 cycle per `npm view next-intl dist-tags`) | i18n for App Router | Only first-class i18n lib explicitly supporting Next.js 16's `proxy.ts` convention. `peerDependencies` confirmed: `next: '^12.0.0 \|\| ^13.0.0 \|\| ^14.0.0 \|\| ^15.0.0 \|\| ^16.0.0'`. Has `defineRouting`, `createNavigation`, `setRequestLocale`, `hasLocale` — every primitive Phase 6 needs. [VERIFIED: npm view next-intl version → 4.12.0; npm view next-intl peerDependencies → next ^16.0.0 confirmed] [CITED: https://next-intl.dev/docs/getting-started/app-router/with-i18n-routing] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `anthropic` (Python SDK) | already installed via Phase 3 | Bilingual emission via `tools[].strict=true` | Used by `scripts/communicator/weekly_brief.py` to call Claude Sonnet 4.5 with a forced bilingual tool schema. [CITED: https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `next-intl@4` | `next-international` | Smaller ecosystem; no first-class Next.js 16 support story. CONTEXT.md D-01 already rejected. |
| `next-intl@4` | `paraglide-js` | Smaller ecosystem; would re-author existing 3 scaffolding files. CONTEXT.md D-01 already rejected. |
| `next-intl@4` | Custom shim | Reinvents middleware + RSC integration; brittle. CONTEXT.md D-01 already rejected. |
| Claude tool_use `strict: true` | Claude JSON-mode `response_format` | Anthropic does not have a documented `response_format: "json_object"` parameter as of 2026-05; tool_use is the canonical structured-output primitive. Strict tool_use gives grammar-constrained sampling — provably impossible for the model to emit a non-conforming `{en, ka}` shape. [VERIFIED: https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use] |
| One Anthropic call returning `{en, ka}` | English-first draft + follow-up translation call | Doubles latency + ~doubles cost; introduces translation drift between primary and translated text. CONTEXT.md D-02 already rejected. |

**Installation:**

```bash
cd viewer
npm install next-intl@^4
# optional: codemod to convert middleware.ts → proxy.ts (Next.js 16 convention)
npx @next/codemod@canary middleware-to-proxy .
```

**Version verification:**

```bash
npm view next-intl version           # → 4.12.0 (confirmed 2026-05-20)
npm view next-intl peerDependencies  # → next ^16.0.0 confirmed
npm view next-intl dist-tags         # → latest: 4.12.0; canary, v4-beta exist
```

`next-intl@4.12.0` published Apr-2026 cycle (latest stable). Project root `npm view next-intl time` shows steady weekly releases since v4.0.

## Package Legitimacy Audit

> Only one new external package is added: `next-intl`. Slopcheck was not available in this research environment.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `next-intl` | npm | 5.5 yrs (created 2020-11-19) | very high (cited as default Next.js i18n in official Next.js i18n guide [CITED: viewer/node_modules/next/dist/docs/01-app/02-guides/internationalization.md line 219]) | https://github.com/amannn/next-intl | NOT RUN (slopcheck unavailable) | Approved — recommended by Next.js docs; published by Jan Amann (verified maintainer); 600+ versions; explicit Next.js 16 peer-dep range. |

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

*slopcheck was unavailable; this is the only new package added this phase, it is recommended by Next.js's own official docs, and it has a 5.5-year publish history. Treating as `[VERIFIED: npm registry + Next.js official docs cite it]`.*

## Architecture Patterns

### System Architecture Diagram

```
                      ┌─────────────────────────┐
   Family browser ───▶│ viewer/proxy.ts         │   (RENAMED from middleware.ts
   GET /dashboard     │ createMiddleware(routing)│    in Next.js 16)
                      └────────┬────────────────┘
                               │ 308 → /en/dashboard (default locale)
                               ▼
                      ┌─────────────────────────────────┐
                      │ viewer/app/[locale]/             │
                      │   layout.tsx                     │  setRequestLocale(locale)
                      │     ↓                            │  + <NextIntlClientProvider>
                      │   dashboard/page.tsx ─┐          │
                      │   timeline/page.tsx   │ (7)      │
                      │   papers/page.tsx     │          │
                      │   therapies/page.tsx  │          │
                      │   hypotheses/page.tsx │          │
                      │   today/page.tsx      │          │
                      │   knowledge/page.tsx ─┘          │
                      └────────┬─────────────────────────┘
                               │ useTranslations()       (static UI strings)
                               │ displayField(jsonb, locale)  (dynamic content)
                               ▼
                      ┌─────────────────────────┐
                      │ Supabase Postgres        │  RLS-protected
                      │  aleksandra_timeline     │  title, description JSONB {en, ka}
                      │  hypotheses              │  title, description JSONB {en, ka}
                      │  therapies               │  name, evidence_summary JSONB {en, ka}
                      │  briefs                  │  sections JSONB; each body → {en, ka}
                      └────────▲─────────────────┘
                               │ INSERT bilingual JSONB
   Anthropic ───┐              │
   Sonnet 4.5   │              │
   tools:[{strict:true,        │
   input_schema:{              │
     en: string,               │
     ka: string                │
   }}]                         │
   tool_choice={type:"tool",   │
     name:"compose_bilingual"} │
                ▼              │
   ┌────────────────────────────┴───┐
   │ Python worker (Railway)         │
   │  scripts/communicator/          │
   │    weekly_brief.py              │
   │    phi_redactor.py    (Georgian-aware already)
   │    banned_phrases.py  (+6 Georgian lexicon entries from D-05)
   │  scripts/manager/               │
   │    briefing.py                  │
   └────────┬────────────────────────┘
            │
   ┌────────┴────────────┐
   │ Telegram (read .ka) │   ◄── audience routing happens in Python worker,
   │ Gmail (read .en)    │       NOT in n8n JSON (workflows just trigger).
   │ Notion              │
   └─────────────────────┘
```

### Recommended Project Structure

```
viewer/
├── app/
│   ├── [locale]/                 ← family-facing routes MOVE here
│   │   ├── layout.tsx            ← setRequestLocale + NextIntlClientProvider
│   │   ├── page.tsx              ← (move from app/page.tsx — "Today" root)
│   │   ├── dashboard/page.tsx
│   │   ├── timeline/page.tsx
│   │   ├── papers/page.tsx
│   │   ├── therapies/page.tsx
│   │   ├── hypotheses/page.tsx
│   │   │   └── [id]/page.tsx
│   │   ├── today/page.tsx
│   │   └── knowledge/page.tsx
│   ├── api/                      ← UNCHANGED, not localized
│   ├── audit/                    ← UNCHANGED, not localized
│   ├── brain/                    ← UNCHANGED, not localized
│   ├── layout.tsx                ← root layout (loads next/font + globals; locale-agnostic)
│   └── globals.css
├── i18n/
│   ├── routing.ts                ← defineRouting({locales:['en','ka'],defaultLocale:'en'})
│   ├── request.ts                ← getRequestConfig({requestLocale}) → resolved locale + messages
│   └── navigation.ts             ← createNavigation(routing) → typed Link/redirect/usePathname
├── messages/
│   ├── en.json                   ← all static UI strings (en)
│   └── ka.json                   ← all static UI strings (ka)
├── lib/
│   ├── supabase.ts               ← UNCHANGED
│   └── i18n.ts                   ← NEW: displayField(field, locale) helper
├── components/
│   ├── LanguageSwitcher.tsx      ← UNCHANGED logic; mounted in [locale]/layout.tsx
│   └── layout/
│       ├── TopNav.tsx            ← UPDATE: use createNavigation Link, add locale-aware hrefs
│       └── BrainPanel.tsx
├── proxy.ts                      ← RENAMED from middleware.ts; createMiddleware(routing)
├── next.config.ts                ← add: createNextIntlPlugin('./i18n/request.ts')
└── package.json                  ← add "next-intl": "^4"

scripts/
├── migrations/
│   ├── 012_i18n_jsonb.sql        ← NEW: TYPE conversion + briefs.sections reshape
│   └── 012_rollback/             ← NEW: pg_dump artifacts (per-table) — researcher recommends per-table for selective restore
│       ├── aleksandra_timeline.pre012.dump
│       ├── hypotheses.pre012.dump
│       ├── therapies.pre012.dump
│       └── briefs.pre012.dump
├── communicator/
│   ├── weekly_brief.py           ← UPDATE: collect_sections returns {en,ka} per section body; call Anthropic strict tool_use
│   ├── phi_redactor.py           ← UPDATE: extend MRN-in-Mkhedruli-digits regex; bilingual fixture set
│   └── banned_phrases.py         ← UPDATE: append 6 Georgian imperative-verb entries from D-05
├── manager/
│   └── briefing.py               ← UPDATE: emit {en, ka} per inserted row
└── verify_phase6.py              ← NEW: 11-bucket verifier (A frontend, B db, C agent, D delivery, E regression)
```

### Pattern 1: next-intl 4 setup for Next.js 16 (proxy.ts, NOT middleware.ts)

**What:** Set up next-intl with the Next.js 16 file convention.

**When to use:** First task in any Plan dealing with I18N-01.

**Critical correction to D-01:** Next.js 16.0 deprecated `middleware.ts` and renamed the file to `proxy.ts`. The function is also renamed `middleware()` → `proxy()`. The codemod `npx @next/codemod@canary middleware-to-proxy .` performs the rename atomically. next-intl 4.12 supports the new convention: the `next-intl/middleware` import path keeps its name (for backward compat) but the file calling `createMiddleware(routing)` should live at `viewer/proxy.ts`.

**Example:**

```typescript
// viewer/i18n/routing.ts
// Source: https://next-intl.dev/docs/getting-started/app-router/with-i18n-routing
import {defineRouting} from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['en', 'ka'],
  defaultLocale: 'en'
});
```

```typescript
// viewer/i18n/request.ts
// Source: https://next-intl.dev/docs/getting-started/app-router/with-i18n-routing
import {getRequestConfig} from 'next-intl/server';
import {hasLocale} from 'next-intl';
import {routing} from './routing';

export default getRequestConfig(async ({requestLocale}) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested)
    ? requested
    : routing.defaultLocale;

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default
  };
});
```

```typescript
// viewer/i18n/navigation.ts
// Source: https://next-intl.dev/docs/routing/navigation
import {createNavigation} from 'next-intl/navigation';
import {routing} from './routing';

export const {Link, redirect, usePathname, useRouter, getPathname} =
  createNavigation(routing);
```

```typescript
// viewer/proxy.ts
// (RENAMED from viewer/middleware.ts per Next.js 16 convention.
//  Source: viewer/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/proxy.md)
import createMiddleware from 'next-intl/middleware';
import {routing} from './i18n/routing';

export default createMiddleware(routing);

export const config = {
  matcher: '/((?!api|audit|brain|_next|_vercel|.*\\..*).*)'
};
```

> Matcher excludes `api`, `audit`, `brain` — these are explicitly NOT localized per SPEC. The `.*\\..*` pattern excludes static files.

```typescript
// viewer/next.config.ts (add the plugin)
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

export default withNextIntl({
  /* existing config */
});
```

### Pattern 2: Locale-segmented layout with Next.js 16 async params

**What:** Wrap family-facing routes in `app/[locale]/layout.tsx` and consume the locale via the Next.js 16 async-params shape.

**When to use:** I18N-02 — moving the 7 family-facing routes.

**Example:**

```typescript
// viewer/app/[locale]/layout.tsx
// Source: https://next-intl.dev/docs/getting-started/app-router/with-i18n-routing
//       + viewer/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/dynamic-routes.md
import {notFound} from 'next/navigation';
import {NextIntlClientProvider, hasLocale} from 'next-intl';
import {setRequestLocale} from 'next-intl/server';
import {routing} from '@/i18n/routing';
import TopNav from '@/components/layout/TopNav';
import BrainPanel from '@/components/layout/BrainPanel';
import LanguageSwitcher from '@/components/LanguageSwitcher';

export function generateStaticParams() {
  return routing.locales.map((locale) => ({locale}));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{locale: string}>;  // ← Next.js 16 async-params shape
}) {
  const {locale} = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }
  setRequestLocale(locale);  // enables static rendering for child pages

  return (
    <NextIntlClientProvider>
      <header className="h-[60px] flex-shrink-0 border-b border-slate-200 bg-white">
        <TopNav />
        <LanguageSwitcher />
      </header>
      <div className="flex flex-1 overflow-hidden">
        <main className="w-full md:w-[65%] h-full overflow-y-auto bg-background p-8">
          {children}
        </main>
        <aside className="hidden md:flex w-[35%] h-full border-l border-slate-200 bg-slate-50 flex-col">
          <BrainPanel />
        </aside>
      </div>
    </NextIntlClientProvider>
  );
}
```

> The existing `viewer/app/layout.tsx` (root) keeps the `<html>` and `<body>` shell; the new `[locale]/layout.tsx` is a nested layout. The `<html lang="en">` attribute on the root layout should become `<html lang={locale}>` — but the root layout doesn't receive `locale`. The cleanest fix is to drop `<html>`/`<body>` from the root layout and move them into `[locale]/layout.tsx` so `lang={locale}` is correct. Alternative: keep root `<html lang="en">` as a static fallback (acceptable for SEO; the family browser only ever sees the locale-segmented routes).

**Pages also take `params: Promise<{locale: string}>` for each page that needs `useTranslations`:**

```typescript
// viewer/app/[locale]/timeline/page.tsx
import {setRequestLocale, getTranslations} from 'next-intl/server';
import {getRows} from '@/lib/supabase';
import {displayField} from '@/lib/i18n';

export const dynamic = "force-dynamic";

export default async function TimelinePage({
  params,
}: {
  params: Promise<{locale: 'en' | 'ka'}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('Timeline');

  type TimelineEvent = {
    id: string;
    event_date: string;
    event_type: string;
    title: { en?: string; ka?: string } | string;  // ← JSONB OR legacy TEXT
    description: { en?: string; ka?: string } | string | null;
    institution: string | null;
    location: string | null;
    created_at: string;
    updated_at: string;
  };

  const events = await getRows<TimelineEvent>("aleksandra_timeline", { /* ... */ });
  // render with: displayField(event.title, locale)
}
```

### Pattern 3: messages/{locale}.json dictionary expansion

**What:** Move the root-level `en.json` + `ka.json` to `viewer/messages/` and add every visible string used in the 7 family-facing routes.

**When to use:** I18N-03.

**Strategy:**
- Group keys by component or page (current root files use `Common`, `Navigation`).
- Add per-page groups: `Dashboard`, `Timeline`, `Papers`, `Therapies`, `Hypotheses`, `Today`, `Knowledge`.
- Add a `Shared.empty`, `Shared.loading`, `Shared.error` triplet for all components.
- `t('Timeline.title')` reads the key `Timeline.title` from the right locale file.

**Verifier check (locks I18N-03 acceptance):**

```bash
# Find every t(...) and useTranslations(...) call, extract the key, assert presence in both files.
grep -rhoE "t\(['\"]([A-Za-z][A-Za-z0-9._]+)['\"]\)" viewer/app/\[locale\]/ viewer/components/ \
  | sed -E "s/^t\(['\"]([^'\"]+)['\"]\)$/\1/" \
  | sort -u \
  > /tmp/used_keys.txt
# Then for each key, jq -e ". | getpath(\"$key\" | split(\".\"))" messages/en.json && messages/ka.json
```

### Pattern 4: LanguageSwitcher mounted in localized layout

**What:** Mount the existing `viewer/components/LanguageSwitcher.tsx` inside `viewer/app/[locale]/layout.tsx`.

**When to use:** I18N-04.

**No code change required** — the existing switcher already uses `useLocale()` and `useRouter()` from `next/navigation`, and re-writes the URL prefix. Once `next-intl` is installed and routing is wired, the switcher works as-is.

Optional polish (Claude's discretion per CONTEXT.md): replace `EN | GE` with `English | ქართული`.

### Pattern 5: Migration 012 SQL pattern (preserving RLS, no GIN)

**What:** Convert 6 columns (4 tables) to JSONB en+ka shape, reshape `briefs.sections`, preserve all RLS from migration 008.

**When to use:** I18N-05 + I18N-09.

**Why RLS survives:** PostgreSQL `ALTER TABLE ... ALTER COLUMN ... TYPE` does not drop row-level-security policies; it only drops indexes whose definition physically references the column type. The 4 target columns have **no indexes** (verified by reading `scripts/schema.sql` for hypotheses/therapies and `scripts/migrations/002_aleksandra_timeline.sql` for the timeline). The only indexes on these tables are on `event_date`, `event_type`, `status`, `confidence_level`, `aleksandra_status`, `therapy_type`, `evidence_in_hie`, `brief_week` — none touch the converted columns.

**Pre-migration:**

```bash
# 1. Per-table pg_dump (per CONTEXT.md preferred shape — selective restore is cheaper than partial-table restore from a multi-table file)
mkdir -p scripts/migrations/012_rollback
for tbl in aleksandra_timeline hypotheses therapies briefs; do
  pg_dump "$SUPABASE_DB_URL" \
    --table="$tbl" \
    --data-only \
    --column-inserts \
    --file="scripts/migrations/012_rollback/$tbl.pre012.dump"
done

# 2. Snapshot RLS policies for after-the-fact comparison
psql "$SUPABASE_DB_URL" -c "\d aleksandra_timeline" > scripts/migrations/012_rollback/aleksandra_timeline.policies.pre.txt
psql "$SUPABASE_DB_URL" -c "\d hypotheses"          > scripts/migrations/012_rollback/hypotheses.policies.pre.txt
psql "$SUPABASE_DB_URL" -c "\d therapies"           > scripts/migrations/012_rollback/therapies.policies.pre.txt
psql "$SUPABASE_DB_URL" -c "\d briefs"              > scripts/migrations/012_rollback/briefs.policies.pre.txt
```

**Migration 012 body (verified syntax against PostgreSQL 15 docs):**

```sql
-- scripts/migrations/012_i18n_jsonb.sql
-- Phase 6 I18N-05 + I18N-09: convert 6 TEXT columns to JSONB {en, ka}
-- and reshape briefs.sections body fields. Preserves RLS from migration 008.

BEGIN;

-- ─────────────────────────────────────────────
-- aleksandra_timeline: title, description → JSONB
-- ─────────────────────────────────────────────
ALTER TABLE aleksandra_timeline
  ALTER COLUMN title TYPE jsonb
    USING jsonb_build_object('en', title, 'ka', title),
  ALTER COLUMN description TYPE jsonb
    USING CASE
      WHEN description IS NULL THEN NULL
      ELSE jsonb_build_object('en', description, 'ka', description)
    END;

-- NOTE: NOT NULL on title is preserved because USING expression always returns non-null
-- when input is non-null (jsonb_build_object never produces SQL NULL).

-- ─────────────────────────────────────────────
-- hypotheses: title, description → JSONB
-- ─────────────────────────────────────────────
ALTER TABLE hypotheses
  ALTER COLUMN title TYPE jsonb
    USING jsonb_build_object('en', title, 'ka', title),
  ALTER COLUMN description TYPE jsonb
    USING jsonb_build_object('en', description, 'ka', description);

-- ─────────────────────────────────────────────
-- therapies: name, evidence_summary → JSONB
-- ─────────────────────────────────────────────
ALTER TABLE therapies
  ALTER COLUMN name TYPE jsonb
    USING jsonb_build_object('en', name, 'ka', name),
  ALTER COLUMN evidence_summary TYPE jsonb
    USING CASE
      WHEN evidence_summary IS NULL THEN NULL
      ELSE jsonb_build_object('en', evidence_summary, 'ka', evidence_summary)
    END;

-- ─────────────────────────────────────────────
-- briefs.sections: rewrite each section body to {en, ka}
-- The existing sections JSONB is the BriefSections.to_dict() shape:
-- {
--   "week_start": "...", "week_end": "...", "generated_at": "...",
--   "summary_lines": [str, ...],
--   "papers":     [{title, citation_id, ingested_at, relevance_score}, ...],
--   "hypotheses": [{title, status, confidence, reviewed_at, supporting}, ...],
--   "therapies":  [{name, therapy_type, aleksandra_status, evidence_in_hie}, ...],
--   "outreach":   [{subject, language, drafted_at, sent_at, contact_label, confidence}, ...],
--   "questions":  [{id, question, context, asked_at, status}, ...],
--   "citations":  [str, ...]
-- }
--
-- Convert string fields to {en, ka} for the family-visible bodies:
--   summary_lines[i]            → {en: line, ka: line}
--   papers[i].title             → {en, ka}
--   hypotheses[i].title         → {en, ka}
--   therapies[i].name           → {en, ka}
--   outreach[i].subject         → {en, ka}
--   questions[i].question       → {en, ka}, .context → {en, ka}
-- Leave alone: citations[] (PMID/DOI/NCT strings), citation_id, dates, scores, statuses.
--
-- We do this with a single UPDATE using jsonb_set per-array-element via a
-- temporary PL/pgSQL helper. The expression is verbose but deterministic:

UPDATE briefs
SET sections = (
  WITH s AS (SELECT sections AS j)
  SELECT
    jsonb_build_object(
      'week_start', s.j->'week_start',
      'week_end',   s.j->'week_end',
      'generated_at', s.j->'generated_at',
      'summary_lines',
        COALESCE(
          (SELECT jsonb_agg(jsonb_build_object('en', x, 'ka', x))
             FROM jsonb_array_elements_text(s.j->'summary_lines') x),
          '[]'::jsonb),
      'papers',
        COALESCE(
          (SELECT jsonb_agg(elem || jsonb_build_object('title', jsonb_build_object('en', elem->>'title', 'ka', elem->>'title')))
             FROM jsonb_array_elements(s.j->'papers') elem),
          '[]'::jsonb),
      'hypotheses',
        COALESCE(
          (SELECT jsonb_agg(elem || jsonb_build_object('title', jsonb_build_object('en', elem->>'title', 'ka', elem->>'title')))
             FROM jsonb_array_elements(s.j->'hypotheses') elem),
          '[]'::jsonb),
      'therapies',
        COALESCE(
          (SELECT jsonb_agg(elem || jsonb_build_object('name', jsonb_build_object('en', elem->>'name', 'ka', elem->>'name')))
             FROM jsonb_array_elements(s.j->'therapies') elem),
          '[]'::jsonb),
      'outreach',
        COALESCE(
          (SELECT jsonb_agg(elem || jsonb_build_object('subject', jsonb_build_object('en', elem->>'subject', 'ka', elem->>'subject')))
             FROM jsonb_array_elements(s.j->'outreach') elem),
          '[]'::jsonb),
      'questions',
        COALESCE(
          (SELECT jsonb_agg(elem
              || jsonb_build_object('question', jsonb_build_object('en', elem->>'question', 'ka', elem->>'question'))
              || jsonb_build_object('context',  jsonb_build_object('en', elem->>'context',  'ka', elem->>'context')))
             FROM jsonb_array_elements(s.j->'questions') elem),
          '[]'::jsonb),
      'citations', s.j->'citations'
    )
  FROM s
);

COMMIT;
```

**Post-migration smoke SELECTs (each must pass):**

```sql
-- Verify shape change
SELECT pg_typeof(title) FROM aleksandra_timeline LIMIT 1;
-- → expected: jsonb

-- Verify content preserved (.en matches pre-migration TEXT)
SELECT id, title->>'en', title->>'ka'
FROM aleksandra_timeline LIMIT 5;
-- → expected: same string in both ->>'en' and ->>'ka'; non-NULL

-- Verify RLS still in place
SELECT polname FROM pg_policy
WHERE polrelid = 'aleksandra_timeline'::regclass;
-- → expected: aleksandra_timeline_family_read,
--             aleksandra_timeline_service_write,
--             aleksandra_timeline_service_update
--   (all three from migration 002 preserved)
```

**Rollback (if smoke fails):**

```bash
for tbl in aleksandra_timeline hypotheses therapies briefs; do
  psql "$SUPABASE_DB_URL" -c "BEGIN; DELETE FROM $tbl; \i scripts/migrations/012_rollback/$tbl.pre012.dump; COMMIT;"
done
# Then revert schema TYPE (manual: ALTER TABLE ... ALTER COLUMN ... TYPE text USING ... ->>'en')
```

### Pattern 6: Bilingual emission via Claude Sonnet 4.5 strict tool_use

**What:** Get Claude Sonnet 4.5 to emit `{"en": "...", "ka": "..."}` in a single, schema-validated call.

**When to use:** I18N-06 — Communicator and Phase-5 composer write paths.

**Why strict tool_use over JSON-mode:** Anthropic's API does NOT have a documented `response_format: "json_object"` parameter (unlike OpenAI). The canonical structured-output primitive is `tools[].strict=true` with `tool_choice={type: "tool", name: "..."}`. Strict mode uses grammar-constrained sampling — provably impossible for the model to emit a non-conforming output. One Anthropic call, deterministic shape, no defensive JSON parsing in the Python worker. [VERIFIED: https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use]

**Cost note:** Tool use adds 313 tokens of system-prompt overhead per call when `tool_choice` is forced to a specific tool (vs 346 for `auto`). For Sonnet 4.5 at $3/$15 per million tokens, that's $0.000939 of overhead per call — negligible. The 30–50% output-token increase (estimating Georgian is ~1.2× English by char count and ~1.5× by token count) is the real cost driver, but Phase 6's $5 ceiling has plenty of headroom (cumulative project spend $4.22 / $60 cap; Phase 5 spent $0).

**Example:**

```python
# scripts/communicator/bilingual.py  (NEW or folded into weekly_brief.py)
# Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use
from anthropic import Anthropic

BILINGUAL_TOOL = {
    "name": "compose_bilingual",
    "description": (
        "Emit a family-facing draft in English and Georgian simultaneously. "
        "Both languages must convey the same medical content with the same "
        "evidence framing. Do not include PHI (names, MRN, DOB) — the caller "
        "redacts before this call, but reinforce: use 'A.J., 8-month-old infant "
        "with severe HIE' as the patient referent."
    ),
    "strict": True,  # ← grammar-constrained sampling
    "input_schema": {
        "type": "object",
        "properties": {
            "en": {"type": "string", "description": "Body in English (US clinician register)."},
            "ka": {"type": "string", "description": "Body in Georgian (family register, Mkhedruli script)."},
        },
        "required": ["en", "ka"],
        "additionalProperties": False,
    },
}

def compose_bilingual(prompt: str, *, client: Anthropic, model: str = "claude-sonnet-4-5") -> dict:
    """Return {'en': str, 'ka': str}. Raises if the model produces no tool_use."""
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        tools=[BILINGUAL_TOOL],
        tool_choice={"type": "tool", "name": "compose_bilingual"},  # force this tool
        messages=[{"role": "user", "content": prompt}],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "compose_bilingual":
            return {"en": block.input["en"], "ka": block.input["ka"]}
    raise RuntimeError("compose_bilingual: model produced no tool_use block")
```

**Integration into `weekly_brief.py`:**

The existing path is **deterministic prose composition** from DB rows (see lines 359–366: `f"{len(sections.papers)} new relevant papers this week."`). Phase 6 has two options:

- **Option A (cheapest, recommended for MVP):** keep the deterministic summary lines exactly as today; manually translate the 5 fixed template strings to Georgian; mirror them into `{en, ka}`. **No Anthropic call for the summary block at all.** This keeps the $0 baseline for the weekly brief composer.

- **Option B (LLM-translated section bodies):** call `compose_bilingual` for each section body that originates from `papers[i].title`, `hypotheses[i].title`, etc. — but these are already stored in `briefs.sections` post-migration-012 as `{en, ka}`. So the bilingual emission is already done at write time by the Communicator agent (CGM-03 flow), and the brief composer just reads what's there.

**Recommendation: Option A for the summary_lines block; Option B for upstream `hypotheses`/`therapies`/`aleksandra_timeline` row inserts.** The Communicator agent's per-row drafting is where the bilingual call happens. The weekly brief composer is then **deterministic stitching of pre-bilingualized rows** — zero new LLM cost per brief.

### Pattern 7: n8n workflows — no JSONB extraction expression changes needed

**What:** Survey the 5 workflows and identify where Telegram/Gmail body content actually lives.

**When to use:** I18N-07.

**Result of survey (verified by reading `workflows/*.json` files):**

| Workflow | Telegram-body source | Gmail-body source | Phase 6 change |
|---|---|---|---|
| `telegram_daily_digest.json` | Python worker `fire_daily_batch()` | n/a | **No n8n change** — body composed in worker. |
| `daily_digest.json` | n8n `Compose digest` JS code node (line 95) reads `topPapers[i].title` directly from Supabase | n/a | **Currently inactive** (`"active": false`). The JS code reads `p.title` — after migration 012, that's a JSONB object. Either (a) activate the workflow and update the JS to `(typeof p.title === 'string' ? p.title : (p.title?.ka ?? p.title?.en ?? ''))`, or (b) leave inactive (per existing `_phase_2_5_note`). **Recommendation: leave inactive; the Phase-4 worker-based `telegram_daily_digest.json` is the live path.** |
| `weekly_brief.json` | Python worker `/render-weekly-brief` (line 59) | Same worker (`stage_gmail_digest: true`) | **No n8n change** — worker reads `briefs.sections.summary_lines[i].ka` for Telegram, `.en` for Gmail. |
| `manager_briefing.json` | Python worker `/morning-briefing` | n/a | **No n8n change** — worker reads `manager_actions` + `briefs` → composes deterministic Telegram bullets. Worker reads `.ka`. |
| `outreach_review_queue.json` | n8n `Compose digest` JS code node (line 49) reads `r.subject` from `outreach_log` | n/a | `outreach_log.subject` is **TEXT** today and **stays TEXT** per SPEC ("outreach_drafter bilingual emission" is deferred). **No n8n change.** |

**Conclusion:** No JSONB extraction expressions need to change inside n8n JSON. All locale-aware reads happen in the Python worker layer. This simplifies Phase 6 dramatically — the n8n migration is zero-touch.

The Python worker change is:

```python
# scripts/communicator/telegram_sender.py — pseudocode
def fire_daily_batch():
    rows = pg_query("SELECT title, ... FROM hypotheses WHERE ...")
    for r in rows:
        # title is now jsonb {en, ka}; locale-resolve for Telegram audience
        title_ka = r.title.get("ka") or r.title.get("en") or ""
        send_telegram(title_ka)

# scripts/communicator/gmail_digest.py — pseudocode
def stage_weekly_digest():
    rows = pg_query("SELECT name, ... FROM therapies WHERE ...")
    for r in rows:
        name_en = r.name.get("en") or ""
        gmail_compose_draft(body_includes=name_en)
```

### Pattern 8: PHI redactor + imperative-verb lint extension for Georgian

**What:** Extend `scripts/communicator/phi_redactor.py` and `scripts/communicator/banned_phrases.py` to be bilingual-aware.

**When to use:** I18N-10.

**Existing coverage (already in code today, verified by reading both files):**

`phi_redactor.py` already has:
- Georgian name patterns: `ალექსანდრა\s+ჯინჭარაძე`, `ალექსანდრა`, `ჯინჭარაძე`
- Georgian DOB: `28\s+აგვისტო\s+2025`
- MRN literal (`7616818`) — language-agnostic since Mkhedruli digits are RARELY used in clinical contexts
- Hospital names — English-only today (BMC, Duke, Wisconsin) — Phase 6 adds Georgian equivalents

`banned_phrases.py` already has 8 Georgian patterns (lines 78–93):
- `უნდა\s+მიიღოს`, `უნდა\s+შეწყდეს`, `უნდა\s+გაიზარდოს`, `უნდა\s+შემცირდეს`, `უნდა\s+ჩაუტარდეს`
- `ვურჩევთ`, `გვირჩევთ`, `რეკომენდირებულია`
- `გამოჯანმრთელდება`, `აუცილებლად\s+გაუმჯობესდება`, `ეს\s+აღკვეთს`

**Phase 6 delta (per D-05):**

Append the 6 imperative-verb lexicon entries from CONTEXT.md to `_PATTERNS_KA`:

```python
# scripts/communicator/banned_phrases.py — additions
_PATTERNS_KA.extend([
    # English "should" → Georgian "უნდა" (already present in subordinate-clause forms;
    #   the new entries are direct-instruction forms)
    r"\bმართებთ\b",                          # martebt ("you ought")
    # English "must" → "აუცილებლად" / "აუცილებელია"
    r"\bაუცილებლად\b",                       # autsileblad (already in `აუცილებლად გაუმჯობესდება`; add bare form)
    r"\bაუცილებელია\b",                      # autsilebelia
    # English "consider" → "განიხილეთ" / "გაითვალისწინეთ"
    r"განიხილეთ",                            # ganikhilet (imperative 2pl polite)
    r"გაითვალისწინეთ",                       # gaitvalistsinet
    # English "try" → "სცადეთ"
    r"სცადეთ",
    # English "ask for" → "მოითხოვეთ"
    r"მოითხოვეთ",
    # English "request" → "ითხოვეთ"
    r"ითხოვეთ",
])
```

> Note: `\b` word-boundary is Latin-aware only; for Mkhedruli, prefer no `\b` anchor or use lookarounds. The existing Georgian patterns in `banned_phrases.py` follow this convention already (no `\b`).

**Morphology recommendation for D-05 discretion:**

Three options for handling Georgian polite-imperative declension:

| Option | Cost | False-positive risk | False-negative risk | Recommendation |
|---|---|---|---|---|
| (a) Literal 6-entry match | very low | very low | medium — misses `სცადე` (singular) and `ცადეთ` (informal) | **Recommended for Phase 6 MVP.** Per CGM-04 doctrine ("false positives accepted in favor of false negatives"), wide-net is the goal — but at MVP, the 6 literal forms already cover the 90% case (polite plural is the default register Communicator uses). |
| (b) Stem + suffix regex | medium | low–medium — collides with non-imperative verbs ending in `-ეთ` | low | Defer. Plan-phase can add this later as a CGM-04 hardening. |
| (c) Georgian NLP lib (spaCy + GE model, Stanza) | high (new dep, ~50MB model) | low | very low | Out of scope per cost ceiling. |

Sample false-positives for option (b) (regex `\S+ეთ\b`):
- `კონფერენციაში მონაწილეობდით` — past tense, not imperative. False positive.
- `ცოდნამ მიგვიყვანათ` — past tense. False positive.

Sample false-negatives for option (a) (literal-only):
- `სცადე ერთხელ` — singular informal "try once". Missed.
- `ცადეთ კიდე` — colloquial "try again". Missed.

**Verdict (plan-phase recommendation):** Ship option (a) for Phase 6. Track a backlog item to upgrade to (b) if a Communicator draft slips through with a declined-imperative form Shako catches manually.

**Bilingual PHI fixture set (verifier C.3 input):**

```yaml
# tests/fixtures/phase6/phi_ka.yaml — 10 Georgian PHI phrases
- name: "Patient full name Mkhedruli"
  input: "ალექსანდრა ჯინჭარაძემ მიიღო თერაპია"
  must_not_appear_in_output: ["ალექსანდრა", "ჯინჭარაძე"]
- name: "Patient short name Mkhedruli"
  input: "ალექსანდრამ კარგად აიტანა"
  must_not_appear_in_output: ["ალექსანდრა"]
- name: "Surname only Mkhedruli"
  input: "ჯინჭარაძემ კარგი შედეგი ნახა"
  must_not_appear_in_output: ["ჯინჭარაძე"]
- name: "DOB Georgian-month format"
  input: "დაბადება: 28 აგვისტო 2025"
  must_not_appear_in_output: ["28 აგვისტო 2025"]
- name: "BMC MRN literal in Mkhedruli context"
  input: "MRN 7616818 დადასტურდა"
  must_not_appear_in_output: ["7616818"]
- name: "Hospital name English in Mkhedruli context"
  input: "Boston Medical Center-ის ცნობით"
  must_not_appear_in_output: ["Boston Medical Center"]
- name: "Doctor name English in Mkhedruli sentence"
  input: "ექიმი Dr. Hien-მა გვირჩია"
  must_not_appear_in_output: ["Dr. Hien"]
- name: "Date format dd.mm.yyyy"
  input: "ვიზიტი: 28.08.2025"
  must_not_appear_in_output: ["28.08.2025"]
- name: "Patient first-name diminutive (catches without surname)"
  input: "ალექსანდრამ კარგად აიტანა გუშინდელი თერაპია"
  must_not_appear_in_output: ["ალექსანდრა"]
- name: "MRI artifact reference (HARD BLOCK)"
  input: "ხედე ფაილი viewer/scans/aleksandra.nii.gz"
  must_block: true   # phi_redactor must return RedactionResult.blocked=True
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Locale-segmented routing in Next.js 16 | A custom `proxy.ts` that parses `accept-language` | `createMiddleware(routing)` from `next-intl/middleware` | next-intl handles 308-redirects on default locale, locale prefix detection, and trailing-slash normalization — getting all 3 right manually is the standard footgun. |
| Strict bilingual JSON output from Claude | Prompt-only "respond with JSON" + `json.loads` retry loop | `tools[].strict=true` + `tool_choice={type:"tool",...}` | Anthropic strict tool_use uses grammar-constrained sampling — provably impossible to emit malformed JSON. Removes ~50 lines of defensive parsing and try/retry. |
| JSONB locale field reading in viewer | Per-component `field?.ka ?? field?.en ?? ''` | One `displayField(field, locale)` helper in `viewer/lib/i18n.ts` | TEXT-tolerance branch handles the legacy-row migration window; one source of truth means fixing a bug fixes it everywhere. |
| Pre-migration backup | A hand-rolled `INSERT INTO ... SELECT` archive table | `pg_dump --table=... --data-only --column-inserts` | `--column-inserts` produces a restorable text file independent of TYPE changes; doesn't pollute the live schema with a `_pre_012` table. |
| Georgian morphology lint | A spaCy/Stanza Georgian NLP pipeline | Literal-string regex over a 6-entry lexicon (D-05) | An NLP dep adds ~50MB; the Communicator's register is narrow enough (polite plural, formal medical) that 6 literal forms catch the 90% case. |
| n8n JSONB extraction expressions | n8n native expressions like `$json["sections"][0]["body"]["ka"]` | Python worker reads JSONB and resolves locale before composing the message | All 5 workflows already delegate body composition to the Python worker (`PHASE4_DIGEST_WORKER_URL`, `PHASE5_MANAGER_WORKER_URL`). n8n JSON stays locale-agnostic. |

**Key insight:** Phase 6 is, in practice, a frontend-and-database phase. The agent-and-delivery side reuses existing Python worker call sites — only the prompt schema, the DB write shape, and the locale-resolution-at-read need to change. Don't be tempted to push locale awareness into n8n JSON; it lives one layer deeper.

## Runtime State Inventory

> This is a refactor/migration phase. State inventory required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | (a) `aleksandra_timeline` rows (count from Phase 2.5 = part of 47 episodes, exact n unknown — Communicator-written) — TEXT title/description need TYPE conversion. (b) `hypotheses` rows (10 total, 3 promising per CLAUDE.md) — TEXT title/description need conversion. (c) `therapies` rows (12 candidates per CLAUDE.md) — TEXT name + evidence_summary need conversion. (d) `briefs` rows — JSONB sections already exists; each section body field needs reshape from string → `{en, ka}`. | **Data migration** in migration 012: `USING jsonb_build_object('en', col, 'ka', col)` for cases (a)–(c); UPDATE with the recursive `jsonb_build_object` expression in Pattern 5 for (d). |
| **Live service config** | (a) n8n workflows — 5 of them survey clean (Pattern 7); only `daily_digest.json` has direct `p.title` extraction in a JS code node, but it's `"active": false`. **No live workflow change.** (b) Python worker URLs (`PHASE4_DIGEST_WORKER_URL`, `PHASE5_MANAGER_WORKER_URL`) point at code that needs to be Phase-6-aware before deployment. | **Code edit** in `scripts/communicator/telegram_sender.py`, `scripts/communicator/gmail_digest.py`, `scripts/manager/briefing.py`. No n8n JSON edits. |
| **OS-registered state** | None — there are no Windows Task Scheduler / launchd / systemd jobs referencing these tables by name. n8n cron triggers are inside n8n's own SQLite, not OS-level. | None. |
| **Secrets/env vars** | None — no secret keys reference the renamed columns or the new locale segments. `SUPABASE_DB_URL`, `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `PHASE4_*`, `PHASE5_*` env names all stay. | None. |
| **Build artifacts / installed packages** | (a) `viewer/.next/` — must be rebuilt after next-intl install (standard `npm run build`). (b) `viewer/node_modules/` — `next-intl` added, no other changes. (c) Python virtualenv — no Python deps change in Phase 6. | **Code edit** + rebuild: `cd viewer && npm install && npm run build`. |

**Nothing found in category:** OS-registered state, secrets/env vars (verified by grepping for the 4 table names across `.env*`, workflows, and pm2 ecosystem files — no hits in pm2-like state because there's no pm2 deployment per CLAUDE.md `pm2` references being Phase-2.5 era artifacts that were never wired live).

## Common Pitfalls

### Pitfall 1: middleware.ts vs proxy.ts mismatch

**What goes wrong:** Developer follows CONTEXT.md D-01 literally, creates `viewer/middleware.ts`, runs `npm run build` — Next.js 16 emits a deprecation warning but still works in this version. Later, a Next.js 16.x patch update tightens the deprecation to an error.

**Why it happens:** CONTEXT.md was written before this researcher confirmed Next.js 16's rename. The file convention changed; the next-intl import path (`next-intl/middleware`) did NOT.

**How to avoid:** Use `viewer/proxy.ts` (or `npx @next/codemod@canary middleware-to-proxy .` after writing it as middleware.ts). The function name inside also changes: `middleware()` → `proxy()`. Both signatures and function bodies are otherwise identical.

**Warning signs:** Next.js 16 build log emits "middleware is deprecated, use proxy instead" — silence this immediately, do not ignore.

### Pitfall 2: Async params missed in one of the 7 routes

**What goes wrong:** Engineer moves dashboard/page.tsx under `[locale]/`, forgets to add `params: Promise<{locale}>`, page builds but `locale` is undefined at runtime. Falls back to default locale silently. User sees English on `/ka/dashboard`.

**Why it happens:** Next.js 14 had sync params; Next.js 16 made it Promise-only. Pages that don't currently take params don't have the signature.

**How to avoid:** Add `params: Promise<{locale: 'en'|'ka'}>` to every page that needs locale (every page that uses `useTranslations` or `displayField`). For pages that don't need locale, omit params entirely.

**Warning signs:** TypeScript will catch this at build time if `params.locale` is accessed directly without `await`. Always destructure: `const {locale} = await params;`.

### Pitfall 3: NOT NULL preserved but JSONB shape skipped on insert path

**What goes wrong:** Migration 012 runs, `title` becomes `NOT NULL` JSONB. Manager API route `/api/manager/apply` inserts a new timeline row by passing `title: "Hello"` (TEXT) — Postgres throws `invalid input syntax for type json: "Hello"`. The manager UI looks broken until everyone realizes the insert path needs updating too.

**Why it happens:** Migration changes column TYPE without changing every caller.

**How to avoid:** Audit every INSERT call site for the 4 tables and update to JSONB shape. Specifically:
- `viewer/app/api/manager/apply/route.ts` — manager inserts timeline rows.
- `scripts/communicator/*` — all Communicator inserts.
- `scripts/manager/briefing.py` — manager briefing inserts (if any).
- `agents/communicator.py` — CrewAI wrapper.

**Warning signs:** Plan-phase MUST include a "find all INSERTs into the 4 target tables" task before migration 012 ships.

### Pitfall 4: setRequestLocale forgotten on a page → silent dynamic rendering

**What goes wrong:** Page imports `getTranslations` but forgets `setRequestLocale(locale)`. The page renders correctly but dynamically (every request), losing the `force-dynamic` opt-in clarity and any future static optimization. For this single-patient app, no functional impact, but the build log will warn.

**Why it happens:** `setRequestLocale` is a next-intl convention, not a Next.js requirement. Easy to skip.

**How to avoid:** Include `setRequestLocale(locale)` at the top of every page that uses `getTranslations` or `useTranslations`. The verifier should grep for this pattern.

**Warning signs:** next-intl build-time warning "Using getTranslations without setRequestLocale".

### Pitfall 5: PHI redactor scanned only English half of the {en, ka} pair

**What goes wrong:** Communicator emits `{en: "...", ka: "..."}`. Worker calls `redact(text)` on only the `en` field, persists both. Telegram sends the `.ka` body — which had no PHI scan — leaking patient name.

**Why it happens:** The redactor entry point is `redact(text: str)` — it's called per-string, not per-bilingual-pair.

**How to avoid:** Always call `redact()` twice: once on `.en`, once on `.ka`. Persistence must `OR` the `blocked` flag from both calls — if either blocks, refuse to persist. The verifier C.3 fixture set (Pattern 8 yaml) must include cases that test both halves.

**Warning signs:** None at runtime — PHI leak is invisible until a clinician notices. Verifier C.3 must catch this in CI.

### Pitfall 6: briefs.sections existing rows broken because new shape doesn't match old reader

**What goes wrong:** Migration 012 rewrites `briefs.sections.summary_lines[i]` from string to `{en, ka}`. Existing `weekly_brief.py` reader code does `f"• {line}"` — Python prints `{'en': '...', 'ka': '...'}` literal dict, not the line.

**Why it happens:** Migration changes the JSONB shape without coordinating with the reader.

**How to avoid:** Land the migration AND the reader update in the same Plan task. The reader fix is a `displayField`-equivalent for Python:

```python
def display_field_py(field, locale: str) -> str:
    if field is None:
        return ""
    if isinstance(field, str):
        return field
    if isinstance(field, dict):
        return field.get(locale) or field.get("en") or ""
    return str(field)
```

**Warning signs:** Verifier C.1 (post-migration smoke read of `briefs.sections`) must assert the reader produces non-`{}` strings.

## Code Examples

Verified patterns from official sources:

### Example: Page consuming async locale params

```typescript
// viewer/app/[locale]/dashboard/page.tsx
// Source: viewer/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/dynamic-routes.md
//       + https://next-intl.dev/docs/getting-started/app-router/with-i18n-routing
import {setRequestLocale, getTranslations} from 'next-intl/server';
import {getCount, getRows} from "@/lib/supabase";
import DashboardCharts from "@/components/DashboardCharts";

export const dynamic = "force-dynamic";

export default async function DashboardPage({
  params,
}: {
  params: Promise<{locale: 'en' | 'ka'}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('Dashboard');

  /* ... existing data loads, references displayField for any JSONB field ... */

  return (
    <main>
      <h1>{t('title')}</h1>
      {/* ... */}
    </main>
  );
}
```

### Example: viewer/lib/i18n.ts displayField helper

```typescript
// viewer/lib/i18n.ts (NEW file)
// Source: CONTEXT.md D-03 (locked utility shape)
export type BilingualField = string | { en?: string; ka?: string } | null | undefined;

export function displayField(field: BilingualField, locale: 'en' | 'ka'): string {
  if (field == null) return '';
  if (typeof field === 'string') return field;        // legacy TEXT row tolerance
  return field[locale] ?? field.en ?? '';              // strict locale → English fallback
}
```

### Example: Communicator inserting bilingual hypothesis row

```python
# Inside the Communicator agent flow (CrewAI wrapper or scripts/communicator/*.py)
from scripts.communicator.bilingual import compose_bilingual
from scripts.communicator.phi_redactor import redact, ConsentFlags
from anthropic import Anthropic

def write_hypothesis_row(brief_prompt: str, db_conn):
    client = Anthropic()
    pair = compose_bilingual(
        prompt=f"Draft a family-readable hypothesis description.\n\n{brief_prompt}",
        client=client,
    )
    # Redact both halves
    en_safe = redact(pair["en"], consent=ConsentFlags())
    ka_safe = redact(pair["ka"], consent=ConsentFlags())
    if en_safe.blocked or ka_safe.blocked:
        raise RuntimeError(f"PHI block: en={en_safe.block_reason} ka={ka_safe.block_reason}")

    # Bilingual lint pass
    from scripts.communicator.banned_phrases import check
    en_lint = check(en_safe.text, locales=("en",))
    ka_lint = check(ka_safe.text, locales=("ka",))
    if not (en_lint.passed and ka_lint.passed):
        raise RuntimeError(f"Imperative-verb lint failed: en={en_lint.violations} ka={ka_lint.violations}")

    # Persist as JSONB
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO hypotheses (title, description, hypothesis_type, status, generated_by)
            VALUES (%s::jsonb, %s::jsonb, 'cross_disease_inference', 'new', 'claude')
            """,
            (
                json.dumps({"en": "Hypothesis title (en)", "ka": "Hypothesis title (ka)"}),
                json.dumps({"en": en_safe.text, "ka": ka_safe.text}),
            ),
        )
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Custom Python harness `scripts/verify_phase{N}.py`, dataclass-based Check + Report. Mirrors verify_phase5.py pattern (read 2026-05-20). No pytest in scripts/. |
| Config file | None — each verify_phase script is self-contained. |
| Quick run command | `.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase6 --mode code-complete` |
| Full suite command | `.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase6` (production mode hits real DB) |
| Phase 4 regression | `.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase4 --mode code-complete` |
| Phase 5 regression | `.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase5 --mode code-complete` |

### Phase Requirements → Test Map

| Req ID | Behavior | Bucket | Test Type | Automated Command | File Exists? |
|--------|----------|--------|-----------|-------------------|-------------|
| I18N-01 | `next-intl` installed, `npm run build` exits 0 | A | E2E build | `cd viewer && npm install && npm run build && echo "OK"` | ❌ Wave 0 — `scripts.verify_phase6.check_i18n_01` |
| I18N-02 | 14 URLs (7 routes × 2 locales) return HTTP 200; bare `/dashboard` → 308 `/en/dashboard` | A | smoke | `for path in dashboard timeline papers therapies hypotheses today knowledge; do curl -sI http://localhost:3000/en/$path; curl -sI http://localhost:3000/ka/$path; done` | ❌ Wave 0 — `scripts.verify_phase6.check_i18n_02` |
| I18N-03 | Every `t(...)` / `useTranslations(...)` key in `viewer/app/[locale]/**` + `viewer/components/**` resolves in BOTH `messages/en.json` and `messages/ka.json` | A | static analysis | Grep + jq verifier (Pattern 3) | ❌ Wave 0 — `scripts.verify_phase6.check_i18n_03` |
| I18N-04 | LanguageSwitcher toggles `/en/*` ↔ `/ka/*` | A | Playwright-style smoke OR manual | Manual: visit `/en/dashboard`, click GE, assert URL is `/ka/dashboard`. Manual gate in MVP; automation deferred. | ❌ Wave 0 — `scripts.verify_phase6.check_i18n_04` (existence check on `LanguageSwitcher.tsx` mount in `[locale]/layout.tsx`) |
| I18N-05 | All 4 tables: `pg_typeof = jsonb` for converted columns; RLS policies present; rollback artifact present | B | DB query | `psql -c "SELECT pg_typeof(title) FROM aleksandra_timeline LIMIT 1;"` + `SELECT polname FROM pg_policy WHERE polrelid='aleksandra_timeline'::regclass;` | ❌ Wave 0 — `scripts.verify_phase6.check_i18n_05` |
| I18N-06 | Weekly-brief dry-run produces `briefs` rows with `{en, ka}` keys non-empty | C | integration | `python -m scripts.communicator.weekly_brief --dry-run --bilingual-test` (NEW flag); assert resulting `sections` JSONB has `summary_lines[0].en` and `summary_lines[0].ka` non-empty | ❌ Wave 0 — `scripts.verify_phase6.check_i18n_06` |
| I18N-07 | weekly_brief n8n dry-run: Telegram body contains Georgian codepoints; Gmail body has zero | D | integration | Python worker dry-run produces 2 strings; assert `any(0x10A0 <= ord(c) <= 0x10FF or 0x1C90 <= ord(c) <= 0x1CBF for c in telegram_body)` and `not any(... for c in gmail_body)` | ❌ Wave 0 — `scripts.verify_phase6.check_i18n_07` |
| I18N-08 | `displayField` helper present in `viewer/lib/i18n.ts`; unit test passes | A | unit | Direct Node import + 5 assertions (string, object-en, object-ka, object-en-only, null) | ❌ Wave 0 — `scripts.verify_phase6.check_i18n_08` |
| I18N-09 | Post-migration: every existing row has identical `.en` and `.ka` content | B | DB query | `SELECT count(*) FROM aleksandra_timeline WHERE title->>'en' = title->>'ka';` — must equal `SELECT count(*) FROM aleksandra_timeline;` | ❌ Wave 0 — folded into `check_i18n_05` |
| I18N-10 | PHI fixture (Pattern 8 yaml, 10 Georgian phrases) passes redactor; imperative-verb count = 0 across 30 bilingual digests | C | unit + integration | Run `tests/fixtures/phase6/phi_ka.yaml` through `phi_redactor.redact()`; run 30 bilingual sample digests through `banned_phrases.check(text, locales=("en","ka"))` | ❌ Wave 0 — `scripts.verify_phase6.check_i18n_10` |
| I18N-11 | `verify_phase4 --mode code-complete` = 9/9; `verify_phase5 --mode code-complete` = 13/13 | E | regression | Subprocess spawn both verifiers; assert exit 0 + parse "X/X PASS" line | ❌ Wave 0 — `scripts.verify_phase6.check_i18n_11` (REGR equivalent) |

### Sampling Rate
- **Per task commit:** `.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase6 --mode code-complete`
- **Per wave merge:** `.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase6` (production mode) + manual `/en/*` `/ka/*` URL smoke
- **Phase gate:** Full verifier green; `verify_phase4` + `verify_phase5` regression green; then `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `scripts/verify_phase6.py` — new file mirroring verify_phase5.py shape
- [ ] `tests/fixtures/phase6/phi_ka.yaml` — 10-entry Georgian PHI fixture set
- [ ] `tests/fixtures/phase6/bilingual_samples.json` — 30-entry bilingual digest fixture set for imperative-lint regression
- [ ] `viewer/messages/en.json`, `viewer/messages/ka.json` — expanded from 2 key groups (7 keys total) to full coverage (estimate 60–80 keys covering Dashboard, Timeline, Papers, Therapies, Hypotheses, Today, Knowledge, Navigation, Common, Shared)
- [ ] `viewer/i18n/routing.ts`, `viewer/i18n/request.ts`, `viewer/i18n/navigation.ts` — new files
- [ ] Rename `viewer/middleware.ts` → `viewer/proxy.ts` (codemod available)

*(No existing test framework — every verifier is hand-rolled per phase. This is consistent with Phases 0–5.)*

## Security Domain

> `security_enforcement` not explicitly disabled in `.planning/config.json` — included by default.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no — Phase 6 does not touch auth; Supabase magic-link auth is Phase 0 / FND-05 | — |
| V3 Session Management | no — URL is the source of truth for locale; no session changes | — |
| V4 Access Control | **yes** | Migration 008 RLS policies must survive migration 012 — verifier check `SELECT polname FROM pg_policy WHERE polrelid IN (...)` |
| V5 Input Validation | **yes** | (a) Locale param validated via `hasLocale(routing.locales, requested)` before any downstream use → notFound() if invalid. (b) JSONB inserts validated by Postgres TYPE (`text::jsonb` parsing). (c) Anthropic strict tool_use grammar-validates `{en, ka}` shape. |
| V6 Cryptography | no — Phase 6 introduces no crypto primitives; reuses Supabase TLS + Anthropic TLS | — |
| V7 Error Handling & Logging | yes | PHI redactor block events logged to `runs.exit_reason`; bilingual lint violations logged to `runs.exit_reason` |
| V12 Files & Resources | yes | `messages/{locale}.json` are static assets bundled at build time — no user-provided paths |

### Known Threat Patterns for Next.js 16 + Postgres + Anthropic stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Locale parameter injection (`/../etc/passwd` style via `[locale]`) | Tampering | `hasLocale(routing.locales, requested)` strict allow-list before any downstream use; `notFound()` on miss. |
| RLS bypass via service-role key leak | Information Disclosure | Existing — Phase 6 does not change service-role-key handling; verifier asserts RLS policies remain. |
| PHI leak in Georgian half of bilingual pair | Information Disclosure | Run `redact()` on both `.en` and `.ka`; verifier C.3 fixture (Pattern 8 yaml) catches this. |
| LLM-injected JSON malformation | Tampering | Anthropic `strict: true` + `tool_choice` — provably impossible per grammar-constrained sampling. |
| Migration 012 partial apply + data loss | Information Disclosure (loss) | Pre-migration `pg_dump --column-inserts` per table; in-transaction (`BEGIN; ... COMMIT;`); post-migration smoke SELECT before commit on a copy run first. |
| Imperative-verb leak in Georgian draft (CGM-04 regress) | Repudiation (medical advice) | `banned_phrases.py` Georgian patterns (12 existing + 6 new from D-05 = 18 total); verifier C.3 30-digest sample. |

## Sources

### Primary (HIGH confidence)

- `viewer/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/proxy.md` — Next.js 16 `proxy.ts` file convention, codemod `middleware-to-proxy`, version history entry `v16.0.0`.
- `viewer/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/dynamic-routes.md` — `params: Promise<{...}>` async-params shape, `PageProps<'/[locale]'>` helper.
- `viewer/node_modules/next/dist/docs/01-app/02-guides/internationalization.md` — Next.js's own canonical i18n guide cites `next-intl` first; uses `proxy.js` examples and `params: Promise<{lang:string}>`.
- https://next-intl.dev/docs/getting-started/app-router/with-i18n-routing — canonical next-intl v4 setup: `defineRouting`, `getRequestConfig({requestLocale})`, `createMiddleware(routing)`, `createNavigation(routing)`, `setRequestLocale(locale)`, `hasLocale`.
- https://next-intl.dev/docs/routing/middleware — confirms next-intl 4 supports `proxy.ts` ("`proxy.ts` was called `middleware.ts` up until Next.js 16").
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use — strict tool_use grammar-constrained sampling; required schema shape; PHI guidance (do not put PHI in schema property names).
- `npm view next-intl version` → 4.12.0 — verified live against npm registry 2026-05-20.
- `npm view next-intl peerDependencies` → `next: '^12.0.0 || ... || ^16.0.0'` — verified explicit Next.js 16 support.
- `scripts/migrations/008_phase3_tables_and_rls.sql` — RLS policy pattern that migration 012 must preserve.
- `scripts/migrations/002_aleksandra_timeline.sql` — TEXT-column shape today; RLS policies that survive.
- `scripts/schema.sql` lines 118–176 (therapies) + 275–332 (hypotheses) — TEXT columns + index inventory (no indexes on the columns being converted).
- `scripts/communicator/banned_phrases.py` lines 78–93 — existing Georgian imperative lexicon to extend.
- `scripts/communicator/phi_redactor.py` lines 81–101 — existing Georgian PHI patterns.
- `scripts/verify_phase5.py` lines 60–100 — `Check` + `Report` dataclass pattern to mirror in `verify_phase6.py`.
- `workflows/weekly_brief.json`, `workflows/telegram_daily_digest.json`, `workflows/daily_digest.json`, `workflows/manager_briefing.json`, `workflows/outreach_review_queue.json` — all 5 workflows surveyed; confirmed Telegram/Gmail body content lives in the Python worker layer, not in n8n JSON expressions.

### Secondary (MEDIUM confidence)

- https://github.com/amuradesign/next.js-16-next-intl-boilerplate — concrete file layout for Next.js 16 + next-intl: `src/proxy.ts` (not middleware.ts), `src/i18n/{routing,request}.ts`, `messages/{locale}.json`. Dependency versions: Next.js 16.2+, React 19.2+, next-intl 4.9+. Independent confirmation of the Next.js 16 proxy.ts convention.
- https://next-intl.dev/blog/next-intl-4-0 — v4 prep for Next.js 16 features; `requestLocale` API; "Require locale to be returned from getRequestConfig" breaking change.

### Tertiary (LOW confidence)

- None — all critical claims are backed by primary or secondary sources.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The 4 target columns have no indexes (B-tree, GIN, or otherwise) | Standard Stack / Pattern 5 | Migration 012 fails with "cannot ALTER COLUMN TYPE because index references it"; rollback artifact saves us. Verified by reading `scripts/schema.sql` + `002_aleksandra_timeline.sql`, but a future migration we missed could have added an index. **Plan-phase should run `\d aleksandra_timeline`, `\d hypotheses`, `\d therapies`, `\d briefs` against the live DB before writing migration 012.** | [ASSUMED] |
| A2 | Anthropic Claude Sonnet 4.5 supports `strict: true` tool_use as documented | Pattern 6 | The docs page cites `claude-opus-4-7` in examples but the strict-mode feature is documented across the API surface; we infer Sonnet 4.5 supports it too. **Plan-phase verifies with a 1-call test (`compose_bilingual("hello")`) before wiring the Communicator path.** | [ASSUMED] |
| A3 | The `daily_digest.json` workflow stays inactive in production | Pattern 7 | If Shako activates it, the JS `Compose digest` code node reads `p.title` directly — that's a JSONB object post-migration. **Plan-phase notes this as a backlog item: either keep inactive (documented) or update the JS to use `displayField`-equivalent in n8n expression syntax.** | [ASSUMED] |
| A4 | n8n's `manager_briefing.json` and `weekly_brief.json` Python workers do not read JSONB content fields directly today (they only fire triggers; the worker does the heavy lifting) | Pattern 7 | If a worker isn't yet implemented or is partially implemented and reads `briefs.sections` with the old string shape, Phase 6 breaks Phase 5 silently. **Plan-phase must read the actual `scripts/manager/briefing.py` source — not just the README — before locking Pattern 7.** | [ASSUMED] |
| A5 | The 60–80 message-key estimate for `viewer/messages/{en,ka}.json` covers all 7 family-facing routes | Standard Stack / Pattern 3 | Estimate could be off by 2×; doesn't affect correctness, only the size of the Plan task for I18N-03. **Plan-phase grep-counts hardcoded strings to get a real number.** | [ASSUMED] |
| A6 | Option (a) literal-string Georgian imperative lint catches the 90% case in practice | Pattern 8 / D-05 | If Communicator's Georgian register is more colloquial than expected (uses singular informal `სცადე` instead of plural polite `სცადეთ`), false-negatives increase. **Mitigation in CONTEXT.md: Shako reviews the lexicon during execute-phase before lint goes live.** | [ASSUMED] |
| A7 | The 4 family-visible tables have no triggers that reference the converted columns by name | Pattern 5 / Runtime State Inventory | Triggers like `aleksandra_timeline_set_updated_at` (verified to only touch `updated_at`) survive TYPE conversion. Other tables — none verified in `schema.sql` text search for trigger functions referencing `title/description/name/evidence_summary`. **Plan-phase confirms `SELECT tgname, tgrelid::regclass FROM pg_trigger WHERE tgrelid IN ('aleksandra_timeline'::regclass, ...)` shows no application triggers reading these columns.** | [ASSUMED] |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

This table is **NOT empty**; the planner should treat A1, A3, A4, A7 as pre-migration verification tasks (live DB introspection) and A2 as a 1-call sanity check before deep integration.

## Open Questions

1. **Should `daily_digest.json` be activated as part of Phase 6, or stay inactive?**
   - What we know: It's currently `"active": false` per the file header (`_phase_2_5_note`). The Phase-4 worker-based `telegram_daily_digest.json` is the live daily-digest path. Activating `daily_digest.json` would create a duplicate digest.
   - What's unclear: Is the family expecting two daily digests, or did Phase 4 supersede Phase 2.5's daily_digest entirely?
   - Recommendation: Leave `daily_digest.json` inactive; document this in the Phase 6 plan as "no n8n JSONB-extraction changes — daily_digest.json stays inactive, telegram_daily_digest.json is the live path."

2. **Does the manager API route (`/api/manager/apply/route.ts`) currently insert into `aleksandra_timeline` directly?**
   - What we know: Phase 5 has `viewer/app/api/manager/apply/route.ts` that applies preview-card batches. The 4 target tables include `aleksandra_timeline`.
   - What's unclear: Whether the manager apply route writes `title` as TEXT today (would break post-migration without an update) or already uses JSONB shape.
   - Recommendation: Plan-phase reads `viewer/app/api/manager/apply/route.ts` and lists every `.from('aleksandra_timeline').insert(...)` call site; updates each to JSONB shape as part of the same task that runs migration 012.

3. **Should the imperative-verb lint also check `outreach_log.body` and `outreach_log.subject` for Georgian violations?**
   - What we know: `outreach_log` columns stay TEXT per SPEC (Phase 6 doesn't touch outreach bilingual). `banned_phrases.check(text, locales=('en','ka','fr'))` runs all three by default.
   - What's unclear: Whether a Georgian outreach to a Tbilisi clinician (`outreach_log.language='ka'`) would now flag false positives from the 6 new lexicon entries that didn't apply pre-Phase-6.
   - Recommendation: Allow `banned_phrases.check(text, locales=(detected_lang,))` to single-locale-scope when the outreach language is known — avoids the new Georgian lint over-flagging French/English outreach. Backward-compatible: default still scans all 3.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js + npm | viewer build (I18N-01) | ✓ (assumed; viewer/package.json + node_modules present) | `next@16.2.6`, `react@19.2.4` | — |
| `next-intl` | I18N-01..04, 08 | ✗ | needs `^4.0.0` (4.12.0 latest) | — |
| psql / SUPABASE_DB_URL | I18N-05, 09 | ✓ (used by `scripts/communicator/weekly_brief.py`) | env-driven | — |
| Python `anthropic` SDK | I18N-06 | ✓ (Phase 3+) | already installed | — |
| Python `psycopg2` | I18N-05, 06 | ✓ | already installed | — |
| Python `reportlab` | weekly_brief PDF | ✓ | Phase 3 | — |
| n8n | I18N-07 | ✓ Railway hosted | n8n 2.x | — |
| `pg_dump` (pre-migration rollback) | I18N-05 acceptance | ✓ ships with Postgres client | — | If absent: take a Supabase logical backup via dashboard before migration. |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Sources

### Primary (HIGH confidence)

(See *Sources* section above.)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — next-intl 4.12 verified live on npm registry; peer-dep `next: ^16.0.0` confirmed; Next.js 16's own i18n guide cites next-intl first.
- Architecture: HIGH — boilerplate `amuradesign/next.js-16-next-intl-boilerplate` confirmed proxy.ts layout; Next.js 16's own proxy.md doc explicitly notes the middleware→proxy rename in v16.0.0.
- Pitfalls: HIGH — middleware/proxy mismatch is a Next.js 16 hard deprecation; async-params is a TypeScript compile-time error; PHI bilingual-redaction gap is a documented CGM-04 invariant.
- Bilingual emission: HIGH — Anthropic strict tool_use is the canonical structured-output primitive; verified in official Anthropic docs.
- Migration safety: HIGH for SQL syntax + MEDIUM for "no triggers reference target columns" — A7 is the only outstanding pre-flight check.
- Georgian morphology lint: MEDIUM — A6 acknowledges the literal-string approach may miss declined forms; Shako review is the mitigation already baked into D-05.

**Research date:** 2026-05-20
**Valid until:** 2026-06-19 (30 days for stable; Next.js 16.x and next-intl 4.x are both on a steady-release cadence so versions could drift but architectural decisions hold).
