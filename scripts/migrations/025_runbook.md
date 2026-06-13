# Migration 025 Runbook — General Bilingual `ka` Repair

**Created:** 2026-06-13
**Owner:** agent (REST backfill) — no operator DDL needed (017 already made the
papers columns JSONB; all other tables were already JSONB).
**Scope:** every bilingual JSONB field across the family-facing tables, going
beyond 024 (which fixed `papers.title` only). Requested as the "professional,
complete" pass — repair until the audit is fully green.

## What it repairs

| table.field | kind | strategy | problem found | action |
|---|---|---|---|---|
| `therapies.name` | title | retranslate | Phase-6.1 dossiers + 2 silent mistranslations + 2 unusable en | re-translate from en (14); flag 2 |
| `therapies.evidence_summary` | prose | auto | a few blank/garbage-en | keep good, flag unusable |
| `hypotheses.title` | title | auto | leading markdown + 2 English mirrors | strip (5), translate (2) |
| `hypotheses.description` | prose | auto | clean | none |
| `aleksandra_timeline.title` | title | auto | leading `# ` (translation OK) | strip (6) |
| `aleksandra_timeline.description` | prose | auto | leading markdown + 1 Cyrillic "МРТ" | strip (7), translate (1) |
| `papers.title` | title | auto | 1 truncated + 2 refusals | translate (3) |
| `papers.abstract` | prose | auto | 499 en==ka mirrors | translate (459), keep (40), skip null (109) |

## Design (why it is safe)

- **Three actions, least-destructive first:**
  - `keep` — ka already good; only strip a leading `# `/`**` (LOSSLESS, no API).
  - `translate` — ka blank / English mirror / dossier / non-Georgian / stray
    CJK or Cyrillic / model commentary → (re)translate from en.
  - `flag` — en itself is unusable (`**` / blank); leave it, report for manual
    rebuild. **Never invents content.**
- **Two translators:**
  - title → direct sonnet-4-6 with `_TITLE_SYSTEM` (single line, no markdown,
    no commentary, Georgian+Latin only, idiom-aware). `_titleize` keeps the
    first line.
  - prose → shared `translate_to_georgian` (markdown-aware), then a leading-
    header + `**` strip; multi-line allowed, CJK/Cyrillic/commentary rejected.
- **Guards:** `_has_cjk` + `_has_cyrillic` (Georgian U+10A0–10FF never overlaps
  either) catch foreign-script artifacts; `_ka_messy` also catches model
  commentary. A translation that fails the guard is retried, then raises
  `TranslationFailed` (en kept — never a bad ka).
- **REST-only** (Supavisor pooler password fails auth); service-role key.
- **Resume-safe** (`skip` for no-op keeps), **budget-guarded**
  (`check_daily_budget` in the shared translator), per-row PATCH.
- **Backup:** `/tmp/aleksandra_ka_backup2/` (all four tables, captured before
  writes). Public research metadata — no PHI.

## Usage

```bash
# dry run (all tables) — prints keep/translate/flag/skip counts + samples
PYTHONUTF8=1 .venv-v7/Scripts/python.exe -m scripts.migrations.025_repair_bilingual_ka

# one table / one field
... 025_repair_bilingual_ka --table therapies --apply
... 025_repair_bilingual_ka --table papers --field abstract --apply
```

(Windows: `PYTHONUTF8=1` is required — cp1252 stdout cannot print Mkhedruli.)

## Result log (2026-06-13)

- **therapies.name:** 14 re-translated from en (fixed "blood-vessel"→
  `ჭიპლარის სისხლი` umbilical-cord and `პუპოსტრის`→`ჭიპლარის სისხლიდან მიღებული
  უჯრედები`); **2 FLAGGED for manual rebuild** — `fb4f27f1` (en `**`) and
  `7d8f2f7c` (en blank). Both are the known CLAUDE.md manual-rebuild therapies;
  they carry a real `mechanism_of_action` + link to hypothesis `93426696`, but
  the `name` cell must be set by the operator (not fabricated here).
- **therapies.evidence_summary:** good rows stripped/kept; `fb4f27f1`,
  `3b47f6ce` flagged (no usable en).
- **hypotheses.title:** 5 markdown-stripped (translation kept), 2 English
  mirrors translated (`c155e7eb`, `93426696`). description already clean.
- **aleksandra_timeline:** 6 titles markdown-stripped; 1 description
  re-translated to clear a Cyrillic "МРТ"→"MRI" artifact (`4c107d9b`); the rest
  stripped/kept.
- **papers.title:** `3296c5aa` ("Human") translated; `a638d030` (Chikungunya)
  refusal cleared by the stricter prompt; **`5e769694` still refuses** (title
  contains "cocaine" + "SARS-CoV-2" — a hard sonnet-4-6 safety-classifier trip
  across every framing). en kept, ka blank, documented — not hand-fabricated.
  → papers.title 607/608.
- **papers.abstract:** 459 translated / 40 already-good kept / 109 null-en
  skipped (no abstract exists). Second + third passes strip `**` bold and
  mid-text `## Methods/Design` section headers (lossless `keep` path, no API).
  2 rows (`99c48423` measles, `f0e893ad` diabetes) first failed the Cyrillic
  guard (model emitted "ШД"/"СД") → fixed with a no-Cyrillic-acronym prompt +
  Cyrillic-strip post-process.
- **Run spend (Anthropic):** ≈ $2.5–3.0 for the whole ka campaign (024 + 025;
  ~580 titles + 459 abstracts), well under the $5/day gate.

## Final scorecard (2026-06-13, post-repair)

Across all 8 bilingual JSONB fields — **0 en==ka mirrors, 0 markdown leftovers,
0 CJK, 0 Cyrillic** (the lone markdown hit is the flagged `fb4f27f1`, left for
manual rebuild). Per field `ka real / en present`:

| field | ka real / en | note |
|---|---|---|
| papers.title | 608 / 608 | `5e769694` now translated by Gemini (Claude had refused) |
| papers.abstract | 499 / 499 | 109 rows have no en abstract |
| hypotheses.title | 10 / 10 | green |
| hypotheses.description | 10 / 10 | green |
| therapies.name | 15 / 15 | `7d8f2f7c` (blank en) flagged |
| therapies.evidence_summary | 8 / 8 | 8 rows have no en summary |
| aleksandra_timeline.title | 9 / 9 | green |
| aleksandra_timeline.description | 9 / 9 | green |

## Residual / handed to the operator (Phase 5 Manager)

1. `therapies.name` for `fb4f27f1`, `7d8f2f7c` — set the real therapy name.
2. `papers.title` `5e769694` — add the Georgian title manually if desired
   (the model refuses to translate it).
3. `therapies.evidence_summary` for the 2 flagged rows — author from source.

## Translator bot + automation (2026-06-13, added after the one-time repair)

**Engine — `scripts/extraction/gemini_translator.py`.** A single reusable
EN→KA bot on Google's newest GA model **gemini-3.5-flash**:

- Two gateways, auto-selected: OpenRouter (`call_llm`, the "writer" tier) when
  `OPENROUTER_API_KEY` is present (Railway production parity, budget-gated +
  logged); otherwise direct Google AI Studio (`GEMINI_API_KEY`) with
  `thinkingConfig.thinkingBudget: 0` (Gemini 3.x otherwise spends the token
  budget on reasoning and truncates short titles). Both hit the same model.
- `translate_title` (one Mkhedruli line) / `translate_prose` (faithful, keeps
  paragraphs). Strict prompts + markdown/`**`/CJK/Cyrillic guards + retry +
  transient-error backoff (the public API 503s under load). A refusal/guard
  failure raises `TranslationFailed`; the caller keeps en.
- **Why Gemini:** it translates clinical titles the Claude classifier refused
  (e.g. the "cocaine" title `5e769694`) — switching the repair engine to Gemini
  closed that last residual, so papers.title is 608/608.
- `025` now delegates all translation to this bot (no Anthropic dependency);
  ingestion (`build_bilingual`) already used the gemini-3.5-flash writer tier.

**Source fix — `build_bilingual`** now sanitizes ka at write time (strip
markdown/bold; drop foreign-script to "" so the nightly bot re-does it), so new
papers land clean.

**Nightly safety net — `.github/workflows/repair-bilingual-ka.yml`.** Runs the
bot through `025 --apply` across all tables every night (07:00 UTC) + a manual
"Run workflow" button. Idempotent: clean rows skip, only broken ka is touched
(this run left 0 to do). Needs repo secrets: `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY` (and optional `OPENROUTER_API_KEY`).

## Root cause (resolved)

`papers.title/abstract` were TEXT only because migration 017 had never been
applied; the ingestion writer (`process_ledger._build_papers_row` →
`build_bilingual`) always produced `{en, ka}` dicts and posts them via
`requests(json=...)`. Now that the columns are JSONB, new perception-tick papers
store proper JSONB objects — no writer change required. (Ingestion translates
`ka` via the OpenRouter tier and falls back to `ka=""` on failure; the
resume-safe 024/025 backfills catch any such gaps.)
