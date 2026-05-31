# Migration 019: Phase 7.3 Simulation Engine — Operator Runbook

> **Scope:** purely additive — 3 new tables (`scenarios`, `simulation_runs`, `simulation_comparisons`) + 7 indexes + RLS on all 3 + 1 immutable-created-at trigger.
> **Touches existing tables:** NONE.
> **Estimated total Shako time:** ~10 minutes (env + pre-flight + apply + verify).
> **Risk profile:** LOW (additive only; mirrors migration 018's purely-additive SCM pattern).
>
> **Sibling file notes:**
> - Migration 016 (belief tables), 018 (SCM tables) and 019 (simulation tables) are independent — apply order does not matter.
> - Migration 017 lives under `scripts/migrations/cypher/` (Neo4j); migration 019 is Supabase Postgres. No conflict.

---

## 0. Pre-flight — MANDATORY backup

Supabase Free has **no automatic backups** (Phase 6.1 incident verified this).
Run a backup before `psql`-ing the migration:

```bash
# 1. Set the service-role connection string
export SUPABASE_DB_URL='postgres://postgres:<password>@db.<project>.supabase.co:5432/postgres'

# 2. Capture pre-019 state via the same wrapper pattern as 018
mkdir -p .planning/backups/pre_019
pg_dump --schema-only "$SUPABASE_DB_URL" > .planning/backups/pre_019/schema.sql
pg_dump --data-only   "$SUPABASE_DB_URL" > .planning/backups/pre_019/data.sql
psql "$SUPABASE_DB_URL" -c "\
  SELECT schemaname, relname, n_live_tup \
  FROM pg_stat_user_tables \
  WHERE schemaname='public' \
  ORDER BY relname" -A -F',' > .planning/backups/pre_019/rowcounts.csv
```

Expected outputs:

| File | Sanity check |
|---|---|
| `schema.sql`  | > 50 KB (Phase 1-7.2 schema dump; should now include 016 + 018 tables) |
| `data.sql`    | > 1 KB (current papers/hypotheses/therapies/contacts/runs/scms/...) |
| `rowcounts.csv` | one row per `public.*` table with current count |

If `schema.sql` is < 50 KB or `data.sql` is empty, **stop** and investigate
(connection string wrong, or DB unreachable, or migrations 016+018 not yet applied).

---

## 1. Apply the migration

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/019_sim_tables.sql
```

Expected `psql` output (one line per object created):

```
BEGIN
CREATE EXTENSION
CREATE TABLE              -- scenarios
CREATE INDEX              -- scenarios_name_idx
CREATE INDEX              -- scenarios_scenario_hash_idx
CREATE TABLE              -- simulation_runs
CREATE INDEX              -- simulation_runs_scenario_id_idx
CREATE INDEX              -- simulation_runs_completed_at_idx
CREATE TABLE              -- simulation_comparisons
CREATE INDEX              -- simulation_comparisons_scenario_a_idx
CREATE INDEX              -- simulation_comparisons_scenario_b_idx
CREATE INDEX              -- simulation_comparisons_created_at_idx
ALTER TABLE               -- ENABLE RLS x3
ALTER TABLE
ALTER TABLE
DROP POLICY               -- 6 DROP IF EXISTS (no-ops on first apply)
CREATE POLICY             -- 6 policies (service_all + family_read x3)
... (12 total policy lines)
CREATE FUNCTION           -- scenarios_touch_created_at
DROP TRIGGER
CREATE TRIGGER            -- scenarios_created_at_immutable
COMMIT
```

Exit code must be **0**. SLA: **< 5 seconds** on Supabase Free.

If `psql` returns non-zero, the entire migration rolls back via the wrapping
`BEGIN; ... COMMIT;` — no partial state. Investigate, fix, re-run.

---

## 2. Post-apply verification

```bash
# 2a. Three tables exist with RLS enabled + correct policies
psql "$SUPABASE_DB_URL" -c "\d scenarios"
psql "$SUPABASE_DB_URL" -c "\d simulation_runs"
psql "$SUPABASE_DB_URL" -c "\d simulation_comparisons"
# Each output must include "Row security: enabled" and the two policies.

# 2b. All three tables empty (population starts at Phase 7.3 Day 11+ save_scenario())
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM scenarios;"              # expect 0
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM simulation_runs;"        # expect 0
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM simulation_comparisons;" # expect 0

# 2c. Anon role cannot read (RLS sanity)
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  "$SUPABASE_URL/rest/v1/scenarios?select=id&limit=1"
# Expected: 401 (preferred) OR 200 with empty array. NEVER a row.

# 2d. Migrations 016 + 018 belief + scm tables + Phase 1-6 base tables unaffected
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM belief_dimensions;"
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM belief_evidence;"
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM scms;"
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM scm_audit_log;"
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM hypotheses;"
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM therapies;"
# All must match pre_019/rowcounts.csv exactly.
```

Any deviation -> invoke rollback (§4).

---

## 3. Hand-off to v7-bayes

Once 2a-2d are green, signal v7-bayes that the simulation persistence layer
is live. The Phase 7.3 Studio CRUD path (`brain/sim/persistence.py`) will
then exercise `save_scenario` / `save_simulation_run` /
`save_scenario_comparison` against the live DB. Re-run the Phase 7.3
verifier in production mode to flip the DRY_RUN-mode checks to PASS:

```bash
.venv-v7/Scripts/python.exe scripts/verify_phase_7_3.py --mode production
# Expected: 10/13 PASS, 3 SKIP (TVB layer B), 0 FAIL, exit code 0
# (TVB checks 7/8/9 stay SKIP until Phase 7.3 Layer B Docker is up.)
```

Then tag the closure:

```bash
git tag v7.3.0-simulation-engine-layer-a-c
git push origin v7.3.0-simulation-engine-layer-a-c  # optional, after Shako review
```

---

## 4. Rollback (only if §2 fails) — spec §5.2

```bash
psql "$SUPABASE_DB_URL" <<'SQL'
BEGIN;
DROP TRIGGER IF EXISTS scenarios_created_at_immutable ON scenarios;
DROP FUNCTION IF EXISTS scenarios_touch_created_at();
DROP TABLE IF EXISTS simulation_comparisons CASCADE;
DROP TABLE IF EXISTS simulation_runs CASCADE;
DROP TABLE IF EXISTS scenarios CASCADE;
COMMIT;
SQL
```

Then restore the pre-flight backup if any base-table count regressed:

```bash
psql "$SUPABASE_DB_URL" -f .planning/backups/pre_019/data.sql
```

(In practice this should never fire — migration 019 only ADDs new tables and
cannot affect Phase 1-7.2 row counts.)

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
