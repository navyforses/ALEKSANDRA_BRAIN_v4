# Architecture Research

**Domain:** Agentic medical-research system (single-patient, family-operated) with continuous literature mining, temporal knowledge graph, multi-agent cognition, client-side neuroimaging, and a Telegram/Gmail/Notion family digest.
**Researched:** 2026-05-13
**Confidence:** HIGH on the 5-layer decomposition and data flow (Graphiti, NiiVue, CrewAI, FastMCP, RAG patterns all documented). MEDIUM on the optimal cross-cutting MCP placement and on TVB / brain2print integration since those are niche components. LOW on long-horizon scaling — irrelevant here (n=1 patient).

---

## Verdict on the 5-Layer Model

The user-supplied five-layer model — **PERCEPTION → MEMORY → COGNITION → VISUALIZATION → ACTION** — is canonical. It maps cleanly onto the prevailing 2026 agentic-AI architecture published in surveys and production guides: a perception / ingestion layer, a memory layer (often split into vector + graph), a cognition / reasoning layer, and an action / tool layer. The only material adjustment recommended in the literature is treating **Visualization as a parallel branch off Memory**, not a serial layer downstream of Cognition — because the 3D viewer and the agent crew both read from the same memory substrate but along different surfaces (the agents read facts and confidence, the viewer reads volumes and meshes).

That single re-routing matters for build order: it means Visualization is genuinely deferrable without blocking the literature pipeline. It is **not** on the critical path to first family value.

---

## Standard Architecture

### System Overview

```
                                                            ┌──────────────────────┐
                                                            │   ACTION (egress)    │
                                                            ├──────────────────────┤
                                                            │ Telegram 2-way       │
                                                            │ Gmail digest         │
                                                            │ Notion KB            │
                                                            │ Calendar / Duke EAP  │
                                                            └──────────▲───────────┘
                                                                       │ digest payload
                                                                       │ (text + links)
┌──────────────────────────────────────────────────────────────────────┴─────────────┐
│                              COGNITION (5 CrewAI agents)                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  Spider → Analyzer → Hypothesis → Repurposing → Communicator                        │
│  Shared memory: mem0 │ Prompt opt: DSPy │ Reasoning: Claude Sonnet 4                │
│  Hypothesis pipeline: Adaptive GoT MCP │ Tool plane: Vercel AI SDK streaming        │
└──────────▲──────────────────────────────────────────────────────────────────────────┘
           │ hybrid query (graph + vector, single call via LightRAG)
           │
┌──────────┴──────────────────────────────────────────────────────────┐  ┌──────────────────────────┐
│                          MEMORY (server-side)                        │  │  VISUALIZATION (browser) │
├──────────────────────────────────────────────────────────────────────┤  ├──────────────────────────┤
│  Neo4j + Graphiti     Qdrant + fastembed     Supabase Postgres       │  │ NiiVue (WebGL2)          │
│  (temporal KG,        (semantic vectors,     (10 tables: papers,     │  │ R3F + drei + post-       │
│   t_valid intervals,  local embeddings)      runs, agent state,      │  │   processing             │
│   confidence decay)                          users, audit log)       │  │ atlas-mcp (read-only     │
│                                                                       │  │   atlas labels)          │
│  LightRAG (unified graph+vector retrieval)   CF R2 / KV (blobs/cache)│  │ niivue-mcp (viewer ops)  │
│  Hindsight (self-improving memory)           Prism MCP (HIPAA edge)  │  │ bonbid-mcp (segmentation │
│                                                                       │  │   results, NOT volumes)  │
│                              ▲                                        │  │ tvb-mcp (sim params)     │
└──────────────────────────────┼────────────────────────────────────────┘  │                          │
                               │ writes (entities + embeddings + chunks)   │ ───────────────────────  │
┌──────────────────────────────┴────────────────────────────────────────┐  │  TRUST BOUNDARY          │
│                          PERCEPTION                                    │  │  ───────────────────────│
├────────────────────────────────────────────────────────────────────────┤  │  NIfTI / DICOM never    │
│  n8n cron (every 6 h) ──orchestrates──▶                                │  │  leaves the browser.    │
│    Crawl4AI (primary, OSS)                                             │  │  Segmentation runs       │
│    Firecrawl MCP (paid fallback, budget-gated)                         │  │  WASM-side. Server only  │
│    Browser Use (paywall bypass)                                        │  │  ever sees mesh + label  │
│    RAGFlow (PDF → chunks + entities)                                   │  │  summaries, never voxels.│
│  Sources: PubMed, ClinicalTrials.gov, bioRxiv/medRxiv, Cochrane,       │  └──────────────────────────┘
│    Google Scholar, Duke / Wisconsin program pages, FDA, Orphanet       │           ▲
└────────────────────────────────────────────────────────────────────────┘           │ MRI/DICOM upload
                                                                                      │ (drag-drop, local file)
                                                                                      │
                                                                              ┌───────┴─────────┐
                                                                              │ Family laptop / │
                                                                              │ browser only    │
                                                                              └─────────────────┘
```

### Component Responsibilities

| Component | Layer | Responsibility | Implementation |
|-----------|-------|----------------|----------------|
| n8n | Perception | Cron, retries, source rotation, budget gate to paid scrapers | Self-hosted on Railway |
| Crawl4AI | Perception | Default crawler for HTML & open-access PDFs | Python, local; OSS |
| Firecrawl MCP | Perception | Fallback for paywalled / JS-heavy sources | Metered, budget-gated |
| Browser Use | Perception | Browser automation for sources Firecrawl can't reach | Containerized; rarely fired |
| RAGFlow | Perception | PDF → text chunks → entity candidates | Python; feeds Graphiti + Qdrant |
| Graphiti + Neo4j | Memory | Temporal KG: facts with `t_valid` / `t_invalid`, confidence decay, provenance edges | Neo4j AuraDB free tier |
| Qdrant + fastembed | Memory | Semantic search over chunks; local embedding model | Docker; OSS embeddings |
| LightRAG | Memory | Fuses graph + vector into a single query path | Library inside agents |
| Supabase Postgres | Memory | Structured metadata: papers, runs, hypotheses, audit, user state | Managed Postgres + RLS |
| mem0 | Memory | Shared working memory across the 5 agents | OSS; reads/writes via API |
| Hindsight | Memory | Self-improving memory; surfaces under-cited facts | OSS; cron-batch |
| Prism MCP | Memory edge | HIPAA-hardened policy enforcement on memory tools | Custom policy layer |
| CF R2 / KV | Memory | Cheap blob store (PDFs cached), KV for rate-limit & token cache | Cloudflare |
| Spider agent | Cognition | Generates the next batch of targeted queries; deduplicates | CrewAI role |
| Analyzer agent | Cognition | Scores study quality, extracts claims with provenance | CrewAI role |
| Hypothesis agent | Cognition | Cross-disease pattern finder; runs Adaptive GoT MCP | CrewAI role |
| Repurposing agent | Cognition | Drug-repurposing leads; calls **repurpose-mcp** | CrewAI role |
| Communicator agent | Cognition | Converts findings into Georgian/English digest, gates anything below MEDIUM confidence | CrewAI role |
| DSPy | Cognition | Prompt optimization for all five agents | Library |
| Vercel AI SDK | Cognition (web) | Streaming + tool-calling surface for the Next.js cockpit | Library |
| Adaptive GoT MCP | Cognition tool | Graph-of-Thought hypothesis expansion | External MCP |
| NiiVue / R3F | Visualization | Browser-only volume + mesh viewer (WebGL2) | npm; client component |
| niivue-mcp | Visualization tool | Viewer commands (load mesh from URL, set lookup, screenshot) | Custom FastMCP |
| bonbid-mcp | Visualization tool | Runs / fetches BONBID-HIE segmentation results | Custom FastMCP |
| tvb-mcp | Visualization tool | Brain simulation parameter sweep + result fetch | Custom FastMCP (TVB Docker) |
| atlas-mcp | Visualization tool | Anatomical atlas labels & region lookups | Custom FastMCP |
| Telegram bot | Action | Primary 2-way family interface (push + `ask_user`) | n8n + Telegram node |
| Gmail MCP | Action | Weekly long-form digest | Registry MCP |
| Notion MCP | Action | Family knowledge base writes | Registry MCP |
| Google Calendar | Action | Treatment timeline, washouts, travel | Registry MCP |
| Booking.com / Kiwi | Action | Duke logistics automation | Registry MCP |

---

## Where the 5 Custom MCPs Belong

This was an explicit downstream-consumer requirement. The mapping is **not** "one per layer" — three of the five live inside Visualization because the viewer is where the imaging tools surface, one lives at the Memory edge, and one is a Cognition tool.

| Custom MCP | Layer placement | Read or Write? | What it owns |
|---|---|---|---|
| **niivue-mcp** | Visualization (browser-side or local bridge) | Read | Viewer commands: load NIfTI, switch overlay, snapshot, region highlight. The volume itself stays in the browser; the MCP only sends commands. |
| **bonbid-mcp** | Visualization → Memory bridge | Write (labels only) | Runs / retrieves BONBID-HIE neonatal segmentation. **Voxel data stays client-side**; only label volumes & summary stats may be persisted server-side, and only if the family explicitly opts in. |
| **tvb-mcp** | Visualization (sandbox) | Read | The Virtual Brain simulation parameter sweeps, run in a Docker sidecar. Inputs are sim parameters, not patient data. |
| **atlas-mcp** | Memory (read-only reference) | Read | Anatomical atlas (lookups, region IDs, parcellation). Public reference data — safe to live server-side. |
| **repurpose-mcp** | Cognition (tool of the Repurposing agent) | Read | Drug-repurposing knowledge sources (DrugBank-like, KEGG-like, OpenTargets-style). Called by the Repurposing agent. |

---

## Recommended Project Structure

```
aleksandra-brain/
├── agents/                         # CrewAI cognition layer
│   ├── spider/                     # query expansion + dedup
│   ├── analyzer/                   # evidence quality + claim extraction
│   ├── hypothesis/                 # cross-disease pattern (uses Adaptive GoT)
│   ├── repurposing/                # drug leads (calls repurpose-mcp)
│   ├── communicator/               # digest writer + gate
│   ├── shared/
│   │   ├── memory.py               # mem0 + LightRAG handles
│   │   ├── prompts/                # DSPy-optimized prompt registry
│   │   └── tools/                  # tool wrappers (Crawl4AI, Qdrant, Graphiti)
│   └── crew.py                     # CrewAI Flow definition
├── mcp/                            # 5 custom MCPs (FastMCP, Python)
│   ├── niivue_mcp/
│   ├── bonbid_mcp/
│   ├── tvb_mcp/
│   ├── atlas_mcp/
│   └── repurpose_mcp/
├── perception/                     # ingestion adapters
│   ├── crawl4ai_adapter.py
│   ├── firecrawl_adapter.py        # budget-gated
│   ├── browseruse_adapter.py
│   ├── ragflow_pipeline.py         # PDF → chunks + entities
│   └── sources.yml                 # PubMed, CT.gov, bioRxiv, Cochrane, FDA, etc.
├── memory/                         # memory-layer wiring
│   ├── graphiti/                   # episode ingest + temporal queries
│   ├── qdrant/                     # collection schemas + index
│   ├── lightrag/                   # hybrid query path
│   ├── supabase/                   # SQL migrations + RLS policies
│   ├── hindsight/
│   └── prism/                      # HIPAA policy wrappers
├── workflows/                      # n8n exports
│   ├── cron_scrape.json            # every 6 h
│   ├── digest_weekly.json
│   └── telegram_askuser.json
├── viewer/                         # Next.js 14 app (Vercel)
│   ├── app/                        # App Router
│   │   ├── (cockpit)/              # family dashboard
│   │   ├── (viewer)/               # NiiVue + R3F shell viewer
│   │   └── api/                    # server-only routes (no PHI)
│   ├── components/
│   │   ├── niivue/                 # client-only — "use client"
│   │   ├── r3f/                    # shell rendering
│   │   └── digest/                 # findings cards
│   ├── lib/
│   │   ├── supabase/               # browser + server clients
│   │   └── ai/                     # Vercel AI SDK
│   └── public/atlas/               # public reference atlas only
├── scripts/                        # migrations, seeds, smoke tests
├── docs/                           # ka + en
└── infra/                          # Railway + Vercel + Docker compose
    ├── railway.toml
    ├── docker-compose.yml          # Qdrant, TVB
    └── neo4j.cypher                # constraints + indexes
```

### Structure Rationale

- **`agents/` is flat, not nested per-pipeline.** Each agent is a unit of replacement. Flat folders make it easy to swap one out without touching the crew definition.
- **`mcp/` sits alongside `agents/` rather than under it.** MCPs serve both agents and the viewer (niivue-mcp is called from the browser). Burying them under either side creates the wrong dependency direction.
- **`viewer/` is a self-contained Next.js app, not a folder inside a monorepo root.** The privacy boundary is easier to audit when the front end is a unit: only `viewer/app/api/*` runs server-side, and a CI lint rule can forbid imports of patient-imaging modules from those files.
- **`perception/` is library code, not services.** n8n is the scheduler; the perception code is just adapters n8n calls. Keeping them as plain Python modules keeps the same code reusable from a CLI when n8n is down.
- **`workflows/` are exported JSON, version-controlled.** n8n state in a database is unreviewable; exported workflows are diff-able.
- **`memory/` co-locates Graphiti, Qdrant, Supabase wiring** so anyone reading the code can see all four stores at once and reason about consistency.

---

## Architectural Patterns

### Pattern 1: Hybrid Graph + Vector Retrieval (LightRAG over Graphiti + Qdrant)

**What:** Every agent query goes through a single retrieval function that issues a Graphiti temporal query (entities, relationships, validity windows) **and** a Qdrant vector query (chunk-level semantic match) in parallel, then merges and re-ranks. LightRAG is the unification layer; the agents never call Graphiti or Qdrant directly.

**When to use:** Whenever a medical claim needs both "what is currently true" (graph) and "show me the source paragraph" (vector). Every Analyzer and Communicator action is this shape.

**Trade-offs:**
- Pro: One code path; agents stop drifting into "I'll just query Qdrant" patterns that lose temporal context.
- Pro: Graphiti's `t_valid` / `t_invalid` means a fact retracted by a newer paper is automatically demoted without manual purge.
- Con: Two stores to keep in sync; ingestion has to write to both atomically (use Supabase as the ingestion ledger, then fan out).

**Example:**
```python
# memory/lightrag/retrieve.py
def retrieve(query: str, t_at: datetime | None = None) -> RetrievalResult:
    graph_facts = graphiti.search(query, valid_at=t_at, top_k=20)
    chunks      = qdrant.search(query, top_k=20)
    return merge_rerank(graph_facts, chunks,
                        weights={"graph": 0.6, "vector": 0.4})
```

### Pattern 2: Provenance-First Ingestion Ledger

**What:** Nothing enters Graphiti or Qdrant without first landing in `supabase.papers` and `supabase.episodes` with a source URL, retrieval timestamp, and (when present) DOI / PMID / NCT. Graph and vector writes are downstream consumers of this ledger.

**When to use:** Always, in this domain. The project's stated principle — "if no source can be cited, the system says 'unknown'" — is unenforceable without a ledger.

**Trade-offs:**
- Pro: Auditable. Every claim's provenance is recoverable by joining the agent's quoted episode ID against Supabase.
- Pro: Re-indexing Qdrant after a model upgrade is just "replay the ledger."
- Con: Adds a write hop to every ingestion. Acceptable: n=1 patient, throughput is trivial.

### Pattern 3: Two-Plane Orchestration — n8n for the When, CrewAI for the What

**What:** n8n owns scheduling, retries, source rotation, fan-out, and the budget gate. CrewAI owns the agent reasoning. n8n triggers the CrewAI Flow via HTTP and persists run state to Supabase; CrewAI does not schedule itself.

**When to use:** Always in this stack. n8n excels at branching workflows but lacks agent goals; CrewAI excels at agent goals but is a poor scheduler. This is the well-trodden 2026 production pattern.

**Trade-offs:**
- Pro: Each tool stays in its lane. n8n's visual auditability is a feature when the family wants to see "did the scrape run."
- Pro: Swapping schedulers later (e.g., Temporal) is a config change, not a rewrite.
- Con: Two systems to monitor. Mitigation: Supabase row `runs` is the single source of truth — both planes write to it.

### Pattern 4: Confidence-Gated Communicator

**What:** The Communicator agent will not send a finding to Telegram / Gmail / Notion below a configurable confidence threshold (initial: `MEDIUM`). Below the threshold, the finding is staged in Notion as a draft with the missing-evidence reason attached.

**When to use:** This is the architectural answer to the "do not fabricate" principle. Confidence is computed from: source quality score (Analyzer), corroboration count (Graphiti edges), and recency (Graphiti `t_valid`).

**Trade-offs:**
- Pro: Pushes the principle into the architecture, not into a per-prompt instruction that drifts.
- Con: Tuning the threshold takes a few weeks of human review feedback. Start strict, loosen carefully.

### Pattern 5: FastMCP for Custom Tools, Registry MCPs for Commodity Integrations

**What:** The five custom MCPs (niivue, bonbid, tvb, atlas, repurpose) are built with FastMCP decorators. Anything that already exists as a registry MCP (Gmail, Notion, Calendar, Perplexity, Crawl4AI-RAG) is consumed as-is.

**When to use:** Always. The cost of maintaining a custom MCP that duplicates a registry one is real.

**Trade-offs:**
- Pro: FastMCP 3 ships authorization, OpenTelemetry, and versioning — production-grade in one decorator.
- Pro: The 23 / 19 / 5 registry MCPs cover commodity needs; the 5 custom ones are genuinely novel.
- Con: Registry MCPs may drift in API; pin versions.

### Pattern 6: Client-Side-Only Imaging — Architectural, Not Conventional

**What:** Patient NIfTI / DICOM is loaded into the browser via drag-and-drop, parsed by NiiVue (with `dcm2niix.wasm` for DICOM → NIfTI), and processed entirely client-side. The server never sees voxel data. When segmentation runs (BONBID-HIE), it runs in the browser (WASM where possible) or in a local helper process — never on the Vercel server.

**When to use:** Always, in this domain. This is the constraint listed first in `PROJECT.md`.

**Implementation specifics:**
- Next.js components touching NiiVue are `"use client"` only. A lint rule (or a CI grep) forbids importing them from `app/api/`.
- The Supabase `papers` and `findings` tables have **no** column that could contain voxel data. The schema itself is the guarantee.
- If the family ever opts into sharing a derived summary (e.g., a lesion volume number), that number — not the volume — is what crosses the boundary.
- `viewer/public/atlas/` may hold the **reference** atlas (public, non-patient). Patient meshes are generated client-side from the loaded volume and never uploaded.

**Trade-offs:**
- Pro: Eliminates the HIPAA blast radius. The viewer can be a static site if needed.
- Pro: Faster UX — no upload round-trip for a 200 MB volume.
- Con: Heavy client. Older laptops will struggle with 3D shells > ~10 M faces. Mitigation: nii2mesh decimation defaults to a face budget.
- Con: No server-side mesh caching across sessions for the same family unless they explicitly opt in.

---

## Data Flow

### Primary Flow: Literature → Family Digest

```
PubMed / CT.gov / bioRxiv / Cochrane / Duke pages
        │ (n8n cron, 6 h)
        ▼
Crawl4AI ──(if blocked)──▶ Firecrawl ──(if blocked)──▶ Browser Use
        │
        ▼  raw HTML / PDF
RAGFlow  (PDF parse → chunks → candidate entities)
        │
        ▼
Supabase.papers  (ledger row with source URL, DOI/PMID, fetched_at)
        │
        ├──▶ Qdrant            (chunk embeddings, fastembed local)
        └──▶ Graphiti / Neo4j  (entities + relationships + t_valid)
                │
                ▼
        LightRAG hybrid query surface
                │
                ▼
CrewAI Flow:  Spider → Analyzer → Hypothesis → Repurposing → Communicator
   (mem0 shared memory across the five; DSPy-optimized prompts;
    Adaptive GoT MCP for hypothesis branching; repurpose-mcp for drug leads)
                │
                ▼
Communicator gate:  confidence ≥ MEDIUM ?
        │                        │
       yes                       no
        │                        ▼
        ▼                  Notion draft + reason
Telegram push  ◀── primary
Gmail digest   ◀── weekly
Notion KB      ◀── on every accepted finding
Calendar       ◀── only when finding has a date (e.g., trial enrollment window)
```

### Imaging Flow (Browser-Local Only)

```
[Family laptop] drag-drop NIfTI or DICOM folder
        ▼
NiiVue (WebGL2)  +  dcm2niix.wasm  (DICOM → NIfTI in-browser)
        ▼
R3F renders 3D anatomical shell
        ▼
(optional) BONBID-HIE segmentation in-browser → label volume
        ▼
nii2mesh decimation → mesh
        ▼
atlas-mcp lookup for region labels  (this MCP call IS server-side,
                                     but it carries only region IDs,
                                     never voxel data)
        ▼
On-screen overlay + agent context  (the agents see "lesion in left
                                    temporal lobe, ~3.2 cm³" — never
                                    the voxels themselves)
```

### Family Question Flow (Telegram `ask_user`)

```
Family → Telegram message ("any news on cord blood timing?")
        ▼
n8n Telegram trigger
        ▼
CrewAI Flow with topic=cord_blood
        ▼
LightRAG hybrid query (Graphiti + Qdrant)
        ▼
Communicator drafts reply (cites provenance)
        ▼
Confidence gate
        ▼
Telegram reply (with source links)  →  Notion KB entry  →  Supabase audit
```

### State Management

| State kind | Owner | Lifetime |
|---|---|---|
| Source-of-truth facts | Graphiti (Neo4j) | Indefinite, with `t_invalid` lifecycle |
| Semantic chunks | Qdrant | Indefinite; re-indexable from Supabase ledger |
| Run / job state | Supabase `runs` | Indefinite; audit |
| Agent working memory | mem0 | Per-flow, cleared on flow end |
| Auth / session | Supabase Auth + Next.js server components (`getUser`) | Session |
| Viewer state | Browser only (React state, IndexedDB cache) | Tab |
| Patient imaging | Browser only (RAM + IndexedDB) | Tab |

The single rule binding all of this: **patient imaging never appears in any column of any table in any store.** That is the schema-level guarantee for the privacy constraint.

---

## Trust Boundaries

```
┌─────────────────────────── BROWSER (family laptop) ──────────────────────────┐
│  HIGH TRUST  │  Patient NIfTI / DICOM, NiiVue, R3F, BONBID-HIE WASM,         │
│              │  mesh generation, atlas overlay logic.                          │
│              │                                                                 │
│              │  Memory: React state, IndexedDB. Never persisted off-device.    │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │ ONLY these cross the boundary:
                                   │   - user auth tokens
                                   │   - structured findings, citations
                                   │   - region IDs & atlas lookups
                                   │   - opt-in derived summaries (numbers)
                                   │ NEVER:
                                   │   - voxel arrays
                                   │   - DICOM headers with PHI
                                   │   - generated meshes (unless opted-in)
                                   ▼
┌────────────────── VERCEL (Next.js server-side) ──────────────────────────────┐
│  MEDIUM TRUST│  Server components, API routes, Supabase server client.        │
│              │  Validates auth with getUser() (sends to Auth server, not       │
│              │  trust-by-cookie). RLS enforced at the Postgres level.          │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────── RAILWAY (n8n, CrewAI, custom MCPs) ────────────────────────────┐
│  MEDIUM TRUST│  Workflow engine + agents + repurpose-mcp + atlas-mcp +        │
│              │  tvb-mcp (sandboxed Docker). Touches public literature,        │
│              │  public atlases, public drug DBs. Does not touch patient        │
│              │  imaging.                                                       │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────── DATA PLANE (Neo4j, Qdrant, Supabase, R2/KV) ─────────────────┐
│  MEDIUM TRUST│  Public-literature derived facts and embeddings. No PHI.       │
│              │  RLS on Supabase. Prism MCP provides HIPAA-style policy        │
│              │  enforcement on tool calls that read memory — future-proofing   │
│              │  for the day an external clinician gets read access.            │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────── EXTERNAL (third-party) ───────────────────────────────┐
│  LOW TRUST   │  Claude API, Firecrawl, PubMed, ClinicalTrials.gov,            │
│              │  Telegram, Gmail, Notion, Booking, Kiwi.                       │
│              │  Receive: queries about public literature, digest payloads.    │
│              │  NEVER receive: patient imaging, raw DICOM headers,            │
│              │                  identifiable clinical notes.                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Trust Boundary Rules (enforceable)

1. **Schema rule:** No Supabase, Neo4j, or Qdrant column / property / payload exists that could legally hold voxel data. The schema is the guarantee.
2. **CI rule:** A grep on `viewer/app/api/**` forbidding imports from `viewer/components/niivue/**`. The viewer's server-side code cannot import the viewer's client-side imaging modules.
3. **Auth rule:** Server components and route handlers use `supabase.auth.getUser()`, **never** `getSession()` — `getUser` revalidates against the auth server; `getSession` trusts local storage and is a known footgun.
4. **RLS rule:** Every Supabase table that holds family-scoped data has `auth.uid() = user_id` policies enabled before the first insert.
5. **MCP rule:** `bonbid-mcp` may not accept a voxel array as a tool argument. It accepts a job descriptor (or runs entirely in-browser). Any future shape change here requires explicit constraint review.
6. **Egress rule:** The Communicator agent's `send_to_telegram` tool is whitelisted on payload shape — text + citation URLs only. Imaging derivatives cross only when the family clicks "share."

---

## Build Order

This is the load-bearing question for the roadmap. The constraint set is:

- Family needs early evidence the **literature pipeline** works.
- 3D viewer and brain simulation are polish — valuable but not on the critical path to first family value.
- Neuroplasticity window (0–2 yr) is a real, ticking deadline. **Front-load research throughput.**
- Cost ceiling: MVP $20–30/mo, full $120/mo.

### Recommended Build Order (justified by dependency, not gut feel)

#### Phase 0 — Foundation (Week 1–2)
**Goal:** Plumbing only, no value yet.
- Repo, monorepo layout, CI, lint rule for trust-boundary imports.
- Supabase project + initial schema (`papers`, `runs`, `findings`, `auth`).
- Neo4j AuraDB free-tier project + base constraints.
- Qdrant Docker on Railway, fastembed model pulled.
- Next.js 14 scaffold deployed to Vercel with a single auth-gated page.
- n8n self-hosted on Railway, hello-world cron.

**Justification:** Every subsequent phase requires one of these. Doing them later means rework. Doing them all up front is two weeks of deferred value — acceptable.

#### Phase 1 — Perception (Week 3–4)
**Dependency:** Supabase ledger exists.
- Crawl4AI adapter pulls PubMed + ClinicalTrials.gov on n8n cron.
- Writes raw HTML/PDF to CF R2.
- Inserts ledger rows in Supabase.
- RAGFlow PDF → chunks (no embedding yet).

**Justification:** Perception is the lowest-trust, most-likely-to-break layer. Validate scrape coverage before paying for embeddings or graph writes. Failure mode is high (sources change, paywalls move) — find out early.

#### Phase 2 — Memory (Week 5–6)
**Dependency:** Perception is producing chunks.
- Wire Qdrant ingest from Supabase ledger (fan-out worker).
- Wire Graphiti from Supabase ledger (entity extraction → temporal facts).
- LightRAG retrieval function with merge-rerank.
- First end-to-end smoke test: ingest 100 papers, query "cord blood + HIE", verify recall.

**Justification:** Memory is the substrate everything else reads from. The Cognition layer is unbuildable without it, and Visualization (which reads atlas-mcp + memory) similarly waits.

#### Phase 3 — Cognition Minimum (Week 7–9)
**Dependency:** Memory queryable.
- CrewAI Flow with **two** agents first: Analyzer + Communicator. **Skip** Spider / Hypothesis / Repurposing initially.
- Communicator writes to a Notion-only draft (no Telegram push yet — too risky during tuning).
- Confidence gate at HIGH (very strict) to start.

**Justification:** Two agents end-to-end proves the loop. Adding three more agents in parallel is cheap *after* the loop is proven; doing all five first means you don't know which one is wrong when the digest is bad.

#### Phase 4 — First Family Value (Week 10–11)
**Dependency:** Cognition is producing acceptable drafts.
- Turn on Telegram push from Communicator (still confidence-gated).
- Gmail weekly digest.
- Notion KB writes on accepted findings.
- **This is the milestone where the family sees the literature pipeline working.** It is the project's first proof.

**Justification:** Up to here, every phase has been infrastructure. This is the first phase that the family can evaluate on its own merits. Hitting this within ~11 weeks is the test of the build order.

#### Phase 5 — Cognition Full (Week 12–14)
**Dependency:** Family-visible value exists; iteration safety net is in place.
- Add Spider, Hypothesis, Repurposing agents.
- Wire repurpose-mcp.
- Wire Adaptive GoT MCP for Hypothesis.
- Loosen confidence gate to MEDIUM with human-in-the-loop review of borderline findings.

#### Phase 6 — Action Surfaces (Week 15–16)
**Dependency:** Stable digest content.
- Telegram 2-way (`ask_user`).
- Google Calendar for treatment timeline (Duke EAP, washouts).
- Booking.com + Kiwi.com automation behind a manual "approve travel?" step.

#### Phase 7 — Visualization Phase 1: Viewer (Week 17–19)
**Dependency:** Memory layer is mature; atlas-mcp can serve labels.
- Next.js viewer page with NiiVue + R3F.
- Drag-drop NIfTI loads.
- DICOM via dcm2niix.wasm.
- atlas-mcp wired for region labels.
- niivue-mcp wired for viewer commands.

**Justification:** This is the first time the family interacts with the *patient's* imaging via the system. It's high-value, but the literature pipeline must be reliable first — splitting attention earlier would slow both.

#### Phase 8 — Visualization Phase 2: Segmentation (Week 20–22)
**Dependency:** Viewer is stable.
- BONBID-HIE segmentation in-browser (or local helper).
- bonbid-mcp wraps the runner.
- nii2mesh decimation.
- 3D anatomical shells with atlas overlay.

#### Phase 9 — Visualization Phase 3: Simulation (Week 23+)
**Dependency:** Everything else.
- TVB Docker via tvb-mcp.
- brain2print STL export.
- This is genuinely polish. It is valuable, but it must not block earlier phases.

### Why Not Build Visualization Earlier?

Tempting, because the viewer is the most visually impressive output. But:

1. The viewer has no agent value yet — without the Memory and Cognition layers, it shows a brain but says nothing useful about it.
2. The viewer is the **only** component that touches PHI. Building it under pressure (before the trust-boundary lint rules and RLS policies exist) is exactly when boundary mistakes happen.
3. The neuroplasticity-window argument — "front-load research throughput" — points the other way: literature pipeline first, viewer second.

The 5-layer model is correct as a static decomposition. As a **build order**, it should be read as: Perception → Memory → Cognition (minimum) → Action (digest) → Cognition (full) → Action (interaction) → Visualization. Visualization is genuinely fifth in priority even though it's listed fourth in the layer model.

---

## Scaling Considerations

This is a single-patient system. Conventional scaling tables don't apply. The realistic dimensions are:

| Dimension | At launch | At 6 months | At 18 months |
|---|---|---|---|
| Papers ingested | 1k | 25k | 100k |
| Graphiti nodes | 5k | 200k | 1M |
| Qdrant points | 50k chunks | 1M chunks | 5M chunks |
| Concurrent users | 2 (parents) | 5 (+ clinicians) | 10 |
| MCP calls / day | 100 | 2k | 5k |

### Where the system actually breaks first

1. **Neo4j AuraDB free-tier limits.** Free tier caps node count. At ~200k entities (≈6 months in), you'll hit it. Mitigation: paid AuraDB tier (~$65/mo) or self-host Neo4j on the same Railway instance. This is a budget-line decision, not an architecture change.
2. **Qdrant disk size.** 5M chunks at fastembed dim is several GB. Railway disk is cheap; not a real worry.
3. **CrewAI Flow runtime under tool-call fan-out.** Hypothesis + Repurposing branches can balloon. Mitigation: per-flow tool-call budget, configurable.
4. **n8n self-hosted reliability.** Single-instance n8n has a long tail of memory leaks. Mitigation: Railway auto-restart + alert to Telegram on missed cron.

None of these are architecture-changing. All are budget or operational.

---

## Anti-Patterns

### Anti-Pattern 1: "Send a thumbnail to the server"

**What people do:** "We'll just upload a 2D screenshot of the lesion for the agents to see — it's just a picture."
**Why it's wrong:** A screenshot of a brain with timestamps, orientation cues, and atlas overlays is *identifiable imaging data*. The HIPAA blast radius is identical to the volume. Worse, it slips past the schema-level guarantee.
**Do this instead:** Send region IDs + measurements, not pixels. The agents reason on "lesion in left temporal lobe, ~3.2 cm³" just as well — better, because that's structured.

### Anti-Pattern 2: "We'll cache the mesh in R2 for next time"

**What people do:** Persist generated meshes to Cloudflare R2 to speed up tab reloads.
**Why it's wrong:** A patient mesh is derived from voxels and is itself PHI. Once it's in R2 you have all the obligations of server-side PHI storage.
**Do this instead:** IndexedDB on the family device. Same UX win, no boundary crossed.

### Anti-Pattern 3: Calling Graphiti and Qdrant directly from agents

**What people do:** "Just give the Spider agent a Qdrant tool, why route through LightRAG."
**Why it's wrong:** Each agent ends up with a different retrieval strategy, you lose temporal context (Qdrant alone has none), and provenance becomes inconsistent.
**Do this instead:** Single `retrieve(query, t_at=...)` tool. Every agent calls it. LightRAG handles the fusion.

### Anti-Pattern 4: One mega-prompt with all five agent roles inside

**What people do:** "Why pay CrewAI's overhead — just ask Claude to play all five roles in one prompt."
**Why it's wrong:** Loses tool-isolation (only Repurposing should be able to call repurpose-mcp), loses mem0's shared-memory affordance, and you can no longer A/B optimize prompts per role with DSPy.
**Do this instead:** Five agents, one CrewAI Flow. The overhead is small; the affordances are large.

### Anti-Pattern 5: Trusting `supabase.auth.getSession()` in a server component

**What people do:** Read the session in a Next.js server component to gate access.
**Why it's wrong:** `getSession()` reads from cookies / local storage and does not revalidate against the auth server. A stale or forged cookie passes.
**Do this instead:** Always `supabase.auth.getUser()` server-side. It calls the auth server and is the documented trustworthy method.

### Anti-Pattern 6: "Just have n8n call the LLM directly"

**What people do:** Use n8n's AI nodes to make the digest call straight from the cron workflow.
**Why it's wrong:** You skip CrewAI, lose mem0, lose DSPy prompts, lose the per-agent goal/backstory primitive that gives the digest its shape. The result is incoherent.
**Do this instead:** n8n schedules. CrewAI reasons. Each tool in its lane.

### Anti-Pattern 7: Building the viewer first because it's visually impressive

**What people do:** Spend the first month on NiiVue + R3F polish to "show progress."
**Why it's wrong:** It's the highest-PHI-risk surface and the lowest-leverage path to first family value. By the time the viewer ships, the literature pipeline still isn't producing weekly digests — which is the actual core value.
**Do this instead:** See Build Order above. Viewer is Phase 7, not Phase 1.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| PubMed E-utilities | REST via Crawl4AI | Rate limit 3 req/s without API key, 10 req/s with — get a free key |
| ClinicalTrials.gov | REST v2 API | Excellent — no key needed; use the modern `/api/v2/studies` endpoint |
| bioRxiv / medRxiv | REST | No key; date-windowed pulls |
| Cochrane | Crawl4AI | Some content paywalled — gate Firecrawl fallback on budget |
| Duke / Wisconsin program pages | Crawl4AI weekly | These change rarely — low-frequency cron |
| FDA / Orphanet | Crawl4AI | Public; useful for repurposing leads |
| Claude API (Sonnet 4) | Anthropic SDK via Vercel AI SDK | Streaming + tool calling; cache prompts where possible |
| Firecrawl | Registry MCP | **Budget-gated** — only fire when Crawl4AI fails |
| Perplexity MCP | Registry MCP | Use sparingly for current-events queries |
| Telegram | n8n Telegram node + bot | 2-way; `ask_user` pattern |
| Gmail | Registry MCP | Weekly digest only |
| Notion | Registry MCP | KB writes, draft staging |
| Google Calendar | Registry MCP | Treatment timeline |
| Booking / Kiwi | Registry MCP | Behind manual approval |
| Neo4j AuraDB | Bolt driver via Graphiti | Free tier to start |
| Supabase | `@supabase/ssr` for Next.js, Python client for agents | RLS on every table |
| Cloudflare R2 / KV | S3-compatible / REST | Cheap blob & cache |

### Internal Boundaries

| Boundary | Communication | Notes |
|---|---|---|
| n8n ↔ CrewAI | HTTPS POST to CrewAI HTTP entrypoint | CrewAI Flow gets job descriptor; writes `runs` row in Supabase |
| Agents ↔ Memory | LightRAG single function | Never direct Qdrant or Graphiti from agent code |
| Agents ↔ Custom MCPs | MCP protocol over stdio (in-process) or HTTP (cross-process) | FastMCP supports both; default stdio for co-located, HTTP for tvb-mcp (Docker) |
| Browser ↔ Vercel server | Next.js server components + route handlers | `getUser()` on every authenticated path |
| Browser ↔ Custom MCPs (niivue, bonbid, atlas) | Via Vercel AI SDK tool calls or direct fetch | bonbid-mcp must not accept voxel arguments — JSON job descriptors only |
| CrewAI ↔ Claude API | Vercel AI SDK on the web side; Anthropic SDK directly from CrewAI Python | Same prompt registry (DSPy) on both sides |
| Vercel ↔ Supabase | `@supabase/ssr` server client per request | Service role only in trusted server contexts; anon key in browser |
| n8n ↔ Supabase | Supabase node + REST | n8n writes `runs`, reads source `papers` |

---

## Sources

- [Multi-Agent AI in 2026: Build Production Systems with CrewAI, LangGraph & AutoGen](https://dev.to/ottoaria/multi-agent-ai-in-2026-build-production-systems-with-crewai-langgraph-autogen-5e40)
- [CrewAI Documentation](https://docs.crewai.com/)
- [CrewAI vs n8n: which AI Agent framework should you use?](https://inkeep.com/blog/crewai-vs-n8n)
- [Multi-Agent Systems & AI Orchestration Guide 2026](https://www.codebridge.tech/articles/mastering-multi-agent-orchestration-coordination-is-the-new-scale-frontier)
- [Graphiti — Build Real-Time Knowledge Graphs for AI Agents (getzep/graphiti)](https://github.com/getzep/graphiti)
- [Graphiti: Knowledge Graph Memory for an Agentic World — Neo4j](https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/)
- [Graphiti: Temporal Knowledge Graphs for Agent Memory](https://codex.danielvaughan.com/2026/03/30/graphiti-agent-memory-store/)
- [A Neo4j-Based Framework for Integrating Clinical Data (medRxiv 2025)](https://www.medrxiv.org/content/10.1101/2025.07.20.25322556v1.full.pdf)
- [The Complete Developer's Guide to GraphRAG, LightRAG, and AgenticRAG](https://dev.to/superorange0707/the-complete-developers-guide-to-graphrag-lightrag-and-agenticrag-14go)
- [Agentic Retrieval-Augmented Generation: A Survey on Agentic RAG (arXiv 2501.09136)](https://arxiv.org/abs/2501.09136)
- [A self-correcting Agentic Graph RAG for clinical decision support (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12748213/)
- [Open-Source Agentic Hybrid RAG Framework for Scientific Literature Review](https://arxiv.org/abs/2508.05660)
- [NiiVue — main site](https://niivue.com/)
- [NiiVue DICOM docs](https://niivue.com/docs/dicom/)
- [niivue/niivue (GitHub)](https://github.com/niivue/niivue)
- [Accessing DICOM Files in the Frontend: Architectural Approaches and Trade-offs](https://adeelbarki.medium.com/accessing-dicom-files-in-the-frontend-architectural-approaches-and-trade-offs-f95ab1e1c000)
- [Web-Based DICOM Viewers: A Survey (Journal of Imaging Informatics in Medicine)](https://link.springer.com/article/10.1007/s10278-024-01216-5)
- [FastMCP (GitHub)](https://github.com/jlowin/fastmcp)
- [How to Build MCP Servers in Python: Complete FastMCP Tutorial](https://www.firecrawl.dev/blog/fastmcp-tutorial-building-mcp-servers-python)
- [Build an MCP server — Model Context Protocol](https://modelcontextprotocol.io/docs/develop/build-server)
- [Setting up Server-Side Auth for Next.js (Supabase)](https://supabase.com/docs/guides/auth/server-side/nextjs)
- [Building a Healthcare App with Next.js and Supabase](https://vaibhav-parmar-portfolio.vercel.app/blog/building-healthcare-app-with-nextjs-supabase)
- [n8n Scheduled Workflows & Cron Jobs Guide](https://cyberincomeinnovators.com/mastering-scheduled-workflows-cron-jobs-in-n8n-the-definitive-guide)
- [Agentic AI Architecture: Types, Components, and Best Practices (Exabeam)](https://www.exabeam.com/explainers/agentic-ai/agentic-ai-architecture-types-components-best-practices/)
- [How we built Cognitive Memory for Agentic Systems (CrewAI blog)](https://crewai.com/blog/how-we-built-cognitive-memory-for-agentic-systems)

---
*Architecture research for: ALEKSANDRA_BRAIN — agentic medical-research system for severe pediatric HIE*
*Researched: 2026-05-13*
