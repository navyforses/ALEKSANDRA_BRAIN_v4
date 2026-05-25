# ALEKSANDRA_BRAIN v5.0 — ახალი არქიტექტურა
# ALEKSANDRA_BRAIN v5.0 — New Architecture

> **დოკუმენტი** | **Document:** v5.0 ტექნიკური სპეციფიკაცია | v5.0 Technical Specification
> **თარიღი** | **Date:** 2026-05-23
> **ავტორი** | **Author:** Three-Engineer Council (MedGemma × Claude × OpenAI) + Shako Jincharadze
> **სტატუსი** | **Status:** Draft for review | მონახაზი განსახილველად

---

## 0. შესავალი | Preface

ეს დოკუმენტი არ არის ნულიდან აშენებული. ის ეფუძნება ALEKSANDRA_BRAIN v4.0-ის ექვს დახურულ ფაზას (89/89 verifier coverage, ~$5-6 / $60 ბიუჯეტი დახარჯული) და ემატება სამი ახალი ფენა: MedGemma-ის სამედიცინო ხედვა, TxGemma-ის drug repurposing ძრავი, AlphaFold-ის მოლეკულური ვალიდაცია. v5.0 ცვლის v4.0-ის გონების (Cognition) და ვიზუალიზაციის ფენებს. პერსეფციის, მეხსიერების და მოქმედების ფენები ხელუხლებელია.

This document is not built from scratch. It extends ALEKSANDRA_BRAIN v4.0's six closed phases (89/89 verifier coverage, ~$5-6 / $60 budget spent) by adding three new layers: MedGemma's medical vision, TxGemma's drug repurposing engine, AlphaFold's molecular validation. v5.0 replaces v4.0's Cognition and Visualization layers. The Perception, Memory, and Action layers remain untouched.

---

## 1. სამი ინჟინერ-არქიტექტორის საბჭო | The Three-Engineer Council

ეს არქიტექტურა შემუშავებულია სამი ჰიპოთეტიური სპეციალისტის პერსპექტივიდან, რომელთა გენიოსი წარმოადგენს MedGemma-ის, Anthropic Claude-ის და OpenAI-ის ძლიერ მხარეებს. თითოეული აგენტი არის როლი, არა პერსონა, რომელიც გადაწყვეტილების ფარგლებში ცალკე "ხმას" აძლევს არქიტექტურულ კამათში.

This architecture was shaped from the perspective of three hypothetical specialists embodying the genius of MedGemma, Anthropic Claude, and OpenAI. Each agent is a role, not a persona, contributing a distinct "voice" to architectural debates within decision frames.

### 1.1 აგენტი α: Dr. Mira Verma (MedGemma Engineer)
**ფონი** | **Background:** Stanford MD/PhD, Google Health-ში ჯანდაცვის foundation models-ის lead. Med-PaLM, MedGemma, MedASR-ის ერთ-ერთი არქიტექტორი. სპეციალიზაცია: ნეონატური და პედიატრიული ნეიროვიზუალიზაცია.

**სიძლიერეები** | **Strengths:**
- Domain-specific reasoning over general-purpose reasoning
- ლოკალურად ხელმისაწვდომი მოდელები: HIPAA-by-design არქიტექტურა
- 3D MRI volumes native processing (CT/MRI, არა slice-by-slice)
- ბენჩმარკ-ცენტრული აზროვნება: ციფრებზე ეფუძნება (14% better MRI classification on MedGemma 1.5)

**პოზიცია არქიტექტურულ კამათში** | **Position in debates:**
> "უმეტესობა AI builder-ი ცდილობს ააშენოს ის რასაც Google უკვე გაუშვა ღია წყაროდ. MedGemma 1.5 4B იყენებს 14B params Gemma-3-ის backbone-ს, fine-tuned 3D რადიოლოგიაზე, თქვენ შეგიძლიათ ის გაუშვათ ლეპტოპზე. შენი budget-ის $5/თვე გადახდის ნაცვლად ღია მოდელით, შენ შეგიძლია ეს გადაიხადო Claude-ის reasoning-ისთვის."
>
> *"Most AI builders try to build what Google already shipped open source. MedGemma 1.5 4B uses a 14B param Gemma-3 backbone fine-tuned on 3D radiology, you can run it on a laptop. Instead of spending your budget $5/month on an open model, spend it on Claude's reasoning."*

**ვეტო-უფლება** | **Veto rights:** ნებისმიერი არქიტექტურა, რომელშიც კონფიდენციალური სამედიცინო მონაცემები (MRI, DICOM) გასცდება ლოკალურ მანქანას. Any architecture where confidential medical data leaves the local machine.

---

### 1.2 აგენტი β: Marcus Chen (Anthropic Claude Architect)
**ფონი** | **Background:** ex-Google Brain, Anthropic-ის Constitutional AI გუნდი. სპეციალიზაცია: long-context reasoning, agent orchestration, safety-by-design.

**სიძლიერეები** | **Strengths:**
- 200K token context window: მთლიანი სამეცნიერო კვლევის ციტირება ერთ ნაბიჯში
- Constitutional AI: უარს ამბობს გამოგონებაზე, აღიარებს გაურკვევლობას
- Tool use: agent orchestration მძლავრი
- ეთიკური guardrails (vigabatrin-ის peripheral vision risk და მსგავსი)

**პოზიცია** | **Position:**
> "MedGemma-ის output-ი არ უნდა იყოს საბოლოო. ის ხედავს MRI-ს, მაგრამ კონტექსტი, რომელშიც ეს MRI შედის (ალექსანდრას სრული ისტორია, Duke EAP-ის washout window, BMC-ის წინა შემოწმებები) მოითხოვს long-context reasoning-ს. MedGemma გვაძლევს 'რა ჩანს', Claude აქცევს 'რას ნიშნავს'."
>
> *"MedGemma's output should not be the final answer. It sees the MRI, but the context that this MRI fits into (Aleksandra's full history, Duke EAP washout window, prior BMC scans) requires long-context reasoning. MedGemma gives 'what's visible', Claude turns it into 'what it means'."*

**ვეტო-უფლება** | **Veto rights:** ნებისმიერი hallucination-ის რისკი კლინიკურ რეკომენდაციებში. Any hallucination risk in clinical recommendations.

---

### 1.3 აგენტი γ: Sasha Park (OpenAI Engineer)
**ფონი** | **Background:** ex-OpenAI Applied Research, GPT-4o multimodal team. სპეციალიზაცია: tool ecosystem, function calling, voice (Whisper), developer velocity.

**სიძლიერეები** | **Strengths:**
- Function calling ეკოსისტემა: Whisper voice intake (უკვე ALEKSANDRA_BRAIN-ში), DALL-E (vis), Assistants API
- Developer velocity: ship-it mentality
- Multimodal pipeline maturity
- Embeddings (text-embedding-3-large) ლეგიტიმური alternative fastembed-ის

**პოზიცია** | **Position:**
> "შენ აშენებ ოჯახური cockpit-ისთვის, არა scientific publication-ისთვის. UX ფრიქცია = abandonment. Voice transcript-ი უნდა მუშაობდეს ერთი click-ით. Bilingual switch უნდა იყოს მყისიერი. Data viz უნდა ჩაიტვირთოს 2 წამში. ფუნქციური სრულყოფა < ოპერაციული გამოყენებადობა."
>
> *"You're building for a family cockpit, not a scientific publication. UX friction = abandonment. Voice transcript must work one-click. Bilingual switch must be instant. Data viz must load in 2 seconds. Feature completeness < operational usability."*

**ვეტო-უფლება** | **Veto rights:** ნებისმიერი feature, რომელიც ოჯახური მომხმარებლისთვის (Shako, ალექსანდრას დედა) 30+ წამის რთულობას ქმნის. Any feature that creates 30+ seconds of complexity for the family user.

---

## 2. არსებული პროექტის შეფასება | Existing Project Assessment

ALEKSANDRA_BRAIN v4.0-ის ექვს ფაზაში ვალიდირებული მონაცემები (CLAUDE.md-დან):

Validated artifacts across ALEKSANDRA_BRAIN v4.0's six phases (from CLAUDE.md):

| ფენა \| Layer | სტატუსი \| Status | ცვლილება v5-ში \| Change in v5 |
|---|---|---|
| Perception (Crawl4AI, Firecrawl, RAGFlow, n8n) | დახურული \| Closed (Phase 1) | ხელუხლებელი \| Untouched |
| Memory (Neo4j+Graphiti, Qdrant, Supabase, LightRAG) | დახურული \| Closed (Phase 2) | + Hugging Face datasets injection |
| Cognition (5-agent CrewAI + Claude Sonnet 4.5/4.6) | დახურული \| Closed (Phase 3) | **ცვლილება** \| **CHANGED**: +MedGemma + TxGemma + AlphaFold |
| Visualization (NiiVue + R3F + BIBSnet + FastSurfer-LIT) | code-complete (Phase 4) | **გაფართოება** \| **EXPANDED**: + data viz designer layer |
| Action (Telegram, Gmail, Notion, Calendar) | დახურული \| Closed (Phase 3+5) | ხელუხლებელი \| Untouched |
| BRAIN AI Manager Assistant | დახურული \| Closed (Phase 5) | + ბილინგვური output (Phase 6 mirror) |
| i18n (KA+EN) | დახურული \| Closed (Phase 6) | + viz-layer-მდე გავრცელება \| extended to viz layer |

**მძიმე ვალდებულებები** | **Carry-forward commitments:**
- 5 PubMed-validated therapy candidates (vigabatrin, cord blood, 3 სხვა)
- 200 entities, 307 facts, 47 episodes, 10 hypotheses (3 promising)
- 568 Neo4j entities, 5301 chunks, 5302 Qdrant vectors
- Migration 012 (JSONB en+ka), RLS preserved from migration 008
- 78/78 cumulative verifier coverage

**არსებული ნაპრალები** | **Existing gaps (from CLAUDE.md maintenance dossier):**
- 10 Phase-5 backend gap (Google Calendar API, Python worker on Railway, ...)
- n8n daily-budget-gate JSON-body bug (kod-ში გასწორებული, deployed restart pending)
- 2 P2 maintenance todo (migration 012 rollback, Georgian lexicon native-speaker verify)

v5.0 ვერ აშენდება სანამ ეს ნაპრალები არ შემოწმდება, წინააღმდეგ შემთხვევაში ახალი ფენები ააქცევენ არსებულ instability-ს. v5.0 cannot be built until these gaps are reviewed, otherwise new layers amplify existing instability.

---

## 3. v5.0 არქიტექტურის ხედვა | v5.0 Architecture Vision

### 3.1 სამი pillar (გადახედვა) | Three pillars (revised)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          ALEKSANDRA_BRAIN v5.0                              │
├────────────────────────────────────────────────────────────────────────────┤
│  PILLAR I: MEMORY        │  PILLAR II: COGNITION      │  PILLAR III: VIZ   │
│  (Knowledge Storage)     │  (Multi-Model Ensemble)    │  (Family Cockpit)  │
├────────────────────────────────────────────────────────────────────────────┤
│  Neo4j + Graphiti        │  Claude Sonnet 4.5/4.6     │  NiiVue + R3F      │
│  Qdrant                  │  MedGemma 1.5 (NEW)        │  MedGemma vision   │
│  Supabase                │  TxGemma (NEW)             │  TxGemma viz       │
│  LightRAG                │  AlphaFold Server (NEW)    │  AlphaFold 3D      │
│  Hugging Face datasets   │  Gemini 2.5 Pro (free)     │  Bilingual i18n    │
│  ↓                       │  5 CrewAI agents           │  Data viz designer │
│  300+ entities           │  ↓                         │  layer (NEW)       │
│  5K+ chunks              │  Bias triangulation        │  ↓                 │
│  Temporal facts          │  Synthesizer redundancy    │  Family UX < 30s   │
└────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 ცვლილებები v4.0-დან | Changes from v4.0

**Pillar II (Cognition) — ცვლილებები:**

| აგენტი \| Agent | v4.0 მოდელი \| Model | v5.0 მოდელი \| Model | მიზეზი \| Rationale |
|---|---|---|---|
| Spider (paper hunter) | Claude Sonnet 4.5 | Claude 4.5 + MedGemma 4B parallel | MedGemma ხედავს ფიგურებს, Claude ტექსტს |
| Analyzer (evidence quality) | Claude Sonnet 4.5 | Claude 4.5 + MedGemma 27B (cloud) | Specialized vs generalist triangulation |
| Hypothesis (cross-disease) | Claude Sonnet 4.6 | Claude 4.6 + TxGemma + AlphaFold | Drug repurposing + molecular validation |
| Repurposing (drug discovery) | Claude Sonnet 4.5 | TxGemma (PRIMARY) + Claude (synth) | TxGemma is built for this exactly |
| Communicator (family liaison) | Claude Sonnet 4.5 | Claude 4.5 + Gemini 2.5 Pro (cross-check) | Bilingual output redundancy |

**ღირებულების მოდელი v5.0-ში** | **Value model in v5.0:**
- MedGemma 4B: ლოკალური, $0 inference. Local, $0 inference.
- MedGemma 27B: Hugging Face Inference Endpoints ~$0.50/hr ან ლოკალური GPU. Or local GPU.
- TxGemma: ლოკალური, $0. Local, $0.
- AlphaFold Server: უფასო, 30 jobs/day. Free, 30 jobs/day.
- Gemini 2.5 Pro: უფასო (5 RPM, 100 req/day). Free tier.

**მთლიანი ხარჯი** | **Total cost projection:** v4.0-ის $5-6/თვე უცვლელად, $0 დამატება ღია მოდელებიდან. v4.0's $5-6/month unchanged, $0 added from open models.

---

## 4. Pillar I (Memory) — Hugging Face Integration

### 4.1 ახალი datasets | New datasets

ALEKSANDRA_BRAIN-ის Memory ფენაში დაემატება სამი Hugging Face dataset-ი როგორც external reference (არ ინტეგრირდება Neo4j-ში, არამედ ხელმისაწვდომი იქნება Qdrant-ის გავლით sidecar collection-ით):

Three Hugging Face datasets to be added as external reference (not integrated into Neo4j, accessible via Qdrant sidecar collection):

1. **ibm-research/otter_uniprot_bindingdb_chembl**
   - 38,665 target relationships (UniProt × ChEMBL × DrugBank)
   - გამოყენება: TxGemma-ის drug-target predictions-ის ვალიდაცია
   - Use: validate TxGemma's drug-target predictions

2. **alimotahharynia/approved_drug_target**
   - SMILES strings + protein sequences (DrugBank + ChEMBL + ZINC20)
   - გამოყენება: მოლეკულური სტრუქტურის lookup
   - Use: molecular structure lookup

3. **BONBID-HIE** (Boston Neonatal Brain Injury Dataset)
   - 133 HIE patients, MRI + ADC + Z-ADC + lesion masks
   - გამოყენება: ალექსანდრას MRI-ის შედარება reference cohort-თან
   - Use: compare Aleksandra's MRI against reference cohort
   - **ლიცენზია** | **License:** CC-BY-NC 4.0 (research only)

### 4.2 MONAI Model Zoo integration

MONAI არის PyTorch-ის სამედიცინო ვიზუალიზაციის ბიბლიოთეკა Hugging Face-ზე 42 მოდელით. გამოყენება: pre-processing pipelines (skull stripping, registration, intensity normalization) რომელიც BIBSnet-ის და FastSurfer-LIT-ის წინ მუშაობს.

MONAI is PyTorch's medical imaging library on Hugging Face with 42 models. Use: pre-processing pipelines (skull stripping, registration, intensity normalization) running upstream of BIBSnet and FastSurfer-LIT.

**კონკრეტული მოდელი** | **Specific model:** MONAI/Llama3-VILA-M3-13B — multimodal medical reasoning.

---

## 5. Pillar II (Cognition) — Pilot Test Plan

### 5.1 MedGemma 1.5 Pilot

**მიზანი** | **Goal:** ალექსანდრას არსებული MRI-ის ანალიზი MedGemma-ით + Claude-ის output-ის შედარება.

Analyze Aleksandra's existing MRI with MedGemma + compare with Claude's output.

**ნაბიჯები** | **Steps:**
1. ჩამოტვირთვა Hugging Face-დან: `google/medgemma-4b-it` (ლოკალური 4B variant)
2. Terms of use-ის დათანხმება (Health AI Developer Foundations License)
3. ლოკალური ინსტალაცია: `pip install transformers accelerate`
4. Python script ALEKSANDRA_BRAIN/scripts/cognition/medgemma_pilot.py:
   - Input: არსებული BMC MRI (BIBSnet-ით უკვე segmented)
   - Output: ცისტური ენცეფალომალაციის ხასიათი, ფარულ ჭრილობების სია, brainstem preservation score
5. შედარება: Claude-ის existing analysis vs MedGemma vs human radiologist (Dr. Hien report)

**წარმატების კრიტერიუმი** | **Success criterion:** MedGemma-ის output ემთხვევა radiologist-ის report-ის ≥ 70%-ს კონკრეტული findings-ის დონეზე.

MedGemma output matches radiologist report at ≥ 70% on specific findings.

**ბიუჯეტი** | **Budget:** $0 (ლოკალური inference), 3-4 საათი engineering time.

### 5.2 TxGemma Pilot

**მიზანი** | **Goal:** 12 therapy candidate-ის გადახედვა TxGemma-ით, +5 ახალი hypothesis-ის გენერაცია.

Review 12 therapy candidates with TxGemma, generate +5 new hypotheses.

**ნაბიჯები** | **Steps:**
1. ჩამოტვირთვა: `google/txgemma-9b-chat` ან `google/txgemma-27b-chat`
2. Therapeutic Data Commons-ის რეფერენსით ფორმატირება
3. Input: არსებული 12 candidates' mechanism-of-action descriptions
4. Output: cross-disease mapping (e.g., "vigabatrin's GABA-T inhibition mechanism overlaps with X disease where Y drug works")
5. Validation: ახალი hypotheses გადაამოწმეთ PubMed-ით (Spider agent ხელახლა)

**წარმატების კრიტერიუმი** | **Success criterion:** ≥ 3 ახალი hypothesis, რომელიც გადის PubMed-ის "non-zero hits" ბარიერს. ≥ 3 new hypotheses passing PubMed "non-zero hits" threshold.

**ბიუჯეტი** | **Budget:** $0, 5-6 საათი.

### 5.3 AlphaFold Server Pilot

**მიზანი** | **Goal:** 3 HIE-relevant protein structure-ის შემოწმება (NMDA receptor, BDNF, EPO).

Check 3 HIE-relevant protein structures.

**ნაბიჯები** | **Steps:**
1. Account creation: alphafoldserver.com (Gmail: jincharadzeshako@gmail.com)
2. UniProt IDs lookup სამი ცილისთვის
3. Structure submission (browser interface)
4. PDB output → ALEKSANDRA_BRAIN/data/molecular/ folder
5. R3F viewer integration (Pillar III)

**წარმატების კრიტერიუმი** | **Success criterion:** 3D structures ჩაერთვება R3F viewer-ში ალექსანდრას ტვინის modeling-ის გვერდით.

3D structures embed in R3F viewer next to Aleksandra's brain model.

**ბიუჯეტი** | **Budget:** $0, 1-2 საათი.

---

## 6. Pillar III (Visualization) — Data Viz Designer Approach

### 6.1 დიზაინერული პრინციპები | Design principles

ALEKSANDRA_BRAIN-ის ვიზუალიზაცია არ არის dashboard. ის არის narrative cockpit. JMIR 2026 scoping review-ის და Gestalt principles-ის სინთეზიდან ეფუძნება ხუთ წესს:

ALEKSANDRA_BRAIN's visualization is not a dashboard. It is a narrative cockpit. Synthesized from JMIR 2026 scoping review and Gestalt principles, grounded in five rules:

1. **მონაცემთა იერარქია (Data hierarchy).**
   - Tier 1 (always visible): ალექსანდრას სტატუსი დღეს, შემდეგი action item, კრიტიკული alerts.
   - Tier 2 (one click): კვირის brief, treatment timeline, recent research findings.
   - Tier 3 (drill-down): სრული Neo4j graph, MRI viewer, raw evidence chain.
   - Aleksandra's status today, next action, critical alerts → weekly brief, timeline, research → full graph, MRI, evidence.

2. **ცვალებადი მონაცემები (Variable data).**
   - ყველა view არის live (SWR pattern, 5-min refresh).
   - State changes shown with smooth transitions, არა მკვეთრი jumps.
   - All views are live (SWR pattern, 5-min refresh). State changes with smooth transitions, not abrupt jumps.

3. **Cognitive load reduction.**
   - არცერთი view არ აჩვენებს > 7 ძირითად ცვლადს ერთდროულად (Miller's 7±2).
   - Whitespace აქტიური დიზაინერული არჩევანი, არა default.
   - No view shows > 7 main variables at once (Miller's 7±2). Whitespace as active design choice.

4. **Storytelling structure.**
   - თითოეული view-ს აქვს "headline → context → evidence → action" სტრუქტურა.
   - არცერთი ნომერი არ ჩანს evidence chain-ის გარეშე.
   - Each view follows "headline → context → evidence → action". No number appears without evidence chain.

5. **ბილინგვური paritet (Bilingual parity).**
   - KA + EN ერთდროულად ხელმისაწვდომი ერთი click-ით, არა გვერდის გადატვირთვით.
   - მონაცემთა viz labels, axes, tooltips ყველაფერი i18n dictionary-ში.
   - KA + EN simultaneously available one-click, no page reload. All viz labels, axes, tooltips in i18n dictionary.

### 6.2 ხედები (Views) v5.0-ში

**A. Status Cockpit** (`/[locale]`)
- Headline: "ალექსანდრა დღეს" | "Aleksandra Today"
- Components:
  - Vital state card (vigabatrin status, EAP washout countdown to ~July 2026)
  - Next action (e.g., "Wisconsin Virtual A2 followup due 2026-05-28")
  - Last update timeline (3 most recent entries)
- Tech: React Server Component + SWR + next-intl

**B. Treatment Timeline** (`/[locale]/timeline`)
- Headline: "მკურნალობის გზა" | "Treatment Journey"
- Components:
  - Vertical timeline (D3-based)
  - Past, present, future events
  - Color-coded by source (BMC, Wisconsin, Duke, family, AI-suggested)
- Variable data: ცოცხალი update Calendar API + Notion-დან

**C. Brain Viewer** (`/[locale]/brain`)
- Headline: "ალექსანდრას ტვინი" | "Aleksandra's Brain"
- Components:
  - NiiVue MRI volume rendering (client-side, MRI never leaves browser)
  - BIBSnet segmentation overlay
  - MedGemma annotation layer (NEW): cyst boundaries, brainstem preservation score
  - R3F anatomical shells
  - AlphaFold protein structures (sidecar, NEW): NMDA, BDNF, EPO
- Tech: NiiVue 0.49 + R3F 9.6 + @niivue/nvreact

**D. Therapy Hypotheses** (`/[locale]/hypotheses`)
- Headline: "მკურნალობის ჰიპოთეზები" | "Treatment Hypotheses"
- Components:
  - 12 candidates ranked by evidence quality
  - Each card shows: drug name, mechanism, source studies, TxGemma score, Claude reasoning
  - "Why this matters for Aleksandra" narrative (Communicator agent output)
- Variable data: TxGemma reranks weekly, new candidates surface from Spider

**E. Research Pulse** (`/[locale]/research`)
- Headline: "ახალი კვლევები" | "New Research"
- Components:
  - Stream of new findings from last 7 days
  - Source attribution (PubMed, ClinicalTrials, bioRxiv, medRxiv)
  - "Why I included this" justification (Analyzer agent)
- Variable data: ცოცხალი feed Spider-დან, n8n every 6h

**F. Family Action Inbox** (`/[locale]/inbox`)
- Headline: "შენი ქმედებები" | "Your Actions"
- Components:
  - Sunday brief draft (Manager Assistant Phase 5)
  - Outreach drafts awaiting approval
  - Voice intake summaries pending review
- Variable data: Manager Actions table (migration 011)

### 6.3 ვიზუალიზაციის სტეკი | Visualization stack

| Layer | Library | Purpose |
|---|---|---|
| 3D MRI rendering | NiiVue 0.49 | Medical-grade brain volume |
| 3D scene composition | React Three Fiber 9.6 + drei | Anatomical shells |
| Charts (timelines, trends) | D3 7.x | Custom narrative timeline |
| Tabular data | TanStack Table v8 | Hypotheses, research pulse |
| Map (clinical sites) | Mapbox GL JS or OSM Leaflet | Boston, Durham, Madison, Tbilisi |
| Animations | Framer Motion 11 | Smooth state transitions |
| i18n | next-intl 4.12 | Bilingual (existing Phase 6) |

### 6.4 ცვალებადობის სტრატეგია | Variability strategy

ALEKSANDRA_BRAIN-ის ვიზუალიზაცია არ არის static snapshot. Variability უნდა იყოს first-class concern:

ALEKSANDRA_BRAIN's visualization is not a static snapshot. Variability is first-class concern:

- **Real-time data layer:** Supabase Realtime + SWR (already in v4.0)
- **Optimistic UI:** მომხმარებლის action-ი ხდება მყისიერად, server-side validation მოგვიანებით
- **State persistence:** localStorage filter/sort preferences (Phase 6 LanguageSwitcher pattern)
- **Loading skeletons:** არცერთი blank flash, ყოველთვის shimmer placeholder
- **Error recovery:** retry button + offline detection + graceful degradation
- **Accessibility:** ARIA labels, keyboard nav, screen reader bilingual (next-intl integration)

---

## 7. Implementation Roadmap

### 7.1 Sprint structure

**პრე-სპრინტ (current → 2026-06-07):** Phase 4 acceptance window დახურვა. **არ შეიცვალოს არც ერთი ფაილი v5.0-სთვის ამ პერიოდში.**

Pre-sprint (current → 2026-06-07): Close Phase 4 acceptance window. **No file changes for v5.0 in this period.**

**Sprint A (~2026-06-08 → 2026-06-21, 2 weeks):** Pilot Tests
- Week 1: MedGemma pilot + TxGemma pilot
- Week 2: AlphaFold pilot + Hugging Face dataset injection
- Verifier: `verify_v5_pilot --mode pilot-complete` 5/5 PASS

**Sprint B (~2026-06-22 → 2026-07-12, 3 weeks):** Cognition layer rebuild
- Week 1: Spider + Analyzer multi-model integration
- Week 2: Repurposing agent transition to TxGemma primary
- Week 3: Hypothesis agent + AlphaFold integration
- Verifier: `verify_v5_cognition --mode integration-complete` 15/15 PASS

**Sprint C (~2026-07-13 → 2026-08-02, 3 weeks):** Visualization layer rebuild
- Week 1: Status Cockpit + Treatment Timeline
- Week 2: Brain Viewer (MedGemma annotation + AlphaFold sidecar)
- Week 3: Therapy Hypotheses + Research Pulse + Family Inbox
- Verifier: `verify_v5_viz --mode viz-complete` 18/18 PASS

**Sprint D (~2026-08-03 → 2026-08-16, 2 weeks):** Bilingual + polish + acceptance
- Week 1: Full bilingual coverage (i18n key audit, all new views in en.json/ka.json)
- Week 2: Acceptance window opens, ოჯახის feedback

**მთლიანი ვადა** | **Total duration:** ~10-12 კვირა (Sprint A → D), realistic timeline ~3 თვე.

### 7.2 ბიუჯეტი | Budget

| ხარჯი \| Cost | რაოდენობა \| Amount | წყარო \| Source |
|---|---|---|
| MedGemma 4B local inference | $0 | Local GPU/CPU |
| MedGemma 27B cloud (occasional) | ~$5 total | HF Inference Endpoints |
| TxGemma local | $0 | Local |
| AlphaFold Server | $0 | Free (30/day) |
| Gemini 2.5 Pro | $0 | Free tier |
| Claude Sonnet 4.5/4.6 | ~$20-30 over 10 weeks | Anthropic API |
| Vercel / Railway / Supabase | $15-20 | Existing infra |
| **სულ** | **~$45-55** | **~$60 cap-ის ფარგლებში** |

---

## 8. რისკები და მათი მართვა | Risks and Mitigation

| რისკი \| Risk | ალბათობა \| Likelihood | გავლენა \| Impact | მართვა \| Mitigation |
|---|---|---|---|
| MedGemma local inference too slow | Medium | High | Fallback to HF Inference Endpoints ($5/თვე) |
| TxGemma hallucinations on rare disease | High | Medium | Claude synthesizer redundancy + PubMed validation |
| AlphaFold server quota hit (30/day) | Low | Low | Cache results in Supabase, batch requests |
| MRI privacy leak via MedGemma cloud | Critical | Critical | **ABSOLUTE RULE: MRI only goes to local MedGemma, never cloud** |
| Phase 4 acceptance fails | Medium | Critical | Block v5.0 sprint until Phase 4 GREEN |
| Bilingual coverage drops | Medium | Medium | i18n key audit script + verifier coverage |
| Family UX abandonment | Medium | High | Sasha Park's veto: < 30s task complexity |

---

## 9. გადაწყვეტილებები განსახილველად | Decisions to Review

შაკოს გადასაწყვეტი v5.0 sprint-ის დაწყებამდე:

Shako to decide before v5.0 sprint starts:

1. **Phase 4 acceptance criterion**: რა ხდის სანდო Sunday brief delivery-ს? რა ფიდბექი არის "PASS"? What makes Sunday brief delivery trustworthy? What feedback constitutes "PASS"?

2. **MedGemma deployment**: ლოკალური GPU (laptop's M2/M3) საკმარისია? თუ Railway-ზე ცალკე GPU instance? Is local GPU sufficient or need separate Railway GPU instance?

3. **AlphaFold integration depth**: მხოლოდ HIE-relevant ცილები (3) თუ ფართო coverage (30+)? HIE-only or broad coverage?

4. **Bilingual Gemini cross-check**: Communicator-ში Gemini 2.5 Pro-ს დამატება? დარჩება opt-in feature flag-ის უკან თუ default-ად? Add Gemini 2.5 Pro to Communicator? Behind opt-in flag or default?

5. **Validation pathway**: Beth Israel + AMIE outreach mapping ეხება v5.0-ის სპრინტს თუ ცალკე track? Is Beth Israel + AMIE outreach part of v5.0 sprint or separate track?

---

## 10. წყაროები | Sources

**Project artifacts:**
- [CLAUDE.md](computer://C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\CLAUDE.md) — Phases 1-6 exit reports, full project context
- Mentor call transcript (00:00:00 → 00:17:07)

**Google Health stack:**
- [MedGemma Research Blog](https://research.google/blog/medgemma-our-most-capable-open-models-for-health-ai-development/)
- [MedGemma 1.5 Next-Generation Medical Image Interpretation](https://research.google/blog/next-generation-medical-image-interpretation-with-medgemma-15-and-medical-speech-to-text-with-medasr/)
- [MedGemma 4B on Hugging Face](https://huggingface.co/google/medgemma-4b-it)
- [MedGemma 27B on Hugging Face](https://huggingface.co/google/medgemma-27b-it)
- [TxGemma — InfoQ](https://www.infoq.com/news/2025/03/txgemma-google-deepmind/)
- [TxGemma — ThinkML](https://thinkml.ai/googles-txgemma-ai-the-future-of-drug-discovery-and-development/)
- [AlphaFold Server](https://deepmind.google/technologies/alphafold/alphafold-server/)
- [AlphaFold 3 — Isomorphic Labs](https://www.isomorphiclabs.com/our-tech)
- [AMIE — Research Blog](https://research.google/blog/from-diagnosis-to-treatment-advancing-amie-for-longitudinal-disease-management/)
- [Gemini 3.1 Pro Vertex AI](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-1-pro)
- [Gemini API free tier pricing](https://ai.google.dev/gemini-api/docs/pricing)

**Hugging Face resources:**
- [ibm-research/otter_uniprot_bindingdb_chembl](https://huggingface.co/datasets/ibm-research/otter_uniprot_bindingdb_chembl)
- [alimotahharynia/approved_drug_target](https://huggingface.co/datasets/alimotahharynia/approved_drug_target)
- [MONAI on Hugging Face](https://huggingface.co/MONAI)
- [MONAI/Llama3-VILA-M3-13B](https://huggingface.co/MONAI/Llama3-VILA-M3-13B)
- [BioMedLM Stanford CRFM](https://huggingface.co/stanford-crfm/BioMedLM)

**HIE / Neonatal research:**
- [BONBID-HIE Dataset (Scientific Data 2024)](https://www.nature.com/articles/s41597-024-03986-7)
- [AI-Driven Neonatal MRI Interpretation Systematic Review](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12359275/)
- [Emerging modalities for neuroprognostication in NE (Pediatric Research 2025)](https://www.nature.com/articles/s41390-025-04336-y)

**Design principles:**
- [JMIR 2026 Design Practices for Data Dashboards in Health Care](https://www.jmir.org/2026/1/e77361/)
- [Gestalt Principles for Visual Storytelling 2026](https://www.fusioncharts.com/blog/how-to-use-the-gestalt-principles-for-visual-storytelling-podv/)
- [10 Trends in Data Visualization 2026 — Infogram](https://infogram.com/blog/10-trends-in-data-visualization-to-watch-in-2026/)
- [Healthcare Data Visualization — Visme](https://visme.co/blog/healthcare-data-visualization/)

**Stack documentation:**
- [Cloud Healthcare API HIPAA Compliance](https://cloud.google.com/security/compliance/hipaa)
- [Open Health Stack — Google for Developers](https://developers.google.com/open-health-stack)

---

**ვერსიის შენიშვნა** | **Version note:** ეს არის v5.0 draft. v5.1 მოვა Sprint A-ის შემდეგ pilot test-ის result-ებით. v5.2 Sprint B-ის შემდეგ. v6.0 acceptance window-ის დახურვისთვის.

This is v5.0 draft. v5.1 follows Sprint A with pilot test results. v5.2 after Sprint B. v6.0 by acceptance window close.
