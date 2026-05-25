# ALEKSANDRA_BRAIN v6.0 — Research-Grounded Architecture

> **დოკუმენტი:** v6.0 ფაქტობრივი ეკოსისტემის კვლევის შემდეგ ჩამოყალიბებული არქიტექტურა
>
> **Author:** Shako Jincharadze + Claude
>
> **თარიღი:** 2026-05-23
>
> **მთავარი განსხვავება v5.0-დან:** v5.0 იყო MedGemma + TxGemma + AlphaFold-ის სამეულზე დაფუძნებული. v6.0 უფრო ფართოა — შეიცავს Google-ის სრულ HAI-DEF პორტფოლიოს (8 მოდელი), Anthropic Claude for Healthcare (2026 იანვარი), OpenAI Whisper რეალური HIPAA ლიმიტებით, MONAI ეკოსისტემას, MedSAM2-ს, TotalSegmentator-ს, ბევრად მეტ ფარულ ხელსაწყოს.

---

## 0. რეზიუმე | Executive Summary

ეს არქიტექტურა აშენდა შემდეგი ფაქტობრივი კვლევის შემდეგ:

**Google Health AI Developer Foundations (HAI-DEF) — 8 ღია მოდელი 2026-ში:**
1. MedGemma 1.5 (4B + 27B, text + image, 3D CT/MRI native)
2. TxGemma (drug repurposing, 66M TDC data points)
3. HeAR (bioacoustic, 300M audio clips)
4. Path Foundation (histopathology embeddings)
5. Derm Foundation (dermatology embeddings)
6. CXR Foundation (chest X-ray, 800K X-rays)
7. MedSigLIP (multimodal medical embeddings — chest X-rays, derm, ophthalmology, histopathology, CT, MRI)
8. MedASR (medical speech-to-text, 2026 release)

**Anthropic Claude for Healthcare 2026:**
- Claude Opus 4.5 with "extended thinking" mode
- Native PubMed + CMS coverage database + ICD-10 + NPI integration
- HIPAA-compliant tier (January 2026)
- Claude Sonnet 4 scored 20/20 (100%) on board-style clinical vignettes
- Available via Microsoft Foundry

**OpenAI ფარული ლიმიტი:**
- Whisper არ არის HIPAA-compliant პირდაპირ
- სამედიცინო კონტექსტში მუშაობს მხოლოდ Azure OpenAI Service-ის გავლით
- "Careless Whisper" კვლევა: hallucination rate ~50% სატესტო ჩანაწერებში
- ALEKSANDRA_BRAIN ფაზა 5-ში Whisper local deployment-ი ერთადერთი სანდო გზაა

**Open-source medical imaging stack:**
- MONAI Core + Label + Deploy SDK + Model Zoo (PyTorch ecosystem)
- MedSAM2 (3D + video, April 2025)
- TotalSegmentator MRI (sequence-independent, 104 anatomic structures)
- SAM-Med2D (4.6M images, 19.7M masks)
- 3D Slicer (desktop, full clinical research)
- OHIF Viewer (web-based, DICOM, zero-footprint)

**Hugging Face ფაქტობრივი state:**
- 2M+ models total
- 62 medical models
- 80% downloads from top 50 models
- Medical AI focus growing per Spring 2026 report

**Multi-agent framework converged choice 2026:**
- CrewAI for prototyping (1-2 weeks)
- LangGraph v1.0+ for production (October 2025 GA)
- ALEKSANDRA_BRAIN-ის გადასვლა CrewAI → LangGraph არის v7.0-ის გადაწყვეტილება, არა v6.0-ის

**RAG architecture 2026 reality:**
- Dense vector RAG-ი არ არის საკმარისი medical-ისთვის
- Hybrid (lexical + semantic + graph-augmented) აუცილებელია
- Reduces hallucination 70-90% vs standard LLM
- Source attribution mandatory

**Observability stack 2026:**
- Langfuse acquired by ClickHouse (January 2026, $400M Series D)
- 21K+ GitHub stars, MIT license, Docker self-host
- Healthcare-specific: Confident AI for HIPAA-aligned trace handling

---

## 1. რას ვისწავლეთ Google-ის გამოცდილებიდან

### 1.1 Med-PaLM-ის სამი გაკვეთილი

Google-მა Med-PaLM 1 (2022) → Med-PaLM 2 (2023) → MedLM (2024, დახურული 2025-09-29) → MedGemma (2025+) გზაში სამი ფუნდამენტური გაკვეთილი ისწავლა:

**გაკვეთილი 1: General-purpose LLM არ მუშაობს medical-ში.**
Google-მა PaLM 2 (general-purpose) გადააქცია Med-PaLM 2-ად domain-fine-tuning-ით. Performance benchmarks-ში გაუმჯობესება იყო. რეალურ კლინიკურ ცდაში, hallucination რჩებოდა. დასკვნა: fine-tuning ცვლის accuracy-ს, არ ცვლის reliability-ს.

**გაკვეთილი 2: Open-source > Cloud API სამედიცინო პროდუქტებში.**
MedLM API დახურა 2025 წელს. ჰოსპიტალები ვერ უმასპინძლებდნენ PHI cloud-ში. გადაწყვიტეს გადასვლა on-premise/on-device-ზე. MedGemma + HAI-DEF არის ამ გაკვეთილის შედეგი: open weights, Apache 2.0-მსგავსი license, hospital deployment local-ად.

**გაკვეთილი 3: Modality matters more than scale.**
MedGemma 4B (4 billion parameters) outperforms GPT-4 (1.7T+ parameters) on specific medical imaging tasks. რადგან 4B იყო trained on relevant data. ეს ნიშნავს: ცალკეული domain-სპეციფიკური მცირე მოდელი > გენერალური დიდი მოდელი.

**ALEKSANDRA_BRAIN-ის implication:**
- არ ენდო ერთ general-purpose LLM-ს (მაშინაც კი თუ ის არის Claude Sonnet 4.5).
- გამოიყენე domain-სპეციფიკური ანსამბლი (MedGemma image + Claude reasoning + TxGemma repurposing).
- აარჩიე open weights, არა cloud API where possible — PHI risk mitigated.

### 1.2 AMIE-ის Beth Israel კვლევა (მარტი 2026) — ფაქტობრივი შედეგი

**ცდის სტრუქტურა:** 100 ზრდასრული პაციენტი, single-arm feasibility study at Beth Israel Deaconess Medical Center. AMIE chat history-taking-ი 5 დღით ადრე appointment-ის წინ.

**შედეგი:**
- Zero safety stops 100 interaction-დან
- პაციენტების attitudes AI-ის მიმართ მნიშვნელოვნად გაუმჯობესდა
- PCPs reported better visit preparedness 50%+ შემთხვევებში
- AI როგორც augmentation (არა replacement)

**ლიმიტი:** Single-center, single-arm. Generalization unclear. ცდის გენერალიზაცია NHS-ის ან BMC-ის environment-ში არ არის გადაცემული.

**ALEKSANDRA_BRAIN-ის implication:**
- ფიზიკურად Boston-ში ყოფნა (Beth Israel = ~15 წუთის სავალი) არის გრძელვადიანი strategic advantage. AMIE research team accessible.
- "AI augmentation" framing არის სწორი — ALEKSANDRA_BRAIN ცვლის ექიმის preparedness, არა ცვლის ექიმს.

### 1.3 MedGemma deployment patterns hospital production-ში

Google Cloud-ი მიყიდის ჰოსპიტალებს Vertex AI-ის გავლით. MedGemma deployment-ი ხდება სამი ფორმით:

1. **Vertex AI HTTPS endpoint** (real-time, cloud)
2. **Vertex AI Batch prediction** (offline, large datasets)
3. **On-premise local inference** (GPU server, PHI never leaves hospital)

ჰოსპიტალის ფარული workflow Meditecs Smart Connect example:
- HL7/FHIR message ingestion EHR/PACS-დან
- AI enrichment via MedGemma
- Output back as HL7/FHIR

**ALEKSANDRA_BRAIN-ის implication:**
- ოჯახური cockpit-ი არ მუშაობს HL7/FHIR pipeline-ით. ეს არის B2C, არა B2B medical.
- მაგრამ თუ Beth Israel/BMC integration-ი მოვა v7.0+-ში, FHIR readiness-ი იქნება unlock factor.
- სხვა სიტყვებით: v6.0 არ უნდა აშენდეს FHIR-ცენტრულად, მაგრამ Pillar I (Memory) უნდა იყოს FHIR-translatable.

---

## 2. Google HAI-DEF სრული პორტფოლიო (8 მოდელი)

### 2.1 ფაქტობრივი list 2026 May-ის მდგომარეობით

| მოდელი | მოდალობა | ზომა | License | ALEKSANDRA_BRAIN რელევანტობა |
|---|---|---|---|---|
| **MedGemma 1.5** | Multimodal (text + image + 3D MRI/CT) | 4B + 27B | HAI-DEF License | ★★★★★ Primary v6.0 model |
| **TxGemma** | Therapeutic prediction (drug repurposing) | 9B + 27B | HAI-DEF License | ★★★★★ Repurposing agent core |
| **HeAR** | Bioacoustic (cough, breathing, speech) | Encoder | HAI-DEF License | ★★ ხანდახან გამოყენებადი ალექსანდრას breathing patterns-ისთვის |
| **MedSigLIP** | Multimodal embeddings | Encoder | HAI-DEF License | ★★★★ Vector search across modalities |
| **CXR Foundation** | Chest X-ray embeddings | Encoder | HAI-DEF License | ★ არ ეხება HIE-ს |
| **Path Foundation** | Histopathology embeddings | Encoder | HAI-DEF License | ★ არ ეხება HIE-ს |
| **Derm Foundation** | Dermatology embeddings | Encoder | HAI-DEF License | ★ არ ეხება HIE-ს |
| **MedASR** | Medical speech-to-text (2026 launch) | TBD | HAI-DEF License | ★★★ Whisper-ის ალტერნატივა Phase 5 voice intake-ისთვის |

### 2.2 თუ ცარიელ ფურცელზე ვაშენებდით — Google-ის optimal stack

1. **MedGemma 27B** primary reasoning (MRI + clinical text)
2. **TxGemma 27B** drug repurposing
3. **MedSigLIP** vector search ერთიანი ცხრილში MRI + papers + drugs
4. **MedASR** voice intake (Whisper-ის ჩანაცვლება)
5. **AMIE-style conversational layer** family liaison-ისთვის (Anthropic Claude უკეთესია ამ-ისთვის reasoning depth-ით)

რეალურად, ALEKSANDRA_BRAIN უკვე ფარავს 80%-ს ამ stack-ის. დარჩენილი 20% არის Sprint A-B-ის scope.

---

## 3. რას ვისწავლეთ Anthropic Claude for Healthcare-დან

### 3.1 Claude for Healthcare suite (2026 იანვარი)

Anthropic-ის sample-ი 2026 JP Morgan Healthcare Conference-ზე:
- **Claude Opus 4.5** with extended thinking mode (designed to reduce hallucinations)
- **Native integrations:** CMS coverage database, PubMed, ICD-10, NPI, Apple Health, Android Health Connect
- **HIPAA-compliant tier** (January 2026 launch)
- **Available via Microsoft Foundry**

### 3.2 Clinical reasoning benchmarks

Claude Sonnet 4 achieved 20/20 (100%) on board-style clinical vignettes (comparative study). ეს არის უმაღლესი ქულა მსოფლიოში 2026-ში. ნიშნავს რომ:
- Claude > GPT-4o > Gemini ჯერ კიდევ clinical reasoning-ში
- Claude Opus 4.6 (current as of project) > Sonnet 4.5 > Sonnet 4 თეორიულად

### 3.3 ALEKSANDRA_BRAIN-ისთვის ცვალდება?

**ცვალდება ერთი რამ:** Claude-ის როლი არ არის "უბრალოდ LLM". Claude-ისთვის Anthropic-მა აშენა medical-specific integrations. ALEKSANDRA_BRAIN-ში Communicator agent-ი შესაძლოა გადავიდეს Claude Opus 4.5-ზე Sonnet 4.5-დან, რათა extended thinking mode-ი იყოს ხელმისაწვდომი rare-disease reasoning-ისთვის.

**ცვალდება მეორე რამ:** Claude-ის CMS + PubMed native integration ეფარდება ALEKSANDRA_BRAIN-ის spider agent-ის PubMed pipeline-ს. ალბათ უფრო ეფექტური იქნება native integration-ის გამოყენება ცალკეული PubMed fetch-ის ნაცვლად. ეს არის v6.1 თემა.

**არ ცვალდება:** Claude-ის core role-ი (reasoning + synthesis) რჩება. Anthropic-ის sample-ი არ ცვლის სტრუქტურულად რასაც აქამდე ვაკეთებდით.

---

## 4. რას ვისწავლეთ OpenAI-დან (და მათი ლიმიტებიდან)

### 4.1 Whisper hallucination crisis

A developer found hallucinations in nearly all of 26,000 transcripts. Computer scientists found 187 hallucinations in over 13,000 clear audio snippets. ML engineer discovered hallucinations in ~50% of over 100 hours of analyzed transcriptions.

ეს არ არის თეორიული რისკი. Whisper ფაქტობრივად ცდილია სამედიცინო ჩანაწერების transcription-ში სრულიად ცარიელ წინადადებას მოიგონებს, ისე რომ ემსგავსება medical jargon-ს.

**ALEKSANDRA_BRAIN-ის implication for Phase 5 voice intake:**
- Whisper-ის local deployment-ი ერთადერთი სანდო პათ-ი. Cloud Whisper API arn'tab-ისთვის უარყოფა.
- Verification layer ფარულად საჭიროა — ცოლის voice intake → Whisper → review draft → თუ confidence low, request re-recording.
- ალტერნატივა: Google MedASR (2026 launch, HAI-DEF). შესაძლოა უფრო სანდო specifically medical context-ში.

### 4.2 GPT-4 clinical decision support — mixed results

Research findings:
- GPT-4 ცდილია სასარგებლო patient data summarization-ში
- Junior physicians-ისთვის accuracy 72.2% with GPT-4 vs lower without
- Senior physicians-ისთვის 75.6% with vs comparable without

**კრიტიკული:** "Research found that the availability of GPT-4 to physicians as a diagnostic aid did not significantly improve clinical reasoning compared to conventional resources."

**ALEKSANDRA_BRAIN-ის implication:**
- AI არ ცვლის ექიმის გადაწყვეტილებას. AI ცვლის ექიმის preparedness-ს.
- "AI provides preparation, doctor provides decision" framing-ი არის empirically validated.

### 4.3 OpenAI-ის როლი v6.0-ში

ფაქტობრივად, ALEKSANDRA_BRAIN-ში OpenAI-ის role-ი არის periphery:
- Whisper (Phase 5 voice intake) — local deployment, არ cloud
- text-embedding-3-large embeddings — fastembed-ის ალტერნატივა, ფასიანი
- DALL-E for documentation graphics — არ არის core

Sasha Park persona-ის სამუშაო v6.0-ში: UX velocity და ergonomics, არა core inference.

---

## 5. Open-Source Medical AI Ecosystem — ფაქტობრივი inventory

### 5.1 MONAI ეკოსისტემა (PyTorch-based)

| კომპონენტი | რა აკეთებს | ALEKSANDRA_BRAIN-ში |
|---|---|---|
| **MONAI Core** | AI model training framework | ★★★ Used internally by BIBSnet/FastSurfer-LIT |
| **MONAI Label** | Interactive annotation tool | ★ ალბათ არ გვჭირდება |
| **MONAI Deploy App SDK** | Production deployment | ★★ თუ ჰოსპიტალთან integration-ი მოვა |
| **MONAI Model Zoo** | Pre-trained model collection | ★★★★ Direct download for HIE/pediatric models |
| **MONAI/Llama3-VILA-M3-13B** | Multimodal medical reasoning | ★★★ შესაძლო alternative to MedGemma 27B |

### 5.2 Segmentation tools — ფარული შესაძლებლობები

| ხელსაწყო | მოდალობა | ALEKSANDRA_BRAIN-ის value |
|---|---|---|
| **BIBSnet** | Neonatal 0-8 months, FreeSurfer-compatible | ★★★★★ Already in stack |
| **FastSurfer-LIT** | Lesion inpainting (cysts/cavities/tumors) | ★★★★★ Already in stack |
| **TotalSegmentator MRI** | 104 anatomic structures, sequence-independent | ★★★ ალბათ value-ი არ აქვს neonatal-ში, ცდილია adult-ში |
| **MedSAM2** | 3D + video, fine-tuned SAM2.1 | ★★★★ Promising for follow-up MRI comparison |
| **SAM-Med2D** | 4.6M images, 19.7M masks, prompt-based | ★★★ შესაძლო alternative for ad-hoc segmentation |
| **MedicoSAM** | Robust SAM improvement | ★★ Backup option |

### 5.3 Viewer ეკოსისტემა

| ხელსაწყო | Type | ALEKSANDRA_BRAIN-ში |
|---|---|---|
| **NiiVue** | Web-based, WebGL2 | ★★★★★ Already integrated, primary viewer |
| **OHIF Viewer** | Web-based, DICOM-first, zero-footprint | ★★★ თუ DICOM workflow მოვა, OHIF არის სტანდარტი |
| **3D Slicer** | Desktop, research-grade | ★★ For deep research only, არა family cockpit |
| **Cornerstone.js** | Web-based DICOM library | ★★ Underlying NiiVue-ის ალტერნატივა |

---

## 6. Best Practices — რა გავიგეთ ფარული წესების შესახებ

### 6.1 RAG architecture 2026 patterns

Medical RAG implementations vary by architecture:
- **Dense RAG** (embedding-only) — არ არის საკმარისი medical-ისთვის
- **Hybrid RAG** (lexical + semantic) — minimum bar for production
- **Graph-augmented RAG** — required for cross-disease reasoning
- **Agentic RAG** — central orchestrator routing to specialized retrievers

ALEKSANDRA_BRAIN-ის ფაქტობრივი state: ფარულად უკვე hybrid + graph-augmented (LightRAG + Graphiti + Qdrant). v6.0 უმატებს TxGemma-ის agentic layer-ს.

### 6.2 Human-in-the-loop verification — non-negotiable

Three patterns 2026-ში:
1. **Bounded generation with recognition-based review** (chart-text pairing)
2. **Automated urgency flagging** (fail-safe escalation)
3. **Progressive disclosure** (cognitive load reduction)

ALEKSANDRA_BRAIN-ის Communicator agent-ი უკვე pattern 1-ისა და 2-ის შემცველია. Pattern 3 (progressive disclosure) არის viewer-ის ცვლადობის სტრატეგია, რომელიც v6.0-ში გაფართოვდება.

**ფარული წესი:** AI accuracy 99.5% with HITL vs 92% AI alone vs 96% pathologist alone. "AI + human > either alone" — empirically validated.

### 6.3 Observability — სავალდებულო ფენა

**Langfuse acquired by ClickHouse** January 2026. $400M Series D. ეს არის წერტილი — observability არის enterprise-grade now.

ALEKSANDRA_BRAIN-ის observability-ის სტატუსი ფაქტობრივად: ცარიელი. სანდო monitoring-ი არ არის wired. **v6.0-ის ერთ-ერთი ფარული ცვლილება:** Langfuse self-hosted Docker deployment.

რა მოგვცემს:
- Token cost tracking per agent
- Hallucination rate per query
- Tool selection quality
- Latency distribution
- Per-conversation tracing

ეს არ არის luxury. რეალური 2026 medical AI deployments use this layer.

### 6.4 Multi-agent framework choice 2026

Industry consolidation:
- **CrewAI** for prototyping (1-2 weeks)
- **LangGraph v1.0+** for production (October 2025 GA, built-in checkpointing, HITL, state persistence)

ALEKSANDRA_BRAIN ჯერ CrewAI-ში არის (Phase 0-6 closed on CrewAI). v6.0 დარჩება CrewAI-ში. **v7.0 candidate:** LangGraph migration. ეს არ არის v6.0-ის scope.

---

## 7. v6.0 არქიტექტურის ფინალური ხედვა

### 7.1 ცვალდება v5.0-დან

```
                    ALEKSANDRA_BRAIN v6.0
┌──────────────────────────────────────────────────────────────────┐
│                                                                   │
│  PILLAR I: MEMORY                  PILLAR II: COGNITION           │
│  ─────────────────                 ────────────────────           │
│  Neo4j + Graphiti                  Claude Sonnet 4.5 (default)    │
│  Qdrant                            Claude Opus 4.5 (escalation)   │
│  Supabase                          MedGemma 1.5 4B (local)        │
│  LightRAG                          MedGemma 1.5 27B (HF endpoint) │
│  HF datasets (otter, drug-target)  TxGemma 9B (local)             │
│  MedSigLIP embeddings (NEW)        AlphaFold Server (browser)     │
│  ↓                                 MedSigLIP encoder (NEW)         │
│  300+ entities                     MedASR (NEW, Phase 5 v2)        │
│  5K+ chunks                        ↓                               │
│  Temporal facts                    5-agent CrewAI                  │
│  FHIR-translatable schema (NEW)    + LangGraph migration plan v7   │
│                                                                    │
│  PILLAR III: VISUALIZATION         PILLAR IV: OBSERVABILITY (NEW)  │
│  ──────────────────────            ──────────────────────────      │
│  NiiVue + R3F + Next.js 16         Langfuse (self-hosted Docker)   │
│  BIBSnet + FastSurfer-LIT          Token cost per agent            │
│  MedGemma annotation overlay (NEW) Hallucination rate tracking     │
│  AlphaFold sidecar (NEW)           Tool selection quality          │
│  MedSAM2 follow-up comparison(NEW) Per-conversation tracing        │
│  Bilingual i18n (en+ka)            Confidence threshold escalation │
│  Data viz designer principles      Audit log (immutable)           │
│                                                                    │
│  PILLAR V: ACTION                  PILLAR VI: VALIDATION (NEW)    │
│  ───────────────                   ───────────────────────────    │
│  Telegram + Gmail + Notion         BMC liaison framework          │
│  Google Calendar                   Beth Israel AMIE outreach      │
│  BRAIN AI Manager Assistant        Duke EAP coordination          │
│  Bilingual outreach drafter        Wisconsin Virtual A2 sync      │
│                                    Native-clinician verify queue  │
└──────────────────────────────────────────────────────────────────┘
```

### 7.2 ცვლილებების სია

**ცვალდება Pillar I (Memory):**
1. MedSigLIP encoder embeddings ემატება Qdrant-ში როგორც sidecar collection
2. FHIR-translatable schema — Supabase migration 014 (planned, v6.1)
3. HF datasets injection (otter, drug-target, BONBID-HIE reference)

**ცვალდება Pillar II (Cognition):**
4. Communicator agent → Claude Opus 4.5 escalation (rare disease reasoning)
5. Repurposing agent → TxGemma primary + Claude synthesis
6. Analyzer agent → MedGemma 4B parallel + Claude
7. Hypothesis agent → AlphaFold-augmented + Claude Opus 4.5 deep reasoning
8. Communicator voice intake (Phase 5 v2) → MedASR replacing Whisper, local deployment

**ცვალდება Pillar III (Visualization):**
9. Brain viewer extends with MedGemma annotation layer
10. AlphaFold protein sidecar
11. MedSAM2 follow-up MRI comparison view (when 2nd MRI available)
12. All views maintain bilingual parity

**ცვალდება Pillar IV (Observability) — NEW PILLAR:**
13. Langfuse self-hosted Docker (Railway deployment)
14. Per-agent token cost dashboards
15. Hallucination rate tracking
16. Immutable audit log

**ცვალდება Pillar VI (Validation) — NEW PILLAR:**
17. BMC liaison framework (Dr. Maypole, Dr. Hien, Dr. August)
18. Beth Israel AMIE outreach (Vivek Natarajan)
19. Duke EAP coordination protocol
20. Wisconsin Virtual A2 sync

---

## 8. Phased Roadmap v6.0

### Phase 6.0 — Sprint A: Pilot tests (2 weeks)
**Pre-condition:** ფაზა 4 acceptance GREEN.
- MedGemma 4B local pilot (Aleksandra's MRI)
- TxGemma 9B local pilot (12 candidates rescoring)
- AlphaFold Server pilot (NMDA, BDNF, EPO)
- HF datasets exploration (otter, drug-target)
- Output: `docs/v6_pilot_findings.md`

### Phase 6.0 — Sprint B: Cognition rebuild (3 weeks)
- Week 1: 4 new MCP wrappers (medgemma, txgemma, alphafold, medsiglip)
- Week 2: 4 agent modifications (analyzer, hypothesis, repurposing, communicator)
- Week 3: Migration 013 (txgemma_score column), MedSigLIP Qdrant sidecar, verify_v6_cognition (12/12 gates)

### Phase 6.0 — Sprint C: Visualization extension (2 weeks)
- Week 1: Therapies/Hypotheses/Brain view extensions
- Week 2: i18n keys, accessibility audit, verify_v6_viz (10/10 gates)

### Phase 6.0 — Sprint D: Observability layer (1 week)
- Langfuse self-hosted Docker on Railway
- Instrumentation in all 5 agents
- Dashboard provisioning
- verify_v6_observability (8/8 gates)

### Phase 6.0 — Sprint E: Validation framework (1 week)
- BMC liaison protocol document
- Beth Israel outreach draft
- Duke EAP coordination checklist
- verify_v6_validation (5/5 gates)

### Phase 6.0 — Sprint F: Bilingual polish + acceptance (1 week)
- Full i18n coverage audit
- Wife test (Georgian UX)
- Mentor presentation
- v6.0 acceptance window opens

**Total duration:** 10 weeks. **Budget projection:** $30-40 / $60 cap.

---

## 9. ფარული ჭეშმარიტებები — რა ისწავლა ეს კვლევა

### 9.1 ჭეშმარიტება 1: Google-ის სტრატეგია არ არის "AI for hospitals"

Google-ის medical AI portfolio (HAI-DEF) არის ფაქტობრივად open-weights strategy enterprise SaaS lock-in-ის ფარგლებში. ღია მოდელები ღია არიან, რადგან მათი deployment scale-ი (Vertex AI) გენერერებს revenue-ს. ეს არ არის charity. ეს არის dual-strategy: free entry, paid scale.

**ALEKSANDRA_BRAIN-ის implication:** იყავი იქ სანამ free entry ღია. Vertex AI lock-in მოვა მაშინ, როცა ჰოსპიტალთან integration-ი მოვა. დაიჭირე value ფანჯრიდან რომელიც დღეს ღიაა.

### 9.2 ჭეშმარიტება 2: Anthropic-ის Claude for Healthcare არის silent disruptor

JP Morgan Healthcare Conference 2026 launch-ი მცირე ფარული ცვლილებაა, რომელიც ჯერ კიდევ ნაკლებად ცნობილია. Claude Opus 4.5 with extended thinking + CMS + PubMed native — ეს არის ის რასაც ჰოსპიტალები ფაქტობრივად ეძებენ, Microsoft Foundry-ის გავლით uniform interface-ით.

**ALEKSANDRA_BRAIN-ის implication:** Communicator agent ფიქს ემიდრობს Opus 4.5-ისკენ rare-disease reasoning-ისთვის. ეს არის v6.0-ის ერთი მცირე ცვლილება, რომელიც დიდ პოტენციალს ფარავს.

### 9.3 ჭეშმარიტება 3: Whisper-ის hallucination არ არის bug, არის სტრუქტურული პრობლემა

50% hallucination rate არ არის "fixable in next release". ეს არის სტრუქტურული თვისება generative ASR-ისთვის. MedASR (Google 2026 launch) ცდილია იყოს უფრო სანდო, რადგან domain-specific training.

**ALEKSANDRA_BRAIN-ის implication:** Phase 5 voice intake-ი არ უნდა ენდოს Whisper output-ს pure. Always require human review before persist. MedASR-ის pilot test ვადაშია 6.1-ში.

### 9.4 ჭეშმარიტება 4: Open-source segmentation არის უკეთესი ვიდრე commercial

BIBSnet (DCAN Labs) + FastSurfer-LIT (Deep-MI) + TotalSegmentator + MedSAM2 — ეს არის open-source stack. Commercial ალტერნატივები (Aidoc, Tempus) ფარულად ფასიანი არიან და limited scope.

**ALEKSANDRA_BRAIN-ის implication:** არ შეიძინო commercial AI medical imaging tools. open-source უკეთესია domain-სპეციფიკურ ცდებზე.

### 9.5 ჭეშმარიტება 5: Multi-agent framework consolidation — CrewAI და LangGraph უსაფრთხო bet

AutoGen Microsoft Agent Framework-ად გადავიდა (maintenance mode). OpenAI Swarm ეცდილია მაგრამ ჯერ არ მუშაობს enterprise scale-ში. AWS Bedrock Agents არის lock-in. **CrewAI + LangGraph არის converged 2026 industry standard.**

**ALEKSANDRA_BRAIN-ის implication:** CrewAI 0.80-დან 1.14+-ზე upgrade-ი ეცდილია v6.0-ში. LangGraph migration არის v7.0.

### 9.6 ჭეშმარიტება 6: Observability არ არის optional anymore

Langfuse-ის ClickHouse acquisition ($400M Series D) ნიშნავს რომ industry serious-ად დაიკავა observability. Healthcare-სპეციფიკური Confident AI ფარულად განცალკევებული.

**ALEKSANDRA_BRAIN-ის implication:** v6.0 Sprint D-ში Langfuse self-hosted deployment არის mandatory, არა nice-to-have.

### 9.7 ჭეშმარიტება 7: Validation pathway არ მუშაობს automatically — Beth Israel ფარული unlock

AMIE Beth Israel კვლევა (March 2026) დაასრულა successfully. Google ეცდილია expand-ი. **Boston-ში ფიზიკურად ყოფნა means Beth Israel research team accessible.** არცერთი sf medical AI builder-ი არ აქცევს ამას strategic advantage-ად, რადგან მათ Aleksandra-ს case არ აქვთ.

**ALEKSANDRA_BRAIN-ის implication:** v6.0 Sprint E (validation framework) უნდა გადადგას ერთი outreach Beth Israel-ის AMIE team-ს (Vivek Natarajan ცნობილია lead-ად). ეს არ არის v6.0-ის blocker, მაგრამ ეს არის strategic seed.

---

## 10. ცვლის თუ არა ეს რამე ფაქტობრივად?

ფაქტობრივი ცვლილებები v5.0 vs v6.0:

**ცვალდება 5 ნივთი:**
1. + Pillar IV (Observability) — Langfuse Docker
2. + Pillar VI (Validation) — BMC + Beth Israel + Duke framework
3. Communicator agent → Claude Opus 4.5 escalation
4. + MedSigLIP encoder for unified vector search
5. MedASR planned for Phase 5 v2 (Whisper replacement)

**არ ცვალდება:**
- Pillar I (Memory) Neo4j+Graphiti+Qdrant+Supabase+LightRAG ბაზა
- Pillar III (Visualization) NiiVue+R3F+BIBSnet+FastSurfer-LIT
- Pillar V (Action) Telegram+Gmail+Notion+Calendar
- 5-agent CrewAI structure
- Bilingual i18n (Phase 6 stable)
- Budget ceiling ($60 cap)

**implication:** v6.0 არ არის rewrite. ეს არის v5.0 + 5 strategic additions ფაქტობრივი ეკოსისტემის კვლევის შემდეგ.

---

## 11. ბიუჯეტი v6.0-სთვის

| Component | Cost | Source |
|---|---|---|
| MedGemma 4B local | $0 | Local GPU/CPU |
| MedGemma 27B occasional | ~$5 | HF Inference Endpoints |
| TxGemma local | $0 | Local |
| AlphaFold Server | $0 | Free (30/day) |
| MedSigLIP encoder | $0 | Local |
| Claude Sonnet 4.5 default | ~$15 | Anthropic API |
| Claude Opus 4.5 escalation | ~$10 | Anthropic API (limited use) |
| Langfuse self-hosted | $0 | Docker on existing Railway |
| Vercel / Supabase / Neo4j Aura | $15 | Existing infra |
| **Total** | **~$45** | **$60 cap-ის ფარგლებში** |

---

## 12. სამოქმედო გეგმა

დღეიდან:
1. ფაზა 4 acceptance window dominates (24 მაისი → 7 ივნისი).
2. Pre-sprint tasks (requirements.txt, CrewAI upgrade, MCP-INVENTORY pre-update) parallel.
3. ეს v6.0 დოკუმენტი არის reference, არ არის immediate execution plan.

7 ივნისის შემდეგ, თუ ფაზა 4 GREEN:
- Sprint A pilot (2 კვირა)
- Sprint B cognition (3 კვირა)
- Sprint C viz (2 კვირა)
- Sprint D observability (1 კვირა) — NEW
- Sprint E validation (1 კვირა) — NEW
- Sprint F polish (1 კვირა)

Total ~10 weeks, end date ~mid-August 2026.

---

## წყაროები

### Google HAI-DEF
- [Health AI Developer Foundations](https://developers.google.com/health-ai-developer-foundations)
- [HAI-DEF on Hugging Face](https://huggingface.co/collections/google/health-ai-developer-foundations-hai-def)
- [MedGemma Research Blog](https://research.google/blog/medgemma-our-most-capable-open-models-for-health-ai-development/)
- [MedGemma 1.5 Technical Report](https://arxiv.org/pdf/2604.05081)
- [MedGemma 1.5 4B HF](https://huggingface.co/google/medgemma-4b-it)
- [MedGemma 1.5 27B HF](https://huggingface.co/google/medgemma-27b-it)
- [TxGemma launch](https://www.infoq.com/news/2025/03/txgemma-google-deepmind/)
- [Path/Derm/CXR Foundation](https://research.google/blog/health-specific-embedding-tools-for-dermatology-and-pathology/)
- [HeAR Research Blog](https://blog.google/innovation-and-ai/technology/health/ai-model-cough-disease-detection/)

### AMIE Clinical Study
- [Exploring AMIE feasibility in clinical study](https://research.google/blog/exploring-the-feasibility-of-conversational-diagnostic-ai-in-a-real-world-clinical-study/)
- [AMIE Beth Israel paper (arxiv)](https://arxiv.org/pdf/2603.08448)
- [Vivek Natarajan RAAIS 2026](https://press.airstreet.com/p/vivek-natarajan-google-deepmind-raais-2026)
- [AMIE first real-world study results](https://digitalhealthwire.com/google-amie-outperforms-in-real-world-debut/)

### Anthropic Claude Healthcare
- [Claude for Healthcare 2026 launch](https://markets.financialcontent.com/wral/article/tokenring-2026-1-13-anthropic-unveils-specialized-claude-for-healthcare-and-lifesciences-suites-with-native-pubmed-and-cms-integration)
- [Claude AI for Medicine analysis](https://www.iatrox.com/blog/claude-ai-for-medicine-can-it-replace-clinical-decision-support-2026)
- [Claude in Microsoft Foundry](https://www.microsoft.com/en-us/microsoft-cloud/blog/healthcare/2026/01/11/bridging-the-gap-between-ai-and-medicine-claude-in-microsoft-foundry-advances-capabilities-for-healthcare-and-life-sciences-customers/)
- [Life sciences page](https://claude.com/solutions/life-sciences)
- [Claude 20/20 board-style vignettes](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12614119/)

### OpenAI Medical
- [Whisper hallucination crisis](https://aiforlawyers.substack.com/p/openais-careless-whisper)
- [HIPAA-compliant Whisper local](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/building-hipaa-compliant-medical-transcription-with-local-ai/4490777)
- [Azure Speech-to-Text HIPAA](https://www.speechmatics.com/company/articles-and-news/best-speech-to-text-ai-guide-apis-platforms-and-services-compared)
- [GPT-4 clinical decision support mixed results](https://www.sciencedaily.com/releases/2024/10/241028164534.htm)

### Open-source medical imaging
- [MONAI](https://monai.io/)
- [MONAI on Hugging Face](https://huggingface.co/MONAI)
- [TotalSegmentator MRI](https://github.com/wasserth/TotalSegmentator)
- [MedSAM](https://github.com/bowang-lab/MedSAM)
- [MedSAM2 (3D + video)](https://opencv.org/blog/medsam2/)
- [SAM-Med2D](https://arxiv.org/pdf/2308.16184)
- [OHIF Viewer](https://ohif.org/)
- [3D Slicer](https://www.slicer.org/)
- [BIBSnet repo](https://github.com/DCAN-Labs/BIBSnet)
- [FastSurfer-LIT](https://github.com/Deep-MI/LIT)
- [BONBID-HIE dataset](https://www.nature.com/articles/s41597-024-03986-7)

### RAG + Multi-agent architecture
- [Medical RAG architectures 2026](https://medium.com/@angelosorte1/rag-architectures-every-ai-developer-must-know-in-2026-a-complete-guide-with-examples-ea59471aeb01)
- [RAG hallucination reduction 70-90%](https://www.kandasoft.com/blog/7-ways-rag-in-ai-models-supports-modern-healthcare)
- [LangGraph vs CrewAI healthcare 2026](https://nirmitee.io/blog/langgraph-crewai-temporal-custom-orchestration-healthcare-agents-2026/)
- [Multi-agent frameworks 2026](https://gurusup.com/blog/best-multi-agent-frameworks-2026)
- [Human-in-the-loop HITL patterns](https://aws.amazon.com/blogs/machine-learning/human-in-the-loop-constructs-for-agentic-workflows-in-healthcare-and-life-sciences/)
- [AI + HITL accuracy 99.5%](https://parseur.com/blog/human-in-the-loop-ai)

### Observability
- [Langfuse + ClickHouse acquisition](https://www.shareuhack.com/en/posts/llm-agent-observability-langfuse-guide-2026)
- [AI observability for healthcare](https://www.confident-ai.com/knowledge-base/compare/best-ai-observability-tools-for-healthcare-companies-2026)

### Drug repurposing databases
- [ChEMBL + Open Targets relationship](https://pubs.acs.org/doi/10.1021/acs.jmedchem.5c00920)
- [Drug repurposing integrative pipeline](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12687465/)

### FHIR + Knowledge graphs
- [FHIR knowledge graph integration](https://www.mdpi.com/2076-3417/16/8/3936)
- [FHIR 2026 interoperability standards](https://murphi.ai/fhir-integration/)

### Project artifacts
- [ALEKSANDRA_BRAIN_v5_AUDIT.md](computer://C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\ALEKSANDRA_BRAIN_v5_AUDIT.md)
- [ALEKSANDRA_BRAIN_v5_ARCHITECTURE.md](computer://C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\ALEKSANDRA_BRAIN_v5_ARCHITECTURE.md)
- [ALEKSANDRA_BRAIN_v5_VSCODE_INSTRUCTIONS_KA.md](computer://C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\ALEKSANDRA_BRAIN_v5_VSCODE_INSTRUCTIONS_KA.md)
- [CLAUDE.md](computer://C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\CLAUDE.md)

---

## ბოლო შენიშვნა

ეს არ არის dogma. ეს არის snapshot 2026-05-23-ის ეკოსისტემის. ფაქტობრივი ცვლილებები ხდება ყოველ თვეში:
- ჯერ კიდევ Google შემოიტანს HAI-DEF-ში ახალ მოდელებს
- Anthropic გააფართოვებს Claude for Healthcare-ს
- MedSAM3 ან BIBSnet 2.0 ცდილია
- LangGraph 2.0 დაიწერება

v6.1 (Q3 2026) გადახედავს ამ snapshot-ს. v7.0 (2027) ცდილია CrewAI → LangGraph migration-ის გადაწყვეტილებას.

ნუ ცდი ცარიელ ფურცელზე ააშენო. v4.0-ის ფუნდამენტი მუშაობს. v6.0 უმატებს 5 strategic layer-ს, რომელიც დახარჯვის ფარგლებში ჯდება.
