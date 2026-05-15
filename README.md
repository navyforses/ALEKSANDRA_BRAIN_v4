# ALEKSANDRA_BRAIN

> Living research brain for pediatric Hypoxic-Ischemic Encephalopathy (HIE).
> An open-source AI system that never sleeps — continuously searching,
> analyzing, and discovering treatment possibilities for children with
> severe brain injury.

**Status:** Phase 2 closed; Phase 2.5/3 entry active (2026-05-15)
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

### 4. Current verification
```bash
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase1
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2 --gate all
.venv/Scripts/python.exe -X utf8 scripts/test_crew.py
```

On Windows, use the project virtualenv and `-X utf8`; bare `python` can miss
dependencies and CP1252 console output can break verifier tables.

### 5. Run the brain shell
```bash
python -m mcp.hello_brain      # MCP server
```

---

## Current progress

- [x] Phase 0 foundation closed — see [`docs/PHASE_0_EXIT_REPORT.md`](docs/PHASE_0_EXIT_REPORT.md)
- [x] Phase 1 perception closed — 10/10 PASS in [`docs/PHASE_1_EXIT_REPORT.md`](docs/PHASE_1_EXIT_REPORT.md)
- [x] Phase 2 memory closed — 19/19 PASS in [`docs/PHASE_2_EXIT_REPORT.md`](docs/PHASE_2_EXIT_REPORT.md)
- [x] External Phase 2 live audit written — [`docs/PHASE_2_LIVE_AUDIT.md`](docs/PHASE_2_LIVE_AUDIT.md)
- [x] Claude Code activity diagnostic written — [`docs/ACTIVITY_DIAGNOSTIC_PLAN.md`](docs/ACTIVITY_DIAGNOSTIC_PLAN.md)
- [ ] Phase 2.5 cleanups — perception scale-up, DSPy training data, supporting paper hydration, repurposing run logs
- [ ] Phase 3 cognition minimum — CGM-01 verifier, Analyzer PICO, Communicator schema, evidence ranking, confidence gate

Historical Phase 0 materials remain available:
[`docs/PHASE_0_PLAN.md`](docs/PHASE_0_PLAN.md) and
[`docs/PHASE_0_HANDOUT.md`](docs/PHASE_0_HANDOUT.md).

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
