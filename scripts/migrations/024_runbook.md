# Migration 024 Runbook — Repair `papers.title.ka`

**Created:** 2026-06-12
**Owner:** Shako (runs 017 DDL in Supabase SQL Editor) + agent (runs 024 backfill via REST)
**Scope:** `papers.title` ONLY. `papers.abstract` and the JSONB tables
(`therapies`, `hypotheses`, `aleksandra_timeline`) were explicitly deferred by
operator decision on 2026-06-12.
**Estimated spend:** ~$0.22 (≈557 short titles × sonnet-4-6 ≈ $0.0004 each), under the $5/day `budget.py` gate.
**Blast radius:** `papers` table only; RLS preserved.

> **Numbering note:** this is `024_*`, not `018_*` as an earlier brief suggested —
> `018_scm_tables.sql` already owns 018. Highest prior migration was 023.

---

## Why two actors

A live audit (`python scripts/audit_data_quality.py`) on 2026-06-12 found:

- `papers` has **608 rows** (not 30). `title.ka`: **557 blank**, **51 real**.
- **`papers.title` / `papers.abstract` are still `TEXT`** in the live DB —
  migration `017_papers_jsonb.sql` was **never applied**. (Confirmed via the
  PostgREST OpenAPI schema: `papers.title format='text'`.) That is the root
  cause of the blank `ka`: there is no `{en, ka}` structure to populate.
- The 51 "real ka" rows are `build_bilingual()` dicts that PostgREST
  **stringified into JSON-text** (`'{"en":"X","ka":"Y"}'`) inside the TEXT
  column. They parse, hence "real", but they are not proper JSONB.

**`psql` / `psycopg2` cannot be used** — the Supavisor pooler password in
`SUPABASE_DB_URL` fails auth (`password authentication failed for user
"postgres"`, the known "pooler drift"). Therefore:

| Step | Tool | Who |
|---|---|---|
| 017 DDL (`ALTER TABLE … TYPE jsonb`) | **Supabase SQL Editor** (REST can't run DDL) | **Shako** |
| 024 ka backfill (per-row PATCH) | PostgREST REST API + service-role key | **agent** |

---

## Step 0 — Backup (DONE, re-runnable)

A full read-only REST backup of the affected columns is already captured at
`/tmp/aleksandra_ka_backup/` (`papers.json` = 608 rows of `id,title,abstract`).
The column is public research metadata — **no PHI**. To refresh it:

```bash
python - <<'PY'
import json, os, urllib.request
from pathlib import Path
for c in (Path.cwd()/".env",):
    for line in c.read_text(encoding="utf-8").splitlines():
        s=line.strip()
        if s and not s.startswith("#") and "=" in s:
            k,_,v=s.partition("="); os.environ.setdefault(k.strip(), v.strip().strip("'\""))
U=os.environ["SUPABASE_URL"].rstrip("/"); K=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
r=urllib.request.Request(f"{U}/rest/v1/papers?select=id,title,abstract&limit=5000",
    headers={"apikey":K,"Authorization":f"Bearer {K}"})
Path("/tmp/aleksandra_ka_backup").mkdir(parents=True, exist_ok=True)
Path("/tmp/aleksandra_ka_backup/papers.json").write_text(
    urllib.request.urlopen(r,timeout=60).read().decode(), encoding="utf-8")
print("backup refreshed")
PY
```

---

## Step 1 — Shako: apply 017 in the Supabase SQL Editor

Open **Supabase Dashboard → SQL Editor → New query**.

### 1a. Pre-flight (confirm BEFORE state)

```sql
SELECT pg_typeof(title) AS title_type, pg_typeof(abstract) AS abstract_type
FROM papers LIMIT 1;
-- Expect: text, text.  If already jsonb → STOP, 017 ran; jump to Step 2.

SELECT count(*) AS total FROM papers;   -- expect ~608
```

### 1b. Apply (paste the full body of `scripts/migrations/017_papers_jsonb.sql`)

It runs in a single `BEGIN … COMMIT`, so a partial failure rolls back cleanly.
In short it: drops the two trigram GIN indexes, does
`ALTER TABLE papers ALTER COLUMN title TYPE jsonb USING jsonb_build_object('en', title, 'ka', title)`
(same for `abstract`, NULL-preserving), then recreates the trigram indexes on
`(title->>'en')` / `(abstract->>'en')`.

> **Expected, harmless side effect:** for the 51 JSON-text rows, 017's naive
> mirror produces `{"en": '{"en":"X","ka":"Y"}', "ka": <same>}` — a
> **double-encoded** `en`. This is fine: **Step 3 (024) unwraps every one of
> them** back to a clean `{en: "X", ka: "Y"}`. Do not hand-edit 017 to try to
> handle this — 024 owns the cleanup and is testable.

### 1c. Smoke check (confirm AFTER state)

```sql
SELECT pg_typeof(title) AS title_type, pg_typeof(abstract) AS abstract_type
FROM papers LIMIT 1;
-- Expect: jsonb, jsonb.

SELECT count(*) FILTER (WHERE title->>'en' = title->>'ka') AS mirrored,
       count(*) AS total
FROM papers;
-- Expect: mirrored = total (every row mirrored at this point; 024 fixes ka next).
```

If `title_type` is not `jsonb`, **stop** and report — 024 will refuse to run.

---

## Step 2 — agent: confirm the column flipped

```bash
# 024 itself prints the authoritative column format from the OpenAPI schema:
PYTHONUTF8=1 .venv-v7/Scripts/python.exe -m scripts.migrations.024_fix_papers_title_ka
# First line must read: "[024] papers.title column format: jsonb"
```

024 **refuses `--apply` while the column is still TEXT** (exit 3) so a dict can
never be re-stringified into a TEXT column.

---

## Step 3 — agent: backfill `ka` (the 024 script)

Always use the `.venv-v7` interpreter (has anthropic + httpx + boto3 + psycopg2)
and force UTF-8 on Windows (cp1252 stdout cannot print Mkhedruli):

```bash
# Dry run — prints the plan + 5 real sample translations, writes nothing.
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  .venv-v7/Scripts/python.exe -m scripts.migrations.024_fix_papers_title_ka --samples 5

# Cost-bounded test (writes 5 rows, ~$0.002).
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  .venv-v7/Scripts/python.exe -m scripts.migrations.024_fix_papers_title_ka --apply --limit 5

# Full apply (≈557 translations + 51 structure-only rewrites, ≈$0.22).
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  .venv-v7/Scripts/python.exe -m scripts.migrations.024_fix_papers_title_ka --apply
```

What 024 does per row:

1. **Unwrap** double-encoded `en`/`ka` (the 51 JSON-text rows).
2. **Strip** leading markdown (`#…# `, `**`) from `ka` — including from the
   translator's own output, because sonnet-4-6 sometimes prepends `# ` to a
   title (the exact corruption mode being repaired).
3. **(Re)translate** `ka` from `en` when `ka` is blank, an English mirror,
   non-Georgian, or still blob-like — via `translate_to_georgian(en,
   client=anthropic.Anthropic())`, forcing the **sonnet-4-6** strict path with
   the reframed "translation utility … do not refuse" system prompt.
4. **PATCH** a proper JSONB `{en, ka}` object.

It is **resume-safe** (re-running skips rows already clean) and
**budget-guarded** (`check_daily_budget()` inside the translator; `--limit` as a
hard per-run cap). Refusals raise `TranslationFailed`: the English is kept, the
`id` is logged, and a blank `ka` is written rather than an invented one — never
a fabricated translation.

---

## Step 4 — Verify

```bash
PYTHONUTF8=1 .venv-v7/Scripts/python.exe scripts/audit_data_quality.py > /tmp/audit_after.txt 2>&1
diff /tmp/audit_before.txt /tmp/audit_after.txt
```

**Acceptance (papers.title):**
- `ka real` ≈ 608 / 608 (minus any genuine translator refusals, listed separately).
- `blank` = 0, `corrupt title` = 0 (the bracketed-English `[…]` false-positives
  disappear once stored as proper `{en, ka}`).

**Spot-check 3 random rows are natural Mkhedruli (not English, not markdown, not JSON):**

```bash
PYTHONUTF8=1 .venv-v7/Scripts/python.exe - <<'PY'
import json, os, urllib.request
from pathlib import Path
for line in (Path.cwd()/".env").read_text(encoding="utf-8").splitlines():
    s=line.strip()
    if s and not s.startswith("#") and "=" in s:
        k,_,v=s.partition("="); os.environ.setdefault(k.strip(), v.strip().strip("'\""))
U=os.environ["SUPABASE_URL"].rstrip("/"); K=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
r=urllib.request.Request(f"{U}/rest/v1/papers?select=id,title&limit=3&order=ingested_at.desc",
    headers={"apikey":K,"Authorization":f"Bearer {K}"})
for row in json.loads(urllib.request.urlopen(r,timeout=30).read().decode()):
    t=row["title"]; print(row["id"][:8], "|", (t.get("en") if isinstance(t,dict) else t)[:50])
    print("   ka:", (t.get("ka") if isinstance(t,dict) else None))
PY
```

---

## Rollback

Per-row safety net first: `/tmp/aleksandra_ka_backup/papers.json` holds the
pre-change `title` for all 608 rows; re-PATCH from it if a write looks wrong.

Full schema rollback (Shako, SQL Editor — converts JSONB back to TEXT using the
English half; Georgian translations are lost but no corruption):

```sql
BEGIN;
DROP INDEX IF EXISTS idx_papers_title_trgm;
DROP INDEX IF EXISTS idx_papers_abstract_trgm;
ALTER TABLE papers
  ALTER COLUMN title    TYPE text USING title->>'en',
  ALTER COLUMN abstract TYPE text USING abstract->>'en';
CREATE INDEX idx_papers_title_trgm    ON papers USING GIN (title gin_trgm_ops);
CREATE INDEX idx_papers_abstract_trgm ON papers USING GIN (abstract gin_trgm_ops);
COMMIT;
```

---

## Result log (2026-06-13)

- **017 applied in SQL Editor:** 2026-06-13 by Shako. Pre-flight `text, text`;
  post `jsonb, jsonb`; `mirrored = total = 608`. ✅
- **024 first pass** (`--apply`): 608 rows patched · 555 ka translated · 51
  structure/strip-only · **2 genuine refusals** (en kept, ka blank):
  - `a638d030` — "Against Chikungunya Virus and Neonatal Infection"
  - `5e769694` — "Chronic cocaine exposure … SARS-CoV-2 spike protein in the rat"
- **024 second pass** (`--polish --apply`): 5 rows had multi-line / markdown /
  commentary / stray-CJK first-pass output (the shared translator's
  "preserve markdown" prompt made sonnet-4-6 elaborate a few titles). Re-translated
  with the strict single-line `_TITLE_SYSTEM` prompt: 4 fixed automatically
  (`e877d32e`, `45323db1`, `db0b4b38`, `64301a99`); 1 (`abf5b02b`, the
  "calm before the storm" idiom → kanji 嵐) fixed on a model rewrite with an
  idiom hint → "სიმშვიდე ქარიშხლამდე …". No hand-authored Georgian.
- **Run spend (Anthropic):** ≈ $0.30–0.40 (≈560 sonnet-4-6 title calls; well
  under the $5/day gate). 2 transient cost-ledger write blips (`getaddrinfo`,
  DNS) — translations themselves succeeded.
- **Post-audit `papers.title`:** 608/608 proper JSONB · ka real **606/608** ·
  blank **2** (the refusals) · markdown 0 · multiline 0 · CJK 0 · mirror 0.
  The audit still prints `corrupt title: 4` — those are **bracketed-English
  false positives** (`ddbb5587`, `dbfeae1d`, `2ee4c013`, `922cf5fe`): correctly
  translated PubMed titles that begin with `[`, which the heuristic over-flags.
- **Scope honored:** `papers.title` only. `papers.abstract` is now JSONB with
  `ka = en` mirror (untranslated) — deferred. `therapies` / `hypotheses` /
  `aleksandra_timeline` JSONB cleanup — deferred.

## Root-cause follow-up (out of scope here, worth a separate task)

The ingestion writer (`scripts/chunking/process_ledger.py::_build_papers_row`)
calls `build_bilingual()`, which already returns `{en, ka}` dicts — but while
`papers.title` was TEXT, PostgREST stringified them into JSON-text, and rows
inserted by other paths (`fetch_pubmed` etc.) wrote plain English with no `ka`.
Once 017 makes the column JSONB, new `build_bilingual()` rows store correctly.
Verify a fresh perception-tick paper lands as proper JSONB `{en, ka}` so this
backfill does not have to be repeated.
