# Migration 022 Runbook — Hypothesis ≥3 Sources Constraint (Phase 7.5 Rule #9)

**Phase:** 7.5 Constitutional Code
**Rule:** #9 Confirmed hypothesis requires ≥ 3 supporting_papers
**Mechanism:** Postgres partial CHECK constraint + ADD COLUMN IF NOT EXISTS
**Risk profile:** LOW (additive column + NOT VALID constraint; existing rows unaffected at creation time)
**Estimated apply time:** 1 minute
**Estimated rollback time:** 1 minute

---

## § 0 — Pre-flight (REQUIRED before apply)

1. Confirm `SUPABASE_DB_URL` is set.
2. Snapshot current confirmed-hypotheses row count:
   ```bash
   psql "$SUPABASE_DB_URL" -c "
     SELECT count(*) AS confirmed_total,
            count(*) FILTER (
              WHERE jsonb_array_length(
                COALESCE(supporting_papers, '[]'::jsonb)
              ) >= 3
            ) AS would_pass
     FROM hypotheses
     WHERE status = 'confirmed';
   "
   ```
   Record both numbers. If `would_pass < confirmed_total`, defer the
   future `VALIDATE CONSTRAINT` step until back-fill is done.
3. Snapshot existing constraint list:
   ```bash
   psql "$SUPABASE_DB_URL" -c "\d hypotheses" \
     > .planning/migration_snapshots/022_pre_apply_hypotheses.txt
   ```

---

## § 1 — Apply

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
  -f scripts/migrations/022_hypothesis_constraint.sql
```

Expect output:
```
BEGIN
ALTER TABLE
COMMENT
DO
COMMENT
COMMIT
```

---

## § 2 — Post-apply smoke test

Run the four checks in `022_hypothesis_constraint.sql` POST-APPLY SMOKE
TEST section. Confirmed + 2 sources MUST reject; confirmed + 3 sources
MUST accept; proposed + 0 sources MUST accept.

---

## § 3 — Verifier hook

`scripts/verify_phase_7_5.py --mode production` will run check_7_5_09
which attempts the same smoke insert via psycopg2.

---

## § 4 — Optional follow-up: validate existing rows

After Shako has back-filled any pre-existing confirmed rows with
sufficient supporting_papers:
```sql
ALTER TABLE hypotheses VALIDATE CONSTRAINT min_sources_when_confirmed;
```
Will succeed iff every existing confirmed row already passes.

---

## § 5 — Rollback

```sql
BEGIN;
ALTER TABLE hypotheses DROP CONSTRAINT IF EXISTS min_sources_when_confirmed;
-- Column supporting_papers retained (data preservation).
COMMIT;
```

Phase 2.5+ application code reads `supporting_papers` as a regular
JSONB column; rollback does not affect that code path.

---

## § 6 — Escape hatch

Per `docs/PHASE_7_5_ESCAPE_HATCHES.md` §Rule 9: a one-off confirmed
hypothesis with fewer than 3 sources requires an
`issue_override(rule_number=9, reason="<≥20-char>")` row + a manual
`ALTER TABLE hypotheses DROP CONSTRAINT min_sources_when_confirmed`
(then re-add after the insert), with 24-hour Telegram notification.
