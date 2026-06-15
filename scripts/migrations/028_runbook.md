# Migration 028 Runbook — Trials Bilingual + Full-text (`clinical_trials`)

**Created:** 2026-06-15
**Owner:** agent (REST backup + matcher backfill) + **operator DDL** (one transaction).
**Scope:** make `clinical_trials` store the FULL ClinicalTrials.gov record and make
the family-facing fields bilingual JSONB `{en, ka}` — exactly like papers
(migrations 017 / 026 / 027). This is "Phase C — Wave 1 (backend)" of the Clinical
Trials Enrollment Board (`docs/CLINICAL_TRIALS_PLAN.md`).

## Why

Phase A seeded `clinical_trials` from the thin `evidence_ledger.payload_metadata`
projection only — so `title` was plain English TEXT, `brief_summary` was just the
official title, and `eligibility_criteria` was a synthetic `Age ?-?; sex=…` string.
But `fetch_ctgov.py` already uploads the **FULL study JSON** to R2 (the
`raw_artifact_url` on each `ctgov` ledger row), so all the real detail —
detailed description, full eligibility text, every site, PI/coordinator contacts —
is already captured and just needs to be surfaced. And the `/ka/research/trials`
surface showed English because the columns were TEXT.

Converting the three family-facing columns to JSONB `{en, ka}` lets the existing
frontend (`flatten(value, locale)`) render Georgian with **no UI change**, and the
two new columns (`detailed_description`, `conditions`) give the cards the depth
papers already have.

## What it does

| step | action | touches |
|---|---|---|
| 1. backup | REST GET every `clinical_trials` row (`select=*`, paginated) → `scripts/migrations/028_trials_backup.json`. Always runs. | read-only |
| 2. ddl | run `028_trials_bilingual_fulltext.sql` via psycopg2 (`SUPABASE_DB_URL`) in one transaction. **Idempotent-by-guard**: the three `ALTER COLUMN TYPE` are skipped when `title`/`brief_summary`/`eligibility_criteria` are already `jsonb`; the two `ADD COLUMN` use `IF NOT EXISTS`. | **DDL on prod** |

DDL detail:
- `title` TEXT → JSONB `{en, ka}` (NOT NULL; en mirrored to ka so the Georgian
  site is never blank pre-backfill).
- `brief_summary` TEXT → JSONB `{en, ka}` (nullable; NULL stays NULL).
- `eligibility_criteria` TEXT → JSONB `{en, ka}` (nullable; NULL stays NULL).
- `detailed_description` JSONB ADD (nullable; bilingual `{en, ka}`).
- `conditions` JSONB ADD (nullable; array of EN condition strings, no translation).

The **ka translation backfill is NOT in this migration** — it lives in the matcher
(`scripts/trials/eligibility_matcher.py`), which reads the FULL study JSON from R2,
extracts the rich fields, and wraps the family-facing ones with `build_bilingual()`
(budget-gated, self-healing: only translates a field whose `ka` is empty; reuses an
existing good `ka`; on `BudgetExceeded` falls back to en-only and the next 6h tick
retries). Ineligible trials are stored en-only to avoid translation cost.

## Why this is safe to apply live

`clinical_trials` is **fully reconstructable** by re-running the matcher from
`evidence_ledger` + R2. The `028_trials_backup.json` snapshot (taken before any
DDL) is an extra safety net, not the only recovery path. No trigram indexes
reference these columns (unlike papers in 017), so there is nothing to drop /
recreate. RLS policies survive `ALTER COLUMN TYPE` (same as 012 / 017).

## Ordering

Apply the DDL **before** running the extended matcher: the matcher PATCHes JSONB
objects into `title`/`brief_summary`/`detailed_description`/`eligibility_criteria`,
which would mis-store into still-TEXT columns. So: **apply 028 → verify columns are
`jsonb` → re-run the matcher (backfill).**

## Usage

```bash
# dry run — backup + preview DDL plan (no writes)
PYTHONUTF8=1 .venv/Scripts/python.exe \
  -m scripts.migrations.028_trials_bilingual_fulltext

# apply — backup + DDL (one transaction) + verify types
PYTHONUTF8=1 .venv/Scripts/python.exe \
  -m scripts.migrations.028_trials_bilingual_fulltext --apply

# then backfill full data + ka via the matcher (no --notify for a backfill)
PYTHONUTF8=1 .venv/Scripts/python.exe -m scripts.trials.eligibility_matcher
```

(Windows: `PYTHONUTF8=1` is required — cp1252 stdout cannot print Mkhedruli.)

If `SUPABASE_DB_URL` is unavailable, run the DDL by hand in the Supabase SQL
Editor (paste `028_trials_bilingual_fulltext.sql`), then re-run the matcher.

## Apply result (2026-06-15)

- types BEFORE: _filled in at apply time_.
- [ ] DDL applied — `title` / `brief_summary` / `eligibility_criteria` /
  `detailed_description` / `conditions` verified `jsonb`.
- [ ] Matcher backfill — full ctgov fields enriched from R2; ka filled vs
  en-fallback counts recorded in the Phase C SUMMARY.
