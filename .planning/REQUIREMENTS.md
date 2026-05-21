# Requirements: ALEKSANDRA_BRAIN

**Defined:** 2026-05-13
**Core Value:** Never miss a credible treatment lead for Aleksandra.

> All v1 requirements are **hypotheses until shipped**. Each is written as something a family member or treating clinician can observe and confirm. Acceptance test for the v1 release: within a 14-day window after Phase 4 ships, the family receives at least one digest containing a credible lead they would not have found via ChatGPT + Google Scholar in the same window, with full source provenance, at total cost under $30.

## v1 Requirements

### Foundation (FND)

- [ ] **FND-01**: Project monorepo has CI that fails any pull request which imports client-side imaging code from a server-route file
- [ ] **FND-02**: Project monorepo has CI that fails any commit adding `fetch`, `axios.post`, or `XMLHttpRequest` calls from `viewer/` paths to non-self origins
- [ ] **FND-03**: Family can send `/stop` to the Telegram bot and within 60 seconds all running agents stop and the next cron tick is cancelled
- [ ] **FND-04**: An n8n daily-spend gate halts downstream Anthropic-calling nodes once that day's billed Anthropic spend crosses $1.50
- [ ] **FND-05**: Supabase schema enforces row-level security so the family account is the only identity that can read any row containing patient data
- [ ] **FND-06**: An `MCP-INVENTORY.csv` lists every MCP server in use with its allowlisted agents; an agent calling a non-allowlisted MCP fails closed
- [ ] **FND-07**: Secrets are loaded from a vault, not committed to git; CI fails on any commit that introduces a high-entropy string in a tracked file

### Perception (PRC)

- [ ] **PRC-01**: Every 6 hours a scheduled job pulls new PubMed records via NCBI E-utilities using a project-identifying user-agent + mailto + registered `api_key`
- [ ] **PRC-02**: Every 6 hours a scheduled job pulls new ClinicalTrials.gov records via the v2 REST API for the Aleksandra facet set
- [ ] **PRC-03**: Every 6 hours a scheduled job pulls new bioRxiv and medRxiv preprints via RSS for the Aleksandra facet set
- [ ] **PRC-04**: Crawl4AI fills coverage gaps where index APIs do not return full text; raw payloads are written to Cloudflare R2 with content-hash keys
- [ ] **PRC-05**: A Firecrawl call only runs when Crawl4AI fails twice on the same URL and the monthly Firecrawl spend is under $10
- [ ] **PRC-06**: A negative-evidence retrieval branch runs on the same cron, querying for null/no-effect/retracted results for currently-tracked candidates
- [ ] **PRC-07**: Every ingested record has a row in the Supabase ledger with `{source_id, retrieval_method, retrieval_timestamp, content_hash, raw_artifact_url}`

### Memory (MEM)

- [ ] **MEM-01**: The citation tuple `{source_id, retrieval_method, retrieval_timestamp, confidence, verbatim_grounding, byte_offset}` is a first-class type referenced by every claim
- [ ] **MEM-02**: A single-writer ingestion service fans out atomically from the Supabase ledger to Graphiti and to Qdrant; a partial fan-out is rolled back
- [ ] **MEM-03**: Every Graphiti fact carries `derived_from_source_ids[]`; a write that omits this field is rejected
- [ ] **MEM-04**: Every Qdrant point is stamped with `embedding_model`, `chunker_version`, `graphiti_uuid`, and `content_hash`; identical content is deduplicated
- [ ] **MEM-05**: Agents retrieve only through one `retrieve(query, t_at=...)` LightRAG function — direct Graphiti or Qdrant client use from agent code is blocked by a lint rule
- [ ] **MEM-06**: The graph ontology lives in a checked-in `graph_ontology.yaml` and changes require a versioned migration; ad-hoc node labels are rejected at write time
- [ ] **MEM-07**: A nightly reconciler asserts every Graphiti fact has a Qdrant point and every Qdrant point has a Graphiti `uuid`; mismatches are flagged in the run log
- [ ] **MEM-08**: A smoke test ingests 100 known papers, then `retrieve("cord blood + HIE")` returns at least 90 of them in the top 100 results

### Cognition — Minimum (CGM)

- [ ] **CGM-01**: A deterministic verifier service round-trips every PMID, DOI, NCT identifier, and URL in a draft digest against its original index API and rejects any identifier that does not resolve to the cited title and authors
- [ ] **CGM-02**: An Analyzer agent extracts study population, intervention, comparator, outcome, and evidence-grade for each ingested paper and writes them to Graphiti via the MEM-03 contract
- [ ] **CGM-03**: A Communicator agent assembles digests using a fixed schema `{finding, source, evidence_strength, population_gap, clinician_question}`
- [ ] **CGM-04**: An imperative-verb lint applied to every Communicator output blocks any draft containing `should`, `must`, `consider`, `try`, `ask for`, or `request` directed at the family
- [ ] **CGM-05**: A six-tier evidence ranking is enforced; findings below tier 2 cannot appear in the top section of a digest
- [ ] **CGM-06**: A `taxonomy/tone.yaml` lexicon post-processor strips or rewrites prognostic language; the deterministic check runs after every Communicator pass
- [ ] **CGM-07**: A confidence gate at level HIGH blocks publishing during initial rollout; sub-HIGH drafts are staged in Notion with a missing-evidence reason
- [ ] **CGM-08**: CrewAI agents run with `max_iter=7`, `max_execution_time=30s`, and `max_tokens_per_run=80_000`; exceeding any limit terminates the run and logs the cause
- [ ] **CGM-09**: mem0 entries are scoped by `agent_id`; cross-agent reads require an explicit traversal that records the source `agent_id`
- [ ] **CGM-10**: An Aleksandra patient-context document is prepended to every agent prompt; the document is versioned and the version is logged with the run

### Action — Digest (ACD)

- [ ] **ACD-01**: A confidence-gated digest is pushed to the family Telegram channel; routine items are batched, notable items send one message, urgent items override quiet hours
- [ ] **ACD-02**: Quiet hours 22:00–07:00 Boston suppress routine and notable tiers; only urgent overrides
- [ ] **ACD-03**: A weekly Gmail digest summarizes the previous seven days of confidence-gated findings as a redundancy channel
- [ ] **ACD-04**: New findings are appended to the Notion family knowledge base with full provenance; the link is included in the Telegram message
- [ ] **ACD-05**: The family can request a clinician-shareable PDF from the bot; the PDF embeds every citation tuple, the patient context version, and the agent run IDs

### Observability (OBS)

- [ ] **OBS-01**: Every agent run is recorded in an append-only Supabase `runs` table with start time, end time, token cost, exit status, and a link to the produced draft
- [ ] **OBS-02**: Every digest sent to Telegram or Gmail is linked from `runs` so any published claim can be traced to the originating run within two clicks
- [ ] **OBS-03**: A daily spend report is posted to the family Telegram channel each morning so cost stays visible

### Bilingual System — i18n (I18N)

- [x] **I18N-01**: next-intl@4 is installed and compatible with Next.js 16.2.6; the viewer builds with locale routing enabled and serves `/en/dashboard` and `/ka/dashboard` as distinct pre-rendered routes
- [x] **I18N-02**: Family-facing routes live under `viewer/app/[locale]/*`; visiting `/en/{dashboard,timeline,papers,therapies,hypotheses,today,knowledge}` and `/ka/{...}` each returns HTTP 200; bare `/dashboard` 308-redirects to `/en/dashboard`
- [x] **I18N-03**: Static UI strings live in `viewer/messages/{en,ka}.json` (143 leaves × 2 locales across 11 namespaces); every `t(...)` / `useTranslations(...)('...')` reference in `viewer/app/[locale]/**` + `viewer/components/**` resolves to a key in both message files
- [x] **I18N-04**: LanguageSwitcher mounted in `viewer/app/[locale]/layout.tsx` header swaps `/en/*` ↔ `/ka/*` via `router.replace(pathname, {locale})`; URL is the single source of truth — no cookie/localStorage
- [x] **I18N-05**: Migration 012 (`scripts/migrations/012_i18n_jsonb.sql`) converts 6 family-visible TEXT columns to JSONB with `USING jsonb_build_object('en', col, 'ka', col)` across 4 tables (`aleksandra_timeline`, `hypotheses`, `therapies`, `briefs.sections`); RLS from migration 008 preserved; Shako-applied 2026-05-20
- [x] **I18N-06**: Communicator + Phase 5 composer emit `{en, ka}` JSONB pairs for family-visible newly-created content via `scripts/communicator/bilingual.py::compose_bilingual` (Anthropic strict tool_use) or deterministic Option-A mirror; budget gate honored via `check_daily_budget(raise_on_over=True)`
- [x] **I18N-07**: Telegram-sending worker code reads `.ka` (via `display_field_py`); Gmail-sending worker code reads `.en`; per-file locale constants (`TELEGRAM_LOCALE`, `GMAIL_LOCALE`, `BRIEFING_LOCALE`); n8n workflows unchanged (zero-touch)
- [x] **I18N-08**: `viewer/lib/i18n.ts::displayField(field, locale)` returns `field?.[locale] ?? field?.en ?? ''` with type guards for legacy TEXT-string passthrough; consumed across 9 displayField call sites in the 4 plan-target pages
- [x] **I18N-09**: Migration 012 sets `ka = en` for all existing rows; AI re-translation of historical content (200 entities, 307 facts, 47 episodes, 10 hypotheses, 12 therapies) is OUT of this phase and deferred to a future maintenance backlog item
- [x] **I18N-10**: PHI redactor runs on both `.en` and `.ka` strings via `redact_bilingual({en, ka}, consent)` wrapper; imperative-verb lint extended with 8 Georgian D-05 entries (`უნდა`, `აუცილებლად`, `განიხილეთ`, `მოითხოვეთ`, `ითხოვეთ`, `სცადეთ`, `გაითვალისწინეთ`, `მართებთ`); Phase 3 CGM-04 English invariants unchanged
- [x] **I18N-11**: After Phase 6 lands, `verify_phase4 --mode code-complete` exits 0 with 9/9 PASS and `verify_phase5 --mode code-complete` exits 0 with 13/13 PASS; `check_i18n_11` spawns both as subprocesses to codify the regression sweep into the Phase 6 verifier itself

## v2 Requirements

Deferred to a later milestone, not in the current roadmap.

### Cognition — Full

- **CGF-01**: Spider agent runs positive and negative retrieval modes with deduplication and query expansion
- **CGF-02**: Hypothesis agent runs cross-disease pattern search (HIE ↔ CP, neonatal stroke, periventricular leukomalacia, anoxic brain injury) and a falsifier step via vendored Adaptive GoT MCP
- **CGF-03**: Repurposing agent surfaces drug-repurposing candidates via a `repurpose-mcp`; candidates are framed as clinician questions, never as recommendations
- **CGF-04**: A weekly "counter-evidence for currently-tracked candidates" digest section runs
- **CGF-05**: A DSPy optimization pass uses the accumulated run-log corpus to improve agent prompts
- **CGF-06**: The confidence gate loosens to MEDIUM with a human-in-the-loop review queue for borderline items

### Action — Interactivity

- **ACI-01**: The Telegram bot supports a `ask_user` 2-way pattern so an agent can pause for clarification
- **ACI-02**: A Google Calendar pipeline tracks the Duke EAP target window, vigabatrin washout, and BMC appointments
- **ACI-03**: Booking.com and Kiwi.com integrations propose travel options for confirmed appointments; the family approves before any booking
- **ACI-04**: Urgent-tier messages are sent bilingually (Georgian + English) with both Tbilisi and Boston timezone stamps

### Visualization

- **VIS-01**: A Next.js client-side viewer loads a NIfTI from a local `File` handle and renders it with NiiVue; the network tab shows zero outbound voxel bytes for the volume
- **VIS-02**: DICOM is converted to NIfTI in-browser via `dcm2niix.wasm`
- **VIS-03**: An atlas overlay is provided by `atlas-mcp` returning region identifiers only — never voxels
- **VIS-04**: A pre-commit hook fails on any new server-side reference to imaging modules
- **VIS-05**: A neonatal segmentation pipeline (FastSurfer-LIT → BIBSnet → BONBID-HIE → nii2mesh) runs on a family-local Docker; `bonbid-mcp` accepts job descriptors only, never voxels
- **VIS-06**: 3D anatomical shells are rendered with React Three Fiber 9.6.x stable; v10 is explicitly excluded until it leaves alpha

### Brain Simulation + Print

- **SIM-01**: TVB Docker is wrapped by `tvb-mcp` to run sandboxed simulations
- **SIM-02**: A `brain2print` STL export produces watertight meshes via `nii2mesh` + `pymeshfix`

### HIPAA Posture (clinician-access path)

- **HPA-01**: Prism MCP is integrated when a treating clinician needs read access; until then no clinician PHI is routed through Telegram or Notion
- **HPA-02**: A Hindsight self-improving memory layer is added once the run-log corpus exceeds N entries

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Auto-generated clinical recommendations to the family | Every medical decision is made by a real clinician; the system surfaces and explains, it does not prescribe |
| Server-side storage of patient MRI / DICOM / NIfTI | Privacy non-negotiable; client-side only is the load-bearing invariant |
| General-purpose chat UI on top of the agent crew | Re-creates ChatGPT; does nothing for the Core Value |
| "Limited outcomes" framing in user-facing copy | Conflicts with the project's stance on neuroplasticity in the 0–2 window |
| Multi-patient generalization, productization, or SaaS | One patient is the entire scope; productization is a distraction during the neuroplasticity window |
| Fabricated citations or paraphrased claims without a verifiable source | "Source not found" is an acceptable answer; fabrication is not |
| Real-time streaming agent UI | Digest is the value, not a chat surface; would inflate cost and complexity |
| Custom mobile app | Telegram already covers mobile delivery |
| All 52 MCP servers active concurrently | MCP sprawl is a named pitfall; start with five, allowlist per agent |
| LangChain or LangGraph for orchestration | CrewAI maps directly to the five named roles; adding a second framework is dead weight |
| OAuth / multi-tenant auth | One family identity; magic-link or single account is enough |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FND-01 | Phase 0 | Pending |
| FND-02 | Phase 0 | Pending |
| FND-03 | Phase 0 | Pending |
| FND-04 | Phase 0 | Pending |
| FND-05 | Phase 0 | Pending |
| FND-06 | Phase 0 | Pending |
| FND-07 | Phase 0 | Pending |
| PRC-01 | Phase 1 | Pending |
| PRC-02 | Phase 1 | Pending |
| PRC-03 | Phase 1 | Pending |
| PRC-04 | Phase 1 | Pending |
| PRC-05 | Phase 1 | Pending |
| PRC-06 | Phase 1 | Pending |
| PRC-07 | Phase 1 | Pending |
| MEM-01 | Phase 2 | Pending |
| MEM-02 | Phase 2 | Pending |
| MEM-03 | Phase 2 | Pending |
| MEM-04 | Phase 2 | Pending |
| MEM-05 | Phase 2 | Pending |
| MEM-06 | Phase 2 | Pending |
| MEM-07 | Phase 2 | Pending |
| MEM-08 | Phase 2 | Pending |
| CGM-01 | Phase 3 | Pending |
| CGM-02 | Phase 3 | Pending |
| CGM-03 | Phase 3 | Pending |
| CGM-04 | Phase 3 | Pending |
| CGM-05 | Phase 3 | Pending |
| CGM-06 | Phase 3 | Pending |
| CGM-07 | Phase 3 | Pending |
| CGM-08 | Phase 3 | Pending |
| CGM-09 | Phase 3 | Pending |
| CGM-10 | Phase 3 | Pending |
| ACD-01 | Phase 4 | Pending |
| ACD-02 | Phase 4 | Pending |
| ACD-03 | Phase 4 | Pending |
| ACD-04 | Phase 4 | Pending |
| ACD-05 | Phase 4 | Pending |
| OBS-01 | Phase 0 | Pending |
| OBS-02 | Phase 4 | Pending |
| OBS-03 | Phase 4 | Pending |
| I18N-01 | Phase 6 | Validated (2026-05-21) |
| I18N-02 | Phase 6 | Validated (2026-05-21) |
| I18N-03 | Phase 6 | Validated (2026-05-21) |
| I18N-04 | Phase 6 | Validated (2026-05-21) |
| I18N-05 | Phase 6 | Validated (2026-05-21) |
| I18N-06 | Phase 6 | Validated (2026-05-21) |
| I18N-07 | Phase 6 | Validated (2026-05-21) |
| I18N-08 | Phase 6 | Validated (2026-05-21) |
| I18N-09 | Phase 6 | Validated (2026-05-21) |
| I18N-10 | Phase 6 | Validated (2026-05-21) |
| I18N-11 | Phase 6 | Validated (2026-05-21) |

**Coverage:**
- v1 requirements: 52 total (41 v1.0 + 11 i18n in v1.1)
- Mapped to phases: 52
- Unmapped: 0

---
*Requirements defined: 2026-05-13*
*Last updated: 2026-05-21 — Phase 6 (Bilingual System i18n) closed; 11 I18N-* requirements validated (89/89 cumulative verifier coverage)*
