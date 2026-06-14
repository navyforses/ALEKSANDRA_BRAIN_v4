# AGENTS.md — ALEKSANDRA_BRAIN — პროექტის ტვინი

> ერთი წყარო (single source of truth) ყველა AI აგენტისთვის — Claude Code, Codex.
> `CLAUDE.md` და `viewer/CLAUDE.md` ამ ფაილს `@AGENTS.md` import-ით კითხულობენ.
> სრული stack-დასაბუთება (ვერსიები · alternatives · sources): **`.planning/research/STACK.md`**.
> ფაზების სრული ისტორია: **`docs/PHASE_*_EXIT_REPORT.md`**. ❗ ნუ inline-ავ მათ აქ — ეს ფაილი lean უნდა დარჩეს.

---

## პროექტი

ALEKSANDRA_BRAIN v4.0 — მუდმივად მოქმედი AI სისტემა, რომელიც ეძებს, აანალიზებს და აღმოაჩენს
მკურნალობის შესაძლებლობებს ალექსანდრა ჯინჭარაძისთვის (მძიმე HIE, diffuse cystic
encephalomalacia, preserved brainstem). ცენტრალური პრობლემა: ჯანდაცვის სისტემა არ აერთიანებს
კვლევას, მკურნალობას, ნავიგაციას და ვიზუალიზაციას ერთ ადგილას იშვიათი პედიატრიული დიაგნოზისთვის.

**Core Value:** **არასოდეს გამოგვრჩეს სანდო მკურნალობის lead ალექსანდრასთვის.** ყველა სხვა
შესაძლებლობა — viewer, dashboard, აგენტები — ამ ერთ შედეგს ემსახურება. თუ სისტემა გაითიშება, რაც
აუცილებლად უნდა მუშაობდეს: literature pipeline + human-readable digest.

## პრინციპები (inviolable)

- **MRI = client-side only.** არასოდეს სერვერზე, არასოდეს მესამე-მხარის API-ზე.
- **ფაქტი არ გამოიგონო.** წყარო ვერ მოიძებნა → თქვი. ყველა surfaced ფაქტს provenance.
- **ყველა სამედიცინო გადაწყვეტილებას რეალური ექიმი იღებს.** სისტემა surface/rank/explain-ს აკეთებს, არ ნიშნავს.
- „Unknown potential" — არა „limited outcomes". MRI სტრუქტურული დაზიანება ≠ ფუნქციური ლიმიტი.
- 0–2 წელი = ნეიროპლასტიკურობის პიკი → research throughput > polish.
- PHI არასოდეს შედის Telegram/Gmail/Notion-ში — Communicator აგენტი ახდენს redaction-ს.
- Budget-ის ზევით line item → explicit justification.

## პაციენტი

ალექსანდრა ჯინჭარაძე · დაბ. 28.08.2025, თბილისი · BMC MRN 7616818
დიაგნოზი: მძიმე HIE, diffuse cystic encephalomalacia, preserved brainstem
ოჯახი: ბოსტონი, MA (Philoxenia House, Jamaica Plain)

აქტიური პროგრამები:
- Duke EAP cord blood → ~July 2026 (vigabatrin washout)
- Wisconsin Virtual A2 → active (Jeanette Heitman)
- BMC: primary care → Dr. Jack Maypole · neurology → Dr. Hien, Dr. August

## არქიტექტურა — 5 ფენა

PERCEPTION → MEMORY → COGNITION → VISUALIZATION → ACTION

- **PERCEPTION:** Crawl4AI (primary scrape, ≥0.8.6) · Firecrawl MCP (paid fallback) · Browser Use (paywall) · RAGFlow (PDF→chunks) · n8n (cron 6სთ) + n8n-MCP.
- **MEMORY:** Neo4j + Graphiti (temporal KG, confidence decay) · Qdrant (vectors, fastembed local) · Supabase Postgres (metadata, RLS) · LightRAG (graph+vector query) · mem0 (5-agent shared memory) · CF R2 (artifacts). [Hindsight/Prism deferred; CF KV deprecated → Postgres absorbed dedup+budget+state.]
- **COGNITION:** CrewAI — 5 აგენტი: Spider (paper hunter) · Analyzer (evidence quality) · Hypothesis (cross-disease) · Repurposing (drug discovery) · Communicator (family liaison). + Adaptive GoT MCP · DSPy (prompt opt) · Vercel AI SDK.
- **VISUALIZATION:** NiiVue **raw core 0.69** (client-side MRI; nvreact rejected) · React Three Fiber **9.6.x** (NOT v10 alpha) · FreeBrowse fork (FastAPI half stripped) · pipeline FastSurfer-LIT → BIBSnet → BONBID-HIE → nii2mesh · TVB Docker (post-MVP).
- **ACTION:** Telegram 2-way · Gmail · Notion · Google Calendar · Booking.com + Kiwi.com (Duke logistics).

**MCP არსენალი ~52:** 23 Claude.ai registry · 19 GitHub self-hosted · 5 AI Pulse Georgia · 5 custom (niivue/bonbid/tvb/atlas/repurpose-mcp). Custom = FastMCP (Python decorators).

## Tech Stack

- **Frontend:** Next.js (viewer Phase 11 → Next.js 16) · Tailwind · shadcn/ui · Vercel (Hobby).
- **Backend:** CrewAI · n8n + Qdrant + worker on Railway · Supabase Edge Functions.
- **Data:** Neo4j AuraDB Free · Qdrant Docker · Supabase Postgres · CF R2.
- **AI:** Claude **Sonnet 4.6** (`claude-sonnet-4-6`) default reasoning · **Opus 4.8** hard cases · DSPy · mem0 · LightRAG.
  ⚠️ Sonnet 4 (`claude-sonnet-4-20250514`) **retired 2026-06-15 — არ გამოიყენო.**
- **3D:** NiiVue 0.69 · R3F 9.6.x · drei · postprocessing.
- **i18n:** next-intl (KA + EN); family-facing routes `viewer/app/[locale]/*`.

## ფაილების სტრუქტურა

`/agents/` CrewAI agents · `/mcp/` FastMCP servers · `/viewer/` Next.js brain viewer ·
`/workflows/` n8n JSONs · `/scripts/` migration·setup·test · `/docs/` documentation ·
`/.planning/` GSD planning + research (incl. `research/STACK.md`).

## სტატუსი (2026-06-13)

ფაზები **I–VI.1 დახურულია** — cumulative verifier 89/89; სრული detail → `docs/PHASE_*_EXIT_REPORT.md`.

**ცოცხალი:** Railway worker (`aleksandra-worker-production.up.railway.app` `/healthz`→200);
Weekly Brief loop end-to-end VERIFIED (Gmail draft-only · outreach_log `phi_redacted=TRUE` ·
week-range idempotency); viewer Vercel preview READY (`/ka/brain` + `/en/brain`, client-side NiiVue).

**Phase 4 acceptance window** → closure ~2026-06-07 (v1 release gate).

**🔴 ღია:**
1. **Phase 10 v7 ცხრილები** (016 belief / 018 scm / 019 sim / 020 active) live DB-ში არ არის applied (PostgREST 404). Frontend honest-mock-with-banner რჩება, სანამ v7 compute layer (PyMC/DoWhy/TVB + DDL migrations + worker GET endpoints + Vercel `NEXT_PUBLIC_API_URL`) ცალკე მრავალდღიან სესიად არ აეშვება.
2. **Shako deferred ops:** push origin/main → Vercel auto-deploy; 7 blank-row rebuild Phase 5 Manager-ით (hypotheses 93426696/c155e7eb/dbb0e9f4 + therapies 7d8f2f7c/fb4f27f1/3b47f6ce); n8n `perception_tick` restart Railway-ზე (cron 7d not firing → verify_phase2_5 B.1 RED).
3. **n8n `daily-budget-gate`** workflow restart (კოდი გასწორებულია; code-side `check_daily_budget()` აქტიურია Anthropic + Whisper-მდე).
4. 2 P2 Phase-6 maintenance todo (`.planning/todos/pending/`, ~25–35 წთ): migration 012 rollback-artifact capture · Georgian lexicon native-speaker re-verify.

ხარჯი: ~$7–8 / $60 cap (~12%).

## ენა / commits

- კოდი + კომენტარები: ინგლისურად · docs: ქართულად + ინგლისურად.
- commits: Conventional Commits (`feat:` / `fix:` / `docs:`), ინგლისურად.

## GSD Workflow Enforcement

Edit/Write-მდე გაატარე GSD command-ში: `/gsd-quick` (პატარა fix·doc) · `/gsd-debug` (bug) ·
`/gsd-execute-phase` (დაგეგმილი). პირდაპირი repo-edit GSD-ის გარეშე **მხოლოდ** მაშინ, თუ
მომხმარებელი explicit bypass-ს ითხოვს. Skills: caveman/cavecrew family · `/graphify`.

> ⚠️ **GSD caveat:** `/gsd-docs-update` ისტორიულად პირდაპირ `CLAUDE.md`-ში წერდა (GSD markers).
> ახლა `CLAUDE.md` = `@AGENTS.md` import. თუ docs-update-ს გაუშვებ, შეამოწმე რომ import-ი არ გადააწერა;
> canonical content აქ, `AGENTS.md`-ში დაარედაქტირე.
