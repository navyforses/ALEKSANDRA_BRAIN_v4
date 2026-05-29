# Concept Input 08 — Accessibility-First Principles for v8

**Date**: 2026-05-25
**Owner**: design-a11y
**Status**: Wave 1 strategic input (not a per-surface audit; full audits live in `.planning/design/a11y-audits/`)

---

## 8.1 Spot-audit findings (compressed)

Spot-checked 5 critical surfaces (today, dashboard, brain, root, layout shell) plus TopNav, LanguageSwitcher, BrainPanel. The `inbox` route does not yet exist as a page — Family Inbox is a Phase 7.6 NEW surface, and the today route hosts ActiveQuestionsSection in the meantime.

**Totals across the 5 surfaces: 4 BLOCK · 9 FLAG · several PASS notes.**

### BLOCK (4)

| # | Location | WCAG SC | Finding | Remediation |
|---|---|---|---|---|
| B1 | `viewer/components/layout/BrainPanel.tsx:11-32` mounted at `viewer/app/[locale]/layout.tsx:55-57` | 1.3.1, 2.4.1 | The 35%-width persistent panel uses `<aside>` correctly at the layout level, but the panel's inner `<h2>` is the activity-feed title; the page below has its own `<h1>` and `<h2>`. There is **no skip link** from `<main>` to either landmark, and the `<aside>` lacks `aria-label`. Keyboard users tab through every BrainPanel control before reaching the page content. | Add "Skip to main content" + "Skip to activity feed" links as the first two focusable elements in `<body>`; add `aria-label="BRAIN activity panel"` to the `<aside>`. |
| B2 | `viewer/app/[locale]/brain/page.tsx:51-57, 25-33` | 4.1.2 | Icon-only Layers button has only `title=` (not exposed as accessible name by all SR); SlidersHorizontal/Maximize/Play buttons rely on visible text but the Play icon in `researcherView` has no `aria-hidden`. The pseudo-tabs (`doctorView`/`parentView`/`researcherView`) are `<button>` elements with no `role="tablist"`/`role="tab"`/`aria-selected`. | Add `aria-label` to the Layers button; add `aria-hidden="true"` to decorative icons; wrap view-selector in `role="tablist"` with proper `aria-selected` state on the active button. |
| B3 | `viewer/app/[locale]/brain/page.tsx:71-82` (legend) and globally everywhere `bg-medical-red` / `bg-medical-green` co-occur | 1.4.1 | The MRI legend uses red dot = "damaged", green dot = "preserved" with text labels (good) — but the same red/green pair recurs across dashboard hypothesis-status badges (`statusTone`, dashboard.tsx:38-42) and in chart fills with **no secondary signal** (no shape, no icon, no pattern). Deuteranopic users see the same hue twice. | Add a shape token to the medical palette (e.g., red = filled square, green = filled check) or pair every red/green chip with a lucide-react icon (`AlertCircle` / `Check`). Verify via Stark or `prefers-contrast` simulator. |
| B4 | `viewer/app/[locale]/dashboard/page.tsx:130-132, 173` + `globals.css:74-83` (`animate-pulse`, `animate-ping`) | 2.3.3-adj, project-rule-7 | Live-status pings/pulses run forever with **no `prefers-reduced-motion` fallback**. `globals.css` defines `shimmer` + `pulse-soft` keyframes but has zero `@media (prefers-reduced-motion: reduce)` block anywhere in the codebase (Grep: 0 matches). Vestibular-sensitive users get a permanent moving target. | Add a global `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; } }` rule in `globals.css`, then re-test that status indicators still convey "live" via a static dot. |

### FLAG (9, condensed)

- **F1** `LanguageSwitcher.tsx:23,30` — buttons are 27px tall (`px-3 py-1`) — below WCAG 2.2 SC 2.5.8 minimum of 24×24 only barely, well below the 44×44 family-facing rule from the agent canon. Bump to `py-2`.
- **F2** `LanguageSwitcher.tsx:23,30` — KA button text `ქართული` is Mkhedruli but no `lang="ka"` wrapper on the button's accessible name. Screen reader on EN page will mispronounce. Add `<span lang="ka">ქართული</span>`.
- **F3** Zero `lang="ka"` / `lang="en"` overrides anywhere in viewer (Grep: 0 matches). Mixed-language strings (PMID labels, "direct HIE", `na`, English enum values on KA pages) will trip the SR pronunciation engine. Need a `<Lang>` helper component.
- **F4** `dashboard/page.tsx:128-155` — `<nav>` inside `<main>`-equivalent block with **no `aria-label`**. Plus the duplicate top-nav (dashboard has its own nav while `TopNav` already exists in layout shell) creates two unlabeled `<nav>` landmarks. Add `aria-label="Dashboard quick links"` and ideally remove the duplicate.
- **F5** `TopNav.tsx:42` — "doctorMode" pill is a `<span>` with no role; users cannot tell whether it's a control or a status badge. If status, `role="status"`; if control, make it a `<button>`.
- **F6** `today/page.tsx:17-22` — section ordering: `<h1>` then `<p>` "comingSoon" then `<ActiveQuestionsSection>` (which has its own `<h2>`). Heading sequence is fine, but the "fallback" `<p>` at line 27 inside an empty `<section>` is a meaningless landmark. Drop the section wrapper.
- **F7** `dashboard/page.tsx:218-224` — hypothesis status chips render `status: count` as plain text inside a colored chip; the chip color is the secondary signal but assistive tech reads only "promising 12" — no semantic separation. Wrap count in `<span aria-label="count: 12">`.
- **F8** `brain/page.tsx:36-46` — horizontal scrolling tab strip (`overflow-x-auto`) has no scroll-shadow or scroll-indicator and no keyboard-only horizontal scroll handler. Mouse-only.
- **F9** No focus-visible audit ever shipped: `globals.css` defines `--ring` token but **no `:focus-visible` rule applies it anywhere globally**. Tailwind 4 default focus ring is browser default (often invisible on white). Add a global `*:focus-visible { outline: 2px solid hsl(var(--ring)); outline-offset: 2px; }` in `globals.css`.

### PASS notes (preserve as patterns)

- `viewer/app/[locale]/layout.tsx:42` correctly emits `<html lang={locale}>` — the single most important a11y win in the codebase, courtesy of next-intl Pattern 2.
- `LanguageSwitcher.tsx:22,29` correctly localizes its own `aria-label` (EN button reads "Switch to English", KA reads "გადართვა ქართულზე" in KA).
- `ActiveQuestionsSection.tsx:69-74` uses `<header>` + `<h2>` + status badge — clean semantic structure to reuse.
- Layout uses real `<header>`/`<main>`/`<aside>` landmarks — better than most React apps.

---

## 8.2 The 5 a11y-first principles for v8

1. **Every locale-foreign string carries `lang`.** Any EN string rendered on a KA page (or vice versa) wraps in `<Lang code="en">` / `<Lang code="ka">`. Mixed enums, PMIDs, dimension names — all wrapped. *Rationale*: screen-reader pronunciation correctness is the bilingual project's load-bearing a11y commitment, and zero wrappers exist today.

2. **Color is never the only signal.** Every red/green/amber chip ships with a paired icon, shape, or text token. The semantic palette stays 6 colors but is always co-presented. *Rationale*: deuteranopia is ~8% of male users; the current medical-red/green pair fails this baseline in dashboard chips and chart fills.

3. **Motion is dual-state by default.** Every animation declares its `prefers-reduced-motion` fallback inline; no `animate-*` class ships without an explicit reduced-motion sibling. *Rationale*: vestibular sensitivity must be honored; zero current motion is reduced-motion-aware.

4. **Focus ring is non-negotiable.** A global `*:focus-visible` rule wired to `--ring` lives in `globals.css`; component-level `focus:outline-none` is a lint error. *Rationale*: keyboard-first Shako persona is the primary daily user and currently has no visible focus indicator.

5. **Family-facing surfaces meet 44×44, not 24×24.** Weekly-brief preview, Family Inbox, Family Handover, Telegram digest landing — all targets ≥44×44 CSS px. Operator surfaces (Shako's audit, hypotheses, twin) may use 24×24. *Rationale*: the wife reads under emotional load; precision input cost is part of accessibility.

---

## 8.3 Cognitive load on family-facing surfaces

The wife's weekly-brief ritual is currently **mostly outside the cockpit** — the brief is composed server-side and pushed via Telegram + Gmail. She rarely lands on a viewer route. When she does (Family Inbox is the Phase 7.6 NEW surface that brings her in), the cognitive load risk is acute.

**Data ratio on the cockpit's existing family-friendly surface** (today/page.tsx + ActiveQuestionsSection): roughly 80% data-bearing UI (status chips, dim labels, monospace IDs, JSON-ish prose) and 20% narrative. For the wife persona this inverts the right ratio. Sunday-morning reading wants **70% narrative / 30% data**, with data appearing as supporting beats inside paragraphs, not as the primary surface. ActiveQuestionsSection in particular renders dim-name + ISO status + truncated prompt — three operator-register elements stacked above one human sentence.

The brief itself (the Telegram/Gmail artifact) is currently a mentally **expensive** read because:
- Hypothesis IDs (`93426696`) leak through.
- Enum statuses (`promising`, `pursuing`) appear without translation context.
- Sentence chains hit 30+ words; the wife reads on a phone, partly distracted.

**Recommendation for v8**: a dedicated Family Brief surface should use prose-first composition, 65–75ch line lengths, body type ≥16px, and **zero raw enums or IDs**. The cockpit-style data view stays available to Shako via a "View source data" link — but is hidden by default from the wife.

---

## 8.4 The one a11y decision Shako must make

**Question**: Family-facing surfaces — do we commit to WCAG 2.2 **AAA** (including 7:1 contrast, ≥18pt body, ≥44×44 targets, no auto-motion at all, no time limits), while operator surfaces stay at AA?

**Recommendation: YES — split the conformance bar.** Family-facing = AAA. Operator-facing (Shako) = AA. The split is honest about the two registers, prevents AA from becoming a ceiling on the surfaces that need more, and lets the audit/twin/causal/simulate routes ship at AA pragmatically. The cost is one extra contrast token pair, one `family-mode` CSS variable, and a `surface-class` declaration per route — small. The win is that the wife and a future grandparent persona reading on a phone in low light get a genuinely accessible surface, not a "we passed AA, it's fine" surface.

If Shako declines the split, fallback: AA everywhere, with the 5 principles above treated as project-specific hard rules on top.
