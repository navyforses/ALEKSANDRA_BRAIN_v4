# Migration 026 Runbook — Bilingual AI Analysis (`ai_summary`, `ai_aleksandra_implications`)

**Created:** 2026-06-14
**Owner:** agent (REST backfill) + **operator DDL** (one `ALTER COLUMN TYPE`).
**Scope:** make the two family-facing AI-analysis prose columns bilingual JSONB
`{en, ka}` so `/ka/research` shows the per-paper analysis in Georgian (it shows
English today). This is "Phase B" in `docs/SESSION-HANDOFF.md`.

## Why

`papers.title` / `papers.abstract` are already JSONB `{en, ka}` (migration 017),
and the viewer's `flatten(value, locale)` renders that shape and falls back
across locales. But `ai_summary` and `ai_aleksandra_implications` were `TEXT`
(English only) — so the Georgian site rendered English analysis text. Converting
them to JSONB lets the existing frontend show Georgian with **no functional UI
change** (only a `PaperRow` type update for correctness).

## What it does (three guarded steps, dry-run by default)

| step | action | touches |
|---|---|---|
| 1. backup | REST GET every paper's `id,ai_summary,ai_aleksandra_implications,ai_key_findings` → `%TEMP%/aleksandra_026_backup.json`. Always runs. | read-only |
| 2. ddl | run `026_bilingual_ai_analysis.sql` via psycopg2 (`SUPABASE_DB_URL`). **Idempotent-by-guard**: skipped when both columns are already `jsonb`. Wraps existing English as `{"en": <text>, "ka": null}`; NULL stays NULL. | **DDL on prod** |
| 3. backfill | fill the `ka` slot for the relevant, analysed papers. **FREE** for the 158 already in the KA digest cache (reuse, no API). A cache miss with non-empty `en` is translated via the Gemini translator (budget-guarded, refusal-safe). `en` stays authoritative; `ka` is never written when `en` is empty; an existing good `ka` is left untouched (idempotent). | REST PATCH |

`ai_key_findings` (`TEXT[]`) is intentionally left English — structured list,
lower priority.

## Ordering (important)

The DDL **must be applied to production before** the code that depends on it
merges to `main`:

- `scripts/analysis/analyze_paper.py` now writes `{"en": summary, "ka": null}`
  (a JSON object) — PATCHing that into a still-`TEXT` column would mis-store it.
- `scripts/migrations/025_repair_bilingual_ka.py` now also lists `ai_summary` /
  `ai_aleksandra_implications`. The **nightly** `repair-bilingual-ka.yml`
  (07:00 UTC) runs `025 --apply` across all tables; if it ran against `TEXT`
  columns it would try to PATCH a JSONB object into `TEXT`.

So: **apply 026 to prod → verify columns are `jsonb` → merge the PR.**

## The KA cache (why backfill is free)

`%TEMP%/aleksandra_ka_digest_cache.json` — built by the family digest generator,
keyed by paper id, each value `{title, summary, implications}` in Georgian, where
`summary` is the translation of `ai_summary` and `implications` of
`ai_aleksandra_implications` (verified against the generator: both were
translated from the same English the DB holds, right after the final Opus 4.8
re-analysis). 158 entries — exactly the relevant, analysed set. If the cache is
ever lost, the backfill falls back to live Gemini translation (budget-guarded).

## Usage

```bash
# dry run — backup + preview DDL + preview backfill plan (no writes)
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe \
  -m scripts.migrations.026_bilingual_ai_analysis

# apply — backup + DDL + ka backfill + verify
... 026_bilingual_ai_analysis --apply

# apply only the backfill (DDL already done by SQL Editor)
... 026_bilingual_ai_analysis --apply --skip-ddl
```

(Windows: `PYTHONUTF8=1` is required — cp1252 stdout cannot print Mkhedruli.)

If `SUPABASE_DB_URL` is unavailable, run the DDL by hand in the Supabase SQL
Editor (paste `026_bilingual_ai_analysis.sql`), then `--apply --skip-ddl`.

## Dry-run result (2026-06-14, pre-apply)

- backup: 789 papers (158 analysed) captured.
- column types before: `ai_summary` = text, `ai_aleksandra_implications` = text.
- backfill plan: 158 papers · **314 / 316 field-values from cache (free)** ·
  1 translated · 1 cache-miss failed translate (stays `en`-only → en fallback) ·
  0 skipped-have-ka · 0 skipped-no-en.

## Apply result (2026-06-14, operator-authorized)

- [x] **DDL applied** — `ai_summary` and `ai_aleksandra_implications` verified `jsonb`.
- [x] **Backfill** — 158 papers patched; 314 / 316 field-values from cache (free).
  - `ai_summary` with ka: **157 / 158**
  - `ai_aleksandra_implications` with ka: **157 / 158** (158 / 158 have en)
- [x] **2 stragglers, en-fallback (honest), not a defect:**
  - `51a6e0cc` (ai_summary) and `234ad791` (implications) — their cache `ka`
    carried a Cyrillic transliteration artifact ("N-ацетил…"), so `_good_ka`
    refused to ship it; the clean re-translation hit a Gemini **HTTP 429**
    (rate limit). Left `ka=NULL` → viewer falls back to `en`. The nightly
    `repair-bilingual-ka.yml` (`025 --apply`, now covering these two fields)
    re-translates them with the no-Cyrillic guard and will self-heal.
- [x] Spend: ~$0 (backfill is REST + free cache; the only LLM calls were the
  two 429'd retries, which cost nothing).
- [ ] `/ka/research` live spot-check (the deployed frontend already reads
  `{en, ka}`, so the DB change alone surfaces Georgian — no redeploy required).
