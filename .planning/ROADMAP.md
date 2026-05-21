# Roadmap: ALEKSANDRA_BRAIN

## Overview

ALEKSANDRA_BRAIN ships in five sequential v1 phases that move from a hardened, cost-gated foundation to a confidence-gated digest the family can act on. Phase 0 establishes the trust boundary (privacy import-lint, RLS, kill-switch, spend cap, MCP allowlist, secrets vault, run ledger). Phase 1 turns on continuous ingestion from PubMed E-utilities, ClinicalTrials.gov v2, bioRxiv/medRxiv RSS, with Crawl4AI for the gaps and Firecrawl as a budget-gated fallback. Phase 2 makes provenance load-bearing: a citation tuple becomes a first-class type, a single-writer ledger atomically fans out to Graphiti and Qdrant, and LightRAG becomes the only retrieval surface agents are allowed to call. Phase 3 stands up the minimum cognition path — a deterministic verifier that round-trips every PMID/DOI/NCT/URL, an Analyzer that extracts PICO + evidence-grade under the provenance contract, and a Communicator that drafts under a fixed schema with an imperative-verb lint, a six-tier evidence ranking, and a HIGH-only confidence gate. Phase 4 closes the loop by delivering one credible lead to the family inside a 14-day window via confidence-gated Telegram pushes, a weekly Gmail digest, Notion archival, and a clinician-shareable PDF that embeds full provenance — under a $30 total-cost ceiling. v2 phases (Cognition-full, Action interactivity, Visualization viewer/segmentation/simulation, HIPAA posture) live in REQUIREMENTS.md and are explicitly out of v1 scope.

Current execution state as of 2026-05-16: Phase 0, Phase 1, Phase 2, and the inserted Phase 2.5 Quick Wins sprint are closed. Phase 3 Cognition Minimum is the active next phase. The only live operational caveat is the n8n `daily-budget-gate` JSON-body expression bug, which is being fixed outside this documentation pass; Phase 2.5A code/data spend instrumentation is green.

## Phases

**Phase Numbering:**
- Integer phases (0, 1, 2, 3, 4): Planned milestone work
- Decimal phases (2.1, 2.2, 2.5): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 0: Foundation** - Trust boundary, cost gates, kill-switch, MCP allowlist, run ledger
- [x] **Phase 1: Perception** - Continuous, provenance-stamped literature ingest on a 6-hour cron
- [x] **Phase 2: Memory** - Citation-tuple-first ledger, Graphiti+Qdrant memory, single retrieval surface
- [x] **Phase 2.5: Quick Wins (INSERTED)** - Spend instrumentation, perception scale-up, family-visible layer, validation workflow
- [x] **Phase 3: Cognition (minimum)** - Verifier-gated Communicator drafting (11/11 PASS; Day 7 closure unblocked same day by Shako's ChatGPT-assisted prereq work)
- [x] **Phase 4: First Family Value** - Engineering sprint closed 2026-05-17, `verify_phase4 --mode code-complete` 9/9 PASS. Step B operator activation (Notion bootstrap + n8n workflow imports) + 14-day acceptance window open at first Weekly Brief Sunday 2026-05-24 09:00 ET. See `docs/PHASE_4_EXIT_REPORT.md` + `docs/PHASE_4_OPERATOR_RUNBOOK.md`.
- [x] **Phase 5: BRAIN AI Manager Assistant** - Engineering sprint closed 2026-05-18, `verify_phase5 --mode code-complete` 13/13 PASS · ALL GREEN. 5 capabilities live: Smart Drop Zone (PDF/photo/voice/email/text intake), Persistent Activity Log, Morning Briefing (Sun 09:00 ET), Voice-First Input (OpenAI Whisper), Email Drafting (Gmail compose-only). Migration 011 applied (manager_actions + intake_drops + RLS + PHI CHECK). 78/78 cumulative verifier coverage. Phase 5 LLM spend $0 / $15 cap. See `docs/PHASE_5_EXIT_REPORT.md` + `docs/PHASE_5_COMPLETION_KA.md` + `docs/PHASE_5_OPERATOR_RUNBOOK.md`.
- [ ] **Phase 6: Bilingual System (i18n)** - Full English+Georgian bilingualism: 7 family-facing routes under `/en/*` and `/ka/*`, 4 dynamic-content tables converted to JSONB en+ka via migration 012, Communicator + Phase 5 composer emit `{en, ka}` pairs via Anthropic strict tool_use, Telegram→ka / Gmail→en audience routing in Python worker layer. 15 plans across 6 wave-groups (0/1/2/3a/3b/4) — post plan-checker iteration 1. Seed: docs/I18N_PLAN.md.

## Phase Details

### Phase 0: Foundation
**Goal**: By the end of this phase, the family has a repo that cannot accidentally leak MRI data, cannot accidentally burn the monthly budget, and can be stopped from a phone — even before a single paper is ingested.
**Depends on**: Nothing (first phase)
**Requirements**: FND-01, FND-02, FND-03, FND-04, FND-05, FND-06, FND-07, OBS-01
**Success Criteria** (what must be TRUE):
  1. A test pull request that imports a `viewer/` client-side imaging module from a server route is automatically rejected by CI, and a test commit that adds a remote `fetch`/`axios.post`/`XMLHttpRequest` call from `viewer/` is automatically rejected — visible as a red check in the PR UI.
  2. Sending `/stop` to the family Telegram bot causes every running agent to stop and the next scheduled cron tick to be cancelled within 60 seconds, observable from the Telegram acknowledgement message.
  3. Once the day's billed Anthropic spend crosses $1.50, the family sees the n8n daily-spend gate flip to red and downstream Anthropic-calling nodes stop firing for the rest of that day.
  4. A second (non-family) Supabase identity attempting to read any row containing patient data is denied by row-level security, observable from the Supabase logs.
  5. An agent attempting to call an MCP server that is not listed for it in `MCP-INVENTORY.csv` fails closed, and a commit that adds a high-entropy secret to a tracked file is rejected by CI.
**Plans**: TBD

**Phase-exit gate (CATASTROPHIC):** MRI-leak countermeasure (import-lint half — FND-01 + FND-02) must be green on `main` before Phase 1 starts. The viewer half of the MRI-leak pitfall is v2 (VIS-*) and not in scope here.
**Phase-exit gate (HIGH):** Cost-runaway countermeasure (FND-03 kill-switch + FND-04 spend cap) must be exercised at least once in a simulated runaway and observed to halt within 60 seconds before Phase 1 starts.

### Phase 1: Perception
**Goal**: By the end of this phase, every six hours the family's Supabase ledger gains new rows from PubMed, ClinicalTrials.gov, and the preprint servers — each with a verifiable source identifier, a retrieval method, a content hash, and an R2 link to the raw artifact.
**Depends on**: Phase 0 (kill-switch, spend cap, run ledger, MCP allowlist, RLS schema)
**Requirements**: PRC-01, PRC-02, PRC-03, PRC-04, PRC-05, PRC-06, PRC-07
**Success Criteria** (what must be TRUE):
  1. A family member can open the Supabase `ledger` table at any time and see new rows from the last 6-hour cron tick across PubMed, ClinicalTrials.gov, and bioRxiv/medRxiv, each carrying `{source_id, retrieval_method, retrieval_timestamp, content_hash, raw_artifact_url}`.
  2. PubMed pulls are visibly identified to NCBI with the project user-agent + mailto + registered `api_key` (verifiable from the request log), so the family will not be IP-blocked.
  3. When the index API does not return full text, Crawl4AI fills the gap and writes the raw payload to Cloudflare R2 under a content-hash key — observable as a present R2 object whose URL appears in the ledger row.
  4. A Firecrawl call only ever appears in the run log after Crawl4AI failed twice on the same URL and only while monthly Firecrawl spend is under $10; the family can see this rule enforced from the run log.
  5. The same cron tick also produces ledger rows tagged `mode=negative` (null/no-effect/retracted results) for currently-tracked candidates, so the family sees counter-evidence alongside positive evidence.

### Phase 2: Memory
**Goal**: By the end of this phase, the system cannot record a claim that lacks a citation tuple, cannot store a graph fact without naming its sources, and cannot present a paper to an agent except through one retrieval call — so by construction no agent can see ungrounded evidence.
**Depends on**: Phase 1 (ledger schema and at least 100 ingested papers to smoke-test recall)
**Requirements**: MEM-01, MEM-02, MEM-03, MEM-04, MEM-05, MEM-06, MEM-07, MEM-08
**Success Criteria** (what must be TRUE):
  1. A clinician auditing any single claim in the system can click from the claim to a populated citation tuple `{source_id, retrieval_method, retrieval_timestamp, confidence, verbatim_grounding, byte_offset}` — and a test write that omits any field is rejected with a visible error.
  2. After ingesting a batch, a deliberately injected mid-batch failure leaves both Graphiti and Qdrant unchanged (rollback observable from the ledger run log), confirming the single-writer atomic fan-out.
  3. An agent that tries to call Graphiti or Qdrant directly fails its lint check at commit time; the only retrieval call permitted from agent code is `retrieve(query, t_at=...)`, observable from the lint report.
  4. A test ingest of 100 known papers followed by the query `"cord blood + HIE"` returns at least 90 of them in the top 100 results, and the morning after a daily reconciler run shows zero `graphiti↔qdrant` mismatches in the family's daily report.
  5. The graph ontology is captured in a checked-in `graph_ontology.yaml`; a write that uses an ad-hoc node label is rejected at write time and surfaces in the run log.

**Phase-exit gate (CATASTROPHIC, half-1 of fabricated-citations defense):** The citation tuple as a first-class type (MEM-01) and the `derived_from_source_ids[]` write contract (MEM-03) must be live before any cognitive agent runs in Phase 3 — i.e., the schema must make ungrounded claims structurally impossible before agents start drafting.

### Phase 2.5: Quick Wins (INSERTED)
**Goal**: Close the Phase 2 carry-forward surface before cognition work: harden spend instrumentation, scale perception/memory volume, add family-visible views, and hydrate validation data for Phase 3.
**Depends on**: Phase 2 (Memory)
**Requirements**: Verification gates A-D in `scripts.verify_phase2_5`
**Status**: Closed 2026-05-16, 16/16 PASS.
**Success Criteria** (what must be TRUE):
  1. Spend instrumentation stores precise `runs.token_cost`, `check_daily_budget()` reads that surface, and at least one positive-cost `llm_call` row exists.
  2. The memory corpus is scaled past the Phase 2 smoke-test size: ≥100 ledger rows, ≥5000 chunks and Qdrant vectors, and ≥500 Neo4j HIE entities.
  3. Family-visible dashboard and workflow fire surfaces exist and pass RLS smoke checks.
  4. Hypothesis validation has a browser route, ≥5 confirmed hypotheses, ≥10 DSPy JSONL examples, and ≥90% supporting-paper hydration.

**Operational caveat:** The code/data spend instrumentation gate is green, but the deployed n8n `daily-budget-gate` JSON-body expression bug is still being fixed. Do not treat workflow-written `budget_lock` rows as confirmed until that workflow fix is deployed and tested.

### Phase 3: Cognition (minimum)
**Goal**: By the end of this phase, the family has a draft digest in Notion every cron cycle that contains zero fabricated citations, zero direct instructions to the family, and only HIGH-confidence findings on top — staged but not yet pushed to Telegram.
**Depends on**: Phase 2.5 (Phase 1/2 regressions green, scaled corpus, validation examples, spend instrumentation)
**Requirements**: CGM-01, CGM-02, CGM-03, CGM-04, CGM-05, CGM-06, CGM-07, CGM-08, CGM-09, CGM-10
**Success Criteria** (what must be TRUE):
  1. The family can open the staged Notion draft and see that every PMID, DOI, NCT identifier, and URL has been round-tripped against its original index API — a synthetic-fabrication smoke test confirms the verifier rejects ≥99 of 100 planted fakes before publication.
  2. Every finding in a draft carries the fixed schema `{finding, source, evidence_strength, population_gap, clinician_question}` and the top section of every draft contains only tier-1 or tier-2 evidence — a tier-3-or-worse finding in the top section is rejected by the gate.
  3. A draft containing any of `should`, `must`, `consider`, `try`, `ask for`, `request` directed at the family is rejected by the imperative-verb lint before staging, and the `taxonomy/tone.yaml` post-processor strips or rewrites prognostic language — confirmed by an imperative-verb count of 0 across 30 sample digests.
  4. While the confidence gate is set to HIGH, any sub-HIGH draft is staged in Notion with an explicit missing-evidence reason — the family can see why it did not publish without reading the agent's chain of thought.
  5. A simulated runaway agent terminates within 60 seconds: each agent run hits `max_iter=7`, `max_execution_time=30s`, or `max_tokens_per_run=80,000`, the cause is logged, and a versioned Aleksandra patient-context document is recorded alongside the run.

**Phase-exit gate (CATASTROPHIC, half-2 of fabricated-citations defense):** The verifier agent (CGM-01) must reject ≥99% of 100 synthetic fabrications before the Communicator is allowed to produce any draft that will be staged.
**Phase-exit gate (CATASTROPHIC, off-label framing defense):** The imperative-verb lint (CGM-04) + six-tier evidence ranking (CGM-05) + tone post-processor (CGM-06) must all be live and produce an imperative-verb count of 0 across 30 sample digests before Phase 4 starts. One off-label suggestion before vigabatrin washout costs the Duke EAP window — this is not deferrable.

### Phase 4: First Family Value
**Goal**: By the end of this phase, within a 14-day observation window after launch, the family receives at least one digest that surfaces a credible treatment lead they would not have found via ChatGPT + Google Scholar in the same window, with full source provenance, at total cost under $30 — and Dr. Hien can be sent a PDF of it without redaction.
**Depends on**: Phase 3 (verifier-gated, confidence-gated drafts staged in Notion)
**Requirements**: ACD-01, ACD-02, ACD-03, ACD-04, ACD-05, OBS-02, OBS-03
**Success Criteria** (what must be TRUE):
  1. Within a 14-day window after this phase ships, the family receives at least one Telegram digest containing a credible treatment lead they would not have found via ChatGPT + Google Scholar over the same window, with full source provenance, at total cost under $30 — the v1 acceptance test.
  2. The family sees a single Telegram message for notable items, batched routine summaries, and an override for urgent items — and between 22:00 and 07:00 Boston time only urgent items can break through quiet hours.
  3. Every Sunday a Gmail digest summarizes the previous seven days of confidence-gated findings, the Notion family knowledge base contains a new appended entry with full provenance for every finding pushed, and the Telegram message includes the Notion link.
  4. From the Telegram bot the family can request a clinician-shareable PDF; the PDF that arrives embeds every citation tuple, the patient-context document version, and the agent run IDs — Dr. Hien can verify any cited paper himself.
  5. Every digest sent is linked from the `runs` table back to its originating agent run within two clicks of audit, and every morning the family Telegram channel receives the previous day's spend report so cost stays visible.

**v1 release gate (the project's existence test):** Phase 4 ships when criterion 1 is observed at least once and criteria 2-5 are continuously true.

### Phase 5: BRAIN AI Manager Assistant
**Goal**: By the end of this phase, the manager (Shako) has a persistent UX layer that intakes content from 5 channels (PDF/photo/voice/email/text), produces preview cards with transactional batch apply + 30-action undo, emits a Sunday morning briefing, accepts voice-first input via OpenAI Whisper, and drafts compose-only Gmail outreach — all routed through a manager_actions audit log under RLS.
**Depends on**: Phase 4 (engineering sprint closed; Phase 4 acceptance window may still be open)
**Requirements**: Verification gates A-M in `scripts.verify_phase5` (see docs/PHASE_5_EXIT_REPORT.md for full coverage)
**Status**: Engineering sprint closed 2026-05-18, 13/13 PASS · ALL GREEN. 78/78 cumulative verifier coverage. Phase 5 LLM spend $0 / $15 cap. Production activation needs ~45min Shako work (MANAGER_USER_ID env + Railway worker deploy + OPENAI_API_KEY + optional Tesseract) — see docs/PHASE_5_OPERATOR_RUNBOOK.md.
**Success Criteria** (what must be TRUE):
  1. Migration 011 applied: `manager_actions` + `intake_drops` tables exist with PHI CHECK constraint and RLS policies that deny non-manager identities.
  2. Smart Drop Zone parses PDF (PyMuPDF), photo (Tesseract OCR if installed), voice (Whisper), email (raw text), and short text into typed entity previews.
  3. Activity Log + Undo: 24-hour window × 30-action ring buffer; undo reverses both DB and Notion side effects atomically.
  4. Sunday morning briefing assembles deterministic prose (no LLM cost by default) from the prior week of `manager_actions` + `briefs`.
  5. Voice-first input transports `.mp3`/`.m4a` to OpenAI Whisper API behind `check_daily_budget()`; transcript becomes the entity router input.

## Progress

**Execution Order:**
Phases execute in numeric order: 0 → 1 → 2 → 2.5 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Foundation | 0/TBD | Closed | 2026-05-14 |
| 1. Perception | 0/TBD | Closed — 10/10 PASS | 2026-05-15 |
| 2. Memory | 0/TBD | Closed — 19/19 PASS | 2026-05-15 |
| 2.5 Quick Wins (INSERTED) | 0/TBD | Closed — 16/16 PASS | 2026-05-16 |
| 3. Cognition (minimum) | 0/TBD | Closed — 11/11 PASS | 2026-05-16 |
| 4. First Family Value | 0/TBD | Engineering closed 9/9 PASS; 14-day acceptance window in progress (closes ~2026-06-07) | 2026-05-17 (engineering) |
| 5. BRAIN AI Manager Assistant | 0/TBD | Closed — 13/13 PASS · ALL GREEN | 2026-05-18 |
| 6. Bilingual System (i18n) | 2/15 | Executing — Wave 0 closed (06-01 next-intl@4 foundation + 06-02 verifier scaffold + fixtures); Wave 1 plans 06-03a/b, 06-04, 06-05a/b unblocked | 2026-05-20 (Wave 0) |

## Coverage

- v1 requirements: 41 total
- Mapped: 41 of 41
- Unmapped: 0
- Duplicates: 0

| Phase | Requirement IDs | Count |
|-------|-----------------|-------|
| Phase 0 | FND-01, FND-02, FND-03, FND-04, FND-05, FND-06, FND-07, OBS-01 | 8 |
| Phase 1 | PRC-01, PRC-02, PRC-03, PRC-04, PRC-05, PRC-06, PRC-07 | 7 |
| Phase 2 | MEM-01, MEM-02, MEM-03, MEM-04, MEM-05, MEM-06, MEM-07, MEM-08 | 8 |
| Phase 3 | CGM-01, CGM-02, CGM-03, CGM-04, CGM-05, CGM-06, CGM-07, CGM-08, CGM-09, CGM-10 | 10 |
| Phase 4 | ACD-01, ACD-02, ACD-03, ACD-04, ACD-05, OBS-02, OBS-03 | 8 |
| Phase 6 | I18N-01, I18N-02, I18N-03, I18N-04, I18N-05, I18N-06, I18N-07, I18N-08, I18N-09, I18N-10, I18N-11 | 11 |
| **Total** | | **52** |

## Catastrophic Pitfall Gates Summary

| Pitfall (severity) | Countermeasure | Lands In |
|--------------------|----------------|----------|
| Fabricated citations (CATASTROPHIC) | Citation tuple as first-class type + `derived_from_source_ids[]` write contract | Phase 2 (MEM-01, MEM-03) |
| Fabricated citations (CATASTROPHIC) | Deterministic verifier round-trips every PMID/DOI/NCT/URL | Phase 3 (CGM-01) |
| Off-label framing (CATASTROPHIC) | Imperative-verb lint + six-tier evidence ranking + tone post-processor + clinician-question schema | Phase 3 (CGM-03, CGM-04, CGM-05, CGM-06) |
| MRI leak (CATASTROPHIC, import-lint half) | CI fails any server-side import of `viewer/` imaging code; CI fails any remote `fetch`/`axios.post`/`XMLHttpRequest` from `viewer/` | Phase 0 (FND-01, FND-02) |
| MRI leak (CATASTROPHIC, viewer half) | Client-side-only viewer, CSP, dcm2niix.wasm, segmentation on family-local Docker | **v2 (VIS-* requirements — not in v1)** |
| Cost runaway (HIGH) | `/stop` kill-switch + code-side `check_daily_budget()` + n8n daily spend gate at $1.50/day; n8n JSON-body fix still needs live confirmation | Phase 0 (FND-03, FND-04) + Phase 2.5A |
| Shared-memory poisoning (HIGH) | `derived_from_source_ids[]` write contract + per-`agent_id` mem0 scoping | Phase 2 (MEM-03) + Phase 3 (CGM-09) |
| PHI leak in Georgian half of bilingual pair (HIGH) | redact_bilingual + 10-fixture Georgian PHI test set + imperative-verb lint Georgian extension (D-05) | Phase 6 (I18N-10) |
| Migration 012 RLS drop (HIGH) | Pre/post `\d table` policy snapshots; programmatic diff in 06-07 task 2; ALTER COLUMN TYPE does not drop policies on PG 15 | Phase 6 (I18N-05) |

### Phase 6: Bilingual System (i18n)

**Goal:** By the end of this phase, every family-facing viewer route is reachable under `/en/*` and `/ka/*` URL segments and renders fully in the matching language; the 4 family-visible dynamic tables (`aleksandra_timeline`, `hypotheses`, `therapies`, `briefs`) store en+ka pairs in JSONB columns with English fallback; the Communicator and Phase 5 composer emit `{en, ka}` pairs for all newly-created family-visible content; and Telegram delivery uses `.ka` while Gmail delivery uses `.en`.
**Depends on:** Phase 5 (does not block on Phase 5 production activation; the two run independently)
**Requirements**: I18N-01, I18N-02, I18N-03, I18N-04, I18N-05, I18N-06, I18N-07, I18N-08, I18N-09, I18N-10, I18N-11
**Plans:** 13 plans (across 5 waves: 0 foundation, 1 frontend, 2 database, 3 agent output, 4 delivery + regression)

Plans:
**Wave 1**
- [x] 06-01-PLAN.md — Install next-intl@4 + rename middleware.ts → proxy.ts (Next.js 16 convention) + author i18n module files + relocate messages
- [x] 06-02-PLAN.md — Phase 6 verifier scaffold (scripts/verify_phase6.py) + 10-entry Georgian PHI fixture + 30-entry bilingual digest sample set
- [ ] 06-03-PLAN.md — Move 7 family-facing routes under viewer/app/[locale]/ with Next.js 16 async-params signature
- [ ] 06-04-PLAN.md — viewer/lib/i18n.ts displayField helper + unit test + LanguageSwitcher typed-nav polish
- [ ] 06-05-PLAN.md — Expand viewer/messages/{en,ka}.json from 7 keys to ~60–80 keys + insert t() refs across 9 pages + locale-aware TopNav

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 06-06-PLAN.md — Author scripts/migrations/012_i18n_jsonb.sql + per-table pg_dump rollback artifacts + RLS policy snapshots + operator runbook
- [ ] 06-07-PLAN.md — [BLOCKING][autonomous=false] Apply migration 012 to production Supabase (Shako maintenance window) + capture post-apply RLS diff
- [ ] 06-08-PLAN.md — Update manager apply route to write JSONB shape + Timeline/Therapies/Hypotheses pages render via displayField

**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 06-09-PLAN.md — scripts/communicator/bilingual.py compose_bilingual helper (Anthropic strict tool_use) + weekly_brief Option-A mirror + Communicator/manager_briefing JSONB emission
- [ ] 06-10-PLAN.md — phi_redactor.py bilingual-aware (Mkhedruli suffix glue) + redact_bilingual helper + 13-test pytest suite over the 10 Georgian PHI fixtures
- [ ] 06-11-PLAN.md — banned_phrases.py D-05 lexicon extension (8 new Georgian imperative-verb entries) + 39-test regression suite + Shako review checkpoint

**Wave 4** *(blocked on Wave 3 completion)*
- [ ] 06-12-PLAN.md — _bilingual_read.py display_field_py helper + telegram_sender reads .ka + gmail_digest reads .en + n8n zero-touch documentation
- [ ] 06-13-PLAN.md — Finalize verify_phase6.py + production-mode 11/11 sweep + verify_phase4 9/9 + verify_phase5 13/13 regression + Phase 6 exit report + STATE/ROADMAP/REQUIREMENTS/CLAUDE updates

**Cross-cutting constraints:**
- No new remote fetch/axios.post/XMLHttpRequest from viewer/ to non-self origins introduced by this plan (FND-02 trust boundary lint must continue to pass)

---

*Roadmap created: 2026-05-13*
*Phase 6 added: 2026-05-20*
*Granularity: standard*
*Mode: yolo*
*v2 phases (Cognition-full, Action interactivity, Visualization, HIPAA posture) live in REQUIREMENTS.md and are explicitly out of v1 scope.*
