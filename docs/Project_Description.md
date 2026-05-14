# ALEKSANDRA_BRAIN

### Living Research Brain for Pediatric Hypoxic-Ischemic Encephalopathy

---

**An open-source AI system that never sleeps — continuously searching, analyzing,
and discovering treatment possibilities for children with severe brain injury.**

---

## The Story

On August 28, 2025, Aleksandra Jintcharadze was born in Tbilisi, Georgia. Within hours, severe hypoxic-ischemic encephalopathy (HIE) caused diffuse cystic encephalomalacia across her brain. Her brainstem — the part that controls breathing, heartbeat, and basic reflexes — survived intact.

Her father, Shalva Jintcharadze, a software developer, began a systematic campaign to find every possible treatment. Over 95 days, he contacted 50+ researchers, clinicians, and institutions across 4 countries. Success rate: 24%. He secured enrollment in Duke University's Expanded Access Program for cord blood therapy, Wisconsin's Virtual A2 study, NAPA Center intensive rehabilitation, and consultations at Boston Medical Center and Boston Children's Hospital.

But the healthcare system is not built for families facing rare or severe pediatric diagnoses. No single institution integrates research, treatment discovery, navigation, and visualization into one system. The neurologist sees seizures. The neurosurgeon sees structure. The rehabilitation specialist sees motor function. No one sees the full picture. PubMed, ClinicalTrials.gov, DrugBank, and bioRxiv exist as isolated databases with invisible connections between them. A diabetes drug showing neuroprotective properties in animal models will never surface in an HIE search unless someone — or something — looks across disease boundaries.

ALEKSANDRA_BRAIN is the systemic integrator that no institution has built: a continuously operating AI research brain that bridges these gaps — searching, analyzing, and discovering treatment possibilities every six hours, every week, every month — during the critical 0-to-2-year neuroplasticity window when intervention matters most. It is built for Aleksandra, but its architecture is designed to serve any family facing a complex pediatric diagnosis.

---

## What It Does

ALEKSANDRA_BRAIN operates as five autonomous agents orchestrated by CrewAI (49K stars), each with a defined role, goal, backstory, and toolset:

**Agent 1: The Spider** runs every 6 hours. It searches PubMed, bioRxiv, medRxiv, ClinicalTrials.gov, and 11 additional academic sources for new publications related to HIE — both directly and through cross-disease inference. When metformin, a diabetes drug, showed neuroprotective properties in animal models, it was the cross-disease search pattern that surfaced it. The Spider uses this same logic across hundreds of molecular pathways.

**Agent 2: The Analyzer** processes every new paper the Spider finds. It parses PDFs (including tables and figures), extracts entities (drugs, genes, pathways, brain regions), assigns relevance scores, and stores everything in a temporal knowledge graph where evidence weight changes over time — a 2019 case report carries less weight than a 2025 randomized controlled trial.

**Agent 3: The Hypothesis Generator** runs weekly. It traverses the knowledge graph looking for patterns humans miss: "Drug X targets Pathway Y. Pathway Y is active in brain region Z. Region Z is damaged in Aleksandra but has moderate plasticity potential. No one has tested Drug X for HIE." These hypotheses are ranked by confidence, novelty, and feasibility, then sent to the family for review.

**Agent 4: The Drug Repurposing Engine** runs monthly. It queries Open Targets for HIE-associated molecular targets, searches DrugBank for approved drugs affecting those targets, checks PubChem for blood-brain barrier penetration and pediatric safety profiles, and uses L1000 reverse transcriptomic signatures to find compounds that could reverse the HIE gene expression pattern. No single institution runs this pipeline in an integrated, automated fashion for neonatal HIE.

**Agent 5: The Communicator** bridges the system and the family. Urgent findings (a relevant trial changing status, a high-confidence drug repurposing hit) trigger immediate Telegram notifications. Weekly discovery briefs arrive by email. When the system finds borderline evidence, it asks the family directly: "This paper has moderate relevance. Include in analysis? [Yes/No]." The family stays informed and in control.

---

## The 3D Brain

The most visible component is an interactive, anatomically accurate 3D model of Aleksandra's brain, viewable in any web browser.

This is not a cartoon. It uses Aleksandra's actual MRI data, processed through FastSurfer (cortical reconstruction) and neonatal-specific atlases (dHCP, M-CRIB-S) designed for infant brains — because adult brain templates are anatomically wrong for a newborn. The BONBID-HIE segmentation models, trained on 133 neonatal HIE patients from Massachusetts General Hospital, identify and map the specific lesion patterns.

The viewer combines two rendering engines, built as a fork of FreeSurfer's freebrowse (a React + NiiVue + Vite browser-based viewer): NiiVue (a WebGL2 medical imaging library from the NIH-funded team behind MRIcroGL) handles the clinical data layer — MRI volumes, lesion overlays, atlas labels, and tractography. React Three Fiber handles the cinematic layer — textbook-quality anatomical shells with adjustable transparency, subsurface scattering for realistic tissue appearance, and interactive region identification on hover.

The result: zoom in and see the cortex give way to white matter, then deep structures, then the preserved brainstem. Click any region to see its function, damage status, plasticity potential, relevant therapies, and the number of papers in the knowledge graph that discuss it. Toggle a therapy overlay to see which brain regions it targets. Slide a timeline to visualize neuroplasticity potential at 6, 12, and 24 months.

A separate "Family View" exports a standalone HTML file — no installation, no internet required — that grandparents in Tbilisi can open to understand, in Georgian, exactly what the damage looks like and where hope remains.

The brain2print pipeline can generate a 3D-printable STL file of Aleksandra's brain, so the family can hold a physical model during conversations with doctors.

All MRI processing happens client-side or on the family's own machine. Aleksandra's medical imaging data never leaves the family's browser. This is the most important technical property for a pediatric medical viewer.

---

## What Makes This Different

Five capabilities exist in ALEKSANDRA_BRAIN that exist nowhere else as of May 2026:

**1. The first neuroimaging MCP server.**
The Model Context Protocol (MCP) is the standard for connecting AI assistants to external tools. As of May 2026, not a single MCP server exists for NIfTI neuroimaging, FreeSurfer surface processing, or brain atlas operations. ALEKSANDRA_BRAIN creates five custom MCP servers that let any AI assistant — Claude, GPT, or future models — load a patient's MRI, segment lesions, export 3D meshes, run simulations, and generate family-readable reports, all through natural language commands. Once published, any AI-powered medical tool in the world can use them.

**2. Patient-specific 3D brain with textbook visual quality.**
Commercial anatomy platforms (BioDigital Human, Complete Anatomy) render beautiful generic brains but cannot show a specific patient's damage. Clinical neuroimaging viewers (NiiVue, BrainBrowser) show patient data but look clinical-grey. No existing product combines both. ALEKSANDRA_BRAIN is the first web-based viewer where a real patient's MRI is rendered with educational-quality visuals, interactive region identification, and damage-specific color coding.

**3. Automated drug repurposing pipeline for neonatal HIE.**
The pipeline integrates Open Targets (target prioritization), DrugBank (17,430 drugs with Jaccard similarity search), PubChem (BBB penetration and safety profiles), Reactome/KEGG (pathway validation), Enrichr (L1000 reverse-signature drug repurposing), and Claude API (hypothesis synthesis). Running monthly, it systematically searches for approved or investigational drugs that could be repurposed for HIE based on shared molecular pathways. No institution operates this pipeline in an integrated, continuous fashion for neonatal brain injury.

**4. Temporal knowledge graph for medical evidence.**
Built on Graphiti (a temporal knowledge graph framework) and Neo4j, the system automatically adjusts evidence weight over time. A 2019 case report gradually loses influence while a 2025 multi-center RCT gains it. Entity extraction is automatic — feed in a paper abstract, and the system identifies drugs, genes, pathways, brain regions, and their relationships without manual curation. No existing medical evidence database implements automatic temporal confidence decay.

**5. Two-way evidence gating between AI and family.**
Most medical AI systems are black boxes. ALEKSANDRA_BRAIN operates as a semi-autonomous system where the family maintains decision authority. The Telegram integration enables real-time two-way communication: the AI proposes, the family disposes. "New hypothesis: Lithium may have neuroprotective effects via GSK-3β inhibition. Confidence: moderate. Should I search for more evidence? [Yes/No]." The family stays informed without being overwhelmed, and the system learns from their decisions.

---

## Technical Architecture

### Data Layer (Three Databases, One Brain)

The system uses three specialized databases that work as one through GraphRAG queries:

**Neo4j with Graphiti** stores entities and relationships as a temporal knowledge graph. Nodes represent papers, therapies, pathways, brain regions, genes, contacts, hypotheses, and clinical trials. Edges represent relationships: "Paper X studies Therapy Y," "Therapy Y targets Pathway Z," "Pathway Z is active in Brain Region W," "Brain Region W is damaged in Aleksandra." A single Cypher query traverses this entire chain in milliseconds.

**Qdrant** stores vector embeddings for semantic search. Every paper abstract, therapy description, and hypothesis text is embedded as a 1536-dimensional vector using local fastembed (no cloud API, HIPAA-friendly). This enables queries like "find papers similar to this one" or "what therapies are semantically related to erythropoietin?"

**Supabase (PostgreSQL)** stores structured metadata, user-facing data, and operational state: paper metadata and scores, contact information and follow-up schedules, clinical trial tracking, hypothesis status, brain region damage maps, ingestion logs, and discovery reports.

### MCP Arsenal (52 Servers)

The system connects to 52 MCP servers: 23 from the Claude.ai registry (PubMed, bioRxiv, Clinical Trials, Open Targets, ChEMBL, Gmail, Google Calendar, Google Drive, Cloudflare, Vercel, and others), 19 self-hosted from GitHub (Graphiti, Qdrant, Supabase MCP, Firecrawl MCP, n8n-MCP, Notion MCP, GitHub MCP, Exa, Tavily, Markdownify, Telegram, blender, drugbank, pubchem, and others), 5 from the AI Pulse Georgia ecosystem (FastMCP for building custom servers, Crawl4AI RAG for web-to-vector pipeline, Prism MCP for HIPAA-hardened memory, Draw.io MCP for architecture diagrams, Perplexity MCP for deep research), and 5 custom-built world-first servers (neuroimaging, BONBID-HIE segmentation, Virtual Brain simulation, neonatal atlas, and drug repurposing orchestration).

### Automation (7 Workflows)

All automated workflows run on self-hosted n8n:

| Workflow | Frequency | Function |
|----------|-----------|----------|
| Ingestion Spider | Every 6 hours | Search 15 queries across PubMed, bioRxiv, ClinicalTrials.gov, RSS feeds |
| Deep Analyzer | Per new paper | Parse PDF, analyze relevance, extract entities, generate embeddings |
| Hypothesis Generator | Weekly | Traverse knowledge graph, generate cross-disease hypotheses |
| Weekly Report | Weekly | Aggregate stats, synthesize brief, deliver via Gmail and Telegram |
| Daily Alerts | Daily | Check overdue follow-ups, approaching deadlines, trial status changes |
| Drug Repurposing | Monthly | Run full Open Targets → DrugBank → PubChem → L1000 pipeline |
| Brain Update | On MRI upload | Process through FastSurfer + LIT + BONBID, update brain regions |

### 3D Visualization Pipeline

The visualization combines a server-side preprocessing pipeline and a client-side hybrid renderer:

**Server-side (one-time per MRI scan):** DICOM → NIfTI conversion, FastSurfer cortical reconstruction with LIT lesion inpainting for cystic areas, BIBSnet neonatal segmentation (0-8 months), BONBID-HIE lesion segmentation as probability heatmap, nii2mesh marching cubes conversion, and gltfpack GLB optimization (~1.5MB total output).

**Client-side (real-time in browser):** NiiVue canvas renders MRI volumes, lesion overlays, atlas labels, and tractography. React Three Fiber canvas renders anatomical shells with per-layer transparency, subsurface scattering, region hover identification via BVH-accelerated raycasting, clipping planes for cross-section views, and postprocessing (selective bloom on lesions, SSAO for depth). Shared React state synchronizes both canvases.

**Simulation (server-side, precomputed):** The Virtual Brain (TVB) runs neural mass simulations on Aleksandra's connectome with cystic regions set to zero coupling weight. Output propagation matrices animate signal pulses along tractography streamlines in the browser — pulses traverse intact tracts and terminate at lesion boundaries, making the functional impact of damage visually immediate.

### Neonatal-Specific Design Decisions

Standard adult brain tools fail for neonatal HIE. Three critical adaptations:

**Atlas choice:** Adult MNI152 templates are anatomically wrong for a newborn. The system uses dHCP atlases (28-44 weeks gestational age) with M-CRIB-S parcellation providing DKT-compatible cortical labels that remain consistent as Aleksandra grows.

**Lesion handling:** Cystic encephalomalacia breaks standard cortical reconstruction (FreeSurfer's recon-all fails on large cavities). FastSurfer's LIT (Lesion Inpainting Tool) fills cystic regions with synthetic tissue, runs reconstruction, then projects the lesion mask back onto the reconstructed surface.

**Uncertainty communication:** HIE lesion segmentation achieves Dice scores of approximately 0.5-0.6 because lesions are diffuse and small. The viewer renders lesions as probability heatmaps with gradient coloring, not crisp boundaries. This is scientifically honest and prevents false precision that could mislead clinical decisions.

---

## Privacy and Safety

Aleksandra's MRI data never leaves the family's browser. NiiVue renders entirely client-side. Neonatal segmentation runs on the family's own machine via Docker. Qdrant uses local fastembed for embeddings — no cloud embedding APIs. The Family View export produces a standalone HTML file that works offline with zero external dependencies.

The system is an information aggregator, analyzer, and visualizer. It does not replace physicians. All clinical decisions are made by real doctors in person. Simulations are educational, not predictive. Drug repurposing outputs are hypotheses for discussion with researchers, not prescriptions.

---

## Technology Stack

**Frontend:** Next.js 14+ (App Router), @niivue/nvreact, React Three Fiber v10, @react-three/drei, Vercel AI SDK (23K stars, streaming + tool calling), D3.js, Recharts, Tailwind CSS, shadcn/ui. Deployed on Vercel.

**Backend:** CrewAI (49K stars, 5-agent orchestration), n8n self-hosted (Railway), Supabase Edge Functions, Cloudflare Workers, Claude API (Sonnet 4). FastSurfer and TVB run as Docker containers.

**Data:** Neo4j AuraDB with Graphiti (25K stars, temporal knowledge graph), Qdrant (30K stars, vector search, self-hosted), LightRAG (34K stars, graph+vector unified queries), Supabase PostgreSQL (structured data), mem0 (53K stars, shared agent memory), Cloudflare R2 (PDF/MRI storage), Cloudflare KV (hot cache).

**Ingestion:** Crawl4AI (64K stars, free local scraping, primary), Firecrawl MCP (6K stars, paid fallback), RAGFlow (78K stars, PDF processing with agent workflow), Browser Use (89K stars, paywall bypass), Markdownify MCP (universal format converter).

**Custom MCP Servers:** Built with FastMCP (24K stars, Python decorators). Five world-first servers for neuroimaging, HIE segmentation, brain simulation, neonatal atlas, and drug repurposing.

**Neonatal Pipeline:** FastSurfer + LIT (Apache-2.0), BIBSnet, BONBID-HIE models, dHCP atlas, M-CRIB-S, nii2mesh, brain2print.

**Cost:** $20-30/month for MVP using free tiers. $120/month at full scale.

---

## Roadmap

| Phase | Timeline | Deliverable |
|-------|----------|-------------|
| 1. Foundation | Weeks 1-2 | Databases + Telegram bot + first ingestion pipeline |
| 2. Intelligence | Weeks 3-4 | Hypothesis generation + weekly reports + dashboard MVP |
| 3. Drug Discovery | Weeks 5-6 | Full repurposing pipeline + knowledge graph explorer |
| 4. 3D Brain | Weeks 7-8 | Patient-specific viewer + world-first NIfTI MCP server |
| 5. Simulation | Weeks 9-10 | TVB integration + animated tractography + family exports |

---

## Beyond Aleksandra

ALEKSANDRA_BRAIN is being built for one child, but its architecture is designed to serve many. The five custom MCP servers, once published as open source, enable any AI assistant to work with neuroimaging data. The drug repurposing pipeline can be reconfigured for any neurological condition by changing the target disease in Open Targets. The temporal knowledge graph can track evidence evolution for any medical domain.

The parent project, Med&გზური (MedPath), will offer this system as a multilingual medical navigation service for families worldwide who face complex pediatric diagnoses — in Georgian, Russian, and English.

Every piece of code that does not contain patient data will be released as open source. The five world-first MCP servers will be published to the MCP registry. The BONBID-HIE integration patterns will be documented for other HIE families. The neonatal atlas pipeline will be packaged as a reproducible Docker workflow.

Because no parent should have to read papers at 2 AM alone.

---

## The Team

**Shalva Jintcharadze** — Father, solo developer, medical advocate. React, Next.js, Supabase, Python, Node.js. Built the system architecture and advocacy methodology that achieved a 24% success rate across 50+ institutional contacts in 95 days.

**Claude (Anthropic)** — AI research partner operating as AMKF v2.0 (Adaptive Memory & Knowledge Filter), a 9-specialist virtual medical team providing continuous research support, communication drafting, and technical architecture.

**The broader community:** Hope for HIE mentors, Boston Medical Center clinical team (Dr. Jack Maypole, Andrew Beak), Duke EAP (Sydney Crane), Wisconsin Virtual A2 (Jeanette Heitman), and dozens of researchers who responded to a father's emails.

---

## Contact

Shalva Jintcharadze
Email: jincharadzeshako@gmail.com
Phone: +1 339 241 2419
Location: Boston, Massachusetts

GitHub: github.com/navyforses/ALEKSANDRA_BRAIN (private, access on request)

---

*"Unknown potential — not limited outcomes."*

*Every 6 hours, a new search. Every week, a new hypothesis.*
*Every month, a new possibility.*

*A brain that never sleeps, for a child who deserves every chance.*
