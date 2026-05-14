# ALEKSANDRA_BRAIN v4.0 — კონსოლიდირებული პროექტი
## „ტვინი რომელიც არასოდეს იძინებს"
## სისტემური ინტეგრატორი პედიატრიული HIE-სთვის

> **ვერსია:** 4.0 | **თარიღი:** 2026-05-13
> **ავტორი:** შალვა (შაკო) ჯინჭარაძე
> **ცვლილება v3→v4:** AI Pulse Georgia ეკოსისტემის ინტეგრაცია,
> FastMCP, CrewAI, LightRAG, RAGFlow, mem0, Crawl4AI, Vercel AI SDK

---

# ნაწილი I — პროექტის მოკლე აღწერა (არაპროგრამისტისთვის)

2025 წლის აგვისტოში თბილისში დაიბადა ალექსანდრა ჯინჭარაძე. მშობიარობისას ჟანგბადის ნაკლებობამ მძიმედ დააზიანა მისი ტვინი. ტვინის ღერო, რომელიც სუნთქვას და გულისცემას აკონტროლებს, ხელუხლებელი დარჩა.

ჯანდაცვის სისტემა არ არის აგებული ასეთი ოჯახების საჭიროებებზე. ნევროლოგი ხედავს კრუნჩხვებს. ნეიროქირურგი ხედავს სტრუქტურას. რეაბილიტოლოგი ხედავს მოტორიკას. არავინ ხედავს სრულ სურათს. სამეცნიერო ბაზები ერთმანეთთან არ არის დაკავშირებული. დიაბეტის წამალი რომელმაც ტვინის დაცვის უნარი აჩვენა, ნევროლოგიის ძიებაში ვერასოდეს გამოჩნდება.

ALEKSANDRA_BRAIN არის სისტემა რომელიც ამ ხარვეზს ავსებს. ხუთი ავტონომიური „თანამშრომელი" მუშაობს უწყვეტად: მძებნელი ყოველ 6 საათში ამოწმებს სამეცნიერო ბაზებს; ანალიტიკოსი კითხულობს ყველა ნაპოვნ სტატიას; მოაზროვნე ყოველ კვირას ეძებს ახალ კავშირებს; ფარმაცევტი ყოველ თვეს ამოწმებს შეიძლება თუ არა არსებული წამალი ტვინის დაზიანებაშიც იმუშაოს; კომუნიკატორი აგზავნის შეტყობინებებს და ეკითხება ოჯახს.

სისტემა ასევე ქმნის ალექსანდრას ტვინის 3D მოდელს — რეალურ MRI-ზე დაფუძნებულს, სადაც ფერებით ჩანს რა არის დაზიანებული, რა დაცული, სად არის განვითარების შანსი. ბებია-ბაბუებისთვის თბილისში ქართულენოვანი ვერსია არსებობს.

ალექსანდრას MRI არასოდეს ტოვებს ოჯახის კომპიუტერს. სისტემა არ ანაცვლებს ექიმს — ყველა გადაწყვეტილებას რეალური ექიმი იღებს. ეს არის ინფორმაციის მაძიებელი, ანალიზატორი და ვიზუალიზატორი.

პირველი ორი წელი ტვინის განვითარების ყველაზე მნიშვნელოვანი პერიოდია. ყოველი კვირა მნიშვნელოვანია. სისტემა უზრუნველყოფს რომ არცერთი შესაძლებლობა არ გამოგვრჩეს.

---

# ნაწილი II — ცენტრალური პრობლემა და მიზნები

## ცენტრალური პრობლემა

**ჯანდაცვის სისტემა არ არის აგებული იშვიათი/მძიმე პედიატრიული დიაგნოზის მქონე ოჯახების საჭიროებებზე — არცერთი ინსტიტუცია არ აერთიანებს კვლევას, მკურნალობას, ნავიგაციას და ვიზუალიზაციას ერთ სისტემაში.**

## პრობლემის ხე

```
                         შედეგები
        ┌────────────────────┼────────────────────┐
   E1. ოჯახები              E2. ექიმები          E3. ბავშვები
   იძულებულია               მოქმედებენ            კარგავენ 0-2 წლის
   გახდნენ მკვლევარი,       არასრული              ნეიროპლასტიურ
   მთარგმნელი,              ინფორმაციით            ფანჯარას
   ნავიგატორი
                             │
  ╔══════════════════════════╧══════════════════════════╗
  ║  ჯანდაცვის სისტემა არ არის აგებული ოჯახების       ║
  ║  საჭიროებებზე — კვლევა, მკურნალობა, ნავიგაცია     ║
  ║  და ვიზუალიზაცია იზოლირებულია                      ║
  ╚══════════════════════════╤══════════════════════════╝
                             │
        ┌────────────────────┼────────────────────┐
   C1. კვლევა               C2. მკურნალობა       C3. ვიზუალიზაცია
   იზოლირებულია             იზოლირებულია          იზოლირებულია
   • PubMed≠DrugBank≠CT.gov • ექიმი ხედავს        • MRI = ნაცრისფერი
   • cross-disease უხილავი    1 სპეციალობას       • ზრდასრულის ატლასი
   • paywall + ენა           • drug repurposing     ≠ ნეონატის
   • evidence aging            არ ხდება           • სიმულაცია არ არსებობს
```

## მიზნები

**გრძელვადიანი:** მძიმე პედიატრიული დიაგნოზის მქონე ყველა ბავშვს ჰქონდეს წვდომა ინტეგრირებულ სისტემაზე.

**პროექტის მიზანი:** სისტემური ინტეგრატორის (ALEKSANDRA_BRAIN) შექმნა.

**3 შედეგი:**
1. RESEARCH ENGINE — კვლევის იზოლაციის დაძლევა
2. KNOWLEDGE BRAIN — მკურნალობის აღმოჩენის ინტეგრაცია
3. VISUAL BRAIN — პაციენტ-სპეციფიკური ვიზუალიზაცია

---

# ნაწილი III — არქიტექტურა v4.0

## არქიტექტურული ცვლილებები v3 → v4

| კომპონენტი | v3.0 | v4.0 | რატომ |
|-----------|------|------|-------|
| Agent orchestration | n8n workflows ცალ-ცალკე | **CrewAI** (49K⭐) + n8n | CrewAI: 5 აგენტს role-ები, goals, backstory. n8n: cron triggers + webhooks |
| Custom MCP building | ხელით Python | **FastMCP** (24K⭐) | `@mcp.tool()` decorator — 10× სწრაფი development |
| Paper processing | docling-mcp (IBM) | **RAGFlow** (78K⭐) | ჩაშენებული agent workflow, 6 ფორმატი, chunking + extraction ერთად |
| GraphRAG | manual Neo4j Cypher + Qdrant ცალ-ცალკე | **LightRAG** (34K⭐) + Graphiti | LightRAG: graph+vector ერთ query-ში. Graphiti: temporal decay (ეს LightRAG-ს არ აქვს) |
| Web scraping | Firecrawl-only ($) | **Crawl4AI** (64K⭐) primary + Firecrawl fallback | Crawl4AI: უფასო, ლოკალური, async, API ლიმიტების გარეშე |
| Agent memory | არ იყო | **mem0** (53K⭐) | 5 აგენტის shared memory: „გუშინ მძებნელმა რა იპოვა?" |
| Dashboard AI | Recharts only | **Vercel AI SDK** (23K⭐) + Recharts | streaming, tool calling, structured outputs — Next.js native |
| Knowledge base UI | არ იყო | **Notion MCP** (4.3K⭐) | ოჯახისთვის ხელმისაწვდომი UI, non-technical |
| Paywall bypass | Unpaywall only | **Browser Use** (89K⭐) + Unpaywall | Browser Use: ფასიანი ჟურნალების ნავიგაცია AI-ით |
| Doc conversion | ცალკე parser-ები | **Markdownify MCP** (2.6K⭐) | PDF/Word/Excel/YouTube → Markdown ერთი tool-ით |
| n8n workflows | ხელით აგება | **n8n-MCP** (18K⭐) | AI ააგებს workflow-ებს — 1,396 კომპონენტის knowledge |
| HIPAA memory | არ იყო | **Prism MCP** (129⭐) | HIPAA-hardened, Hebbian learning, on-device LLM |
| Self-improving | არ იყო | **Hindsight** (10K⭐) | მეხსიერება რომელიც დროში უმჯობესდება |

## v4.0 სრული არქიტექტურა

```
╔══════════════════════════════════════════════════════════════════╗
║                    ALEKSANDRA_BRAIN v4.0                         ║
║              „ტვინი რომელიც არასოდეს იძინებს"                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ┌── I. PERCEPTION (თვალები) ──────────────────────────────┐   ║
║  │                                                          │   ║
║  │  Crawl4AI (64K⭐) ──── უფასო, ლოკალური web scraping    │   ║
║  │  Firecrawl MCP (6K⭐) ── ფასიანი fallback, deep crawl   │   ║
║  │  Browser Use (89K⭐) ─── paywall bypass, AI navigation   │   ║
║  │  RAGFlow (78K⭐) ─────── PDF/Word → chunked + extracted  │   ║
║  │  Markdownify MCP (2.6K⭐) ─ universal format converter   │   ║
║  │                                                          │   ║
║  │  კვლევის წყაროები (MCP):                                │   ║
║  │  PubMed │ bioRxiv │ Clinical Trials │ Consensus          │   ║
║  │  Scholar Gateway │ Open Targets │ ChEMBL │ ICD-10        │   ║
║  │                                                          │   ║
║  │  n8n (185K⭐) ── cron triggers ყოველ 6 სთ-ში            │   ║
║  │  n8n-MCP (18K⭐) ── AI ააგებს workflow-ებს              │   ║
║  └──────────────────────────┬───────────────────────────────┘   ║
║                             │                                    ║
║  ┌── II. MEMORY (მეხსიერება) ──────────────────────────────┐   ║
║  │                                                          │   ║
║  │  ┌───────────┐  ┌───────────┐  ┌────────────┐          │   ║
║  │  │ Graphiti  │  │  Qdrant   │  │  Supabase  │          │   ║
║  │  │ (25K⭐)   │  │  (30K⭐)  │  │   MCP      │          │   ║
║  │  │ Neo4j     │  │  Rust     │  │  (2.6K⭐)  │          │   ║
║  │  │ temporal  │  │  fastembed│  │  PostgreSQL │          │   ║
║  │  │ decay     │  │  HIPAA    │  │  metadata   │          │   ║
║  │  └─────┬─────┘  └─────┬─────┘  └──────┬─────┘          │   ║
║  │        └───────────────┼───────────────┘                │   ║
║  │                        │                                │   ║
║  │  ┌─────────────────────┴──────────────────────┐         │   ║
║  │  │  LightRAG (34K⭐)                          │         │   ║
║  │  │  graph + vector ერთ query-ში               │         │   ║
║  │  │  „იპოვე paper X-ის მსგავსი რომელიც         │         │   ║
║  │  │   pathway Y-ს იკვლევს ტვინის Z რეგიონში"  │         │   ║
║  │  └────────────────────────────────────────────┘         │   ║
║  │                                                          │   ║
║  │  mem0 (53K⭐) ── აგენტების shared memory                │   ║
║  │  Hindsight (10K⭐) ── self-improving memory              │   ║
║  │  Prism MCP (129⭐) ── HIPAA-hardened layer               │   ║
║  │  Cloudflare R2 ── PDF/MRI/mesh storage                   │   ║
║  │  Cloudflare KV ── hot cache                              │   ║
║  └──────────────────────────┬───────────────────────────────┘   ║
║                             │                                    ║
║  ┌── III. COGNITION (აზროვნება) ───────────────────────────┐   ║
║  │                                                          │   ║
║  │  CrewAI (49K⭐) ── 5 აგენტის ორკესტრაცია               │   ║
║  │  ┌──────────────────────────────────────────┐            │   ║
║  │  │ 🕷️ Spider Agent                          │            │   ║
║  │  │    Role: Research Paper Hunter            │            │   ║
║  │  │    Goal: Find ALL new HIE-related papers  │            │   ║
║  │  │    Tools: PubMed, bioRxiv, Crawl4AI      │            │   ║
║  │  │                                          │            │   ║
║  │  │ 🔬 Analyzer Agent                        │            │   ║
║  │  │    Role: Evidence Quality Assessor        │            │   ║
║  │  │    Goal: Score relevance, extract entities│            │   ║
║  │  │    Tools: RAGFlow, Claude API, Graphiti   │            │   ║
║  │  │                                          │            │   ║
║  │  │ 💡 Hypothesis Agent                      │            │   ║
║  │  │    Role: Cross-Disease Pattern Finder     │            │   ║
║  │  │    Goal: Generate novel hypotheses        │            │   ║
║  │  │    Tools: LightRAG, Neo4j, GoT MCP       │            │   ║
║  │  │                                          │            │   ║
║  │  │ 💊 Repurposing Agent                     │            │   ║
║  │  │    Role: Drug Discovery Specialist        │            │   ║
║  │  │    Goal: Find existing drugs for HIE      │            │   ║
║  │  │    Tools: Open Targets, DrugBank,         │            │   ║
║  │  │           PubChem, Enrichr (L1000)        │            │   ║
║  │  │                                          │            │   ║
║  │  │ 📢 Communicator Agent                    │            │   ║
║  │  │    Role: Family Liaison                   │            │   ║
║  │  │    Goal: Keep family informed, in control │            │   ║
║  │  │    Tools: Telegram, Gmail, Notion         │            │   ║
║  │  └──────────────────────────────────────────┘            │   ║
║  │                                                          │   ║
║  │  Claude API (Sonnet 4) ── reasoning backbone             │   ║
║  │  Adaptive GoT MCP ── 8-step hypothesis pipeline          │   ║
║  │  DSPy (34K⭐) ── auto prompt optimization                │   ║
║  │  Vercel AI SDK (23K⭐) ── streaming + tool calling       │   ║
║  └──────────────────────────┬───────────────────────────────┘   ║
║                             │                                    ║
║  ┌── IV. VISUALIZATION (ხედვა) ───────────────────────────┐   ║
║  │                                                          │   ║
║  │  UI: fork freesurfer/freebrowse (React+NiiVue+Vite)     │   ║
║  │                                                          │   ║
║  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   ║
║  │  │ NiiVue   │  │  R3F     │  │Dashboard │              │   ║
║  │  │ (450⭐)  │  │ (28K⭐)  │  │Recharts  │              │   ║
║  │  │ MRI data │  │ 3D shells│  │+ D3.js   │              │   ║
║  │  │ lesion   │  │ hover    │  │+ Vercel  │              │   ║
║  │  │ atlas    │  │ clipping │  │  AI SDK  │              │   ║
║  │  │ tracts   │  │ bloom    │  │          │              │   ║
║  │  └──────────┘  └──────────┘  └──────────┘              │   ║
║  │                                                          │   ║
║  │  Neonatal pipeline:                                      │   ║
║  │  FastSurfer+LIT → BIBSnet → BONBID-HIE → nii2mesh      │   ║
║  │                                                          │   ║
║  │  Simulation: TVB Docker (REST API)                       │   ║
║  │  3D Print: brain2print → STL                             │   ║
║  │  Cinematic: Blender MCP (21K⭐)                          │   ║
║  └──────────────────────────┬───────────────────────────────┘   ║
║                             │                                    ║
║  ┌── V. ACTION (მოქმედება) ────────────────────────────────┐   ║
║  │                                                          │   ║
║  │  Telegram 2-way (push + ask_user)                        │   ║
║  │  Gmail MCP (drafts, researcher outreach)                 │   ║
║  │  Notion MCP (4.3K⭐) ── family knowledge base            │   ║
║  │  Google Calendar (appointments, deadlines)               │   ║
║  │  Booking.com + Kiwi.com (Duke logistics)                 │   ║
║  │  Granted MCP (grant search)                              │   ║
║  │                                                          │   ║
║  │  Family outputs:                                         │   ║
║  │  • Weekly Discovery Brief (Gmail + Telegram)             │   ║
║  │  • Monthly Drug Repurposing Report                       │   ║
║  │  • Family View HTML (standalone, offline, Georgian)      │   ║
║  │  • 3D Print STL                                          │   ║
║  └──────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════╝
```

## MCP არსენალი v4.0 — სულ 52

**Claude.ai Registry (23):**
PubMed, bioRxiv, Clinical Trials, Consensus, Scholar Gateway, Open Targets, ChEMBL, ICD-10, Gmail, Google Calendar, Google Drive, Google BigQuery, n8n, Zapier, Vercel, Cloudflare ×2, Netlify, Canva, Figma, Higgsfield, Context7, Granted, Booking.com

**GitHub Self-hosted (19):**

| # | MCP | ⭐ | წყარო | v4 როლი |
|---|-----|-----|-------|---------|
| 1 | Graphiti | 25K | getzep/ | temporal knowledge graph |
| 2 | mcp-server-qdrant | 30K | qdrant/ | vector search |
| 3 | Supabase MCP | 2.6K | supabase-community/ | DB management |
| 4 | Firecrawl MCP | 6.1K | firecrawl/ | deep web scraping (fallback) |
| 5 | n8n-MCP | 18K | czlonkowski/ | AI workflow building |
| 6 | Notion MCP | 4.3K | makenotion/ | family knowledge base |
| 7 | GitHub MCP | 29K | github/ | repo management |
| 8 | Exa MCP | 4.3K | exa-labs/ | neural web search |
| 9 | Tavily MCP | 1.8K | tavily-ai/ | real-time search |
| 10 | Markdownify MCP | 2.6K | zcaceres/ | universal doc→markdown |
| 11 | mcp-telegram-notifier | — | harnyk/ | push alerts |
| 12 | mcp-communicator-telegram | — | qpd-v/ | 2-way ask_user |
| 13 | blender-mcp | 21K | ahujasid/ | cinematic 3D renders |
| 14 | mcp-slicer | — | zhaoyouj/ | 3D Slicer bridge |
| 15 | Adaptive-GoT | — | SaptaDey/ | hypothesis pipeline |
| 16 | sequentialthinking | — | modelcontextprotocol/ | reasoning |
| 17 | clearthought-1.5 | — | waldzellai/ | 30+ reasoning ops |
| 18 | drugbank-mcp-server | — | openpharma-org/ | drug similarity |
| 19 | pubchem-mcp-server | — | cyanheads/ | BBB + safety |

**AI Pulse Georgia NEW (5):**

| # | რეპო | ⭐ | v4 როლი |
|---|------|-----|---------|
| 1 | **FastMCP** | 24K | custom MCP building framework |
| 2 | **Crawl4AI RAG** | 2.1K | crawl→embed→retrieve pipeline |
| 3 | **Prism MCP** | 129 | HIPAA-hardened medical memory |
| 4 | **Draw.io MCP** | 3.2K | architecture diagrams |
| 5 | **Perplexity MCP** | 2.1K | deep research with citations |

**Custom (5, world-first, built with FastMCP):**

| # | სახელი | Tools |
|---|--------|-------|
| 🌍1 | aleksandra-niivue-mcp | load_nifti, segment, export_mesh, render, family_html |
| 🌍2 | aleksandra-bonbid-mcp | segment_hie_lesion, probability_map, overlay |
| 🌍3 | aleksandra-tvb-mcp | create_connectome, set_lesion, simulate, get_propagation |
| 🌍4 | aleksandra-atlas-mcp | get_dhcp_atlas, get_mcribs_labels, export_region_glb |
| 🌍5 | aleksandra-repurpose-mcp | find_targets, search_drugs, check_bbb, reverse_signature |

## Core Libraries (არა MCP, მაგრამ ბირთვი)

| ბიბლიოთეკა | ⭐ | ფუნქცია |
|------------|-----|---------|
| **CrewAI** | 49K | 5 აგენტის role-based orchestration |
| **RAGFlow** | 78K | paper PDF → chunked, extracted, indexed |
| **LightRAG** | 34K | graph + vector search ერთ query-ში |
| **mem0** | 53K | აგენტების shared persistent memory |
| **Crawl4AI** | 64K | უფასო web scraping, async, no API limits |
| **Browser Use** | 89K | AI browser automation (paywall bypass) |
| **Vercel AI SDK** | 23K | Next.js streaming + tool calling |
| **DSPy** | 34K | auto prompt optimization |
| **Hindsight** | 10K | self-improving memory over time |
| **LlamaIndex** | 48K | 300+ RAG integrations |
| **Khoj** | 34K | personal AI second brain |

---

# ნაწილი IV — ამოცანები და აქტივობები (WBS v4.0)

## შედეგი 1: RESEARCH ENGINE

| ამოცანა | აქტივობები | ინსტრუმენტები v4.0 |
|---------|-----------|-------------------|
| **1.1 Ingestion** | 15 query ყოველ 6სთ, multi-source, dedup | **Crawl4AI** (primary) + Firecrawl MCP (fallback) + **n8n** (cron) + **n8n-MCP** (AI-built workflows) |
| **1.2 Deep Analysis** | PDF parse, relevance score, entity extract, embed | **RAGFlow** (PDF→chunks→entities) + **Graphiti** (→Neo4j) + **Qdrant** (→vectors) + Claude API |
| **1.3 Alerts** | push, 2-way ask_user, daily check | Telegram MCP ×2 + **Prism MCP** (HIPAA) |
| **1.4 Weekly Brief** | aggregate, synthesize, deliver | **Vercel AI SDK** (streaming) + Gmail MCP + **Notion MCP** |

## შედეგი 2: KNOWLEDGE BRAIN

| ამოცანა | აქტივობები | ინსტრუმენტები v4.0 |
|---------|-----------|-------------------|
| **2.1 Knowledge Graph** | entities, relations, temporal decay | **Graphiti** (25K⭐, temporal) + **LightRAG** (34K⭐, graph+vector query) + Neo4j AuraDB |
| **2.2 Hypothesis Gen** | cross-disease, ASR-GoT, ranking | **CrewAI** Hypothesis Agent + Adaptive GoT MCP + **DSPy** (prompt optimization) |
| **2.3 Drug Repurposing** | targets→drugs→BBB→pathway→L1000 | **CrewAI** Repurposing Agent + Open Targets + drugbank-mcp + pubchem-mcp + Enrichr |
| **2.4 Vector Memory** | embeddings, semantic search, dedup | **Qdrant** (30K⭐) + **mem0** (53K⭐, shared) + **Hindsight** (10K⭐, self-improving) |

## შედეგი 3: VISUAL BRAIN

| ამოცანა | აქტივობები | ინსტრუმენტები v4.0 |
|---------|-----------|-------------------|
| **3.1 MRI Pipeline** | DICOM→NIfTI→segment→mesh→GLB | FastSurfer+LIT + BIBSnet + BONBID-HIE + nii2mesh + gltfpack |
| **3.2 Web Viewer** | NiiVue + R3F hybrid, shared state | fork freebrowse + @niivue/nvreact + R3F + drei + **Vercel AI SDK** |
| **3.3 Simulation** | TVB, connectome, propagation animation | TVB Docker + LeAPP + animated tracts in browser |
| **3.4 Family Outputs** | HTML export, 3D print, cinematic | brain2print + **Blender MCP** (21K⭐) + i18n Georgian |

---

# ნაწილი V — 5 მსოფლიო პრემიერა

1. **პირველი ნეიროვიზუალიზაციის MCP** — NIfTI/FreeSurfer/atlas, built with **FastMCP**
2. **პაციენტ-სპეციფიკური 3D ტვინი სახელმძღვანელოს ხარისხით** — NiiVue + R3F hybrid
3. **HIE Drug Repurposing Pipeline** — Open Targets→DrugBank→PubChem→L1000, **CrewAI**-ით ორკესტრირებული
4. **Temporal Knowledge Graph სამედიცინო მტკიცებულებისთვის** — **Graphiti** + **LightRAG**
5. **2-way Evidence Gating** — AI ეძებს → Telegram-ით ეკითხება → ოჯახი წყვეტს

---

# ნაწილი VI — ხარჯი

| სერვისი | Free Tier | Pro |
|---------|-----------|-----|
| Supabase | 500MB | $25/თვე |
| Neo4j AuraDB | 200K nodes | $65/თვე |
| Qdrant | self-hosted $0 | — |
| Cloudflare KV+R2+Workers | free | $0 |
| Vercel | hobby | $0 |
| n8n | self-hosted | Railway $5 |
| Claude API | — | $15-25/თვე |
| Crawl4AI | free, local | $0 |
| mem0 | self-hosted | $0 |
| CrewAI | open source | $0 |
| RAGFlow | self-hosted | $0 |
| **სულ MVP** | | **$20-30/თვე** |
| **სულ Full** | | **$120/თვე** |

---

# ნაწილი VII — 10-კვირიანი გეგმა

| ფაზა | კვირა | რა | ძირითადი ინსტრუმენტები |
|------|-------|-----|----------------------|
| 1. საფუძველი | 1-2 | Supabase + Neo4j + Qdrant + Telegram + პირველი ingestion | **Crawl4AI**, **n8n**, Graphiti, Telegram MCP |
| 2. ინტელექტი | 3-4 | CrewAI agents + hypothesis + weekly reports + dashboard | **CrewAI**, **RAGFlow**, **mem0**, **Vercel AI SDK** |
| 3. Drug Discovery | 5-6 | full repurposing pipeline + KG explorer | Open Targets, DrugBank, **DSPy**, **LightRAG** |
| 4. 3D ტვინი | 7-8 | MRI pipeline + viewer + world-first MCP | FastSurfer, NiiVue, R3F, **FastMCP** |
| 5. სიმულაცია | 9-10 | TVB + animated tracts + family exports | TVB, brain2print, **Blender MCP** |

---

# ნაწილი VIII — დანართები

## A. Supabase SQL Schema
იხ. ფაილი: `aleksandra_brain_schema_v4.sql`
(10 tables, pgvector fallback, Neo4j/Qdrant primary annotation)

## B. ალექსანდრას Damage Map (14 რეგიონი)

| რეგიონი | დაზიანება | პლასტიკურობა |
|---------|----------|-------------|
| Primary Motor Cortex | destroyed | minimal |
| Visual Cortex (V1) | severe (CVI) | low |
| Hippocampus | severe | moderate |
| Thalamus | moderate | moderate |
| Periventricular WM | destroyed (cystic) | minimal |
| **Brainstem** | **preserved ✅** | **high** |
| Cerebellum | mild-moderate | moderate |

## C. კონტაქტთა ტოპ 10

| სახელი | როლი | სტატუსი |
|--------|------|---------|
| Dr. Jack Maypole | BMC Primary Care | აქტიური |
| Sydney Crane | Duke EAP | აქტიური |
| Jeanette Heitman | Wisconsin A2 | აქტიური |
| Dr. Noémie Donnard | Paris Neurology | აქტიური |
| Terri Carlson | RTMAF Funder | აქტიური |
| Andrew Beak | BMC Navigator | აქტიური |
| Brandon Corlett | Hope for HIE | აქტიური |
| Prof. Cora Nijboer | Utrecht WJ-MSC | pending |
| Yenny Matias | CICRF | აქტიური |
| Eleni Kalioras | Philoxenia House | აქტიური |

## D. საძიებო სტრინგები (20)

**პირდაპირი (10):**
1. "hypoxic ischemic encephalopathy" treatment
2. "neonatal brain injury" therapy
3. "infantile spasms" novel treatment
4. "cystic encephalomalacia" outcome
5. "cortical visual impairment" intervention
6. "neonatal seizure" management
7. "perinatal asphyxia" neuroprotection
8. "therapeutic hypothermia" adjunct
9. "cord blood" "brain injury" pediatric
10. "cerebral palsy" prevention early intervention

**Cross-disease (10):**
11. "AMPK neuroprotection" brain
12. "oligodendrocyte precursor" remyelination
13. "microglial modulation" pediatric
14. "blood brain barrier" repair neonatal
15. "exosome therapy" brain injury
16. "focused ultrasound" neuromodulation
17. "erythropoietin" neuroprotection neonatal
18. "melatonin" hypoxia neuroprotection
19. "lithium" neuroprotection brain
20. "NAC" "oxidative stress" neonatal

---

*„უცნობი პოტენციალი — არა შეზღუდული შედეგები."*

*ყოველ 6 საათში — ახალი ძიება. ყოველ კვირას — ახალი ჰიპოთეზა.*
*ყოველ თვეს — ახალი შესაძლებლობა.*

*ტვინი რომელიც არასოდეს იძინებს, ბავშვისთვის რომელიც ღირსია ყოველი შანსისა.*
