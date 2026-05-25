# Migration 023 Runbook — Constitutional Overrides Table (Phase 7.5 Meta)

**Phase:** 7.5 Constitutional Code
**Scope:** Meta — escape-hatch audit ledger for all 13 rules
**Mechanism:** new table `constitutional_overrides` with RLS + 24h auto-expiry semantics
**Risk profile:** LOW (additive new table; no FK references; no DDL on existing tables)
**Estimated apply time:** 2 minutes
**Estimated rollback time:** 1 minute

---

## § 0 — Pre-flight (REQUIRED before apply)

1. Confirm `SUPABASE_DB_URL` is set.
2. Confirm pgcrypto extension is available (used by migrations 016/018/019/020):
   ```bash
   psql "$SUPABASE_DB_URL" -c "SELECT extname FROM pg_extension WHERE extname='pgcrypto';"
   ```
3. No table snapshot required — this migration creates a brand-new table
   with no references to existing data.

---

## § 1 — Apply

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
  -f scripts/migrations/023_constitutional_overrides.sql
```

Expect output:
```
BEGIN
CREATE EXTENSION
CREATE TABLE
CREATE INDEX
CREATE INDEX
COMMENT
COMMENT
COMMENT
COMMENT
ALTER TABLE
DROP POLICY
DROP POLICY
CREATE POLICY
CREATE POLICY
COMMIT
```

---

## § 2 — Post-apply smoke test

Run the five checks in `023_constitutional_overrides.sql` POST-APPLY
SMOKE TEST section. Confirm:
- Table empty after creation.
- Smoke insert returns `ttl ~ 24:00:00`.
- Rule 14 INSERT rejects via `constitutional_overrides_rule_range`.
- Short reason INSERT rejects via `constitutional_overrides_reason_min_length`.

---

## § 3 — Verifier hook

`scripts/verify_phase_7_5.py --mode production` runs check_7_5_14 which
calls `brain.common.overrides.issue_override(...)` and confirms a row
appears with the expected expiry window.

---

## § 4 — Application wiring

After apply, the application surface in `brain/common/overrides.py`
will switch from DRY_RUN sentinel returns to real INSERT statements.
No code change required — the module reads SUPABASE_DB_URL at call
time and routes accordingly.

---

## § 5 — Rollback

```sql
BEGIN;
DROP TABLE IF EXISTS constitutional_overrides CASCADE;
-- pgcrypto retained.
COMMIT;
```

Phase 7.5 application code falls back to DRY_RUN mode automatically
when the table is dropped (SUPABASE_DB_URL still set) — the call will
attempt the INSERT and raise; defensive callers wrap in try/except.

---

## § 6 — Escape hatch (meta)

Migration 023 IS the escape hatch substrate for every other rule. The
table itself has no constitutional override — the integrity of the
audit ledger is non-negotiable. Operational compromise (table drop
without rollback record) is an out-of-band incident, not an in-band
override.
