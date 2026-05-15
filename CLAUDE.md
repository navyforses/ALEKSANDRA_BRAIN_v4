# CLAUDE.md
# ALEKSANDRA_BRAIN — პროექტის ტვინი

> ეს ფაილი Claude Code-ს აძლევს პროექტის სრულ კონტექსტს.
> ყოველ სესიაში ავტომატურად იკითხება.
> არასოდეს დაიწყო ნულიდან — ყოველთვის იცი ყველაფერი.

---

## პროექტი

ALEKSANDRA_BRAIN v4.0 — მუდმივად მოქმედი AI სისტემა რომელიც ეძებს, აანალიზებს და აღმოაჩენს მკურნალობის შესაძლებლობებს ალექსანდრა ჯინჭარაძისთვის (მძიმე HIE, ცისტური ენცეფალომალაცია, შენარჩუნებული ტვინის ღერო).

ცენტრალური პრობლემა: ჯანდაცვის სისტემა არ არის აგებული იშვიათი/მძიმე პედიატრიული დიაგნოზის მქონე ოჯახების საჭიროებებზე — არცერთი ინსტიტუცია არ აერთიანებს კვლევას, მკურნალობას, ნავიგაციას და ვიზუალიზაციას ერთ სისტემაში.

## არქიტექტურა

5 ფენა: PERCEPTION → MEMORY → COGNITION → VISUALIZATION → ACTION

### PERCEPTION (თვალები)
- Crawl4AI (64K⭐, primary scraping, უფასო, ლოკალური)
- Firecrawl MCP (6K⭐, ფასიანი fallback)
- Browser Use (89K⭐, paywall bypass)
- RAGFlow (78K⭐, PDF→chunks→entities)
- n8n (185K⭐, cron ყოველ 6სთ) + n8n-MCP (18K⭐)

### MEMORY (მეხსიერება)
- Neo4j + Graphiti (25K⭐, temporal knowledge graph, confidence decay)
- Qdrant (30K⭐, vector search, fastembed ლოკალური)
- Supabase (PostgreSQL, 10 tables, metadata)
- LightRAG (34K⭐, graph+vector ერთ query-ში)
- mem0 (53K⭐, 5 აგენტის shared memory)
- Hindsight (10K⭐, self-improving memory)
- Prism MCP (HIPAA-hardened)
- Cloudflare R2/KV (storage/cache)

### COGNITION (აზროვნება)
- CrewAI (49K⭐, 5 აგენტი):
  1. Spider — Research Paper Hunter
  2. Analyzer — Evidence Quality Assessor
  3. Hypothesis — Cross-Disease Pattern Finder
  4. Repurposing — Drug Discovery Specialist
  5. Communicator — Family Liaison
- Claude API Sonnet 4
- Adaptive GoT MCP (hypothesis pipeline)
- DSPy (34K⭐, prompt optimization)
- Vercel AI SDK (23K⭐, streaming + tool calling)

### VISUALIZATION (ხედვა)
- NiiVue (@niivue/nvreact) — სამედიცინო MRI viewer
- React Three Fiber v10 — 3D ანატომიური shells
- UI scaffold: fork freesurfer/freebrowse
- Neonatal pipeline: FastSurfer+LIT → BIBSnet → BONBID-HIE → nii2mesh
- TVB Docker — ტვინის სიმულაცია
- brain2print — 3D print STL

### ACTION (მოქმედება)
- Telegram 2-way (push + ask_user)
- Gmail MCP
- Notion MCP (4.3K⭐, family knowledge base)
- Google Calendar
- Booking.com + Kiwi.com (Duke logistics)

## MCP არსენალი: 52 სულ
- 23 Claude.ai registry
- 19 GitHub self-hosted
- 5 AI Pulse Georgia (FastMCP, Crawl4AI RAG, Prism, Draw.io, Perplexity)
- 5 custom world-first (niivue-mcp, bonbid-mcp, tvb-mcp, atlas-mcp, repurpose-mcp)

Custom MCP = FastMCP-ით (24K⭐, Python decorators)

## Tech Stack
- Frontend: Next.js 14, Tailwind, shadcn/ui, Vercel
- Backend: CrewAI, n8n (Railway), Supabase Edge Functions, CF Workers
- Data: Neo4j AuraDB, Qdrant Docker, Supabase PostgreSQL, CF R2/KV
- AI: Claude Sonnet 4, DSPy, mem0, LightRAG
- 3D: NiiVue, R3F, drei, postprocessing

## ფაილების სტრუქტურა
```
/agents/         ← CrewAI agents (spider, analyzer, hypothesis, repurposing, communicator)
/mcp/            ← custom MCP servers (FastMCP)
/viewer/         ← Next.js 3D brain viewer (fork freebrowse)
/workflows/      ← n8n workflow JSONs
/scripts/        ← migration, setup, test scripts
/docs/           ← documentation
```

## პაციენტი
ალექსანდრა ჯინჭარაძე, დაბ. 28.08.2025, თბილისი
დიაგნოზი: მძიმე HIE, diffuse cystic encephalomalacia, preserved brainstem
ოჯახი: ბოსტონი, MA (Philoxenia House, Jamaica Plain)
BMC MRN: 7616818

## აქტიური პროგრამები
- Duke EAP cord blood → ~July 2026 (vigabatrin washout)
- Wisconsin Virtual A2 → active (Jeanette Heitman)
- BMC primary care → Dr. Jack Maypole
- BMC neurology → Dr. Hien, Dr. August

## პრინციპები
- „Unknown potential" — არა „limited outcomes"
- MRI სტრუქტურული დაზიანება ≠ ფუნქციური ლიმიტი
- 0-2 წელი = ნეიროპლასტიკურობის პიკი
- ფაქტი არ გამოიგონო. წყარო ვერ მოიძებნა → თქვი
- MRI = client-side only. არასოდეს სერვერზე
- ყველა გადაწყვეტილებას რეალური ექიმი იღებს

## მიმდინარე ეტაპი
მიმართულება I: აღქმა (Perception) — **დახურულია 2026-05-15** (10/10 PASS — see docs/PHASE_1_EXIT_REPORT.md)
შემდეგი: მიმართულება II (Memory) — RAGFlow chunking + Qdrant embeddings + Graphiti entity extraction

## ენა
- კოდი: ინგლისურად
- კომენტარები: ინგლისურად
- docs: ქართულად + ინგლისურად
- commits: ინგლისურად, conventional commits (feat:, fix:, docs:)

## ხარჯი
MVP: $20-30/თვე | Full: $120/თვე

<!-- GSD:project-start source:PROJECT.md -->
## Project

**ALEKSANDRA_BRAIN**

A continuously-running AI research system that hunts, evaluates, and surfaces treatment opportunities for Aleksandra Jincharadze — a child with severe HIE (hypoxic-ischemic encephalopathy), diffuse cystic encephalomalacia, and preserved brainstem. It unifies literature mining, multi-agent reasoning, a temporal medical knowledge graph, and a client-side 3D MRI viewer into a single family-operated cockpit, then pushes findings to caregivers via Telegram, Gmail, and Notion. The aim is to compress the gap between "the family searches" and "the clinician decides."

**Core Value:** **Never miss a credible treatment lead for Aleksandra.** Every other capability — viewers, dashboards, agents — exists to serve this single outcome. If the system goes offline, what must keep working is the literature pipeline and the human-readable digest.

### Constraints

- **Privacy**: MRI / DICOM data is client-side only — Never persisted on a server, never sent to a third-party API
- **Budget**: $20–30/month MVP, $120/month full — Family-funded; any line item above this needs explicit justification
- **Tech stack**: Next.js 14 + Tailwind + shadcn/ui on Vercel; CrewAI + n8n on Railway; Supabase Postgres; Neo4j AuraDB; Qdrant Docker; CF R2/KV — Already partially provisioned; switching costs are real
- **Source integrity**: Every surfaced fact carries provenance — Required by the "do not fabricate" principle
- **AI**: Claude Sonnet 4 is the default reasoning model; DSPy for prompt optimization; mem0 for shared agent memory — Stack converged on Anthropic + OSS tooling
- **Frontend 3D**: NiiVue + React Three Fiber v10 + drei + postprocessing; fork freesurfer/freebrowse as UI scaffold — Avoids reinventing a medical-grade viewer
- **Decision authority**: A clinician makes every medical decision — The system surfaces, ranks, and explains; it does not prescribe
- **Compliance posture**: HIPAA-aware (Prism MCP HIPAA-hardened) even though we're not a covered entity — Future-proofing against any external clinician access
- **Time pressure**: Neuroplasticity window 0–2 years — Phase ordering must front-load research throughput over polish
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Executive Stance
## Recommended Stack
### PERCEPTION Layer — Acquisition & Ingestion
| Technology | Version (verified 2026-05) | Purpose | Why for THIS project |
|---|---|---|---|
| **Crawl4AI** | 0.8.6 (Mar 2026; security hotfix replacing litellm) | Primary OSS web scraper, LLM-friendly markdown extraction, deep-crawl with crash recovery | Apache-2.0, locally runnable, zero per-call cost. v0.8 added crash recovery + prefetch (5–10x faster URL discovery) — critical for a 6-hour cron over 50+ sources. CVSS 10.0 Docker-API vuln was fixed in 0.8.0; **must be ≥0.8.6** because of the litellm supply-chain attack of Mar 24, 2026. |
| **Firecrawl** (cloud + MCP) | Hobby $16/mo, 3K credits | Paid fallback when Crawl4AI fails (JS-heavy, anti-bot sites) | Credit model: ~7 credits/page for crawl+extract. Hobby tier ≈ 400 enriched pages/mo — fits the $20–30 MVP ceiling. The official Firecrawl MCP server was updated 2026-05-08 — current. |
| **Browser Use** | SDK 3.0.x (Feb 2026 rewrite) | Headless-browser agent for paywall bypass and form-based interactions (PubMed full-text login, ClinicalTrials filters) | Necessary for sites Crawl4AI cannot reach. v3.0 is a clean break with `client.run()` API. **Verify** that litellm was removed from core (it was, post Mar-2026 supply-chain incident). |
| **RAGFlow** | ≥ 0.17.x (Apr 2026 release standardized REST APIs) | PDF → chunks → entities pipeline for research papers | v0.17 decoupled PDF parsing from chunking, exposing DeepDoc / Naive / **MinerU / Docling / OpenDataLoader**. Use **Docling** or **MinerU** as default; reserve DeepDoc for scanned/OCR PDFs. Self-host on Railway. |
| **n8n** (self-hosted, Community edition) | 2.x (May 2026 weekly bugfix cadence) | Cron orchestration, source-monitor workflows, Telegram/Gmail webhook router | Community edition is free with unlimited executions on self-host. Already pegged in the CLAUDE.md stack — keep. Run on Railway ≈ $5/mo. |
| **n8n-MCP** | Current (community) | Exposes n8n workflows as MCP tools | Lets Claude trigger workflows directly. Confidence MEDIUM (smaller project, fewer 2026 release datapoints). |
### MEMORY Layer — Knowledge & Retrieval
| Component | Version (verified 2026-05) | Owns | Why this assignment |
|---|---|---|---|
| **Neo4j AuraDB Free** | Aura Free tier ($0; 200K nodes / 400K rels per FAQ — some inconsistency vs. product page showing 50K/175K, plan for the lower number) | Temporal medical knowledge graph + Adaptive GoT backing store | Free tier covers MVP scale. AuraDB Free now includes auto-pause/resume + Aura Console + Bloom basic. Hosted; no Docker maintenance. |
| **Graphiti** (getzep/graphiti, OSS) | Active dev, repo updated Feb 21, 2026 | Temporal-aware writes to Neo4j with bi-temporal model, point-in-time queries, confidence decay | Built explicitly for "facts that change over time" — exactly the medical-evidence use case. Works with Neo4j 5.26 / FalkorDB / Kuzu / Neptune. Open-source; no per-fact cost. |
| **Qdrant** | Latest stable (1.x; April 2026 Cloud added GPU indexing + Multi-AZ — irrelevant for MVP, you self-host) | Vector search over papers, chunks, and entities | Run Qdrant Docker on Railway ≈ $5/mo. Use **fastembed** locally for free embeddings (BGE-small or jina-v3 — both work in fastembed). Avoids per-embedding API costs. |
| **Supabase** (PostgreSQL + Edge Functions) | Free tier (500 MB DB, 500K Edge invocations/mo, 2-active-project limit, 1-week-idle pause) | Relational metadata: papers, agents, audit log, decision provenance, user preferences | Free tier covers MVP. **Beware the 1-week idle-pause** — n8n cron pinging Supabase weekly counts as activity, so it stays warm. |
| **LightRAG** (HKUDS) | v1.4.16 (May 7, 2026) | **Single combined graph+vector query** for the Spider/Analyzer agents | Replaces hand-rolled "query Neo4j + query Qdrant + merge" logic. May 2026 release adds OpenSearch backend + setup wizard + Langfuse tracing + RAGAS evaluation. EMNLP 2025 paper. |
| **mem0** | 2026 token-efficient algorithm (April 2026 release; 91.6% accuracy at <7K tokens, +29.6 pts on temporal queries) | **Shared memory across the 5 CrewAI agents** (Spider ↔ Analyzer ↔ Hypothesis ↔ Repurposing ↔ Communicator) | This is mem0's exact sweet spot. April 2026 algorithm is dramatically better on temporal/multi-hop reasoning — both directly relevant. **OpenMemory MCP** lets the same memory store also serve Claude Desktop / Cursor. |
| **Cloudflare R2** | Free tier (10 GB storage, 1M Class-A ops, 10M Class-B ops/mo, **zero egress**) | Raw artifacts (cached HTML, PDFs, scraped JSON) | Egress-free is the killer feature — your Crawl4AI nightly run can re-read freely. |
| **Cloudflare Workers KV** | Free tier (limited, included with Free Workers plan) | Hot cache for n8n workflow state, dedup keys, source URLs seen | Daily-reset limits but free. Pair with R2 for cold artifacts. |
- **Hindsight** (self-improving memory): brings real value once you have **months** of agent traces to learn from. Adopt at Phase 3+, not MVP.
- **Prism MCP** (HIPAA-hardened on-device memory with `prism-coder:7b`): adopt **when a clinician needs read access**, not before. Until then, your PHI surface (MRI) is client-side-only anyway and PHI never enters server memory. Bringing Prism in early adds an on-device LLM dependency you don't need yet.
### COGNITION Layer — Reasoning & Agents
| Technology | Version (verified 2026-05) | Purpose | Why for THIS project |
|---|---|---|---|
| **CrewAI** | 1.14.5a5 (May 12, 2026 pre-release); 1.x stable ≥ 1.1.0 | 5-agent role-based crew: Spider, Analyzer, Hypothesis, Repurposing, Communicator | Role/goal/backstory primitives are the cleanest fit for the 5 named agents. CrewAI has the **fastest time-to-working-demo** (2–3 engineer-days per multiple 2026 framework comparisons). Active development; AutoGen is in Microsoft maintenance mode as of 2026. |
| **Claude Sonnet 4.5** (`claude-sonnet-4-5`) | Active; retirement ≥ Sep 29, 2026 | **Default reasoning model** for all agents | $3 in / $15 out per 1M tokens. **Replaces Sonnet 4** which deprecates 2026-04-14 and retires 2026-06-15 — CLAUDE.md says "Sonnet 4," this must change. |
| **Claude Sonnet 4.6** (`claude-sonnet-4-6`) | Active; retirement ≥ Feb 17, 2027 | Reasoning escalation for Hypothesis agent on hard cases | Same pricing. Use 4.5 by default; gate 4.6 calls behind a "complexity ≥ N" check to stay inside the cost ceiling. |
| **DSPy** | 3.2.1 (May 5, 2026) | Prompt optimization for the 5 agent roles, signature compilation | DSPy 3.x stabilized async streaming + per-call `caching=False`. `BetterTogether` chains prompt-optimize → fine-tune → prompt-optimize. Use this to tune each agent's signatures against a small held-out set of HIE/repurposing queries. |
| **Vercel AI SDK** | v5.x (2026) | Streaming + tool calling in the Next.js viewer/dashboard | AI SDK 5 brought type-safe `UIMessage`, custom `tool-<NAME>` part identifiers, data parts — exactly what a streaming agent UI needs. Free, OSS, MIT. |
| **Adaptive Graph of Thoughts MCP** | SaptaDey/Adaptive-Graph-of-Thoughts-MCP-server (active 2025–2026; based on the AGoT paper, arXiv 2502.05078) | Hypothesis decomposition → DAG of reasoning steps backed by Neo4j | Designed explicitly for **scientific reasoning**, with tools `scientific_reasoning_query`, `analyze_research_hypothesis`, `explore_scientific_relationships`, `validate_scientific_claims`. The fit for the Hypothesis agent is uncanny. MEDIUM confidence — single-maintainer project; pin a commit, vendor the source. |
| **FastMCP** | 3.2.4 stable; 3.0 released Jan 19, 2026 with versioning + OpenTelemetry + granular auth | Build 5 custom MCPs (niivue-mcp, bonbid-mcp, tvb-mcp, atlas-mcp, repurpose-mcp) | 70% of MCP servers use FastMCP. Decorators `@mcp.tool() / @mcp.resource() / @mcp.prompt()` give the shortest path from Python function to MCP tool. 3.0+ adds OpenTelemetry — useful for the audit-trail requirement. |
### VISUALIZATION Layer — Browser-side Imaging & 3D
| Technology | Version (verified 2026-05) | Purpose | Why for THIS project |
|---|---|---|---|
| **NiiVue** (`@niivue/niivue`) | 0.49.0 (April 2026, monorepo); v1.0 RC in dev with WebGPU + smaller bundles | WebGL2 medical image viewer (30+ volume/mesh formats) | The de facto OSS web NIfTI/DICOM viewer. **Client-side-only** — patient MRI never reaches a server. Active maintainers; v1 RC is the migration target. |
| **`@niivue/nvreact`** | Active, repo updated 2026-03-26 | React bindings for NiiVue with multi-instance scenes, declarative hooks, standalone viewer component | This is the right binding (not the older `niivue-react`). Maintained by the NiiVue org. |
| **React Three Fiber** | **9.6.1 (stable, late April/early May 2026)** — NOT v10 | React renderer for Three.js anatomical shells around the NiiVue viewer | **Important deviation from CLAUDE.md:** v10 is **still alpha** as of May 2026 (`@react-three/fiber@alpha`). Ship on 9.6.x; revisit v10 once it hits stable (it adds WebGPURenderer + new scheduler + first-class TSL + Drei 11). For an MVP you want stable. |
| **@react-three/drei** | Stable companion to R3F 9.x | Premade R3F helpers (Environment, OrbitControls, etc.) | Use the version matching R3F 9.x. Drei 11 is the alpha that targets R3F v10. |
| **@react-three/postprocessing** | Stable companion to R3F 9.x | Visual polish for anatomical shells | Use the version matching R3F 9.x. |
| **FreeBrowse** (fork) | Current React + TypeScript + Vite + Tailwind 4 + Radix UI + FastAPI rewrite (the original v1 is on a branch) | UI scaffold to fork as the viewer chrome | Funded by Gates Ventures, implemented by Zühlke. Repo `freesurfer/freebrowse`. **Caveat:** modern FreeBrowse includes a **FastAPI server** — if you fork, **strip the FastAPI half** so PHI stays in the browser, per your privacy constraint. |
| **FastSurfer + LIT** | FastSurfer-LIT (Imaging Neuroscience 2025) | Whole-brain segmentation with lesion inpainting (handles cysts, cavities — Aleksandra's case profile) | DDPM-based lesion inpainting outperforms prior approaches on N=100 simulated tumors and N=39 synthetic MS lesions. **Exactly the right tool** for cystic encephalomalacia, which breaks naive FreeSurfer/FastSurfer pipelines. Run as a one-shot batch (Docker), not in-app. |
| **BIBSnet** | DCAN-Labs/BIBSnet (active; segmentations are FreeSurfer-compatible) | Neonatal/infant brain segmentation (0–8 months) | **600× faster than JLF**, no skull-stripping required. Trained on a large 0–8 month dataset. **Aleksandra's age band (0–9 months as of May 2026) is exactly the training distribution.** Run as a one-shot Docker pipeline. |
| **BONBID-HIE** | Dataset + 2023 MICCAI challenge methods (BONBID-HIE 2024 challenge results published 2025) | HIE-specific lesion segmentation reference + benchmark | 133 patients, ADC + ZADC maps + binary lesion masks. >50% of patients have lesions <1% of brain volume — exactly why off-the-shelf segmenters fail for HIE. Use the **2024 challenge top-3 architectures** as a reference for the lesion-segmentation MCP. |
| **nii2mesh** | neurolabusc/nii2mesh (active) | NIfTI → STL/OBJ via marching cubes for the 3D anatomical shells | Caveat: nii2mesh outputs are not watertight after simplification — for **on-screen viewing** this is fine; for **3D printing** (brain2print) run `meshlab`/`pymeshfix` afterward. |
| **TheVirtualBrain (TVB)** Docker | TVB 2.9 + new TVB-C++ backend (Wiley 2026) | Whole-brain simulation (post-MVP capability for the Hypothesis agent) | Brain Simulation Section publishes Docker on DockerHub. TVB-C++ is the new fast backend for large-scale runs. **Deferable to Phase 3+** — not needed for the literature-mining MVP. |
| **brain2print / 3D print pipeline** | Community pipelines (nii2mesh + meshlab + slicer-CLI) | STL output for physical brain models for the family / clinicians | Nice-to-have; deferable. |
### ACTION Layer — Outbound Channels
| Technology | Version (verified 2026-05) | Purpose | Why for THIS project |
|---|---|---|---|
| **Telegram Bot API** | Stable | 2-way family channel: push findings + `ask_user` clarifications | Already used daily by the family. Bot API is free. n8n has a first-class Telegram node. |
| **Gmail MCP** | Active community/Anthropic ecosystem | Daily/weekly digest emails | Pairs with the Communicator agent. |
| **Notion MCP** | Active (Anthropic registry) | Family-facing knowledge base | Notion API is free for personal/small-team use. |
| **Google Calendar API** | Stable | Treatment-timeline events (vigabatrin washout, Duke EAP target, BMC appointments) | Free for the workload at hand. |
| **Booking.com + Kiwi.com APIs** (or scraping via Crawl4AI) | — | Duke EAP travel logistics (Tbilisi ↔ Boston ↔ Durham NC) | If APIs require partner status, fall back to Crawl4AI of price-comparison aggregators. |
### Front-end & Hosting (already pegged; verified)
| Technology | Version | Purpose | Notes |
|---|---|---|---|
| **Next.js** | 14.x (or 15 if appetite for App Router updates) | Viewer + dashboard | Already in CLAUDE.md. Vercel deploys for free at this scale. |
| **Tailwind CSS** | 3.x stable (Tailwind 4 in FreeBrowse fork is fine; both work) | Styling | — |
| **shadcn/ui** | Latest CLI | Components | — |
| **Vercel** (Hobby plan) | Free | Frontend hosting | Hobby tier is more than enough for one viewer. |
| **Railway** | Pay-as-you-go (~$5/mo per service typical) | n8n + Qdrant Docker + RAGFlow + CrewAI worker | Comfortably inside $20–30 MVP ceiling for 3–4 small services. |
## Recommended MVP-vs-Full Cost Breakdown
| Tier | Component cost | Total |
|---|---|---|
| **MVP ($20–30/mo target)** | Vercel Hobby $0 + AuraDB Free $0 + Supabase Free $0 + CF R2/KV Free $0 + Railway ~$15 (n8n + Qdrant + 1 worker) + Firecrawl Hobby $16 + Claude API metered (start with $5/mo cap) | **~$36/mo** at the cap (slightly over the floor; well under $120). Drop Firecrawl Hobby for first month to hit $20. |
| **Full ($120/mo target)** | + Railway expansion to ~$30 (RAGFlow, additional worker) + Firecrawl Standard credits as needed + Claude API headroom ~$40 + AuraDB Professional only if you grow beyond Free | **~$110–120/mo** sustainable. |
## Installation (canonical bootstrap)
# Python / agents / MCP servers (uv recommended over pip in 2026)
# RAGFlow → docker-compose (pin a tag ≥ v0.17)
# n8n → docker run -d --name n8n -p 5678:5678 n8nio/n8n:latest
# Qdrant → docker run -p 6333:6333 qdrant/qdrant:latest
# Frontend
# Neuroimaging pipeline (run as one-shot Docker containers; not in-app)
# TVB image from thevirtualbrain DockerHub when you reach Phase 3
## Alternatives Considered
| Recommended | Alternative | When to switch |
|---|---|---|
| **CrewAI** | **LangGraph** | If you need durable long-running workflows with first-class human-in-the-loop checkpoints and LangSmith tracing. LangGraph is the most "battle-tested for production" framework per 2026 comparisons — but it is harder to model the 5 named roles cleanly. Switch only if CrewAI hits a wall on observability. |
| **CrewAI** | **AutoGen** | Don't. Microsoft has moved AutoGen to maintenance mode in favor of Microsoft Agent Framework. Net negative for a single-patient project. |
| **CrewAI** | **OpenAI Swarm / Agents SDK** | Tied to OpenAI ecosystem; your stack is Anthropic-first. Skip. |
| **Neo4j + Graphiti** | **Zep Cloud** (managed Graphiti) | If you outgrow the Aura Free 200K-node ceiling and don't want to operate Neo4j. Zep is the commercial host for Graphiti. |
| **Qdrant** | **pgvector on Supabase** | If you want one fewer service. Trade-off: pgvector loses on hybrid + sparse + payload filtering at the throughput Crawl4AI generates. Keep Qdrant. |
| **LightRAG** | **Roll your own (Neo4j query + Qdrant query + merge)** | Only if LightRAG's defaults don't match your retrieval shape. LightRAG is OSS; you can fork. |
| **RAGFlow Docling parser** | **DeepDoc (RAGFlow default)** | Use DeepDoc for **scanned** PDFs (OCR-heavy). Docling/MinerU wins for born-digital research papers. |
| **Crawl4AI** | **Firecrawl as primary** | Don't — Firecrawl's credit model burns the $20 MVP budget on ~3K pages/mo. Keep Firecrawl as fallback. |
| **Browser Use** | **Playwright direct** | If your paywall bypass becomes site-specific enough that a custom Playwright script is simpler. Otherwise Browser Use is faster to author. |
| **Vercel AI SDK** | **`@anthropic-ai/sdk` directly** | Use the raw Anthropic SDK in the **backend** (CrewAI workers), AI SDK in the **frontend** (streaming UI). Both, not either-or. |
| **R3F 9.x stable** | **R3F 10 alpha** | Only when v10 hits stable. WebGPU is compelling but not blocker-relevant for this app. |
| **NiiVue monorepo** | **niivue-react** (older) | Don't — `niivue-react` is the older binding. Use `@niivue/nvreact`. |
| **FastSurfer-LIT for cyst handling** | **Raw FreeSurfer** | Don't — FreeSurfer's surface reconstruction fails badly in the presence of large cystic cavities. LIT is purpose-built for this. |
| **BIBSnet for neonatal segmentation** | **Adult-trained FreeSurfer/FastSurfer** | Don't — adult-brain models systematically mis-segment infant brains (very different tissue contrast pre-myelination). BIBSnet was built precisely for the 0–8 month band. |
| **Adaptive GoT MCP** | **Tree-of-Thoughts via DSPy / hand-rolled** | If the AGoT MCP project goes unmaintained, port the DAG reasoning into DSPy modules. Vendor the AGoT source now to de-risk. |
## What NOT to Use
| Avoid | Why | Use Instead |
|---|---|---|
| **Claude Sonnet 4 (`claude-sonnet-4-20250514`)** | Deprecated 2026-04-14; **retires 2026-06-15** — every call after that date errors | Claude Sonnet 4.5 (default), Sonnet 4.6 (hard cases). Same $3/$15 pricing. |
| **Server-side DICOM / NIfTI storage** | HIPAA blast radius; explicit out-of-scope per PROJECT.md | Client-side NiiVue + local-only file picker. Strip the FastAPI half if you fork FreeBrowse. |
| **Raw LangChain as the agent framework** | Imperative chains with leaky abstractions; the 5 named roles map awkwardly to LangChain primitives | CrewAI for orchestration; you may import individual LangChain integrations for specific tools but do not let LangChain own the loop. |
| **OpenAI Swarm / OpenAI Agents SDK as primary** | Ties you to OpenAI; your model strategy is Anthropic-first | CrewAI + Claude Sonnet 4.5/4.6. |
| **AutoGen** | Microsoft moved it to maintenance mode in 2026 | CrewAI. |
| **R3F v10 alpha in production** | Still alpha as of May 2026 | R3F 9.6.x stable; revisit v10 at GA. |
| **`niivue-react`** (older repo) | Older, less maintained binding | `@niivue/nvreact`. |
| **DeepDoc as the only PDF parser** | OCR-first; slow and lossy on born-digital papers | Use RAGFlow 0.17+ with Docling or MinerU as the default parser; DeepDoc only for scanned PDFs. |
| **Pinecone / Weaviate Cloud / Astra** | Per-month cost adds $50–$200+; you have Qdrant + free tier | Qdrant Docker on Railway. |
| **Notion as the agent DB** | Slow, rate-limited; not designed for write-heavy agent operations | Notion is the **read** surface for the family. Supabase Postgres + Neo4j is where agents write. |
| **Hugging Face Inference Endpoints for embeddings** | Per-call cost beats the budget | `fastembed` (BGE-small or jina-v3) locally inside Qdrant indexer. |
| **Litellm versions 1.82.7 / 1.82.8** | **Backdoored** on March 24, 2026 (supply-chain attack) — affected Crawl4AI and Browser Use, both have patched | Use only litellm versions Crawl4AI ≥0.8.6 and Browser Use ≥3.0 explicitly pin (they removed litellm from core deps or replaced it with `unclecode-litellm`). |
| **`raw HTTP scraping of PubMed/NCBI without compliance with NCBI E-Utilities rate limits`** | NCBI throttles aggressively; you'll get IP-banned | Use **NCBI E-Utilities** with an API key (free), rate-limited to 10 req/sec. Reserve Crawl4AI for non-NCBI sources. |
| **Storing raw clinician identifiers in Supabase without RLS** | Even non-PHI identifiers (Dr. names, MRN) deserve isolation | Use Supabase Row Level Security + service-role-only writes from n8n. |
| **All four memory layers (Graphiti + LightRAG + mem0 + Hindsight + Prism) in MVP** | Operational overhead + ambiguous source-of-truth | MVP = Graphiti (graph) + Qdrant via LightRAG (retrieval) + mem0 (agent memory). Defer Hindsight and Prism. |
## Stack Patterns by Variant
- Lean hard on Crawl4AI + n8n + RAGFlow + Qdrant + Graphiti.
- CrewAI Spider + Analyzer agents only. Hypothesis/Repurposing/Communicator can stub.
- Defer the entire VISUALIZATION layer.
- Lean on NiiVue + R3F 9.x + nvreact + FreeBrowse fork (frontend-only mode) + nii2mesh artifacts pre-baked by FastSurfer-LIT + BIBSnet.
- Skip CrewAI; agents are async.
- Adaptive GoT MCP + DSPy-optimized Hypothesis agent + LightRAG + Claude Sonnet 4.6 (with hard budget caps).
- TVB Docker becomes relevant here, not before.
- Drop Firecrawl Hobby ($16/mo savings); accept that ~10% of sources will be unscrapable until you re-add.
- Run n8n + Qdrant on a single Railway service ($5/mo).
- Cap Claude API at $10/mo via Anthropic console budget.
## Version Compatibility Notes
| Component A | Compatible With | Notes |
|---|---|---|
| `@niivue/niivue ^0.49` | `@niivue/nvreact` current | The nvreact README pins the niivue version it depends on — match. |
| `@react-three/fiber ^9.6` | `@react-three/drei` 9-line, `three ^0.169` | Don't mix R3F 9 with Drei 11 — Drei 11 is the v10-alpha companion. |
| `crewai 1.x` | `mem0ai` current | CrewAI ships first-class mem0 integration. |
| `crawl4ai >= 0.8.6` | (post supply-chain patch) | Refuse to install `crawl4ai < 0.8.6` — security exposure. |
| `browser-use >= 3.0.x` | (post supply-chain patch) | Refuse `1.82.7` / `1.82.8` `litellm` builds. |
| `graphiti-core` | `Neo4j 5.26`, `FalkorDB 1.1.2`, `Kuzu 0.11.2`, AWS Neptune | Confirmed in repo docs Feb 2026. |
| `lightrag-hku 1.4.16` | Neo4j, MongoDB, OpenSearch, Qdrant | Multi-backend support added across 2025–2026 releases. |
| `fastmcp 3.x` | Python 3.10+ | 3.0 (Jan 2026) introduced versioning + auth; 3.2 is current stable. |
| `dspy 3.2.1` | `litellm` (now unbounded) | The 3.2.1 release explicitly removed the litellm upper bound. |
| `next 14` + `vercel ai sdk 5` + `react 18` | Stable | AI SDK 5 supports both React 18 and React 19. |
## Privacy / HIPAA Posture per Component
| Component | Touches patient data? | Posture |
|---|---|---|
| NiiVue + nvreact (browser) | **Yes — MRI** | Client-side only; files via `<input type="file">`. Never sent over the wire. ✅ |
| FreeBrowse fork | **Yes — MRI** if you keep FastAPI half | **Strip the FastAPI server** half. Keep the React + Vite frontend only. ✅ after fork. |
| FastSurfer + LIT, BIBSnet | **Yes — MRI** | Run on a **family-controlled machine** (laptop / local workstation), never in the cloud. Output artifacts (segmentation masks) are de-identified and can be cached in R2 if you choose. ✅ with discipline. |
| Neo4j + Graphiti | No PHI; only research-paper facts + project decisions | Aura Free is hosted in commercial cloud — fine because no PHI lives there. ✅ |
| Qdrant | No PHI; only paper embeddings | Self-hosted, Railway. ✅ |
| Supabase | Metadata only (paper IDs, agent runs, decisions) — **no PHI** | Enable RLS. Service-role keys never leave server. ✅ |
| RAGFlow | Public research papers — no PHI | Self-hosted on Railway. ✅ |
| Crawl4AI, Firecrawl, Browser Use | Public web — no PHI | ✅ |
| n8n | Workflow state — **no PHI** | Self-hosted. ✅ |
| Claude API | Prompts contain research content — **no PHI** | Anthropic offers zero-data-retention on Enterprise; the Hobby tier without a BAA still works because **no PHI ever enters the prompt**. ✅ by discipline. |
| mem0 / Mem0 SaaS | Agent-shared memory — **no PHI** by policy | If you use OpenMemory MCP (local-first), all storage is on-device. ✅ |
| Prism MCP (if/when adopted) | HIPAA-hardened on-device | The right tool **if** a clinician ever needs access; until then, deferred. ✅ |
| Telegram, Gmail, Notion, Google Calendar | Family-facing — **no PHI by policy** | Never auto-include MRI links or clinical numbers in messages. Communicator agent enforces the redaction. ✅ by discipline. |
## Open Issues & Things To Validate in Phase 1
## Sources
- [Crawl4AI GitHub releases](https://github.com/unclecode/crawl4ai/releases) and [v0.8.0 release notes](https://docs.crawl4ai.com/blog/releases/v0.8.0/) — confirmed v0.8.6 Mar 2026, litellm replacement
- [CrewAI changelog](https://docs.crewai.com/en/changelog), [CrewAI GitHub releases](https://github.com/crewAIInc/crewAI/releases), [CrewAI 1.1.0 release](https://community.crewai.com/t/new-release-crewai-1-1-0-is-out/7142) — confirmed 1.14.5a5 May 12 2026
- [Graphiti GitHub](https://github.com/getzep/graphiti), [Zep open source](https://www.getzep.com/product/open-source/) — confirmed Neo4j 5.26 / FalkorDB / Kuzu / Neptune support
- [FastMCP GitHub (jlowin)](https://github.com/jlowin/fastmcp), [fastmcp on PyPI](https://pypi.org/project/fastmcp/) — confirmed 3.0 release Jan 19 2026, 3.2.4 current
- [DSPy GitHub releases](https://github.com/stanfordnlp/dspy/releases), [DSPy site](https://dspy.ai/) — confirmed 3.2.1 May 5 2026
- [LightRAG GitHub](https://github.com/HKUDS/LightRAG), [lightrag-hku PyPI](https://pypi.org/project/lightrag-hku/) — confirmed v1.4.16 May 7 2026
- [mem0 product updates](https://docs.mem0.ai/changelog), [State of AI Agent Memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026) — April 2026 algorithm
- [RAGFlow release notes](https://ragflow.io/docs/release_notes), [Select PDF parser](https://ragflow.io/docs/select_pdf_parser) — confirmed v0.17 parser plug-ability
- [Browser Use changelog](https://browser-use.com/changelog), [Browser Use releases](https://github.com/browser-use/browser-use/releases) — confirmed 3.0 Feb 25 2026, litellm removal
- [n8n release notes](https://docs.n8n.io/release-notes/) — confirmed 2026 weekly cadence
- [Vercel AI SDK 5 blog](https://vercel.com/blog/ai-sdk-5), [AI SDK GitHub releases](https://github.com/vercel/ai/releases) — confirmed v5 features
- [NiiVue org GitHub](https://github.com/niivue), [`@niivue/niivue` npm](https://www.npmjs.com/package/@niivue/niivue/v/0.24.0), [API docs v0.57.0](https://niivue.github.io/niivue/devdocs/) — confirmed 0.49 monorepo + v1.0 RC in dev
- [React Three Fiber GitHub](https://github.com/pmndrs/react-three-fiber), [v10 alpha discussion](https://github.com/pmndrs/react-three-fiber/discussions/3665), [npm](https://www.npmjs.com/package/@react-three/fiber) — confirmed v10 alpha-only as of May 2026
- [FreeBrowse repo](https://github.com/freesurfer/freebrowse) — confirmed React + FastAPI rewrite
- [FastSurfer GitHub](https://github.com/Deep-MI/FastSurfer), [LIT repo](https://github.com/Deep-MI/LIT), [Imaging Neuroscience 2025 paper](https://direct.mit.edu/imag/article/doi/10.1162/imag_a_00446/127374/FastSurfer-LIT-Lesion-inpainting-tool-for-whole) — confirmed LIT capabilities
- [BIBSnet repo (DCAN-Labs)](https://github.com/DCAN-Labs/BIBSnet), [BIBSNet bioRxiv paper](https://www.biorxiv.org/content/10.1101/2023.03.22.533696v4.full) — confirmed 0–8 month coverage, 600× speedup
- [BONBID-HIE dataset Scientific Data paper](https://www.nature.com/articles/s41597-024-03986-7), [BONBID-HIE 2023 challenge IEEE](https://ieeexplore.ieee.org/document/11297440/) — confirmed 133-patient dataset, ZADC + lesion masks
- [nii2mesh GitHub](https://github.com/neurolabusc/nii2mesh) — confirmed marching-cubes, watertight caveats
- [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing), [Claude API pricing 2026 breakdown](https://www.cloudzero.com/blog/claude-api-pricing/) — confirmed Sonnet 4 deprecation 2026-04-14, retire 2026-06-15
- [Neo4j pricing](https://neo4j.com/pricing/) — confirmed Aura Free tier
- [Supabase pricing](https://supabase.com/pricing) and [Edge Functions limits](https://supabase.com/docs/guides/functions/limits) — confirmed free-tier ceilings
- [Cloudflare Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/), [R2 pricing](https://developers.cloudflare.com/r2/pricing/), [Workers KV pricing](https://developers.cloudflare.com/kv/platform/pricing/) — confirmed free tiers
- [Firecrawl MCP server repo](https://github.com/firecrawl/firecrawl-mcp-server), [Firecrawl pricing](https://www.firecrawl.dev/) — confirmed updated 2026-05-08, Hobby $16/mo
- [Adaptive GoT MCP server repo](https://github.com/SaptaDey/Adaptive-Graph-of-Thoughts-MCP-server), [AGoT arXiv 2502.05078](https://arxiv.org/pdf/2502.05078) — confirmed Neo4j-backed scientific reasoning DAG
- [Prism Coder repo](https://github.com/dcostenco/prism-coder) — confirmed HIPAA-hardened on-device design
- [TVB docs](https://docs.thevirtualbrain.org/), [TVB-C++ Wiley 2026](https://advanced.onlinelibrary.wiley.com/doi/10.1002/advs.202406440) — confirmed Docker availability and new C++ backend
- [CrewAI vs LangGraph vs AutoGen 2026 (DataCamp)](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen)
- [Best Multi-Agent Frameworks 2026 (Gurusup)](https://gurusup.com/blog/best-multi-agent-frameworks-2026)
- [Fountain City Agent Memory Systems Compared 2026](https://fountaincity.tech/resources/blog/agent-memory-knowledge-systems-compared/)
- [Firecrawl pricing breakdown 2026 (ScrapeGraph AI)](https://scrapegraphai.com/blog/firecrawl-pricing)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

| Skill | Description | Path |
|-------|-------------|------|
| cavecrew | > Decision guide for delegating to caveman-style subagents. Tells the main thread WHEN to spawn `cavecrew-investigator` (locate code), `cavecrew-builder` (1-2 file edit), or `cavecrew-reviewer` (diff review) instead of doing the work inline or using vanilla `Explore`. Subagent output is caveman-compressed so the tool-result injected back into main context is ~60% smaller — main context lasts longer across long sessions. Trigger: "delegate to subagent", "use cavecrew", "spawn investigator/builder/reviewer", "save context", "compressed agent output". | `.agents/skills/cavecrew/SKILL.md` |
| caveman | > Ultra-compressed communication mode. Cuts token usage ~75% by speaking like caveman while keeping full technical accuracy. Supports intensity levels: lite, full (default), ultra, wenyan-lite, wenyan-full, wenyan-ultra. Use when user says "caveman mode", "talk like caveman", "use caveman", "less tokens", "be brief", or invokes /caveman. Also auto-triggers when token efficiency is requested. | `.agents/skills/caveman/SKILL.md` |
| caveman-commit | > Ultra-compressed commit message generator. Cuts noise from commit messages while preserving intent and reasoning. Conventional Commits format. Subject ≤50 chars, body only when "why" isn't obvious. Use when user says "write a commit", "commit message", "generate commit", "/commit", or invokes /caveman-commit. Auto-triggers when staging changes. | `.agents/skills/caveman-commit/SKILL.md` |
| caveman-compress | > Compress natural language memory files (CLAUDE.md, todos, preferences) into caveman format to save input tokens. Preserves all technical substance, code, URLs, and structure. Compressed version overwrites the original file. Human-readable backup saved as FILE.original.md. Trigger: /caveman-compress FILEPATH or "compress memory file" | `.agents/skills/caveman-compress/SKILL.md` |
| caveman-help | > Quick-reference card for all caveman modes, skills, and commands. One-shot display, not a persistent mode. Trigger: /caveman-help, "caveman help", "what caveman commands", "how do I use caveman". | `.agents/skills/caveman-help/SKILL.md` |
| caveman-review | > Ultra-compressed code review comments. Cuts noise from PR feedback while preserving the actionable signal. Each comment is one line: location, problem, fix. Use when user says "review this PR", "code review", "review the diff", "/review", or invokes /caveman-review. Auto-triggers when reviewing pull requests. | `.agents/skills/caveman-review/SKILL.md` |
| caveman-stats | > Show real token usage and estimated savings for the current session. Reads directly from the Claude Code session log — no AI estimation. Triggers on /caveman-stats. Output is injected by the mode-tracker hook; the model itself does not compute the numbers. | `.agents/skills/caveman-stats/SKILL.md` |
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
