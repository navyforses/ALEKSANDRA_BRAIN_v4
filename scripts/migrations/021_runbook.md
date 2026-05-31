# Migration 021 Runbook — Voice Review Trigger (Phase 7.5 Rule #2)

**Phase:** 7.5 Constitutional Code
**Rule:** #2 Voice ingest always flagged for human review
**Mechanism:** Postgres BEFORE INSERT trigger on `intake_drops`
**Risk profile:** LOW (additive trigger + function; no DDL on existing columns; idempotent)
**Estimated apply time:** 2 minutes
**Estimated rollback time:** 1 minute

---

## § 0 — Pre-flight (REQUIRED before apply)

1. Confirm `SUPABASE_DB_URL` is set to the project's service-role DSN.
2. Confirm migration 011 (manager_actions + intake_drops) is applied:
   ```bash
   psql "$SUPABASE_DB_URL" -c "\dt intake_drops"
   ```
   Expect one row showing the table.
3. Confirm intake_drops `source` and `requires_review` columns exist:
   ```bash
   psql "$SUPABASE_DB_URL" -c "\d intake_drops" | grep -E "source|requires_review"
   ```
   Expect both columns present.
4. Snapshot existing trigger list to a file so rollback can verify cleanly:
   ```bash
   psql "$SUPABASE_DB_URL" -c "\d intake_drops" \
     > .planning/migration_snapshots/021_pre_apply_intake_drops.txt
   ```

---

## § 1 — Apply

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
  -f scripts/migrations/021_voice_review_trigger.sql
```

Expect output:
```
BEGIN
CREATE FUNCTION
COMMENT
DROP TRIGGER
CREATE TRIGGER
COMMENT
COMMIT
```

---

## § 2 — Post-apply smoke test

Run the four checks in `021_voice_review_trigger.sql` POST-APPLY SMOKE
TEST section. All four must succeed; on the smoke insert the trigger
must override `requires_review=false` to `true` only for voice sources.

---

## § 3 — Verifier hook

After apply, in production mode `scripts/verify_phase_7_5.py
--mode production` will run `check_7_5_02` which attempts the same
smoke insert via psycopg2 and confirms the trigger fired.

---

## § 4 — Rollback

```sql
BEGIN;
DROP TRIGGER IF EXISTS voice_review_required ON intake_drops;
DROP FUNCTION IF EXISTS set_voice_review_required();
COMMIT;
```

Phase 5 Manager flow is unaffected by rollback — it sets
`requires_review=true` voluntarily at the application layer.

---

## § 5 — Escape hatch

Per `docs/PHASE_7_5_ESCAPE_HATCHES.md` §Rule 2: only `service_role` can
DROP the trigger; doing so writes a `constitutional_overrides` row with
24-hour auto-expiry and a Telegram notification to the wife.
