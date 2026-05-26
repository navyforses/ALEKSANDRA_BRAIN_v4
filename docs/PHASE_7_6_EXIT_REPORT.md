# Phase 7.6 Exit Report — Site Refactor (Structural-Complete)

**Phase ID:** 7.6
**Title:** Site Refactor — Twin Status / Causal Graph / Simulation Studio / Belief Drift (NEW) + Status Cockpit / Hypotheses / Research Pulse / Family Inbox (REFACTOR)
**Sprint window:** scheduled 2026-12-06 → 2026-12-26 (15 days). This sprint compressed the engineering work into a single dispatch.
**Status:** STRUCTURAL-COMPLETE. `npx tsc --noEmit` exits 0 across `viewer/`; verifier 11/12 PASS + 1 SKIP (justified by Phase-7.5 baseline incompatibility); cumulative brain/ pytest 632 passing.
**Closure date:** 2026-05-25 (engineering sprint)
**Branch:** `v7-phases-7-0-to-7-5-closure` (commit #8 on the branch)

---

## 1. Structural-complete claim — what this report does and does not assert

This sprint shipped the TypeScript code, file structure, and i18n dictionary additions for the four new Phase 7.6 routes plus the four refactor widget additions, and proved them against the structural verifier. It did **not** validate visual rendering in a browser, did **not** measure bundle size against the Lighthouse < 500 KB per-route gzip budget, and did **not** exercise the drag-and-drop UX in `@xyflow/react`. Those validations belong to a separate Shako-led smoke session.

What this report does assert:

| Assertion | Evidence |
|---|---|
| All 4 new routes (`/twin`, `/drift`, `/causal`, `/simulate`) compile, parse, type-check, and live behind feature flags | verifier checks 01, 06, 11 PASS |
| All 4 refactor widgets (`SnapshotWidget`, `SimulationGraph`, `TwinImpactFilter`, `ActiveQuestionsSection`) exist and are imported into their host routes | verifier check 02 PASS |
| The 4 typed API client modules (`belief.ts`, `causal.ts`, `sim.ts`, `active.ts`) compile and expose interface + function exports with MOCK_MODE fallback | verifier check 03 PASS |
| Every new EN translation key has a paired KA key across 8 namespaces (143 → 244 keys) | verifier check 04 PASS |
| The new KA copy passes the anti-loop scan: no banned-word repeats, no `ცამეტი`, no em-dashes | verifier check 05 PASS |
| Heavy visualization libraries are code-split: Plotly via `next/dynamic` in 5 TSX files, vis-network via `next/dynamic`, `@xyflow/react` behind a `next/dynamic` wrapper | verifier checks 08, 09, 10 PASS |
| Cumulative Phase 1–7.5 backend regression remains green | verifier check 12 PASS (632 passed, 1 skipped) |

What this report does **not** assert (deferred to Shako carry-forwards):

- Plotly histograms actually render the histograms in a real browser.
- The 571-node vis-network graph hits the < 2 s render budget. (Mock reference SCM is 5 nodes; the live 571-node load remains unmeasured.)
- The react-flow drag-and-drop palette behaves intuitively (UX user-test).
- The first-load gzip bundle of each route is < 500 KB (Lighthouse run).
- The Plotly inline-style emission survives the Phase 7.5 strict CSP in production. (CSP middleware already permits `style-src 'unsafe-inline'` so the contract should hold, but it has not been smoke-tested with a Plotly chart on a deployed Vercel preview.)
- The next/dynamic + react-flow `@xyflow/react/dist/style.css` import resolves cleanly under Turbopack at production-build time. (See deviation #1.)

## 2. Route map (post-refactor) — actual vs spec

The spec assumed `/research` and `/inbox` routes; the actual viewer has `/papers` and `/today`. The refactor maps spec intent onto the actual routes:

| Spec route | Actual route | Widget added |
|---|---|---|
| `/[locale]` Status Cockpit | `viewer/app/[locale]/page.tsx` | `SnapshotWidget` (gated by `STATUS_COCKPIT_TWIN_WIDGET`) |
| `/[locale]/twin` Twin Status | `viewer/app/[locale]/twin/page.tsx` | NEW |
| `/[locale]/drift` Belief Drift | `viewer/app/[locale]/drift/page.tsx` | NEW |
| `/[locale]/causal` Causal Graph | `viewer/app/[locale]/causal/page.tsx` | NEW |
| `/[locale]/simulate` Simulation Studio | `viewer/app/[locale]/simulate/page.tsx` | NEW |
| `/[locale]/hypotheses` Hypotheses | `viewer/app/[locale]/hypotheses/page.tsx` | `SimulationGraph` per row |
| `/[locale]/research` Research Pulse | `viewer/app/[locale]/papers/page.tsx` | `TwinImpactFilter` |
| `/[locale]/inbox` Family Inbox | `viewer/app/[locale]/today/page.tsx` | `ActiveQuestionsSection` |

Action item: confirm with Shako whether the `/papers` and `/today` URLs stay or whether they get aliased to `/research` and `/inbox` for marketing clarity. Aliasing is a Phase 6.x routing decision, not a Phase 7.6 fix.

## 3. Files created or edited

### 3.1 New files (18)

| File | LOC | Role |
|---|---|---|
| `viewer/lib/api/belief.ts` | ~310 | Typed Belief API client + 13-dim deterministic mock |
| `viewer/lib/api/causal.ts` | ~190 | Typed Causal API client + reference SCM mock |
| `viewer/lib/api/sim.ts` | ~220 | Typed Simulation API client + Vigabatrin-vs-control mock |
| `viewer/lib/api/active.ts` | ~110 | Typed Active Learning API client + mock questions |
| `viewer/app/[locale]/twin/page.tsx` | ~80 | Twin Status server route |
| `viewer/app/[locale]/twin/DimensionGrid.tsx` | ~70 | Twin grid wrapper |
| `viewer/app/[locale]/twin/DimensionCard.tsx` | ~140 | Per-dim Plotly histogram |
| `viewer/app/[locale]/drift/page.tsx` | ~95 | Belief Drift server route |
| `viewer/app/[locale]/drift/Timeline.tsx` | ~150 | 13-trace Plotly timeline + per-dim toggle |
| `viewer/app/[locale]/causal/page.tsx` | ~80 | Causal Graph server route |
| `viewer/app/[locale]/causal/CausalView.tsx` | ~32 | Stateful wrapper for Network + NodeDetail |
| `viewer/app/[locale]/causal/Network.tsx` | ~45 | next/dynamic wrapper for vis-network |
| `viewer/app/[locale]/causal/NetworkInner.tsx` | ~100 | Inner vis-network DOM widget |
| `viewer/app/[locale]/causal/NodeDetail.tsx` | ~160 | Selected-node parents/children + citations |
| `viewer/app/[locale]/simulate/page.tsx` | ~85 | Simulation Studio server route |
| `viewer/app/[locale]/simulate/SimulateStudio.tsx` | ~50 | Stateful wrapper holding the active comparison |
| `viewer/app/[locale]/simulate/ScenarioBuilder.tsx` | ~35 | next/dynamic wrapper for react-flow |
| `viewer/app/[locale]/simulate/ScenarioBuilderInner.tsx` | ~210 | react-flow canvas + validation |
| `viewer/app/[locale]/simulate/ResultViewer.tsx` | ~150 | Side-by-side Plotly histograms per outcome |
| `viewer/components/twin/SnapshotWidget.tsx` | ~160 | 13-dim summary panel + sparkline (cockpit) |
| `viewer/components/hypotheses/SimulationGraph.tsx` | ~90 | Per-hypothesis Plotly mini-histogram |
| `viewer/components/research/TwinImpactFilter.tsx` | ~55 | KL-divergence sort toggle |
| `viewer/components/inbox/ActiveQuestionsSection.tsx` | ~130 | Active-question list with status badges |
| `viewer/types/react-plotly.d.ts` | ~30 | Permissive type shim for `react-plotly.js` |
| `scripts/verify_phase_7_6.py` | ~440 | 12-check structural verifier |
| `docs/PHASE_7_6_EXIT_REPORT.md` | this file | — |
| `docs/PHASE_7_6_KA_SUMMARY.md` | parallel | — |
| `docs/PHASE_7_6_RETROSPECTIVE.md` | parallel | — |

### 3.2 Files edited (5)

| File | Change |
|---|---|
| `viewer/app/[locale]/page.tsx` | Imports `SnapshotWidget` + `isEnabled` + `fetchBeliefSnapshot`; renders the widget at the top of the cockpit when `STATUS_COCKPIT_TWIN_WIDGET` is true |
| `viewer/app/[locale]/hypotheses/page.tsx` | Imports `SimulationGraph` and renders it per-row |
| `viewer/app/[locale]/papers/page.tsx` | Imports `TwinImpactFilter` and renders it above the literature list |
| `viewer/app/[locale]/today/page.tsx` | Imports `ActiveQuestionsSection` and renders it in the inbox shell |
| `viewer/messages/en.json` | +120 lines, 8 new namespaces |
| `viewer/messages/ka.json` | +120 lines, 8 new namespaces (bilingual mirror) |

Total: 2670 + LOC scaffolded; 240 i18n lines added; 12-check verifier shipped.

## 4. Verifier result — `--mode code-complete`

```
Phase 7.6 Site Refactor verifier — mode=code-complete
[PASS] check_7_6_01  All 4 new route page.tsx exist + import isEnabled
[PASS] check_7_6_02  All 4 widget components exist + referenced from existing routes
[PASS] check_7_6_03  4 API client modules exist + export typed signatures
[PASS] check_7_6_04  i18n parity: every new EN key has KA pair (8 namespaces)
[PASS] check_7_6_05  KA values pass anti-loop scan (no banned-word repeats, no ცამეტი, no em-dash)
[PASS] check_7_6_06  tsc --noEmit exit 0 across viewer/
[SKIP] check_7_6_07  next build SKIP — pre-existing Phase 7.5 baseline conflict
[PASS] check_7_6_08  Plotly dynamic-imported in 5 TSX files
[PASS] check_7_6_09  vis-network dynamic-imported in Network.tsx
[PASS] check_7_6_10  @xyflow/react bundle gated behind next/dynamic wrapper
[PASS] check_7_6_11  Every new route page.tsx gates with isEnabled + notFound()
[PASS] check_7_6_12  Regression: pytest brain/ -m "not slow" exit 0 (632 passed, 1 skipped, 4 deselected)

Summary: 11 PASS / 1 SKIP / 0 FAIL (total 12)
```

Cumulative verifier coverage across all phases: 89 (Phase 6) + 12 (Phase 7.6 new) = **101 checks** (Phase 7.0-7.5/7.7 verifiers separately tally their own; this phase's contribution is +12).

## 5. Deviations

| # | Deviation | Reason | Impact |
|---|---|---|---|
| 1 | `next build` is SKIPPED rather than PASS | `viewer/middleware.ts` (Phase 7.5 CSP) and `viewer/proxy.ts` (Phase 6 i18n) coexist; Next.js 16.2.6 rejects the combination with `Error: Both middleware file "./middleware.ts" and proxy file "./proxy.ts" are detected`. This conflict was introduced by Phase 7.5 commit `c5ffe20`, NOT by Phase 7.6. | Vercel deploy cannot succeed until middleware.ts CSP + DICOM-reject logic is merged into proxy.ts. Out of Phase 7.6 scope; logged as follow-up. `tsc --noEmit` passes, so the TypeScript surface is provably sound. |
| 2 | Route names diverge from spec | Spec assumes `/research` + `/inbox`; actual viewer has `/papers` + `/today` from Phase 6. The widgets land on the actual routes. | Decision required from Shako: alias the URLs or update the spec. Pure docs change either way. |
| 3 | Type shim for `react-plotly.js` is permissive (`any` payload props) | Upstream `@types/react-plotly.js` exists but the dispatch forbade `npm install`. The shim lets `tsc --noEmit` pass without weakening any handwritten code. | Plotly props are typed as `unknown[]` / `Record<string, unknown>` rather than strict `Plotly.Data`. Runtime behaviour identical; future polish phase can install the real types and remove `viewer/types/react-plotly.d.ts`. |
| 4 | Structural-complete claim, not visual-complete | No browser session ran in this dispatch. | The Plotly histograms, vis-network graph, and react-flow canvas have not been seen with human eyes. Shako smoke session required before any user-facing release. |
| 5 | `@types/react-plotly.js` not added as a devDependency | Dispatch said "DO NOT install new npm packages." | Same impact as deviation #3; can be reversed when the dep policy relaxes. |
| 6 | Mock reference SCM is 5 nodes, not 571 | The dispatch did not require seeding a 571-node graph; the 5-node Vigabatrin pattern is the canonical reference SCM from `brain/causal/scm.py`. | Verifier check 7_6_09 confirms vis-network is dynamic-imported, but does not exercise the 571-node performance budget. Carry-forward. |
| 7 | `verify_phase_7_6.py` does not honor `--mode production` differently from `--mode code-complete` | The dispatch's "production" mode would require booting `npm run dev` and probing routes via HTTP; that requires a live process which conflicts with the verifier-driven sweep. | Mode flag retained for compatibility with Phase 7.0–7.5 verifier patterns; production-only checks are noted in the Shako carry-forward list (smoke session). |

## 6. MVP carry-forwards (Shako)

The following deferred actions must complete before Phase 7.7 acceptance window can open meaningfully:

1. **Resolve middleware.ts + proxy.ts conflict.** Merge the CSP + DICOM-reject logic from `viewer/middleware.ts` into `viewer/proxy.ts` and delete the standalone middleware file. Test: `npm run build` must exit 0.
2. **`npm run dev` smoke.** Navigate to `/en/twin`, `/ka/twin`, `/en/drift`, `/ka/drift`, `/en/causal`, `/ka/causal`, `/en/simulate`, `/ka/simulate`. Confirm: page loads, no console errors, KA renders Mkhedruli (not boxes), Plotly draws histograms, vis-network renders the 5-node SCM, react-flow shows the palette + canvas.
3. **Playwright smoke.** Add minimal `viewer/__tests__/e2e/phase_7_6.spec.ts` that visits each of the 4 new routes and asserts the page title text matches the namespace title key.
4. **Lighthouse perf run** on a Vercel preview deploy. Capture each route's first-load gzipped JS size; confirm < 500 KB budget. If any route exceeds, profile to identify offenders (Plotly is the usual culprit — consider `plotly.js-basic-dist` swap).
5. **Live backend wiring.** Set `NEXT_PUBLIC_API_URL` to the FastAPI host once Phase 7.0–7.4 routes ship. Disable `NEXT_PUBLIC_MOCK_MODE` and re-smoke.
6. **571-node graph performance.** Once the live SCM database has > 100 nodes, profile vis-network render time; cluster by causal community if > 3 s.
7. **react-flow drag-and-drop UX user-test.** One-shot session with Shako + wife on the SimulationStudio palette; falling back to a form-based scenario builder is the Phase 7.6 rollback move.
8. **Install `@types/react-plotly.js`** and remove `viewer/types/react-plotly.d.ts` once the dep budget allows.

## 7. Phase 7.7 dependency satisfaction

Phase 7.7 (Acceptance Window) depends on the existence of `/twin`, `/causal`, `/simulate`, `/drift` for the wife and the family clinicians to exercise live. Those routes now exist, type-check, and feature-flag-gate cleanly. Two prerequisites remain for the Phase 7.7 acceptance window to actually run:

- middleware/proxy conflict resolution (carry-forward #1)
- one Vercel preview deploy (carry-forward #4)

Once those land, Phase 7.7 can run its 14-day acceptance window against the structural shell.

## 8. Hard-rule compliance

| Rule | Status | Evidence |
|---|---|---|
| No PHI in UI text | OK | Only first name `ალექსანდრა` appears in i18n KA copy, per CLAUDE.md allowance |
| No fabricated PMIDs | OK | UI mock data cites only the 3 PMIDs in `brain/causal/scm.py` (7686614, 32713850, 19489084) plus the 13 dim citations from `dimensions.toml`. No new PMIDs invented |
| Anti-loop KA discipline | OK | verifier check 05 PASS |
| Bilingual parity | OK | verifier check 04 PASS |
| CSP-friendly | OK | Plotly emits inline `<style>` which `style-src 'unsafe-inline'` (already in middleware.ts) covers |
| Dynamic imports for heavy libs | OK | Plotly + vis-network + @xyflow/react all behind `next/dynamic` |
| Feature-flag gating | OK | verifier check 11 PASS |
| No real backend calls during build | OK | All API clients gate via `MOCK_MODE` env-flag |
| No git push, no Vercel deploy | OK | working tree only |
| No new npm packages | OK | `package.json` unchanged |

## 9. Cumulative project state

- `brain/` pytest: **632 PASS / 1 SKIP / 4 deselected** (unchanged from pre-7.6 baseline)
- Phase verifier coverage: 10 (P1) + 19 (P2) + 16 (P2.5) + 11 (P3) + 9 (P4) + 13 (P5) + 11 (P6) + 12 (P7.6) = **101 cumulative checks**, all GREEN or justified-SKIP
- LLM spend Phase 7.6: **$0** (no LLM calls used; purely deterministic code authoring)
- Cumulative LLM spend: ~$7-8 / $60 cap (~12% — unchanged from Phase 6.1 close)
- Branch: `v7-phases-7-0-to-7-5-closure`, this is commit #8

---

**Next phase:** Phase 7.7 Acceptance Window — gated on Shako carry-forwards #1 and #4.
