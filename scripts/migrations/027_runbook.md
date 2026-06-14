# Migration 027 Runbook — Bilingual `therapies.mechanism_of_action`

**Created:** 2026-06-14
**Owner:** agent (REST backfill) + **operator DDL** (one `ALTER COLUMN TYPE`).
**Scope:** make `therapies.mechanism_of_action` bilingual JSONB `{en, ka}` so
`/ka/research` shows the therapy mechanism in Georgian (it showed English — the
column was `TEXT`). Matches `therapies.name` / `therapies.evidence_summary`,
which are already JSONB.

## Why (found 2026-06-14)

A reader sheet for a therapy showed the mechanism in English on the Georgian
site. Root cause: `mechanism_of_action` was `TEXT` (English only) and the ka
translation campaign (024/025) had not covered it. (Two sibling bugs were fixed
in the same PR on the frontend: `flatten()` no longer dumps raw JSON metadata,
and `therapies.ai_assessment` — pipeline metadata, not prose — is no longer
surfaced to the reader.)

## What it does (three guarded steps, dry-run by default)

| step | action | touches |
|---|---|---|
| 1. backup | REST GET every therapy's `id,mechanism_of_action` → `%TEMP%/aleksandra_027_backup.json`. | read-only |
| 2. ddl | run `027_bilingual_therapy_mechanism.sql` via psycopg2 (`SUPABASE_DB_URL`). Idempotent-by-guard: skipped when already `jsonb`. | **DDL on prod** |
| 3. backfill | translate the `ka` slot from `en` via the Gemini translator (budget-guarded, refusal-safe). `en` authoritative; `ka` never written when `en` empty; a good `ka` left untouched; a messy/Cyrillic translation refused (en fallback). ~16 rows. | REST PATCH |

## Ordering

Apply 027 to prod **before** merging the code that depends on it:
- `extract_candidates.py` now writes `mechanism_of_action` as `{"en":…, "ka":null}`.
- `025_repair_bilingual_ka.py` now lists `mechanism_of_action`; the nightly
  `repair-bilingual-ka.yml` would otherwise PATCH a JSONB object into `TEXT`.

So: **apply 027 → verify column is `jsonb` → merge the PR.**

## Usage

```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe \
  -m scripts.migrations.027_bilingual_therapy_mechanism            # dry run
... 027_bilingual_therapy_mechanism --apply                        # DDL + translate
... 027_bilingual_therapy_mechanism --apply --skip-ddl             # backfill only
```

If `SUPABASE_DB_URL` is unavailable, paste `027_bilingual_therapy_mechanism.sql`
into the Supabase SQL Editor, then `--apply --skip-ddl`.

## Apply result (2026-06-14, operator-authorized)

- [x] **DDL applied** — `mechanism_of_action` verified `jsonb`.
- [x] **ka backfill: 10 / 16 mechanisms now Georgian.**
  - The production Gemini path was rate-limited (HTTP 429, free-tier daily
    quota), so all 16 failed there. 10 were filled via a one-off Anthropic
    translate pass (the engine that built the digest cache); it adds short
    family-friendly glosses for terse medical terms (e.g. "anticonvulsant" →
    "ანტიკონვულსანტი (კრუნჩხვის საწინააღმდეგო …)") — explanatory, not fabricated.
  - Anthropic returned empty for the remaining 6 (`3b47f6ce`, `fb4f27f1`,
    `7d8f2f7c`, `f84c92d6`, `347adbe2`, `681cc49f`) — left `ka=NULL` → the viewer
    falls back to `en` (honest English, no regression).
- [x] **Sibling frontend fixes** shipped in the same PR: `flatten()` no longer
  dumps raw JSON metadata; `therapies.ai_assessment` (metadata) is no longer
  surfaced to the reader; `SourceTag` label/value spacing.
- [ ] **The 6 self-heal** via the nightly `repair-bilingual-ka.yml`
  (`025 --apply`, now covering `mechanism_of_action`) once the Google quota
  resets. To do it sooner: `... 027_bilingual_therapy_mechanism --apply --skip-ddl`.
- _Future:_ add an Anthropic fallback inside `gemini_translator` so a Google 429
  does not block translation (and use a faithful, gloss-free prompt for parity).
