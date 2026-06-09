# Multi-Provider Tiered Model Routing — Implementation Plan

> **Status:** IN PROGRESS. Saved 2026-06-09 for cross-session continuation.
> **Branch:** `claude/status-check-1ZMxG` · **PR:** #10
> **Resume point:** Section 12 ("Where to resume").
>
> **Progress (2026-06-09):**
> - ✅ **Phase A done** — `scripts/cognition/models.py` registry + `llm.py` router
>   (`call_llm(task=...)`, OpenRouter path, MODEL_PROVIDER rollback). 10 unit tests.
> - ✅ **Phase B done (loop-critical)** — `graphiti_client.py` provider-aware
>   (DeepSeek via OpenRouter + instrumented AsyncOpenAI), `relevance.py` →
>   `task="relevance"`, `batch_ingest.py` honesty-log. 12 tests total green.
>   ⚠️ Graphiti+DeepSeek structured-extraction compatibility is UNVERIFIED here
>   (no Neo4j/graphiti in CI container) — needs the live curl in §7. Honesty-log
>   will surface a recall regression.
>   ↪️ `refactor/classify_edges.py` (worker tier) deferred — NOT in the live
>   30-min tick (manual migration utility); convert in a follow-up.
> - ⏭️ **Next:** Phase C (writer→Gemini), Phase D (thinker→Opus, gated), Phase E
>   (budget cap $5 + digest health-check + verifier sweep).

---

## 0. Context — why this exists

Two things converged into one plan:

### 0a. Live incident (2026-06-09): extraction pipeline DOWN
Telegram ticks showed `extraction-tick +9 papers · 0 episodes · ~0 entities · ⚠️ 3 errors`
repeating every 30 min for hours, plus daily digest `LLM: 1000 ცდა · $0.0000 (ბიუჯეტი 0.0%)`.

**Diagnosis (code-confirmed, not yet live-confirmed):** 100% of Anthropic API calls are
failing. Evidence chain:
- `daily_spend_report.py:85` counts ALL `runs` rows where `kind='llm_call'` and sums
  `token_cost`. A FAILED call (`llm.py:196`) records `exit_status='failed'`, `tokens=0`,
  **`cost=$0`**. So `1000 calls / $0` = **1000 failed calls** (success is never $0).
- Graphiti `add_episode` (`ingest_paper.py:162`) makes the Anthropic call for entity
  extraction → fails → `counters["errors"]++` → `batch_ingest.py:39` `MAX_ERRORS=3`
  hard-stops → 0 episodes, 0 entities. This is a safety rail working correctly.
- chunking `0 scored` = relevance scoring (also Anthropic) failing too.
- Budget is NOT the cause: budget gate raises BEFORE recording a row, so a block would
  not count as a "call". Spend $0 / 0.0% confirms cap is not hit.

**Most likely live root cause:** invalid/expired `ANTHROPIC_API_KEY` on the Railway
worker, OR Anthropic account billing/credits, OR egress block. Confirm with:
```sql
SELECT exit_reason, count(*) FROM runs
WHERE kind='llm_call' AND exit_status='failed'
  AND start_time > now() - interval '24 hours'
GROUP BY exit_reason ORDER BY 2 DESC LIMIT 10;
```

### 0b. The strategic goal (user request)
Restructure all LLM usage into 3 cost/capability tiers:
- **Repetitive technical work** (no deep reasoning) → cheap/free model
- **Reasoning** → Anthropic's newest (Opus 4.8)
- **Writing** → Google Gemini

> **Synergy:** routing the worker tier off Anthropic + putting everything behind one
> OpenRouter key makes the broken `ANTHROPIC_API_KEY` irrelevant. Phase B closes the
> outage as a side effect.

---

## 1. Locked decisions (user-approved 2026-06-09)

| Decision | Choice |
|---|---|
| Worker model | **DeepSeek-V3** (`deepseek/deepseek-chat`), near-free (~$0.27/$1.10 per 1M) |
| Access path | **OpenRouter single gateway** (one OpenAI-compatible API + one key) |
| Pre-cutover A/B quality test | **No** — switch directly; rely on free honesty-log instead |
| Thinker model | **Opus 4.8** (`anthropic/claude-opus-4-8`) — via OpenRouter |
| Writer model | **Gemini 2.5 Flash** (`google/gemini-2.5-flash`) — via OpenRouter |

**Still OPEN (ask user before/early in implementation):**
- Thinker = Opus on EVERY reasoning call, or gated behind a complexity≥N check
  (simple hypotheses → worker, hard → Opus)? Plan currently assumes gating is desirable.

---

## 2. Final model lineup

| Tier | Model (OpenRouter slug) | Price ≈/1M (in/out) | Used for |
|---|---|---|---|
| 🔧 Worker | `deepseek/deepseek-chat` | $0.27 / $1.10 | extraction · edge-classify · relevance · intake · self-review |
| 🧠 Thinker | `anthropic/claude-opus-4-8` ¹ | $15 / $75 | hypothesis · GoT · cross-disease · hard evidence |
| ✍️ Writer | `google/gemini-2.5-flash` ² | $0.30 / $2.50 | weekly brief · family/clinician · Gmail draft · en→ka translate · summarize |

¹ Confirm exact OpenRouter slug for newest Anthropic Opus at implementation time.
² Upgrade to `google/gemini-2.5-pro` via one registry edit if prose quality needs it.

---

## 3. Secrets / env (Railway + local `.env`)

| Var | Value |
|---|---|
| `OPENROUTER_API_KEY` | **NEW** — the only required key |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` (default) |
| `ANTHROPIC_API_KEY` | no longer required; kept as legacy fallback |
| `DAILY_BUDGET_USD` | raise to `5.00` (see Phase E) |
| `MODEL_PROVIDER` | rollback flag: `openrouter` (default) \| `anthropic` (legacy) |

---

## 4. New file — `scripts/cognition/models.py`

Single source of truth for the lineup (task→tier→model) + pricing.

```python
TIER_MODEL = {
    "worker":  "deepseek/deepseek-chat",
    "thinker": "anthropic/claude-opus-4-8",
    "writer":  "google/gemini-2.5-flash",
}
TASK_TIER = {
    "extraction": "worker", "edge_classify": "worker", "relevance": "worker",
    "intake_parse": "worker", "self_review": "worker",
    "got": "thinker", "repurpose": "thinker", "evidence_hard": "thinker",
    "translate": "writer", "weekly_brief": "writer",
    "family_msg": "writer", "summarize": "writer",
}
PRICING_USD_PER_M = {            # (input, output)
    "deepseek/deepseek-chat":      (0.27, 1.10),
    "google/gemini-2.5-flash":     (0.30, 2.50),
    "anthropic/claude-opus-4-8":   (15.00, 75.00),
}
FALLBACK = (15.00, 75.00)        # conservative for unknown IDs

def model_for(task: str) -> str: ...
def tier_for(task: str) -> str: ...
```

---

## 5. Phases

### Phase A — Router core  (pure code, unit-testable)
- New `scripts/cognition/models.py` (Section 4).
- Refactor `scripts/cognition/llm.py`:
  - One OpenAI-compatible client → OpenRouter base_url.
  - Keep `call_claude(...)` as back-compat alias; add `call_llm(*, task, prompt, ...)`.
    `task` resolves model via router; explicit `model=` still overrides (migrations safe).
  - Same `runs` instrumentation; OpenRouter usage → `prompt_tokens`/`completion_tokens`.
  - Generalize refusal-guard (OpenAI shape: empty `choices`/`content`) — port the
    Phase 6.1 defensive wrap from `translate.py`.
  - Extend pricing to read from `models.PRICING_USD_PER_M`.
- **Rollback flag:** `MODEL_PROVIDER=anthropic` → legacy Anthropic path.

### Phase B — Extraction cutover  (🔴 closes the outage)
- `scripts/extraction/graphiti_client.py`: `AnthropicClient` → Graphiti OpenAI-generic
  client (`base_url=OpenRouter`, `model=deepseek/deepseek-chat`), instrumented cost-hook
  on OpenAI shape. **fastembed embedder unchanged** (local 384-dim, never touched Anthropic).
- Add entity-count honesty log to `batch_ingest.run_batch` (before/after; baseline 568
  Neo4j entities). Non-blocking.
- `scripts/scoring/relevance.py` → `task="relevance"`.
- `scripts/refactor/classify_edges.py` → worker (DeepSeek via OpenRouter).

### Phase C — Writer cutover
- `scripts/extraction/translate.py` (en→ka) → `task="translate"` (Gemini).
- `scripts/communicator/bilingual.py` `compose_bilingual` → `task="weekly_brief"` (Gemini).
- `scripts/communicator/summarize.py` → `task="summarize"`.
- Re-verify Georgian output + refusal handling (Gemini has its own safety filters; the
  Phase 6.1 Sonnet refusal incident is the precedent — keep retry + reframe-prompt).

### Phase D — Thinker cutover
- `scripts/hypothesis/got_pipeline.py` → `task="got"` (Opus).
- `scripts/repurposing/extract_candidates.py` → `task="repurpose"`.
- `scripts/repurposing/pubmed_validation.py` → `task="evidence_hard"`.
- CrewAI agents (`agents/*.py`): change `llm=` string to LiteLLM provider-prefixed
  `openrouter/<model>` per tier. Map: spider→worker, analyzer→worker, hypothesis→thinker,
  repurposing→thinker, communicator→writer.
- If Opus-gating is chosen: add complexity≥N check that downgrades easy reasoning to worker.

### Phase E — Budget + verifier sweep
- `scripts/cognition/budget.py:51` `DEFAULT_DAILY_BUDGET_USD` 1.50 → 5.00.
- `workflows/daily-budget-gate.json:50` cap sync to `5.00`.
- digest health-check: in `daily_spend_report.py`, if `llm_calls > 50 AND spend == 0`,
  prefix `⚠️ ALL LLM CALLS FAILING` (this exact signature = the 2026-06-09 outage).
- Run `verify_phase2`, `verify_phase2_5`, `verify_phase3`.
- Closes pending todo `.planning/todos/pending/2026-06-02-raise-budget-cap-and-cache-pricing.md`
  (budget-cap half).

---

## 6. Full call-site rewiring map (live loop)

| File | Currently | → task | → tier |
|---|---|---|---|
| `extraction/graphiti_client.py` | Haiku (AnthropicClient) | `extraction` | 🔧 worker |
| `scoring/relevance.py:126` | call_claude sonnet | `relevance` | 🔧 worker |
| `refactor/classify_edges.py:136` | Haiku direct | `edge_classify` | 🔧 worker |
| `manager/intake/text_extractor.py:141` | call_claude | `intake_parse` | 🔧 worker |
| `observer/reviewer.py:185,213` | call_claude | `self_review` | 🔧 worker |
| `hypothesis/got_pipeline.py:220` | call_claude MODEL | `got` | 🧠 thinker |
| `repurposing/extract_candidates.py:94` | call_claude | `repurpose` | 🧠 thinker |
| `repurposing/pubmed_validation.py:138` | call_claude | `evidence_hard` | 🧠 thinker |
| `extraction/translate.py:104` | sonnet-4-6 direct | `translate` | ✍️ writer |
| `communicator/bilingual.py:169` | sonnet-4-5 direct | `weekly_brief` | ✍️ writer |
| `communicator/summarize.py:248` | call_claude | `summarize` | ✍️ writer |
| `agents/spider.py:43` | crewai `llm=` | spider | 🔧 worker |
| `agents/analyzer.py:35` | crewai | analyzer | 🔧 worker |
| `agents/hypothesis.py:38` | crewai | hypothesis | 🧠 thinker |
| `agents/repurposing.py:32` | crewai | repurposing | 🧠 thinker |
| `agents/communicator.py:100` | crewai | communicator | ✍️ writer |

> **Do NOT touch** migrations `013`–`017` (historical one-offs, hardcoded models OK).

---

## 7. Testing strategy (this container CANNOT run live)

Fresh clone: no `.env`, no deps installed. Therefore:
- **Unit (doable in-session):** `models.py` router (task→model), pricing math,
  refusal-guard — with mocks.
- **Integration (user side, after `OPENROUTER_API_KEY` set on Railway):**
  `curl -X POST $PERCEPTION_WORKER_URL/extraction-tick -d '{"limit":3}'`
  → expect `episodes>0, errors=0` + new `runs` rows with positive `token_cost`.
- **Honesty log:** entity count before/after extraction cutover (baseline 568).

---

## 8. Rollout & rollback

- One PR, 5 commits (A→E), or 5 small PRs.
- Cutover order: **A → B (outage closes) → C → D → E**.
- Rollback: set `MODEL_PROVIDER=anthropic` (one env var) → legacy Anthropic path returns.
- The `kv_state.graphiti_processed` guard means failed extractions auto-retry; no manual
  cleanup needed when switching providers.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| 🩺 DeepSeek extraction recall < Haiku (medical core) | honesty-log (A/B declined); `MODEL_PROVIDER` rollback |
| ✍️ Gemini Georgian medical refusal | refusal-guard + retry + reframe prompt (Phase 6.1 precedent); fallback `gemini-2.5-pro` |
| 🔌 OpenRouter rate-limit / geo | use DeepSeek PAID tier (not free pool) for stability |
| 💸 Opus cost spike | thinker = low volume; budget gate $5; optional complexity-gating |

---

## 10. Cost / effort

- **Effort:** A ~½d · B ~½d · C ~½d · D ~¼d · E ~¼d → **~2 days** of code.
- **Projected monthly spend after:** worker+writer ≈ $1–3/mo; Opus reasoning (gated) ≈
  $2–5/mo → **likely < $10/mo**, comfortably under MVP ceiling.

---

## 11. CLAUDE.md compliance notes

- Code English; comments English; commits conventional (`feat:`/`fix:`/`refactor:`).
- Implementation must go through a GSD workflow command (CLAUDE.md GSD enforcement).
- MRI/PHI constraint untouched — none of these tiers touch patient imaging (client-side only).
- "Do not fabricate" principle: provenance/`runs` ledger preserved through the refactor.

---

## 12. Where to resume (next session)

1. Read this file end-to-end.
2. (Optional but recommended) confirm the live outage root cause via the SQL in §0a, and
   resolve the OPEN question in §1 (Opus always vs gated).
3. Kick off **Phase A** then **Phase B** through a GSD command (`/gsd-execute-phase`).
   Phase B closing also resolves the extraction outage.
4. User action required for live verification: set `OPENROUTER_API_KEY` (+ optional
   `DAILY_BUDGET_USD=5.00`) on the Railway worker, then run the integration curl in §7.
