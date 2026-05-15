# Phase 1 Exit Report

> ფაზის გასაშვები ანგარიში. ROADMAP-ის Phase-1-exit gate-ი მოითხოვს, რომ ეს ფაილი
> ხელით შევსებული იყოს სანამ Phase 2 დაიწყება. ცარიელი ფაილი = ფაზა დახურული არ არის.

---

## სათაური ინფორმაცია

| ველი | მნიშვნელობა |
|------|-------------|
| ფაზის სტატუსი | **closed (10/10 PASS)** |
| Phase 1 PRC items | 7/7 (PRC-01 … PRC-07) — ცოცხალი მტკიცებულებით |
| Acceptance drill | 2026-05-15 01:36 UTC, perception_tick --small --no-telegram |
| Drill დროის ხანგრძლივობა | 39 წამი |
| Drill outcome | +30 row from empty ledger, 5 distinct sources |
| Git commits | 25b5a8f, c4d3f1d, bff3294, 25e45cb, 2397297, 6dd810d, 839ff64, f84746e, 7e1c6d8 |
| Supabase ცხრილები (ახალი) | evidence_ledger (003), kv_state (004) |
| R2 prefixes (ცოცხალი) | pubmed/, ctgov/, biorxiv/, medrxiv/, crawl4ai/, negative/ |
| n8n workflow | workflows/perception_6h.json (template, inactive) |
| Ledger snapshot | 30 row · 5 source_types · 6 mode='negative' · 40 R2 artifacts |

---

## 1. PRC-01 … PRC-07 — თითო ერთი ხაზი ცოცხალი მტკიცებულებით

| # | PRC | სტატუსი | მტკიცებულება |
|---|-----|---------|--------------|
| 01 | PubMed E-utilities (api_key + mailto + tool) | ✅ | [scripts/fetch_pubmed.py](../scripts/fetch_pubmed.py) — `Entrez.email = NCBI_EMAIL`, `Entrez.tool = aleksandra_brain`, `Entrez.api_key = NCBI_API_KEY` (optional, warn-only); drill produced 9 ledger rows from 20-query Aleksandra facet |
| 02 | ClinicalTrials.gov v2 REST | ✅ | [scripts/fetch_ctgov.py](../scripts/fetch_ctgov.py) — 5-facet query set against `clinicaltrials.gov/api/v2/studies` with `filter.overallStatus=RECRUITING,…`; drill produced 6 trial rows |
| 03 | bioRxiv + medRxiv RSS | ✅ | [scripts/fetch_preprints.py](../scripts/fetch_preprints.py) — `connect.biorxiv.org/biorxiv_xml.php?subject=neuroscience` + `connect.medrxiv.org/medrxiv_xml.php?subject=Pediatrics`; drill produced 6 preprint rows |
| 04 | Crawl4AI fills coverage gaps; payloads written to R2 by content-hash | ✅ | [scripts/gap_filler.py](../scripts/gap_filler.py) — single asyncio context, AsyncWebCrawler arun per candidate, R2 key = `crawl4ai/<sha256[:24]>.md`; drill produced 3 crawl4ai full-text rows |
| 05 | Firecrawl only when Crawl4AI fails 2× AND monthly spend < $10 | ✅ | [scripts/gap_filler.py](../scripts/gap_filler.py) — `_bump_fail` + `_firecrawl_under_cap` gates; spend tracked in `kv_state.firecrawl_spend:<YYYY-MM>`; drill spend = $0.00 (gates didn't trip) |
| 06 | Negative-evidence branch (mode='negative') | ✅ | [scripts/fetch_negative.py](../scripts/fetch_negative.py) — therapies-table-driven negation queries (`<seed> "no effect"`, `null result`, retracted-pub filter); drill produced 6 negative rows incl. 2 real retracted publications |
| 07 | Provenance ledger row per ingestion (5 fields) | ✅ | [scripts/migrations/003_evidence_ledger.sql](../scripts/migrations/003_evidence_ledger.sql) + [scripts/ledger.py](../scripts/ledger.py) `insert_ledger_row()` — every row carries source_id, retrieval_method, retrieval_timestamp, content_hash, raw_artifact_url; verify_phase1 criterion 3 confirms `null_rows=0` across all 30 |

**ჯამში: 7 / 7** ✅

---

## 2. ფაზის გასაშვები ცდა (perception_tick drill)

```text
$ TRUNCATE evidence_ledger; DELETE FROM kv_state WHERE key LIKE 'crawl_fail:%' OR key LIKE 'firecrawl_spend:%';
After TRUNCATE: 0 rows

$ .venv/Scripts/python.exe -m scripts.perception_tick --small --no-telegram
perception_tick start: 2026-05-15T01:35:44Z

=== PubMed (PRC-01) ===
  query: hypoxic ischemic encephalopathy treatment  found=3 new=3
  query: neonatal brain injury therapy              found=3 new=3
  query: infantile spasms novel treatment           found=3 new=3
PubMed: queries_run=3 pmids_found=9 new_pmids=9 ledger_inserted=9

=== ClinicalTrials.gov (PRC-02) ===
  query: cond=Hypoxic Ischemic Encephalopathy  found=3 new=3
  query: cond=Infantile Spasms                 found=3 new=3
ClinicalTrials.gov: studies_found=6 new_studies=6 ledger_inserted=6

=== bioRxiv + medRxiv RSS (PRC-03) ===
  feed: bioRxiv neuroscience subject feed   entries=3 new=3
  feed: medRxiv Pediatrics subject feed     entries=3 new=3
Preprints: feeds_run=2 entries_seen=6 new_entries=6 ledger_inserted=6

=== Crawl4AI gap-fill (PRC-04+05) ===
  [ok crawl4ai] medrxiv/10.64898/2026.04.30.26352183v1  -> s3://aleksandra-brain-storage/crawl4ai/...
  [ok crawl4ai] medrxiv/10.64898/2026.05.01.26352206v1  -> s3://aleksandra-brain-storage/crawl4ai/...
  [ok crawl4ai] medrxiv/10.64898/2026.05.06.26352605v1  -> s3://aleksandra-brain-storage/crawl4ai/...
Gap-filler: candidates=3 crawl4ai_success=3 ledger_inserted=3

=== Negative-evidence branch (PRC-06) ===
  built 12 negative queries (Keppra/levetiracetam + Vigabatrin/Sabril seeds)
  Keppra "no effect"                          found=2 new=2
  levetiracetam[ti] AND "Retracted Publication"[ptyp]  found=2 new=2
  Vigabatrin "no effect"                      found=2 new=2
Negative: pmids_found=10 new_pmids=6 ledger_inserted=6

────────────────────────────────────────────────────────────
🕷️ perception_tick OK  +30 rows in 39s
  pubmed=9  ctgov=6  preprints=6
  gap-fill=3  negative=6
runs row id: 58953cd1-eeab-4ad3-b194-31c3bb7d8942
────────────────────────────────────────────────────────────
```

შემაჯამებელი:
- ცარიელი → 30 row 39 წამში
- 5 distinct source_type: pubmed, ctgov, biorxiv, medrxiv, crawl4ai
- 6 negative-branch row (PRC-06)
- 0 ცდისპირული ცარიელი provenance ველი
- 1 runs row inserted exit_status='completed' kind='perception_tick'

---

## 3. verify_phase1.py — 10/10 PASS

```text
$ .venv/Scripts/python.exe -m scripts.verify_phase1
Phase 1 exit-gate verification
============================================================
  [PASS] 1. ledger rows >= 20                          actual=30
  [PASS] 2. distinct source_types >= 3                 actual=5 (biorxiv,crawl4ai,ctgov,medrxiv,pubmed)
  [PASS] 3. all 5 provenance fields non-null           null_rows=0
  [PASS] 4. >= 1 mode='negative' row                   negative_rows=6
  [PASS] 5. R2 artifact count >= ledger rows           R2=40  ledger=30
  [PASS] 6. content_hash integrity (sample 3)          3/3 match
  [PASS] 7. NCBI compliance (email+tool, key optional) email=set  tool=aleksandra_brain
  [PASS] 8. firecrawl spend < cap                      spend=$0.00  cap=$10.00  calls=0
  [PASS] 9. workflows/perception_6h.json present       path=workflows/perception_6h.json
  [PASS] 10. Phase 0 fetch-lint regression             violations=0
============================================================
RESULT: 10/10 PASS
```

---

## 4. რა გადადო ფაზა 2-სთვის (deferred)

| # | რა | რატომ deferred | Phase |
|---|-----|----------------|-------|
| 1 | RAGFlow PDF→chunks→entities pipeline | Phase 1 = pure perception (no reasoning, no chunking). Chunking is the entry point of the Memory layer. | 2 |
| 2 | Qdrant embedding upserts per ledger row | Same — Memory layer responsibility. | 2 |
| 3 | Neo4j Graphiti entity extraction (Drug, Gene, Pathway) | Same. | 2 |
| 4 | LightRAG unified graph+vector retrieval | Same. | 2 |
| 5 | Spider/Analyzer/Hypothesis CrewAI agent reasoning | Phase 1 stays mechanical. Spider agent skeleton wires up in Phase 5 when the agent loop actually runs. | 5 |
| 6 | mem0 cross-agent memory (Spider ↔ Analyzer) | No agents are reasoning yet. | 3 |
| 7 | NCBI_API_KEY (currently empty → 3 req/sec) | Functional with anon rate; user registers when comfortable. fetch_pubmed warns visibly each run. | non-blocking |
| 8 | Railway Python worker exposing `/perception-tick` | Phase 1 acceptance ran local. Workflow JSON is template-ready. | mini-phase 1.1 |
| 9 | n8n activating workflows/perception_6h.json | Needs worker URL above. | mini-phase 1.1 |
| 10 | Dashboard "Recent Discoveries" card | Frontend = Phase 4. | 4 |
| 11 | Telegram URGENT/IMPORTANT/WEEKLY alert routing | Analyzer-driven; Phase 3+. | 3 |
| 12 | Hindsight self-learning relevance scoring | Needs months of usage signal. | 3+ |
| 13 | bioRxiv search-feed (HIE-targeted) | `biorxiv.org/search/<q>/feedformat:rss` returns malformed XML via feedparser; subject feed already covers most cases. | optional |
| 14 | Cloudflare KV for crawl_fail / firecrawl_spend | KV REST API needs a separate API token we don't have. Supabase `kv_state` table fills the same role for our 4/day cron volume. | optional |

---

## 5. Phase 1 budget posture

| ხაზი | რეალური ხარჯი | ბუჯეტი |
|------|---------------|--------|
| NCBI E-utilities | $0 | $0 |
| ClinicalTrials.gov v2 | $0 | $0 |
| bioRxiv / medRxiv RSS | $0 | $0 |
| Crawl4AI (ლოკალური) | $0 | $0 |
| Firecrawl | $0 (cap $10/თვე) | $10/თვე max |
| Supabase Free tier | $0 | $0 |
| Cloudflare R2 (40 artifacts, ~5 MB) | $0 | $0 (10GB free) |
| n8n Railway (already running) | $5/თვე | $5/თვე |
| Anthropic API (Phase 1 makes 0 calls) | $0 | $0 |
| **ჯამი** | **$5/თვე** | **$15–26/თვე ბუჯეტი** |

ფაზა 1 ბუჯეტს ერთხელაც არ ეხება.

---

## 6. Phase 0 regression — ცოცხალია

- FND-01 (MRI-leak lint): ESLint + verify_phase1 fetch-lint reimpl → violations=0 ✅
- FND-02 (trust boundary): pre-commit hook + GitHub Actions trust-boundary.yml — passed on every Phase 1 commit
- FND-03 (Telegram kill-switch): not re-exercised in Phase 1 (deferred to Phase 5 when agents loop); pattern preserved in perception_tick `_budget_locked` pre-flight
- FND-04 (daily budget gate): `_budget_locked()` queries `runs WHERE kind=budget_lock AND start_time >= midnight_UTC` — drill confirmed pre-flight works (Phase 0 fire-drill lock from 2026-05-14 18:39 was correctly NOT counted after UTC midnight rollover)
- FND-05 (RLS service-role write): evidence_ledger and kv_state both inherit the pattern
- Append-only `runs`: perception_tick writes one row at completion (not UPDATE) — confirmed in drill (id 58953cd1)
- Secret scan / gitleaks: passed on every Phase 1 commit
- ruff + ruff-format: passed on every Phase 1 commit

---

## 7. შემდეგი ნაბიჯი

- Phase 2 (Memory): RAGFlow chunking + Qdrant embeddings + Graphiti entity extraction
- mini-phase 1.1 (optional): Railway Python worker deploy, n8n activates the 6h cron
- Operational hygiene: register NCBI_API_KEY (10 req/sec instead of 3)

ფაზა 1 დახურულია 2026-05-15 01:36 UTC. ფაზა 2 ღიად.
