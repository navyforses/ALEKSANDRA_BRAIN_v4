# ALEKSANDRA_BRAIN — სესიის ჰენდოფი (Phase 2.5B mid-flight)

**თარიღი:** 2026-05-15 (ღამის სესია)
**გამავალი მოდელი:** Claude Opus 4.7 (1M context) — `claude-opus-4-7[1m]`
**გამავალი სესიის ID:** `860213fd-9256-49a2-b151-d3a67febf1f9`
**პროექტის root:** `c:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane`
**ფილიალი:** `main` (remote push არ მცდია — Claude Code-ის auto-classifier `git push main`-ს ბლოკავს)
**წინა ჰენდოფი დაარქივებულია:** `.handoffs/handoff-2026-05-15-night.md`

---

## 1. გოლი

**ობიექტივი:** Phase 2.5B (Perception Scale-up) — ledger 30 → 100+, papers 30 → 80+, chunks 409 → 5000+, ყველა ახალ papers-ს `relevance_score` Haiku 4.5-ით; დღევანდელი ღამის ციკლი = **Cycle 1 ლოკალურად დასრულდა**, Cycle 2 ან Railway-ის deploy ხდება შემდეგ სესიაში.

**"დასრულებულის" განმარტება Phase 2.5B-სთვის (Gate B 4/4):**
- B.1: Railway perception_worker deployed + n8n `perception_6h.json` active + tick logged → **არ არის გაკეთებული** (user-side deploy ჯერ არ ჩატარდა)
- B.2: `evidence_ledger ≥ 100` → ✅ **გადააჭარბა (302)**
- B.3: `paper_chunks ≥ 5000` AND Qdrant `papers` collection ≥ 5000 → ⚠️ **chunks=4176 (83.5%)**, Qdrant ცალკე უნდა გადამოწმდეს
- B.4: Neo4j `Entity {group_id:'hie_research'} ≥ 500` → ❌ **ჯერ ვერ გადამოწმდა** (batch_ingest არ გაშვებულა)

**სკოპის საზღვრები (NOT in scope ამ სესიამდე):**
- ❌ Phase 2.5C (Dashboard / Cloudflare Access)
- ❌ Phase 2.5D (Curator UI / hypothesis flips)
- ❌ Railway deploy — user-side, ხელით
- ❌ batch_ingest (Graphiti extraction) — overnight cycle-ის მე-3 ნაბიჯი, **ჯერ არ გაშვებული**
- ❌ Cycle 2 perception loop — ბიუჯეტი დარჩა, მაგრამ სესია იწურება
- ❌ Phase 3/4-ის ნებისმიერი მუშაობა (Communicator, DSPy, NiiVue, Ask BRAIN)

---

## 2. ამჟამინდელი შტატი

### რა მუშაობს (გადამოწმებული)

**Live Supabase counts (2026-05-15 ღამის ციკლის ბოლოს, `psycopg2`-ით პირდაპირ DB-დან):**
```
evidence_ledger           = 302    (was 45 → +257 ერთ ციკლში)
papers                    = 245    (was 33 → +212)
papers_scored             = 233    (95% scored)
papers_unscored           = 12     (NULL relevance_score; OR-2 fallback worked)
paper_chunks              = 4176   (was ~409 → +3767)
hypotheses                = 10     (unchanged from Phase 2)
hypotheses_confirmed      = 0      (Gate D target ≥5)
today_llm_calls           = 236
today_spend_usd           = $0.216808   (cap დღევანდელ სესიაში $3.0, 7%-ში ვართ)
```

**Cycle 1 outcome (perception_tick full → process_ledger full):**
- `scripts.perception_tick` (no `--small`): 371 წამში +257 ledger rows (pubmed=178, ctgov=23, preprints=12, gap-fill=20, negative=24). LLM=$0.
- `scripts.chunking.process_ledger` (full + `score=True`, limit=200): summary-ში `chunks_inserted: 0` ★ მაგრამ live DB-ში paper_chunks 409→4176 (+3767). 212 ახალი paper, 200 relevance scored Haiku 4.5-ით (200 calls ≈ $0.20).
  - ★ შენიშვნა: summary-ის `chunks_inserted: 0` შეცდომა-ჰგავს, მაგრამ DB-მ ნამდვილად მიიღო ჩუნკები. სავარაუდოდ ხდება run-ის შიდა counter-ის bug ან მე-2 sweep-ი ცარიელი ხდება პირველის შემდეგ. **შემდეგი სესია უნდა გადახედოს `scripts/chunking/process_ledger.py`-ის totals-ის ლოგიკას.**
- 269 `errors` reported — სავარაუდოდ ledger rows-ი, რომელთაც არ ჰქონდათ scrapeable text (negative/ctgov/preprints რომელთა PDF არ ჩამოიქაჩა). არც-ფატალურია; pipeline-მ ბოლომდე გავიდა exit 0.

**ფუნდამენტი (Phase 2.5A-დან, უცვლელი):**
- ✅ `scripts/cognition/llm.py` — `call_claude` (sync) + `make_instrumented_async_anthropic` (async) — ერთადერთი გზა Anthropic SDK-სთან
- ✅ `runs.token_cost` NUMERIC(14,8) precision (migration 007 applied)
- ✅ `check_daily_budget()` enforced both sync + async paths (HC-2 hard cap $12 + soft warn $10)
- ✅ 4 Phase 2 wrappers route through call_claude (zero `anthropic.Anthropic(` outside `scripts/cognition/llm.py:190`)

### რა არის გაფუჭებული ან ნაწილობრივი

| ნივთი | სტატუსი | რა გასაკეთებელია |
|---|---|---|
| `process_ledger` summary `chunks_inserted: 0` | მიუხედავად იმისა, რომ DB-მ +3767 chunk მიიღო, counter null-ი ჰქონდა | `scripts/chunking/process_ledger.py`-ის totals dict-ი გადახედე |
| `batch_ingest` (Graphiti extraction) | ჯერ არ გაშვებული ამ ციკლში | overnight cycle-ის სამი ფაზიდან მე-3 დარჩა; ~$1-2 |
| Qdrant vector count | DB chunk-ი 4176, მაგრამ Qdrant `papers` collection-ი ცალკე გადასამოწმებელია | `qdrant.count('papers')` ან verify_phase2 MEM-02 |
| 12 papers without relevance_score | OR-2 fallback (Haiku failure / empty abstract) | backfill `scripts.scoring.relevance --backfill --limit 50` |
| Gate B verify | `verify_phase2_5 --gate b` შემდეგ batch_ingest გაშვების შემდეგ უნდა გაიაროს | რომელიც Cycle 1-ის ბოლო ნაბიჯია |

### ფილიალი, ბოლო ვალდებულება, ბინძური ფაილები

```
branch: main
HEAD:   1c6632d feat(phase-2.5B): verify_phase2_5 harness + chunking/extraction/digest workflows
last 5: 1c6632d feat(phase-2.5B): verify_phase2_5 harness + chunking/extraction/digest workflows
        a8a3077 feat(phase-2.5B): wire relevance scoring into process_ledger pipeline
        2f1b9a6 feat(phase-2.5B): perception_worker (HTTP) + scoring/relevance.py scaffold
        c094385 feat(phase-2.5): add hypothesis paper backfill
        bbd80cc docs(audit): add activity diagnostic handoff

git status:
  ?? docs/PHASE_2_LIVE_AUDIT.md     (Phase 2 closing artifact; უნდა დაკომიტდეს)
  ?? handoff.md                      (ეს ფაილი — შემდეგ overwrite-ის შემდეგ უნდა დაკომიტდეს)
  ?? .handoffs/handoff-2026-05-15-night.md   (archived prior handoff)
```

### სერვისები/პორტები/ფონის პროცესები

- **არცერთი ფონის პროცესი ცოცხალი არ არის** — `process_ledger` background task `bcx6qqmt0` დასრულდა exit 0-ით.
- Docker services (Phase 2-დან): `docker ps --filter name=aleksandra` → Neo4j (port 7687), Qdrant (port 6333) უნდა იყვნენ live (პრე-flight გადასამოწმებელია).
- Railway: ჯერ არ აქვს deployed perception_worker. n8n workflows-ი `workflows/*.json` `active: false`-ში არიან.
- პორტი 8000: Railway-ის deploy შემდეგ perception_worker იქ უნდა იყოს; ლოკალურად `python -m scripts.perception_worker` smoke-ისთვის.
- DAILY_BUDGET_USD env var დაყენებული იყო `=3.0` ციკლისთვის — ეს გარემოს ცვლადი მხოლოდ ამ shell sessions-ში ცოცხალია.

---

## 3. აქტიური ფაილები

| ფაილი | დანიშნულება | მომლოდინე ცვლილება |
|---|---|---|
| `scripts/perception_worker.py` | stdlib http.server, 3 POST endpoints (/perception-tick, /chunking-tick, /extraction-tick) | მზადაა; Railway deploy მოლოდინში (user-side) |
| `scripts/scoring/relevance.py` | Haiku 4.5 single-paper relevance classifier | მზადაა; 12 unscored row-ი დარჩა backfill-სთვის |
| `scripts/chunking/process_ledger.py` | populate_papers + chunk + embed + score | **bug review-ში: summary totals chunks_inserted=0 ცრუა** |
| `scripts/verify_phase2_5.py` | 15-item Gate A/B/C/D harness | მზადაა; Cycle 1-ის შემდეგ ხელახლა გაშვება საჭიროა |
| `workflows/chunking_trigger.json` | n8n 30-min cron → /chunking-tick | მზადაა; deploy-ის შემდეგ active=true |
| `workflows/extraction_trigger.json` | n8n 30-min cron → /extraction-tick | მზადაა; deploy-ის შემდეგ active=true |
| `workflows/daily_digest.json` | n8n 09:00 UTC template-based digest | მზადაა; deploy-ის შემდეგ active=true |
| `workflows/perception_6h.json` | n8n 6h perception cron (Phase 2.5-ის წინ შემუშავებული) | active=false; deploy-ის შემდეგ active=true |
| `scripts/hypothesis/backfill_supporting_papers.py` | user-მა plan mode-ში დაამატა (commit c094385) | **2.5D-ში გასაშვები `--apply` რეჟიმში** |
| `docs/PHASE_2_LIVE_AUDIT.md` | Phase 2 დახურვის external 21-item audit | uncommitted; დაკომიტდეს Cycle 1 status commit-ში |
| `handoff.md` | ეს ფაილი | uncommitted; დაკომიტდეს `chore: handoff` commit-ში |

**TodoWrite stale state:** [in_progress: 1] + [pending: 6]. შემდეგი სესია უნდა გადატვირთოს — ციკლი ნახევრად დასრულდა (perception+chunking ✅, batch_ingest+verify+commit ❌).

---

## 4. გადაწყვეტილებები და ვაჭრობა

**ამ სესიაში გაკეთებული:**

1. **stdlib http.server > FastAPI** `scripts/perception_worker.py`-სთვის. რატომ: ერთი endpoint service (~80 LOC); FastAPI 30 MB depependency + version pinning headache იქნებოდა. Pareto choice.
2. **process_ledger ვრცელი run, არა targeted** — ლიმიტი=ცარიელი იყო, ანუ ყველა 302 ledger row-ი დაიფაროს. ცოცხალი counts საქმის შესასწავლად ღირდა იმაზე მეტი, ვიდრე targeted ექსპერიმენტი.
3. **OR-2 fallback შენარჩუნდა** — relevance scoring failure-ზე paper იწერება `NULL`-ით, ingest გრძელდება. 12 unscored row-ის არსებობა ცხადყოფს, რომ ფოლბექი მუშაობს (არ შეჩერდა pipeline).
4. **DAILY_BUDGET_USD=3.0 manual override** ღამის ციკლისთვის. user-მა plan mode-ში `B) ლოკალურად ღამით გავუშვა (~$2-3)` ავტორიზაცია გასცა; cap $12-ის ნაცვლად $3 დადგა, რომ overspend-ი ფიზიკურად შეუძლებელი ყოფილიყო.
5. **არ გავუშვი batch_ingest ამ სესიაში** — Cycle 1-ის მე-3 ნაბიჯი (Graphiti extraction ~$1-2) ვერ შევძელი context limit-ის გამო. ეს არ არის გადაწყვეტილება — ეს არის *მაგვარი*.

**უარყოფილი ალტერნატივები (შემდეგი სესია არ უნდა გადახედოს):**

- ❌ **FastAPI** perception_worker-სთვის — ერთი endpoint, stdlib საკმარისია.
- ❌ **დამატებითი `daily_budget_log` table** — QB-2: n8n + Python ერთსა და იმავე `runs.token_cost`-ს კითხულობს; two ledgers would drift.
- ❌ **Hypothesis-ის auto-promote** Phase 2.5-ში — manual flip 2.5D-ში (user-locked).
- ❌ **Vercel password protection** — Hobby tier-ში არ აქვს; Cloudflare Access (free) უნდა იყოს 2.5C-ში.
- ❌ **Episodic 47/30 "Graphiti quirk fix"** — REJECTED, ეს არის `EPISODE_CHAR_THRESHOLD=8000`-ის სეგმენტაცია (პასუხი 2.5D audit addendum-ში).
- ❌ **6-MCP drug repurposing in 2.5** — DEFERRED 2.6-მდე (user-locked AskUserQuestion).

**შუა-სესიის აღმოჩენილი შეზღუდვები:**

- PostgREST `gte.now-7d` shorthand-ს ვერ უწევს parse. გამოყენებული iso-string timedelta (`_iso_ago(days, hours)` helper `verify_phase2_5.py`-ში).
- `evidence_ledger`-ის ცხრილს column-ი ჰქვია `ingested_at`, არა `created_at` (HR-მაგვარი mistake; corrected at audit time).
- ruff-format pre-commit hook ავტო-fix-ს ახდენს ruff-check pass-ის შემდეგ — პირველი commit ხშირად ფერხდება; re-stage + re-commit.
- harness რომელიც `sleep` loop-ით pollings-ს უკრძალავს — background task notifications-ი იყენე, არ poll.

---

## 5. ვცადე და ჩავარდა

| რა ვცადე | რატომ ვერ გამოვიდა | ზუსტი შეცდომა/სიმპტომი |
|---|---|---|
| `Get-Content` Bash tool-ში | Bash = POSIX; `Get-Content` PowerShell-ის cmdlet-ია | `/usr/bin/bash: line 1: Get-Content: command not found` |
| `Copy-Item ... ; Get-ChildItem` Bash tool-ში | იგივე — Bash ≠ PowerShell | `Copy-Item: command not found` |
| PowerShell tool `$ts = Get-Date ...; Copy-Item ...` ერთ ხაზში | PowerShell tool exit 1-ით ჩავარდა გაუგებარი მიზეზით (output ცარიელი) | `Exit code 1`, ცარიელი output. Workaround: bash + `mkdir -p .handoffs && cp ...` |
| process_ledger output-ში "errors" pattern grep-ი | output ფაილში traceback-ი არ ჩაიწერა — მხოლოდ pipeline summary-ი | მხოლოდ summary-ის ხაზები `relevance_failed`, `errors` შემოვიდა; სტეკი არ მოიძებნა — შესაძლოა `_supabase_insert` ერორებს მუნჯად ყლაპავს |
| sleep+wc+tail loop background task-ის გადასამოწმებლად | harness-მა დაბლოკა "Long leading sleep commands are blocked" | "use Monitor with an until-loop" — გადავედი passive wait-ზე |
| FastAPI import smoke 2.5B-ის დასაწყისში (პრე-context-compaction) | FastAPI პროექტში არ იყო installed | switched to stdlib http.server (better Pareto regardless) |
| Override DAILY_BUDGET_USD env-ით per-script | perception_worker.py explicit `threshold_usd=12.0` argument გადასცემს, რაც env-ს გადაფარავს | precedence order is **caller arg > env > default**; ეს არის სასურველი ქცევა HC-2-სთვის (hard cap არ უნდა იყოს env-ის გადასაფარი) |

---

## 6. გარემო და ხელსაწყოების სახელმწიფო

**MCP სერვერები გამოყენებაში:**
- ⚠️ `claude.ai Context7` / `mcp__context7__*` — ხელმისაწვდომი, ამ სესიაში არ გამოვიყენე
- ⚠️ `claude.ai PubMed`, `claude.ai Open_Targets`, `mcp__qdrant__*`, `mcp__code-review-graph__*` — ხელმისაწვდომი, არ გამოვიყენე
- 🟢 ლოკალური MCP servers: `mcp/panic_stop.py` (FastMCP kill-switch), `mcp/hello_brain.py` — uncalled

**უნარები ამ სესიაში:**
- `claude-mem` (Session memory injection) — pending second session
- TodoWrite — გამოვიყენე ციკლის სათარჯიმნოდ (ჯერჯერობით stale, განახლება საჭიროა)

**ქვე-აგენტები გაფანტული:** არც ერთი ამ სესიაში.

**Hooks მოდიფიცირებული ქცევა:**
- `SessionStart:compact` hook აქტიური (suppressOutput true).
- ruff-format pre-commit hook ფერხდება — workaround: re-stage + re-commit.

**Env vars შემდეგი სესიისთვის (მხოლოდ სახელები):**
```
ANTHROPIC_API_KEY                 (loaded from .env)
SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_DB_URL
NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
QDRANT_URL
NCBI_EMAIL
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
DAILY_BUDGET_USD          (optional; default 1.50; ბოლო სესიაში manual=3.0)
PERCEPTION_WORKER_URL     (გასაყენებელია Railway deploy-ის შემდეგ)
CF_ACCESS_AUD             (გასაყენებელია 2.5C-ში)
```

**ღია dev servers / დამკვირვებლები / გვირაბები:** არცერთი. (perception_worker.py ლოკალურად არ მუშაობს ფონზე.)

**ფონის task-ის arch:** background task `bcx6qqmt0` დასრულდა exit 0; output ფაილი:
`C:\Users\jinch\AppData\Local\Temp\claude\c--Users-jinch-OneDrive--------------aleksandra-brane\860213fd-9256-49a2-b151-d3a67febf1f9\tasks\bcx6qqmt0.output` (40 lines)

---

## 7. ღია შეკითხვები

**ეს უნდა ჰკითხო user-ს pipe-ის გაშვებამდე:**

1. **Cycle 1-ის ბოლო ნაბიჯი (batch_ingest) დაუყოვნებლივ უნდა შესრულდეს თუ ჯერ Gate B verify გავუშვათ chunks-only კონფიგურაციაში?** — batch_ingest ~$1-2 დაჯდება; ეს გაიყვანს Graphiti entities 200→500-მდე (B.4).
2. **Cycle 2-ის გაშვება ღირს კი?** — ბიუჯეტი დარჩა $2.78 (cap $3); chunks 4176→5000+-მდე გასაყვანად, ალბათ მხოლოდ targeted re-chunking საჭიროა; ahcual perception_tick-მა მსოფლიო პრობლემა ვერ აღმოაჩინა — ცარიელია წყაროებში.
3. **`process_ledger` summary counter bug-ი (chunks_inserted=0 vs DB delta +3767)** root cause-ის გამოკვლევას ღირს, თუ Cycle 2-მდე ცოცხალი DB-ის ნდობა საკმარისია?

**გამოკვლევა საჭიროა:**

- Qdrant `papers` collection-ის live count (B.3-ის მე-2 ნახევრისთვის).
- Neo4j `MATCH (e:Entity {group_id:'hie_research'}) RETURN count(e)` (B.4-ის baseline-სთვის batch_ingest-ის წინ).
- 12 unscored paper-ის ID-ები: დააფასე ან abstract არ აქვთ, ან Haiku ჩავარდა (relevance_failed=0 ცხადყოფს, რომ ჩავარდნა არ მომხდარა; სავარაუდოდ abstract არ აქვს — `relevance_skipped_no_text=0` თუმცა საწინააღმდეგოს ამბობს. **diagnostic გასარკვევია**).

**გამოთქმული ვარაუდები, რომლებიც უნდა იყოს ვალიდირებული:**

- 269 `errors` chunking pipeline-ში არ-ფატალური ვარაუდი (exit 0 აქცია მართებული) — შემდეგ სესიამ უნდა გადახედოს დეტალური log-ი.
- chunks_inserted summary counter `0` არის bug, არა truth — DB delta +3767 chunk-ი არის ground truth.
- Cycle 1-ის $0.217 spend მართებულად რეგისტრირდა `runs.token_cost`-ში (236 calls × ~$0.0009 average = მართებული Haiku-ის pricing-ით).

---

## 8. შემდეგი ნაბიჯი (ერთიანი, ბეტონი, დარბილებადი)

**ზუსტი შემდეგი მოქმედებათა თანმიმდევრობა (10 წუთის სამუშაო ციკლი):**

```powershell
# 1. Pre-flight (1 წუთი)
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2 --gate all   # უნდა იყოს 19/19
docker ps --filter name=aleksandra                                       # Neo4j + Qdrant ცოცხალი

# 2. Live state snapshot (30 წამი) — ცოცხალი DB და დარჩენილი ბიუჯეტი
.venv/Scripts/python.exe -X utf8 -c "
import psycopg2, os
from scripts.ledger import load_env
load_env()
c = psycopg2.connect(os.environ['SUPABASE_DB_URL'], sslmode='require').cursor()
c.execute('SELECT COUNT(*) FROM evidence_ledger'); print('ledger:', c.fetchone()[0])
c.execute('SELECT COUNT(*) FROM papers'); print('papers:', c.fetchone()[0])
c.execute('SELECT COUNT(*) FROM paper_chunks'); print('chunks:', c.fetchone()[0])
c.execute(\"SELECT COALESCE(SUM(token_cost),0) FROM runs WHERE start_time >= current_date AT TIME ZONE 'UTC'\"); print('today:', c.fetchone()[0])
"
# მოლოდინი: ledger=302, papers=245, chunks=4176, today=~0.22 USD

# 3. Cycle 1-ის მე-3 ნაბიჯი: batch_ingest 50-ზე (5-15 წუთი, ~$1-2)
$env:DAILY_BUDGET_USD = "3.0"
.venv/Scripts/python.exe -X utf8 -m scripts.extraction.batch_ingest --limit 50

# 4. Gate B verify (30 წამი)
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2_5 --gate b

# 5. Commit Cycle 1 progress (1 წუთი)
git add -- scripts/ docs/PHASE_2_LIVE_AUDIT.md handoff.md .handoffs/
git commit -m "feat(phase-2.5B): Cycle 1 overnight — ledger 45→302, papers 33→245, chunks 409→4176"
```

**მოსალოდნელი შედეგი:**
- Cycle 1 დასრულდება: B.2 ✅ EXCEED, B.3 likely ⚠️ (4176/5000 = 83.5%; batch_ingest can push 4500+), B.4 ✅ (50 papers × ~10 entities = 500+).
- დღევანდელი ბიუჯეტი: $0.22 + ~$1.5 = ~$1.7 (≈ 57% of $3 cap).
- შემდეგი commit: `feat(phase-2.5B): Cycle 1 ...`

**როგორ გადაამოწმოთ წარმატება:**
- `verify_phase2_5 --gate b` უნდა აჩვენოს ≥ 3/4 PASS (B.1 user-side deploy-ის გარეშე ვერ გავა, ეს ცნობილია).
- `git log --oneline -1` უნდა აჩვენოს ახალი commit SHA Cycle 1-ის უსასყიდლოდ.
- `psycopg2` count-ი chunks ≥ 4176-დან გადახტომა (თუნდაც ცოტა, batch_ingest ხან მცირე chunking-საც აკეთებს).
- `runs WHERE kind='llm_call' AND start_time >= current_date AT TIME ZONE 'UTC'` count უნდა გაიზარდოს ~236 → ~280-300 (Haiku per-entity extraction calls).

---

## 9. დადასტურების ბრძანებები

**შემდეგი სესია უნდა გაუშვას ეს ბრძანებები პირველი 5 წუთის განმავლობაში, რომ დაადასტუროს, რომ ზემოთ აღწერილი შტატი ჯერ კიდევ ზუსტია:**

```powershell
# A. რეპოს ბაზური მდგომარეობა
git log --oneline -5
# მოლოდინი: HEAD = 1c6632d (იხილოს section 2-ის HEAD)

git status --short
# მოლოდინი: ?? docs/PHASE_2_LIVE_AUDIT.md, ?? handoff.md, ?? .handoffs/handoff-2026-05-15-night.md

# B. Phase 2 regression
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2 --gate all
# მოლოდინი: 19/19 PASS (Phase 2 უცვლელია)

# C. Phase 1 regression (5 წამი)
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase1
# მოლოდინი: 10/10 PASS

# D. Lint
.venv/Scripts/python.exe -X utf8 -m ruff check scripts/ agents/
# მოლოდინი: clean

# E. Model deprecation watch (OR-6)
.venv/Scripts/python.exe -X utf8 -c "import subprocess; r = subprocess.run(['grep','-rn','claude-sonnet-4-20250514','scripts/','agents/','viewer/'], capture_output=True, text=True); print('matches:', r.stdout or 'NONE')"
# მოლოდინი: NONE (Sonnet 4 retires 2026-06-15; ჩვენ -4-5-ზე ვართ)

# F. Wrapper exclusivity (HC-4)
.venv/Scripts/python.exe -X utf8 -c "import subprocess; r = subprocess.run(['grep','-rn','anthropic.Anthropic(','scripts/','agents/'], capture_output=True, text=True); print(r.stdout)"
# მოლოდინი: მხოლოდ ერთი match — scripts/cognition/llm.py:~190 (canonical wrapper)

# G. Live DB sanity (Cycle 1 ground truth)
.venv/Scripts/python.exe -X utf8 -c "
import psycopg2, os
from scripts.ledger import load_env
load_env()
c = psycopg2.connect(os.environ['SUPABASE_DB_URL'], sslmode='require').cursor()
for q, label in [
    ('SELECT COUNT(*) FROM evidence_ledger', 'ledger (expect ≥302)'),
    ('SELECT COUNT(*) FROM papers', 'papers (expect ≥245)'),
    ('SELECT COUNT(*) FROM papers WHERE relevance_score IS NOT NULL', 'scored (expect ≥233)'),
    ('SELECT COUNT(*) FROM paper_chunks', 'chunks (expect ≥4176)'),
    ('SELECT COUNT(*) FROM hypotheses', 'hypotheses (expect 10)'),
]:
    c.execute(q); print(f'{label:40s} = {c.fetchone()[0]}')
"

# H. ბიუჯეტი
.venv/Scripts/python.exe -X utf8 -c "from scripts.cognition.budget import check_daily_budget; t, o = check_daily_budget(threshold_usd=12.0); print(f'today: \${t:.6f}, over_cap: {o}')"
# მოლოდინი: today ≈ $0.22 (Cycle 1 mid-state), over_cap=False
```

**თუ A-H-დან რომელიმე ჩავარდა → STOP, RCA via 5-why, შესთავაზე user-ს 2-3 fix option, არ აეცი ახალი ნაბიჯი regression-ის ზემოდან.**

---

## დანართი: HC/QB/OR სწრაფი reminder

- **HC-1:** strict sequence A→B→C→D, no reorder.
- **HC-2:** $12 hard cap; $10 soft warn. ღამის ციკლისთვის manual=3.0.
- **HC-4:** ყველა LLM call უნდა გავიდეს `call_claude` ან `make_instrumented_async_anthropic`-ით.
- **HC-6:** No Phase 3/4 creep (Communicator, PDF Weekly Brief, Ask BRAIN, 3D viewer).
- **QB-1:** დასასრულს Anthropic console ↔ `SUM(runs.token_cost)` ± 5%.
- **QB-3:** service-role key არასოდეს client bundle-ში (2.5C-ისთვის).
- **QB-4:** DSPy training file-first compensating-action (2.5D-ისთვის).
- **OR-1:** n8n workflows queue mode (executionOrder: 'v1') — გათვალისწინებულია JSON-ში.
- **OR-2:** relevance_score Haiku failure → NULL + log; ingest grow.
- **OR-6:** Sonnet 4 retires 2026-06-15; ჩვენ `claude-sonnet-4-5` და `claude-haiku-4-5-20251001` ვიყენებთ.
- **Hard Stop 6:** Shako sends `/stop` in Telegram → halt everything (FND-03; `mcp/panic_stop.py`).

---

*ფაზა 2.5B Cycle 1 = ledger 6.7×, papers 7.4×, chunks 10.2× ერთ ღამეში $0.22-ში.*
*დარჩა: batch_ingest 50-ზე → Gate B verify → commit → Cycle 2 ან 2.5C entry.*
