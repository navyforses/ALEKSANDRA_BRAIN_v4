# Migration 017 Runbook — Papers JSONB i18n

**Created:** 2026-05-31
**Owner:** Shako (operator) + executor agent (verification)
**Estimated window:** 25–40 minutes (5 min apply + 20–30 min backfill)
**Estimated spend:** ~$3–5 (sonnet-4-6 translate × ~327 papers × ~$0.005-0.01 avg)
**Blast radius:** `papers` table only; RLS preserved; no other tables touched.

## What this changes

- `papers.title` **TEXT NOT NULL → JSONB NOT NULL** (mirror `ka = en` for existing rows)
- `papers.abstract` **TEXT nullable → JSONB nullable** (mirror `ka = en` for existing rows)
- Two trigram GIN indexes recreated on the `->>'en'` subkey so English-side search keeps working
- `_build_papers_row` in `scripts/chunking/process_ledger.py` now writes JSONB at ingestion time (translated via `scripts/extraction/translate.py`)

After 017 lands + backfill completes, every paper in the corpus has a real Georgian title and abstract visible on the site.

## Pre-flight (Shako)

```bash
psql "$SUPABASE_DB_URL" -c "SELECT pg_typeof(title), pg_typeof(abstract) FROM papers LIMIT 1;"
# Expect: text, text  (this is the BEFORE state)

psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM papers;"
# Expect: ~327 (verify against your current count)
```

If `pg_typeof = jsonb` already, **STOP** — migration already applied; jump to backfill (Step 3).

## Step 1 — Capture rollback artifact

```bash
mkdir -p scripts/migrations/017_rollback
pg_dump "$SUPABASE_DB_URL" \
  --table=papers --data-only --column-inserts \
  --no-owner --no-privileges \
  --file=scripts/migrations/017_rollback/papers.pre017.dump

psql "$SUPABASE_DB_URL" -c "\d papers" \
  > scripts/migrations/017_rollback/papers.policies.pre.txt
```

Verify the dump file is >1 KB and contains `INSERT INTO papers`.

## Step 2 — Apply the schema migration

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
  -f scripts/migrations/017_papers_jsonb.sql
```

Smoke check:

```bash
psql "$SUPABASE_DB_URL" <<SQL
SELECT 'papers.title' AS col, pg_typeof(title) FROM papers LIMIT 1;
SELECT 'papers.abstract' AS col, pg_typeof(abstract) FROM papers LIMIT 1;
SELECT count(*) AS mirrored FROM papers WHERE title->>'en' = title->>'ka';
SELECT count(*) AS total FROM papers;
SQL
```

Expected: both `pg_typeof = jsonb`, `mirrored = total`. If `mirrored < total`, **STOP** — the mirror didn't fire for some rows; investigate before backfill.

## Step 3 — Backfill ka translations

Dry run first:

```bash
python -m scripts.migrations.017_backfill_papers_ka
# Prints "N papers with untranslated ka"
```

Limited test run (3 papers, ~$0.05):

```bash
python -m scripts.migrations.017_backfill_papers_ka --apply --limit 3
```

Spot-check the result:

```bash
psql "$SUPABASE_DB_URL" -c \
  "SELECT title->>'en' AS en, title->>'ka' AS ka FROM papers WHERE title->>'en' != title->>'ka' LIMIT 3;"
```

If the `ka` column contains real Mkhedruli script (not English, not empty), proceed:

```bash
python -m scripts.migrations.017_backfill_papers_ka --apply
```

This is resume-safe — Ctrl-C and re-run is OK; only `ka == en` rows are processed.

## Step 4 — Verify

```bash
psql "$SUPABASE_DB_URL" <<SQL
SELECT
  count(*) FILTER (WHERE title->>'en' != title->>'ka') AS title_translated,
  count(*) FILTER (WHERE abstract IS NOT NULL AND abstract->>'en' != abstract->>'ka') AS abstract_translated,
  count(*) AS total
FROM papers;
SQL
```

Expected: `title_translated` close to `total` (a few rows may have translator refusals — that's OK, retry later). `abstract_translated` slightly lower than `total` because some papers legitimately have no abstract.

## Step 5 — Update viewer display (covered by this PR)

The viewer's existing `displayField` helper (Phase 6) reads `field?.[locale] ?? field?.en` — no code change needed in the viewer; the migration alone flips paper cards to bilingual.

Smoke-test on the deployed preview (Vercel):
1. Open `/ka/papers` (or wherever the corpus list is rendered).
2. Confirm paper titles render in Mkhedruli.
3. Open one paper; confirm abstract renders in Mkhedruli.
4. Switch language to `/en/papers`; confirm English.

## Step 6 — Commit artifacts

```bash
git add scripts/migrations/017_rollback/*.dump \
        scripts/migrations/017_rollback/*.txt
git commit -m "chore(017): capture papers pre-migration artifacts"
```

## Rollback

If anything goes wrong before the backfill commits:

```bash
psql "$SUPABASE_DB_URL" -c "
BEGIN;
DROP INDEX IF EXISTS idx_papers_title_trgm;
DROP INDEX IF EXISTS idx_papers_abstract_trgm;
ALTER TABLE papers
  ALTER COLUMN title TYPE text USING title->>'en',
  ALTER COLUMN abstract TYPE text USING abstract->>'en';
CREATE INDEX idx_papers_title_trgm ON papers USING GIN (title gin_trgm_ops);
CREATE INDEX idx_papers_abstract_trgm ON papers USING GIN (abstract gin_trgm_ops);
COMMIT;
"
```

This converts JSONB back to TEXT using the English half — the Georgian translation is lost but no data corruption.

After rollback, restore the pre-migration trgm indexes (the rollback SQL above does this) and `papers.pre017.dump` is your safety net for full row recovery if needed.

## What stays English-only

- `paper_chunks.text` — RAG retrieval chunks (~5,301 rows). Not displayed directly; English-only is intentional. Translating would cost ~$50+ and add no user value.
- `papers.authors`, `journal`, `pmid`, `doi` — proper nouns / identifiers; never translated.
- Spider's internal search queries — still English-native (clinical jargon).

## Why this is safe

- ALTER COLUMN TYPE does not drop RLS policies; migration 008's `service_role-all` + `authenticated-read` policies stay attached.
- The migration runs in a single BEGIN/COMMIT — partial failure rolls back cleanly.
- Backfill is per-row transactional; one bad row doesn't poison the rest.
- `build_bilingual()` at ingestion falls back to `ka=""` on translator failure instead of blocking the ingest — Spider keeps running even if Anthropic is down.
