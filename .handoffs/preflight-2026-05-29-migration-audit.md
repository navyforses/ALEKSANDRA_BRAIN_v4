# Migration runbook preflight audit — Phase 7.0 → 7.5

**Date:** 2026-05-29
**Auditor:** Claude (code-only preflight before Shako's 6 production-apply sessions)
**Scope:** 9 migration files (8 SQL + 1 Cypher) across 6 sessions
**Verdict:** ✅ **CLEARED to apply** — one tiny gap patched in 017 runbook; everything else clean

---

## TL;DR for Shako

Read the runbooks in order: 016 → 017 → 018 → 019 → 020 → (021 + 022 + 022b + 023).
Each runbook is self-contained. Apply commands all carry
`-v ON_ERROR_STOP=1` so a partial apply aborts cleanly. Every migration is
wrapped in a `BEGIN; ... COMMIT;` transaction so a syntax error inside the
file leaves zero side effects. Rollback blocks are at the bottom of every
SQL file (commented out — uncomment to execute).

**Total estimated Shako time across 6 sessions:** ~50–70 minutes.
Single-session apply per phase is fine; spreading across days is also
fine since each phase verifier can re-run idempotently.

---

## Migration map

| # | Phase | File(s) | Type | Runbook | Touches |
|---|---|---|---|---|---|
| 016 | 7.0 | `scripts/migrations/016_belief_tables.sql` | SQL (additive) | `016_runbook.md` | 3 new tables + RLS + trigger |
| 017 | 7.1 | `scripts/migrations/cypher/017_causal_edges.cypher` | Cypher (additive) | `cypher/017_runbook.md` | 15 constraints + 3 indexes on Neo4j |
| 018 | 7.2 | `scripts/migrations/018_scm_tables.sql` | SQL (additive) | `018_runbook.md` | SCM + audit log tables |
| 019 | 7.3 | `scripts/migrations/019_sim_tables.sql` | SQL (additive) | `019_runbook.md` | mc_simulations + tvb_simulations |
| 020 | 7.4 | `scripts/migrations/020_active_questions.sql` | SQL (additive) | `020_runbook.md` | weekly_questions + question_responses |
| 021 | 7.5 | `scripts/migrations/021_voice_review_trigger.sql` | SQL (trigger) | `021_runbook.md` | 1 function + 1 trigger on intake_drops |
| 022 | 7.5 | `scripts/migrations/022_hypothesis_constraint.sql` | SQL (CHECK) | `022_hypothesis_runbook.md` | hypotheses CHECK constraint |
| 022b | 7.5 | `scripts/migrations/022b_active_rate_constraint.sql` | SQL (CHECK) | `022b_active_rate_runbook.md` | active_rate_log CHECK + trigger |
| 023 | 7.5 | `scripts/migrations/023_constitutional_overrides.sql` | SQL (additive) | `023_runbook.md` | 1 new table + RLS |

---

## Audit checklist — per migration

| # | BEGIN/COMMIT | Idempotent | -v ON_ERROR_STOP=1 in apply | Post-apply smoke | Rollback block | Pre-flight backup | Production verifier call |
|---|---|---|---|---|---|---|---|
| 016 | ✅ | ✅ (IF NOT EXISTS × 10, DROP IF EXISTS × 12, RLS DROP+CREATE pattern) | ✅ | ✅ inline | ✅ commented | ✅ `016_pre_flight_backup.sh` | ✅ `scripts.verify_phase_7_0 --mode production` |
| 017 | n/a (cypher) | ✅ (IF NOT EXISTS on every CREATE CONSTRAINT/INDEX) | n/a | ✅ Cypher SHOW + counts | ✅ commented (15 DROP statements) | ✅ `scripts/backup_neo4j.py` | ✅ **patched in this audit** — see below |
| 018 | ✅ | ✅ (IF NOT EXISTS × 10, DROP IF EXISTS × 12) | ✅ | ✅ | ✅ | snapshot under `.planning/migration_snapshots/` | ✅ `scripts.verify_phase_7_2 --mode production` |
| 019 | ✅ | ✅ (IF NOT EXISTS × 12, DROP IF EXISTS × 12, 3 RLS) | ✅ | ✅ | ✅ | snapshot | ✅ `verify_phase_7_3.py --mode production` |
| 020 | ✅ | ✅ (IF NOT EXISTS × 9, DROP IF EXISTS × 11, 2 RLS) | ✅ | ✅ | ✅ (2 blocks — separated table-create + check-add) | snapshot | ✅ `verify_phase_7_4.py --mode production` |
| 021 | ✅ | ✅ (trigger DROP+CREATE pattern) | ✅ | ✅ | ✅ | snapshot of intake_drops `\d` | indirect — `verify_phase_7_5.py` check_7_5_02 covers it |
| 022 | ✅ | ✅ (NOT VALID + VALIDATE pattern) | ✅ | ✅ | ✅ | snapshot of hypotheses `\d` | indirect — `verify_phase_7_5.py` check_7_5_09 |
| 022b | ✅ | ✅ (trigger DROP+CREATE; uses migration 020 base table) | ✅ | ✅ | ✅ | snapshot of active_rate_log `\d` | indirect — `verify_phase_7_5.py` check_7_5_11 |
| 023 | ✅ | ✅ (IF NOT EXISTS × 5, DROP IF EXISTS × 3, 1 RLS) | ✅ | ✅ | ✅ | none required — net-new table | indirect — `verify_phase_7_5.py` check_7_5_14 |

---

## Gap caught + patched

### 017 runbook lacked an explicit `verify_phase_7_1.py --mode production` invocation

The runbook's "Post-apply verification" section only ran raw
`cypher-shell SHOW CONSTRAINTS` queries — useful but not the same as
running the Phase 7.1 verifier in production mode, which exercises 7
checks that are currently SKIPed in `--mode code-complete`.

**Fix landed in this audit:** added a second sub-section "Phase 7.1
production verifier" with the explicit command:

```bash
NEO4J_URI='neo4j+s://<your-aura>.databases.neo4j.io' \
NEO4J_USERNAME='neo4j' \
NEO4J_PASSWORD='<your-password>' \
.venv-v7/Scripts/python.exe scripts/verify_phase_7_1.py --mode production
# Expected: 9/9 PASS, 0 SKIP, 0 FAIL, exit code 0
```

Note this runs **after** Days 4-6 mutations land (the
`classify_edges.py` + `cross_link.py` runs), not immediately after the
017 cypher apply. The cypher apply only creates the schema; the data
mutations happen subsequently and the verifier expects post-mutation
state.

---

## Common patterns observed (all 9 migrations)

- Every SQL migration starts with:
  ```sql
  BEGIN;
  ```
  and ends with:
  ```sql
  COMMIT;
  -- ─── POST-APPLY SMOKE TEST (manual, NOT in this transaction) ───
  -- ─── ROLLBACK (apply only if migration X must be reversed) ───
  ```
  Standardized footer convention.

- Idempotency contract:
  - `CREATE TABLE IF NOT EXISTS …`
  - `CREATE INDEX IF NOT EXISTS …`
  - `DROP POLICY IF EXISTS p1 ON t; CREATE POLICY p1 ON t …;` (replacement pattern)
  - `DROP TRIGGER IF EXISTS t1 ON x; CREATE TRIGGER t1 ON x …;`
  - `CREATE OR REPLACE FUNCTION …`
  - `ALTER TABLE … ADD CONSTRAINT … NOT VALID; ALTER TABLE … VALIDATE CONSTRAINT …;` (for adding CHECKs on populated tables)

- Apply command consistency:
  ```bash
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f <file>
  ```
  `-v ON_ERROR_STOP=1` aborts on first error → entire BEGIN/COMMIT
  rolls back. Safe.

- Pre-flight backup convention:
  - Foundation-level migrations (016) use a dedicated bash wrapper
    that pg_dumps schema + data + rowcounts.
  - Targeted constraint/trigger migrations (021, 022, 022b) capture a
    `\d <affected_table>` snapshot under
    `.planning/migration_snapshots/<num>_pre_apply_<table>.txt` instead
    of a full pg_dump.
  - Brand-new tables (023) don't require a backup (rollback = DROP TABLE).
  - 017 (Cypher) uses `scripts/backup_neo4j.py` which exports all nodes +
    relationships + properties to JSON (AuraDB Free has no
    neo4j-admin dump).

- Rollback block content (every SQL migration, bottom of file, commented out):
  ```sql
  -- BEGIN;
  -- DROP TRIGGER IF EXISTS …;
  -- DROP FUNCTION IF EXISTS …;
  -- DROP TABLE IF EXISTS … CASCADE;
  -- COMMIT;
  ```
  Reverse order. CASCADE only on tables (not on extensions or functions
  needed by other migrations).

---

## Risk assessment per session

| Session | Risk | Why |
|---|---|---|
| Phase 7.0 (016) | LOW | Net-new tables; no existing data touched; RLS pattern mirrors 008 |
| Phase 7.1 (017) | MEDIUM | Neo4j (different stack); AuraDB Free has snapshot rollback but JSON dump is fragile; Days 4-6 mutations are NOT in this migration but the runbook bridges them |
| Phase 7.2 (018) | LOW | Net-new tables (scms, scm_audit_log) |
| Phase 7.3 (019) | LOW | Net-new tables (mc_simulations, tvb_simulations) |
| Phase 7.4 (020) | LOW-MED | Net-new tables; ALSO needs n8n perception_tick worker restart + Telegram bot tokens (orthogonal but in same session); see `.handoffs/incident-2026-05-29-weekly-brief-silent-failure-risk.md` |
| Phase 7.5 (021+022+022b+023) | LOW | One trigger + two CHECK constraints + one net-new table; all targeted edits |

---

## Recommended apply order (matches PR_BODY.md)

```
Phase 7.0  →  Phase 7.1  →  Phase 7.2  →  Phase 7.3  →  Phase 7.4  →  Phase 7.5
   016         017            018           019           020           021 + 022 + 022b + 023
```

- 7.0 first because every later phase depends on the `belief_*` tables.
- 7.1 second because the SCM in 7.2 cross-links to Neo4j CausalNodes.
- 7.2 before 7.3 because the simulation engine consumes SCMs.
- 7.3 before 7.4 because EIG calculations read from sim trajectories.
- 7.4 before 7.5 because constitutional overrides (023) require all
  prior phases' tables to be present for full check coverage.

**No phase can be skipped or reordered** — each verifier's production
mode reads from prior-phase tables.

---

## Open questions for Shako before applying

1. **`SUPABASE_DB_URL`** — confirm you have the **service-role** connection
   string (not anon/authenticated). The `capture_post_artifacts.sh`-style
   scripts already check this, but the runbooks don't. If you're not
   sure, run: `psql "$SUPABASE_DB_URL" -tAc 'SELECT current_user;'` —
   must NOT return `anon` or `authenticated`.

2. **Neo4j AuraDB credentials** — `NEO4J_URI` should be `neo4j+s://…`
   (TLS); `NEO4J_USERNAME` is usually `neo4j`. The 017 backup needs
   these set in the same shell before the `cypher-shell` apply.

3. **Telegram bot tokens for Phase 7.4** — orthogonal to migration 020
   but the same session adds:
   - `TELEGRAM_BOT_TOKEN` (for the active-question outbound)
   - `MANAGER_USER_ID` (Shako's Telegram numeric ID; already set per
     Phase 5 production)
   Confirm wife has opted in to receive active questions before any
   real outbound (Phase 4 acceptance window dependency).

4. **n8n restart** — needs to happen during Phase 7.4 session along
   with `perception_tick` worker check. See the separate incident note
   `.handoffs/incident-2026-05-29-weekly-brief-silent-failure-risk.md`
   for diagnostic steps.

5. **GitHub Actions push for Phase 7.5** — the constitutional CI gate
   (`verify_all.yml`) only activates after first push to origin. First
   run may fail on a YAML validation; budget 5 extra minutes for one
   iteration.

---

## What's verified clean (no Shako action needed)

- All 9 migration SQL/cypher files parse-clean (verified by syntax
  pattern matching; no live `psql --dry-run` available without DB)
- All runbooks reference the correct SQL/cypher files
- All runbooks have pre-flight + apply + verify + rollback blocks
- All migrations are purely additive (no `DROP TABLE` of existing,
  no `ALTER COLUMN TYPE` that drops policies — Phase 6.1 incident
  patterns avoided)
- All migrations use `service_role + authenticated read` RLS pattern
  consistent with migration 008
- All trigger and function names are unique (no name collisions across
  migrations)
- All pre-flight backup scripts exist on disk (`016_pre_flight_backup.sh`,
  `scripts/backup_neo4j.py`)

---

## Status after this audit

- ✅ All 9 migrations CLEARED to apply by Shako
- ✅ 017 runbook gap patched in this audit (will land in next commit)
- ⚠️ Phase 7.4 session has an orthogonal n8n-restart concern — see
  `.handoffs/incident-2026-05-29-weekly-brief-silent-failure-risk.md`
- 📋 No further code-side work blocks Shako from running the 6 sessions
