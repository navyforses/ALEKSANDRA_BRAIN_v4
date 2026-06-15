# Migration 029 Runbook — Trials Registry Columns (`clinical_trials`)

**Created:** 2026-06-15
**Owner:** agent (REST backup) + **operator DDL** (one transaction via `SUPABASE_DB_URL`).
**Scope:** make `clinical_trials` registry-aware so EU **CTIS** + UK **ISRCTN** trials
(which have **no NCT id**) can live alongside ClinicalTrials.gov rows without polluting
the NCT namespace. This is "Phase E — Wave 1 (backend)" of the multi-registry expansion
(`docs/CLINICAL_TRIALS_SOURCES_RESEARCH.md`, "Schema change → Option A").

## Why

Phase A–C keyed `clinical_trials` solely on `nct_id` (UNIQUE). A CTIS trial is
identified by a `ctNumber` (e.g. `2025-520538-49-00`) and an ISRCTN trial by an
ISRCTN number (e.g. `61218504`) — neither is an NCT id. The research doc's verified
best lead for Aleksandra (UCL's **ACUMEN** IV-melatonin HIE Phase I) lives ONLY in
CTIS + ISRCTN, not ClinicalTrials.gov — so we cannot ingest it without a registry-aware
key. Option A (recommended in the research) adds three columns and a partial unique
index, keeping the ctgov upsert path 100% unchanged.

## What it does

| step | action | touches |
|---|---|---|
| 1. backup | REST GET every `clinical_trials` row (`select=*`, paginated) → `scripts/migrations/029_trials_backup.json`. Always runs (even dry-run). | read-only |
| 2. ddl | run `029_trials_registry_columns.sql` via psycopg2 (`SUPABASE_DB_URL`) in one transaction. **Idempotent-by-guard**: skipped only when all three columns AND `ux_trials_registry` already exist; the SQL itself is re-run-safe (every statement is `IF NOT EXISTS`; the backfill `UPDATE` matches `WHERE registry IS NULL`). | **DDL on prod** |

DDL detail (all ADDITIVE — no column is dropped or retyped):
- `registry` TEXT ADD — `'ctgov'` | `'ctis'` | `'isrctn'` (the id namespace).
- `registry_id` TEXT ADD — registry-native id (`nct_id` / `ctNumber` / ISRCTN number).
- `secondary_ids` TEXT[] ADD — sibling-registry ids for cross-registry dedup
  (e.g. `{'NCT06...','ISRCTN61218504','EudraCT...'}`).
- backfill: `UPDATE clinical_trials SET registry='ctgov', registry_id=nct_id WHERE registry IS NULL`.
- `ux_trials_registry` — partial `UNIQUE INDEX (registry, registry_id) WHERE registry IS NOT NULL`.

## Why this is safe to apply live

`clinical_trials` is **fully reconstructable** by re-running the matcher from
`evidence_ledger` + R2. The `029_trials_backup.json` snapshot (taken before any DDL)
is an extra safety net, not the only recovery path. The migration is ADDITIVE — no
column is dropped or retyped — so RLS policies survive untouched (same reasoning as
012 / 017 / 028). The new index is partial (`WHERE registry IS NOT NULL`), so it can
never conflict with rows that legitimately have a NULL registry.

## Ordering

Apply the DDL **before** running the extended matcher: the matcher writes `registry`,
`registry_id`, `secondary_ids` and upserts non-NCT registries on
`on_conflict=registry,registry_id`, which requires the partial unique index to exist.
So: **apply 029 → verify columns + index → run the new fetchers (ctis, isrctn) → run
the matcher.**

## Usage

```bash
# dry run — backup + preview DDL plan (no writes)
PYTHONUTF8=1 .venv/Scripts/python.exe \
  -m scripts.migrations.029_trials_registry_columns

# apply — backup + DDL (one transaction) + verify columns/index + backfill
PYTHONUTF8=1 .venv/Scripts/python.exe \
  -m scripts.migrations.029_trials_registry_columns --apply

# then ingest the new registries + re-run the matcher
PYTHONUTF8=1 .venv/Scripts/python.exe -m scripts.perception.sources.ctis
PYTHONUTF8=1 .venv/Scripts/python.exe -m scripts.perception.sources.isrctn
PYTHONUTF8=1 .venv/Scripts/python.exe -m scripts.trials.eligibility_matcher
```

(Windows: `PYTHONUTF8=1` is required — cp1252 stdout cannot print Mkhedruli.)

If `SUPABASE_DB_URL` is unavailable, run the DDL by hand in the Supabase SQL Editor
(paste `029_trials_registry_columns.sql`), then run the fetchers + matcher.

## Apply result (2026-06-15)

- registry breakdown BEFORE: _filled in at apply time_.
- [ ] DDL applied — `registry` / `registry_id` / `secondary_ids` present;
  `ux_trials_registry` index present.
- [ ] Backfill — every pre-existing row `registry='ctgov'`, `registry_id=nct_id`.
- [ ] registry breakdown AFTER: _filled in at apply time (ctgov / ctis / isrctn counts)_.
