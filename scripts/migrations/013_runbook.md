# Migration 013 Operator Runbook

> **Purpose.** Deterministic operator manual Shako follows to backfill
> genuine Georgian content into the 6 JSONB columns migration 012
> deterministically mirrored (`ka = en`). Plan 06.1-03 authored both this
> runbook and the script (`scripts/migrations/013_backfill_ka_translations.py`).
> Plan 06.1-03 Task 3 (autonomous=false, BLOCKING) is the wave-2 step that
> actually runs these commands.

**Audience:** one operator (Shako), one terminal, one production Postgres URL.

## Prerequisites

- `SUPABASE_DB_URL` = service-role connection string (same env var as
  `012_runbook.md` / `scripts/communicator/weekly_brief.py`; no new credential).
- `ANTHROPIC_API_KEY` set with a real key. Without it the script bypasses
  Anthropic and emits `[KA-PLACEHOLDER] …` — **NOT acceptable for the live run.**
- Local clone on `main`, clean tree (or only the migration artifacts you are
  about to commit).
- `psycopg2` + `anthropic` Python packages installed (already in the
  Communicator venv).
- Estimated LLM spend: ~$0.6–1.2 for ~31 rows × ~2 fields × ~$0.01–0.02 each.
  `check_daily_budget(raise_on_over=True)` fires INSIDE `compose_bilingual`
  before each Anthropic call (FND-04 ceiling); BudgetExceeded rolls back the
  whole transaction.

## Phase 0 — Confirm starting state (no DB writes yet)

```bash
git status --short
# expected: empty (or only the artifacts you will commit)

echo "${SUPABASE_DB_URL%%@*}@<REDACTED>"
psql "$SUPABASE_DB_URL" -c "SELECT current_database(), current_user;"
# current_user must be the service-role user, NOT 'anon' / 'authenticated'

psql "$SUPABASE_DB_URL" -c "
  SELECT 'aleksandra_timeline.title' AS col, pg_typeof(title) FROM aleksandra_timeline LIMIT 1;"
# expected: jsonb. If text → migration 012 is NOT applied; STOP and fix.
```

## Fresh backup (before any writes)

Per-table data dumps of the 3 affected tables to
`scripts/migrations/013_rollback/{table}.pre013.dump`. (`briefs` is NOT
touched by 013.)

```bash
mkdir -p scripts/migrations/013_rollback
for tbl in aleksandra_timeline hypotheses therapies; do
  pg_dump "$SUPABASE_DB_URL" \
    --table="$tbl" \
    --data-only \
    --column-inserts \
    --no-owner --no-privileges \
    --file="scripts/migrations/013_rollback/$tbl.pre013.dump"
done

for tbl in aleksandra_timeline hypotheses therapies; do
  test -s "scripts/migrations/013_rollback/$tbl.pre013.dump" \
    && head -1 "scripts/migrations/013_rollback/$tbl.pre013.dump"
done
# expected: each file non-empty, first line "-- PostgreSQL database dump"
```

## Dry-run preview (no writes, $0)

Stub mode — `compose_bilingual` returns `[KA-PLACEHOLDER] …` but the script
still walks every eligible row so you can see counts:

```bash
BILINGUAL_TEST_MODE=1 python -m scripts.migrations.013_backfill_ka_translations --dry-run
```

Expected output:

```
=== migration 013 — DRY RUN — no writes, $0 spend (test-mode stub) ===

  [DRY] aleksandra_timeline.title id=...…: en='…' → ka='[KA-PLACEHOLDER] …'
  …

=== per-table summary ===
table.column                              scanned eligible  updated  blocked  skipped
aleksandra_timeline.title                       N        K        0        0      N-K
aleksandra_timeline.description                 …        …        …        …        …
hypotheses.title                                …        …        …        …        …
hypotheses.description                          …        …        …        …        …
therapies.name                                  …        …        …        …        …
therapies.evidence_summary                      …        …        …        …        …

DRY RUN complete — no writes, rollback issued.
```

Record the `eligible` counts — they should match `updated` in the live run.

## Live backfill

```bash
python -m scripts.migrations.013_backfill_ka_translations
```

Expected: header `=== migration 013 — LIVE BACKFILL ===`, per-row `[DRY]`
lines absent (writes happen silently), per-table summary with `updated`
counts matching dry-run eligible (minus any `blocked` rows), final line
`LIVE BACKFILL complete — transaction committed.`

Runtime at current row counts (~31 rows total): under 1 minute (mostly
Anthropic latency). If `check_daily_budget` raises BudgetExceeded → entire
transaction rolls back, no partial writes.

## Post-check (sample ka != en)

```bash
psql "$SUPABASE_DB_URL" -c "
  SELECT id, title->>'en' AS en, title->>'ka' AS ka
  FROM aleksandra_timeline
  WHERE title->>'en' <> title->>'ka' LIMIT 5;
"
# expected: ka now genuine Georgian, distinct from en, NOT containing '[KA-PLACEHOLDER]'

# Repeat for hypotheses.title and therapies.name
psql "$SUPABASE_DB_URL" -c "
  SELECT id, title->>'en' AS en, title->>'ka' AS ka
  FROM hypotheses
  WHERE title->>'en' <> title->>'ka' LIMIT 5;
"

psql "$SUPABASE_DB_URL" -c "
  SELECT id, name->>'en' AS en, name->>'ka' AS ka
  FROM therapies
  WHERE name->>'en' <> name->>'ka' LIMIT 5;
"
```

## Idempotency check

```bash
python -m scripts.migrations.013_backfill_ka_translations
```

Expected: every table's `eligible` count = 0 (all already translated). If
any row still shows eligible, investigate before re-running.

## Rollback procedure

The migration writes only JSONB CONTENT (no column-type change), so rollback
is a per-table data restore from the pre013 dumps. No schema TYPE revert
needed (012 already made these columns JSONB).

```bash
for tbl in aleksandra_timeline hypotheses therapies; do
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 <<SQL
BEGIN;
DELETE FROM $tbl;
SQL
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
    -f "scripts/migrations/013_rollback/$tbl.pre013.dump"
  psql "$SUPABASE_DB_URL" -c "COMMIT;"
done

# Re-run smoke 1 from Phase 0 — pg_typeof still jsonb (012 unaffected).
# Re-run idempotency — eligible counts should be >0 again (all rows back to ka=en).
```

After rollback, file an incident note in `.handoffs/` describing what
failed and why; the next attempt can re-run after the root cause is fixed.

## What 06.1-03 checkpoint does (handoff contract)

The [BLOCKING] task in Plan 06.1-03 runs Phase 0 → Fresh backup → Dry-run →
Live → Post-check → Idempotency end-to-end. The plan is `autonomous: false`
— Shako must be at the keyboard with `SUPABASE_DB_URL` + `ANTHROPIC_API_KEY`.
After all steps pass, Shako types `approved`; if rollback ran, types
`rollback executed` with the failure mode.

## Quick reference card

| Action | Command |
|--------|---------|
| Confirm jsonb shape | `psql "$SUPABASE_DB_URL" -c "SELECT pg_typeof(title) FROM aleksandra_timeline LIMIT 1;"` |
| Fresh backup | `pg_dump … --table=X --data-only --column-inserts --file=scripts/migrations/013_rollback/X.pre013.dump` |
| Dry-run preview | `BILINGUAL_TEST_MODE=1 python -m scripts.migrations.013_backfill_ka_translations --dry-run` |
| Live backfill | `python -m scripts.migrations.013_backfill_ka_translations` |
| Post-check ka | `psql "$SUPABASE_DB_URL" -c "SELECT title->>'en', title->>'ka' FROM aleksandra_timeline WHERE title->>'en' <> title->>'ka' LIMIT 5;"` |
| Idempotency | re-run the live command; expected eligible=0 |
| Rollback data | `psql … DELETE; psql … -f X.pre013.dump; COMMIT` |
