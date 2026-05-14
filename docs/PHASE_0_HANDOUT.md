# ფუნდამენტის ჰენდაუთი
## პრომპტები, ლინკები, ინსტალაციის ინსტრუქციები

> **როგორ გამოვიყენოთ:** ეს არის „განხორციელების გეგმის" პრაქტიკული თანმხლები.
> გეგმა გეუბნება **რატომ** და **რა**, ჰენდაუთი გეუბნება **როგორ**.
> თითოეული პუნქტი შეესაბამება გეგმის სექციას.
>
> ⚠️ API key-ები არ ჩასვა Claude.ai საუბარში — გამოიყენე .env ფაილი.

---

## პუნქტი 1.1 — Supabase

**ლინკი:** https://supabase.com/dashboard

**ნაბიჯები:**
1. supabase.com → „Start your project" → GitHub-ით login
2. „New project" → სახელი: `aleksandra-brain` → რეგიონი: `us-east-1` → DB password ჩაინიშნე
3. Settings → API → დააკოპირე `Project URL` და `anon public key` და `service_role key`
4. .env ფაილში ჩაწერე:
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbG...
SUPABASE_SERVICE_ROLE_KEY=eyJhbG...
```

**პრომპტი 1.1:**
```
Supabase project მზადაა. წაიკითხე project knowledge-დან
aleksandra_brain_schema.sql და დამიწერე ეტაპობრივი
migration script რომელიც:
1. ჯერ extensions (pgvector, pg_trgm)
2. შემდეგ tables (10 ცხრილი სწორი თანმიმდევრობით, foreign keys!)
3. შემდეგ indexes
4. შემდეგ functions (4)
5. შემდეგ views (2)
6. ბოლოს RLS policies

SQL Editor-ში copy-paste-ისთვის მზა ფორმატში მომეცი.
```

**შედეგის შემოწმება:** Table Editor-ში ხედავ 10 ცხრილს? ✅

---

## პუნქტი 1.2 — Neo4j + Graphiti

**ლინკები:**
- Neo4j AuraDB Free: https://neo4j.com/cloud/aura-free/
- Graphiti: https://github.com/getzep/graphiti
- Graphiti docs: https://docs.getzep.com/graphiti

**ნაბიჯები:**
1. neo4j.com → „Start Free" → Google ან GitHub login
2. Create Free Instance → neo4j 5 → სახელი: `aleksandra-brain`
3. დააკოპირე Connection URI, Username, Password
4. .env:
```
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=xxxx
```

**პრომპტი 1.2:**
```
Neo4j AuraDB მზადაა. გთხოვ:

1. დამიწერე Python script რომელიც graphiti-core-ით:
   a) უკავშირდება Neo4j-ს (.env-დან credentials)
   b) ქმნის entity types:
      - Drug (name, mechanism, bbb_penetration, pediatric_safe)
      - Gene (name, ensembl_id, expression_in_neonatal_brain)
      - Pathway (name, type, relevance_to_hie)
      - BrainRegion (name, function, damage_status, plasticity_potential)
      - Paper (title, doi, year, relevance_score)
      - Trial (nct_id, title, status, phase)
      - Contact (name, role, institution, email, follow_up_date)
      - Hypothesis (title, description, confidence, status)
      - Patient (name, dob, diagnosis)
   c) ქმნის relationship types:
      STUDIES, TARGETS, ACTIVE_IN, DAMAGED_IN, AUTHORED,
      BASED_ON, SUPPORTS, CONTRADICTS, MODULATES
   d) ქმნის test data:
      Patient(Aleksandra) -[:HAS_CONDITION]-> Diagnosis(HIE)
      BrainRegion(Brainstem) -[:DAMAGED_IN {status:'preserved'}]-> Patient
      BrainRegion(Motor_Cortex) -[:DAMAGED_IN {status:'destroyed'}]-> Patient
   e) verification query: MATCH (p:Patient)-[r]->(b:BrainRegion) RETURN p,r,b

2. requirements.txt-ში დაამატე graphiti-core, neo4j
```

**შედეგის შემოწმება:** Neo4j Browser-ში (console.neo4j.io) ხედავ Aleksandra node-ს + Brainstem/Motor_Cortex? ✅

---

## პუნქტი 1.3 — Qdrant

**ლინკები:**
- Qdrant: https://github.com/qdrant/qdrant
- Qdrant Docker: https://qdrant.tech/documentation/quick-start/
- fastembed: https://github.com/qdrant/fastembed

**ნაბიჯები:**
1. Docker Desktop დააინსტალირე (თუ არ გაქვს): https://www.docker.com/products/docker-desktop/
2. ტერმინალში: `docker run -p 6333:6333 qdrant/qdrant`
3. ბრაუზერში: http://localhost:6333/dashboard — ხედავ Qdrant UI-ს?

**პრომპტი 1.3:**
```
Qdrant Docker-ით ეშვება localhost:6333.

დამიწერე Python script:
1. fastembed-ით ლოკალური embedding model-ის ჩატვირთვა
   (BAAI/bge-small-en-v1.5, არა OpenAI!)
2. 3 collection-ის შექმნა: papers, therapies, hypotheses
   (vector size = fastembed model-ის dim)
3. test: „Melatonin shows neuroprotective effects in neonatal HIE"
   → embed → upsert papers collection-ში
4. test search: „neuroprotection brain injury" → იპოვის melatonin paper-ს?
5. requirements.txt: qdrant-client, fastembed
```

**შედეგის შემოწმება:** localhost:6333/dashboard → 3 collection, papers-ში 1 point? ✅

---

## პუნქტი 1.4 — Cloudflare R2 + KV

**ლინკი:** https://dash.cloudflare.com/

**ნაბიჯები:**
1. cloudflare.com → Sign Up (უფასო)
2. R2 Object Storage → Create Bucket → `aleksandra-brain-storage`
3. Workers & Pages → KV → Create Namespace → `aleksandra-brain-cache`
4. My Profile → API Tokens → Create Token → R2 read/write
5. .env:
```
CLOUDFLARE_ACCOUNT_ID=xxxx
CLOUDFLARE_R2_ACCESS_KEY_ID=xxxx
CLOUDFLARE_R2_SECRET_ACCESS_KEY=xxxx
CLOUDFLARE_KV_NAMESPACE_ID=xxxx
```

**შედეგის შემოწმება:** R2-ში bucket ჩანს? KV namespace ჩანს? ✅

---

## პუნქტი 2.1 — n8n

**ლინკები:**
- Railway: https://railway.app/
- n8n docs: https://docs.n8n.io/

**ნაბიჯები:**
1. railway.app → GitHub login
2. „New Project" → „Deploy Template" → ეძებე „n8n" → Deploy
3. deploy-ის შემდეგ Settings → Networking → Generate Domain
4. მიიღებ URL: `https://xxxx.railway.app`
5. .env: `N8N_URL=https://xxxx.railway.app`

**პრომპტი 2.1:**
```
n8n ეშვება Railway-ზე: [URL].

დამიწერე n8n workflow JSON (import-ისთვის მზა):

Workflow 1: „Test Heartbeat"
- Schedule Trigger: ყოველ 6 საათში (0 */6 * * *)
- HTTP Request: GET https://httpbin.org/get
- IF: status = 200
  - Telegram: „✅ BRAIN heartbeat OK [timestamp]"
- ELSE:
  - Telegram: „🔴 BRAIN heartbeat FAILED"

Telegram credentials:
- Bot Token: [ამას მე ჩავწერ]
- Chat ID: [ამას მე ჩავწერ]

n8n-ში import → Workflows → Import from JSON
```

**შედეგის შემოწმება:** n8n dashboard-ში workflow active? Telegram-ში test message? ✅

---

## პუნქტი 2.2 — Telegram Bot

**ლინკი:** https://t.me/BotFather

**ნაბიჯები:**
1. Telegram-ში: ეძებე @BotFather → `/start` → `/newbot`
2. სახელი: `ALEKSANDRA BRAIN` → username: `aleksandra_brain_bot`
3. BotFather მოგცემს token: `123456:ABC-DEF...` → .env:
```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
```
4. Telegram → New Group → „ALEKSANDRA_BRAIN Alerts"
5. bot-ი დაამატე ჯგუფში
6. Chat ID-ის გასაგებად: ჯგუფში დაწერე რამე → `https://api.telegram.org/bot[TOKEN]/getUpdates` → `chat.id` დააკოპირე
```
TELEGRAM_CHAT_ID=-100xxxxxxx
```

**შედეგის შემოწმება:** ჯგუფში bot-ი ჩანს? getUpdates-ით chat_id მიიღე? ✅

---

## პუნქტი 3.1 — Claude API

**ლინკი:** https://console.anthropic.com/

**ნაბიჯები:**
1. console.anthropic.com → login
2. API Keys → Create Key → სახელი: `aleksandra-brain`
3. .env:
```
ANTHROPIC_API_KEY=sk-ant-api03-xxxx
```

**პრომპტი 3.1:**
```
Claude API key მაქვს.

დამიწერე Python test script:
1. anthropic SDK-ით Sonnet 4-ს უგზავნის:
   „ALEKSANDRA_BRAIN system check. Respond with: BRAIN_OK"
2. პასუხი = „BRAIN_OK"? → print(„✅ Claude API works")
3. error handling: API key არასწორია? rate limit? network?
```

**შედეგის შემოწმება:** „✅ Claude API works" ტერმინალში? ✅

---

## პუნქტი 3.2 — CrewAI 5 Agents

**ლინკები:**
- CrewAI: https://github.com/crewaiinc/crewai
- CrewAI docs: https://docs.crewai.com/

**პრომპტი 3.2:**
```
დამიწერე CrewAI project:

/agents/
  spider.py        — role: Research Paper Hunter
  analyzer.py      — role: Evidence Quality Assessor
  hypothesis.py    — role: Cross-Disease Pattern Finder
  repurposing.py   — role: Drug Discovery Specialist
  communicator.py  — role: Family Liaison
crew.py            — orchestrator: sequential process

თითოეულ agent-ში:
- role (ინგლისურად)
- goal (1 წინადადება)
- backstory (2-3 წინადადება, კონტექსტი ალექსანდრას შესახებ)
- tools = []  (ცარიელი, მომდევნო ეტაპზე შეივსება)
- llm = Claude Sonnet 4

crew.py:
- CrewAI Crew with all 5 agents
- Process: sequential
- test task: „Report system status"

test_crew.py:
- crew.kickoff() → 5 agent initialized → print status
```

**შედეგის შემოწმება:** `python test_crew.py` → „Agent Spider initialized..." ×5? ✅

---

## პუნქტი 3.3 — mem0 Shared Memory

**ლინკები:**
- mem0: https://github.com/mem0ai/mem0
- mem0 docs: https://docs.mem0.ai/

**პრომპტი 3.3:**
```
Qdrant ეშვება localhost:6333. CrewAI agents მზადაა.

დამიწერე mem0 integration:
1. mem0 config: Qdrant backend, collection „agent_memory"
2. 5 user_id: spider, analyzer, hypothesis, repurposing, communicator
3. test script:
   a) spider ინახავს: „Found paper: Melatonin in HIE, PMID 12345"
   b) analyzer კითხულობს spider-ის memories → ხედავს melatonin paper-ს?
   c) hypothesis კითხულობს ორივეს → shared memory მუშაობს?
4. CrewAI agent-ებში mem0 integration (memory parameter)
```

**შედეგის შემოწმება:** analyzer-მა წაიკითხა spider-ის შენახული? ✅

---

## პუნქტი 4.1 — GitHub Repo

**ლინკი:** https://github.com/new

**პრომპტი 4.1:**
```
შექმენი ALEKSANDRA_BRAIN GitHub repo-სთვის ყველა ფაილი:

1. README.md (პროექტის 5-წინადადებიანი აღწერა + quick start)
2. .env.example (ყველა key placeholder, კომენტარებით)
3. .gitignore (Python + Node.js + .env + *.nii.gz + *.dcm)
4. docker-compose.yml (Neo4j 5 + Qdrant + n8n, volumes, ports)
5. requirements.txt (crewai, mem0ai, graphiti-core,
   qdrant-client, fastembed, anthropic, supabase, fastmcp)
6. package.json (next, react, @niivue/nvreact,
   @react-three/fiber, @react-three/drei, tailwindcss)

Folder structure:
/agents/spider.py, analyzer.py, hypothesis.py, repurposing.py, communicator.py, crew.py
/mcp/hello_brain.py
/viewer/ (ცარიელი, freebrowse fork-ისთვის)
/workflows/ (n8n JSON files)
/scripts/migrate_papers.py, migrate_contacts.py, test_all.py
/docs/ARCHITECTURE.md, PHASE_0.md
```

**შედეგის შემოწმება:** `git clone` → folder structure სწორია? ✅

---

## პუნქტი 4.2 — Next.js + Vercel

**ლინკები:**
- Vercel: https://vercel.com/
- Next.js: https://nextjs.org/docs
- freebrowse: https://github.com/freesurfer/freebrowse
- shadcn/ui: https://ui.shadcn.com/

**პრომპტი 4.2:**
```
დამიწერე Next.js 14 App Router skeleton:

/app/
  layout.tsx      — Tailwind + shadcn/ui wrapper
  page.tsx        — Dashboard (ცარიელი shell: „ALEKSANDRA_BRAIN v4.0")
  brain/page.tsx  — 3D Viewer (placeholder: „3D Brain Viewer — Coming Soon")
  graph/page.tsx  — KG Explorer (placeholder)
  reports/page.tsx — Reports (placeholder)

Components:
  /components/ui/  — shadcn/ui (button, card, badge)
  /components/Navbar.tsx — ნავიგაცია 4 გვერდზე

Vercel deployment config: vercel.json
Environment variables: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
```

**შედეგის შემოწმება:** `https://aleksandra-brain.vercel.app` → dashboard skeleton? ✅

---

## პუნქტი 4.3 — Docker Compose

**პრომპტი 4.3:**
```
დამიწერე docker-compose.yml:

services:
  neo4j:
    image: neo4j:5
    ports: 7474, 7687
    volumes: neo4j_data
    environment: NEO4J_AUTH (from .env)

  qdrant:
    image: qdrant/qdrant
    ports: 6333
    volumes: qdrant_data

ორივეს .env-დან იღებს credentials.
`docker-compose up -d` → ორივე ეშვება.
```

(n8n Railway-ზეა, ლოკალურად არ გვჭირდება)

**შედეგის შემოწმება:** `docker-compose up` → Neo4j :7474 + Qdrant :6333? ✅

---

## პუნქტი 5.1 — FastMCP

**ლინკები:**
- FastMCP: https://github.com/jlowin/fastmcp
- FastMCP docs: https://gofastmcp.com/

**პრომპტი 5.1:**
```
დამიწერე FastMCP hello-world MCP server:

/mcp/hello_brain.py:
- tool: hello_brain() → „ALEKSANDRA_BRAIN v4.0 is alive"
- tool: brain_stats() → Supabase-დან real counts:
  {papers: N, contacts: N, hypotheses: N, brain_regions: N}
- tool: system_health() → checks Neo4j, Qdrant, Supabase connectivity

FastMCP @mcp.tool() decorator-ებით.
ასევე: როგორ დავარეგისტრირო Claude Desktop-ში
(claude_desktop_config.json-ში)
```

**შედეგის შემოწმება:** Claude-ს ვეუბნები „call brain_stats" → real numbers? ✅

---

## პუნქტი 5.2 — Registry MCP-ების ვერიფიკაცია

**ლინკი:** claude.ai → Settings → Connected Apps / MCP

**23 MCP სერვერის ჩეკლისტი:**

```
□ PubMed          → „search HIE treatment" → results?
□ bioRxiv         → „neonatal brain injury" → results?
□ Clinical Trials → „HIE recruiting" → results?
□ Consensus       → „cord blood brain injury" → results?
□ Scholar Gateway → „encephalomalacia therapy" → results?
□ Open Targets    → „ENSG00000..." → results?
□ ChEMBL          → „melatonin" → results?
□ ICD-10          → „P91.6" → HIE?
□ Gmail           → inbox access?
□ Google Calendar → events visible?
□ Google Drive    → files visible?
□ Google BigQuery → connection?
□ n8n             → workflows visible?
□ Zapier          → connection?
□ Vercel          → projects visible?
□ Cloudflare ×2   → workers/KV/R2?
□ Netlify         → connection?
□ Canva           → connection?
□ Figma           → connection?
□ Context7        → docs query works?
□ Granted         → grant search works?
□ Booking.com     → search works?
```

თუ რომელიმე ❌ → reconnect claude.ai Settings-დან.

---

## პუნქტი 5.3 — GitHub Self-hosted MCP-ები

**პრიორიტეტული 5 (ჯერ ესენი):**

| # | MCP | ინსტალაცია | GitHub |
|---|-----|-----------|--------|
| 1 | Graphiti MCP | `pip install graphiti-core` (MCP ჩაშენებული) | https://github.com/getzep/graphiti |
| 2 | Qdrant MCP | `npx @qdrant/mcp-server-qdrant` | https://github.com/qdrant/mcp-server-qdrant |
| 3 | Supabase MCP | `npx supabase-mcp` | https://github.com/supabase-community/supabase-mcp |
| 4 | Firecrawl MCP | `npx firecrawl-mcp` (API key: firecrawl.dev) | https://github.com/firecrawl/firecrawl-mcp-server |
| 5 | n8n-MCP | `npx n8n-mcp` | https://github.com/czlonkowski/n8n-mcp |

**დანარჩენი 14:**

| # | MCP | GitHub |
|---|-----|--------|
| 6 | Notion MCP | https://github.com/makenotion/notion-mcp-server |
| 7 | GitHub MCP | https://github.com/github/github-mcp-server |
| 8 | Exa MCP | https://github.com/exa-labs/exa-mcp-server |
| 9 | Tavily MCP | https://github.com/tavily-ai/tavily-mcp |
| 10 | Markdownify MCP | https://github.com/zcaceres/markdownify-mcp |
| 11 | Telegram notifier | https://github.com/harnyk/mcp-telegram-notifier |
| 12 | Telegram 2-way | https://github.com/qpd-v/mcp-communicator-telegram |
| 13 | Blender MCP | https://github.com/ahujasid/blender-mcp |
| 14 | GoT MCP | https://github.com/SaptaDey/Adaptive-Graph-of-Thoughts |
| 15 | Sequential thinking | https://github.com/modelcontextprotocol/sequentialthinking |
| 16 | ClearThought | https://github.com/waldzellai/clearthought-1.5 |
| 17 | DrugBank MCP | https://github.com/openpharma-org/drugbank-mcp-server |
| 18 | PubChem MCP | https://github.com/cyanheads/pubchem-mcp-server |
| 19 | 3D Slicer MCP | https://github.com/zhaoyouj/mcp-slicer |

**პრომპტი 5.3:**
```
დამიწერე MCP სერვერების ინსტალაციის და ტესტის script:

თითოეულისთვის:
1. install command
2. claude_desktop_config.json entry
3. test tool call
4. expected result
5. PASS / FAIL

პრიორიტეტული 5 ჯერ, შემდეგ დანარჩენი 14.
```

---

## პუნქტი 5.4 — AI Pulse Georgia MCP-ები

| # | MCP | ინსტალაცია | GitHub |
|---|-----|-----------|--------|
| 1 | FastMCP | `pip install fastmcp` (5.1-ში უკვე) | https://github.com/jlowin/fastmcp |
| 2 | Crawl4AI RAG | `pip install crawl4ai` + MCP config | https://github.com/coleam00/mcp-crawl4ai-rag |
| 3 | Prism MCP | Docker setup | https://github.com/dcostenco/prism-mcp |
| 4 | Draw.io MCP | `npx drawio-mcp` | https://github.com/jgraph/drawio-mcp |
| 5 | Perplexity MCP | `npx @anthropic/perplexity-mcp` (API key: perplexity.ai) | https://github.com/perplexityai/modelcontextprotocol |

---

## პუნქტი 6.1 — Papers მიგრაცია

**პრომპტი 6.1:**
```
Project Knowledge-ში 60+ PDF და კვლევა არის.

გთხოვ:
1. წაიკითხე project knowledge-ს ფაილების სია (project_knowledge_search)
2. თითოეული სამეცნიერო ფაილისთვის extract:
   - title, authors, year, journal, DOI
   - abstract ან პირველი 500 სიტყვა
   - relevance_score (0-1): რამდენად ეხება HIE/ნეონატალურ ტვინის დაზიანებას
   - tags: [hie, stem_cells, neuroprotection, drug_repurposing,
            cord_blood, epilepsy, rehabilitation, erythropoietin,
            hypothermia, melatonin, genetics, imaging]
3. დამიწერე migration script:
   a) Supabase INSERT → papers table
   b) fastembed → Qdrant papers collection
   c) Graphiti → Neo4j Paper nodes + entity extraction
4. Batch processing: 10 papers / batch, error handling
5. verification: count matching across 3 DBs
```

---

## პუნქტი 6.2 — Contacts მიგრაცია

**პრომპტი 6.2:**
```
AMKF system prompt-ში და project knowledge-ში 80+ კონტაქტია.

გთხოვ:
1. ამოიღე ყველა კონტაქტი: name, role, institution, email,
   phone, status (active/pending/closed)
2. დამიწერე migration script:
   a) Supabase INSERT → contacts table
   b) Neo4j → Contact nodes + WORKS_AT → Institution nodes
   c) follow_up_date calculation: ბოლო ცნობილი კომუნიკაცია + 7 დღე
3. ასევე:
   a) aleksandra_timeline: 28.08.2025 → დღემდე ყველა მოვლენა
   b) therapies: Keppra, Vigabatrin, Duke EAP, Wisconsin A2, NAPA...
   c) brain_regions: 14+ რეგიონი damage map-იდან
```

---

## პუნქტი 6.3 — Timeline + Therapies + Brain Regions

**პრომპტი 6.3:**
```
წაიკითხე project knowledge-დან ალექსანდრას სამედიცინო ისტორია
და შექმენი Supabase INSERT scripts:

1. aleksandra_timeline (ქრონოლოგიური):
   28.08.2025 — დაბადება, HIE
   28.08-25.10.2025 — NICU თბილისი (58 დღე)
   ... (ყველა მოვლენა)

2. therapies:
   - Keppra 150mg BID — status: receiving
   - Vigabatrin 400mg/day — status: receiving
   - Duke EAP cord blood — status: planned (July 2026)
   - Wisconsin Virtual A2 — status: active

3. brain_regions (14+):
   - Brainstem: preserved, high plasticity
   - Motor Cortex: destroyed, minimal plasticity
   - ... (ყველა რეგიონი damage map-იდან)
```

---

## პუნქტი 7 — უსაფრთხოება

**პრომპტი 7:**
```
დამიწერე:
1. Supabase RLS policies ყველა 10 ცხრილისთვის:
   - papers, therapies, brain_regions: authenticated read, service_role write
   - contacts: service_role only
   - ingestion_log: service_role write, authenticated read
2. .env audit checklist: ყველა key .env-შია?
3. .gitignore verification: .env, *.nii.gz, *.dcm ფაილები
4. Prism MCP install + basic HIPAA config
5. MRI data handling protocol (1-გვერდიანი policy)
```

---

## პუნქტი 8 — საბოლოო ვერიფიკაცია

**პრომპტი 8:**
```
ფუნდამენტის ბოლო ტესტი. შეამოწმე 10 პუნქტი:

1. Supabase → SELECT count(*) FROM papers
2. Neo4j → MATCH (n) RETURN labels(n), count(n)
3. Qdrant → GET /collections → 3 collection?
4. n8n → GET /workflows → active workflows?
5. Telegram → send test alert → მივიდა?
6. CrewAI → crew.kickoff() → 5 agent initialized?
7. mem0 → cross-agent read → მუშაობს?
8. FastMCP → brain_stats → real numbers?
9. Vercel → app URL → loads?
10. docker-compose up → Neo4j + Qdrant → running?

PASS / FAIL თითოეულისთვის.
FAIL → diagnose → fix → retest.
ყველა PASS → ფუნდამენტი მზადაა.
```

---

## შემდეგი ნაბიჯი

ფუნდამენტი 10/10 PASS? → მიმართულება I იწყება.

**პრომპტი „შემდეგი":**
```
ფუნდამენტი მზადაა (10/10 PASS).

დავიწყოთ მიმართულება I: კვლევითი ინტელექტი.
პირველი ამოცანა: Spider Agent-ს მივცეთ რეალური ინსტრუმენტები.

CrewAI Spider Agent-ში დაამატე tools:
1. PubMed MCP → search_articles
2. Crawl4AI → scrape URLs, extract text
3. Supabase MCP → INSERT papers
4. Qdrant MCP → upsert embeddings
5. Graphiti → entity extraction to Neo4j
6. n8n cron trigger integration

პირველი ნამდვილი ძიება: „hypoxic ischemic encephalopathy treatment 2026"
```

---

*ყოველი ✅ = ერთი ნაბიჯი ტვინისკენ რომელიც არასოდეს იძინებს.*
