# Branch C resolution — no migration needed

**Date:** 2026-05-19
**Decision:** Branch C.1 (write migration 012) NOT executed. Replaced by Branch C.2 (no-op — confirmed no real drift).

## Audit claim revisited

`.planning/AUDIT_2026-05-18.md` §4.1 reported:
> Tables that **do not exist** in `public` schema (queried, errored with "Could not find the table"): `llm_call`, `citations`, `digest_to_run_link`, `telegram_history`, `email_log`, `firecrawl_calls`.

This was probed with `supabase.table(name).select('*', count='exact').limit(1).execute()`. The error confirmed those names are not tables.

## What the code actually expects

Grep evidence run 2026-05-19 against `scripts/`:

| Name | Real form | Citation |
|---|---|---|
| `llm_call` | `runs.kind = 'llm_call'` discriminator value | `scripts/cognition/llm.py:103` writes `"kind": "llm_call"` into the existing `runs` table |
| `citations` | a `list[str]` field on `BriefSections` / `Draft` / `Summary` dataclasses; serialized into `outreach_log.evidence_refs` and PDF appendix | `scripts/communicator/summarize.py:61`, `weekly_brief.py:131`, `outreach_drafter.py:556` |
| `digest_to_run_link` | not a table; migration 010 (`010_delivery_originating_run_id.sql`) added an `originating_run_id` column to existing delivery tables instead | `scripts/migrations/010_delivery_originating_run_id.sql:42` |
| `telegram_history` | `runs.kind='telegram_send'` (or similar) — no separate table | no `FROM telegram_history` query in `scripts/` |
| `email_log` | conceptually replaced by `outreach_log` (Phase 3 migration 008) | no `FROM email_log` query in `scripts/` |
| `firecrawl_calls` | `runs.kind='firecrawl_call'` discriminator | no `FROM firecrawl_calls` query; `verify_phase1` PRC-08 sums `runs` filtered by kind |

**No `.table('llm_call')` / `FROM llm_call` query exists in the codebase.** Same for the other 5.

## Why the audit got confused

My audit Phase 4.1 probe iterated a list of "tables I'd expect to see in this schema." That list was generated from CLAUDE.md + earlier discussion text, NOT from a `\d` schema dump or a grep of actual `.table(...)` / `FROM ...` calls in code. The list contained names that the codebase uses as `kind` discriminator values inside the `runs` table, not as standalone tables.

The verifier scripts (`verify_phase1..5`) never query these names as tables. None of the 73 passing checks depend on them. CGM-01's failure was unrelated (Qdrant 403, fixed in R0.7).

## Consequence for MASTER_PLAN.md

- **RISK-05** ("6 missing Supabase tables — code references may silently fail") → DOWNGRADE from M/M to L/L (no risk).
- **R2.4** ("Triage 6 missing tables") → reframe as documentation cleanup. Either:
  - Add a `.planning/SCHEMA_NOTES.md` documenting that `runs.kind` values include `llm_call`, `telegram_send`, `firecrawl_call`, etc.
  - Or update the audit to remove the misleading "missing tables" framing.
- **Branch C in MASTER §5** → resolved as C.3 (no action). Branch C.1 and C.2 not executed.

## What WAS confirmed by this investigation

Real migrations applied through 011:
- 001 runs append-only
- 002 aleksandra_timeline
- 003 evidence_ledger
- 004 kv_state
- 005 paper_chunks
- 006 citation_tuple  ← note: this IS a table (singular `citation_tuple`, not the misnamed plural `citations`)
- 007 runs_token_cost_precision
- 008 phase3_tables_and_rls
- 009 runs_digest_id
- 010 delivery_originating_run_id
- 011 manager_actions_and_intake_drops

Schema is at version 011. No pending migrations. No drift.

---

*Resolved by Claude during R0 execution, 2026-05-19. No code or DB change required.*
