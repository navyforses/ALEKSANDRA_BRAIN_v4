# Pitfalls Research — ALEKSANDRA_BRAIN

**Domain:** Family-operated agentic medical research cockpit (rare pediatric neurology — severe HIE)
**Researched:** 2026-05-13
**Confidence:** HIGH (medical-evidence pitfalls cite primary literature 2025–2026); MEDIUM (engineering pitfalls cite vendor docs + community post-mortems); HIGH (ethical pitfalls grounded in the project's own constitution)

> The 5 architectural layers used throughout this doc map to the project:
> **Perception** (Crawl4AI / Firecrawl / Browser Use / RAGFlow / n8n)
> **Memory** (Neo4j+Graphiti / Qdrant / Supabase / LightRAG / mem0 / Hindsight / Prism / R2/KV)
> **Cognition** (CrewAI 5 agents / Claude Sonnet 4 / Adaptive GoT / DSPy / Vercel AI SDK)
> **Visualization** (NiiVue / R3F / FastSurfer→BIBSnet→BONBID→nii2mesh / TVB / brain2print)
> **Action** (Telegram 2-way / Gmail / Notion / Calendar / Booking+Kiwi)

---

## Critical Pitfalls

### Pitfall 1: Fabricated citations surfaced to the family as "evidence"

**Severity:** CATASTROPHIC
**Category:** Medical-evidence

**What goes wrong:**
The LLM (Claude Sonnet 4 in the Spider / Analyzer / Hypothesis agents) emits a citation that looks plausible — correct journal name, plausible author, DOI-shaped string — that does not resolve to a real paper, or resolves to a real paper that does not actually contain the claim. The Communicator agent passes this into a Telegram digest. The family forwards it to Drs. Hien / August / Maypole / Heitman. Trust with the clinical team collapses.

**Why it happens:**
LLMs do not retrieve — they pattern-match. Recent audits found 19.9% of GPT-4o citations in literature reviews are entirely fabricated, 45.4% of seemingly-real citations contain bibliographic errors (most often invalid DOIs), and hallucinated citations in biomedical literature jumped 12× in two years. Rare-disease / pediatric-HIE topics are *under-represented* in training data, which raises hallucination rates further.

**Detection (warning signs):**
- A citation's DOI does not resolve via `https://doi.org/{doi}` → 404
- A claimed PMID returns no record from the NCBI E-utilities `esummary` endpoint
- The cited paper exists but a verbatim phrase search inside the full-text returns 0 hits
- More than one citation per digest points to the same author cluster (sign of confabulation)

**Prevention (concrete):**
1. **Citation tuple as a first-class type.** Every agent output must carry `{source_id, retrieval_timestamp, confidence, retrieval_method}` where `retrieval_method ∈ {pubmed_eutils, clinicaltrials_api, crawl4ai_url, firecrawl_url, manual}`. If `retrieval_method == manual` or missing, the claim cannot leave the Cognition layer.
2. **Verifier agent gates the Communicator.** Before any fact reaches Telegram/Gmail, a deterministic (non-LLM) verifier round-trips every citation: PMID → E-utilities, DOI → resolver, ClinicalTrials.gov ID → CT.gov API, URL → HEAD 200. Anything that fails → claim degraded to "unverified — source not located," never silently dropped.
3. **Verbatim grounding.** The Analyzer must store a verbatim quote (≥ 30 chars) per claim and the byte offset in the source. The verifier confirms the quote appears in the retrieved document.
4. **"Source not found" is a valid answer.** Enforce in the Communicator's system prompt and in the digest schema — null citation field is allowed; fabrication is not.

**Phase to address:** Memory phase (citation tuple schema in Graphiti + Supabase) and Cognition phase (verifier agent). Both must land before Action phase ships any user-facing digest.

---

### Pitfall 2: Shared-memory poisoning across the 5 CrewAI agents

**Severity:** HIGH
**Category:** Engineering

**What goes wrong:**
Spider hallucinates a "fact" ("vigabatrin washout is 14 days"). It is written to mem0 / Graphiti as ground truth. Analyzer reasons on it. Hypothesis builds a theory on it. Repurposing weights a drug on the wrong constraint. Communicator pushes it to the family. The original error never resurfaces because every downstream agent treats it as canon. This is the documented "context poisoning" cascade — one hallucination becomes ground truth for every reasoner that follows it.

**Why it happens:**
mem0 and Graphiti are designed for fast persistence — they do not by default distinguish *who* wrote a fact, *which retrieval grounded it*, or *whether a clinician confirmed it*. Multi-agent systems fail at 41–86.7% rates in production largely because of unstructured shared-state.

**Detection (warning signs):**
- Two agents repeat the same wrong fact in the same digest using different phrasing → evidence of shared-memory replay rather than independent verification
- The Graphiti node has no `derived_from` edge to a `Source` node
- Confidence on a fact rises across runs without any new source supporting it (echo-chamber signature)

**Prevention (concrete):**
1. **Memory write contract.** Every write into mem0 / Graphiti must include `author_agent`, `derived_from_source_ids[]`, `confidence`, `created_at`. Writes without `derived_from_source_ids` are rejected at the memory boundary.
2. **Read-time provenance check.** Agents downstream of Spider must traverse `derived_from` to verify at least one terminal `Source` node before treating a fact as input. No source chain → fact is downgraded to `hypothesis` and cannot leave Cognition.
3. **No agent writes to another agent's namespace.** mem0 supports per-`agent_id` scoping — use it. Cross-agent communication goes through CrewAI tasks (explicit), not through memory side-effects (implicit).
4. **Confidence decay on un-reinforced facts** (Graphiti supports this) — a fact that has not been re-grounded in a fresh retrieval within N days drops below the read threshold.

**Phase to address:** Memory phase (schema + write-contract) before Cognition phase brings the 5 agents online together.

---

### Pitfall 3: Off-label / repurposing suggestions framed as recommendations

**Severity:** CATASTROPHIC
**Category:** Medical-evidence + ethical

**What goes wrong:**
The Repurposing agent finds a signal that drug X (approved for adult condition Y) has a putative mechanism relevant to cystic encephalomalacia. The Communicator phrases it as "consider asking Dr. Hien about drug X." The family asks. The clinician now must defend not prescribing — the AI has shifted the decision-making frame. Worse: 2024 JCO analysis showed all four tested LLMs (incl. GPT-4, Gemini 1.5) produced responses recommending treatment combinations *not supported by the FDA-approved label*. For a 9-month-old on vigabatrin with a Duke EAP enrollment in flight, an off-label suggestion that contraindicates the protocol can cost the cord-blood window.

**Why it happens:**
LLMs are tuned to be helpful; "here is a paper" naturally drifts into "here is what you should do." The Communicator agent's "family liaison" role description in CrewAI primes it toward action-oriented language. The learned-intermediary doctrine that protects pharma manufacturers does not yet have a clean analog for AI-driven prescribing nudges.

**Detection (warning signs):**
- Digest contains second-person imperatives ("ask," "request," "consider"). Audit the last 20 digests — count imperatives.
- Digest names a specific drug without naming the specific paper, dose, study population, and the gap between study population and Aleksandra
- A clinician on the team flags an "interesting" suggestion (this is already a smell — the system was supposed to surface, not suggest)

**Prevention (concrete):**
1. **Output schema separates "evidence" from "action."** Communicator output is `{finding, source, evidence_strength, population_gap, clinician_question_template}`. The `clinician_question_template` is phrased as a question *to* a clinician, never an instruction *for* a family member.
2. **Hard blocklist on imperative phrasing.** Lint the Communicator output for verbs `{should, must, consider, try, ask for, request}` directed at the family. Allowed: "Question for Dr. X: …".
3. **Six-tier evidence ranking** (per AI-drug-repurposing literature): `published treatment | symptom mgmt | co-morbidity tx | feasible | possible contraindication | unknown`. Anything in tiers 3–6 may not be top-of-digest.
4. **Population-gap field is mandatory.** Every drug/intervention mention must declare: "Studied in: adult ischemic stroke, n=42. Aleksandra: neonatal cystic encephalomalacia. Generalization risk: HIGH."

**Phase to address:** Cognition phase (Communicator's system prompt + output schema) and Action phase (digest template lint).

---

### Pitfall 4: "Limited outcomes" framing leaking into user-facing copy

**Severity:** HIGH
**Category:** Ethical / communication

**What goes wrong:**
The training data of Claude Sonnet 4 — and the medical literature it summarizes — is saturated with prognostic language about severe HIE: "poor outcome," "minimal recovery expected," "limited functional potential." The Communicator paraphrases. The phrase appears in a Telegram message read by a sleep-deprived parent at 02:00. The project's stated constitution ("unknown potential," not "limited outcomes") is silently violated.

**Why it happens:**
The bias is in the source corpus, not the prompt. Medical literature on severe HIE was written before / outside the neuroplasticity-first framing this project adopts. Without active filtering, the system inherits the corpus's prognostic posture.

**Detection (warning signs):**
- Any of the following substrings appear in Action-layer output: `limited`, `poor outcome`, `severe disability`, `minimal recovery`, `will not`, `unable to`, `permanent damage`, `static encephalopathy`
- A summary of a paper drops the qualifiers the paper itself used (e.g., paper says "in this cohort," summary says "children with this MRI")
- The digest's tone test (run weekly) returns a Communicator output that the family rates as "deflating"

**Prevention (concrete):**
1. **Tone lexicon — explicit allow/deny.** Maintain `taxonomy/tone.yaml` with `denied_phrases[]` and `preferred_reframings{}` (e.g., `"poor prognosis" → "outcome unknown; cohort outcome was X"`). Run as a deterministic post-processor on every Communicator output.
2. **Quote, don't paraphrase, prognostic claims.** If a paper says "poor outcome," the digest must say *"the paper states: 'poor outcome'"*, with the cohort and the date — never the system's own voice asserting it.
3. **Reframe MRI structural findings.** Every imaging-derived claim carries a fixed footer: "Structural MRI findings do not by themselves predict functional capacity in the 0–2 neuroplasticity window."
4. **Weekly tone audit** — Communicator outputs across 7 days hashed, manually reviewed against the lexicon. Drift detected → DSPy re-optimization triggered with the audited examples as negative exemplars.

**Phase to address:** Cognition phase (Communicator prompt + lexicon) — must land *before* the first Telegram digest goes out.

---

### Pitfall 5: Recency bias swamping legacy evidence + preprint over-weighting

**Severity:** HIGH
**Category:** Medical-evidence

**What goes wrong:**
The Spider agent on its 6-hour cron is biased toward "new." Fresh PubMed indexes, new bioRxiv preprints, recent ClinicalTrials.gov postings all rank higher because they are newer. Graphiti's "temporal decay" amplifies this — old facts decay, new facts dominate. Result: a 2008 Cochrane review with rigorous methodology is outweighed by three 2026 preprints that have not survived peer review. Research shows preprint→peer-review changes effect estimates by ~6% on average but tightens CIs ~7% — and a non-trivial fraction of preprints never get published.

**Why it happens:**
- Cron schedulers reward freshness.
- Graphiti's temporal-decay primitive was designed for *operational* facts (a status, a config, a user preference), not for *evidence quality* (a 20-year-old RCT is still better than a fresh editorial).
- Preprints arrive faster than peer-reviewed versions, so they dominate any time-window-based retrieval.

**Detection (warning signs):**
- Top-3 digest items from the last 30 days are all <12 months old and none are systematic reviews / RCTs
- Graphiti queries scored by recency-only return 0 results when filtered to "peer-reviewed and `evidence_grade >= moderate`"
- A specific claim's confidence rises only because of preprint accumulation (no peer-reviewed reinforcement)

**Prevention (concrete):**
1. **Evidence-grade is a first-class field**, ranked above recency in retrieval. Schema: `evidence_grade ∈ {systematic_review, rct, cohort, case_series, case_report, preprint, opinion, news}`. Communicator scoring formula: `score = w_grade * evidence_grade + w_relevance * cosine + w_recency * recency_decay`, with `w_grade > w_recency`.
2. **Preprint flag is sticky and visible.** Every preprint is marked `preprint: true` until a `peer_reviewed_doi` is back-linked. Digests must visually mark preprints (e.g., "[PREPRINT — not peer reviewed]").
3. **Confidence weighting per preprint publication likelihood.** Use the AI-driven approach: weight preprint contribution to a Graphiti fact by `p_eventual_publication` (heuristic: journal venue history + author H-index + months-since-posting).
4. **Periodic re-balance.** Every 30 days, the Analyzer re-runs old-vs-new evidence reconciliation; any Graphiti fact whose evidence base flipped should be re-flagged for the family.

**Phase to address:** Memory phase (schema) and Cognition phase (Analyzer logic).

---

### Pitfall 6: Negative-evidence blindness (the "absence of evidence" trap)

**Severity:** HIGH
**Category:** Medical-evidence

**What goes wrong:**
The Spider agent is trained to find "papers supporting treatment X for HIE." It does not retrieve papers showing X *failed* in HIE, nor protocols that were *halted*, nor null-result trials. Publication bias amplifies this — negative trials are 2–3× less likely to be published in the first place. The system's evidence picture is systematically inflated toward "things might work."

**Why it happens:**
- LLM-generated Boolean search strategies "lack stability" and over-rely on positive-framing keywords.
- Hypothesis agents and Repurposing agents are explicitly optimization-oriented ("find a candidate"), not falsification-oriented ("disprove a candidate").
- AI tools "hallucinate" MeSH terms and miss key studies — disproportionately the harder-to-find negative ones.

**Detection (warning signs):**
- The corpus in Qdrant has < 15% of papers tagged `outcome = null/negative/halted` (the literature base rate is ~30–40%)
- ClinicalTrials.gov retrievals exclude trials with status `Terminated`, `Withdrawn`, `Suspended`
- Repurposing agent has never returned "X is contraindicated for Aleksandra because Y" in its output history

**Prevention (concrete):**
1. **Spider has two retrieval modes.** `mode=positive` (default) and `mode=negative` (forced: query rewriter prefixes "failure," "ineffective," "halted," "contraindicated," "adverse," "withdrawn"). Cron schedules both.
2. **Ingestion preserves trial status.** ClinicalTrials.gov scraping (via the *official API*, see Pitfall 9) must persist `overall_status` — `Terminated` / `Withdrawn` / `Suspended` records are kept and tagged, not filtered out.
3. **A dedicated "negative evidence" view in the digest.** Every weekly Communicator digest contains a fixed section: "Counter-evidence for currently-tracked candidates" — empty section is itself a red flag.
4. **Falsifier role on the Hypothesis agent.** Add a falsification step: for every hypothesis emitted, the agent must search for and report the strongest counter-evidence before passing it to Communicator.

**Phase to address:** Perception phase (negative-mode scraping) + Cognition phase (Hypothesis falsifier step).

---

### Pitfall 7: Scraper IP-blocking from PubMed / ClinicalTrials.gov / publisher sites

**Severity:** HIGH (operational — kills the literature pipeline = kills core value)
**Category:** Engineering

**What goes wrong:**
Crawl4AI hits PubMed at unpolite rates, NCBI rate-limits or IP-bans the Railway egress IP. Same agent then hits ClinicalTrials.gov, which serves bootstrap JS (the site is now an SPA — screen-scraping returns no actual study data); the agent silently captures empty pages. Firecrawl fallback engages but burns the $20–30 MVP budget in days. The system goes dark on its single most important capability.

**Why it happens:**
- NCBI rate-limits anonymous E-utilities to 3 req/s without an API key, 10 req/s with one.
- ClinicalTrials.gov screen-scraping has been broken since the SPA rewrite — the NLM tech bulletin (Jul/Aug 2025) explicitly says: use the API.
- Publisher sites (Elsevier, Wiley, Springer) actively block scrapers and rotate Cloudflare challenges.
- The Crawl4AI default user-agent is bot-flagged.

**Detection (warning signs):**
- HTTP 429 / 403 counts in Crawl4AI logs > 1% of requests
- `len(extracted_content) == 0` rate spikes on ClinicalTrials.gov targets
- Firecrawl spend in n8n's monthly dashboard > $5 in any week of MVP phase
- New paper count per 6h cron drops below baseline (e.g., from ~50 → < 5)

**Prevention (concrete):**
1. **Use APIs, not scrapers, for the structured sources.** PubMed → E-utilities with `&api_key=...` (free, register an NCBI account). ClinicalTrials.gov → official v2 API. Crawl4AI is for *publisher landing pages and full-text where allowed*, never for the indexes.
2. **Respect rate limits explicitly.** 3 req/s anonymous, 10 req/s authenticated for NCBI; `Retry-After` honored everywhere. Implement at the scraper layer, not at the agent layer.
3. **User-agent identifies the project** with a contact mailto (NCBI policy expects this). Example: `ALEKSANDRA_BRAIN/0.1 (research; mailto:jincharadzeshako@gmail.com)`.
4. **Firecrawl is metered.** Hard ceiling in n8n: kill the workflow at `monthly_firecrawl_spend > $10` (MVP) / `$50` (full). Browser Use only fires on Crawl4AI failure *and* Firecrawl failure — never as default.
5. **Cache aggressively** (CF KV with 7-day TTL on paper metadata) so re-runs do not re-hit the same endpoints.

**Phase to address:** Perception phase. This is the first thing to harden — the whole project depends on the literature pipeline staying alive.

---

### Pitfall 8: Vector ↔ graph desynchronization (Qdrant drift vs Graphiti truth)

**Severity:** HIGH
**Category:** Engineering

**What goes wrong:**
Spider ingests a paper. Graphiti gets an entity + provenance. Qdrant gets fastembed vectors of the abstract. Six weeks later, Spider re-ingests an updated version (preprint → peer-reviewed); Graphiti's confidence updates, but Qdrant's vector is stale (still pointing to the preprint chunks). LightRAG queries that join graph+vector return contradictory answers — Graphiti says "peer-reviewed, confidence 0.85," Qdrant retrieves the preprint chunks. Embedding-drift literature calls this "the silent killer of RAG accuracy."

**Why it happens:**
- The two stores have different write paths (Graphiti = Graphiti SDK; Qdrant = direct upsert via fastembed).
- Partial re-embedding (only 20% of corpus refreshed) puts vectors from two different preprocessing eras in the same index.
- Model switches (fastembed model version bump) silently invalidate old vectors against new queries.
- Chunking heuristics change ("fix HTML stripper," "add Unicode normalization") and old chunks no longer match new ones.

**Detection (warning signs):**
- Same query through LightRAG returns different graph-fact and top-vector-doc more than 5% of the time
- Qdrant `payload.embedding_model_version` is heterogeneous in the same collection
- `count(qdrant_doc_id) ≠ count(graphiti_source_node)` after a 6h cron run

**Prevention (concrete):**
1. **Single-writer ingestion path.** Only one service (the n8n "ingest" workflow) writes to both stores in the same transaction-shaped pipeline: write Graphiti node, write Qdrant point with same `source_id`, fail closed if either fails.
2. **Embedding versioning.** Every Qdrant point carries `payload.embedding_model = "fastembed:BAAI/bge-small-en-v1.5@<sha>"` and `payload.chunker_version`. Re-embeds on model bump are full-corpus and atomic; mixed-version queries are rejected.
3. **Schema contract between layers.** A `Source` node in Graphiti must have a `qdrant_point_ids[]` field; a Qdrant point must have `payload.graphiti_uuid`. Nightly reconciler asserts bijection.
4. **Idempotent ingestion** — content hash (`sha256(normalized_full_text)`) is the canonical key in both stores. Re-running the same scrape never creates duplicates.

**Phase to address:** Memory phase (schema + ingest pipeline) — must land before LightRAG queries are exposed to agents.

---

### Pitfall 9: MCP server sprawl (52 servers → context pollution, secret leaks, supply-chain risk)

**Severity:** MEDIUM–HIGH
**Category:** Engineering / security

**What goes wrong:**
The stated arsenal is 52 MCPs (23 registry + 19 self-hosted + 5 AI Pulse + 5 custom). Each exposes 5–20 tools. The Claude context window is filled with thousands of tool descriptors *before* the conversation begins. Tool-selection accuracy degrades, latency rises, costs rise. Worse: secrets leak — recent surveys found MCP servers are a top new vector for credential exposure (GitGuardian), and 11 distinct MCP-specific risks (sensitive data exfiltration, unauthorized agent actions, supply-chain exposure, missing audit trails) have been catalogued.

**Why it happens:**
- "Spin up an MCP server in minutes" → no governance.
- Registry MCPs pull arbitrary code on update — supply-chain.
- Tool descriptors are loaded eagerly into the system prompt by default.
- No central inventory of which MCP has which scope.

**Detection (warning signs):**
- Average tokens-in-system-prompt for any CrewAI agent > 8K
- Any MCP runs with permissions broader than its single documented use
- `.env` / config files referenced by an MCP land in commit history
- More than one MCP can perform the same action (e.g., two Telegram MCPs) — ambiguity = attack surface

**Prevention (concrete):**
1. **Per-agent MCP allowlist, not global.** Spider gets `crawl4ai-rag`, `firecrawl`, `pubmed-eutils`. Communicator gets `telegram`, `gmail`, `notion`. No agent gets the union.
2. **Two-tool meta pattern for big surfaces** (Cloudflare reference architecture): rather than 200 fine-grained tools, expose `search_tools(query)` + `execute_tool(name, args)`. Cuts context-window cost by ~90%.
3. **Sealed secrets.** No MCP reads `.env` directly; secrets injected via a vault (1Password CLI / SOPS / CF secrets). `mcp-config-validator` pre-commit hook rejects any config that hardcodes a token.
4. **MCP inventory CSV** (`docs/mcp-inventory.md`): name, repo URL, pinned commit SHA, scopes, last-reviewed date, which agent uses it. Anything > 90 days unreviewed is auto-disabled.
5. **Custom MCPs (FastMCP) are the canonical pattern for anything touching patient data.** Registry MCPs are read-only / public-data only.

**Phase to address:** Foundation phase (governance + inventory) and every phase that adds a new MCP.

---

### Pitfall 10: Notification fatigue → desensitization to actual important findings

**Severity:** HIGH
**Category:** UX / communication

**What goes wrong:**
The 6-hour cron emits 4 digests/day. After a week, the family scrolls past them. The one digest that surfaces a genuinely-actionable Duke EAP update gets the same eye-pattern as the 27 routine ones. Core value ("never miss a credible lead") fails not because the system missed it, but because the family did.

**Why it happens:**
- Default Telegram bot UX = post-everything-as-it-arrives.
- No tiering between "we found 6 new tangentially-relevant papers" and "vigabatrin washout window changed."
- LLM tone is uniform — the urgent digest reads like the routine one.

**Detection (warning signs):**
- Telegram message-open-rate on cron digests < 50% after week 2
- Time-to-read on the most recent 10 digests is < 5 seconds (family is skimming/dismissing)
- Family asks "did you tell me about X?" for an X that *was* in a digest

**Prevention (concrete):**
1. **Three urgency tiers,** rendered differently:
   - `routine` → silent digest, batched into a single 8am Gmail summary
   - `notable` → Telegram message, no sound, persists in pinned "this week"
   - `urgent` → Telegram message + sound + `ask_user` confirmation that it was read
2. **Urgency is determined by a classifier**, not the Communicator's discretion. Criteria: explicit Aleksandra-relevant intervention update, logistics deadline (Duke EAP, vigabatrin washout), or a contradiction with currently-tracked evidence.
3. **Quiet hours.** No `notable`/`routine` between 22:00–07:00 Boston time. `urgent` always passes.
4. **Weekly "what I almost didn't tell you" digest** — Communicator surfaces the lowest-confidence findings of the week so the family knows what was filtered.

**Phase to address:** Action phase. Critical because it gates whether the rest of the system has real-world impact.

---

### Pitfall 11: Patient MRI accidentally leaving the browser

**Severity:** CATASTROPHIC
**Category:** Privacy / security

**What goes wrong:**
NiiVue is designed as client-side, but a careless edit adds a "share view" feature that POSTs the loaded volume to a backend "for analysis." Or the FastSurfer pipeline (which runs on a server) is wired through Aleksandra's actual scan instead of a synthetic test volume. Or browser dev-mode logging writes the volume to console which gets captured by Vercel's edge logs. The non-negotiable constraint ("MRI never persisted on a server") is violated.

**Why it happens:**
- Convenience features creep in (share-link, server-side rendering for thumbnails).
- The neonatal pipeline (FastSurfer → BIBSnet → BONBID-HIE → nii2mesh) is server-side by nature — easy to accidentally pipe real data through it.
- Vercel + browser telemetry are not designed with PHI in mind.

**Detection (warning signs):**
- Any network request from the viewer with `content-type: application/octet-stream` or `application/dicom` going to anywhere outside `localhost` / `blob:` / `data:`
- Any backend log entry containing `.nii`, `.nii.gz`, or `.dcm` filenames tied to Aleksandra
- A "share" / "export" / "save" button exists on the viewer
- The neonatal segmentation pipeline runs against real MRI (it should run only against open-source test volumes or against synthetic / anonymized data that the family explicitly uploads on their own infra)

**Prevention (concrete):**
1. **CSP header on the viewer** restricts `connect-src` to `'self' blob: data:` only — no third-party POST possible.
2. **Volume loading is `File` / `FileSystemFileHandle` only** — no `fetch()` of a remote `.nii.gz`. Forces user-initiated local selection.
3. **Disable browser telemetry / source maps for the viewer build.** Strip `console.log` in production.
4. **Segmentation pipeline runs on the family's local machine** (Docker locally) or never on real data. Cloud-hosted FastSurfer/BIBSnet is only allowed against synthetic test volumes (and tagged as such in the repo).
5. **Pre-commit hook**: any TS/TSX file in `/viewer/` that introduces `fetch(`, `axios.post`, or `new XMLHttpRequest()` to a remote origin fails CI unless explicitly allowlisted.
6. **Quarterly red-team**: a manual review walks the network tab during an MRI load and confirms zero outbound bytes carry imaging data.

**Phase to address:** Visualization phase — non-negotiable gate before the viewer is shipped, even to the family privately.

---

### Pitfall 12: Family/clinician boundary erosion ("the AI said…")

**Severity:** HIGH
**Category:** Ethical

**What goes wrong:**
The family arrives at a BMC appointment with an AI-generated brief. The clinician (Dr. Hien) is now in the position of either agreeing, disagreeing publicly, or hedging — every option degrades the working relationship. Over time, clinicians become defensive; the AI's role shifts from *information amplifier* to *trust corroder*.

**Why it happens:**
- Survey data: parents place high emphasis on human autonomy and on clinicians' ability to refuse AI, but the same parents anchor on AI-provided info when it appears confident.
- LLM outputs sound declarative; clinicians' provisional language sounds weaker by contrast.
- The family is doing emotional labor 24/7 and naturally over-weights anything that feels like progress.

**Detection (warning signs):**
- A digest item directly addresses a clinician by name ("Dr. Hien should consider…")
- The family reports a clinician was "annoyed" or "skeptical" after seeing an AI brief
- The AI brief format mirrors a clinical note (headers like "Plan," "Assessment") — it looks like it's speaking *as* a clinician

**Prevention (concrete):**
1. **AI briefs are formatted as "questions from the family to the clinician,"** never as "recommendations from the AI to the clinician." Fixed header: "Questions Aleksandra's family would like to discuss."
2. **Three-way artifact**: the Notion page shared with clinicians includes (a) the question, (b) the source(s), (c) an explicit blank for the clinician's response. The clinician's note becomes the durable record, not the AI's.
3. **No clinician name in agent prompts.** The Communicator must not generate "Dr. Hien"-targeted phrasing. Names are added only at the family's manual edit time.
4. **Opt-in for clinician-visible artifacts.** Default = family-only. The family must consciously decide to share a brief with the care team for each instance.
5. **Plain-language guarantee.** No use of clinical-note structure (SOAP, A/P) in family-facing or clinician-shared documents.

**Phase to address:** Action phase (artifact templates) and Cognition phase (Communicator prompt).

---

### Pitfall 13: Cost runaway from agent infinite-loops or autonomous re-runs

**Severity:** HIGH (project-survival — family-funded, $20–30 MVP ceiling)
**Category:** Engineering / operational

**What goes wrong:**
Hypothesis agent enters an iteration loop trying to satisfy an unsatisfiable constraint. CrewAI does not enforce `max_iterations` by default in all task configurations. Overnight, Claude API spend hits $80. The family-funded ceiling is blown — the project may have to shut down.

**Why it happens:**
- CrewAI default `max_iter` per agent is high (25) and per-task budgets are not enforced unless configured.
- The cron firing every 6h means a runaway in one cycle can compound across 4 cycles before anyone notices.
- DSPy optimization runs (especially `BootstrapFewShotWithRandomSearch`) can themselves spend hundreds of dollars if uncapped.

**Detection (warning signs):**
- Hourly Anthropic API spend > $1
- Any single CrewAI task's iteration count > 7
- n8n workflow execution count for a single cron entry > 1 (re-trigger storms)

**Prevention (concrete):**
1. **Per-agent `max_iter=7`** (community-validated guardrail) and per-task `max_execution_time=30s`.
2. **Token budget per run.** Hard cap in CrewAI: `crew.run(max_tokens_per_run=80_000)`. Exceeds → abort, log, alert.
3. **n8n workflow has a daily Claude-spend node**: queries Anthropic usage API, kills downstream nodes if `today_spend > $1.50` (gives ~$45/mo ceiling with buffer).
4. **Kill-switch MCP.** A dedicated `panic-stop` MCP (Telegram command: `/stop`) immediately disables all cron + agent invocations until manually re-enabled.
5. **DSPy runs are gated** behind a manual `make optimize` target — never auto-fired.

**Phase to address:** Cognition phase (CrewAI config) + Foundation phase (n8n cost-gate).

---

### Pitfall 14: Knowledge-graph schema rot (ontology drifts, queries break)

**Severity:** MEDIUM
**Category:** Engineering

**What goes wrong:**
Six months in, the team has added entity types ad-hoc: `Drug`, `Compound`, `Medication`, `Therapeutic` — all referring to the same concept. Relationships drift: `TREATS`, `USED_FOR`, `INDICATED_FOR`. Queries that worked in month 1 silently return empty results in month 6 because they used the old labels. LightRAG joins degrade. The system "still runs" but its accuracy decays invisibly.

**Why it happens:**
- Graphiti supports both prescribed and learned ontology — without governance, the learned side eats the prescribed side.
- Multiple agents writing entities under slightly-different prompts → near-duplicates.
- Neo4j does not enforce a schema; you need to build versioning yourself.

**Detection (warning signs):**
- `MATCH (n) RETURN DISTINCT labels(n)` returns > 30 entity types
- `MATCH ()-[r]->() RETURN DISTINCT type(r)` returns near-synonym relationships
- A canonical retrieval query's result count drops > 20% month-over-month with no upstream change in corpus

**Prevention (concrete):**
1. **Prescribed ontology, frozen at v1.** A short YAML (`graph_ontology.yaml`) lists allowed entity types and relationships. Graphiti's writer validates against it.
2. **Migration policy.** Adding a type requires a migration script + a query re-validation suite.
3. **Weekly schema health dashboard**: counts of types, edges, orphan nodes, near-duplicate labels (Levenshtein < 3).
4. **Entity-resolution pass.** Nightly job that merges near-duplicate entities (Drug/Medication/Compound) using fastembed similarity + a verification LLM call.

**Phase to address:** Memory phase, then ongoing.

---

## Technical Debt Patterns

| Shortcut | Immediate benefit | Long-term cost | When acceptable |
|----------|-------------------|----------------|-----------------|
| Skip citation tuple, store free-text claims | Faster Spider implementation | Fabricated citations reach family → trust collapse | **Never** |
| Use the same Claude API key for all 5 agents | One env var | Cannot isolate which agent is over-spending | Only in week 1 prototype; split before first cron |
| Eager-load all 52 MCP tool descriptors | Easier wiring | Context pollution, slower agents, higher cost | Only in local dev; production must be per-agent allowlist |
| Skip the verifier agent — "the Analyzer is careful enough" | Saves one agent call | Pitfall 1 (fabricated citations) | **Never** for user-facing output |
| Share mem0 namespace across all agents | Less plumbing | Pitfall 2 (shared-memory poisoning) | Only in pre-Memory-phase prototypes |
| Cron-only ingestion, no event-driven backfill | Simpler n8n flow | Misses urgent ClinicalTrials.gov updates | Acceptable in MVP; revisit at first missed update |
| Ship the viewer without CSP | Faster iteration | Pitfall 11 (MRI leak) | **Never** in any code that loads Aleksandra's actual MRI |
| Persist Telegram bot token in repo | Faster onboarding | Credential leak | **Never** |
| Skip negative-mode scraping | Cleaner-looking digests | Pitfall 6 (negative-evidence blindness) | **Never** past MVP |
| Use Crawl4AI to hit PubMed index pages | Avoid API key step | Pitfall 7 (IP block, ToS violation) | **Never** — use E-utilities |

---

## Integration Gotchas

| Integration | Common mistake | Correct approach |
|---|---|---|
| PubMed | Scrape the search results page | Use NCBI E-utilities with an `api_key` and `tool=` + `email=` parameters |
| ClinicalTrials.gov | Scrape `https://clinicaltrials.gov/study/NCT...` | Use the v2 API — the site serves bootstrap JS, screen-scraping returns empty content |
| Notion | Treat as HIPAA-compliant by default | Notion BAA requires Enterprise plan; for non-covered-entity family use, document the choice and avoid storing identifiable PHI beyond what the family already shares personally |
| Telegram | Treat as a secure channel | Telegram has no BAA, default chats are not end-to-end encrypted; OK as a *family* channel because family-to-family communication is outside HIPAA scope, but never use it to convey clinician-originated PHI |
| Graphiti | Use with non-OpenAI/Gemini LLM | Graphiti needs Structured Output support — Claude Sonnet 4 supports tool-call JSON modes; pin to a model+version that round-trips schemas reliably |
| mem0 | Share one global memory across all 5 agents | Scope every memory op by `agent_id`; cross-agent comms go through CrewAI tasks |
| Neo4j AuraDB free tier | Build production schema on it | Free tier has hard size limits (200K nodes, 400K relationships) — Aleksandra's literature graph will hit this within 6–12 months. Plan a migration path. |
| Qdrant Docker | One collection, mixed embedding versions | Stamp every point with `embedding_model_version`; full re-embed on model bump |
| Vercel | Server-side render anything involving Aleksandra's MRI | Viewer routes must be `'use client'` only; no server components touch volume bytes |
| CrewAI | Skip `max_iter` and `max_execution_time` | Set both per-agent and per-task; add token budget at the crew level |
| FastMCP custom MCPs | Run unauthenticated on Railway public port | Bind to localhost or use Railway private networking; auth header on every tool call |
| Crawl4AI | Default user-agent | Set a project-identifying UA with a contact email (NCBI explicitly expects this) |

---

## Performance Traps

| Trap | Symptoms | Prevention | When it breaks |
|---|---|---|---|
| Full-corpus re-embed on every model bump | Hours-long cron, Qdrant downtime | Background re-embed + dual-write to a "v_next" collection, swap on completion | First fastembed model upgrade |
| Graphiti queries without indexes on `Source.url` / `Claim.text_hash` | Sub-second queries become 30s+ | Index every field used in MATCH constraints | ~10K nodes |
| NiiVue rendering full-res 3D volume on a mobile browser | Tab crashes / OOM | Down-sample on load, progressive enhancement, detect low-mem devices | First time the family opens the viewer on phone |
| LightRAG joins without LIMIT | Memory blow-up | Always `LIMIT 50` on graph traversals before vector rerank | ~5K papers in corpus |
| 5 CrewAI agents all calling Claude in parallel without rate-limit awareness | 429s, partial failures | Sequential or rate-limited crew, retry-after honored | First "research storm" day |
| Storing full paper text in Supabase | DB bloat, slow queries | Store full text in CF R2; Supabase keeps metadata + R2 key | ~1K papers |
| Notion API rate limit (3 req/s) hit by Communicator | Digest publish fails | Batch + backoff; use Notion only for human-readable summary, not for raw data | First week of daily digests |
| Telegram message size limit (4096 chars) | Truncated digests | Split + thread; rich content goes to Notion link | First long digest |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---|---|---|
| Hardcoding Anthropic / Firecrawl / Telegram tokens in n8n workflow JSONs | Credential leak via repo + workflow exports | n8n credentials store + CF secrets; pre-commit scan for token patterns |
| Allowing arbitrary URLs into Crawl4AI / Firecrawl from agent decisions | SSRF via prompt injection — agent fetches `http://169.254.169.254/...` (cloud metadata) | URL allowlist (PubMed, ClinicalTrials.gov, known publishers); block private IP ranges + cloud metadata IPs |
| MCP that wraps shell commands with agent-controlled args | Remote code execution via prompt injection | Never expose `bash` / `subprocess` as an MCP tool surface; whitelist commands |
| Patient MRI in browser dev tools console | PHI leak via screenshot / screen-share | Strip console logs in production build; disable source maps |
| Notion page shared "to web" with patient identifiers | Public PHI exposure | Audit on every page; default share = workspace-only |
| Supabase row-level-security off | Anyone with the anon key reads all data | Enable RLS; service role key never in client code |
| Claude Sonnet 4 API key with no `key_name` scope | Hard to detect runaway agent identity | One key per agent (`spider-key`, `analyzer-key`, etc.) — narrows blast radius |
| Telegram bot token in plain Notion page (common during setup) | Token leak via shared workspace | Tokens never in Notion; always in vault |
| Logging full prompts/responses to a third-party observability SaaS | PHI may end up in their logs | Strip PHI markers before logging; or self-host (e.g., Langfuse Docker) |
| The same `OPENAI_API_KEY` used for Graphiti structured-output | Per-call cost not attributable | Tag every call with `metadata={agent, task, run_id}` |

---

## UX Pitfalls

| Pitfall | User impact | Better approach |
|---|---|---|
| Uniform-toned digests | "Important" and "trivial" feel identical → fatigue (Pitfall 10) | Three urgency tiers with different rendering |
| Headline-only summaries | Family clicks through to find no source → trust drop | Every headline links to a verified citation tuple |
| Action-oriented imperatives | Family acts before clinician sees (Pitfall 3) | Question-format, "ask Dr. X about Y" |
| Prognostic language | Family despair, violates project constitution (Pitfall 4) | Tone lexicon enforced by post-processor |
| "Confidence: 0.87" with no explanation | Number theater — false precision | Confidence as a band {low/medium/high} + one-line rationale |
| Source link to paywalled paper without warning | Family hits paywall, can't verify | Mark paywalled vs. open; route open versions / preprints when available |
| Mobile-unfriendly Notion pages | Family on phone in clinical waiting room can't read brief | Test every artifact at 375px width before ship |
| English-only digests | Family is bilingual GE/EN — context loss | Bilingual mode for high-urgency digests (Georgian + English side-by-side) |
| Time-zone confusion (Tbilisi / Boston) | "Tomorrow 9am" ambiguous | Always include both TZs for any deadline-bearing message |
| MRI viewer requires "drag and drop nifti file" with no guidance | Family unable to use the viewer they paid for | Onboarding flow with a synthetic sample volume preloaded |

---

## "Looks Done But Isn't" Checklist

- [ ] **Citation verifier**: feed the verifier a deliberately-fabricated DOI in a test — does it correctly reject? If not, it's not done.
- [ ] **Negative-mode scraping**: corpus has ≥ 25% of papers tagged with neutral/negative outcomes — if 100% are positive, it's not done.
- [ ] **Tone lexicon**: feed the Communicator a paper with "poor prognosis" wording in its abstract — does the digest filter it? If the phrase appears in plain Communicator voice, it's not done.
- [ ] **CSP on viewer**: open browser network tab while loading a volume — any outbound bytes carrying voxel data? If yes, it's not done.
- [ ] **Per-agent MCP scoping**: pass Spider a Telegram tool call — does it execute or get rejected? Must be rejected.
- [ ] **Budget kill-switch**: simulate $50 of spend in an hour — does the n8n gate fire? If not, it's not done.
- [ ] **Idempotent ingestion**: run the same scrape twice — do node counts double in Graphiti? Must not.
- [ ] **Embedding version stamp**: query Qdrant — does every point have `embedding_model_version`? Missing values = not done.
- [ ] **MRI volume never POSTed**: viewer integration test asserts zero outbound `multipart/form-data` carrying the volume.
- [ ] **Clinician boundary**: does any agent prompt mention "Dr. Hien" / "Dr. August" / "Dr. Maypole" by name? If yes, scrub.
- [ ] **Source provenance for every claim** in the last 50 digests: `null source_id` count = 0.
- [ ] **Population-gap field** is populated for every drug/intervention mention; the absence = not done.
- [ ] **`max_iter` / `max_tokens_per_run`** is set on every CrewAI task — not just the crew default.
- [ ] **Bilingual support** verified by a native Georgian speaker on at least one urgent-tier digest.
- [ ] **Quiet hours**: simulate a cron at 03:00 Boston — `notable` is suppressed, `urgent` passes.

---

## Recovery Strategies

| Pitfall | Recovery cost | Recovery steps |
|---|---|---|
| Fabricated citation reached family | HIGH | (1) Immediate retraction message via Telegram (same channel as the original). (2) Document incident in Notion with full provenance trail. (3) Communicator output schema audit — find the validation gap. (4) Re-run last 30 days of digests against the (now-improved) verifier — proactively retract anything else that fails. |
| Shared-memory poisoning detected | MEDIUM | (1) Identify the poison fact via Graphiti audit (which `Source` node, when, which agent). (2) Cypher delete the fact and all derived facts (`MATCH (n)-[:DERIVED_FROM*]->(:Source {id:'X'}) DETACH DELETE n`). (3) Replay affected cron windows with the corrected schema. |
| Off-label suggestion sent | HIGH | (1) Immediate clarifying Telegram message: "the previous message was an information lead, not a recommendation — please disregard until Dr. X reviews." (2) Notify the relevant clinician proactively. (3) Communicator prompt revision + new lint rule + regression test. |
| MRI accidentally POSTed | CATASTROPHIC | (1) Pull the network logs — confirm scope. (2) Contact the receiving service (Vercel, etc.) for log purge — get a written confirmation. (3) Rotate any credentials that may have been in the same request. (4) Family notified. (5) Code freeze on `/viewer/`; CSP + pre-commit hook added before any new viewer commit. |
| Scraper IP-blocked | MEDIUM | (1) Confirm via direct curl from a different IP. (2) Add NCBI API key if not already. (3) Lower rate to 1 req/s, add jitter. (4) Reach out to NCBI helpdesk if 24h+ ban (they unban legitimate research with a polite email). (5) Switch to Firecrawl fallback gated by spend cap. |
| Vector/graph desync detected | MEDIUM | (1) Reconciler job identifies mismatches. (2) Re-embed the affected `Source` nodes using the current embedding version. (3) Backfill `qdrant_point_ids[]` on Graphiti side. (4) Add the reconciler to the daily cron. |
| Cost runaway | HIGH | (1) `panic-stop` MCP via Telegram. (2) Anthropic usage dashboard → identify the spending agent. (3) Add `max_iter` to that agent specifically. (4) Postmortem note in `docs/incidents/`. |
| Notification fatigue (open-rate < 50%) | MEDIUM | (1) Switch all `routine` to email-only. (2) Reduce digest frequency from every-cron to daily 8am Gmail. (3) Re-tier the past month — find what should have been `urgent` but wasn't. |
| Schema rot detected | MEDIUM | (1) Run entity-resolution merge pass (fastembed + LLM). (2) Migrate near-duplicate relationship types. (3) Lock the ontology with a JSON-schema validator on the Graphiti writer. |

---

## Pitfall → Phase Mapping

The roadmap should sequence phases so each pitfall is addressed *before* the capability that would expose it.

| # | Pitfall | Severity | Prevention phase | Verification at phase exit |
|---|---|---|---|---|
| 1 | Fabricated citations | CATASTROPHIC | Memory (schema) + Cognition (verifier) | Verifier rejects ≥ 99% of synthetic fabrications in a test set of 100 |
| 2 | Shared-memory poisoning | HIGH | Memory (write contract) | Provenance traversal test passes; no agent writes without `derived_from_source_ids` |
| 3 | Off-label recommendations | CATASTROPHIC | Cognition (Communicator prompt) + Action (lint) | Imperative-verb lint count = 0 across 30 sample digests |
| 4 | "Limited outcomes" framing | HIGH | Cognition (tone lexicon) | Denied-phrase count = 0; quarterly tone audit passed |
| 5 | Recency bias | HIGH | Memory (schema) + Cognition (scorer) | Top-3 digest items in last 30d contain ≥ 1 systematic review when one exists |
| 6 | Negative-evidence blindness | HIGH | Perception (dual-mode scrape) + Cognition (falsifier) | Corpus ≥ 15% negative-tagged; every digest has counter-evidence section |
| 7 | Scraper IP-blocking | HIGH | Perception (APIs + rate limits) | 429/403 rate < 0.1% over 7 days; NCBI API key configured |
| 8 | Vector/graph desync | HIGH | Memory (single writer + versioning) | Reconciler reports bijection; ingestion is idempotent on re-run |
| 9 | MCP server sprawl | MEDIUM–HIGH | Foundation (governance) | Inventory exists; per-agent allowlist enforced; system-prompt tokens < 8K |
| 10 | Notification fatigue | HIGH | Action (urgency tiers) | Open-rate ≥ 80% on `urgent`; tiering test passes |
| 11 | MRI leaving the browser | CATASTROPHIC | Visualization (CSP + local-only) | Network-tab review shows zero outbound voxel bytes; CSP header verified |
| 12 | Family/clinician boundary erosion | HIGH | Cognition (prompt) + Action (artifact templates) | No clinician name in agent output; question-format briefs |
| 13 | Cost runaway | HIGH | Foundation (budget gate) + Cognition (max_iter) | Simulated runaway is killed within 60s; daily spend cap fires |
| 14 | KG schema rot | MEDIUM | Memory (ontology yaml) | Distinct label count ≤ 20; weekly schema health dashboard green |

**Recommended phase ordering** (derived from prevention dependencies):

1. **Foundation** — governance (MCP inventory, budget gates, kill-switch, repo hygiene). Pitfalls 9, 13.
2. **Perception** — APIs (not scrapers) first, negative-mode second, Firecrawl/Browser Use last. Pitfalls 6, 7.
3. **Memory** — citation tuple schema, single-writer ingestion, ontology lock, embedding versioning. Pitfalls 1 (schema half), 2, 5, 8, 14.
4. **Cognition** — verifier agent FIRST, then Spider/Analyzer/Hypothesis/Repurposing, Communicator LAST with the tone lexicon and imperative lint. Pitfalls 1 (verifier half), 3, 4, 6 (falsifier), 12, 13 (max_iter).
5. **Visualization** — viewer with CSP and local-only loading; cloud pipeline only on synthetic data. Pitfall 11.
6. **Action** — Telegram tiering, Notion artifacts, Gmail digest, calendar. Pitfalls 3 (lint half), 10, 12 (artifact half).

Each phase exit must verify its mapped pitfalls before the next phase begins. This is the structural defense.

---

## Sources

**Medical-evidence pitfalls (Pitfalls 1, 3, 5, 6):**
- [One in 277 PubMed-indexed papers in 2026 shows fabricated references — Retraction Watch (2026-05-07)](https://retractionwatch.com/2026/05/07/one-in-277-pubmed-indexed-papers-in-2026-shows-fabricated-references-says-analysis/)
- [Influence of Topic Familiarity and Prompt Specificity on Citation Fabrication in Mental Health Research Using LLMs — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12658395/)
- [Reference Hallucination Score for Medical AI Chatbots — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11325115/)
- [LLM hallucinations in the wild: Large-scale evidence from non-existent citations — arXiv 2605.07723](https://arxiv.org/abs/2605.07723)
- [Fabricated Citations in Medical Research: What the Lancet Audit Means for Authors](https://www.journalmetrics.org/blog/ai-fabricated-citations-medical-research-2026)
- [Comparison of preprints and their corresponding peer-reviewed publications in the health field — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12829155/)
- [Incorporating Preprints in Systematic Reviews — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12338926/)
- [Robustness of evidence reported in preprints during peer review — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9553196/)
- [Publication bias — Importance of studies with negative results! — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6573059/)
- [When AI Rewrites the Label: The Prescribing Risk Pharma Can't Afford to Ignore](https://drugchatter.com/insights/2026/05/12/when-ai-rewrites-the-label-the-prescribing-risk-pharma-cant-afford-to-ignore/)
- [Artificial intelligence in drug repurposing for rare diseases: a mini-review — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11150798/)
- [AI in Systematic Reviews: Overcoming Reproducibility, Bias and Validation Challenges](https://www.preprints.org/manuscript/202506.1895)

**Multi-agent / memory pitfalls (Pitfalls 2, 13):**
- [Why Do Multi-Agent LLM Systems Fail? — arXiv 2503.13657](https://arxiv.org/pdf/2503.13657)
- [LLM-based Agents Suffer from Hallucinations: A Survey — arXiv 2509.18970](https://arxiv.org/html/2509.18970v1)
- [Multi-Agent AI Systems: Why They Fail and How to Fix Coordination Issues — Augment Code](https://www.augmentcode.com/guides/why-multi-agent-llm-systems-fail-and-how-to-fix-them)
- [What Happens When One Agent in a Multi-Agent Pipeline Gets It Wrong? — Pithy Cyborg](https://www.pithycyborg.com/what-happens-when-one-agent-in-a-multi-agent-pipeline-gets-it-wrong/)
- [AI Memory Security: Best Practices and Implementation — Mem0](https://mem0.ai/blog/ai-memory-security-best-practices)
- [A Survey on the Security of Long-Term Memory in LLM Agents — arXiv 2604.16548](https://arxiv.org/html/2604.16548)
- [How to Stop AI Agent Cost Blowups Before They Happen — DEV](https://dev.to/sapph1re/how-to-stop-ai-agent-cost-blowups-before-they-happen-1ehp)
- [AI Agent Token Budget Management — MindStudio](https://www.mindstudio.ai/blog/ai-agent-token-budget-management-claude-code)

**Knowledge-graph and vector/graph pitfalls (Pitfalls 5, 8, 14):**
- [Knowledge Drift — The Silent AI Killer in RAG models — Medium](https://medium.com/@leeladesai/knowledge-drift-the-silent-ai-killer-in-rag-models-034eb35c7af4)
- [Detecting Embedding Drift: The Silent Killer of RAG Accuracy](https://decompressed.io/learn/embedding-drift)
- [Embedding Staleness Is Probably Corrupting Your RAG System Right Now — HackerNoon](https://hackernoon.com/embedding-staleness-is-probably-corrupting-your-rag-system-right-now)
- [RAG Is a Data Engineering Problem Disguised as AI — DEV](https://dev.to/aws-builders/rag-is-a-data-engineering-problem-disguised-as-ai-39b2)
- [Graphiti — getzep/graphiti GitHub](https://github.com/getzep/graphiti)
- [Building a Temporal Infrastructure Knowledge Graph: A Year of Wrestling with Neo4j at Scale](https://medium.com/@roxane.fischer_50383/building-a-temporal-infrastructure-knowledge-graph-a-year-of-wrestling-with-neo4j-at-scale-949e989c98a2)
- [Keeping track of graph changes using temporal versioning — Neo4j Developer Blog](https://medium.com/neo4j/keeping-track-of-graph-changes-using-temporal-versioning-3b0f854536fa)

**Scraping, MCP, security pitfalls (Pitfalls 7, 9, 11):**
- [Does Screen Scraping ClinicalTrials.gov Work? — NLM Technical Bulletin Jul/Aug 2025](https://www.nlm.nih.gov/pubs/techbull/ja25/ja25_clinical_trials_screen-scraping.html)
- [AI Web Scraping for Healthcare and Medical Research](https://scrapegraphai.com/blog/scraping-healthcare)
- [Scraping the Web for Public Health Gains: Ethical Considerations from a 'Big Data' Research Project](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7392638/)
- [Scaling MCP adoption — Cloudflare](https://blog.cloudflare.com/enterprise-mcp/)
- [11 Emerging AI Security Risks with MCP — Checkmarx Zero](https://checkmarx.com/zero-post/11-emerging-ai-security-risks-with-mcp-model-context-protocol/)
- [A Look Into the Secrets of MCP: The New Secret Leak Source — GitGuardian](https://blog.gitguardian.com/a-look-into-the-secrets-of-mcp/)
- [MCP Servers Are the New Microservices Sprawl — DEV](https://dev.to/evanlausier/mcp-servers-are-the-new-microservices-sprawl-and-were-making-all-the-same-mistakes-4mmm)
- [NiiVue — niivue/niivue GitHub](https://github.com/niivue/niivue)
- [Telegram HIPAA Compliance — Accountable](https://www.accountablehq.com/post/telegram-hipaa-compliance-is-it-safe-for-healthcare-communication)
- [HIPAA configuration — Notion Help Center](https://www.notion.com/help/hipaa)

**Ethical / family-facing pitfalls (Pitfalls 3, 4, 10, 12):**
- [Ethical considerations in AI for child health and recommendations for child-centered medical AI — npj Digital Medicine](https://www.nature.com/articles/s41746-025-01541-1)
- [Ethical and Practical Considerations of AI in Pediatric Medicine: A Systematic Review — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11914856/)
- [Parents' understanding and attitudes toward the application of AI in pediatric healthcare — Frontiers](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2025.1654482/full)
- [From diagnosis to system change: what rare disease is teaching us about safety, bias and AI — Patient Safety Learning](https://www.pslhub.org/learn/patient-safety-in-health-and-care/conditions/rare-diseases/from-diagnosis-to-system-change-what-rare-disease-is-teaching-us-about-safety-bias-and-ai-r14254/)
- [Human in the loop AI in healthcare — ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1386505626001024)
- [In the Loop or On the Loop: The Conundrum of AI Clinical Decision Support — Penn LDI](https://ldi.upenn.edu/our-work/research-updates/in-the-loop-or-on-the-loop-the-conundrum-of-ai-clinical-decision-support/)
- [How to Help Users Avoid Notification Fatigue — MagicBell](https://www.magicbell.com/blog/alert-fatigue)

**Operational / cron pitfalls:**
- [Idempotent Cron Jobs are Operable Cron Jobs — Robust Perception](https://www.robustperception.io/idempotent-cron-jobs-are-operable-cron-jobs/)
- [Event-Driven Scraping vs Cron Jobs: What Actually Works at Scale — DEV](https://dev.to/promptcloud_services/event-driven-scraping-vs-cron-jobs-what-actually-works-at-scale-3h66)

---
*Pitfalls research for: ALEKSANDRA_BRAIN — family-operated agentic medical research cockpit for severe pediatric HIE*
*Researched: 2026-05-13*
