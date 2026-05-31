# Migration 018: Phase 7.2 SCM Persistence — Operator Runbook

> **Scope:** purely additive — 3 new tables (`scms`, `scm_audit_log`, `causal_estimates`) + 5 indexes + RLS on all 3 + 1 trigger.
> **Touches existing tables:** NONE.
> **Estimated total Shako time:** ~10 minutes (env + pre-flight + apply + verify).
> **Risk profile:** LOW (additive only; mirrors migration 016's purely-additive belief pattern).
>
> **Sibling file notes:**
> - Migration 016 (belief tables) and 018 (SCM tables) are independent — apply order does not matter.
> - Migration 017 lives under `scripts/migrations/cypher/` (Neo4j); migration 018 is Supabase Postgres. No conflict.

---

## 0. Pre-flight — MANDATORY backup

Supabase Free has **no automatic backups** (Phase 6.1 incident verified this).
Run a backup before `psql`-ing the migration:

```bash
# 1. Set the service-role connection string
export SUPABASE_DB_URL='postgres://postgres:<password>@db.<project>.supabase.co:5432/postgres'

# 2. Capture pre-018 state via the same wrapper pattern as 016
mkdir -p .planning/backups/pre_018
pg_dump --schema-only "$SUPABASE_DB_URL" > .planning/backups/pre_018/schema.sql
pg_dump --data-only   "$SUPABASE_DB_URL" > .planning/backups/pre_018/data.sql
psql "$SUPABASE_DB_URL" -c "\
  SELECT schemaname, relname, n_live_tup \
  FROM pg_stat_user_tables \
  WHERE schemaname='public' \
  ORDER BY relname" -A -F',' > .planning/backups/pre_018/rowcounts.csv
```

Expected outputs:

| File | Sanity check |
|---|---|
| `schema.sql`  | > 30 KB (Phase 1-7.0 schema dump) |
| `data.sql`    | > 1 KB (current papers/hypotheses/therapies/contacts/runs/...) |
| `rowcounts.csv` | one row per `public.*` table with current count |

If `schema.sql` is < 30 KB or `data.sql` is empty, **stop** and investigate
(connection string wrong, or DB unreachable).

---

## 1. Apply the migration

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/018_scm_tables.sql
```

Expected `psql` output (one line per object created):

```
BEGIN
CREATE EXTENSION
CREATE TABLE              -- scms
CREATE INDEX              -- scms_name_idx
CREATE TABLE              -- scm_audit_log
CREATE INDEX              -- scm_audit_log_scm_id_idx
CREATE INDEX              -- scm_audit_log_occurred_at_idx
CREATE TABLE              -- causal_estimates
CREATE INDEX              -- causal_estimates_scm_id_idx
CREATE INDEX              -- causal_estimates_computed_at_idx
ALTER TABLE               -- ENABLE RLS x3
ALTER TABLE
ALTER TABLE
DROP POLICY               -- 6 DROP IF EXISTS (no-ops on first apply)
CREATE POLICY             -- 6 policies (service_all + family_read x3)
... (12 total policy lines)
CREATE FUNCTION           -- scms_touch_updated_at
DROP TRIGGER
CREATE TRIGGER            -- scms_updated_at
COMMIT
```

Exit code must be **0**. SLA: **< 5 seconds** on Supabase Free.

If `psql` returns non-zero, the entire migration rolls back via the wrapping
`BEGIN; ... COMMIT;` — no partial state. Investigate, fix, re-run.

---

## 2. Post-apply verification

```bash
# 2a. Three tables exist with RLS enabled + correct policies
psql "$SUPABASE_DB_URL" -c "\d scms"
psql "$SUPABASE_DB_URL" -c "\d scm_audit_log"
psql "$SUPABASE_DB_URL" -c "\d causal_estimates"
# Each output must include "Row security: enabled" and the two policies.

# 2b. All three tables empty (population starts at Day 12+ create_scm())
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM scms;"             # expect 0
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM scm_audit_log;"    # expect 0
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM causal_estimates;" # expect 0

# 2c. Anon role cannot read (RLS sanity)
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  "$SUPABASE_URL/rest/v1/scms?select=id&limit=1"
# Expected: 401 (preferred) OR 200 with empty array. NEVER a row.

# 2d. Migration 016 belief tables + Phase 1-6 base tables unaffected
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM belief_dimensions;"
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM belief_evidence;"
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM hypotheses;"
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM therapies;"
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM contacts;"
# All must match pre_018/rowcounts.csv exactly.
```

Any deviation → invoke rollback (§4).

---

## 3. Hand-off to v7-causal

Once 2a-2d are green, signal v7-causal that the persistence layer is live.
The Day 12 SCM CRUD path (`brain/causal/scm_persistence.py`) will then
exercise `create_scm` / `update_scm` / `revert_scm` / `list_scm_audit`
against the live DB. Re-run the Phase 7.2 verifier in production mode
to flip the 3 SKIP gates (8 / 9 / 10) to PASS:

```bash
.venv-v7/Scripts/python.exe -m scripts.verify_phase_7_2 --mode production
# Expected: 12/12 PASS, 0 SKIP, 0 FAIL, exit code 0
```

Then tag the closure:

```bash
git tag v7.2.0-causal-layer
git push origin v7.2.0-causal-layer  # optional, after Shako review
```

---

## 4. Rollback (only if §2 fails)

```bash
psql "$SUPABASE_DB_URL" <<'SQL'
BEGIN;
DROP TRIGGER IF EXISTS scms_updated_at ON scms;
DROP FUNCTION IF EXISTS scms_touch_updated_at();
DROP TABLE IF EXISTS causal_estimates CASCADE;
DROP TABLE IF EXISTS scm_audit_log CASCADE;
DROP TABLE IF EXISTS scms CASCADE;
COMMIT;
SQL
```

Then restore the pre-flight backup if any base-table count regressed:

```bash
psql "$SUPABASE_DB_URL" -f .planning/backups/pre_018/data.sql
```

(In practice this should never fire — migration 018 only ADDs new tables and
cannot affect Phase 1-7.0 row counts.)

---

## 5. Total Shako SLA

| Step | Time |
|---|---|
| Set `SUPABASE_DB_URL` env | 30 s |
| Pre-flight backup (§0) | 1-3 min (data-volume dependent) |
| Apply migration (§1) | < 5 s |
| Verification (§2) | 3-5 min |
| Production verifier (§3) | < 30 s |
| **Total** | **~9-10 min** |
