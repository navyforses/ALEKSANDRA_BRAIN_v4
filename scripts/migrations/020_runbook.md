# Migration 020: Phase 7.4 Active Learning — Operator Runbook

> **Scope:** purely additive — 2 new tables (`active_questions`, `active_rate_log`) + 5 indexes + RLS on both + 2 triggers.
> **Touches existing tables:** NONE (FKs to `belief_dimensions` and `belief_evidence` from migration 016 are SET NULL / RESTRICT only — no constraints altered on either side).
> **Estimated total Shako time:** ~8 minutes (env + pre-flight + apply + verify + smoke).
> **Risk profile:** LOW (additive only; mirrors migrations 018/019 pattern).
>
> **Sibling file notes:**
> - Migrations 016 (belief), 018 (SCM), 019 (sim) and 020 (active) are independent except for the FKs above. Migration 020 REQUIRES migration 016 to be applied first (FK targets).
> - Constitutional rule #11 (3 questions/week cap) is enforced at TWO layers: application-side `brain.active.rate_limiter.can_send_question()` AND DB-side `CHECK (questions_sent <= cap)`. Both must agree.

---

## 0. Pre-flight — MANDATORY backup

Supabase Free has **no automatic backups** (Phase 6.1 incident verified this).
Run a backup before `psql`-ing the migration:

```bash
# 1. Set the service-role connection string
export SUPABASE_DB_URL='postgres://postgres:<password>@db.<project>.supabase.co:5432/postgres'

# 2. Capture pre-020 state
mkdir -p .planning/backups/pre_020
pg_dump --schema-only "$SUPABASE_DB_URL" > .planning/backups/pre_020/schema.sql
pg_dump --data-only   "$SUPABASE_DB_URL" > .planning/backups/pre_020/data.sql
psql "$SUPABASE_DB_URL" -c "\
  SELECT schemaname, relname, n_live_tup \
  FROM pg_stat_user_tables \
  WHERE schemaname='public' \
  ORDER BY relname" -A -F',' > .planning/backups/pre_020/rowcounts.csv
```

Expected outputs:

| File | Sanity check |
|---|---|
| `schema.sql`  | > 60 KB (now includes 016 + 018 + 019 tables) |
| `data.sql`    | > 1 KB |
| `rowcounts.csv` | one row per `public.*` table |

If `schema.sql` is < 60 KB or `data.sql` is empty, **stop** and investigate.

---

## 1. Verify prerequisites

```bash
psql "$SUPABASE_DB_URL" -c "\d belief_dimensions" | head -3
psql "$SUPABASE_DB_URL" -c "\d belief_evidence" | head -3
```

Both must exist. If either is missing, apply migration 016 first.

---

## 2. Apply the migration

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/020_active_questions.sql
```

Expected output:

```
BEGIN
CREATE EXTENSION
CREATE TABLE
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
COMMENT
COMMENT
COMMENT
CREATE TABLE
CREATE INDEX
COMMENT
ALTER TABLE
ALTER TABLE
DROP POLICY (×3)
CREATE POLICY (×3)
CREATE FUNCTION (×2)
DROP TRIGGER (×2)
CREATE TRIGGER (×2)
COMMIT
```

No `ERROR` lines. The full transaction is wrapped in `BEGIN/COMMIT`; any error rolls everything back.

---

## 3. Post-apply verification

```bash
# 3a. Tables exist with RLS enabled
psql "$SUPABASE_DB_URL" -c "\d active_questions"
psql "$SUPABASE_DB_URL" -c "\d active_rate_log"
# Both must show "Row security: enabled".

# 3b. Tables empty
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM active_questions;"  # 0
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM active_rate_log;"    # 0

# 3c. Regression — earlier migration tables unaffected
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM belief_dimensions;"
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM belief_evidence;"
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM scms;"
psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM scenarios;"
```

Compare against `.planning/backups/pre_020/rowcounts.csv` — every previous count
must match exactly.

---

## 4. Cap CHECK smoke test (constitutional rule #11)

```bash
# Try to insert a row that violates the cap
psql "$SUPABASE_DB_URL" <<'SQL'
BEGIN;
INSERT INTO active_rate_log (week_iso, questions_sent, cap)
  VALUES ('2026-W45-test', 4, 3);
SQL
```

Expected: `ERROR:  new row for relation "active_rate_log" violates check constraint "active_rate_log_within_cap"`.

Roll the transaction back; the row must NOT appear in subsequent SELECTs.

---

## 5. Run verifier in production mode

```bash
.venv-v7/Scripts/python.exe scripts/verify_phase_7_4.py --mode production
```

Expected: 10/10 PASS (the production mode flips check 8 from DRY_RUN sentinel to live evidence_id assertion).

---

## 6. Rollback procedure (only if migration must be reversed)

```sql
BEGIN;
DROP TRIGGER IF EXISTS active_questions_response_stamp ON active_questions;
DROP FUNCTION IF EXISTS active_questions_stamp_received();
DROP TRIGGER IF EXISTS active_rate_log_updated_at ON active_rate_log;
DROP FUNCTION IF EXISTS active_rate_log_touch_updated_at();
DROP TABLE IF EXISTS active_rate_log CASCADE;
DROP TABLE IF EXISTS active_questions CASCADE;
COMMIT;
```

The migration leaves zero residue: pgcrypto stays (used by 016+).

---

## 7. Known maintenance items (carry-forward to Phase 7.5)

- Constitutional rule #11 currently checked at TWO layers (app + DB). Phase 7.5 §rule #11 should consolidate to DB-only via a stored procedure that wraps both increment + cap check, removing the application-side TOCTOU window.
- `posterior_delta_kl` is populated lazily by the integration module. Consider a backfill cron to ensure no row stays NULL longer than 24h.
- Live Telegram outbound (Day 7 production path) gated on Shako restart of the n8n perception_tick worker (Phase 6.1 carry-forward) AND bot-token env vars (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_FAMILY_CHAT_ID`).
