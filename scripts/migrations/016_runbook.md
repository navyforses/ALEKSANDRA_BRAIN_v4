# Migration 016: Phase 7.0 Belief Tables — Operator Runbook

> **Scope:** purely additive — 3 new tables (`belief_dimensions`, `belief_evidence`, `belief_traces`) + indexes + RLS + 1 trigger.
> **Touches existing tables:** NONE.
> **Estimated total Shako time:** ~10 minutes (env + pre-flight + apply + verify).
> **Risk profile:** LOW (additive only; ALTER COLUMN trap from Phase 6.1 does not apply).
>
> **Sibling file note:** `016_restore_hypotheses.py` is a Phase 6.1 emergency
> data-restore script (different extension, different purpose). The two coexist.

---

## 0. Pre-flight — MANDATORY backup

Supabase Free has **no automatic backups** (Phase 6.1 incident verified this).
Run the pre-flight script before `psql`-ing the migration:

```bash
# 1. Set the service-role connection string
export SUPABASE_DB_URL='postgres://postgres:<password>@db.<project>.supabase.co:5432/postgres'

# 2. Run the wrapper
bash scripts/migrations/016_pre_flight_backup.sh
```

Expected outputs (under `.planning/backups/pre_016/`):

| File | Sanity check |
|---|---|
| `schema.sql`  | > 30 KB (Phase 1-6 schema dump) |
| `data.sql`    | > 1 KB (current papers/hypotheses/therapies/contacts/runs/...) |
| `rowcounts.csv` | one row per `public.*` table with current count |
| `manifest.txt` | redacted connection string, date, file listing |

If `schema.sql` is < 30 KB or `data.sql` is empty, **stop** and investigate
(connection string wrong, or DB unreachable).

---

## 1. Apply the migration

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/016_belief_tables.sql
```

Expected `psql` output (one line per object created):

```
BEGIN
CREATE EXTENSION
CREATE TABLE              -- belief_dimensions
CREATE TABLE              -- belief_evidence
CREATE INDEX              -- 3 indexes on belief_evidence
CREATE INDEX
CREATE INDEX
CREATE TABLE              -- belief_traces
CREATE INDEX              -- 3 indexes on belief_traces
CREATE INDEX
CREATE INDEX
ALTER TABLE               -- ENABLE RLS x3
ALTER TABLE
ALTER TABLE
DROP POLICY               -- 6 DROP IF EXISTS (no-ops on first apply)
CREATE POLICY             -- 6 policies (service_all + family_read x3)
... (12 total policy lines)
CREATE FUNCTION
DROP TRIGGER
CREATE TRIGGER
COMMIT
```

Exit code must be **0**. SLA: **< 5 seconds** on Aura Free / Supabase Free.

If `psql` returns non-zero, the entire migration rolls back via the wrapping
`BEGIN; ... COMMIT;` — no partial state. Investigate, fix, re-run.

---

## 2. Post-apply verification

```bash
# 2a. Three tables exist with RLS enabled + correct policies
psql "$SUPABASE_DB_URL" -c "\d belief_dimensions"
psql "$SUPABASE_DB_URL" -c "\d belief_evidence"
psql "$SUPABASE_DB_URL" -c "\d belief_traces"
# Each output must include "Row security: enabled" and the two policies.

# 2b. All three tables empty (population is Day 6+ bootstrap)
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM belief_dimensions;"   # expect 0
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM belief_evidence;"     # expect 0
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM belief_traces;"       # expect 0

# 2c. Anon role cannot read (RLS sanity)
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  "$SUPABASE_URL/rest/v1/belief_dimensions?select=id&limit=1"
# Expected: 401 (preferred) OR 200 with empty array. NEVER a row.

# 2d. Migration 008 base tables unaffected
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM hypotheses;"
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM therapies;"
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM contacts;"
# All three must match pre_016/rowcounts.csv exactly.
```

Any deviation → invoke rollback (§4).

---

## 3. Hand-off to v7-bayes

Once 2a-2d are green, signal v7-bayes that the persistence layer is live.
The Day 6 bootstrap (`python -m brain.belief.bootstrap`) will then populate
`belief_dimensions` with all 13 rows (one INSERT per dimension, each carrying
a primary-source citation — the `belief_dimensions_citation_nonempty` CHECK
enforces `length(citation) >= 10`).

---

## Step 4: Bootstrap 13 dimensions into belief_dimensions

Migration 016 creates the empty table. The 13 dimensions live in
`brain/belief/dimensions.toml` (literature-grounded by Day 7-9 librarians).
Run the bootstrap helper to UPSERT them:

```bash
# Dry-run first (no DB writes; validates TOML + reports planned changes)
.venv-v7/Scripts/python.exe -m brain.belief.bootstrap --dry-run

# If dry-run reports 13 dims clean → live UPSERT
.venv-v7/Scripts/python.exe -m brain.belief.bootstrap
# Expected: 13 INSERT (first run) or 13 UNCHANGED (repeat runs)
# Exit code 0 on success
```

Idempotent: re-running gives identical output. Service-role connection
required (anon role cannot write to belief_dimensions even with RLS).

After bootstrap succeeds, re-run the Phase 7.0 verifier in production
mode to flip 10/11 → 11/11:

```bash
.venv-v7/Scripts/python.exe -m scripts.verify_phase_7_0 --mode production
```

Then tag the closure:

```bash
git tag v7.0.0-belief-foundation
git push origin v7.0.0-belief-foundation  # optional, after Shako review
```

---

## 5. Rollback (only if §2 fails)

```bash
psql "$SUPABASE_DB_URL" <<'SQL'
BEGIN;
DROP TRIGGER IF EXISTS belief_dimensions_updated_at ON belief_dimensions;
DROP FUNCTION IF EXISTS belief_dimensions_touch_updated_at();
DROP TABLE IF EXISTS belief_traces CASCADE;
DROP TABLE IF EXISTS belief_evidence CASCADE;
DROP TABLE IF EXISTS belief_dimensions CASCADE;
COMMIT;
SQL
```

Then restore the pre-flight backup if any base-table count regressed:

```bash
psql "$SUPABASE_DB_URL" -f .planning/backups/pre_016/data.sql
```

(In practice this should never fire — migration 016 only ADDs new tables and
cannot affect Phase 1-6 row counts.)

---

## 6. Total Shako SLA

| Step | Time |
|---|---|
| Set `SUPABASE_DB_URL` env | 30 s |
| Pre-flight backup (§0) | 1-3 min (data-volume dependent) |
| Apply migration (§1) | < 5 s |
| Verification (§2) | 3-5 min |
| Bootstrap 13 dimensions (§4) | < 10 s (dry-run + live UPSERT) |
| Production verifier (§4) | < 30 s |
| **Total** | **~10-11 min** |
