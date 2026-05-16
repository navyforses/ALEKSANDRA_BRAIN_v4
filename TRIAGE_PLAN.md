# ALEKSANDRA_BRAIN Phase 3 Readiness Sprint Triage

Date: 2026-05-16
Manager: BRAIN_MANAGER
Budget cap: $3 total LLM spend, hard stop at $2.50
Time cap: 8 hours

## Baseline

- `verify_phase1.py`: 10/10 passing in discovery audit
- `verify_phase2.py`: 19/19 passing in discovery audit
- `verify_phase2_5.py`: 16/16 passing in discovery audit
- Known live budget issue: Python wrapper writes `runs.kind = 'llm_call'`, while `workflows/daily-budget-gate.json` only counts `agent_run` and `fire_drill`
- No Phase 3 implementation is approved in this sprint

## Agent Work Breakdown

### CLEANUP_AGENT

Owned files:

- `workflows/daily-budget-gate.json`
- `.env.example`

Tasks:

- Fix the n8n budget gate query so it counts `llm_call`
- Add `CLOUDFLARE_R2_ENDPOINT` to `.env.example`
- Identify stale files, but do not delete them until scope decisions are approved

### SECURITY_AGENT

Owned files:

- Read-only audit unless a security document is requested by Manager

Tasks:

- Audit RLS policy definitions in SQL files
- Identify possible anon exposure
- Confirm `.env` is ignored
- Run or inspect the local secret scan path
- Report concrete commands and results

### SCOPE_DECISION_AGENT

Owned files:

- `.planning/ROADMAP.md` only after Manager approval

Tasks:

- Classify unplanned work as keep, remove, formalize, or investigate
- No deletion authority

### DOCUMENTATION_AGENT

Owned files:

- `CLAUDE.md`
- `README.md`
- `.planning/ROADMAP.md`
- `docs/` documentation files

Tasks:

- Align docs with verified Phase 2.5 reality
- Archive outdated reports instead of deleting them
- Keep claims evidence-based

### FEATURE_GAP_AGENT

Owned files:

- `viewer/app/papers/page.tsx`
- `viewer/app/therapies/page.tsx`
- `viewer/app/timeline/page.tsx`
- Shared viewer helpers only with Manager approval

Tasks:

- Build minimal read-only routes for papers, therapies, and timeline
- No `/brain` implementation; document deferment to Phase 4
- No new dependencies

### PHASE_3_ARCHITECT

Owned files:

- `docs/PHASE_3_PLAN.md`
- `docs/PHASE_3_HANDOUT.md`

Tasks:

- Define Phase 3 from current reality
- Scope communicator activation, alert refinement, outreach automation, and weekly brief PDF
- Include budget, timeline, dependency map, and quality gates

### VERIFIER_AGENT

Owned files:

- No source edits

Tasks:

- Run `verify_phase1.py`, `verify_phase2.py`, `verify_phase2_5.py`
- Check viewer routes after frontend changes
- Maintain green-status log in reports to Manager

## Dependency Graph

1. Budget gate fix and `.env.example` update can start immediately.
2. Security audit can run in parallel with cleanup and docs.
3. Scope decisions must complete before any stale-code deletion.
4. Documentation can update completion state immediately, but should absorb scope decisions before final pass.
5. Feature routes can be built in parallel with docs because they write disjoint files.
6. Phase 3 plan can start once scope decisions are drafted; final plan must reflect approved classifications.
7. Final Georgian readiness report waits for verification and Manager review.

## Parallel Execution Plan

- Stage 2 parallel batch: CLEANUP_AGENT, SECURITY_AGENT, DOCUMENTATION_AGENT, VERIFIER_AGENT baseline.
- Stage 3 parallel sidecar: SCOPE_DECISION_AGENT while Manager reviews cleanup/security.
- Stage 4 parallel implementation: FEATURE_GAP_AGENT and PHASE_3_ARCHITECT, with disjoint file ownership.
- Stage 6 final batch: VERIFIER_AGENT full regression plus Manager route checks.

## Quality Gates

- After budget workflow edits: run Phase 2.5 verifier and inspect budget query manually.
- After documentation edits: run grep checks for stale Phase 2.5 claims.
- After frontend route edits: run viewer lint/build if available and check each route returns 200.
- Before final report: run all three phase verifiers.
- Any verifier failure blocks sprint completion.

## Scope Rules

- No code deletion until SCOPE_DECISION_AGENT classification and Manager approval.
- No database schema change without a migration file and explicit Manager approval.
- No new dependencies.
- No Phase 3 implementation work.
- Any unplanned file write must be reported before merge.
