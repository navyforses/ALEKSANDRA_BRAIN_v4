# Migration 012 Operator Runbook

> **Purpose.** This file is the deterministic operator manual Shako follows
> to apply `scripts/migrations/012_i18n_jsonb.sql` against production Supabase.
> Plan 06-06 authored both this runbook and the SQL it applies; Plan 06-07
> (autonomous=false, BLOCKING) is the wave-2 step that actually runs the
> commands below in a maintenance window.

**Audience:** one operator (Shako), one terminal, one production Postgres URL.

**Prerequisite (must hold before step 1):**

- `SUPABASE_DB_URL` environment variable points at the **service-role**
  connection string for the production Supabase Postgres. This is the same
  env var used by `scripts/communicator/weekly_brief.py` (per Phase 5
  Operator Runbook); no new credential surface is introduced.
- `psql` and `pg_dump` are on `$PATH` (PostgreSQL client tools, version
  ≥ 14 — both ship in the same Postgres install).
- Local clone is on `main` and clean: `git status --short` returns empty.
- Branch protection: do NOT apply on a feature branch — apply only when
  `main` reflects the migration SQL Shako has reviewed.

---

## Phase 0 — Confirm starting state (no DB writes yet)

```bash
# Clean tree
git status --short
# expected: empty output (or only the migration artifacts you are about to commit)

# Sanity: migration file is the version you reviewed
sha256sum scripts/migrations/012_i18n_jsonb.sql

# Sanity: SUPABASE_DB_URL set, points at the correct project
echo "${SUPABASE_DB_URL%%@*}@<REDACTED>"   # masks password; project ref visible
psql "$SUPABASE_DB_URL" -c "SELECT current_database(), current_user;"
# expected: current_database is the Supabase project DB; current_user is the
# service-role user (NOT 'anon', NOT 'authenticated').
```

If anything in Phase 0 fails, **STOP**. Do not proceed.

---

## Step 1 — Pre-flight live-DB introspection (replaces 06-06 placeholders)

The four `.policies.pre.txt` files under `scripts/migrations/012_rollback/`
are placeholders today. Replace them with live `\d <table>` output:

```bash
psql "$SUPABASE_DB_URL" -c "\d aleksandra_timeline" \
  > scripts/migrations/012_rollback/aleksandra_timeline.policies.pre.txt
psql "$SUPABASE_DB_URL" -c "\d hypotheses" \
  > scripts/migrations/012_rollback/hypotheses.policies.pre.txt
psql "$SUPABASE_DB_URL" -c "\d therapies" \
  > scripts/migrations/012_rollback/therapies.policies.pre.txt
psql "$SUPABASE_DB_URL" -c "\d briefs" \
  > scripts/migrations/012_rollback/briefs.policies.pre.txt
```

Audit each output before continuing:

- **A1 — Index audit (no indexes on converted columns).** Grep each file
  for the converted column names. Expect ZERO matches in any `Indexes:`
  section:

  ```bash
  grep -E "(title|description|name|evidence_summary)" \
       scripts/migrations/012_rollback/*.policies.pre.txt \
       | grep -i "btree\|gin\|hash"
  # expected: empty output. If any hit, STOP — escalate to plan-phase research.
  ```

- **A7 — Trigger audit.** No trigger should fire on UPDATE of the converted
  columns by name. The only known trigger is
  `aleksandra_timeline_set_updated_at` which touches `updated_at` only.

- **RLS policy count.** Record the count per table for the post-migration diff:
  - `aleksandra_timeline`: 3 policies (family_read, service_write, service_update)
  - `hypotheses`: 2 (service_all, family_read)
  - `therapies`: 2 (service_all, family_read)
  - `briefs`: 2 (service_all, family_read) + `briefs_phi_redacted_chk` CHECK

- **A3 — daily_digest.json inactive (no n8n surprise).**
  ```bash
  grep -c '"active": false' workflows/daily_digest.json
  # expected: 1 or more
  ```

- **A4 — Reader call-site scan.**
  ```bash
  grep -rn "sections\[" scripts/manager/ scripts/communicator/ 2>/dev/null || true
  grep -rn "summary_lines\[" scripts/manager/ scripts/communicator/ 2>/dev/null || true
  # if any hits read string-shape fields without a display_field_py-style
  # helper, file as Plan 06-08 backlog before continuing
  ```

Record the audit summary into `scripts/migrations/012_rollback/_preflight.txt`
(replace the placeholder with the live results). If A1 / A7 / RLS / A3 / A4
all pass, continue to Step 2.

---

## Step 2 — Pre-migration `pg_dump` rollback artifacts

Replace the 4 placeholder `.pre012.dump` files with live data dumps. Each
file contains every existing row as explicit `INSERT INTO ... VALUES (...)`
statements that survive the TEXT-to-JSONB conversion:

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

Sanity-check each dump:

```bash
for tbl in aleksandra_timeline hypotheses therapies briefs; do
  test -s "scripts/migrations/012_rollback/$tbl.pre012.dump" \
    && head -1 "scripts/migrations/012_rollback/$tbl.pre012.dump"
done
# expected: each file non-empty AND first line begins
#           "-- PostgreSQL database dump"
```

If a dump is empty for a table that DOES have rows, STOP. Investigate before
proceeding.

> Note. These dumps may contain row data that should NOT be committed to the
> public repo if PHI policy classifies it as sensitive. Plan 06-07 commits
> the dumps only if the diff with the placeholder shows no secret content
> per the gitleaks pre-commit hook; otherwise the dumps are kept locally and
> the commit lists them as `.gitignore`'d artifacts. Default: commit (the
> 4 tables are family-internal research/metadata, no PHI per Phase 3 audit).

---

## Step 3 — Apply the migration

Single command, fail-fast on any error:

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/012_i18n_jsonb.sql
```

Expected output: a series of `ALTER TABLE` confirmations followed by an
`UPDATE` row count for `briefs`, ending with `COMMIT`. Total runtime at
current row counts (~10-50 rows per table): under 1 second.

If `psql` exits non-zero: the transaction rolled back (`BEGIN; ... COMMIT;`
wraps the entire script). Inspect the error, repair, and re-run. The
database state is unchanged.

---

## Step 4 — Post-apply smoke checks (run in order)

Run all six checks. ALL must pass before Step 5.

1. **Column TYPE is JSONB** (all 6 converted columns):

   ```bash
   psql "$SUPABASE_DB_URL" -c "
     SELECT 'aleksandra_timeline.title'       AS col, pg_typeof(title)       FROM aleksandra_timeline LIMIT 1;
     SELECT 'aleksandra_timeline.description' AS col, pg_typeof(description) FROM aleksandra_timeline LIMIT 1;
     SELECT 'hypotheses.title'                AS col, pg_typeof(title)       FROM hypotheses          LIMIT 1;
     SELECT 'hypotheses.description'          AS col, pg_typeof(description) FROM hypotheses          LIMIT 1;
     SELECT 'therapies.name'                  AS col, pg_typeof(name)        FROM therapies           LIMIT 1;
     SELECT 'therapies.evidence_summary'      AS col, pg_typeof(evidence_summary) FROM therapies      LIMIT 1;
   "
   ```
   **Expected:** every row reports `jsonb` in the `pg_typeof` column.

2. **Sample en/ka values are identical** (I18N-09 — ka mirrors en for legacy rows):

   ```bash
   psql "$SUPABASE_DB_URL" -c "
     SELECT id, title->>'en' AS en, title->>'ka' AS ka
     FROM aleksandra_timeline LIMIT 5;
   "
   ```
   **Expected:** every row has identical `en` and `ka` values; neither is NULL.

3. **briefs.sections internal shape** (only if briefs rows exist):

   ```bash
   psql "$SUPABASE_DB_URL" -c "
     SELECT count(*) FROM briefs
     WHERE sections->'summary_lines'->0->>'en' IS NOT NULL
        OR sections->'summary_lines' = '[]'::jsonb;
   "
   ```
   **Expected:** equals total briefs count. (For briefs with no summary_lines,
   the reshape leaves `[]`; for briefs with summary_lines, the first element
   has an `en` key.)

4. **RLS policies preserved (aleksandra_timeline — 3 policies):**

   ```bash
   psql "$SUPABASE_DB_URL" -c "
     SELECT polname FROM pg_policy
     WHERE polrelid = 'aleksandra_timeline'::regclass
     ORDER BY polname;
   "
   ```
   **Expected:** exactly these 3 rows in some order:
   - `aleksandra_timeline_family_read`
   - `aleksandra_timeline_service_update`
   - `aleksandra_timeline_service_write`

5. **RLS policies preserved (hypotheses + therapies + briefs — 2 each):**

   ```bash
   for tbl in hypotheses therapies briefs; do
     psql "$SUPABASE_DB_URL" -c "
       SELECT '$tbl' AS table, polname FROM pg_policy
       WHERE polrelid = '$tbl'::regclass ORDER BY polname;
     "
   done
   ```
   **Expected per table:** `{table}_family_read` and `{table}_service_all`.

6. **Snapshot post-migration policies and diff vs pre.** This is the
   definitive RLS-preservation proof:

   ```bash
   for tbl in aleksandra_timeline hypotheses therapies briefs; do
     psql "$SUPABASE_DB_URL" -c "\d $tbl" \
       > scripts/migrations/012_rollback/$tbl.policies.post.txt
     diff scripts/migrations/012_rollback/$tbl.policies.pre.txt \
          scripts/migrations/012_rollback/$tbl.policies.post.txt \
       | grep -E "(Policies|policy|Indexes|index|Triggers|trigger)" || echo "($tbl) NO POLICY/INDEX/TRIGGER DIFF"
   done
   ```
   **Expected per table:** `NO POLICY/INDEX/TRIGGER DIFF` (the only diff
   acceptable is the column-type change `text → jsonb` lines, which is
   the intended migration effect).

If any smoke check fails: **STOP**. Proceed to "Rollback procedure" below.

---

## Step 5 — Final commit

Stage the populated rollback artifacts + the post-migration snapshots:

```bash
git add scripts/migrations/012_rollback/*.pre012.dump
git add scripts/migrations/012_rollback/*.policies.pre.txt
git add scripts/migrations/012_rollback/*.policies.post.txt
git add scripts/migrations/012_rollback/_preflight.txt
git status --short
```

Commit with the standard Phase 6 conventional-commit message:

```bash
git commit -m "$(cat <<'EOF'
chore(06-07): apply migration 012 to production + populate rollback artifacts

Live live-DB introspection results + pg_dump rollback dumps written to
scripts/migrations/012_rollback/. Migration applied via:

  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/012_i18n_jsonb.sql

Smoke 1..6 PASS. RLS pre/post diff: NO POLICY/INDEX/TRIGGER DIFF on all 4 tables.

EOF
)"
```

Push and update STATE.md to mark plan 06-07 complete.

---

## Rollback procedure (if any Step-4 smoke check fails)

The migration is wrapped in a single `BEGIN; ... COMMIT;` so a `psql` error
mid-script already rolled back automatically. The rollback below is for the
case where `psql` exited 0 but a post-apply smoke check FAILED (semantic
regression, not a SQL error).

```bash
# 1. Restore data from per-table dumps
for tbl in aleksandra_timeline hypotheses therapies briefs; do
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 <<SQL
BEGIN;
DELETE FROM $tbl;
SQL
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
    -f "scripts/migrations/012_rollback/$tbl.pre012.dump"
  psql "$SUPABASE_DB_URL" -c "COMMIT;"
done

# 2. Revert TYPE on the 3 TEXT-to-JSONB tables
#    (briefs.sections JSONB type is unchanged so no revert needed there)
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;

ALTER TABLE aleksandra_timeline
  ALTER COLUMN title TYPE text USING title->>'en',
  ALTER COLUMN description TYPE text USING description->>'en';

ALTER TABLE hypotheses
  ALTER COLUMN title TYPE text USING title->>'en',
  ALTER COLUMN description TYPE text USING description->>'en';

ALTER TABLE therapies
  ALTER COLUMN name TYPE text USING name->>'en',
  ALTER COLUMN evidence_summary TYPE text USING evidence_summary->>'en';

COMMIT;
SQL

# 3. Re-run smoke checks 1-5 from Step 4 — pg_typeof should be `text` again.
# 4. Run verify_phase4 + verify_phase5 to confirm no regression.
# 5. File an incident note in .handoffs/ describing what failed and why.
```

After rollback, the database is back to pre-migration shape, the dump
artifacts remain on disk, and the migration SQL can be re-attempted after
the root cause is fixed (likely a fix lands in `scripts/migrations/012_i18n_jsonb.sql`
itself or in upstream Communicator code that wrote unexpected shapes).

---

## What Plan 06-07 specifically does (handoff contract)

The [BLOCKING] task in Plan 06-07 runs Steps 1-5 above end-to-end. The plan
itself is `autonomous: false` — Shako must be at the keyboard. Downstream
Wave-3 plans (06-09 Communicator bilingual emission, 06-12 n8n delivery
routing) block until Plan 06-07's `verify_phase6 --bucket B --mode production`
exits 0.

If Step 4 fails and Step 5 rollback runs, Plan 06-07 returns a checkpoint
to the orchestrator with the failure mode; downstream waves stay blocked.

---

## Quick reference card

| Action | Command |
|--------|---------|
| Set credential | `export SUPABASE_DB_URL=postgres://...` (shell-specific) |
| Pre-flight scan | `psql "$SUPABASE_DB_URL" -c "\d aleksandra_timeline" > ...pre.txt` |
| Per-table dump | `pg_dump "$SUPABASE_DB_URL" --table=X --data-only --column-inserts --file=...` |
| Apply | `psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/012_i18n_jsonb.sql` |
| Smoke check type | `psql "$SUPABASE_DB_URL" -c "SELECT pg_typeof(title) FROM aleksandra_timeline LIMIT 1;"` |
| Smoke check policy | `psql "$SUPABASE_DB_URL" -c "SELECT polname FROM pg_policy WHERE polrelid='X'::regclass;"` |
| Post snapshot diff | `diff X.policies.pre.txt X.policies.post.txt` |
| Rollback data | `psql ... DELETE; psql ... -f X.pre012.dump; COMMIT` |
| Rollback type | `ALTER TABLE X ALTER COLUMN c TYPE text USING c->>'en';` |

---

## Post-hoc capture script (added 2026-05-24 by v7-devops)

Migration 012 was applied to production on 2026-05-20, but Steps 1, 2, and
Step 4 sub-check 6 above were NOT run in the same maintenance window. The
four `.pre012.dump` and four `.policies.pre.txt` files in
`scripts/migrations/012_rollback/` remain Plan-06-06 placeholders, and the
four `.policies.post.txt` files plus `post_apply_smoke.txt` were never
authored.

To close the deferred-artifacts hole (todo:
`.planning/todos/pending/2026-05-21-capture-migration-012-rollback-artifacts.md`)
in one 20-minute window, run:

```bash
SUPABASE_DB_URL='postgres://service_role:...@db.<project-ref>.supabase.co:5432/postgres' \
  bash scripts/migrations/012_rollback/capture_post_artifacts.sh
```

The script is **idempotent** (re-running overwrites in place), **dry-run-safe**
(pre-flight aborts before any DB connection if `psql`, `pg_dump`, or
`SUPABASE_DB_URL` is missing), and **read-only against the DB** (only `\d`
describes and `pg_dump --data-only` reads — zero writes).

### What it does

1. Pre-flight: asserts `psql` + `pg_dump` on `$PATH`, `SUPABASE_DB_URL` set,
   connection reachable, and the URL points at a **service-role** user (not
   `anon` / `authenticated`, otherwise RLS would hide rows from `pg_dump`).
2. Step 1: writes live `\d <table>` output to `<table>.policies.post.txt`
   for each of `aleksandra_timeline`, `hypotheses`, `therapies`, `briefs`,
   and mirrors each into `<table>.policies.pre.txt` (the "new operational
   baseline" — see todo Step 1 note on the redefined semantics).
3. Step 2: `pg_dump --data-only --column-inserts` per table into
   `<table>.pre012.dump`, asserting non-empty + correct pg_dump banner.
4. Step 4 sub-check 6: writes `post_apply_smoke.txt` containing
   `SELECT pg_typeof(<col>)` for each of the 6 converted JSONB columns plus
   the I18N-09 mirror invariant counts. Asserts `jsonb` appears ≥ 6 times
   and `mirrored_rows == total_rows`.
5. Exits 0 only if every assertion passes. Exits 1 on the first failure,
   leaving partial artifacts on disk for Shako to inspect.

### Required environment

| Variable | Purpose | Source |
|---|---|---|
| `SUPABASE_DB_URL` | service-role connection string for production Supabase | same value used by `scripts/communicator/weekly_brief.py` per Phase 5 Operator Runbook |

### After the script exits 0

```bash
# 1. Run the production-mode verifier (resolves I18N-05 + I18N-09 to PASS)
python -m scripts.verify_phase6 --mode production --bucket B

# 2. Commit the populated artifacts
git add scripts/migrations/012_rollback/*.pre012.dump \
        scripts/migrations/012_rollback/*.policies.pre.txt \
        scripts/migrations/012_rollback/*.policies.post.txt \
        scripts/migrations/012_rollback/post_apply_smoke.txt
git commit -m "chore(06-07-followup): capture migration 012 rollback artifacts post-hoc"

# 3. Move the todo
git mv .planning/todos/pending/2026-05-21-capture-migration-012-rollback-artifacts.md \
       .planning/todos/completed/
```
