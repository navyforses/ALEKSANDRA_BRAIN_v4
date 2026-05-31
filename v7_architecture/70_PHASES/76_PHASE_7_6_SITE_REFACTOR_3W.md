# Phase 7.6 — Site Refactor: 4 New Views + 4 Refactor Views (3 კვირა)

> **ფაზის ID:** 7.6
> **სახელი:** Site Refactor — Twin Status / Causal Graph / Simulation Studio / Belief Drift (NEW) + Status Cockpit / Hypotheses / Research Pulse / Family Inbox (REFACTOR)
> **ვადა:** 21 დღე (3 კვირა), 2026-12-06 → 2026-12-26
> **მთავარი deliverable:** 4 ახალი Next.js route + 4 არსებული route-ის refactor, Plotly + vis.js + react-flow ინტეგრაცია, full bilingual (ka + en)
> **წინაპირობა:** Phase 7.5 verifier 14/14 PASS · 7.0-7.4 API-ები ცოცხალი
> **LLM ბიუჯეტი:** $4
> **ფიზიკური ბიუჯეტი:** $0 ნამატი (Vercel Hobby covers)

---

## 0. ფაზის სახელი, ვადა, წინაპირობა

### 0.1 სკოპი

ფაზა აშენებს Next.js 16 saytze 4 ახალ ხედს ციფრული ტყუპის ვიზუალურ წვდომისთვის (TwinStatus, CausalGraph, SimulationStudio, BeliefDrift), იღებს Phase 7.0-7.5-ის backend API-ებს და ცვლის 4 არსებულ ხედს v7 enhancement-ით. ცოლი ხედავს ციფრული ტყუპის snapshot-ს Status Cockpit-ში; ექიმი იღებს Simulation Studio-ს PDF-ის ნაცვლად.

### 0.2 ფაზის ვადა

| საზომი | მნიშვნელობა |
|---|---|
| სტარტი | 2026-12-06 |
| დასრულება | 2026-12-26 |
| სამუშაო დღეები | 15 |
| შაკოს ფოკუს საათები | ~60 |
| Verifier gate | Phase 7.7-მდე 12/12 PASS |

### 0.3 წინაპირობების checklist

| # | წინაპირობა | სტატუსი |
|---|---|---|
| 1 | Phase 7.5 closure | gate |
| 2 | Backend APIs (belief, causal, sim, active) live | ✅ from 7.0-7.4 |
| 3 | next-intl@4.12.0 + viewer/proxy.ts | ✅ from Phase 6 |
| 4 | Plotly.js + react-plotly.js installable | check `npm i plotly.js react-plotly.js` |
| 5 | vis-network installable | check `npm i vis-network vis-data` |
| 6 | @xyflow/react (react-flow) installable | check |
| 7 | Vercel deployment connected | ✅ from Phase 6.1 (deploy pending) |

---

## 1. დღიური Breakdown (15 დღე)

### კვირა 1 — Twin Status + Belief Drift (NEW) (Days 1-5)

| Day | View | ნაბიჯი | Outcome |
|---|---|---|---|
| 1 | TwinStatus scaffold | `viewer/app/[locale]/twin/page.tsx` + server-side fetch `/api/belief/snapshot` | route 200 OK |
| 2 | TwinStatus 13-dim grid | 13 Plotly histograms (small multiples), each posterior visualized | grid renders 13 charts |
| 3 | TwinStatus drift sparkline | 30-day rolling posterior mean per dim | sparkline overlay |
| 4 | BeliefDrift scaffold | `viewer/app/[locale]/drift/page.tsx` + `/api/belief/history` | route 200 OK |
| 5 | BeliefDrift Bayesian timeline | x=time, y=posterior_mean per dim, evidence events as vertical lines | timeline interactive |

### კვირა 2 — Causal Graph + Simulation Studio (NEW) (Days 6-10)

| Day | View | ნაბიჯი | Outcome |
|---|---|---|---|
| 6 | CausalGraph scaffold | `viewer/app/[locale]/causal/page.tsx` + `/api/causal/graph` | route 200 OK |
| 7 | CausalGraph vis-network render | nodes = CausalNode, edges colored by type (CAUSES green, INHIBITS red, etc.) | 571-node graph renders < 2s |
| 8 | CausalGraph node detail panel | click node → show parents/children, edge mechanisms, citations | panel works |
| 9 | SimulationStudio scaffold + scenario builder | `viewer/app/[locale]/simulate/page.tsx` + react-flow for drag-and-drop interventions | scenario JSON emitted |
| 10 | SimulationStudio result viewer | POST `/api/sim/compare`, render Plotly histograms per outcome | comparison view live |

### კვირა 3 — Refactor 4 existing + Verifier (Days 11-15)

| Day | View | Change | Outcome |
|---|---|---|---|
| 11 | StatusCockpit refactor | + TwinStatus snapshot widget + today's active question | widget renders |
| 12 | Hypotheses refactor | + per-hypothesis simulation outcome graph (Plotly) + expected benefit distribution | graph per row |
| 13 | ResearchPulse refactor | + "what changes in twin from this evidence" filter, sortable by KL divergence | filter works |
| 14 | FamilyInbox refactor | + active questions section + ცოლის response history (Phase 7.4 active_questions table) | section live |
| 15 | Verifier + Vercel preview deploy + exit report | 12/12 PASS, preview URL shared, tag `v7.6.0-site-refactor` | green |

---

## 2. Deliverables

### 2.1 Frontend code

| ფაილი | მიზანი | LOC |
|---|---|---|
| `viewer/app/[locale]/twin/page.tsx` | TwinStatus route | 180 |
| `viewer/app/[locale]/twin/DimensionCard.tsx` | Per-dim Plotly card | 140 |
| `viewer/app/[locale]/drift/page.tsx` | BeliefDrift route | 160 |
| `viewer/app/[locale]/drift/Timeline.tsx` | Plotly timeline component | 180 |
| `viewer/app/[locale]/causal/page.tsx` | CausalGraph route | 140 |
| `viewer/app/[locale]/causal/Network.tsx` | vis-network wrapper | 200 |
| `viewer/app/[locale]/causal/NodeDetail.tsx` | side panel | 120 |
| `viewer/app/[locale]/simulate/page.tsx` | SimulationStudio route | 200 |
| `viewer/app/[locale]/simulate/ScenarioBuilder.tsx` | react-flow builder | 280 |
| `viewer/app/[locale]/simulate/ResultViewer.tsx` | Plotly comparison | 180 |
| `viewer/components/twin/SnapshotWidget.tsx` | for StatusCockpit | 100 |
| `viewer/components/hypotheses/SimulationGraph.tsx` | for Hypotheses | 120 |
| `viewer/components/research/TwinImpactFilter.tsx` | for ResearchPulse | 100 |
| `viewer/components/inbox/ActiveQuestionsSection.tsx` | for FamilyInbox | 140 |
| `viewer/messages/en.json` (additions) | new translation keys | +200 keys |
| `viewer/messages/ka.json` (additions) | KA translation keys | +200 keys |
| `viewer/lib/api/belief.ts` | typed API client | 120 |
| `viewer/lib/api/causal.ts` | typed API client | 100 |
| `viewer/lib/api/sim.ts` | typed API client | 130 |
| `viewer/lib/api/active.ts` | typed API client | 80 |

ჯამური LOC: ~2670 (TypeScript/TSX) + 400 (i18n keys).

### 2.2 npm dependencies (added)

```json
{
  "plotly.js": "^2.35.x",
  "react-plotly.js": "^2.6.x",
  "vis-network": "^9.1.x",
  "vis-data": "^7.1.x",
  "@xyflow/react": "^12.x"
}
```

### 2.3 Route map (post-refactor)

| Route | View | Status | Backend dependency |
|---|---|---|---|
| `/[locale]` | Status Cockpit | refactor (+ widget) | belief + active |
| `/[locale]/twin` | Twin Status | NEW | belief |
| `/[locale]/causal` | Causal Graph | NEW | causal |
| `/[locale]/simulate` | Simulation Studio | NEW | sim |
| `/[locale]/drift` | Belief Drift | NEW | belief |
| `/[locale]/hypotheses` | Hypotheses | refactor (+ sim graphs) | sim + Phase 2.5 |
| `/[locale]/research` | Research Pulse | refactor (+ twin filter) | belief + Phase 2 |
| `/[locale]/inbox` | Family Inbox | refactor (+ active Q section) | active + Phase 5 |

### 2.4 Bilingual key naming convention

```jsonc
// viewer/messages/ka.json (snippet)
{
  "Twin": {
    "title": "ციფრული ტყუპის სტატუსი",
    "lastUpdated": "ბოლო განახლება",
    "dimensions": {
      "cyst_volume": "ცისტური ენცეფალომალაცია",
      "seizure_frequency": "ეპილეფსიური სპაზმის სიხშირე"
    },
    "confidenceWindow": "{low}% — {high}% ნდობით",
    "evidenceCount": "{count} მტკიცებულება ბოლო 30 დღეში"
  },
  "Simulate": {
    "title": "სცენარის სიმულატორი",
    "newScenario": "ახალი სცენარი",
    "runSimulation": "გაშვება ({samples} ნიმუში)",
    "compareTo": "შედარება სცენართან"
  }
}
```

---

## 3. Blocking Dependencies

| დამოკიდებულება | ბლოკავს | Mitigation |
|---|---|---|
| Phase 7.0-7.4 backend APIs | every view | gate |
| Phase 7.5 CSP headers | TwinStatus image rendering (Plotly inline SVG must be allowed) | adjust CSP `script-src` + `style-src 'unsafe-inline'` only for Plotly |
| next-intl namespaces | all views (bilingual) | ✅ from Phase 6 |
| Vercel deployment slot | preview URL | ✅ |
| vis-network bundle size (~600 KB gzipped) | CausalGraph load time | code-split: dynamic `import()` per route |
| plotly.js bundle size (~3 MB gzipped) | Twin, Drift, Sim load time | use `plotly.js-basic-dist` if full not needed |
| Migration 012 JSONB Mkhedruli content | KA display in Hypotheses | ✅ (mostly; 7 blank rows pending wife rebuild — known carry-over) |

---

## 4. Verifier Checklist (12 ცდა)

| # | Check ID | აღწერა | PASS criterion |
|---|---|---|---|
| 1 | `check_7_6_01` | TwinStatus renders | E2E: navigate `/ka/twin`, 13 cards visible, no console error |
| 2 | `check_7_6_02` | BeliefDrift renders | E2E: navigate `/ka/drift`, timeline interactive |
| 3 | `check_7_6_03` | CausalGraph renders < 3s | Lighthouse + manual stopwatch |
| 4 | `check_7_6_04` | SimulationStudio scenario submit | E2E: build scenario, submit, result renders |
| 5 | `check_7_6_05` | StatusCockpit widget visible | E2E: snapshot widget on `/ka` |
| 6 | `check_7_6_06` | Hypotheses sim graphs | E2E: each row has graph |
| 7 | `check_7_6_07` | ResearchPulse twin filter | E2E: filter changes list |
| 8 | `check_7_6_08` | FamilyInbox active Q section | E2E: section present |
| 9 | `check_7_6_09` | Bilingual parity | every new key has en+ka entries (`scripts/check_i18n_parity.py`) |
| 10 | `check_7_6_10` | Bundle size budget | Lighthouse: each route JS < 500 KB gzipped, first-load < 2.5s on 4G |
| 11 | `check_7_6_11` | CSP compliance | no inline-script violation in production deploy |
| 12 | `check_7_6_12` | Phase 1-7.5 verifiers regression | all GREEN |

---

## 5. Rollback Strategy

### 5.1 Triggers

| Trigger | Severity | Action |
|---|---|---|
| Day 2: Plotly bundle blows budget by > 50% | HIGH | switch to `plotly.js-basic-dist` or alternative (Apache ECharts) |
| Day 7: vis-network renders 571 nodes > 5s | HIGH | virtualize / cluster nodes by causal community |
| Day 9: react-flow drag-drop UX confusing in user-test | MEDIUM | fall back to form-based scenario builder |
| Day 14: any refactor breaks existing Phase 6 family-facing route | CRITICAL | revert that route's commit, keep new routes |
| Day 15: verifier ≤ 9/12 | HIGH | 1-week extension; consider partial ship (NEW routes only, defer refactors) |

### 5.2 Rollback procedure

```bash
# revert specific routes
git revert <commit-sha-for-route>
# redeploy
git push origin main  # Vercel auto-deploys
```

```typescript
// feature flag in viewer/lib/flags.ts (emergency disable)
export const FEATURE_FLAGS = {
  TWIN_VIEW_ENABLED: true,
  CAUSAL_VIEW_ENABLED: true,
  SIM_VIEW_ENABLED: true,
  DRIFT_VIEW_ENABLED: true,
  // toggle to false to render placeholder + link to old experience
};
```

### 5.3 Compatibility

Phase 6 routes (`/ka`, `/ka/hypotheses`, `/ka/research`, `/ka/inbox`) უნდა დარჩეს ცოცხალი refactor-ის შემდეგ. დიდი ცვლილებები gated behind feature flags.

---

## 6. LLM Spend Tracking

### 6.1 Cap

| კატეგორია | Cap |
|---|---|
| Total | $4 |
| Per-day | $0.40 |
| Per-call | $0.25 |

### 6.2 Breakdown

| Activity | Calls | Model | Cost |
|---|---|---|---|
| Day 2-3 Plotly chart code-review | 4 | Sonnet 4.5 | $0.80 |
| Day 7 vis-network performance debug | 3 | Sonnet 4.5 | $0.60 |
| Day 9 react-flow drag-drop UX feedback | 4 | Sonnet 4.5 | $0.80 |
| Day 11-14 refactor diff review | 5 | Sonnet 4.5 | $1.00 |
| Day 15 KA exit report | 2 | Sonnet 4.5 | $0.50 |
| Buffer | — | — | $0.30 |
| **Total** | **~18** | — | **$4.00** |

### 6.3 Cumulative

| ფაზა | Cap | Cumulative |
|---|---|---|
| Through 7.5 | $82 | ~$30 |
| Phase 7.6 | $4 | $34 |

---

## 7. Sprint Retrospective Template

`docs/PHASE_7_6_RETROSPECTIVE.md`.

### 7.1 Metrics

| Metric | Target | Actual |
|---|---|---|
| Verifier PASS | 12/12 | __/12 |
| LLM spend | ≤ $4 | __ |
| Routes shipped (NEW + refactor) | 8 | __ |
| Avg route first-load size | < 500 KB | __ |
| Lighthouse perf score (avg) | ≥ 80 | __ |
| Bilingual parity | 100% | __% |
| Phase 1-7.5 regression | GREEN | __ |
| Vercel preview deploy successful | yes | __ |

### 7.2 Sections

- Plotly vs ECharts decision (if changed)
- vis-network performance tuning notes
- ცოლი-impact: did the StatusCockpit widget help with daily flow?
- Carry-forward to Phase 7.7 (acceptance window will exercise these views with real users)

---

## 8. წყაროები

### 8.1 Frontend libraries

- [Plotly.js docs](https://plotly.com/javascript/)
- [react-plotly.js GitHub](https://github.com/plotly/react-plotly.js)
- [vis-network docs](https://visjs.github.io/vis-network/docs/network/)
- [react-flow (@xyflow/react)](https://reactflow.dev/)
- [Next.js 16 App Router docs](https://nextjs.org/docs/app)
- [next-intl 4.12 routing](https://next-intl-docs.vercel.app/docs/routing/navigation)

### 8.2 Visualization guidance

- [Few S. _Information Dashboard Design_ 2013](https://www.perceptualedge.com/library.php)
- [Tufte E. _The Visual Display of Quantitative Information_ 2001](https://www.edwardtufte.com/tufte/books_vdqi)

### 8.3 Bundle size analysis

- [Next.js bundle analyzer](https://github.com/vercel/next.js/tree/canary/packages/next-bundle-analyzer)
- [web.dev: code splitting](https://web.dev/articles/reduce-javascript-payloads-with-code-splitting)

### 8.4 პროექტის ფაილები

- [75_PHASE_7_5_CONSTITUTIONAL_2W.md](./75_PHASE_7_5_CONSTITUTIONAL_2W.md)
- [ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md §11](../../ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md)
- [Phase 6 i18n implementation — CLAUDE.md Phase VI](../../CLAUDE.md)

---

**შემდეგი:** [77_PHASE_7_7_ACCEPTANCE_WINDOW_2W.md](./77_PHASE_7_7_ACCEPTANCE_WINDOW_2W.md)
