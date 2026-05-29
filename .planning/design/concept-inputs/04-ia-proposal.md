# Concept Input 04 — Information Architecture Proposal

**Author**: design-product
**Date**: 2026-05-25
**Wave**: 2 of 3 — structural + visual proposals
**Status**: input for design-director synthesis
**Analogs read**: `viewer/app/[locale]/hypotheses/page.tsx` · `viewer/app/[locale]/causal/page.tsx` · `viewer/app/[locale]/twin/page.tsx` · `viewer/app/[locale]/page.tsx` · `viewer/app/[locale]/layout.tsx` · `viewer/components/layout/TopNav.tsx` · `viewer/components/layout/BrainPanel.tsx` · `external-skills/awesome-design-md/design-md/linear.app/DESIGN.md` · `external-skills/awesome-design-md/design-md/raycast/DESIGN.md`

---

## 4.1 Reframing premise

Concept Input 01 collapsed the audience model from four site personas to two: **Shako-operator** (now) and **Future-Shako** (T+6mo). Wife and clinician are channel personas — message-link destinations, not URL visitors. The IA must follow. Routes that were authored for the wife (`/today`'s placeholder body, hero-style `dashboardCardTitle` on `/`) are mis-fit; routes that serve operator triage (`/dashboard`, `/audit`) are under-promoted. The new constraint: **every authenticated route assumes a keyboard-first operator who is dropping in from an IDE, glancing at overnight output, deciding what to dispatch, and leaving inside 90 seconds**. Channel-destination surfaces (3-4 routes max) are designed as message landings — single-scroll, no jargon, no operator chrome — and live in a parallel namespace so they cannot leak into operator habits or vice versa. The brain panel, the top nav, and the workspace concept all answer to this single reframe.

## 4.2 Current 14-route inventory — keep / merge / retire / promote

The current routes (from `viewer/app/[locale]/`): `today, hypotheses, papers, therapies, timeline, audit, dashboard, brain, knowledge, twin, causal, simulate, drift, hypotheses/[id]`. Plus Phase 7.6 NEW: `inbox, handover, briefMobile, constitution` (per brief — `inbox` is the Family Inbox surface and does not yet exist as a page).

| Route | Verdict | Rationale |
|---|---|---|
| `/` (Home landing) | **REFRAME** to operator entry | Currently a wife-style hero with two card-CTAs. Reframe as Shako's overnight-diff "since-cursor" surface (replaces what `/today` was meant to be). The hero copy moves to a marketing-only build-time route. |
| `/today` | **RETIRE** | Concept Input 01 calls this a category error. Three placeholder strings + one Phase 7.4 widget. Its job is absorbed by the reframed `/` and a new `/queue` (see 4.3). |
| `/dashboard` | **MERGE** into `/` | Dashboard's KPI rail + `latestEvents` becomes the body of `/`. The in-page duplicate-nav (F4 in a11y audit) disappears with the merge. |
| `/hypotheses` | **KEEP**, promote to workspace section "Research" | Load-bearing for operator decision flow. |
| `/hypotheses/[id]` | **KEEP** as child of `/hypotheses` | Drill-down preserves URL-shareability for Telegram message links. |
| `/papers` | **KEEP**, group under "Research" | — |
| `/therapies` | **KEEP**, group under "Research" | — |
| `/timeline` | **KEEP**, group under "Research" | — |
| `/audit` | **KEEP**, group under "System" | — |
| `/knowledge` | **MERGE** into `/papers` as a tab | Two routes that answer the same operator question ("what does the system know"). Promotion costs nav-slot; merge buys focus. |
| `/twin` | **KEEP**, group under "Belief" | The Phase 7.6 13-dim posterior surface. |
| `/causal` | **KEEP**, group under "Belief" | SCM DAG. |
| `/simulate` | **KEEP**, group under "Belief" | Scenario studio. |
| `/drift` | **KEEP**, group under "Belief" | Posterior timeline. |
| `/brain` | **KEEP**, group under "Belief" | MRI viewer hero (NiiVue lands later per Wave 3). |
| `/inbox` (Phase 7.6 NEW) | **CREATE under channel namespace** `/family/inbox` | Wife-facing. Lives outside operator IA. |
| `/handover` (Phase 7.6 NEW) | **CREATE under channel namespace** `/clinician/handover` | Clinician deep-link landing. |
| `/briefMobile` (Phase 7.6 NEW) | **CREATE under channel namespace** `/family/brief/[id]` | The phone-first single-scroll target for Telegram deep-links. |
| `/constitution` (Phase 7.6 NEW) | **CREATE under system namespace** `/system/constitution` | Future-Shako re-grounding surface; first-class. |

Net: 14 routes → **11 operator routes** (Home + 4 Research + 5 Belief + Audit) + **3 channel routes** under `/family/*` and `/clinician/*` + **1 system route** under `/system/constitution`. **15 total**, but grouped into 4 conceptual buckets that survive memory.

## 4.3 Proposed v8 IA — workspace concept, yes

**Verdict: yes to a lightweight workspace concept; no to a left-sidebar workspace shell.** A Linear-style left sidebar would consume horizontal real-estate that the BrainPanel already owns (see 4.4) and would teach the wrong gesture for a 90-second triage. Instead: **workspaces as top-nav sections**, with each section's routes revealed in a secondary in-section nav rendered as horizontal tabs.

Map (read top-down as nav structure):

```
ALEKSANDRA_BRAIN  [Home]  [Research]  [Belief]  [System]   ⌘K    Lang   doctorMode
                              │            │          │
                              │            │          └─ Audit · Constitution
                              │            │
                              │            └─ Twin · Causal · Simulate · Drift · Brain
                              │
                              └─ Hypotheses · Papers · Therapies · Timeline

Out of operator nav, addressable only via deep-link:
  /family/brief/[id]      ← Telegram tap target
  /family/inbox           ← wife-facing inbox
  /clinician/handover     ← clinician deep-link
```

Four sections. The "workspace" is the **section context**, not a database concept. Section context persists when navigating within a section (sub-nav stays sticky); switching sections does a 100ms fade per Wave 2 motion. Each operator route renders the top-nav section row + section-specific sub-nav row (24px tall, Linear-style hairline border below), giving Shako two memory anchors: which workspace am I in, which surface within it. Sub-nav uses pure text tabs, no chips; active state is a `--ring`-colored underline. KA labels are 10-15% longer; section labels stay one word each in EN and KA to absorb the overflow without wrap.

Mobile (< 768px): top-nav collapses to a hamburger drawer; sub-nav becomes a horizontally-scrolling chip strip. Channel routes (`/family/brief/[id]`) are mobile-primary, not mobile-degraded — the BrainPanel does not render at all on those routes.

## 4.4 BrainPanel real estate — dockable, default-collapsed on dense routes

**Verdict: keep 35% on `/` (Home triage) and `/audit`; collapse to 56px rail on every other operator route; remove entirely on channel routes.** This is a route-class decision, not a global toggle.

Rationale: BrainPanel is Shako's most-touched UI element, but its information density (activity log + EmailIntent) duplicates `/audit`'s primary content on most routes. On `/hypotheses`, `/twin`, `/causal`, etc., the operator is **reading the page, not the panel** — the 35% column steals reading width from data-dense surfaces (the hypotheses cards already constrain to `max-w-7xl`; the panel pushes them narrower). On `/` and `/audit`, the panel is the page; full-width earned.

Collapsed-rail state (56px wide, right-docked): renders only the activity-pulse indicator (the `bg-medical-green animate-pulse` dot from `BrainPanel.tsx:16`), the EmailIntent trigger as an icon-only button, and a vertical "BRAIN" label rotated 90°. One click (or `⌘.`) expands to the current 35% panel; one click again collapses. State persists per-route via `localStorage`. The transition is a 200ms ease-standard width animation, with reduced-motion fallback per a11y principle 3.

Channel routes (`/family/*`, `/clinician/*`) render no BrainPanel and no operator top-nav — they share `viewer/app/[channel]/layout.tsx`, a parallel root layout that exposes only the family-mode shell.

## 4.5 Keyboard-first navigation layer

**Verdict: ship a `⌘K` command palette in v8 as the canonical cross-surface jump.** Raycast's `command-palette-row` pattern (see `awesome-design-md/raycast/DESIGN.md` lines 222-228, 531-538) is the precedent. The palette is the single keyboard primitive Shako learns; per-route hotkeys are layered on top of it for power moves.

Three layers, in order of priority:

1. **Global `⌘K` palette** — opens an overlay (Radix Dialog under the shadcn migration trigger per Concept Input 03). Search across: routes (`Go to → Hypotheses`), recent items (`Recent → Hypothesis 93426696`), actions (`Dispatch overnight cron`, `Open weekly brief`), and constitutional rules (`Why does FND-01 exist?` → routes to `/system/constitution#fnd-01`). Same primitive as Linear, Raycast, Notion. Tokens: surface uses `--color-surface-card` (per Wave 1 surface-ladder proposal), keycaps use `--font-mono` + `--color-surface-inset`. Mkhedruli overflow is absorbed by a vertical list (each row independent), not a horizontal layout.

2. **Section-jump hotkeys** — `g h` (go Home), `g r` (Research), `g b` (Belief), `g s` (System). Two-key sequences are the Linear/GitHub convention; they avoid `⌘`-collision with browser shortcuts. Within a section, `1`/`2`/`3`/`4` jump to ordered sub-routes. So `g b 1` is "Belief → Twin"; `g b 2` is "Belief → Causal".

3. **Per-route action hotkeys** — `c` confirm hypothesis · `r` review · `x` reject (on `/hypotheses`); `?` opens an inline "shortcuts for this page" cheatsheet (Linear pattern). `Esc` always closes the BrainPanel or palette before navigating up.

The cheatsheet is the Future-Shako bridge: in 6 months, `?` rediscovers the keyboard layer even if the muscle memory is gone. Cheatsheet copy lives in the per-route i18n namespace with a `Shortcuts.*` key prefix; KA renders in Mkhedruli with English keycap glyphs (`⌘ K`) wrapped in `<Lang code="en">` per a11y principle 1.

## 4.6 Channel-destination surfaces — deep-link landing UX

Three routes serve channel-persona deep-links from Telegram and Gmail. They share the parallel `/family/*` and `/clinician/*` root layouts — no operator top-nav, no BrainPanel, no `phaseLabel` chrome, no `ALEKSANDRA_BRAIN` wordmark in the header (the system stays invisible per Concept Input 02 voice rule).

| Route | Triggered by | First paint |
|---|---|---|
| `/family/brief/[id]` | Telegram weekly digest link (KA), Gmail digest link (EN) | Single-scroll, prose-first, 65-75ch line lengths, body type ≥16px (matches a11y AAA family bar). One narrative section per finding. Provenance lives as a "5 papers · last updated {date}" tag, never inline. Footer: "Open dashboard →" deep-link routes Shako-mode users into `/` (i.e., behaves as a normal anchor for the operator; ignored by the wife). |
| `/family/inbox` | Phase 7.6 Family Inbox surface | List of weekly briefs, newest first. Each row: date + headline-sentence + one provenance tag. Tap → `/family/brief/[id]`. No filters, no sort controls, no operator vocabulary. |
| `/clinician/handover` | Family Handover PDF deep-link footer | Citation-forward variant: PMIDs primary, narrative secondary, evidence-strength badges visible, "Generate PDF →" CTA top-right. EN-only by default; KA toggle hidden under settings. |

First-paint performance budget for channel routes: **< 1.5s to meaningful content** on a mid-tier phone over 4G. No client-side dataviz on first paint (charts lazy-mount below the fold). The BrainPanel's WebSocket / polling logic is not loaded into the bundle at all for these routes — `viewer/app/[channel]/layout.tsx` does not import `BrainPanel`.

## 4.7 Future-Shako support — how the IA explains itself

Three concrete IA decisions for the operator who has forgotten his own product:

1. **`/system/constitution` is a first-class route, not a docs file.** Each of the 13 inviolable rules from Phase 7.5 renders as a card with: rule text · "Why this rule exists" 2-sentence rationale · "Last verified" timestamp · link to the verifier in `foundation_logs/`. The `⌘K` palette indexes the rules by short-code (FND-01 etc.) so `⌘K → fnd-01` jumps directly. This is the surface that re-teaches Shako his own constraints six months from now.

2. **"Last modified" surfacing on every operator card.** Hypothesis cards, therapy cards, paper cards, twin dimension tiles, causal nodes — every list item gets a `--font-mono text-xs text-tertiary` "updated 2d ago" line in the same position. The operator visually scans for drift without parsing prose. The token is the same across surfaces; Future-Shako learns one signal and reads it everywhere.

3. **Drift markers in section sub-nav.** When a sub-route has activity since the operator's last visit (per-user `localStorage` cursor), the sub-nav tab renders a 6px `--color-medical-orange` dot to the right of the label. Visited routes return to neutral on tap. This is the "what changed since I last looked" signal Concept Input 01 names as the third painful moment — solved as nav chrome, not as a separate surface. Cursor lives client-side only (no server PHI).

## 4.8 Three IA decisions Shako must make

1. **Merge `/dashboard` into `/` and retire `/today`?** Recommendation: **YES.** Both routes currently fail their stated audience (Concept Input 01 §1.3). A single triage Home that ships the dashboard's KPI rail + a "since-cursor" diff matches what Shako actually does at 9am. Cost: one router redirect, ~2hr of layout work. Risk: low.

2. **Adopt the workspace section grouping (Home / Research / Belief / System) as v8 top-nav?** Recommendation: **YES.** The current 5-item flat top-nav already omits 9 of 14 routes (TopNav.tsx:14-20); growing to 14 items breaks Miller's 7±2. Grouping into 4 sections honors the operator's mental model (research vs. belief vs. system-health) and gives Future-Shako four shapes to remember instead of fourteen. Cost: top-nav refactor + sub-nav component + ~5hr to wire. Risk: low — pattern is Linear/Notion-standard.

3. **Ship `⌘K` command palette in v8 as the canonical cross-surface jump?** Recommendation: **YES, gated on the shadcn adoption trigger from Concept Input 03 §3.4.** The palette is the third overlay primitive Phase 7.6 would otherwise hand-roll (after the simulation Dialog and causal Tooltip). Bundling Radix Dialog + Command for this purpose is the exact justification that flips shadcn adoption from "wait" to "go". Cost: ~2 days for the palette + index + hotkeys. Risk: medium (bundle growth, but accessibility + Future-Shako value outweighs).
