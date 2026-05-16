# Phase 2.5 Exit Report

**Date closed:** 2026-05-16
**Scope:** Quick Wins Sprint — spend instrumentation, perception scale-up, family-visible layer, validation workflow.

## Verdict

Phase 2.5 is closed: **16/16 PASS** in `scripts.verify_phase2_5 --gate all`.

| Gate | Result | Evidence |
| --- | --- | --- |
| A — Spend Instrumentation | 3/3 PASS | `runs.token_cost` is `NUMERIC(14,8)`; budget reader works; positive-cost LLM row exists |
| B — Perception Scale-up | 4/4 PASS | 326 ledger rows, 255 papers, 5301 chunks, 5302 Qdrant vectors, 568 Neo4j entities |
| C — Family-Visible Layer | 4/4 PASS | `/dashboard`, RLS smoke, daily digest run, urgent alert run |
| D — Validation Workflow | 4/4 PASS | `/hypotheses`, 5 confirmed research hypotheses, 10 DSPy JSONL examples, 10/10 supporting-paper hydration |
| Regression | PASS | Phase 2 verifier remains 19/19 PASS |

## What Changed

- Added the family dashboard route: `viewer/app/dashboard/page.tsx`.
- Added the hypothesis validation route and server action: `viewer/app/hypotheses/page.tsx`.
- Added server-only Supabase REST helpers in `viewer/lib/supabase.ts`.
- Added urgent alert workflow template: `workflows/urgent_alerts.json`.
- Added local family workflow fire helper: `scripts/family_visibility/fire_workflows.py`.
- Added deterministic validation finalizer: `scripts/phase2_5/finalize_validation.py`.
- Generated 10 DSPy training examples under `scripts/hypothesis/dspy_training/`.
- Hydrated live `hypotheses.supporting_papers` to 10/10 and marked 5 evidence-linked hypotheses `confirmed`.

`confirmed` means research evidence links were curated for follow-up. It is not clinical approval or a treatment recommendation.

## Verification Run

```powershell
.venv\Scripts\python.exe -X utf8 -m scripts.verify_phase2_5 --gate all
# 16/16 PASS — ALL GREEN

.venv\Scripts\python.exe -X utf8 -m scripts.verify_phase2 --gate all
# 19/19 PASS — ALL GREEN

cd viewer
npm run build
# /, /dashboard, /hypotheses build successfully
```

## Phase 3 Entry

The repo is ready to start Phase III Cognition Minimum.

Recommended first Phase 3 work:

1. Define `scripts.verify_phase3` with CGM-01.. gates before implementation.
2. Add Analyzer PICO extraction and source-quality ranking.
3. Add Communicator output schema with PHI redaction and clinician-decision language.
4. Enforce imperative-verb lint on recommended actions.
5. Promote only HIGH evidence through the confidence gate.
