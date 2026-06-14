# SESSION HANDOFF — ALEKSANDRA_BRAIN

> **NEXT SESSION: READ THIS FIRST.** This file lets a fresh Claude Code session
> continue *exactly* where the last session stopped. Written for both the next AI
> session (precise, actionable) and Shako (the non-programmer owner).
> **No secrets in this file** — the repo is public.
>
> ქართულად Shako-სთვის: ეს ფაილი ინახავს რა გავაკეთეთ + რა დარჩა + როგორ გავაგრძელოთ.
> შემდეგ სესიაში უბრალოდ თქვი: **„წაიკითხე docs/SESSION-HANDOFF.md და გააგრძელე."**

Last updated: **2026-06-14** (continuation session — Phase B + security + viewer fixes)

---

## 0. TL;DR — where we are

The analysis brain works end-to-end **and the family site is now fully Georgian,
paginated, and clickable.** Both blockers from the previous handoff are **CLOSED**:

1. ✅ **Security** — Shako rotated the Supabase DB password; `.env` updated; verified.
2. ✅ **Phase B** — per-paper analysis (`ai_summary`, `ai_aleksandra_implications`)
   now bilingual JSONB `{en, ka}` and showing **in Georgian** on `/ka`.

Plus several viewer bugs the owner spotted were fixed and shipped (pagination,
metadata leak in the reader, English therapy text, non-clickable home cards), and
the translator was made resilient (now runs on **paid Gemini via OpenRouter** — no
more free-tier rate limits).

Production site: **https://viewer-sigma-two.vercel.app** (`main` auto-deploys to Vercel).

---

## 1. DONE this session

| # | Work | State / ref |
|---|------|-------------|
| 1 | **Phase B** — `ai_summary` + `ai_aleksandra_implications` → JSONB `{en,ka}`; ka backfilled FREE from the digest cache | migration **026**, **PR #24**, live (157/158 then) |
| 2 | **Security** — DB password rotated by owner; `.env` `SUPABASE_DB_URL` updated; psycopg2 `select 1` OK | done |
| 3 | **/research pagination** — 5 items/page + numbered switcher (ellipsis windowing), auto-grows, resets on filter/search | **PR #25**, live |
| 4 | **Reader metadata leak** — `flatten()` no longer dumps raw JSON; a valid-JSON object with no text → `""` (never raw). `therapies.ai_assessment` (metadata) no longer surfaced | **PR #26**, live |
| 5 | **Therapy mechanism bilingual** — `therapies.mechanism_of_action` TEXT → JSONB `{en,ka}` | migration **027**, **PR #26**, live |
| 6 | **SourceTag spacing** — `წყაროpreclinical` → `წყარო preclinical` | **PR #26**, live |
| 7 | **Translator Claude fallback** — `gemini_translator` 3rd gateway when both Gemini gateways fail | **PR #27**, merged |
| 8 | **Home "what needs you" cards now clickable** — shared `Reader` extracted; cards open the reading sheet (were static `<li>`) | **PR #28**, live |
| 9 | **OpenRouter restored** — `OPENROUTER_API_KEY` added to `.env`; translator primary = **Gemini via OpenRouter** (no 429). All 16 therapy mechanisms re-translated faithfully by Gemini (uniform, no glosses) | done |

PRs **#24–#28** merged to `main`. Migrations **026, 027** applied to prod (full
backups taken first → `%TEMP%/aleksandra_026_backup.json`, `aleksandra_027_backup.json`).

---

## 2. CRITICAL environment facts (read before running anything)

- **venv:** `.venv/Scripts/python.exe` (Windows, Python 3.12). Always prefix LLM
  runs with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` (cp1252 stdout crashes on Mkhedruli).
- **Translator routing (`scripts/extraction/gemini_translator.py`):** 3 gateways
  tried in order — (1) **OpenRouter Gemini** `google/gemini-3.5-flash` (now PRIMARY,
  `OPENROUTER_API_KEY` present, ~$25 credit, paid → no free-tier 429), (2) direct
  Google Gemini (free tier, daily-quota limited), (3) **Claude** last-resort
  fallback. ⚠️ Claude's safety classifier **refuses** some clinical/gene-therapy
  phrasings (`stop_reason="refusal"` → empty) — **Gemini handles those**, so keep
  Gemini primary.
- **LLM model registry** (`scripts/cognition/models.py`): translate tier =
  `google/gemini-3.5-flash`. `MODEL_PROVIDER` is **not** forced to anthropic
  anymore (default = openrouter). `call_llm` is budget-gated + writes one `runs` row.
- **Budget:** `.env` `DAILY_BUDGET_USD` cap; `check_daily_budget()` raises
  `BudgetExceeded` before each LLM call. Translation is cents — well under cap.
- **Supabase — two paths:** REST (`SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`,
  always works, used for all reads/writes) and direct Postgres (`SUPABASE_DB_URL`,
  for DDL/migrations — **works** after the password rotation).
- **Bilingual JSONB columns** (shape `{en, ka}`, rendered by `viewer/lib/data.ts`
  `flatten(value, locale)` which falls back across locales): `papers.title`,
  `papers.abstract`, `papers.ai_summary`, `papers.ai_aleksandra_implications`,
  `therapies.name`, `therapies.evidence_summary`, `therapies.mechanism_of_action`,
  `hypotheses.title/description`, `aleksandra_timeline.title/description`, `briefs.sections`.
- **Nightly ka safety net:** `.github/workflows/repair-bilingual-ka.yml` runs
  `025 --apply` (now covers `ai_summary`, `ai_aleksandra_implications`,
  `mechanism_of_action`) — idempotent, only fixes blank/mirror ka.
- **Deploy flow:** branch → PR → `gh pr merge --merge` → `main` → Vercel auto-deploy.
  Code changes need the redeploy; pure DB-data changes show immediately.

---

## 3. REMAINING WORK

**Priority 1 (security) and Priority 2 (Phase B) are DONE.** What's left:

### A. Production env parity (so prod doesn't hit free-Google 429)
The `OPENROUTER_API_KEY` (and ideally `ANTHROPIC_API_KEY` for the fallback) live
only in the **local** `.env`. For the same resilience in production, add them as:
- **Railway worker** env vars (ingestion + analysis translate at scale), and
- **GitHub Actions secrets** for `repair-bilingual-ka.yml` (the nightly repair).
Until then, those run on the free Google tier and can 429.

### B. Two therapies still need real names (carried from prior handoff)
`fb4f27f1` (en name `**`) and `7d8f2f7c` (en name blank) — their `mechanism_of_action`
ka is now translated, but the **name** must be set by the operator (never fabricated).
Rebuild via Phase 5 Manager.

### C. Prior open items (unchanged)
- Phase 10 v7 tables (016/018/019/020) not applied live (frontend honest-mock-with-banner).
- `weekly_brief.py` PDF digest (now runnable — direct DB works).
- `docs/FINDINGS-DIGEST-KA.md` is ~587 KB (over the 50 KB doc ceiling) — keep out of
  normal commits or split.
- 15 unscored papers (`relevance.py` backfill), low priority.

---

## 4. HOW TO RESUME (next session)
1. Read this file.
2. `git fetch origin && git log --oneline origin/main -5` (expect PR #28 merge or later).
3. Confirm DB + translator: a `select 1` via `SUPABASE_DB_URL`, and a quick
   `translate_prose("...")` (should route via OpenRouter Gemini).
4. Pick up at **Remaining Work A** (prod env parity) or whatever the owner asks.
5. Use `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` for python LLM runs; respect the budget cap.

## 5. Guardrails (project rules — always)
- **Never fabricate.** No source → say so. Every surfaced fact carries provenance.
- **No medical decisions** — surface/rank/explain only; a real clinician decides.
- **MRI/PHI stays client-side**, never server / third-party API.
- **PHI never enters Telegram/Gmail/Notion** without redaction.
- Code + comments in English; docs in KA + EN; Conventional Commits.
- **Secrets never in chat or the repo** — `.env` only (gitignored).
