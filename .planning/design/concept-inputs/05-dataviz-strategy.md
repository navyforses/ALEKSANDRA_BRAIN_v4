# Concept Input 05 — Dataviz Strategy

**Author**: design-dataviz
**Date**: 2026-05-25
**Status**: Wave 2 deliverable for fresh-site-concept-v1
**Scope**: cross-surface chart inventory, semantic-palette discipline audit, Phase 7.6 unifying viz language, library-budget cap, color+second-signal pattern, two dataviz decisions for Shako

---

## 5.1 Current chart inventory — works / decorative / wrong-type

| Surface | File:line | Type | Verdict | Note |
|---|---|---|---|---|
| Dashboard — budget gauges | `viewer/components/DashboardCharts.tsx:183-205` | horizontal progress bar | **works** | clean ratio readout; daily uses cyan, monthly uses emerald — but emerald is medical-green misapplied (see 5.2 V1) |
| Dashboard — ingestion rate | `viewer/components/DashboardCharts.tsx:222-285` | hand-rolled SVG area+line+dots | **works (but hand-rolled)** | answer "trend over time" is correct fit; should migrate to Plotly to converge tech |
| Dashboard — daily spend | `viewer/components/DashboardCharts.tsx:296-349` | hand-rolled SVG vertical bar | **works** | "how does spend change day-by-day" — bar fits; same Plotly migration applies |
| Dashboard — hypothesis status mix | `viewer/components/DashboardCharts.tsx:368-395` | **donut chart** | **wrong-type** | donut = pie variant; design-dataviz forbids. Replace with horizontal bar sorted descending |
| Twin — per-dimension posterior | `viewer/app/[locale]/twin/DimensionCard.tsx:91-114` | Plotly histogram | **works** | textbook fit for "what's the distribution"; consistent across 13 dims |
| Twin — cockpit snapshot sparkline | `viewer/components/twin/SnapshotWidget.tsx:120-141` | Plotly mini-histogram | **works** | tasteful — picks widest-HDI dim only, not 13 thumbnails |
| Hypothesis — simulation result | `viewer/components/hypotheses/SimulationGraph.tsx:60-81` | Plotly histogram (90px) | **works** | per-hypothesis benefit distribution; μ-overlay readout is good |
| Drift — 13-trace timeline | `viewer/app/[locale]/drift/Timeline.tsx:136-160` | Plotly multi-line + diamond markers | **works** | "how has belief evolved" — line + evidence-event markers is correct. **Palette concern below** |
| Simulate — A vs B overlay | `viewer/app/[locale]/simulate/ResultViewer.tsx:100-132` | Plotly overlay-histogram | **works (with caveat)** | overlay at 0.55 opacity is legible at 2 series; **color choice is wrong** (5.2 V2) |
| Simulate — scenario builder | `viewer/app/[locale]/simulate/ScenarioBuilderInner.tsx:158-172` | @xyflow/react flow | **works** | "compose a scenario" → flow is the canonical fit |
| Causal — DAG | `viewer/app/[locale]/causal/NetworkInner.tsx:78-87` | vis-network force-directed | **partial** | works for <300 nodes; **physics stays on forever** (anti-pattern); no clustering when ~571 nodes land |

**Net**: 9 charts work, 1 is wrong-type (donut), 1 is partial (causal physics + no clustering). Zero charts are purely decorative — good restraint.

## 5.2 Semantic palette discipline — where medical-red has gone aesthetic

Three concrete violations where medical-red (or its `bg-rose-*` / `bg-emerald-*` cousins) is carrying an **aesthetic** signal instead of a clinical one:

- **V1 · Dashboard budget gauges** (`DashboardCharts.tsx:200, 329, 440`) — emerald (`#059669` / `bg-emerald-600` / `bg-emerald-100`) is medical-green. It is being used for "monthly spend bar" and for the "ბიუჯეტის მდგრადობა" insight chip. Spend is not "confirmed positive evidence." Remediation: switch budget bars to neutral foreground or to `--color-medical-blue` (info / model output is a closer fit than "confirmed positive"). Reserve `medical-green` strictly for gate-passed therapies, PubMed-validated evidence, confirmed citations.
- **V2 · Simulate overlay histogram** (`ResultViewer.tsx:107, 115`) — Scenario A is cyan `#0891b2` (neutral), Scenario B is `#dc2626` (medical-red). Scenario B is not a clinical alert — it is the second arm of a comparison. Coloring it medical-red reads to the wife as "the bad scenario," which is exactly the clinical-meaning drift the load-bearing rule forbids. Remediation: use the **categorical chart palette** (5.3 below) — A = neutral blue, B = neutral orange — both at 0.55 opacity. Verdict pill stays in semantic palette (emerald = A_better, rose = B_better) because there the color **is** the semantic signal.
- **V3 · Drift Timeline palette** (`drift/Timeline.tsx:23-37`) — the 13-color trace palette includes `#dc2626`, `#ef4444`, `#16a34a`, `#10b981`, `#9333ea`, `#a855f7`, `#eab308` — every one of the medical 6 plus duplicates, used categorically. A user looking at "dim 4 is red, dim 8 is also red-ish" cannot tell that dim 4 is not flagged as an alert. Remediation: build a **non-clinical categorical palette of 13** (escalate to design-systems-lead per the agent rule §83) using colors that are *not* in the medical 6. Reserve the medical 6 for marker overlays where they encode evidence-event type, not trace identity.

Additional minor: `ScenarioBuilderInner.tsx:42-47` palette uses `#dc2626` for "Outcome" node-type — same drift, less severe (palette is in-canvas, not a chart fill). Remediation: shift Outcome to medical-blue (model output) or to neutral; keep semantic palette out of node-type taxonomy.

**Count**: 3 clear V-violations + 1 minor. All recoverable inside the v8 token-foundation phase by paired-PRs against the existing chart files.

## 5.3 Unifying viz language for Phase 7.6 NEW routes

TwinStatus / CausalGraph / SimulationStudio / BeliefDrift already share Plotly + vis-network + @xyflow/react technically. The **unifying language** that holds them together is five rules:

1. **One categorical palette (non-clinical, 13 entries) for trace/category identity.** Mid-saturation, deuteranope-tested (e.g., `ColorBrewer Set3` mapped to OKLCH at L≈65 / C≈0.10 / hue-spaced 27.7° apart). Medical 6 never appears as a trace identifier — only as a marker overlay or annotation color when the marker carries clinical meaning (lesion event, confirmed evidence event, alert state).
2. **Posterior/uncertainty is medical-blue.** Posterior means, HDI bands, model-output samples → `--color-medical-blue`. This is the chart-wide convention that ties Twin histograms → Drift posterior lines → Sim outcome distributions into one visual sentence: "blue = what the model believes."
3. **Evidence events are diamond markers in medical-purple** (hypothesis / exploration / "interesting unknown") — never red. Drift's `marker: { symbol: "diamond" }` is the pattern; promote it to the canonical evidence-event glyph across all four routes.
4. **Annotations get the semantic palette honestly.** Lesion zones, alert thresholds, dim-out-of-range bands — these are where medical-red earns its place. Use as fill-with-pattern or annotation line, never as the primary series.
5. **Loading is shimmer; empty is text-CTA; error is inline-banner; partial renders with the same axes.** No empty plots. Plotly `displayModeBar: false` everywhere. Initial render has zero animation; filter-change has 200ms ease-standard.

This language lets a user scan from TwinStatus → Drift → Sim → Causal and immediately read color, shape, and motion the same way. The wife reads "blue = belief" once and the lesson holds across four surfaces.

## 5.4 Library budget cap recommendation

**Recommendation: YES — cap at 3 chart libraries permanently. Plotly + vis-network + @xyflow/react is the ceiling.**

Trigger for an exception: a new visualization need (a) cannot be expressed in any of the 3 libs without >1 day of custom work, AND (b) the fourth lib bundles <100KB gzipped, AND (c) it has been considered against re-using Plotly's full chart database (scatter-3d, parallel-coordinates, sankey, sunburst, treemap, candlestick, contour, choropleth — all are already in `plotly.js-dist-min`). In nine months of operation we have not hit a chart Plotly cannot render. The cap is the right discipline.

Adjacent recommendation: **migrate the DashboardCharts hand-rolled SVGs to Plotly** in the v8 token-foundation phase. Two reasons: (1) eliminates a fourth de-facto "chart system" (hand-rolled SVG) that drifts from the unified language; (2) the SVG path math at `DashboardCharts.tsx:74-82` cannot be a11y-augmented as cheaply as Plotly's built-in `aria-label` + view-as-table affordance.

## 5.5 Pairing color with second signal (a11y response to 8.3 BLOCK)

a11y B3 flagged red/green chips + MRI legend as failing the colorblind baseline. For **charts specifically**, the pattern is:

- **Trace legends**: every legend entry pairs a color swatch with a **line-style glyph** (solid / dashed / dotted) AND the dim/category text. Plotly supports this via `line: { dash: "dot" }` per trace. Cycle three dash styles across the 13-trace palette → each trace carries color + dash + text. Deuteranope reads dash; grayscale-print reader reads dash; sighted reader reads color.
- **Marker overlays**: evidence-event diamonds (purple) vs. alert markers (red, where they earn it) are distinguished by **shape token**, not color alone: diamond = evidence-event, circle-with-cross = alert, triangle = warning. Plotly `marker: { symbol }` is free; we just need to use it.
- **Chart-internal status chips** (verdict badge in ResultViewer, status chip on hypothesis cards): pair the colored chip with a **lucide-react icon token** — `Check` for A_better, `AlertTriangle` for B_better, `Equal` for tie, `HelpCircle` for inconclusive. Color stops being the sole signal.
- **MRI legend pattern (cross-domain consistency)**: same recipe — dot + lucide-icon + text label. Even though MRI is design-webgl-3d territory, the pattern must match charts so the wife reads legends with one mental model across the product.

Concrete deliverable for v8: a `<ChartLegend />` primitive that takes `{ swatch, dashStyle, icon, en, ka }` and renders all four. design-engineer builds it; every chart consumes it.

## 5.6 Two dataviz decisions Shako must make

1. **Replace the dashboard donut with a horizontal bar sorted descending in v8?** (Recommendation: **YES.** Donut is a forbidden chart type in the agent canon; horizontal bar answers "how do hypothesis statuses compare" without the angular-perception penalty. ~2 hours of work, no data-contract change. Side benefit: removes one hand-rolled SVG.)

2. **Commission a 13-entry non-clinical categorical chart palette in v8 (the missing piece in the medical-6 closed system)?** (Recommendation: **YES.** This is the only way Drift Timeline + future multi-category charts can use color categorically without poisoning the medical semantics. design-systems-lead owns the spec; design-dataviz owns the application. ~1 day systems-lead work + ~half day to retrofit Drift Timeline + ScenarioBuilder palette. Risk: low. Without this, V3 above stays unfixed.)

---

**Hand-off note to design-director**: the unifying viz language (5.3) is the load-bearing recommendation; everything else is correction work. The two Shako-calls (5.6) unblock both the donut removal and the medical-palette purge across charts. Coordinate with design-systems-lead on the categorical palette token-set and with design-a11y on the `<ChartLegend />` primitive.
