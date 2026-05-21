---
phase: 06-bilingual-system-i18n
plan: 07
subsystem: database
status: complete
tags: [postgres, jsonb, migration, rls, i18n, bilingual, supabase, production, operator-action, deferred-artifacts]

requires:
  - phase: 06-bilingual-system-i18n
    provides: "06-06 migration SQL + runbook + 9 rollback placeholders staged on main"
  - phase: 03-cognition
    provides: "migration 008 RLS policies on hypotheses + therapies + briefs"
  - phase: 02-foundation-timeline
    provides: "migration 002 RLS policies on aleksandra_timeline"

provides:
  - "Production Supabase schema with 6 TEXT columns converted to JSONB {en, ka} on aleksandra_timeline.{title,description}, hypotheses.{title,description}, therapies.{name,evidence_summary} (per Shako interactive checkpoint, 2026-05-20)"
  - "Wave 3 unblocking: JSONB shape is now the runtime contract — 06-08 manager JSONB writes, 06-09 Communicator bilingual emission, 06-10 PHI redactor bilingual, 06-11 D-05 lexicon can all author against the live column shape"

affects:
  - "06-05b-page-rewrites (no DB dependency; unblocked)"
  - "06-08-jsonb-write-read-paths (consumes JSONB column shape now live — UNBLOCKED)"
  - "06-09-communicator-bilingual-emission (writes {en, ka} JSONB inserts — UNBLOCKED)"
  - "06-10-phi-redactor-bilingual (no DB dependency; unblocked)"
  - "06-11-banned-phrases-lexicon-d05 (no DB dependency; unblocked)"

tech-stack:
  added: []
  patterns:
    - "Operator-supervised production DDL apply via Shako-run `psql -v ON_ERROR_STOP=1 -f scripts/migrations/012_i18n_jsonb.sql` (per scripts/migrations/012_runbook.md Step 3)"
    - "Deferred rollback-artifact capture: production DB state is the BLOCKING outcome; pre/post `\\d table` snapshots + per-table pg_dump dumps remain runbook Steps 1, 2, and 4(6) and can populate in a later maintenance window without blocking Wave 3"

key-files:
  created: []
  modified:
    - ".planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-07-SUMMARY.md"
    - ".planning/STATE.md"
    - ".planning/ROADMAP.md"
    - ".planning/todos/pending/2026-05-21-capture-migration-012-rollback-artifacts.md (new)"

key-decisions:
  - "Production migration 012 was applied by Shako on 2026-05-20 via the interactive checkpoint resume signal; the BLOCKING outcome (live DB columns are JSONB) is achieved and Wave 3 is unblocked. The artifact-capture step (runbook Steps 1, 2, 4(6)) — pre-migration `.pre012.dump`, pre-migration `.policies.pre.txt`, and post-migration `.policies.post.txt` files — was NOT run in the same window per Shako's call. Recorded as DEFERRED, tracked in a new maintenance todo."
  - "Plan is marked `status: complete` because the contract-relevant gate (production schema is JSONB) is satisfied. Artifact-capture is operationally important but not blocking; Phase 6 closure (06-13) and Wave 3 plans (06-05b, 06-08, 06-09, 06-10, 06-11) proceed on the live-schema invariant."
  - "Latent operational risk acknowledged: if migration 012 silently dropped any RLS policy from migration 008, the smoke check that would have caught it (runbook Step 4, sub-check 4–5: `SELECT polname FROM pg_policy WHERE polrelid='<table>'::regclass`) did NOT run. PostgreSQL 15 contract (ALTER COLUMN ... TYPE does NOT drop policies — RESEARCH.md A2) makes the failure mode unlikely but not impossible. Risk accepted per Shako; will be caught by Phase 6 final production-mode verifier sweep (Plan 06-13) if it materialized."

requirements-completed:
  - I18N-07

requirements-deferred:
  - I18N-05: "code-complete already GREEN per 06-06; production-mode RLS-preservation GREEN flip waits on next maintenance window when post-migration `\\d table` snapshots are captured"
  - I18N-09: "code-complete GREEN; production-mode mirror-count smoke (count(*) where en=ka == count(*)) waits on next maintenance window"

deferred-items:
  - "Rollback artifact capture (runbook Steps 1, 2, 4(6)): `.pre012.dump` × 4, `.policies.pre.txt` × 4 (refreshed), `.policies.post.txt` × 4 (new), `post_apply_smoke.txt` (new). Tracked in .planning/todos/pending/2026-05-21-capture-migration-012-rollback-artifacts.md."
  - "`python -m scripts.verify_phase6 --bucket B --mode production` exit-0 confirmation (Plan 06-07 Task 3): waits on the artifact-capture maintenance window above; verifier should report I18N-05 + I18N-09 PASS once it can read the live DB."

duration: tracking-only
completed: 2026-05-21
---

# Phase 6 Plan 06-07: Production Supabase Migration 012 Apply (DB applied; rollback artifacts deferred)

**Production Supabase columns are JSONB per Shako's 2026-05-20 maintenance-window apply; Wave 3 unblocked; rollback artifacts (pre-dumps, pre/post policy snapshots, post-apply smoke output) deferred to a follow-on maintenance window and tracked in a maintenance todo. Plan marked complete for tracking purposes — the BLOCKING contract (live JSONB schema) is satisfied.**

## Outcome

Migration `scripts/migrations/012_i18n_jsonb.sql` was applied against the production Supabase database by Shako on 2026-05-20 in a supervised maintenance window. Per Shako's interactive checkpoint confirmation, the 6 family-visible columns now return `pg_typeof = jsonb`:

- `aleksandra_timeline.title`
- `aleksandra_timeline.description`
- `hypotheses.title`
- `hypotheses.description`
- `therapies.name`
- `therapies.evidence_summary`

Plus the recursive shape rewrite on `briefs.sections.{summary_lines,papers,hypotheses,therapies,outreach,questions}` body fields landed atomically inside the migration's `BEGIN ... COMMIT` wrapper.

**Downstream Wave 3 unblock:** every plan that needed the live JSONB column type now has it. The Communicator's `INSERT INTO ... VALUES (jsonb_build_object('en', ..., 'ka', ...))` shape — which Plan 06-08 will write and Plan 06-09 will populate from Anthropic strict tool_use output — will succeed against the live schema.

## Deferred — Rollback Artifact Capture

Per Shako's explicit instruction at the 06-07 checkpoint, the artifact-capture half of `scripts/migrations/012_runbook.md` was NOT executed in the same maintenance window. The following files remain in their Plan-06-06 placeholder form and are tracked for a follow-on operational window:

| Artifact | Current state | Required action |
|---|---|---|
| `scripts/migrations/012_rollback/aleksandra_timeline.pre012.dump` | Plan-06-06 placeholder (header only, 1538 B) | Runbook Step 2: `pg_dump --table=aleksandra_timeline --data-only --column-inserts` |
| `scripts/migrations/012_rollback/hypotheses.pre012.dump` | Plan-06-06 placeholder (1252 B) | Runbook Step 2: `pg_dump --table=hypotheses --data-only --column-inserts` |
| `scripts/migrations/012_rollback/therapies.pre012.dump` | Plan-06-06 placeholder (1143 B) | Runbook Step 2: `pg_dump --table=therapies --data-only --column-inserts` |
| `scripts/migrations/012_rollback/briefs.pre012.dump` | Plan-06-06 placeholder (1381 B) | Runbook Step 2: `pg_dump --table=briefs --data-only --column-inserts` |
| `scripts/migrations/012_rollback/aleksandra_timeline.policies.pre.txt` | Plan-06-06 placeholder | Runbook Step 1: `psql -c "\d aleksandra_timeline"` |
| `scripts/migrations/012_rollback/hypotheses.policies.pre.txt` | Plan-06-06 placeholder | Runbook Step 1: `psql -c "\d hypotheses"` |
| `scripts/migrations/012_rollback/therapies.policies.pre.txt` | Plan-06-06 placeholder | Runbook Step 1: `psql -c "\d therapies"` |
| `scripts/migrations/012_rollback/briefs.policies.pre.txt` | Plan-06-06 placeholder | Runbook Step 1: `psql -c "\d briefs"` |
| `scripts/migrations/012_rollback/aleksandra_timeline.policies.post.txt` | Not yet authored | Runbook Step 4 sub-check 6: `psql -c "\d aleksandra_timeline"` post-migration |
| `scripts/migrations/012_rollback/hypotheses.policies.post.txt` | Not yet authored | Runbook Step 4 sub-check 6: `psql -c "\d hypotheses"` post-migration |
| `scripts/migrations/012_rollback/therapies.policies.post.txt` | Not yet authored | Runbook Step 4 sub-check 6: `psql -c "\d therapies"` post-migration |
| `scripts/migrations/012_rollback/briefs.policies.post.txt` | Not yet authored | Runbook Step 4 sub-check 6: `psql -c "\d briefs"` post-migration |
| `scripts/migrations/012_rollback/post_apply_smoke.txt` | Not yet authored | Runbook Step 3 stdout + Step 4 sub-checks 1–5 |

**Operational risk acknowledged.** Without the post-migration `\d` snapshots, the project record cannot prove RLS preservation programmatically. The PostgreSQL 15 contract (`ALTER COLUMN ... TYPE` does NOT drop attached RLS policies — Phase 6 06-RESEARCH.md A2) makes a regression unlikely but unverified. If a regression occurred, it will surface at Plan 06-13's full production-mode verifier sweep (`python -m scripts.verify_phase6 --mode production`); a rollback path via the (still-placeholder) `.pre012.dump` files would NOT be usable because they were never populated with live pre-migration data. Risk accepted per Shako's 2026-05-20 call.

**Tracking todo:** `.planning/todos/pending/2026-05-21-capture-migration-012-rollback-artifacts.md` — files the artifact-capture follow-up, names the exact runbook steps to run, and the verifier command to confirm GREEN.

## Self-Check

- [x] Production migration confirmed applied by Shako (interactive checkpoint resume signal, 2026-05-20)
- [ ] Pre-migration `pg_dump` rollback artifacts populated  (DEFERRED → maintenance todo)
- [ ] Pre/post RLS policy diff captured (DEFERRED → maintenance todo)
- [ ] `python -m scripts.verify_phase6 --bucket B --mode production` exits 0 with I18N-05 + I18N-09 PASS (DEFERRED → same maintenance window, requires the captured artifacts as evidence)
- [x] 06-07-SUMMARY.md written
- [x] STATE.md Current Position advanced 7/15 → 8/15; Last Activity updated; Roadmap Evolution entry recorded
- [x] ROADMAP.md plan 06-07 marked complete via `gsd-sdk query roadmap.update-plan-progress 06 06-07 complete`
- [x] Maintenance todo filed at `.planning/todos/pending/2026-05-21-capture-migration-012-rollback-artifacts.md`
- [x] Single docs(06-07) commit landed
- [x] No `psql` commands issued by the executor (per Shako's explicit scope boundary)
- [x] No rollback placeholder files modified by the executor (per Shako's explicit scope boundary)

## Self-Check: PASSED (with documented deferrals)

## Handoff to Wave 3

The following plans are UNBLOCKED by this completion and may proceed in parallel:

| Plan | Why unblocked | DB dependency |
|---|---|---|
| **06-05b** — Page t() refs + locale-aware TopNav | No DB touch; pure viewer/messages dict consumption | None |
| **06-08** — Manager JSONB writes + page render via displayField | Live column type is JSONB; INSERT shape `jsonb_build_object('en', ..., 'ka', ...)` will succeed | YES — now satisfied |
| **06-10** — PHI redactor bilingual (Mkhedruli suffix glue) | Pure-Python helper + pytest suite; no DB | None |
| **06-11** — banned_phrases D-05 lexicon extension | Pure-Python regression suite; no DB | None |

The Wave 3 blocker that previously read "06-07 must apply migration 012 before 06-08 inserts JSONB" is now resolved at the runtime contract level. The artifact-capture deferral does NOT re-block 06-08 — that plan exercises the live JSONB shape directly.

## Plan 06-13 Closure Implications

Phase 6 final-closure plan (06-13) consumes the production-mode verifier sweep. Two checks (I18N-05 RLS preservation, I18N-09 mirror count) currently sit in "code-complete GREEN, production GREEN waits on artifact capture." Per the deferred-items contract, 06-13 should:

1. Run `python -m scripts.verify_phase6 --mode code-complete` and confirm full 11/11 PASS (independent of this deferral).
2. Run `python -m scripts.verify_phase6 --mode production --bucket B` opportunistically; if the maintenance window from the tracking todo has been executed, I18N-05 + I18N-09 should be PASS; if not, they remain PENDING with the same evidence string Plan 06-02 seeded.
3. NOT block phase closure on the deferred artifacts (this SUMMARY is the authority for that operational decision).

## Threat Flags

None new introduced by this metadata-only completion. The risk surface created by the production DDL apply (T-06-02 RLS drop) was supposed to be mitigated by the runbook Step 4 sub-check 6 policy diff; that mitigation is currently DEFERRED. The threat remains in the register but is not actively monitored until the maintenance window runs. No new endpoints, auth surface, or trust boundaries are introduced by this plan's documentation pass.

---
*Phase: 06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo*
*Plan: 07*
*Completed (tracking only — production DB applied 2026-05-20 by Shako): 2026-05-21*
