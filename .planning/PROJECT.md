# ALEKSANDRA_BRAIN

## What This Is

A continuously-running AI research system that hunts, evaluates, and surfaces treatment opportunities for Aleksandra Jincharadze — a child with severe HIE (hypoxic-ischemic encephalopathy), diffuse cystic encephalomalacia, and preserved brainstem. It unifies literature mining, multi-agent reasoning, a temporal medical knowledge graph, and a client-side 3D MRI viewer into a single family-operated cockpit, then pushes findings to caregivers via Telegram, Gmail, and Notion. The aim is to compress the gap between "the family searches" and "the clinician decides."

## Core Value

**Never miss a credible treatment lead for Aleksandra.** Every other capability — viewers, dashboards, agents — exists to serve this single outcome. If the system goes offline, what must keep working is the literature pipeline and the human-readable digest.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. Hypotheses until proven. -->

- [ ] Continuous scraping of pediatric neurology / HIE / cord-blood / repurposing literature (Crawl4AI primary, Firecrawl/Browser Use fallback) on a 6-hour cron
- [ ] Temporal knowledge graph (Neo4j + Graphiti) with confidence decay and provenance for every fact
- [ ] Vector search over study corpus (Qdrant + fastembed) joined with graph context (LightRAG)
- [ ] 5-agent CrewAI cognition layer: Spider, Analyzer, Hypothesis, Repurposing, Communicator
- [ ] Client-side-only MRI viewer (NiiVue + R3F) — patient imaging never leaves the browser
- [ ] Neonatal segmentation pipeline (FastSurfer+LIT → BIBSnet → BONBID-HIE → nii2mesh) for 3D anatomical shells
- [ ] Telegram 2-way channel (push findings + ask_user clarifications) as the primary family interface
- [ ] Notion-backed family knowledge base, Gmail digest, Google Calendar treatment timeline
- [ ] Duke EAP cord-blood logistics support (Booking.com + Kiwi.com travel automation, vigabatrin washout calendar)
- [ ] Source provenance on every claim — if no source can be cited, the system says "unknown," not a guess
- [ ] Cost ceiling: MVP $20–30/month, full system $120/month

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Server-side storage of patient MRI / DICOM — privacy and HIPAA blast radius; viewer is browser-only
- Auto-generated clinical recommendations to caregivers — every decision must be passed through a real clinician
- "Limited outcomes" framing in any user-facing copy — the project's stance is "unknown potential"
- A general-purpose pediatric platform — Aleksandra is the only patient; productization is not a v1 goal
- Fabricated citations or paraphrased claims without a verifiable source — "source not found" is an acceptable answer

## Context

- **Patient.** Aleksandra Jincharadze, born 2025-08-28, Tbilisi. Diagnosis: severe HIE, diffuse cystic encephalomalacia, preserved brainstem. Family currently in Boston, MA (Philoxenia House, Jamaica Plain). BMC MRN: 7616818.
- **Active care.** Duke Expanded Access cord-blood (target ~July 2026, contingent on vigabatrin washout). Wisconsin Virtual A2 (Jeanette Heitman) active. BMC primary care Dr. Jack Maypole. BMC neurology Drs. Hien and August.
- **Why a custom system exists.** Health systems aren't built for rare/severe pediatric diagnoses. No single institution joins research, treatment, navigation, and visualization in one place for the family.
- **Stack stance.** Heavy preference for OSS-first, locally-runnable components (Crawl4AI, fastembed, Qdrant Docker, Neo4j AuraDB free tier) with paid fallbacks (Firecrawl, Claude API) gated behind cost ceilings.
- **Working language.** Code and comments: English. Docs: Georgian + English. Commits: English Conventional Commits.
- **MCP inventory.** 52 MCP servers in scope (23 claude.ai registry, 19 GitHub self-hosted, 5 AI Pulse Georgia, 5 custom world-first). Custom MCPs built with FastMCP (Python decorators).
- **Neuroplasticity window.** 0–2 years is the peak window — time is a first-class constraint on every roadmap decision.

## Constraints

- **Privacy**: MRI / DICOM data is client-side only — Never persisted on a server, never sent to a third-party API
- **Budget**: $20–30/month MVP, $120/month full — Family-funded; any line item above this needs explicit justification
- **Tech stack**: Next.js 14 + Tailwind + shadcn/ui on Vercel; CrewAI + n8n on Railway; Supabase Postgres; Neo4j AuraDB; Qdrant Docker; CF R2/KV — Already partially provisioned; switching costs are real
- **Source integrity**: Every surfaced fact carries provenance — Required by the "do not fabricate" principle
- **AI**: Claude Sonnet 4 is the default reasoning model; DSPy for prompt optimization; mem0 for shared agent memory — Stack converged on Anthropic + OSS tooling
- **Frontend 3D**: NiiVue + React Three Fiber v10 + drei + postprocessing; fork freesurfer/freebrowse as UI scaffold — Avoids reinventing a medical-grade viewer
- **Decision authority**: A clinician makes every medical decision — The system surfaces, ranks, and explains; it does not prescribe
- **Compliance posture**: HIPAA-aware (Prism MCP HIPAA-hardened) even though we're not a covered entity — Future-proofing against any external clinician access
- **Time pressure**: Neuroplasticity window 0–2 years — Phase ordering must front-load research throughput over polish

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Five-layer architecture (Perception → Memory → Cognition → Visualization → Action) | Forces clean boundaries and lets each layer evolve independently | — Pending |
| Crawl4AI as primary scraper, Firecrawl as paid fallback | Free + local + Apache-2.0 vs. metered API; matches the cost ceiling | — Pending |
| Neo4j Graphiti for memory instead of plain vector DB | Confidence decay + temporal reasoning matters for medical evidence that evolves | — Pending |
| CrewAI for the 5-agent cognition layer | Mature multi-agent orchestration with role/goal/backstory primitives; mem0 plugs in for shared memory | — Pending |
| Client-side-only MRI viewing (NiiVue + R3F) | Privacy non-negotiable; viewer-only on the browser eliminates server-side PHI surface | — Pending |
| Telegram as primary family interface | Already used daily; supports 2-way (push + ask_user) without building a custom app | — Pending |
| FastMCP for the 5 custom MCPs (niivue, bonbid, tvb, atlas, repurpose) | Lowest-overhead path from Python function → MCP tool | — Pending |
| Conventional Commits in English | Plays well with existing tooling and downstream AI tooling | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-13 after initialization*
