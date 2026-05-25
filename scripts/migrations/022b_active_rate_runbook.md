# Migration 022b Runbook — Active Rate Constraint + Trigger (Phase 7.5 Rule #11)

**Phase:** 7.5 Constitutional Code
**Rule:** #11 Wife question cap ≤ 3 per ISO week
**Mechanism:** explicit CHECK + BEFORE INSERT/UPDATE trigger on `active_rate_log`
**Risk profile:** LOW (additive; migration 020 already carries a CHECK; this duplicates with named identifier)
**Estimated apply time:** 1 minute
**Estimated rollback time:** 1 minute

---

## § 0 — Pre-flight (REQUIRED before apply)

1. Confirm `SUPABASE_DB_URL` is set.
2. Confirm migration 020 is applied:
   ```bash
   psql "$SUPABASE_DB_URL" -c "\d active_rate_log"
   ```
   Expect the table exists with `active_rate_log_within_cap` already
   listed in Check constraints.
3. Snapshot existing constraint + trigger list:
   ```bash
   psql "$SUPABASE_DB_URL" -c "\d active_rate_log" \
     > .planning/migration_snapshots/022b_pre_apply_active_rate_log.txt
   ```

---

## § 1 — Apply

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
  -f scripts/migrations/022b_active_rate_constraint.sql
```

Expect:
```
BEGIN
DO
COMMENT
CREATE FUNCTION
COMMENT
DROP TRIGGER
CREATE TRIGGER
COMMENT
COMMIT
```

---

## § 2 — Post-apply smoke test

Run the three checks in `022b_active_rate_constraint.sql` POST-APPLY
SMOKE TEST section. Cap breach via UPDATE must raise
"Phase 7.5 Rule #11: weekly question cap of 3 exceeded" with errcode
23514. In-cap update must succeed.

---

## § 3 — Verifier hook

`scripts/verify_phase_7_5.py --mode production` will run check_7_5_11
which inserts then updates a row to trigger the cap breach via
psycopg2 and confirms the explicit "Rule #11" error string fires.

---

## § 4 — Rollback

```sql
BEGIN;
DROP TRIGGER IF EXISTS active_rate_cap_enforce ON active_rate_log;
DROP FUNCTION IF EXISTS enforce_active_rate_cap();
ALTER TABLE active_rate_log DROP CONSTRAINT IF EXISTS questions_within_cap;
-- Migration 020's active_rate_log_within_cap CHECK remains.
COMMIT;
```

The application-side `brain/active/rate_limiter.py` is unaffected by
rollback; the application cap check still fires.

---

## § 5 — Escape hatch

Per `docs/PHASE_7_5_ESCAPE_HATCHES.md` §Rule 11: a one-off urgent
question above the weekly cap requires an
`issue_override(rule_number=11, reason="<≥20-char>")` row + a manual
`UPDATE active_rate_log SET cap = cap + 1 WHERE week_iso = '<week>'`
within the 24-hour override window. Wife Telegram notification fires.
