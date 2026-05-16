# Phase 3 Readiness

**Snapshot date:** 2026-05-16
**Status:** Phase 3 Cognition Minimum is ready to start.

## Verified Gates

| Gate | Result | Current evidence |
| --- | --- | --- |
| Phase 1 Perception | 10/10 PASS | `.venv\Scripts\python.exe -X utf8 -m scripts.verify_phase1` |
| Phase 2 Memory | 19/19 PASS | `.venv\Scripts\python.exe -X utf8 -m scripts.verify_phase2 --gate all` |
| Phase 2.5 Quick Wins | 16/16 PASS | `.venv\Scripts\python.exe -X utf8 -m scripts.verify_phase2_5 --gate all` |

Phase 2.5B/C/D are complete:

- **B — Perception Scale-up:** 326 ledger rows, 5301 chunks, 5302 Qdrant vectors, 568 Neo4j entities.
- **C — Family-visible layer:** dashboard route, RLS smoke, daily digest fire, urgent alert fire.
- **D — Validation workflow:** hypotheses route, 5 confirmed hypotheses, 10 DSPy examples, 10/10 supporting-paper hydration.

## Budget Caveat

Phase 2.5A spend instrumentation is closed at the verifier level:
`runs.token_cost` precision is fixed, `check_daily_budget()` works, and at least
one positive-cost `llm_call` row exists.

The n8n `daily-budget-gate` workflow still has an operational JSON-body
expression bug being fixed outside this documentation pass. Do not treat that
workflow as fully repaired until the workflow owner confirms the deployed n8n
node writes `budget_lock` rows without the simulator. The code-side budget
reader remains active before Anthropic calls.

## Phase 3 Entry Contract

Start Phase 3 with:

1. `scripts.verify_phase3` scaffold for CGM-01 through CGM-10.
2. Deterministic PMID/DOI/NCT/URL round-trip verifier.
3. Analyzer PICO extraction and source-quality ranking.
4. Communicator fixed schema with PHI redaction and clinician-decision language.
5. Imperative-verb lint, six-tier evidence ranking, and HIGH-only confidence gate.

Archived audit snapshots live under `docs/archive/` and should not be used as
current backlog.
