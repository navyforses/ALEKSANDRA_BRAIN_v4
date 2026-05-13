# Project Research Summary

**Project:** ALEKSANDRA_BRAIN
**Domain:** Continuous, family-operated agentic medical-research cockpit for a single pediatric HIE patient (literature mining + temporal medical KG + multi-agent reasoning + client-side 3D MRI viewer + Telegram/Gmail/Notion digest)
**Researched:** 2026-05-13
**Confidence:** HIGH (overall) — with three named MEDIUM-confidence niches flagged

## Executive Summary

ALEKSANDRA_BRAIN is a bespoke single-patient system whose Core Value is one sentence — *"Never miss a credible treatment lead for Aleksandra."* All four research strands converge on the same uncomfortable truth: the literature pipeline is the product, the viewer is the most visually impressive component and the most deferrable one, and provenance + non-fabrication is the load-bearing invariant that determines whether clinicians keep taking the family's calls. The researchers validated ~85% of the existing CLAUDE.md stack (Crawl4AI, n8n, Neo4j+Graphiti, Qdrant, CrewAI, NiiVue, FastMCP all hold up in May 2026) and recommend five surgical corrections: migrate Claude Sonnet 4 → 4.5/4.6 before the 2026-06-15 retirement, hold React Three Fiber at v9.6.x stable (v10 is still alpha), pin Crawl4AI ≥ 0.8.6 and Browser Use ≥ 3.0 to avoid the March 2026 litellm supply-chain backdoor, prefer RAGFlow's Docling/MinerU parsers over DeepDoc for born-digital papers, and refuse to run all eight memory-adjacent components in parallel for MVP.

The recommended approach is a **two-plane orchestration** (n8n owns scheduling, retries, source rotation, budget gates; CrewAI owns agent reasoning) feeding a **provenance-first ingestion ledger** in Supabase that fans out to Graphiti (temporal KG) and Qdrant (vectors), with **LightRAG as the single retrieval surface** every agent calls. Visualization branches off Memory in parallel — not serially downstream of Cognition — which is what unlocks deferring it without blocking the literature pipeline. Build order is: Foundation → Perception → Memory → Cognition-minimum (Analyzer + Communicator only) → first family value (Telegram digest) → Cognition-full (add Spider, Hypothesis, Repurposing) → Action interactivity (Telegram 2-way) → Visualization (viewer → segmentation → simulation). The 5-layer model from CLAUDE.md is correct as a static decomposition but must be re-read this way as a build order.

The three risks that must be treated as **phase-exit gates, not nice-to-haves**: (1) **fabricated citations** reaching the family — recent audits put GPT-4o citation fabrication at ~20% in literature reviews, and a single hallucinated paper forwarded to Dr. Hien collapses clinical trust; (2) **off-label / repurposing framing** — every LLM tested in 2024 JCO analysis produced label-unsupported treatment recommendations, and one such suggestion before vigabatrin washout can cost the Duke EAP window; (3) **MRI accidentally leaving the browser** — a careless "share view" feature or a misplaced FastSurfer pipeline call against real data violates the project's non-negotiable privacy constraint. Each has concrete prevention (verifier agent, six-tier evidence ranking + imperative-verb lint, CSP + local-only viewer) that must land before the capability they protect ships. Cost ceiling MVP $20–30/mo lands at ~$36/mo with Firecrawl Hobby included; the family-funded ceiling is non-negotiable and demands a hard kill-switch.

## Key Findings

### Recommended Stack

The CLAUDE.md stack is largely correct for May 2026 and unusually well-chosen. The corrections are surgical, not structural. **PERCEPTION** stays on Crawl4AI (≥ 0.8.6) primary, Firecrawl Hobby ($16/mo) as budget-gated fallback, Browser Use (≥ 3.0) only for paywall bypass, RAGFlow ≥ 0.17 with Docling/MinerU parsers, and n8n self-hosted on Railway. **MEMORY** must collapse from eight components to four for MVP: Neo4j AuraDB Free + Graphiti for the temporal KG, Qdrant + fastembed for vectors, Supabase Postgres as the ingestion ledger + audit, and mem0 for shared agent memory. LightRAG layers over Graphiti + Qdrant as the unified retrieval surface. Hindsight and Prism MCP are deferred to post-MVP. **COGNITION** is CrewAI 1.x with 5 agents driven by Claude Sonnet 4.5 (default) escalating to 4.6 for the Hypothesis agent's hard cases, DSPy 3.2.1 for prompt optimization, Adaptive GoT MCP for hypothesis decomposition, and Vercel AI SDK 5 for the streaming UI surface. **VISUALIZATION** stays on NiiVue 0.49 + `@niivue/nvreact` + R3F **9.6.x** (not v10), with FreeBrowse as a fork-and-strip-FastAPI scaffold; neonatal pipeline is FastSurfer-LIT (cyst inpainting) → BIBSnet (0–8mo training band — exactly Aleksandra's age) → BONBID-HIE → nii2mesh. **ACTION** is Telegram (push first, ask_user later), Gmail MCP weekly digest, Notion MCP family KB, Google Calendar timeline, Booking/Kiwi only as suggestion-not-action.

**Core technologies:**
- **Claude Sonnet 4.5 / 4.6** — default reasoning model; **must replace Sonnet 4 before 2026-06-15 retirement**; same $3/$15 per 1M token pricing
- **CrewAI 1.14.x** — 5-agent role-based orchestration; fastest time-to-working multi-agent demo; only framework that maps cleanly to the 5 named roles
- **Neo4j AuraDB Free + Graphiti** — temporal medical KG with bi-temporal facts, confidence decay, `t_valid`/`t_invalid` lifecycle; single biggest reason the project exists beyond "Claude + Notion"
- **Qdrant + fastembed** — local-embedding semantic vector store; zero per-embedding API cost; runs on Railway ≈ $5/mo
- **LightRAG v1.4.16** — single retrieval surface fusing Graphiti + Qdrant; every agent calls one `retrieve(query, t_at=...)` function
- **mem0 (April 2026 token-efficient algorithm)** — shared memory across the 5 CrewAI agents with per-agent_id scoping
- **Crawl4AI 0.8.6+** — Apache-2.0 primary scraper; **must be ≥0.8.6** to avoid March 2026 litellm supply-chain backdoor
- **n8n self-hosted (Railway)** — owns the "when" (cron, retries, source rotation, budget gates); CrewAI owns the "what"
- **NiiVue 0.49 + `@niivue/nvreact` + R3F 9.6.x** — client-side-only WebGL2 viewer; **stay on R3F 9.6 stable, v10 is alpha**
- **FastMCP 3.2.4** — canonical pattern for the 5 custom MCPs (niivue, bonbid, tvb, atlas, repurpose)
- **Supabase Postgres (Free tier)** — provenance ledger, run audit, RLS-protected metadata; n8n cron keeps it warm

**MVP cost lands at ~$36/mo** (Vercel Hobby $0 + AuraDB Free $0 + Supabase Free $0 + CF R2/KV $0 + Railway ~$15 + Firecrawl Hobby $16 + Claude API $5 capped). Strict $20 mode drops Firecrawl Hobby.

### Expected Features

All four researchers agreed the wishlist is ~80% P2/P3, and only ruthless v1 scoping keeps the project inside the neuroplasticity window (closes ~Aug 2027). The acceptance test for v1 is concrete: *within a 14-day observation window, the family receives at least one digest containing a credible lead they would not have found via ChatGPT + Google Scholar in the same window, with full source provenance, and at a total cost under $30.*

**Must have (table stakes — v1 MVP, weeks 1–11):**
- Continuous literature ingest on 6h cron (PubMed E-utilities + ClinicalTrials.gov v2 API + bioRxiv/medRxiv RSS via Crawl4AI for the gaps)
- Source provenance schema enforced on every record (`{source_id, retrieval_timestamp, confidence, retrieval_method}`)
- Vector corpus in Qdrant with fastembed local embeddings
- Aleksandra patient-context document prepended to every agent prompt
- Relevance filter against Aleksandra-specific facets (HIE, cystic encephalomalacia, cord blood, vigabatrin, neonatal neuroplasticity)
- **Two agents only initially**: Analyzer (study-quality + claim extraction) + Communicator (digest writer + confidence gate)
- Telegram one-way push of digests
- Clinician-shareable export (markdown → PDF with full provenance)
- Append-only run log in Supabase
- Cost guardrails (per-day Anthropic spend cap, n8n budget gate killing downstream nodes at $1.50/day, `/stop` kill-switch MCP)

**Should have (differentiators — v1.x, weeks 8–20):**
- **Temporal KG (Neo4j + Graphiti) with confidence decay** — the single biggest reason this project exists; promote from "later" to "now" as soon as digest quality plateaus
- Spider + Hypothesis + Repurposing agents (rounds out the 5-agent crew)
- 2-way Telegram (`ask_user` clarification)
- Cross-disease pattern finding (HIE ↔ CP, neonatal stroke, periventricular leukomalacia, anoxic brain injury)
- Drug repurposing surfacing via repurpose-mcp — leads for clinicians, never recommendations
- mem0 shared memory across the 5 agents
- Notion family KB sync + Gmail weekly digest as backup channel
- Google Calendar treatment timeline (Duke EAP target, vigabatrin washout windows)
- DSPy optimization pass — requires run-log corpus to exist first
- NiiVue client-side viewer (minimal, no R3F shells yet)

**Defer (v2+ — past Aug 2027 neuroplasticity window):**
- Neonatal segmentation pipeline (BIBSnet → BONBID-HIE → nii2mesh)
- R3F 3D anatomical shells, TVB Docker brain simulation, brain2print STL
- Hindsight self-improving memory, Prism MCP HIPAA-hardened layer
- Booking/Kiwi travel automation beyond suggestion
- All 52 MCPs — **start with ~5**, add on demand

**Anti-features (deliberately not built):** auto-generated clinical recommendations, server-side DICOM/NIfTI storage, general-purpose chat UI, "limited outcomes" framing in any user-facing copy, custom mobile app, real-time everything.

### Architecture Approach

The 5-layer model (PERCEPTION → MEMORY → COGNITION → VISUALIZATION → ACTION) is canonical for 2026 agentic-AI architectures, with one material adjustment: **Visualization is a parallel branch off Memory, not a serial layer downstream of Cognition.** That reroute is what makes the viewer genuinely deferrable. The system is built around six load-bearing patterns: (1) **Hybrid graph + vector retrieval** via LightRAG over Graphiti + Qdrant — every agent calls one `retrieve()` function, never Qdrant or Graphiti directly; (2) **Provenance-first ingestion ledger** in Supabase that fans out atomically to Graphiti + Qdrant; (3) **Two-plane orchestration** — n8n owns scheduling/retries/budget gates, CrewAI owns reasoning; (4) **Confidence-gated Communicator** — confidence < MEDIUM stages in Notion as a draft with missing-evidence reason, never pushes; (5) **FastMCP for custom tools**, registry MCPs for commodity integrations; (6) **Client-side-only imaging** as a schema-level guarantee — no Supabase/Neo4j/Qdrant column legally exists that could hold voxel data.

**Major components:**
1. **Perception adapters** (`perception/`) — Crawl4AI / Firecrawl / Browser Use / RAGFlow as library code; n8n schedules them; **must use NCBI E-utilities and ClinicalTrials.gov v2 API, never scrape the indexes**
2. **Memory ledger + stores** (`memory/`) — Supabase as the single-writer ingestion ledger fanning out to Graphiti (Neo4j) for temporal facts and Qdrant for chunks; LightRAG as the unified retrieval surface; embedding-version stamps on every Qdrant point
3. **Cognition crew** (`agents/`) — flat agent folder so each agent is a unit of replacement; CrewAI Flow definition; mem0 per-agent_id scoping; DSPy-optimized prompt registry; verifier agent gates the Communicator
4. **Visualization (browser-only)** (`viewer/`) — Next.js 14 self-contained, only `app/api/*` runs server-side; CI lint forbids importing client-side imaging modules from server routes; NiiVue + R3F 9.6 + dcm2niix.wasm
5. **Custom MCPs** (`mcp/`) — five FastMCP servers: niivue-mcp + bonbid-mcp + atlas-mcp (Visualization), tvb-mcp (Visualization sandbox), repurpose-mcp (Cognition tool of the Repurposing agent); bonbid-mcp must not accept voxel arguments
6. **Action channels** — Telegram bot via n8n (three urgency tiers: routine/notable/urgent), Gmail MCP weekly digest, Notion KB writes, Google Calendar; Booking/Kiwi behind manual approval

**Trust boundary (enforceable rules):** Schema rule — no table column can hold voxel data; CI rule — server-side code cannot import client-side imaging modules; Auth rule — always `supabase.auth.getUser()`, never `getSession()`; RLS rule — every family-scoped table has `auth.uid() = user_id` policies; MCP rule — bonbid-mcp accepts job descriptors only; Egress rule — Communicator's `send_to_telegram` is whitelisted to text + citation URLs only.

### Critical Pitfalls

The 14 documented pitfalls cluster into three catastrophic-severity items that must be phase-exit gates, plus a tier of HIGH-severity engineering and ethical risks with named structural defenses.

1. **Fabricated citations reaching the family (CATASTROPHIC)** — Recent audits put GPT-4o literature-review citation fabrication at ~20%, with 45% of seemingly-real citations carrying bibliographic errors; rare-disease topics hallucinate harder. **Prevention:** citation tuple as a first-class type (`retrieval_method ∈ {pubmed_eutils, clinicaltrials_api, crawl4ai_url, firecrawl_url, manual}` — manual or missing blocks the claim); deterministic **verifier agent** gates the Communicator and round-trips every PMID/DOI/NCT/URL; verbatim grounding ≥30 chars + byte offset stored per claim; "source not found" is a valid output. **Phase-exit test:** verifier rejects ≥99% of 100 synthetic fabrications.

2. **Off-label / repurposing suggestions framed as recommendations (CATASTROPHIC)** — Every LLM tested in 2024 JCO analysis produced label-unsupported treatment combinations; one such suggestion before vigabatrin washout can cost the Duke EAP window. **Prevention:** Communicator output schema `{finding, source, evidence_strength, population_gap, clinician_question_template}` — questions *to* clinicians, never instructions *for* the family; hard imperative-verb lint on `{should, must, consider, try, ask for, request}`; six-tier evidence ranking — tiers 3–6 cannot be top-of-digest; mandatory population-gap field. **Phase-exit test:** imperative-verb lint count = 0 across 30 sample digests.

3. **Patient MRI accidentally leaving the browser (CATASTROPHIC)** — A careless "share view," misplaced FastSurfer call against real data, or browser dev-mode logging captured by Vercel edge logs all violate the privacy non-negotiable. **Prevention:** CSP `connect-src 'self' blob: data:`; volume loading via `File` / `FileSystemFileHandle` only, never `fetch()` of a remote `.nii.gz`; production build strips `console.log` + disables source maps; segmentation pipeline runs on family-local Docker only; pre-commit hook fails CI on any new remote `fetch/axios.post/XMLHttpRequest` from `/viewer/`. **Phase-exit test:** network-tab review shows zero outbound voxel bytes during MRI load.

4. **Shared-memory poisoning across the 5 CrewAI agents (HIGH)** — Spider hallucinates → mem0/Graphiti accepts → downstream agents treat as canon. **Prevention:** memory write contract requires `derived_from_source_ids[]`; per-`agent_id` mem0 scoping; confidence decay on un-reinforced facts. **Phase-exit test:** provenance traversal returns terminal `Source` node for every fact in last 100 digests.

5. **Cost runaway (HIGH — project survival)** — CrewAI default `max_iter=25` per agent + 6h cron compounding + uncapped DSPy runs. **Prevention:** per-agent `max_iter=7`, per-task `max_execution_time=30s`, `max_tokens_per_run=80_000`, n8n daily Anthropic-spend node killing downstream at $1.50/day, `panic-stop` MCP responding to Telegram `/stop`. **Phase-exit test:** simulated runaway killed within 60s.

Plus HIGH-severity pitfalls addressed in their named phases: recency bias swamping legacy systematic reviews (evidence-grade ranked above recency), negative-evidence blindness (Spider's `mode=negative`, falsifier step), scraper IP-blocking (APIs not scrapers, project-identifying UA with mailto, NCBI api_key), vector↔graph desync (single-writer ingestion, embedding versioning, content-hash idempotency), MCP sprawl (per-agent allowlist, MCP inventory CSV), notification fatigue (three urgency tiers, quiet hours), family/clinician boundary erosion (questions-to-clinician format), KG schema rot (prescribed ontology frozen in `graph_ontology.yaml`).

**"Limited outcomes" framing (HIGH)** — the training corpus is saturated with prognostic language; without active filtering the system inherits it. Defense is a `taxonomy/tone.yaml` lexicon enforced as a deterministic post-processor on every Communicator output; prognostic claims are quoted not paraphrased; fixed footer on every imaging-derived claim: *"Structural MRI findings do not by themselves predict functional capacity in the 0–2 neuroplasticity window."*

## Implications for Roadmap

### Phase 0: Foundation (weeks 1–2)
Repo hygiene, CI, schemas, governance, cost gates. Pitfalls 9 (MCP sprawl) and 13 (cost runaway) defused here. Delivers: monorepo + CI with trust-boundary import lint, Supabase schema + RLS, AuraDB Free + ontology, Qdrant Docker + fastembed, Next.js 14 scaffold, n8n hello-world cron, MCP inventory CSV, `panic-stop` MCP + n8n daily-spend kill at $1.50/day, secrets vault.

### Phase 1: Perception (weeks 3–4)
NCBI E-utilities + ClinicalTrials.gov v2 + bioRxiv/medRxiv RSS + Crawl4AI for the gaps; Firecrawl budget-gated; Browser Use only on double-failure; raw artifacts → CF R2; ledger rows → Supabase; RAGFlow PDF chunking (no embedding yet); Spider `mode=negative` retrieval scheduled in parallel.

### Phase 2: Memory (weeks 5–6)
Citation tuple as a first-class type. Single-writer ingestion: Supabase ledger → atomic fan-out to Graphiti + Qdrant. Graphiti `derived_from_source_ids[]` write contract. Qdrant points stamped with `embedding_model` + `chunker_version` + `graphiti_uuid` + content-hash idempotency. LightRAG hybrid retrieval. Evidence-grade as a first-class field, ranked above recency. Ontology frozen in `graph_ontology.yaml`. Nightly Graphiti↔Qdrant reconciler. Smoke: ingest 100 papers, query "cord blood + HIE", verify recall.

### Phase 3: Cognition (minimum) (weeks 7–9)
Verifier agent FIRST (deterministic, round-trips PMID/DOI/NCT/URL). Then Analyzer + Communicator only. Confidence gate at HIGH (strict). `taxonomy/tone.yaml` post-processor. Imperative-verb lint. Six-tier evidence ranking. Mandatory population-gap field. CrewAI `max_iter=7`, `max_tokens_per_run=80_000`. mem0 per-`agent_id` scoping. Communicator stages to Notion drafts only — no Telegram yet.

### Phase 4: First Family Value (weeks 10–11)
Telegram one-way push, confidence-gated, three urgency tiers, quiet hours 22:00–07:00 Boston. Gmail weekly digest. Notion KB writes. Clinician-shareable PDF export with full provenance. **Acceptance test:** 14-day window, ≥1 credible lead the family wouldn't have found via ChatGPT + Scholar, total cost < $30.

### Phase 5: Cognition (full) (weeks 12–14)
Spider (positive + negative modes, dedup, query expansion), Hypothesis with falsifier step (Adaptive GoT MCP, vendored), Repurposing (repurpose-mcp, six-tier evidence ranking). Weekly "counter-evidence for currently-tracked candidates" section. Confidence gate loosens to MEDIUM with human-in-the-loop borderline review. DSPy optimization pass using accumulated run-log corpus.

### Phase 6: Action Interactivity (weeks 15–16)
Telegram 2-way (`ask_user`). Google Calendar (Duke EAP target, vigabatrin washout, BMC appointments). Booking/Kiwi suggestion-only behind manual approval. Bilingual support (Georgian + English side-by-side for urgent tier). Timezone clarity (Tbilisi + Boston on every deadline).

### Phase 7: Visualization — Viewer (weeks 17–19)
Highest-PHI-risk surface. NiiVue + R3F 9.6.x stable + drag-drop NIfTI via `File`/`FileSystemFileHandle`. DICOM via dcm2niix.wasm. CSP `connect-src 'self' blob: data:`. Production build strips console.log + disables source maps. Viewer pre-commit hook. atlas-mcp + niivue-mcp wired (region IDs only — never voxels). Quarterly red-team network-tab review.

### Phase 8: Visualization — Segmentation (weeks 20–22)
Family-local Docker only. FastSurfer-LIT (cyst inpainting) → BIBSnet (neonatal — Aleksandra's age fits training band) → BONBID-HIE → nii2mesh. bonbid-mcp wraps the runner, accepts job descriptors not voxels. 3D anatomical shells with atlas overlay. Segmentation feeds clinician-shareable exports only.

### Phase 9: Visualization — Simulation + 3D Print (weeks 23+)
Polish. TVB Docker via tvb-mcp. brain2print STL export with meshlab/pymeshfix watertight pass.

### Phase Ordering Rationale

- **Foundation before everything** — Pitfalls 9 + 13 are catastrophically expensive to retrofit; budget ceiling is non-negotiable.
- **Perception before Memory** — validating scrape coverage prevents wasted Qdrant disk and AuraDB Free node-count (hard caps within 6–12 months).
- **Memory before Cognition** — citation tuple schema + provenance write contract must exist before any agent writes a claim. All three CATASTROPHIC pitfalls have a Memory-half landing here.
- **Cognition (min) before Cognition (full)** — two agents end-to-end prove the loop; five in parallel hides which one breaks.
- **Action (digest) between the two Cognition phases** — family seeing first value within ~11 weeks is the structural test of the build order.
- **Visualization last** — without Memory + Cognition it shows a brain but says nothing useful; it's the only PHI surface; neuroplasticity-window argument front-loads research throughput.

### Research Flags

**Needs deeper research during planning:** Phase 2 (Graphiti GC + AuraDB ceiling), Phase 5 (Adaptive GoT vendoring + DSPy eval set), Phase 7 (FreeBrowse licensing), Phase 8 (joined neonatal pipeline on Aleksandra's actual MRI), Phase 9 (TVB-C++ Docker + watertight meshing).
**Standard patterns (skip deep research):** Phases 0, 1, 3, 4, 6.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against official releases as of May 2026. MEDIUM only on TVB-C++ Docker and Adaptive GoT MCP project health. |
| Features | HIGH | Off-the-shelf stress test passes for every P1; v1 acceptance test is concrete and measurable. MEDIUM on neonatal-pipeline timeline. |
| Architecture | HIGH | 5-layer canonical for 2026; LightRAG + Graphiti + Qdrant + Supabase ledger pattern well-documented. |
| Pitfalls | HIGH | Cited primary literature 2025–2026; engineering pitfalls cite vendor docs + community post-mortems. |

**Overall confidence:** HIGH

### Gaps to Address

- AuraDB Free node ceiling (200K vs 50K) — pull live limit from Aura console day 1 of Phase 2.
- Adaptive GoT MCP single-maintainer risk — vendor source at Phase 5; DSPy-Tree-of-Thoughts fallback ready.
- FreeBrowse fork licensing + FastAPI-stripping — legal review before Phase 7.
- NCBI E-utilities `api_key` registration — Phase 0 task.
- DSPy training corpus accumulates Phase 3 → Phase 5; not a Phase-5 starting condition.
- No published BONBID-HIE benchmark on cystic encephalomalacia with preserved brainstem — Phase 8 includes clinician review.
- Vigabatrin washout duration is patient-specific — Phase 6 calendar reads from a family-editable field.
- Telegram BAA gap — OK family-to-family; clinician PHI routes through Prism MCP (Phase-6.5 if needed).

## Sources

Primary research files: `.planning/research/STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md`. Project context: `.planning/PROJECT.md`. External: Anthropic deprecation calendar (Sonnet 4 retire 2026-06-15), Crawl4AI 0.8.6 March 2026 supply-chain fix, CrewAI 1.14.5a5 (May 12 2026), Graphiti + Neo4j blog Feb 2026, LightRAG 1.4.16, mem0 April 2026, FastMCP 3.2.4, DSPy 3.2.1, RAGFlow 0.17, NiiVue 0.49 + `@niivue/nvreact` March 2026, FastSurfer-LIT (Imaging Neuroscience 2025), BIBSnet (DCAN-Labs), BONBID-HIE (Scientific Data 2024), NCBI Technical Bulletin Jul/Aug 2025, Retraction Watch May 2026, 2024 JCO LLM off-label analysis.

---
*Research synthesized: 2026-05-13*
*Ready for roadmap: yes*
