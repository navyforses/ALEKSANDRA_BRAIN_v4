# Feature Research

**Domain:** Bespoke single-patient pediatric medical-research cockpit (HIE, severe diffuse cystic encephalomalacia, preserved brainstem) — audience: 1 family + treating clinicians
**Researched:** 2026-05-13
**Confidence:** HIGH (domain), MEDIUM (specific tool maturity)

## Framing

This is a **1-patient bespoke system**, not a SaaS, not a community platform, not a clinical product.
The Core Value from PROJECT.md is unambiguous: **"Never miss a credible treatment lead for Aleksandra."**
Every feature below is evaluated against that single sentence. If a feature does not measurably reduce the probability of missing a credible lead, or measurably increase the probability of a clinician acting on one, it is not table stakes — no matter how exciting it looks on the architecture diagram.

The neuroplasticity window (0–2 years) is a hard time constraint. Aleksandra was born 2025-08-28, so the window closes ~Aug 2027. Anything that does not ship before then is functionally a v2.

The "off-the-shelf alternative" benchmark is concrete: ChatGPT/Claude + Google Scholar + Notion + a shared Telegram chat. A feature is a real differentiator only if it does something this combo demonstrably cannot.

## Feature Landscape

### Table Stakes (Must Have — or the Family Abandons the Tool)

These are the features without which the system has no value. Each traces directly to Core Value.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Continuous literature ingest (Crawl4AI + Firecrawl fallback) on cron** | Without this, the system is just a chatbot — the differentiating claim is "we watch the literature so you don't have to" | M | 6h cron is fine; daily would suffice for v1. PubMed E-utilities + bioRxiv/medRxiv RSS + ClinicalTrials.gov RSS cover ~80% of signal with zero scraping. Crawl4AI only needed for sites that block API access. |
| **Source provenance on every claim (URL, DOI, retrieval date, agent that surfaced it)** | PROJECT.md "Out of Scope" explicitly forbids fabricated citations; a single hallucinated paper destroys family trust | S | Required schema column on every fact. Reject any agent output that lacks it. Cheap to enforce, catastrophic to skip. |
| **Human-readable digest pushed to Telegram (and/or Gmail) on a cadence** | This IS the product surface for the family. If digests don't arrive, the entire pipeline behind them is invisible. | S | One-way push first. Markdown formatting. Top-N findings with confidence + 1-line "why this matters for Aleksandra." |
| **De-duplication + relevance filtering before anything reaches the family** | A pipeline that pushes 200 papers/day is unread within a week. Cognitive load is the real failure mode. | M | Embeddings + a "seen-before" hash on DOI/title. Relevance scoring against a small set of Aleksandra-specific facets (HIE, cystic encephalomalacia, cord blood, vigabatrin, neonatal neuroplasticity). |
| **Persistent corpus you can re-query (vector + metadata, not just a chat history)** | The corpus is the only durable asset; if it lives in ChatGPT threads it can't be re-asked when treatment options change | M | Qdrant + Supabase metadata covers this. Neo4j/Graphiti is nice but not strictly required for v1 — see Differentiators. |
| **Per-fact confidence + "source not found" honesty** | PROJECT.md principle: "ფაქტი არ გამოიგონო. წყარო ვერ მოიძებნა → თქვი" | S | Output schema must allow `confidence: unknown / source: null`. Prompt and post-validation both enforce. |
| **A single human-readable index of Aleksandra's current care state** (diagnoses, active programs, contacts, key dates) | Without grounding, every agent run re-derives context and drifts. Also serves as the family's own working memory. | S | A markdown/Notion page is sufficient. Treat as the canonical patient summary the agents read at every run. |
| **Clinician-shareable export of any finding (PDF or link with all sources)** | The system surfaces; clinicians decide. If a clinician can't quickly see the sources, the lead dies in the email. | S | Single "send this to Dr. Maypole" button → packages findings + provenance into a one-page PDF or shareable Notion link. |
| **Auditable run log (what ran, when, what it found, what it dropped)** | If a credible lead is missed, you must be able to ask "did we even see it?" | S | Append-only log to Supabase. Without this, you cannot debug Core Value failures. |
| **Cost guardrails (per-day spend cap, paid-API fallback gating)** | $20–30/mo MVP ceiling is non-negotiable per constraints; one runaway Firecrawl loop kills the project | S | Hard counter in n8n + Claude API. Stop and Telegram-alert at threshold, don't silently overrun. |

### Differentiators (The Reason This Beats ChatGPT + Google Scholar)

These are where the project earns its existence. Each is a capability the off-the-shelf combo cannot replicate, and each ties back to Core Value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Temporal knowledge graph with confidence decay (Neo4j + Graphiti)** | Medical evidence ages — a 2018 cord-blood result reads differently after 2023 contradicting evidence. Plain vector search can't represent "this used to be true." This is the single biggest reason this project exists beyond "Claude + Notion." | L | Graphiti handles temporal edges natively. The cost is real (Neo4j AuraDB free tier has limits) — but this is the load-bearing differentiator. **If anything in v1 is allowed to slip, it is NOT this.** |
| **Aleksandra-specific relevance model (her facets, her history, her contraindications baked in)** | A generic chatbot does not know vigabatrin washout matters for her Duke EAP timing. A bespoke system can. | M | A small structured patient context (diagnoses, current meds, active trials, contraindications) prepended to every agent prompt and used as a relevance prior. |
| **Cross-disease pattern finding (Hypothesis agent)** | HIE research alone is sparse. Cerebral-palsy, perinatal stroke, and adult ischemic-stroke literatures contain transferable signal. A focused agent looking for "evidence in adjacent populations that might apply" is genuinely novel for a family. | M | CrewAI Hypothesis agent + a small adjacency map (HIE ↔ CP, neonatal stroke, periventricular leukomalacia, anoxic brain injury). |
| **Drug repurposing surfacing (Repurposing agent)** | Vigabatrin, levetiracetam, etc. interact with cord-blood and neuroplasticity windows in non-obvious ways. Off-the-shelf chat will not proactively flag a repurposing candidate. | M | Repurposing agent with a curated list of approved-elsewhere drugs intersected with neonatal-neuroplasticity literature. Outputs are *leads for clinicians*, never recommendations. |
| **Client-side-only MRI viewer (NiiVue + R3F)** | Aleksandra's MRIs never touching a server is a privacy stance the family can defend to any clinician asking. No mainstream tool offers "AI + viewer + zero server-side PHI" today. | M | NiiVue does the viewing; R3F is for the 3D shells. v1 can ship with NiiVue only and defer R3F shells. |
| **Duke EAP / vigabatrin washout / travel timeline as a single calendar** | The logistics of "infusion target July 2026 → washout window → Boston→Durham flight + Booking" are currently scattered. Unifying them prevents missing the trial window. | M | Google Calendar + a single n8n flow that watches washout dates and triggers booking-search prompts. The booking *recommendations* are surfaced; the family books manually. |
| **2-way Telegram (ask_user)** | The system can clarify ambiguous findings before pushing them — "this paper mentions vigabatrin co-administration, does Aleksandra still use vigabatrin?" — preventing low-quality digests. | M | n8n Telegram trigger + a small dialog state machine. v1 can do push-only; ask_user is the upgrade. |
| **Neonatal segmentation pipeline (BIBSnet → BONBID-HIE → nii2mesh)** | Adult segmentation tools produce nonsense on neonatal brains. A neonatal-specific pipeline producing 3D anatomical shells is genuinely rare and valuable for clinician conversations. | L | High complexity, lower urgency relative to literature monitoring. Strong candidate for **post-MVP** — see MVP section. |
| **Shared agent memory (mem0) so agents don't re-derive context every run** | Reduces token cost (matters under $30/mo cap) and produces more coherent multi-run reasoning | S | mem0 layered over the existing patient context. Mostly a cost/quality multiplier, not a primary feature. |
| **DSPy-optimized prompts for the 5 agents** | Hand-written prompts drift. DSPy compiles them against held-out examples. Quality multiplier. | M | Defer until after baseline agents are running; you need traces to optimize against. |

### Anti-Features (Deliberately NOT Build)

Each of these traces back to PROJECT.md "Out of Scope" or violates the bespoke single-patient framing.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Auto-generated clinical recommendations to caregivers** | "The AI should just tell us what to do" feels like the point of an AI medical system | PROJECT.md is explicit: "every decision must be passed through a real clinician." Autonomous recommendations create medical, legal, and ethical liability the family cannot absorb. | System surfaces leads + sources + confidence + open questions. A clinician decides. Output framing uses "evidence suggests" / "open question for Dr. X," never "you should." |
| **Server-side storage of patient MRI/DICOM** | "It would be easier to just upload the NIfTI once and view from anywhere" | PROJECT.md "Out of Scope": privacy + HIPAA blast radius. The moment a DICOM lands on a server you can't control, the project's trust story collapses. | NiiVue client-side viewer; files live on the family's machine. Server-side stores only derived, de-identified metadata (segmentation volumes, not voxels). |
| **A productized "platform for rare pediatric families"** | The stack is clearly capable, and the temptation to "open this up to other HIE families" is real | PROJECT.md "Out of Scope": "Aleksandra is the only patient; productization is not a v1 goal." Multi-tenant adds auth, isolation, PHI segregation, terms-of-service, regulatory exposure — all of which slow the neuroplasticity-window work that is the actual goal. | Build single-tenant. If others ask later, evaluate after the window. |
| **General-purpose chat UI ("ask anything about Aleksandra")** | Looks impressive in demos | Open-ended chat is exactly what ChatGPT already does. The differentiator is *automatic, scheduled, source-cited surfacing* — not query-on-demand. A chat UI also tempts the family to ask medical-advice questions the system must not answer. | Structured digests + a "search the corpus" function with required source display. Not a free-form chatbot. |
| **"Limited outcomes" or prognosis-prediction features** | Medical literature is full of outcome statistics; surfacing them seems factual | PROJECT.md "Out of Scope": "Limited outcomes framing in any user-facing copy — the project's stance is 'unknown potential'." Population-level prognoses are not predictive for an individual and corrode hope without changing care. | Surface mechanisms, interventions, and adjacent evidence. Do not surface population outcome percentages without explicit clinician request. |
| **Auto-booking flights/hotels for Duke logistics** | Booking.com + Kiwi.com MCPs exist and the temptation is real | A booking error during a clinical-trial window is high-cost and low-reversibility. Automation here saves minutes and risks the trip. | The system *suggests* booking windows, surfaces prices, drafts the search. The family clicks book. |
| **Custom mobile app** | "It would be nicer than Telegram" | Telegram is already in the family's daily workflow per PROJECT.md. Building and maintaining a mobile app is months of work that competes directly with the neuroplasticity window. | Telegram + Notion mobile + Gmail. They are the mobile app. |
| **Real-time everything (websockets, streaming digests, live KG updates)** | Modern stack norms | The signal (new credible papers) arrives on the timescale of hours-to-days, not seconds. Realtime adds infra cost and complexity for zero Core Value gain. | Cron-driven (6h) + on-demand re-run. That's the right cadence. |
| **AI-generated MRI segmentation overlays presented to the family as findings** | The pipeline exists (BIBSnet/BONBID) and visuals are compelling | Segmentation is for *clinician conversation support*, not for family-facing claims about "what this means." Showing a heatmap labelled "lesion volume" without a clinician on the call invites misinterpretation. | Segmentation outputs feed clinician-shareable exports only; family-facing views are 3D anatomy, not lesion labels. |
| **A community forum / private social network for HIE families** | Hope for HIE has 6,000+ Facebook members; "we could do better" feeling | Out of scope (PROJECT.md: not a platform) and Hope for HIE already does this well. Building it would duplicate a working community and burn the runway. | Link to Hope for HIE in the family knowledge base. Done. |
| **Public-facing website / SEO / marketing surface** | "If we share our findings publicly we could help others" | Zero Core Value contribution. Also creates implicit medical-advice liability. | If findings are publishable later, publish them through Hope for HIE or peer-review, not from this system. |
| **Voice interface / always-on assistant** | Hands-busy caregivers, infant care, etc. | High infra cost, low marginal Core Value (the digest is async by design — voice doesn't change the signal), and it gives the system a "voice of authority" that conflicts with the clinician-decides principle. | Telegram with notification audio. Sufficient. |
| **Auto-tweeting / auto-posting findings to social** | None requested, but the agent stack makes it trivial — flag pre-emptively | Patient privacy + medical claim liability + zero Core Value | Never. |
| **Generic "explainability dashboard" of the agent's reasoning** | Demos well; lots of OSS examples | The family does not need traceability of *agent reasoning* — they need traceability of *evidence*. Provenance on every claim already covers that. | Provenance schema is the explainability. Skip the dashboard. |

## Feature Dependencies

```
Continuous literature ingest (Crawl4AI/Firecrawl)
    └──feeds──> Vector corpus (Qdrant + fastembed)
                   └──joined-with──> Temporal KG (Neo4j + Graphiti)
                                         └──read-by──> 5 CrewAI agents
                                                          └──produce──> Digests / leads
                                                                            └──delivered-via──> Telegram / Gmail / Notion
                                                                                                   └──shared-with──> Clinician exports

Patient context (canonical summary)
    └──prepended-to──> Every agent prompt
    └──seeds──> Relevance model

Source provenance schema
    └──enforced-on──> Every fact ingested
    └──enforced-on──> Every agent output
    └──surfaced-in──> Every digest

Cost guardrails
    └──gate──> Firecrawl fallback
    └──gate──> Claude API spend per day

Run log
    └──captures──> Every ingest, agent run, digest send
    └──enables──> "Did we miss X?" audits

mem0 shared memory
    └──enhances──> 5 CrewAI agents (reduces re-derivation)

DSPy prompt optimization
    └──requires──> Run log with labelled examples
    └──enhances──> 5 CrewAI agents

Neonatal segmentation pipeline (BIBSnet → BONBID → nii2mesh)
    └──feeds──> 3D viewer (NiiVue + R3F shells)
    └──feeds──> Clinician-shareable exports

NiiVue client-side viewer
    └──independent-of──> All server-side components (this is the point)

Duke EAP timeline + travel logistics
    └──reads──> Vigabatrin washout schedule
    └──reads──> Patient context

Telegram 2-way (ask_user)
    └──requires──> Telegram push (one-way) already working
```

### Dependency Notes

- **KG must come before sophisticated agent reasoning over the corpus.** Agents can run on vector-only for v0, but the cross-disease and repurposing differentiators get materially better with a temporal graph.
- **Provenance schema must be defined before *any* ingest runs.** Backfilling provenance into an unscoped corpus is painful and tempts you to ship without it.
- **Patient context must exist before relevance filtering can work.** A "what is Aleksandra currently on?" doc is a prerequisite for the relevance model.
- **Run log is a prerequisite for DSPy optimization.** You need traces to optimize against.
- **Segmentation pipeline depends only on the viewer for its consumer side**, so it can be developed in parallel with the literature pipeline — but it is *not* on the critical path to Core Value and should not block.
- **2-way Telegram (ask_user) depends on 1-way Telegram push working** — ship push first, add ask_user only after digests are valuable.
- **Cost guardrails block Firecrawl/Claude API use** but should NOT block free-tier Crawl4AI / fastembed / Neo4j AuraDB free / Qdrant Docker.

## MVP Definition

### Launch With (v1 — target: within 4–8 weeks)

The minimum that fulfills Core Value. Be ruthless.

- [ ] **Continuous literature ingest (PubMed + bioRxiv + medRxiv + ClinicalTrials.gov via APIs/RSS, Crawl4AI for the few sources that need scraping)** — without this there is no product
- [ ] **Vector corpus in Qdrant with fastembed** — durable searchable memory
- [ ] **Source provenance schema enforced on every record** — non-negotiable trust foundation
- [ ] **Aleksandra patient context document (canonical summary)** — agents read this every run
- [ ] **Relevance filter (Aleksandra-specific facets)** — kills the "200 papers/day, unread" failure mode
- [ ] **One agent (Spider) that fetches + extracts + writes to corpus with provenance** — start with one, prove the loop
- [ ] **One agent (Communicator) that produces a daily Telegram digest** — closes the loop end-to-end
- [ ] **Telegram one-way push** — the family's primary surface
- [ ] **Clinician-shareable export (markdown → PDF, includes all sources)** — Core Value depends on a clinician acting
- [ ] **Run log (Supabase append-only)** — audit + future DSPy training data
- [ ] **Cost guardrails (per-day spend cap, alert on threshold)** — budget compliance is a hard constraint

**Explicitly NOT in v1:** Neo4j/Graphiti, full 5-agent CrewAI, NiiVue viewer, neonatal segmentation, 2-way Telegram, DSPy, mem0, TVB, custom MCPs beyond what is strictly required, Duke logistics automation.

**Acceptance test for v1:** *Within a 14-day observation window, the family receives at least one digest containing a credible lead that they would not have found via ChatGPT + Google Scholar in the same window, with full source provenance, and at a total cost under $30.*

### Add After Validation (v1.x — weeks 8–20)

These get added only after the v1 loop is demonstrably surfacing leads.

- [ ] **Temporal KG (Neo4j + Graphiti) — promote from "later" to "now" as soon as digest quality plateaus** — this is the differentiator and should not be delayed long
- [ ] **Analyzer + Hypothesis + Repurposing agents (rounds out the 5-agent CrewAI)** — each added when the prior layer is stable
- [ ] **2-way Telegram (ask_user clarifications)** — improves digest quality
- [ ] **mem0 shared memory** — token-cost optimization, quality multiplier
- [ ] **Notion family knowledge base sync** — durable family-readable archive
- [ ] **Gmail digest as a secondary channel** — backup when Telegram is noisy
- [ ] **Google Calendar treatment timeline (Duke EAP + vigabatrin washout windows)** — logistics support
- [ ] **NiiVue client-side viewer (minimal, no R3F shells yet)** — clinician conversation support
- [ ] **DSPy optimization pass on the 5 agents** — requires a run-log corpus to be useful

### Future Consideration (v2 — after Aug 2027 neuroplasticity window)

If the v1+v1.x system is working, these are the upgrades. None of them should jeopardize the window.

- [ ] **Neonatal segmentation pipeline (BIBSnet → BONBID-HIE → nii2mesh)** — high complexity, not on the Core Value critical path
- [ ] **R3F 3D anatomical shells** — visualization polish
- [ ] **TVB Docker brain simulation** — interesting research, but not Core Value
- [ ] **brain2print STL export** — novelty, optional
- [ ] **Hindsight self-improving memory** — quality multiplier, needs the system mature first
- [ ] **All 5 custom MCPs polished and published** — only if there is genuine community demand
- [ ] **Booking/Kiwi.com travel automation beyond suggestion-only** — only after Duke EAP completes once successfully under manual booking

## Feature Prioritization Matrix

| Feature | Family Value | Cost | Priority |
|---------|------------|------|----------|
| Continuous literature ingest | HIGH | M | P1 |
| Source provenance schema | HIGH | S | P1 |
| Vector corpus (Qdrant + fastembed) | HIGH | M | P1 |
| Patient context document | HIGH | S | P1 |
| Relevance filter | HIGH | M | P1 |
| Spider agent (ingest + extract) | HIGH | M | P1 |
| Communicator agent (digest) | HIGH | M | P1 |
| Telegram one-way push | HIGH | S | P1 |
| Clinician-shareable export | HIGH | S | P1 |
| Run log | MEDIUM | S | P1 |
| Cost guardrails | HIGH | S | P1 |
| Temporal KG (Neo4j + Graphiti) | HIGH | L | P2 |
| Analyzer / Hypothesis / Repurposing agents | HIGH | M | P2 |
| 2-way Telegram (ask_user) | MEDIUM | M | P2 |
| mem0 shared memory | MEDIUM | S | P2 |
| Notion family KB sync | MEDIUM | S | P2 |
| Google Calendar treatment timeline | MEDIUM | M | P2 |
| NiiVue client-side viewer | MEDIUM | M | P2 |
| DSPy prompt optimization | MEDIUM | M | P2 |
| Neonatal segmentation pipeline | MEDIUM | L | P3 |
| R3F 3D anatomical shells | LOW | M | P3 |
| TVB brain simulation | LOW | L | P3 |
| brain2print STL export | LOW | M | P3 |
| Hindsight memory | LOW | M | P3 |
| Travel auto-booking | LOW | M | P3 (anti-feature-leaning) |

**Priority key:**
- P1: In v1 MVP — without this the system cannot deliver Core Value
- P2: Add after v1 validates — these elevate quality from "useful" to "genuinely differentiated"
- P3: Defer past the neuroplasticity window — interesting, not on the critical path

## Scope Creep Audit (Honest Assessment of Stated Wants)

The PROJECT.md and CLAUDE.md list ~52 MCPs and a large feature list. Cutting it honestly:

| Stated want | Verdict | Reasoning |
|-------------|---------|-----------|
| Continuous literature ingest (Crawl4AI + Firecrawl + Browser Use) | **Core (Browser Use deferred)** | Browser Use is for paywall bypass; defer until a paywalled source is proven to block real signal. PubMed + bioRxiv + medRxiv + ClinicalTrials.gov are open and cover the bulk of HIE literature. |
| Temporal KG (Neo4j + Graphiti) with confidence decay | **Core differentiator, but not v1-week-1** | Promote to P2 — ship the linear pipeline first, then layer KG on top once you have a real corpus to model. |
| Vector + graph fusion (LightRAG) | **P2** | LightRAG only matters once you have both stores populated. v1 is vector-only. |
| 5-agent CrewAI | **P1 for 2 agents, P2 for the other 3** | Spider + Communicator close the loop. Analyzer, Hypothesis, Repurposing are differentiators added once the loop is real. |
| Client-side MRI viewer (NiiVue) | **P2** | Important, but not Core Value. Aleksandra's MRIs exist; viewing them is for clinician conversations, not for "never miss a lead." |
| Neonatal segmentation pipeline (BIBSnet → BONBID) | **P3** | Genuinely cool, high complexity, not on the Core Value critical path. Defer. |
| Telegram 2-way | **One-way is P1, ask_user is P2** | Push the digest first; clarification dialog is an enhancement. |
| Notion KB + Gmail + Calendar | **Notion P2, Gmail P2, Calendar P2** | Telegram is the v1 surface. Others are durable backups added after. |
| Duke EAP + Booking + Kiwi travel automation | **Suggestion-only, never auto-book** | Auto-booking around a clinical trial window is a tail-risk you cannot accept. Suggest, don't act. |
| TVB brain simulation, brain2print, all 5 custom MCPs | **P3 / cut from v1 entirely** | These are research-grade nice-to-haves with zero Core Value contribution before Aug 2027. |
| mem0, DSPy, Hindsight, Prism, LightRAG | **All P2 quality multipliers, none P1** | Each makes an existing thing better; none constitutes Core Value on its own. |
| All 52 MCPs configured and live | **No — start with ~5** | MCP-per-feature cost (config, auth, version drift) is real. Start with the MCPs you actually exercise on day 1: Telegram, Gmail, Notion, Supabase/Qdrant access, one scraping MCP. Add others on demand. |

## "Off-the-Shelf Alternative" Stress Test

For each P1 feature, why doesn't "ChatGPT + Google Scholar + Notion + Telegram chat" suffice?

- **Continuous ingest:** ChatGPT cannot run a 6h cron. Scholar Alerts are noisy and don't dedupe. **Genuine gap.**
- **Source provenance enforcement:** Generic chat hallucinates citations. **Genuine gap.**
- **Vector corpus you can re-query:** Chat threads are not persistent searchable memory. **Genuine gap.**
- **Aleksandra-specific relevance filter:** Generic chat has no patient context across sessions. **Genuine gap.**
- **Daily digest with confidence + sources:** Manual workflow; falls apart in week 3 under sleep deprivation. **Genuine gap.**
- **Clinician-shareable export:** A messy chat transcript is not a clinician handoff artifact. **Genuine gap.**
- **Run log / audit:** Off-the-shelf has none. **Genuine gap.**

Every P1 has a defensible reason. If a P2 feature stress-tests poorly against the off-the-shelf benchmark, demote it.

## Trace to PROJECT.md Out of Scope

Every anti-feature above maps to PROJECT.md "Out of Scope":

| Anti-feature | PROJECT.md "Out of Scope" entry |
|--------------|-------------------------------|
| Server-side DICOM storage | "Server-side storage of patient MRI / DICOM — privacy and HIPAA blast radius" |
| Auto-generated clinical recommendations | "Auto-generated clinical recommendations to caregivers — every decision must be passed through a real clinician" |
| Productization / multi-tenant platform | "A general-purpose pediatric platform — Aleksandra is the only patient; productization is not a v1 goal" |
| Prognosis / "limited outcomes" features | "'Limited outcomes' framing in any user-facing copy — the project's stance is 'unknown potential'" |
| Hallucinated / unsourced claims | "Fabricated citations or paraphrased claims without a verifiable source — 'source not found' is an acceptable answer" |
| Auto-booking flights/hotels | Derived from clinician-decides principle: irreversible actions stay with humans |
| Custom mobile app, real-time everything, voice UI | Derived from budget + time constraints + neuroplasticity window pressure |

## Trace to Core Value

Each P1 feature traces to "Never miss a credible treatment lead for Aleksandra":

- Continuous ingest → expands the *set* of papers seen (reduces miss probability)
- Relevance filter → ensures credible leads are not buried in noise (reduces miss probability via fatigue)
- Source provenance → makes "credible" verifiable (defines credible)
- Patient context → ensures relevance is judged for *Aleksandra*, not generic HIE
- Spider + Communicator agents → close the loop from web → family
- Telegram digest → the family actually sees the lead (delivery is the last mile)
- Clinician-shareable export → the lead converts to clinical action (Core Value's *intent*)
- Run log → enables "did we miss X?" diagnosis when the answer is yes
- Cost guardrails → the system stays alive (a paused system misses everything)

## Sources

- [Resources for Patients and Families | Rare Diseases Clinical Research Network](https://www.rarediseasesnetwork.org/resources/patients-families)
- [Exploring the role of digital tools in rare disease management: An interview-based study (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11735183/)
- [Navigating the Unique Challenges of Caregiving for Children with Rare Diseases (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11313382/)
- [Hope for HIE — community + advocacy reference](https://hopeforhie.org/)
- [Hypoxic-Ischemic Encephalopathy | Boston Children's Hospital](https://www.childrenshospital.org/conditions-treatments/hypoxic-ischemic-encephalopathy)
- [Hypoxic Ischemic Encephalopathy | NINDS](https://www.ninds.nih.gov/health-information/disorders/hypoxic-ischemic-encephalopathy)
- [Expanded Access Protocol of Umbilical Cord Blood Infusion for Children with Neurological Conditions (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8449593/)
- [Cord Blood Treatment for Children With Cerebral Palsy: Individual Participant Data Meta-Analysis (Pediatrics, 2025)](https://publications.aap.org/pediatrics/article/155/5/e2024068999/201565/Cord-Blood-Treatment-for-Children-With-Cerebral)
- [Expanded Access Protocol: Umbilical Cord Blood Infusions — ClinicalTrials.gov NCT03327467](https://clinicaltrials.gov/study/NCT03327467)
- [N-of-1 Healthcare: Challenges and Prospects (Frontiers, 2022)](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2022.830656/full)
- [The Patient Experience of the Future is Personalized: N of 1 Approach (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10084530/)
- [A Review of Multi-Agent AI Systems for Biological and Clinical Data Analysis (MDPI)](https://www.mdpi.com/2409-9279/9/2/33)
- [AI Agents in Clinical Medicine: A Systematic Review (PubMed)](https://pubmed.ncbi.nlm.nih.gov/40909853/)
- [KARMA: Multi-Agent LLMs for Automated Knowledge Graph Enrichment (OpenReview)](https://openreview.net/pdf?id=k0wyi4cOGy)
- [Elicit — AI for scientific research (alerting workflow reference)](https://elicit.com/)
- PROJECT.md (this project, 2026-05-13) — Core Value, Active requirements, Out of Scope, Constraints
- CLAUDE.md (this project, 2026-05-13) — architecture, principles, patient context

---
*Feature research for: Bespoke single-patient pediatric medical-research cockpit (ALEKSANDRA_BRAIN)*
*Researched: 2026-05-13*
