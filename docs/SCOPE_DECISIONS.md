# Scope Decisions — Phase 3 Readiness Sprint

**Date:** 2026-05-16
**Author:** BRAIN_MANAGER (Phase 3 Readiness Sprint)
**Status:** Recommendations only. Deletions require an explicit follow-up sprint.

This document classifies work that exists in the repo but was not part of the
original Phase 0–2.5 plan. The goal is to make every leftover artifact either
formally adopted, formally archived, or formally retired before Phase 3 starts.

## Decision Legend

- **KEEP** — Adopt as official scope. Update docs to reflect it.
- **FORMALIZE** — Keep, but write a contract/README and add to roadmap notes.
- **DEFER** — Leave in place; decision postponed to a future phase.
- **INVESTIGATE** — Owner must confirm intent in a small follow-up.
- **REMOVE** — Approved for deletion in a future cleanup sprint. Not removed in
  this sprint per the sprint's "no deletion until classified and approved"
  rule.

## Classification Table

| Item | Path(s) | Status | Decision | Rationale |
| --- | --- | --- | --- | --- |
| Observer bot (diff review) | `scripts/observer/`, `.observer/` | Live tooling, no verifier impact | **FORMALIZE** | Useful guardrail against unreviewed ChatGPT-authored edits. Needs a short README and an explicit `.gitignore` rule for `.observer/state.json` and `.observer/findings/`. |
| Code-review knowledge graph | `.code-review-graph/` | Tooling artifact only | **FORMALIZE** | Should be gitignored if not already; it's an index, not source. |
| `chunking_trigger.json` workflow | `workflows/chunking_trigger.json` | Used by Phase 2.5B chunking pipeline | **KEEP** | Already produces the 5301 chunks the Phase 2.5 verifier asserts. Add a one-line note in ROADMAP under Phase 2.5 deliverables. |
| `extraction_trigger.json` workflow | `workflows/extraction_trigger.json` | Used by Phase 2.5B entity extraction pipeline | **KEEP** | Same reasoning as chunking trigger; supports the 568 Neo4j entities the verifier asserts. |
| Communicator agent skeleton | `agents/communicator.py` | Skeleton only | **FORMALIZE** | Phase 3 plan already names this as Workstream 1. Keep as-is until Phase 3 implementation activates it. |
| Panic MCP (kill-switch) | `mcp/panic_stop.py` | Live, used by `/stop` Telegram contract | **KEEP** | Documented in `docs/RUNBOOK-kill-switch.md`. The Phase 0 FND-03 control. |
| Hello-brain MCP placeholder | `mcp/hello_brain.py` | Phase 0 placeholder | **INVESTIGATE** | Verify it's still referenced. If unused, schedule removal alongside Phase 3 custom-MCP work. |
| Family visibility helpers | `scripts/family_visibility/` | Live, used by Phase 2.5C fire scripts | **KEEP** | Supports the daily-digest + urgent-alert workflow fire helpers tracked by the verifier. |
| One-shot migration scripts | `scripts/migrate_papers.py`, `scripts/migrate_contacts.py` | Legacy | **INVESTIGATE** | If the migrations have already run against production data, move to `scripts/archive/`. Do not delete until confirmed idempotent or obsolete. |
| `scripts/test_all.py` legacy | `scripts/test_all.py` | Legacy convenience runner | **INVESTIGATE** | Replaced in practice by `scripts.verify_phase*` modules. Move to `scripts/archive/` if no docs/scripts call it. |
| Frontend 3D deps at repo root | `three`, `@react-three/*`, `ai` in root `package.json` | Carried over from earlier setup | **DEFER** | They are Phase 4 viewer dependencies. Strip if Phase 4 is delayed; keep for now to avoid re-resolving npm tree later. |
| Phase 3 design docs | `docs/PHASE_3_PLAN.md`, `docs/PHASE_3_HANDOUT.md`, `docs/PHASE_3_READINESS.md` | New in this sprint | **KEEP** | Sprint deliverables. |
| Triage plan | `TRIAGE_PLAN.md` | New in this sprint | **KEEP** | Sprint artifact. Belongs at repo root for visibility during Phase 3 startup. |
| Viewer routes added in this sprint | `viewer/app/papers/`, `viewer/app/therapies/`, `viewer/app/timeline/` | New in this sprint | **KEEP** | Closes the FEATURE_GAP_AGENT scope. Read-only, server-rendered, no schema changes. |

## Notes on Items Not Yet Touched

- **Full LightRAG retrieval merge** — Out of scope for this sprint. Phase 3 plan
  describes the `retrieve(query, t_at=...)` facade as ready; deeper LightRAG
  integration is post-Phase 3.
- **Adaptive Graph of Thoughts MCP** — Deferred. Phase 3 plan does not depend on
  it. Vendor decision pending after Phase 3 minimum is implemented.
- **6-MCP drug repurposing pipeline** — Deferred. Will be its own future sprint
  per the Phase 3 plan.

## Required Follow-up Actions

These are recorded here but do **not** execute in this sprint:

1. Add `.observer/` and `.code-review-graph/` to `.gitignore` if not already.
2. Confirm `mcp/hello_brain.py` is still imported. If not, retire in Phase 3
   custom-MCP work.
3. Confirm `scripts/migrate_*.py` and `scripts/test_all.py` are no longer
   referenced by any runbook or workflow. If not, move to `scripts/archive/`.
4. Phase 4 sprint should re-evaluate root-level `three` / `ai` packages.

## Manager Approval

This document does not delete anything. Every item marked REMOVE or
INVESTIGATE requires an explicit follow-up sprint with a Manager-approved task
that names the file(s), runs a "is this used?" check, and commits the change
atomically.
