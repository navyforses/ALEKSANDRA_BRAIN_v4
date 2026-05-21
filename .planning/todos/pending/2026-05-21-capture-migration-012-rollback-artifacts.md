---
status: pending
created: 2026-05-21
resolves_phase: maintenance
source: .planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-07-SUMMARY.md
owner: Shako (operator) + executor agent (artifact mirror + verifier run)
priority: P2 (operational hygiene; not blocking Wave 3 or Phase 6 closure)
estimated_window: 15-20 minutes (one psql session + one git commit)
runbook: scripts/migrations/012_runbook.md
related_plan: 06-07-migration-012-apply
---

# Capture Migration 012 Rollback Artifacts (post-hoc)

## Context

Plan 06-07 marked **complete** on 2026-05-21 after Shako applied `scripts/migrations/012_i18n_jsonb.sql` against production Supabase on **2026-05-20**. The BLOCKING contract — production columns return `pg_typeof = jsonb` — is satisfied; Wave 3 (Plans 06-05b, 06-08, 06-09, 06-10, 06-11) is unblocked on the live-schema invariant.

However, the artifact-capture half of `scripts/migrations/012_runbook.md` (Steps 1, 2, and 4 sub-check 6) was NOT run in the same maintenance window. The four `scripts/migrations/012_rollback/*.pre012.dump` files and four `scripts/migrations/012_rollback/*.policies.pre.txt` files remain in their Plan-06-06 placeholder form, and four `*.policies.post.txt` files plus one `post_apply_smoke.txt` have not been authored.

**Operational risk.** Without the captured pre/post artifacts:

1. The project record cannot programmatically prove RLS-policy preservation across the migration. PostgreSQL 15's contract (RESEARCH.md A2) says `ALTER COLUMN ... TYPE` does NOT drop policies, so a regression is unlikely — but unverified.
2. If a regression DID occur, the `.pre012.dump` placeholders are NOT usable for the rollback procedure (runbook "Rollback procedure" section) because they were never populated with live pre-migration row data.
3. `python -m scripts.verify_phase6 --bucket B --mode production` cannot reach exit 0 for I18N-05 + I18N-09 until the live DB is read by the verifier (which requires SUPABASE_DB_URL to be set in the executor environment, currently only available in Shako's terminal).

## What to do

Open a 20-minute maintenance window. Set `SUPABASE_DB_URL` to the service-role connection string. Then follow `scripts/migrations/012_runbook.md` post-hoc, skipping Step 3 (apply) which is already done:

### Step 1 (post-hoc) — Snapshot live schema as the new "pre" baseline + new "post" snapshot

> Because the migration is already applied, the live `\d <table>` output captures the POST-migration state. Save it twice: as `.policies.post.txt` (the canonical post-migration snapshot for Plan 06-13 evidence) and as the new `.policies.pre.txt` (which now represents the new operational baseline going forward — older runbook used "pre" to mean pre-012, but since 012 is permanent, the new "pre" is the current state).

```bash
for tbl in aleksandra_timeline hypotheses therapies briefs; do
  psql "$SUPABASE_DB_URL" -c "\d $tbl" \
    > scripts/migrations/012_rollback/$tbl.policies.post.txt
  cp scripts/migrations/012_rollback/$tbl.policies.post.txt \
     scripts/migrations/012_rollback/$tbl.policies.pre.txt
done
```

**Verify** each `.policies.post.txt` contains:
- The line `Policies:` (psql `\d` output format)
- The expected policy names per table:
  - `aleksandra_timeline`: 3 policies (`aleksandra_timeline_family_read`, `aleksandra_timeline_service_update`, `aleksandra_timeline_service_write`)
  - `hypotheses`: 2 policies (`hypotheses_family_read`, `hypotheses_service_all`)
  - `therapies`: 2 policies (`therapies_family_read`, `therapies_service_all`)
  - `briefs`: 2 policies (`briefs_family_read`, `briefs_service_all`) + CHECK constraint `briefs_phi_redacted_chk`

If any expected policy is missing, **STOP — file an incident note** in `.handoffs/` immediately. RLS regression in production is a P0; the migration 008 + 002 policies must be restored before any further bilingual writes land.

### Step 2 (post-hoc) — Capture current-state data dumps as the "pre" rollback artifacts going forward

> The original Plan 06-07 contract was to capture PRE-012 dumps so that a rollback (DELETE + restore from dump + ALTER COLUMN TYPE text) was possible. Since 012 is permanent and tested, the operational meaning of these dumps is now "snapshot of the post-012 state for any future 013/014 rollback scenario." Same command, current data:

```bash
for tbl in aleksandra_timeline hypotheses therapies briefs; do
  pg_dump "$SUPABASE_DB_URL" \
    --table="$tbl" \
    --data-only \
    --column-inserts \
    --no-owner --no-privileges \
    --file="scripts/migrations/012_rollback/$tbl.pre012.dump"
done
```

**Verify** each `.pre012.dump`:
- First line begins `-- PostgreSQL database dump`
- File size > placeholder size (placeholders are 1-2 KB; populated dumps should be 5-30 KB depending on row count)
- No PHI: `briefs.sections` body fields run through `phi_redactor.py` before reaching `briefs` per Phase 5 contract, so the dump is safe to commit. The other 3 tables hold research metadata, not PHI.

### Step 3 (post-hoc) — Capture smoke-check evidence

```bash
{
  echo "# Post-apply smoke check evidence (captured 2026-05-21+ from Shako's maintenance window)"
  echo "# Migration 012 was applied on 2026-05-20; this file evidences current state."
  echo "---"
  psql "$SUPABASE_DB_URL" -c "SELECT 'aleksandra_timeline.title' AS col, pg_typeof(title) FROM aleksandra_timeline LIMIT 1;"
  psql "$SUPABASE_DB_URL" -c "SELECT 'aleksandra_timeline.description' AS col, pg_typeof(description) FROM aleksandra_timeline LIMIT 1;"
  psql "$SUPABASE_DB_URL" -c "SELECT 'hypotheses.title' AS col, pg_typeof(title) FROM hypotheses LIMIT 1;"
  psql "$SUPABASE_DB_URL" -c "SELECT 'hypotheses.description' AS col, pg_typeof(description) FROM hypotheses LIMIT 1;"
  psql "$SUPABASE_DB_URL" -c "SELECT 'therapies.name' AS col, pg_typeof(name) FROM therapies LIMIT 1;"
  psql "$SUPABASE_DB_URL" -c "SELECT 'therapies.evidence_summary' AS col, pg_typeof(evidence_summary) FROM therapies LIMIT 1;"
  psql "$SUPABASE_DB_URL" -c "SELECT count(*) AS mirrored_rows FROM aleksandra_timeline WHERE title->>'en' = title->>'ka';"
  psql "$SUPABASE_DB_URL" -c "SELECT count(*) AS total_rows FROM aleksandra_timeline;"
} > scripts/migrations/012_rollback/post_apply_smoke.txt
```

**Verify** `post_apply_smoke.txt`:
- Contains the string `jsonb` at least 6 times (once per converted column).
- The two `aleksandra_timeline` count(*) queries return the same number (I18N-09 mirror invariant).

### Step 4 — Run the production-mode verifier

```bash
python -m scripts.verify_phase6 --mode production --bucket B
```

**Expected:** exit 0, I18N-05 PASS, I18N-09 PASS. If any check fails, the maintenance window has exposed a regression that the original Plan 06-07 deferral did not catch — surface to Shako immediately and file an incident note in `.handoffs/`.

### Step 5 — Commit artifacts

```bash
git add scripts/migrations/012_rollback/*.pre012.dump \
        scripts/migrations/012_rollback/*.policies.pre.txt \
        scripts/migrations/012_rollback/*.policies.post.txt \
        scripts/migrations/012_rollback/post_apply_smoke.txt
git commit -m "chore(06-07-followup): capture migration 012 rollback artifacts post-hoc

Live snapshots taken on YYYY-MM-DD after Shako's 2026-05-20 production
apply of scripts/migrations/012_i18n_jsonb.sql. Resolves the deferred-
artifacts note in 06-07-SUMMARY.md and the corresponding pending todo.

verify_phase6 --mode production --bucket B exits 0 (I18N-05 + I18N-09 PASS).
"
```

### Step 6 — Close the todo

Move this file from `.planning/todos/pending/` to `.planning/todos/completed/` (or whatever convention the project adopts; pending/completed split is OK as a first pass). Update 06-07-SUMMARY.md's Self-Check section in place to flip the three DEFERRED rows to `[x]`.

## Done criteria

- 4 `.pre012.dump` files contain real `INSERT INTO` rows (file size > 5 KB each in expected cases)
- 4 `.policies.pre.txt` files contain a `Policies:` block with the expected policy names per table
- 4 `.policies.post.txt` files contain a `Policies:` block identical (by polname set) to the corresponding `.pre.txt`
- 1 `post_apply_smoke.txt` file contains `jsonb` at least 6 times and identical mirror counts
- `python -m scripts.verify_phase6 --mode production --bucket B` exits 0 with I18N-05 + I18N-09 PASS
- Commit landed; todo moved out of `pending/`

## Why this is not blocking

- 06-05b (page t() refs): no DB touch.
- 06-08 (manager JSONB writes): exercises the live schema directly; if it works, RLS is preserved (failing closed).
- 06-09, 06-10, 06-11: no DB touch.
- 06-13 (Phase 6 closure): code-complete mode passes regardless; production-mode verifier sweep is a nice-to-have for the exit report but not a closure gate.

If the maintenance window runs and surfaces a regression, that becomes a Phase 6 P0 incident and 06-13 closure waits on the fix. Until then, treat this todo as scheduled hygiene.
