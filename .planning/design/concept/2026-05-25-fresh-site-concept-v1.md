# ALEKSANDRA_BRAIN, Fresh Site Concept v1

**Date**: 2026-05-25
**Author**: design-director (synthesis of 8 specialist inputs)
**Status**: DRAFT for Shako review
**Audience**: Shako (primary), the design studio team (secondary)

---

## Executive synthesis

The product works. Nine months of shipping, six closed phases, fourteen routes, and an in-flight v7 sprint have produced an instrument that runs without us for six-hour cron windows. The fresh-site-concept question is not "is the product right" but "what is the cockpit for, now that the operator knows what it does." Eight specialists answered that. The team converged on more than it diverged on.

The largest single finding came from Audience Refresh. Wife and clinician are not site personas, they are channel personas. They read Telegram, Gmail, and the Family Handover PDF. They do not type our URL. Future-Shako, the operator six months from now who has forgotten why a rule exists, is the real second site persona that the brief named only in passing. This reframe cascades into the IA proposal (parallel `/family/*` and `/clinician/*` namespaces, BrainPanel docking by route class), into the voice strategy (register tags per namespace, banned-token CI), and into Phase 7.6 NEW-route placement.

The visual-token, motion, and a11y inputs converged on a v8 token-foundation sprint as the load-bearing dependency for everything else. HSL to OKLCH unblocks dark mode in v9. The seven motion tokens unblock reduced-motion compliance. The global `prefers-reduced-motion` block closes the standing a11y BLOCK. The 13-entry non-clinical categorical palette unblocks the Drift Timeline medical-palette purge. The `:focus-visible` global rule restores keyboard-first dignity. None of this is glamorous. All of it is debt the v7 sprints have not had air to pay down.

The 3D viewer is the only place commitment beats deferral. `/brain` has been a placeholder for nine months. NiiVue is small, self-contained, lazy-loaded, and ships in three to four engineer-days. R3F plus FreeBrowse fork is a different conversation that defers to v9.

Five decisions need Shako's signature before v8 planning starts. They are in §9. The headline: the team recommends YES on every one.

---

## 1. აუდიტორიის განახლება / Audience Refresh

Nine months has reshaped who uses this cockpit, and the persona model has not caught up.

Shako is no longer the primary user the original brief described. Per Audience Refresh §1.1, he is a single-operator SRE for a 5-agent system that runs without him for six-hour cron windows. The cockpit is not where he does the work; it is where he checks whether the system did the work. The persona note calling him a "developer who reads dense info" is right in voice but wrong in operating context. He is an operator who triages overnight output in under ninety seconds and drops back into his IDE. The fourteen-route IA was designed for an explorer who lives inside the app. He visits it.

The wife persona is correct in voice and wrong in surface. The brief implied she reads the weekly brief on a viewer route. She does not. Audience Refresh §1.2 traces the evidence: `telegram_sender reads .ka`, `gmail_digest reads .en`, and no `/weekly-brief` route exists in the fourteen surfaces. The weekly brief is a Telegram payload and a Gmail payload, not a destination URL. The first real Sunday brief was 2026-05-24, yesterday. Vercel analytics for that 09:00–12:00 ET window will confirm whether she opened the viewer at all. Until that answer arrives, the safe planning posture is to treat her as a channel persona living in Telegram and Gmail.

The clinician persona is correct in voice and currently un-served by the site. Their artifact is the Family Handover PDF (ReportLab, Phase 3). The site has zero clinician-tuned surfaces. An honest gap, not a drift; the right gap to leave open until a real clinician asks for a viewer.

The audience that emerged organically and that the brief named only in passing is Future-Shako, T+6 months. Audience Refresh §1.1 argues, and the director agrees, that this persona deserves first-class status. The thirteen inviolable Phase 7.5 rules, the 89/89 verifier coverage, the foundation_logs directory: these are not for present-Shako who wrote them. They are for a Shako who has forgotten why a rule exists and needs the cockpit to re-teach him. He reads in EN at developer register but needs narrative re-grounding the way the wife does on her phone. There is no "why does this rule exist" surface, only the rule itself.

Three painful moments in Shako-the-operator's daily ritual (Audience Refresh §1.3, evidenced against code). First, `/today` ships three placeholder strings as the body of the daily landing page, with one Phase 7.4 widget below them. The page promises "today" and delivers `t("comingSoon")` plus `t("fallback")`. BLOCK against Nielsen's visibility-of-system-status. Second, the dashboard nav (`viewer/app/[locale]/dashboard/page.tsx:142-153`) lists five of fourteen routes. Shako has to use the BrainPanel or URL-type to reach `today`, `audit`, `twin`, `drift`, `causal`, `simulate`, `brain`, or `knowledge`. Recognition-over-recall failure on the surface meant to be his nav backstop. Third, no surface answers "what changed since I last looked." No since-cursor anywhere in the product. The operator who wants a one-screen diff between Sunday 09:00 and now visits six routes to assemble it.

The recommended audience model for v8 (Audience Refresh §1.5) consolidates to two site personas and two channel personas. Shako-operator owns all fourteen-plus operator routes, keyboard-first and dense. Future-Shako owns the re-grounding surfaces: `/audit`, the constitution viewer, the "why does this rule exist" copy. Wife owns the Telegram message body, the Gmail digest, and an optional phone-first deep-link landing target. Clinician owns the Family Handover PDF, the doctor session prep doc, and an optional citation-forward landing.

This is a reframe, not an addition. The current model treats all four as site personas and under-serves all four. Building for the two who actually visit URLs, and treating wife and clinician as channel-first audiences with deep-link landings designed as message destinations, is the cleaner decomposition. One immediate consequence: the `/today` placeholder is not a "needs finishing" page. It is a category error. It was designed as if Shako-operator and wife-warm-morning shared a surface. They do not. `/today` should be Shako-operator-only and dense; the wife's "today" is the Telegram message that arrived at 09:00.

One open question the researcher kicked to synthesis: does demoting wife and clinician from site personas to channel personas conflict with anything in the 5-decisions section. The director's answer is no. The IA proposal in §4 absorbs the reframe via the `/family/*` and `/clinician/*` parallel namespaces. The voice strategy in §2 absorbs it via the per-namespace register tags. No site-level decision in §9 contradicts.

---

## 2. ხმა და რეგისტრი / Voice + Register Strategy

The 143-key dictionary samples cleanly into three register zones, per Voice + Register §2.1. One of them leaks into the others.

On-register surfaces hold. `Home.subtitle` reads warm-narrative ("clinical action stays with physicians"); `Therapies.subtitle` carries an explicit not-clinical-advice disclaimer; `Manager.input.askPlaceholder` is verb-first and direct. These are the patterns the rest of the family-facing copy should match.

Drifted surfaces tell a story. `Dashboard.rlsSmoke` ships "RLS smoke: covered by Phase 2.5 verifier C.2" as user copy. `Hypotheses.emptySupportingPapers` carries a file path, an internal table name, and a UUID in a single empty-state string the wife reads. The four mock-notice strings on Twin, Drift, Causal, and Simulate open with "Structural build:" and "Backend wiring lands in a follow-up sprint", sprint-planning vocabulary rendered to the family. The ten `phaseLabel` keys expose internal phase numbers ("Phase II.5C", "Phase 7.6 Digital Twin") as navigational chrome.

The drift is not random; it clusters on surfaces written during engineering sprints without a copy pass. The proposed fix is a register tag per namespace in `en.json` (family, shako, or clinician) and a verifier that fails CI when a family-tagged key contains a banned-token list: file extensions, table names, UUIDs, phase numbers, the words "verifier", "pipeline", "backfill", "wiring", "sprint". Mechanical, cheap, catches drift at authorship.

"Unknown potential" needs re-reading at month 9, per §2.2. At month 0 the phrase did real work, naming a stance against a default prognosis. At month 9 it risks reading as evasive because the system now has data: five confirmed hypotheses, twelve therapy candidates, a posterior over thirteen dimensions. The wife is no longer asking "is there hope" but "what changed this week, and on what evidence." The phrase still belongs in three places: the landing hero, the Family Handover preamble, and genuinely empty states. It does not belong on dashboards with real numbers. Rule: where the alternative is "limited outcomes" keep "Unknown potential"; where the alternative is "no update" say what changed. KA note for v7-i18n: the existing `უცნობი პოტენციალი` is on-register and not loop-prone.

The Telegram weekly digest preview is the load-bearing string in the product, per §2.3. It appears in a notification banner before the wife opens the app. Phone lockscreens truncate around 140 chars EN and ~120 chars Mkhedruli. Three constraints stack: warmth, length, no clinical content. The proposed shape is three lines:

- Line 1, always: "Weekly brief ready. {n} new findings this week."
- Line 2, if any: "Highlight: {one-sentence headline, no jargon}"
- Line 3, always, short: "Open to read together."

Voice rules: never lead with a zero (if `n = 0`, lead "This week was quiet. {one observation we did make}"). Never include "BRAIN", "agent", "hypothesis", "Sonnet", or any model name; the system stays invisible. Never include a clinician name, MRN, or trial code in the preview. The closing line is invitational, not transactional. KA: ≤120 chars per line. `ერთად წავიკითხოთ` carries the invitational register without imperative tone (D-05 safe, first-person plural suggestion, not an order).

Provenance in family copy, per §2.4: the clinician needs PubMed IDs visible; the wife needs to trust the finding without reading the citation. The pattern that works is a single-line provenance tag, never inline. The wife sees "Based on 5 papers" or "5 papers · 3 trials · last updated {date}." A "show sources" affordance reveals IDs for anyone who asks. Two anti-patterns to forbid: mid-sentence citations in family-facing copy, and "AI-generated" disclaimers. The wife already knows. Provenance reads as confidence; disclaimer reads as hedging.

The v8 voice strategy in three sentences, per §2.5. Tag every namespace with one of three registers and have CI fail when family-tagged copy contains developer tokens. Replace internal phase labels and sprint vocabulary with neutral status phrases on family-facing surfaces, while keeping Shako's audit-mode shells dense and jargon-rich on purpose. Reserve "Unknown potential" for the landing hero and genuinely empty states; everywhere the system has data, render the data.

---

## 3. ვიზუალი და ტოკენები / Visual + Token Direction

`viewer/app/globals.css` is 129 lines. Per Visual + Token §3.1, the foundation is small, disciplined, and mostly correct for month 9. What holds: the closed semantic palette (`--color-medical-*`, 6 entries) consistent with the constitutional rule that red = lesion and green = confirmed evidence; the `--radius: 0.5rem` lock with derived `radius-md` / `radius-sm` via `calc()`; Inter as the single UI face with system fallback; the `--panel: 210 40% 98%` slate-tint separating the 35% BRAIN column from the 65% content column without a border.

What is brittle, and what v8 should close. The color space is HSL-only, not OKLCH; this blocks honest dark-mode work, prevents tinted-neutral discipline, and forces ad-hoc contrast math. The medical 6 are raw hex literals, not tokens in the same theming surface; they cannot be re-derived for dark mode without rewriting each one. There are no state tokens (hover, focused, pressed, disabled, selected); components hard-code these in TSX. Shimmer uses `#f5f5f4`, an off-palette hex, the first and only token-system breach. `--background: 0 0% 100%` is pure white, which the hard-rule file forbids. There are no elevation, shadow, or easing tokens; motion lives in component CSS until §6 ships the canon.

The system is a good v1 skeleton that has not yet earned the right to call itself a design system. v8 is the right moment to upgrade it.

The Mayo-clean register at month 9 should evolve, not break, per §3.2. Hold Mayo-clean / Linear-crisp as the product register. Earn a tighter, quieter identity by doing two things v8 has not. First, tinted neutrals, not pure white or pure gray, triangulating from Linear's faint-blue tint, Vercel's near-white canvas, and Notion's warm soft-surface. v8 should adopt a faintly cool-tinted canvas (toward `--ring` clinical blue at hue ~222) at ~99% lightness, visible only subliminally but enough to cure the AI-generated-white-site feel. Second, a surface ladder, not a single panel. Linear runs four surface steps (canvas, surface-1, surface-2, surface-3) and carries all hierarchy from that ladder. v8 needs two more: a card surface between body and panel, and a deeper-inset surface for nested code blocks, audit log rows, and dataviz cells. What v8 does not evolve toward: Notion's pastel feature tints (off-register for clinical), Vercel's hero mesh gradient (decorative), Linear's pure-dark canvas (we are not a dark product yet).

Dark mode is a v8-token-foundation-only call, per §3.3. Ship the OKLCH token migration. Do not ship the dark theme. Dark mode done right is a six-week project (palette redefinition for all 6 medical semantics plus neutrals plus state colors plus dataviz plus MRI viewer behavior plus per-component review). Adding "dark mode" to v8 risks shipping it broken (medical-red looking pink, dataviz unreadable, lesion overlays inverted). The token migration ships standalone benefit: migrate HSL to OKLCH for all neutrals (`oklch(L C H)` form, neutrals at chroma 0.005-0.015 tinted toward clinical blue hue ~243); express the medical 6 in OKLCH alongside their hex (keep hex as canonical chart token for libraries that do not accept OKLCH directly); add the semantic-token layer (`--color-text-primary/secondary/tertiary`, `--color-surface-card/inset`, `--color-border-default/strong`). Only the semantic layer redefines for dark mode. v9 ships dark theme by overriding only the semantic layer. The MRI viewer stays dark by default regardless of app theme.

shadcn adoption is a conditional-yes call, per §3.4. The trigger is the third overlay primitive. The team currently has zero. Phase 7.6 plus the IA proposal will demand a command palette, `Select`, `Dialog`, `Tooltip`, and `DropdownMenu`: five overlay primitives. Hand-rolling five a11y-correct overlays (focus trap, escape, scroll lock, portal, ARIA, keyboard nav) is not $2/feature; it is $20-40/feature done correctly, and the team will get it subtly wrong on at least two. shadcn (Radix) gives the a11y for free. Bundle impact ~30-50KB tree-shaken. The decision: when the third overlay ships, adopt shadcn for the primitives in use only. Do not adopt the full registry. Cards, buttons, badges stay hand-rolled. The IA proposal in §4 names `⌘K` as the third overlay, which means shadcn flips from "wait" to "go" in v8.

The medical 6 palette stays closed at 6, per §3.5. The 6 cover lesion/urgent (red), confirmed evidence (green), pending/warning (orange), agent reasoning/hypothesis (purple), action/link/brain (blue), info/drug-class neutral (yellow). No surface is starved. The temptation to add a seventh for "treatment/therapy" should be resisted. What v8 should add is tonal variants: each color gets a `-soft` background tint (12-15% lightness lift toward canvas) and a `-deep` text-on-tint pair. Not a 7th color; the missing intra-color scale. Six colors times three tones equals 18 entries, still closed.

Typography stays Inter, per §3.6. Do not introduce a Mkhedruli display face. Inter ships competent Georgian glyphs (correct, well-hinted, paired with the Latin without a family swap). A display face means dual font loading, weight-pair calibration per locale, a parallel type ramp, and a QA burden the team is not staffed for. The hero moments are quiet; typographically still product-register. What v8 should do is formalize a type ramp in tokens (`--font-size-display-xl` at 40px / -1px tracking, through `--font-size-caption` at 12px / 0). Currently TSX hard-codes Tailwind utility classes for every text element. The ramp lives in `globals.css` as `@theme` entries; component TSX consumes named tokens. The most impactful typography improvement for v8, larger than any font choice.

---

## 4. ინფორმაციული არქიტექტურა / Information Architecture

The audience reframe in §1 reshapes the IA. Routes authored for the wife (`/today`'s placeholder body, hero-style `dashboardCardTitle` on `/`) are mis-fit. Routes serving operator triage (`/dashboard`, `/audit`) are under-promoted. Per IA Proposal §4.1, every authenticated route assumes a keyboard-first operator dropping in from an IDE, glancing at overnight output, deciding what to dispatch, and leaving inside ninety seconds. Channel-destination surfaces (three or four max) are message landings: single-scroll, no jargon, no operator chrome, parallel namespace so neither set leaks.

The route inventory verdict, per §4.2: fourteen current plus four Phase 7.6 NEW (`inbox`, `handover`, `briefMobile`, `constitution`) reshape to eleven operator routes (Home + four Research + five Belief + Audit) plus three channel routes under `/family/*` and `/clinician/*` plus one system route under `/system/constitution`. Fifteen total, grouped into four conceptual buckets that survive memory.

Two retirements deserve naming. `/today` retires entirely (Audience Refresh §1.3 and IA §4.2 both call it a category error); its job is absorbed by the reframed `/` and a new "since-cursor" diff. `/dashboard` merges into `/`; KPI rail and `latestEvents` become the body of `/`, and the duplicate in-page nav (a11y F4) disappears with the merge. `/knowledge` folds into `/papers` as a tab. Three Phase 7.6 NEW routes (`inbox`, `handover`, `briefMobile`) move into the channel namespace, never into the operator nav.

The workspace concept is yes-but-lightweight, per §4.3. A Linear-style left sidebar would consume horizontal real-estate the BrainPanel already owns and teach the wrong gesture for ninety-second triage. Workspaces become top-nav sections instead. Each section's routes reveal in a secondary in-section nav rendered as horizontal tabs:

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

Four sections. The "workspace" is the section context, not a database concept. Section context persists when navigating within a section (sub-nav stays sticky); switching sections does a 100ms fade per the motion canon in §6. Each operator route renders the top-nav section row plus a section-specific sub-nav row (24px tall, Linear-style hairline border below), giving Shako two memory anchors: which workspace, which surface within it. Sub-nav uses pure text tabs, no chips; active state is a `--ring`-colored underline. KA labels run 10-15% longer; section labels stay one word each in EN and KA. On mobile under 768px, top-nav collapses to a hamburger drawer and sub-nav becomes a horizontally-scrolling chip strip. Channel routes are mobile-primary, not mobile-degraded; BrainPanel does not render on those routes.

BrainPanel real estate becomes a route-class decision, not a global toggle, per §4.4. Keep 35% on `/` (Home triage) and `/audit`; collapse to a 56px rail on every other operator route; remove entirely on channel routes. On `/hypotheses`, `/twin`, `/causal`, and the rest of the dense reading surfaces, the operator is reading the page, not the panel; the 35% column steals reading width. Collapsed-rail state renders only the activity-pulse indicator (the `bg-medical-green animate-pulse` dot from `BrainPanel.tsx:16`, now respecting the global reduced-motion rule from §6), the EmailIntent trigger as an icon-only button, and a vertical "BRAIN" label rotated 90°. One click or `⌘.` expands; another collapses. State persists per-route via `localStorage`. Channel routes share `viewer/app/[channel]/layout.tsx`, a parallel root layout that exposes only the family-mode shell.

The keyboard-first navigation layer ships in three layers, per §4.5. First, a global `⌘K` command palette (Radix Dialog under the shadcn trigger from §3.4) that searches routes, recent items, actions, and constitutional rules (`⌘K → fnd-01` jumps directly to the constitution viewer at that rule). Second, section-jump hotkeys: `g h`, `g r`, `g b`, `g s` for Home, Research, Belief, System; within a section, `1`/`2`/`3`/`4` jump to ordered sub-routes (`g b 1` is Belief, then Twin). Third, per-route action hotkeys: `c` confirm hypothesis, `r` review, `x` reject on `/hypotheses`; `?` opens an inline shortcuts cheatsheet (Linear pattern); `Esc` always closes the BrainPanel or palette before navigating up. The cheatsheet is the Future-Shako bridge: in six months, `?` rediscovers the keyboard layer even if muscle memory is gone. KA renders in Mkhedruli with English keycap glyphs wrapped in `<Lang code="en">` per §8.

Channel-destination surfaces are deep-link landings, per §4.6. Three routes serve channel-persona links. They share `/family/*` and `/clinician/*` root layouts: no operator top-nav, no BrainPanel, no `phaseLabel` chrome, no wordmark in the header (the system stays invisible per §2.3). `/family/brief/[id]` is the Telegram tap target: single-scroll, prose-first, 65-75ch lines, body type ≥16px (the AAA family bar from §8). One narrative section per finding. Provenance as a "5 papers · last updated {date}" tag, never inline. Footer "Open dashboard →" routes Shako-mode users into `/`, ignored by the wife. `/family/inbox` is a list of weekly briefs, newest first, each row date + headline + provenance tag. `/clinician/handover` is citation-forward: PMIDs primary, narrative secondary, evidence-strength badges visible, "Generate PDF →" CTA top-right, EN-only by default. First-paint budget for channel routes: under 1.5s to meaningful content on a mid-tier phone over 4G. No client-side dataviz on first paint. BrainPanel polling logic does not load into the bundle for these routes.

Future-Shako support shows up in three concrete IA decisions, per §4.7. First, `/system/constitution` is a first-class route, not a docs file. Each of the thirteen Phase 7.5 inviolable rules renders as a card with rule text, a "Why this rule exists" two-sentence rationale, a "Last verified" timestamp, and a link to the verifier in `foundation_logs/`. The `⌘K` palette indexes rules by short-code. Second, "Last modified" surfacing on every operator card: hypothesis cards, therapy cards, paper cards, twin dimension tiles, causal nodes all get a `--font-mono text-xs text-tertiary` "updated 2d ago" line in the same position. Third, drift markers in section sub-nav: when a sub-route has activity since the operator's last visit (per-user `localStorage` cursor), the sub-nav tab renders a 6px `--color-medical-orange` dot. This is the "what changed since I last looked" signal Audience Refresh §1.3 named as the third painful moment, solved as nav chrome rather than as a separate surface. Cursor lives client-side only.

---

## 5. მონაცემთა ვიზუალიზაცია / Dataviz Strategy

Nine charts hold, per Dataviz §5.1. Dashboard budget gauges work; the ingestion-rate hand-rolled SVG works (should migrate to Plotly); the daily-spend bar works; Twin per-dimension Plotly histograms are textbook fits; the cockpit snapshot sparkline tastefully picks the widest-HDI dim; hypothesis simulation histograms with μ-overlay readouts work; the Drift 13-trace timeline and the Simulate A-vs-B overlay both work shape-wise. One chart is wrong-type: the dashboard hypothesis-status donut violates the agent canon and should become a horizontal bar sorted descending. One is partial: the causal vis-network DAG works under 300 nodes but its physics stays on forever and has no clustering plan for the ~571 nodes Phase 7.6 brings online. Zero charts are purely decorative.

Three medical-palette violations need remediation, per §5.2. V1: dashboard budget gauges use emerald (`#059669`) for "monthly spend"; emerald is medical-green, and spend is not "confirmed positive evidence." Switch budget bars to neutral or `--color-medical-blue`. V2: the Simulate overlay colors Scenario A cyan and Scenario B medical-red (`#dc2626`); Scenario B is not a clinical alert. Coloring it medical-red reads to the wife as "the bad scenario." Use the categorical palette below, A neutral blue, B neutral orange, both at 0.55 opacity. V3: the Drift Timeline 13-color trace palette includes every medical-6 color plus duplicates, used categorically. A user cannot tell that "dim 4 is red" is not an alert. Build a non-clinical categorical palette of 13 (systems-lead owns) using colors not in the medical 6. Reserve the medical 6 for marker overlays where they encode evidence-event type, not trace identity. All recoverable inside the v8 token-foundation phase.

The unifying viz language for Phase 7.6 NEW routes holds on five rules, per §5.3. One categorical palette (non-clinical, 13 entries) for trace/category identity, mid-saturation, deuteranope-tested (ColorBrewer Set3 mapped to OKLCH at L≈65, C≈0.10, hue-spaced 27.7° apart). Medical 6 never appears as a trace identifier; only as marker overlay or annotation color when the marker carries clinical meaning. Posterior/uncertainty is medical-blue (means, HDI bands, model-output samples); this ties Twin histograms, Drift posterior lines, and Sim outcome distributions into one visual sentence: "blue is what the model believes." Evidence events are diamond markers in medical-purple, never red. Annotations get the semantic palette honestly: lesion zones, alert thresholds, out-of-range bands earn medical-red as fill-with-pattern or annotation line, never as primary series. Loading is shimmer; empty is text-CTA; error is inline-banner. No empty plots. Plotly `displayModeBar: false` everywhere. Initial render zero animation; filter-change 200ms ease-standard per the motion canon.

The library budget caps permanently at three, per §5.4. Plotly + vis-network + @xyflow/react is the ceiling. Exception trigger: a need that cannot be expressed in any of the three without more than one day of custom work, and the fourth lib bundles under 100KB gzipped, and it has been considered against Plotly's full database first. In nine months the team has not hit a chart Plotly cannot render. Adjacent: migrate the DashboardCharts hand-rolled SVGs to Plotly in the v8 token-foundation phase, eliminating a fourth de-facto "chart system" and unlocking Plotly's built-in `aria-label` plus view-as-table affordances.

Color is never the only signal in charts, per §5.5. Every legend entry pairs a color swatch with a line-style glyph (solid / dashed / dotted) and the category text. Plotly supports `line: { dash: "dot" }` per trace; cycle three dash styles across the 13-trace palette. Marker overlays distinguish by shape: diamond for evidence-event, circle-with-cross for alert, triangle for warning. Chart-internal status chips pair the colored chip with a lucide-react icon (`Check` for A_better, `AlertTriangle` for B_better, `Equal` for tie, `HelpCircle` for inconclusive). MRI legend pattern uses the same recipe so the wife reads legends with one mental model across the product. Deliverable: a `<ChartLegend />` primitive that takes `{ swatch, dashStyle, icon, en, ka }`. design-engineer builds; every chart consumes.

---

## 6. მოძრაობის ენა / Motion Language

The current inventory is two keyframes (`shimmer` 1.8s, `pulse-soft` 50% scale) plus one SVG `.group`-scoped hover, plus Tailwind's stock `animate-pulse`/`animate-ping` on live-status dots. Per Motion §6.1: the restraint is correct, the discipline is broken. Restraint is the right philosophy for a medical-family product. Under-supply is not the problem. The problem is that none of this motion is reduced-motion-aware (zero `prefers-reduced-motion` matches anywhere in the repo, the standing a11y BLOCK), no canon governs future additions, and the two surviving keyframes use ad-hoc cubic-beziers no one else can reuse. The team is restrained for the wrong reason, restrained by accident because no system exists.

The reduced-motion BLOCK response is the first-order concern, per §6.2. v8 ships one rule before any other motion work, dropped into `globals.css` after the `body` block:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

WCAG-compliant default: instant state change, not slow. `0.01ms` is the convention. `!important` because component-level utilities will otherwise outrank under Tailwind 4's cascade order. Companion utility: a `motion-safe-pulse` opt-in for cases where a static "live" indicator must still convey liveness. Every animated component opts IN via `motion-safe-*` rather than opting OUT.

The 3 by 3 canon is yes, per §6.3. Add seven tokens to `globals.css`:

```css
@theme {
  --duration-reactive: 100ms;
  --duration-transitional: 200ms;
  --duration-emphasized: 300ms;

  --ease-standard: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-emphasized: cubic-bezier(0.2, 0, 0, 1);
  --ease-decelerate: cubic-bezier(0, 0, 0.2, 1);

  --color-shimmer-bg: hsl(var(--muted));
}
```

Three migrations land alongside: the SVG `.group` rules switch from inline `0.25s cubic-bezier(0.4, 0, 0.2, 1)` to `var(--duration-transitional) var(--ease-standard)`; `shimmer-loading` uses `var(--color-shimmer-bg)` instead of the off-palette `#f5f5f4` (closes systems-lead brittleness item 4); any new `transition:` in component CSS or Tailwind arbitrary value must reference these tokens. Adding a 4th timing or 4th easing requires written sign-off from director + systems-lead. The canon is closed.

Page transitions stay absent, per §6.4. Next.js 16 App Router gives instant navigation; a 100ms fade adds perceived latency where none existed. Linear, Raycast, and the cockpit-register peers all ship zero route motion. The 300ms `emphasized` slot is reserved for true attention moments (new question arrival, agent finishing a long-running task) where motion informs rather than decorates.

framer-motion is a permanent no for v8 and v9, conditional yes after that on one trigger only, per §6.5. The trigger: layout-aware shared-element transitions on the MRI viewer (a thumbnail expanding into a full-volume render while preserving its bounding box). CSS cannot orchestrate FLIP-style cross-component transitions; framer-motion's `LayoutGroup` plus `motion.div layoutId` is the canonical solution. No other use case justifies the bundle (~30-40KB gzipped) or the React-render overhead. CSS-first is the permanent default. Treat any framer-motion PR as a regression until the shared-element trigger fires.

---

## 7. სამგანზომილებიანი / 3D + MRI Viewer Strategy

`viewer/app/[locale]/brain/page.tsx` is 86 lines of placeholder chrome with zero 3D, per 3D Strategy §7.1. It renders a card-shaped frame, three pseudo-tabs without `role="tab"` (the a11y B2 BLOCK), an icon-only Layers toggle, a red/green legend (the a11y B3 BLOCK), and centered "in development" copy. `viewer/package.json` confirms NiiVue is not installed, `@niivue/nvreact` is not installed, `@react-three/fiber` is not installed, `drei` is not installed, `postprocessing` is not installed. The only related dep is `react-dropzone@15.0.0`, the file picker the agent canon names as the privacy-correct ingest UX. The brain route is greenfield: no rip-and-replace cost, no in-flight viewer state to migrate.

The viewer lives in the Belief section, per §7.2, alongside Twin, Causal, Simulate, Drift. Belief is the model-versus-anatomy section: Twin holds the 13-dimensional posterior, Drift holds its evolution, Causal holds the DAG, `/brain` is the only Belief surface where the anatomy is literal. Co-locating teaches the operator: "this is what we believe about Aleksandra, expressed five ways." Brain is not a Research route (Research is paper-and-finding pipeline; the MRI viewer never produces a citation). Brain is not a channel-namespace route; no wife-facing `/family/brain` in v8 or v9. The BrainPanel docking rule from IA §4.4 applies: `/brain` gets the collapsed-rail panel because the viewer owns the visual real estate.

The minimum viable v8 surface, per §7.3:

1. NiiVue volume render of a single client-loaded NIfTI file (`.nii.gz` / `.nii`) via `@niivue/nvreact`'s declarative component, mounted inside `<Suspense>` with the shimmer fallback.
2. `react-dropzone` ingest with explicit privacy reassurance copy ("Files stay in your browser. Nothing is uploaded."), non-negotiable per FND-01/FND-02 and agent canon rule 13.
3. Three orthogonal slice views (axial / coronal / sagittal) with a single linked-crosshair and keyboard slice navigation (↑/↓ steps slice, ←/→ jumps 10 slices, Home/End extremes).
4. One overlay type: a binary lesion mask, loaded as a second NIfTI, viridis colormap at 0.6 opacity, toggle via `L` key or Layers icon-button.
5. Reduced-motion mode with zero auto-rotate and static camera.
6. ARIA description plus text-summary fallback announcing slice changes throttled to 500ms.

Out for v8, deferred to v9: R3F anatomical shells, multiple simultaneous overlays, the nii2mesh STL pipeline (off-app Docker), TVB simulation visualization, and the doctor/parent/researcher view-mode tabs as functionally distinct.

The v8 commit call, per §7.4: commit. Do not defer. The brain route is already in nav, already in i18n, already named in the brief as a hero surface. Shipping it with zero of the promised functionality for another version cycle reads as broken to anyone who clicks the tab. NiiVue is small (~600KB gzipped, lazy-loaded via dynamic import on the brain route only, zero impact on home/dashboard/research bundles). `@niivue/nvreact` is a thin React wrapper. No R3F yet; v8 does NOT install `@react-three/fiber@9.6.x` or `drei` or `postprocessing`. The neuroplasticity-window time pressure argues for making the surface real now, even at a floor. Cost: 3-4 engineer-days. Dependencies that must land first: the motion §6.2 reduced-motion global rule, the a11y F9 focus-visible rule, the IA §4.4 BrainPanel collapsed-rail behavior. All three are prerequisites.

The segmentation pipeline UX is honest about the client-side-only rule, per §7.5. FastSurfer-LIT, BIBSnet, BONBID-HIE, and nii2mesh run on a family-controlled machine, never in the cloud. The family does not see segmentations in v8 because the pipeline does not exist as a running service. The viewer accepts a lesion mask (Duke radiologist deliverable, manually drawn ITK-SNAP mask, or a BIBSnet output if/when one exists) but does not assume any specific pipeline produced it. Off-device to in-viewer flow: Docker containers run on Shako's MacBook, outputs to `~/aleksandra-imaging/`, Shako drags the file into the viewer dropzone. v9 may add a saved-files affordance, also client-side-only. v8 keeps the file picker honest. The clinician deep-link MRI variant (`/clinician/brain/[hash]`) is a v9 conversation, per §7.6. v8 does not pre-build the channel surface.

---

## 8. ხელმისაწვდომობა / Accessibility-First Principles

Spot-audit across five surfaces plus TopNav, LanguageSwitcher, and BrainPanel produced **4 BLOCK and 9 FLAG** findings, per A11y §8.1.

The four BLOCKs. B1: the 35%-width BrainPanel uses `<aside>` correctly but the panel's `<h2>` competes with the page `<h1>`/`<h2>`; no skip link exists; the `<aside>` lacks `aria-label`. Remediation: skip links + `aria-label="BRAIN activity panel"`. B2: the brain route's icon-only Layers button has only `title=`; the pseudo-tabs are `<button>` without `role="tablist"`/`role="tab"`/`aria-selected`. Remediation: real tablist semantics, `aria-label` on Layers, `aria-hidden="true"` on decorative icons. B3: the MRI legend (red dot = damaged, green dot = preserved) and the same red/green pair on dashboard badges and chart fills with no secondary signal. Deuteranopic users see the same hue twice. Remediation: pair every red/green chip with a lucide-react icon (`AlertCircle` / `Check`), aligned with `<ChartLegend />` in §5.5. B4: live-status pings/pulses run forever with no `prefers-reduced-motion` fallback. Remediation: the global block from motion §6.2.

The nine FLAGs in one line: language-switcher hit targets at 27px (below 44×44 family rule) and missing `lang="ka"` wrapper; zero `lang` overrides anywhere in viewer; dashboard `<nav>` without `aria-label` plus duplicate top-level nav; "doctorMode" pill ambiguity; empty `<section>` wrappers on `/today`; status-chip text fused with count; horizontal-scrolling tab strip without scroll-shadow or keyboard handler; no global `:focus-visible` rule.

The five a11y-first principles for v8, per §8.2. First, every locale-foreign string carries `lang`: any EN string on a KA page (or vice versa) wraps in `<Lang code="en">` / `<Lang code="ka">`. Second, color is never the only signal: every red/green/amber chip ships with a paired icon, shape, or text token. Third, motion is dual-state by default: every animation declares its `prefers-reduced-motion` fallback inline. Fourth, focus ring is non-negotiable: a global `*:focus-visible` rule wired to `--ring` lives in `globals.css`; component-level `focus:outline-none` is a lint error. Fifth, family-facing surfaces meet 44×44, not 24×24: weekly-brief preview, Family Inbox, Family Handover, Telegram digest landing all target ≥44×44 CSS px. Operator surfaces may use 24×24.

Cognitive load on family-facing surfaces, per §8.3. The current data ratio on the only family-friendly surface (today + ActiveQuestionsSection) is roughly 80% data-bearing UI and 20% narrative. For the wife persona this inverts the right ratio. Sunday-morning reading wants 70% narrative / 30% data, with data as supporting beats inside paragraphs. The dedicated Family Brief surface (`/family/brief/[id]` in IA §4.6) uses prose-first composition, 65–75ch line lengths, body type ≥16px, zero raw enums or IDs. The cockpit-style data view stays available to Shako via a "View source data" link, hidden by default from the wife.

The recommendation in §8.4: split the conformance bar. Family-facing surfaces commit to WCAG 2.2 AAA (7:1 contrast, ≥18pt body, ≥44×44 targets, no auto-motion, no time limits); operator surfaces stay at AA. The split is honest about the two registers, prevents AA from becoming a ceiling on surfaces that need more, and lets audit/twin/causal/simulate routes ship at AA pragmatically. Cost: one contrast token pair, one `family-mode` CSS variable, a `surface-class` declaration per route.

---

## 9. ხუთი გადაწყვეტილება შაკოსთვის / 5 Site-Level Decisions Shako Must Make

These five decisions unblock v8 planning. Each is binary or narrow-choice. The team converged on all five with a YES.

### Decision 1, Adopt the four-section operator workspace IA?

Home / Research / Belief / System; retire `/today`; merge `/dashboard` into `/`; route Phase 7.6 NEW surfaces into `/family/*` and `/clinician/*` parallel namespaces. Option A: ship the consolidated IA in v8. Option B: keep the 14-route flat IA and add the four NEW Phase 7.6 routes to the same flat nav.

The current 5-item top-nav already omits 9 of 14 routes; growing to 18 breaks Miller's 7±2 and amplifies the future-Shako recall failure (Audience Refresh §1.3). The four-section grouping plus parallel channel namespaces is the only structural answer that absorbs both the audience reframe and the Phase 7.6 NEW routes without recombobulating mid-sprint.

Convergence: Audience Refresh §1.5, IA Proposal §4.8 D2, Voice + Register §2.1, A11y §8.3. Owner: design-product, with design-engineer for top-nav refactor and design-systems-lead for section-row + sub-nav tokens.

> RECOMMENDATION: YES. Adopt Home / Research / Belief / System; retire /today; merge /dashboard into /; create /family/* and /clinician/* parallel layouts.

### Decision 2, Ship the v8 token-foundation sprint?

Bundle HSL to OKLCH primitives, the semantic-token layer, tonal `-soft`/`-deep` variants on the medical 6, the non-clinical 13-entry categorical chart palette, the global `prefers-reduced-motion` block, the global `*:focus-visible` rule, and the 7 motion tokens into a single v8-opening phase. Option A: bundle. Option B: spread across v8 and v9.

Every other v8 decision (3D viewer, IA channel split, dataviz palette purge, channel-route AAA bar) depends on at least one of these foundation pieces. Bundling buys one review and one regression sweep; spreading buys two of each and an inconsistent baseline.

Convergence: Visual + Token §3.7, Motion §6.6, A11y §8.4, Dataviz §5.6 D2. Owner: design-systems-lead, with design-motion for the canon + reduced-motion block and design-a11y for the focus-visible gate.

> RECOMMENDATION: YES. Land the foundation as one phase; ~5-7 engineer-days; no visual change for default users.

### Decision 3, Commit to NiiVue + `@niivue/nvreact` in v8 for the MV MRI viewer?

Ship volume render, react-dropzone ingest, three orthogonal slices, keyboard navigation, one lesion-mask overlay with viridis. Defer R3F + drei + postprocessing + FreeBrowse fork to v9. Option A: ship MV in v8. Option B: defer the 3D stack to v9 and keep `/brain` as placeholder. Option C: commit to the full R3F sprint in v8.

The brain route has been a placeholder for nine months. NiiVue is small (~600KB gzipped, lazy-loaded on `/brain` only), self-contained, 3-4 engineer-days. R3F is a different conversation and earns its bundle only when a designed visual reason exists. Option C balloons v8 to ~3 weeks of viewer work alone.

Convergence: 3D Strategy §7.8, A11y §8.1 B2/B3 (this work closes both BLOCKs), Motion §6.2 + §6.5. Owner: design-webgl-3d, with design-a11y for keyboard + ARIA gate and design-systems-lead for the lesion-mask legend primitive.

> RECOMMENDATION: YES. Install NiiVue + nvreact, ship the MV viewer in v8, defer R3F to v9.

### Decision 4, Split the WCAG conformance bar?

AAA on family-facing surfaces (`/family/*`, weekly brief preview, Family Handover, Telegram digest landing). AA on operator surfaces (`/`, `/audit`, `/hypotheses`, `/twin`, `/causal`, `/simulate`, `/drift`, `/brain`). Option A: split-bar. Option B: AA everywhere with the five a11y-first principles as project hard rules. Option C: AAA everywhere.

The split is honest about the two registers. Option C blocks legitimate operator-density work (24×24 hit targets on the audit table). Option B caps the wife's surfaces below where they should be. Cost: one contrast token pair, one `family-mode` CSS variable, a `surface-class` declaration per route.

Convergence: A11y §8.4, Audience Refresh §1.5, IA Proposal §4.6. Divergence: none in the inputs; closest is the A11y §8.4 fallback (AA-everywhere if Shako declines). Owner: design-a11y, with design-systems-lead for the `family-mode` variable.

> RECOMMENDATION: YES. AAA on family-facing surfaces, AA on operator surfaces; fallback to AA-everywhere only if Shako declines.

### Decision 5, Adopt shadcn (tree-shaken Radix primitives) at the 3rd overlay-primitive trigger?

The `⌘K` command palette in IA §4.5 trips the trigger immediately in v8. Option A: adopt for overlays only (command palette, select, dialog, tooltip, dropdown-menu); keep cards/buttons/badges hand-rolled. Option B: hand-roll all overlays. Option C: adopt the full shadcn registry.

Hand-rolling five a11y-correct overlays is $20-40/feature done correctly, and the team will get it subtly wrong on at least two. shadcn under Radix gives the a11y for free. Bundle impact ~30-50KB tree-shaken. Option C adds surface area the team does not need.

Convergence: Visual + Token §3.4 + §3.7, IA Proposal §4.8 D3, A11y §8.1 B1/B2/F4. Divergence: Visual + Token §3.4 originally proposed deferring the trigger-count decision to Wave 2; the IA proposal in §4.5 names `⌘K` palette as the third overlay, which trips the trigger immediately. Director resolves: trigger is tripped in v8. Owner: design-systems-lead, with design-engineer for the migration plan and design-a11y for the gate sweep.

> RECOMMENDATION: YES. Adopt shadcn in v8 for overlay primitives only, scoped to the five the team will ship.

---

## 10. ტექნიკური შესაძლებლობების შევსება / Technical Capability Gaps

The eight inputs surfaced capability decisions across two buckets: ones already covered in §3, §6, and §7, and ones the inputs did not cover that the director surfaces here.

| Capability | v8 / v9 / never | Cost | Benefit | Owner |
|---|---|---|---|---|
| shadcn (Radix overlay primitives only) | v8 | ~30-50KB gzipped; 1d migration plan + per-overlay engineering | A11y correctness on focus trap, escape, scroll lock, portal, ARIA across 5 overlays | design-systems-lead |
| framer-motion | never until trigger | $0 in v8/v9; ~30-40KB gzipped + render overhead when adopted | Layout-aware shared-element transitions on MRI viewer (only justified trigger) | design-motion |
| Dark theme | v9 (foundation in v8) | v8: 2d OKLCH migration only; v9: ~6 weeks for full dark theme | v8 foundation unblocks v9 dark theme | design-systems-lead |
| NiiVue + `@niivue/nvreact` | v8 | ~600KB lazy-loaded on `/brain` only; 3-4 engineer-days | Closes 9-month placeholder; first real client-side MRI viewer | design-webgl-3d |
| R3F + drei + postprocessing + FreeBrowse fork | v9 | 0 in v8; ~3 weeks design+build in v9 when justified | Anatomical shells + depth-of-field around the volume render | design-webgl-3d |
| PWA / offline support | v9 candidate | ~3d service-worker scaffolding; Workbox config; offline fallback shells | Wife's Telegram-landed `/family/brief/[id]` on intermittent connectivity is the only honest use case | design-engineer |
| Realtime data layer (Supabase realtime / SSE) | v9 candidate | ~2-3d for Supabase realtime channel subscription on `/audit`, BrainPanel activity feed | Drift markers in section sub-nav (IA §4.7) push without poll. Brief leaves backend out of scope; defers to v9. | design-engineer + backend |
| Storybook for design-system docs | v9 candidate | ~2d initial scaffold + ongoing per-component cost; one CI workflow | Documents surface ladder, tokens, motion canon, ChartLegend for design-engineer onboarding | design-systems-lead |
| Playwright visual regression | v9 candidate | ~3d initial harness + per-route snapshot maintenance | Catches token-drift regressions automatically; complements verifier suite. Recommend after dark-mode v9 work begins. | design-engineer + design-a11y |

The v8 token-foundation phase (Decision 2) is the only net-new-dependency commitment for v8. The three other v8 commitments (Decision 1 IA, Decision 3 NiiVue, Decision 5 shadcn) are all framed inside that foundation phase or follow from it. None of the v9 candidates require commitment now. The right v8 posture: land the foundation, the IA, the NiiVue MV, the shadcn overlays, and the AAA/AA split. Leave PWA, realtime, Storybook, and Playwright for a v9 conversation that will have evidence-of-need by then.

Budget envelope. The v8 net-new bundle additions: shadcn Radix primitives (~30-50KB gzipped, tree-shaken) and NiiVue (~600KB gzipped, lazy-loaded on `/brain` only, zero impact on home/dashboard/research bundles). No framer-motion. No R3F. No Three.js outside R3F. No GSAP. No lottie. Total v8 frontend dep growth is well inside the budget the brief named.

---

## Appendix A: Source deliverables

- Audience Refresh: `.planning/design/concept-inputs/01-audience-refresh.md`
- Voice + Register: `.planning/design/concept-inputs/02-voice-register-strategy.md`
- Visual + Tokens: `.planning/design/concept-inputs/03-visual-token-direction.md`
- IA Proposal: `.planning/design/concept-inputs/04-ia-proposal.md`
- Dataviz Strategy: `.planning/design/concept-inputs/05-dataviz-strategy.md`
- Motion Language: `.planning/design/concept-inputs/06-motion-language.md`
- 3D / MRI Viewer: `.planning/design/concept-inputs/07-3d-mri-strategy.md`
- A11y Principles: `.planning/design/concept-inputs/08-a11y-first-principles.md`
- Brief: `.planning/design/briefs/2026-05-25-fresh-site-concept.md`

---

## Appendix B: Gate verdict (self-administered)

The director runs the three-gate review against the synthesis doc itself before declaring ship.

**design-systems-lead gate.** Token compliance: the doc proposes the OKLCH primitives, semantic-token layer, tonal variants, categorical palette, and 7 motion tokens as a single v8 foundation phase. No off-palette colors in any proposal. The `--background: 0 0% 100%` violation is named for fix. The shimmer `#f5f5f4` breach is named for fix. The medical 6 stay closed; the 13-entry categorical palette is non-clinical. Verdict: PASS.

**design-a11y gate.** WCAG 2.2 AA conformance, KA `lang` discipline, and reduced-motion respect: the doc names the global `prefers-reduced-motion` block, the global `*:focus-visible` rule, the `<Lang>` wrapper requirement, the `<ChartLegend />` second-signal primitive, the AAA/AA split, and the 5 a11y-first principles. Four BLOCK findings have remediation paths in the v8 plan. Nine FLAG findings have remediation paths. Verdict: PASS.

**design-content-bilingual gate.** EN copy register and KA voice direction captured for v7-i18n: the doc preserves the per-namespace register tags, the banned-token CI verifier proposal, the "Unknown potential" scope narrowing, the Telegram digest preview 3-line shape with KA character limits and the `ერთად წავიკითხოთ` D-05-safe phrasing, the provenance-tag pattern (count plus verb, not inline citation), and the anti-disclaimer rule. No clinical-advice copy. No mid-sentence citations. No PHI. KA section headings present. Verdict: PASS.

**Composite verdict: PASS.** No BLOCK remediation required. The doc is ship-ready for Shako review.
