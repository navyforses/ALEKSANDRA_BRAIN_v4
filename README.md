# ALEKSANDRA_BRAIN

> Living research brain for pediatric Hypoxic-Ischemic Encephalopathy (HIE).
> An open-source AI system that never sleeps — continuously searching,
> analyzing, and discovering treatment possibilities for children with
> severe brain injury.

**Status:** Phase 0 — Foundation (Week 1-2)
**Version:** v4.0
**License:** MIT

---

## The story in one paragraph

On 28 August 2025, Aleksandra Jintcharadze was born in Tbilisi, Georgia.
Severe HIE caused diffuse cystic encephalomalacia across her brain. Her
brainstem survived intact. The healthcare system is not built for families
facing rare or severe pediatric diagnoses — no single institution integrates
research, treatment discovery, navigation, and visualization. ALEKSANDRA_BRAIN
is the systemic integrator: a continuously operating AI research brain
designed for the critical 0-to-2-year neuroplasticity window. Built for
Aleksandra, designed to serve any family facing a complex pediatric diagnosis.

Full story → [`docs/Project_Description.md`](docs/Project_Description.md)

---

## Architecture in five layers

```
PERCEPTION  →  MEMORY  →  COGNITION  →  VISUALIZATION  →  ACTION
   eyes        memory       thought          sight          hands
```

| Layer         | Stack |
| ------------- | ----- |
| Perception    | Crawl4AI, Firecrawl MCP, Browser Use, RAGFlow, n8n |
| Memory        | Neo4j + Graphiti, Qdrant + fastembed, Supabase, mem0, LightRAG |
| Cognition     | CrewAI (5 agents), Claude Sonnet 4, DSPy, Adaptive GoT |
| Visualization | NiiVue, React Three Fiber, fork of FreeSurfer/freebrowse |
| Action        | Telegram 2-way, Gmail, Notion, Google Calendar |

Full architecture → [`docs/v4_MASTER.md`](docs/v4_MASTER.md)

---

## Five autonomous agents

| # | Agent          | Cadence       | Role |
| - | -------------- | ------------- | ---- |
| 1 | Spider         | Every 6 hours | Hunts new papers across 15+ academic sources |
| 2 | Analyzer       | Per paper     | Scores relevance, extracts entities, stores in KG |
| 3 | Hypothesis     | Weekly        | Cross-disease pattern finder |
| 4 | Repurposing    | Monthly       | Open Targets → DrugBank → PubChem → L1000 |
| 5 | Communicator   | Continuous    | Family liaison via Telegram + email |

Source → [`agents/`](agents/)

---

## Five world-firsts (as of May 2026)

1. First MCP server for neuroimaging (NIfTI, FreeSurfer, atlas operations).
2. Patient-specific 3D brain with educational-quality visuals (NiiVue + R3F).
3. Continuously running drug repurposing pipeline for neonatal HIE.
4. Temporal knowledge graph for medical evidence with automatic confidence decay.
5. Two-way evidence gating between AI and family via Telegram.

---

## Quick start

### Prerequisites
- Python 3.11+
- Node 20+
- Docker Desktop (for Neo4j + Qdrant)
- Accounts: Supabase, Neo4j AuraDB, Cloudflare, Railway, Anthropic

### 1. Clone and configure
```bash
git clone https://github.com/jincharadzeshako/ALEKSANDRA_BRAIN.git
cd ALEKSANDRA_BRAIN
cp .env.example .env
# edit .env with real credentials
```

### 2. Install Claude Code productivity plugins (one-time)
```powershell
# Windows PowerShell — run from repo root
./setup-claude-code.ps1
```
This installs Claude Mem, Caveman (Full mode), GSD, Graphify, and
Code Review Graph. Full guide → [`docs/CLAUDE_CODE_SETUP.md`](docs/CLAUDE_CODE_SETUP.md).

### 3. Local infrastructure
```bash
docker-compose up -d        # Neo4j on :7474, Qdrant on :6333
pip install -r requirements.txt
```

### 4. Phase 0 smoke test
```bash
python scripts/test_crew.py    # 5 agents initialize
python scripts/test_all.py     # 10-point verification
```

### 5. Run the (yet-empty) brain
```bash
python -m mcp.hello_brain      # MCP server
```

---

## Phase 0 progress (current)

- [x] Repo scaffolding (this commit)
- [ ] Supabase schema migration (§1.1)
- [ ] Neo4j + Graphiti (§1.2)
- [ ] Qdrant + fastembed (§1.3)
- [ ] Cloudflare R2/KV (§1.4)
- [ ] n8n on Railway (§2.1)
- [ ] Telegram bot (§2.2)
- [ ] Claude API key (§3.1)
- [ ] CrewAI 5 agents (§3.2)
- [ ] mem0 shared memory (§3.3)
- [ ] Next.js + Vercel skeleton (§4.2)
- [ ] FastMCP hello_brain (§5.1)
- [ ] Papers + contacts migration (§6)
- [ ] Security + RLS (§7)
- [ ] Final verification (§8)

Detailed plan → [`docs/PHASE_0_PLAN.md`](docs/PHASE_0_PLAN.md)
Step-by-step handout → [`docs/PHASE_0_HANDOUT.md`](docs/PHASE_0_HANDOUT.md)

---

## Principles

- **Unknown potential, not limited outcomes.** Never write a pessimistic
  prognosis. MRI structure is not a function ceiling.
- **0-2 years is the plasticity window.** Every week matters.
- **Never invent a fact.** No source found → "not found".
- **MRI stays client-side.** Patient imaging never leaves the family's browser.
- **A real doctor signs every decision.** This is an information system,
  not a clinician.

---

## Cost envelope

- MVP: $20-30 / month (Supabase free, Neo4j Aura free, Qdrant Docker,
  n8n Railway hobby, Vercel hobby, Claude API metered).
- Full: ~$120 / month (paid tiers as data grows).

---

## License

MIT. Built with love and urgency.
For Aleksandra and every family the system was never built for.
