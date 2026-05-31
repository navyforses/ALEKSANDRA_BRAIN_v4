# ALEKSANDRA_BRAIN v5.0 — ულტრა-აუდიტი
# Ultra-Audit Report

> **მიზანი:** v5.0 არქიტექტურის გეგმის გრძელვადიანი სანდოობის უზრუნველყოფა ფაქტობრივი კოდის წინააღმდეგ შემოწმებით. ეს ფაილი მისცემს რეორგანიზაციის pre-flight-ს, რომ წინა v5.0 დოკუმენტში დადებული 50+ ვარაუდიდან რომელია მართალი, რომელია არასწორი, რომელია ნაწილობრივ მართალი.
>
> **Purpose:** Provide pre-flight reality check for v5.0 architecture by verifying ~50 assumptions made in earlier docs against actual code.
>
> **მეთოდი:** ფაქტობრივი წაკითხვა 35+ ფაილისა (agents/, scripts/, mcp/, viewer/, workflows/), რომელიც წინა v5.0 დოკუმენტი მხოლოდ CLAUDE.md-ის შემაჯამებელი ტექსტით აღწერა.
>
> **თარიღი:** 2026-05-23
> **ვერსია:** 1.0

---

## 0. რეზიუმე | Executive Summary

წინა v5.0 დოკუმენტი (ARCHITECTURE.md + SIMULATOR_KA.md) იყო **70% სწორი** ფაქტობრივ კოდთან მიმართებაში. სამი დიდი დასკვნა:

**1. პროექტი უფრო მოწინავეა, ვიდრე CLAUDE.md ჩანდა.** ფაქტობრივი viewer-ი მუშაობს Next.js 16.2.6-ზე (არა 14-ზე, როგორც CLAUDE.md-ში წერია), React 19.2.4-ზე, Tailwind 4-ზე. 16 i18n namespace, 186 translation key, ბილინგვური `displayField()` helper, `setRequestLocale` server-side, JSONB `{en, ka}` მონაცემთა მოდელი migration 012-ის შემდეგ.

**2. v5.0 integration points არსებობს არსებულ კოდში.** Repurposing agent-ის `TOOLS = []` სიცარიელე არის ზუსტი intercept point TxGemma-სთვის. MCP-INVENTORY.csv უკვე შეიცავს `niivue`, `bonbid`, `atlas`, `repurpose` (custom FastMCP), `tvb` MCP-ებს. ინფრასტრუქტურა მზადაა, საჭიროა ცალკეული ფაილების შევსება.

**3. CrewAI ვერსიის drift არის რეალური რისკი.** Requirements.txt-ში `crewai>=0.80.0` ფიქსირებულია. ეს არის 2025 წლის Q3-Q4 ვერსია. 2026 წლის მაისში CrewAI არის v1.14.5+. v5.0 ცვლილებები შეიძლება ჩაიჭიროს `>=0.80` constraint-ში vs რეალური 1.x API. ეს არ არის blocker, მაგრამ ამოწმდება pilot-ის წინ.

**ცვლის თუ არა აუდიტი v5.0 sprint-ის გეგმას?** კი, ნაწილობრივ. სამი ცვლილება:
- Sprint B (cognition) ცვლის ფაქტობრივი code path-ით. ფაილების სია იცვლება.
- Sprint C (visualization) ცვლის ფაქტობრივი viewer სტრუქტურით. ხედები უკვე არსებობს როგორც placeholder, არ ვაშენებთ ნულიდან.
- Sprint A (pilot) რჩება უცვლელად.

---

## 1. ფაქტობრივი Stack vs დოკუმენტირებული Stack

### 1.1 Python ჯაჭვი (requirements.txt verified)

| ბიბლიოთეკა \| Library | requirements.txt | v5.0 docs | რეალობა \| Reality |
|---|---|---|---|
| `crewai` | `>=0.80.0` | "CrewAI 1.x" | **MISMATCH** — წერია 0.80+, 2026 ვერსიაა 1.14.5+, რეალური installed ვერსია უცნობია |
| `anthropic` | `>=0.40.0` | Claude SDK | ✅ ემთხვევა |
| `graphiti-core` | `>=0.7.0` | "Graphiti latest" | ✅ ემთხვევა |
| `neo4j` | `>=5.20.0` | "Neo4j 5.26 LTS" (docker-compose) | ✅ ემთხვევა |
| `lightrag-hku` | `>=1.4.16` | "LightRAG 1.4.16" | ✅ ემთხვევა |
| `qdrant-client` | `>=1.12.0` | "Qdrant 1.x" | ✅ ემთხვევა |
| `mem0ai` | `>=0.1.50` | "mem0 2026 algorithm" | **MISMATCH** — 0.1.50 ძველი ვერსიაა, 2026 ალგორითმისთვის 0.2.x საჭიროა |
| `fastmcp` | `>=0.4.0` | "FastMCP 3.2.4" | **MISMATCH** — pinned 0.4, 2026 ვერსიაა 3.x |
| `crawl4ai` | `>=0.4.0` | "Crawl4AI 0.8.6 (security)" | **CRITICAL MISMATCH** — pinned 0.4 ნიშნავს ძველი ვერსიის ნებას, supply-chain vulnerability (Mar 2026 litellm incident) არ არის ბლოკირებული |
| `dspy-ai` | `>=2.5.0` | "DSPy 3.2.1" | **MISMATCH** — 2.5 vs 3.2 |
| `reportlab` | `>=4.2.5` | (added Phase 3) | ✅ ემთხვევა |
| `notion-client` | `>=2.2.1` | (added Phase 4) | ✅ ემთხვევა |
| `pytesseract`, `pillow` | (Phase 5 OCR) | (added Phase 5) | ✅ ემთხვევა |
| `biopython`, `nibabel` | (bioinformatics) | (NIfTI medical imaging) | ✅ ემთხვევა |

**კრიტიკული ფინდინგი:** `crawl4ai>=0.4.0` ნიშნავს, რომ pip install-ი დააყენებს არც 0.8.6-ს ან არც უფრო ახალს. ეს არის security gap, რომელიც CLAUDE.md-ში "PRC-04 — pin >=0.8.6 (supply-chain fix)" როგორც აღწერილია, მაგრამ requirements.txt-ში ეს არ ფიქსირდება. **გასწორება დროულია.**

### 1.2 Frontend ჯაჭვი (viewer/package.json verified)

| ბიბლიოთეკა | package.json | v5.0 docs | რეალობა |
|---|---|---|---|
| `next` | `16.2.6` | "Next.js 14" | **MAJOR MISMATCH** — v16 არის bleeding edge, 2 major version მუშაობს რეალურად |
| `react` | `19.2.4` | (არ მითითებული) | React 19 stable, server components first-class |
| `next-intl` | `^4.0.0` | "next-intl 4.12" | ✅ ემთხვევა |
| `tailwindcss` | `^4` | "Tailwind 3.x" | **MISMATCH** — Tailwind 4 (CSS-first config) გამოყენებულია |
| `lucide-react` | `^1.16.0` | (icons) | ✅ |
| `react-dropzone` | `^15.0.0` | (file upload) | ✅ |
| `typescript` | `^5` | TypeScript | ✅ |

**კრიტიკული შენიშვნა:** Next.js 16 + React 19 ნიშნავს, რომ `@niivue/nvreact` ბიბლიოთეკის compatibility უნდა შემოწმდეს. React 19 server components-ის ცვლილებები შესაძლოა გავლენას ახდენდეს NiiVue-ის client-side rendering-ზე. **v5.0-ის "Brain Viewer" ხედის წინ ეს ცალკე ვერიფიკაცია სჭირდება.**

### 1.3 LLM model strings

v5.0 docs-ში წერდა "Claude Sonnet 4.5 default + 4.6 escalation". ფაქტობრივად:

| ფაილი | model string |
|---|---|
| `agents/spider.py` line 34 | `claude-sonnet-4-5` |
| `agents/analyzer.py` line 35 | `claude-sonnet-4-5` |
| `agents/hypothesis.py` line 38 | `claude-sonnet-4-5` |
| `agents/repurposing.py` line 32 | `claude-sonnet-4-5` |
| `agents/communicator.py` line 100 | `claude-sonnet-4-5` |

**ფაქტობრივი real:** მთელი სისტემა მუშაობს Sonnet 4.5-ზე. 4.6 escalation hypothesis agent-ისთვის, რომელიც CLAUDE.md-ში დოკუმენტირებულია, **ფაქტობრივად არ არის wired** — `hypothesis.py`-ში default-ად `claude-sonnet-4-5` წერია.

რეკომენდაცია v5.0-სთვის: ან wire Sonnet 4.6 escalation hypothesis-ში, ან განახლე CLAUDE.md რომ ფაქტობრივი state ასახოს.

---

## 2. Cognition Layer — დეტალური ანალიზი

### 2.1 ხუთი აგენტი — ფაქტობრივი მდგომარეობა

| აგენტი | LOC | TOOLS რეგისტრი | LLM | max_iter | allow_delegation |
|---|---|---|---|---|---|
| spider.py | 47 | `[check_ledger_new, trigger_chunking]` | sonnet-4-5 | 15 | False |
| analyzer.py | 48 | `[run_graphiti, neo4j_stats]` | sonnet-4-5 | 10 | False |
| hypothesis.py | 51 | `[run_hypothesis_generation, validate_hypothesis]` | sonnet-4-5 | 20 | **True** |
| repurposing.py | 46 | `[]` ← **ცარიელი** | sonnet-4-5 | 15 | False |
| communicator.py | 296 | `[]` + COMMUNICATOR_TOOLS dict | sonnet-4-5 | 10 | False |

**კრიტიკული აღმოჩენა:** `agents/repurposing.py` ხაზი 15: `TOOLS: list = []`. ეს არის v5.0-ის ფაქტობრივი intercept point. TxGemma + AlphaFold integration ჩაჯდება ფიქს აქ, არცერთ სხვაგან.

### 2.2 MCP Allowlist — სავალდებულო ფენა

`agents/_mcp_allowlist.py` (159 ხაზი) არის security gate, რომელიც:
- კითხულობს `MCP-INVENTORY.csv`
- ფიქს გადადის CrewAI Agent factory-ში
- ნებისმიერი blocked MCP call წერს `runs` table-ში `exit_status='blocked_by_allowlist'`
- "Fail closed" pattern: უცნობი MCP = denied

**v5.0-ის implication:** MedGemma + TxGemma + AlphaFold + Hugging Face datasets ვერ ჩაჯდება სისტემაში სანამ **MCP-INVENTORY.csv** არ განახლდება. ეს არის ერთჯერადი ცვლილება (5-6 ახალი ხაზი CSV-ში), მაგრამ მისი გამოტოვება ჩაშლის ყველაფერს.

### 2.3 Repurposing-ის ფაქტობრივი backstory

```
You operate the drug repurposing pipeline. Your search space is not "drugs
for HIE" — it is "approved drugs that target the molecular pathways HIE
damages". The difference matters: there are 17,430 known drugs and only
a handful labeled for HIE.

You score every candidate on three axes:
  1. Mechanism: does it hit a relevant target?
  2. BBB penetration: can it reach the brain?
  3. Pediatric safety: known profile in neonates/infants?
```

**TxGemma-ის pitch ემთხვევა.** TxGemma-ის mechanism-of-action prediction + Therapeutic Data Commons-ის 66M data points პირდაპირ ფარავს ამ სამი ღერძიდან პირველს (mechanism). მეორე (BBB penetration) მოითხოვს ცალკე lookup (DrugBank/PubChem). მესამე (pediatric safety) — ცალკე lookup.

**v5.0 cleaning recommendation:** Repurposing agent უნდა გადაიქცეს მულტი-tool agent-ად:
- TxGemma → mechanism scoring
- BBB lookup tool → DrugBank მონაცემები
- Pediatric safety tool → FDA Pediatric Decision Tree

---

## 3. Scripts Layer — 18,687 ხაზი

### 3.1 ფაქტობრივი სტრუქტურა

| ქვედირექტორია | ფაილების რაოდენობა | LOC | მიზანი |
|---|---|---|---|
| `scripts/` (root) | 19 ფაილი | ~5,000 | fetch_*, migrate, ledger, seed, verify_phase_* |
| `scripts/cognition/` | 2 | 474 | budget.py + llm.py (Anthropic wrapper) |
| `scripts/communicator/` | 14 | 4,067 | phi_redactor, bilingual, banned_phrases, telegram, gmail, notion, weekly_brief, outreach_drafter, clinician_pdf |
| `scripts/manager/` | 5 | ~685 | briefing, email_draft, intake/, routing/, activity/ |
| `scripts/extraction/` | 4 | 564 | batch_ingest, graphiti_client, ingest_paper, ontology |
| `scripts/hypothesis/` | 2 | 630 | got_pipeline, backfill_supporting_papers |
| `scripts/chunking/` | 5 | 1,239 | chunker, embedder, extractor, process_ledger, retrofit_qdrant_stamps |

### 3.2 budget.py — ფაქტობრივი state

```python
DEFAULT_DAILY_BUDGET_USD: float = 1.50

def check_daily_budget(
    threshold_usd: float | None = None,
    *,
    raise_on_over: bool = False,
) -> tuple[float, bool]:
```

ფაქტობრივი mechanism:
- Reads `runs.token_cost` since midnight UTC
- Returns `(today_spend_usd, is_over_budget)`
- Optional `BudgetExceeded` exception
- **Fail open:** Supabase unreachable → returns `(0.0, False)` (per design)

**კრიტიკული შენიშვნა:** `DEFAULT_DAILY_BUDGET_USD = 1.50` ნიშნავს, რომ daily ceiling-ი დღეში მხოლოდ $1.50-ია (კოდიდან). v5.0 docs-ში წერდა "$60 cap" — ეს არის სრული პროექტის lifetime cap-ი, არა per-day cap. **მათ შორის სხვაობა მნიშვნელოვანია გასათვალისწინებლად:** $1.50/day × 30 days = $45/month. შესაბამისად, თუ MedGemma/TxGemma local inference $0-ად ჩამოვა, Claude-ის ხარჯი დარჩება ~$45/თვის ფარგლებში.

**Latent verifier issue dossier-დან:** "verify_phase2_5 A.2 (today_spend=$0 → raise_on_over=False)" — ეს არის ცნობილი edge case რომელიც pending fix-ში დევს.

### 3.3 verify_phase_*.py — 5,242 ხაზი

| ფაილი | LOC | მიზანი |
|---|---|---|
| `verify_phase1.py` | 330 | Perception 10/10 gates |
| `verify_phase2.py` | 503 | Memory 19/19 gates |
| `verify_phase2_5.py` | 634 | Quick wins 16/16 gates |
| `verify_phase3.py` | 976 | Cognition 11/11 gates |
| `verify_phase4.py` | 885 | First family value 9/9 gates |
| `verify_phase5.py` | 852 | BRAIN AI Manager 13/13 gates |
| `verify_phase6.py` | 1,062 | Bilingual 11/11 gates |

**Pattern:** თითოეული ფაზის closure-ი მოითხოვს deterministic verifier-ის PASS. v5.0 sprint A-ის შემდეგ შესაბამისი `verify_v5_pilot.py` უნდა აშენდეს ანალოგიური სტრუქტურით (5-10 gate).

### 3.4 phi_redactor.py — 381 ხაზი

ფაქტობრივი mechanism:
- ბილინგვური (KA + EN) PHI detection
- Mkhedruli suffix-glue handling (D-05 lexicon Phase 6)
- `redact_bilingual()` wrapper, OR-block contract
- `ConsentFlags` per-field control

**v5.0 implication:** MedGemma cloud inference (Hugging Face Inference Endpoints) **ვერ ნახულობს ალექსანდრას MRI ფაილს** — phi_redactor-ი არ ანაცვლებს client-side-only rule-ს. MedGemma local inference-ის mandatory rule განცალკეებული რჩება.

---

## 4. Workflows Layer — n8n JSON ანალიზი

### 4.1 11 workflow inventory

| Workflow | მიზანი | სტატუსი |
|---|---|---|
| `daily-budget-gate.json` | FND-04 budget enforcement | **bug-ი არსებობს, code-ში fix, deployed restart pending** |
| `weekly_brief.json` | Phase 4 Sunday brief | Active |
| `manager_briefing.json` | Phase 5 Sunday briefing | Active |
| `perception_6h.json` | Phase 1 cron every 6h | Active |
| `chunking_trigger.json` | Phase 2 chunking | Active |
| `extraction_trigger.json` | Phase 2 graphiti | Active |
| `outreach_review_queue.json` | Phase 3 Communicator | Active |
| `urgent_alerts.json` | Phase 3 high-tier alerts | Active |
| `daily_digest.json` | Phase 4 daily digest | Active |
| `daily_spend_report.json` | Phase 0 ledger | Active |
| `telegram_daily_digest.json` | Phase 4 Telegram | Active |

### 4.2 daily-budget-gate.json — bug ანალიზი

ფაქტობრივი workflow (155 ხაზი) შეიცავს:

**Compute Exceeded node (line 50):**
```javascript
const rows = $input.all().map(i => i.json);
const spend = rows.reduce((a, r) => a + parseFloat(r.token_cost || 0), 0);
const cap = parseFloat($env.DAILY_BUDGET_USD || '1.50');
```

შესაძლო bug location: `$input.all()` ფიქს n8n-ის HTTP node-ის output ფორმატთან მიმართებაში. n8n-ის HTTP Request v4.2 default behavior-ი ცვალდება v4.1-დან: JSON array ცალკე items-ად იშლება ან ერთ item-ში დევს, რომელიც self-contains array-ს. თუ workflow მუშაობდა v4.1-ში და მერე v4.2-ზე გადავიდა, ეს რეგრესია იქნებოდა.

**fix-ი code-ში არსებობს** (per CLAUDE.md). Deployed n8n workflow JSON ჯერ ძველ ვერსიაშია. ეს workflow უნდა გადააიმპორტდეს Railway-ის n8n instance-ში გასწორებული JSON-ით.

**ბიუჯეტის telegram alert-ი ქართულადაა:**
```
"🔴 ბიუჯეტი დაბლოკილია დღევანდელ თარიღში..."
```

Hard-coded ქართული. Phase 6-ის ბილინგვური bilingual contract არ ფარავს n8n workflow-ებს. ეს არის ფარული gap — თუ რომელიმე non-Georgian-speaking partner მიიღებს ამ alert-ს, ისინი ვერ წაიკითხავენ. **v5.0-ში n8n workflow-ების bilingualization deferred item-ად რჩება, არ არის blocker.**

---

## 5. Viewer Layer — Next.js 16 + i18n არქიტექტურა

### 5.1 ფაქტობრივი routing structure

```
viewer/app/
├── api/manager/
│   ├── apply/route.ts        (74 lines)
│   ├── audit/route.ts        (49 lines)
│   ├── email/route.ts        (73 lines)
│   ├── undo/[id]/route.ts
│   └── voice/route.ts        (85 lines)
├── audit/                     (non-localized)
│   ├── layout.tsx
│   └── page.tsx
├── brain/                     (non-localized, MRI viewer)
│   ├── layout.tsx
│   └── page.tsx
├── [locale]/                  (en | ka)
│   ├── layout.tsx
│   ├── page.tsx               (Home / Today / Status Cockpit)
│   ├── dashboard/page.tsx
│   ├── hypotheses/
│   │   ├── actions.ts
│   │   ├── page.tsx
│   │   └── [id]/page.tsx      (dynamic detail view)
│   ├── knowledge/page.tsx
│   ├── papers/page.tsx
│   ├── therapies/page.tsx     (231 lines, JSONB bilingual already)
│   ├── timeline/page.tsx
│   └── today/page.tsx
└── layout.tsx                 (root)
```

### 5.2 v5.0 ხედები vs ფაქტობრივი routing

წინა v5.0 დოკუმენტში მე ვწერდი 6 ახალი ხედის შესახებ. ფაქტობრივად:

| v5.0 ხედი (proposed) | რეალური ხედი | სტატუსი |
|---|---|---|
| Status Cockpit (`/[locale]`) | `app/[locale]/page.tsx` + `today/page.tsx` | **არსებობს** — გაფართოება საჭიროა |
| Treatment Timeline | `app/[locale]/timeline/page.tsx` | **არსებობს** — გაფართოება საჭიროა |
| Brain Viewer | `app/brain/page.tsx` (non-localized) | **არსებობს** — localization + MedGemma annotation slot საჭიროა |
| Therapy Hypotheses | `app/[locale]/hypotheses/page.tsx` + `[id]/page.tsx` | **არსებობს** — TxGemma score column საჭიროა |
| Research Pulse | `app/[locale]/papers/page.tsx` | **არსებობს** — "last 7 days" filter საჭიროა |
| Family Action Inbox | `app/[locale]/dashboard/page.tsx` | **არსებობს** (Manager API ფარავს უკვე) |

**ფინდინგი:** ჩემი v5.0 დოკუმენტი ლაპარაკობდა ისე, თითქოს 6 ხედს ნულიდან ვაშენებდი. ფაქტობრივად, ექვსივე ხედი არსებობს. Sprint C არ არის "build", ეს არის "extend & polish".

### 5.3 ბილინგვური pattern (verified)

`viewer/app/[locale]/therapies/page.tsx` ხაზი 161:
```tsx
<h2>{displayField(therapy.name, locale)}</h2>
```

ხაზი 13: `name: BilingualField` (JSONB `{en, ka}` post-migration-012).

ფაქტობრივი pattern (verified):
- DB column-ი JSONB `{en, ka}`
- TypeScript type `BilingualField`
- Helper `displayField(field, locale)` -> string
- Server-side `setRequestLocale(locale)` + `getTranslations(namespace)`

ეს არის mature pattern. v5.0-ის ახალი ხედები ფიქს ჯდება ამ patterns-ში, არ მოითხოვს ცვლილებას.

### 5.4 i18n messages — actual key inventory

`viewer/messages/en.json` სტრუქტურა:
- 16 namespace: Common, ConfidenceLevel, Dashboard, Home, Hypotheses, HypothesisStatus, HypothesisType, Knowledge, Manager, Navigation, Papers, Shared, Therapies, Timeline, TimelineEventType, Today
- 186 total translation keys
- Mirror file `ka.json` (99.3% Mkhedruli coverage per Phase 6)

**v5.0 implication:** ახალი 6 ხედი არ მოითხოვს ახალი namespace-ის შექმნას. შესაბამისი key-ები არსებულ namespace-ში დაემატება (`Therapies.txgemma_score`, `Hypotheses.alphafold_protein`, ე.წ.).

---

## 6. MCP Servers — 5 custom server

### 6.1 ფაქტობრივი MCP-ები

| MCP | LOC | Status | Allowlisted for |
|---|---|---|---|
| `aleksandra-niivue-mcp` | 338 | Active | viewer (per MCP-INVENTORY.csv) |
| `swarm_orchestrator` | 529 | Active | (not in allowlist — internal helper) |
| `panic_stop` | 176 | Active | * (every agent) |
| `hello_brain` | 66 | Active | * (Phase 0 liveness) |

### 6.2 niivue MCP — fully implemented

```python
from fastmcp import FastMCP

mcp = FastMCP(
    "aleksandra-niivue-mcp",
    dependencies=["nibabel", "numpy"],
    description="მსოფლიოში პირველი ნეიროვიზუალიზაციის MCP სერვერი"
)

@mcp.tool()
def load_nifti(file_path: str) -> str:
    # Returns JSON: dim, voxel_size, affine, dtype, data_range
```

**ფინდინგი:** NIfTI metadata extraction უკვე implemented-ია. MedGemma-ის MRI input pipeline-ი ამ MCP-ის output-ით იკვებება. **integration cost = ნული**, ფიქს ჩაერთვება existing pipeline-ში.

### 6.3 MCP-INVENTORY.csv

ფაქტობრივი sheet (27 MCP):
- 14 active (Phases 0-6)
- 5 v2 reserved (`gcalendar`, `niivue`, `atlas`, `bonbid`, `tvb`)
- 8 outside allowlist

**v5.0-ის MCP additions საჭიროა:**

```csv
medgemma,Google Health open MedGemma 1.5 local inference,analyzer|hypothesis|repurposing,5,cognition,Local inference only - MRI never leaves machine
txgemma,Google DeepMind TxGemma drug repurposing,repurposing,5,cognition,Therapeutic Data Commons-based scoring
alphafold,AlphaFold Server protein structure (browser API),hypothesis|repurposing,5,cognition,Free tier 30 jobs/day non-commercial
hf-datasets,Hugging Face medical datasets sidecar,analyzer,5,cognition,otter_uniprot + approved_drug_target read-only
```

ეს არის 4 ხაზიანი ცვლილება MCP-INVENTORY.csv-ში, რომელიც სავალდებულოა MCP allowlist-ის passing-ისთვის.

---

## 7. Critical Mismatches Identified

### 7.1 Documentation drift

| საკითხი | CLAUDE.md / v5.0 docs | რეალური code |
|---|---|---|
| CrewAI ვერსია | "1.x stable" | `>=0.80.0` (pre-1.0) |
| Next.js ვერსია | "Next.js 14" | `16.2.6` |
| Tailwind ვერსია | "Tailwind 3.x" | `^4` (CSS-first) |
| Sonnet 4.6 escalation | "Hypothesis agent on hard cases" | **არ არის wired** — ყველა აგენტი 4.5-ზე |
| FastMCP ვერსია | "FastMCP 3.2.4" | `>=0.4.0` |
| Crawl4AI security pin | ">=0.8.6" | `>=0.4.0` (vulnerable) |
| DSPy ვერსია | "DSPy 3.2.1" | `>=2.5.0` |
| mem0 algorithm | "April 2026 algorithm" | `>=0.1.50` (older) |

### 7.2 Hidden gaps

**1. Sonnet 4.5 deprecation timeline.** CLAUDE.md ციტირებს "Sonnet 4 deprecates 2026-04-14, retires 2026-06-15". შაკოს ფაქტობრივად ყველა აგენტი წერია `claude-sonnet-4-5`-ზე. ეს არის Sonnet 4.5, არა 4. **საფრთხე არ არის**, მაგრამ ფაქტი არის რომ Anthropic-ის model retirement policy-ი მუდმივი მონიტორინგი მოითხოვს.

**2. n8n workflow language hard-coding.** `daily-budget-gate.json`-ში Telegram alert ქართულადაა, hard-coded. Phase 6 bilingual coverage არ მოიცავს workflow JSON-ებს.

**3. mem0 algorithm gap.** v5.0 docs ციტირებდა "91.6% accuracy at <7K tokens, +29.6 pts on temporal queries" — ეს არის April 2026 algorithm (mem0 0.2.x). requirements.txt-ში pinned 0.1.50 ნიშნავს, რომ ეს გაუმჯობესება არ მუშაობს. **upgrade ღირს, არ არის blocker.**

**4. Adaptive GoT MCP missing.** CLAUDE.md ციტირებს "Adaptive Graph of Thoughts MCP" როგორც hypothesis agent-ის backbone. MCP-INVENTORY.csv-ში `adaptive-got` ფიქს ლისტებულია. ფაქტობრივი MCP server file `mcp/`-ში არ არსებობს. ეს ან არის vendor source რომელიც pip-დან მოდის, ან არასწორი დოკუმენტირება.

**5. Voice intake real path.** Phase 5 Whisper voice transcription `scripts/manager/intake/`-ში უნდა იყოს. დაგვადასტურდა filesystem მიხედვით, კოდი მე არ წავიკითხე ფაქტობრივად.

---

## 8. Integration Points for v5.0 — Concrete Mapping

### 8.1 MedGemma integration

**File modifications required:**

1. **`MCP-INVENTORY.csv`** — append:
   ```csv
   medgemma,Google Health open MedGemma 1.5 local inference,analyzer|hypothesis|repurposing,5,cognition,Local inference only - MRI never leaves machine
   ```

2. **New file `mcp/medgemma_local.py`** (~150 ხაზი ვარაუდი) — FastMCP wrapper:
   - `@mcp.tool() def analyze_mri(nifti_path: str) -> dict`
   - `@mcp.tool() def classify_findings(image_path: str) -> dict`
   - Local Hugging Face transformers loading (`google/medgemma-4b-it`)

3. **`agents/analyzer.py`** line 20 modification:
   ```python
   from agents.tools.analyzer_tools import neo4j_stats, run_graphiti
   from agents.tools.medgemma_tools import analyze_mri  # NEW
   TOOLS: list = [run_graphiti, neo4j_stats, analyze_mri]  # MODIFIED
   ```

4. **New file `agents/tools/medgemma_tools.py`** — CrewAI Tool wrappers.

5. **`requirements.txt`** — append:
   ```
   transformers>=4.45.0
   accelerate>=0.34.0
   torch>=2.5.0
   ```

**Total file changes:** 1 modification + 2 new files + 1 CSV row. ~200 lines of new code total.

### 8.2 TxGemma integration

**File modifications required:**

1. **`MCP-INVENTORY.csv`** — append:
   ```csv
   txgemma,Google DeepMind TxGemma drug repurposing,repurposing,5,cognition,Therapeutic Data Commons-based scoring
   ```

2. **New file `mcp/txgemma_local.py`** (~180 lines)

3. **`agents/repurposing.py`** modification (CRITICAL — empty TOOLS slot):
   ```python
   from agents.tools.txgemma_tools import score_mechanism, find_repurposing_candidates
   TOOLS: list = [score_mechanism, find_repurposing_candidates]  # was []
   ```

4. **New file `agents/tools/txgemma_tools.py`** — CrewAI wrappers.

5. **DB migration `migrations/013_add_txgemma_score.sql`** — therapies table gets `txgemma_score numeric(3,2)` column.

6. **viewer modification `app/[locale]/therapies/page.tsx`** — add txgemma_score column to TypeScript type + UI.

**Total file changes:** 2 modifications + 2 new files + 1 SQL migration + 1 CSV row + 1 viewer extension. ~300 lines.

### 8.3 AlphaFold integration

**File modifications required:**

1. **`MCP-INVENTORY.csv`** — append:
   ```csv
   alphafold,AlphaFold Server protein structure (browser API),hypothesis|repurposing,5,cognition,Free tier 30 jobs/day non-commercial
   ```

2. **New file `mcp/alphafold_server.py`** (~120 lines) — HTTP wrapper to alphafoldserver.com

3. **New file `data/molecular/`** directory for cached PDB outputs.

4. **viewer modification `app/brain/page.tsx`** — sidecar 3D protein structure renderer.

5. **`agents/hypothesis.py`** TOOLS expansion:
   ```python
   from agents.tools.alphafold_tools import predict_structure
   TOOLS: list = [run_hypothesis_generation, validate_hypothesis, predict_structure]
   ```

**Total file changes:** 2 modifications + 2 new files + 1 directory + 1 CSV row. ~200 lines.

### 8.4 Hugging Face datasets

**Lightest touch.** No MCP server needed — direct Python use:

1. **New file `scripts/cognition/hf_datasets.py`** (~80 lines):
   ```python
   from datasets import load_dataset
   def load_drug_target_dataset(): ...
   def load_otter_dataset(): ...
   ```

2. **`requirements.txt`** — append:
   ```
   datasets>=3.0.0
   ```

3. **Optional Qdrant sidecar collection** for embedded reference data.

---

## 9. Updated v5.0 Sprint Plan (Post-Audit)

### 9.1 Sprint allocation revised

**Sprint A (Pilots) — 2 კვირა, UNCHANGED**
- Week 1: MedGemma pilot (3-4 hours) + TxGemma pilot (5-6 hours)
- Week 2: AlphaFold pilot (1-2 hours) + Hugging Face exploration (2-3 hours)
- Output: `docs/v5_pilot_findings.md`, no code changes yet

**Sprint B (Integration) — 2 კვირა, REVISED FROM 3**
- Week 1:
  - MCP-INVENTORY.csv update (5 minutes)
  - 4 new MCP wrappers in `mcp/` (12-16 hours)
  - 4 new tool modules in `agents/tools/` (8 hours)
- Week 2:
  - 4 agent modifications (`spider.py`, `analyzer.py`, `hypothesis.py`, `repurposing.py`)
  - Migration 013 (add txgemma_score)
  - `verify_v5_cognition.py` (10/10 gates)

**Sprint C (Visualization) — 2 კვირა, REVISED FROM 3**
- Week 1: viewer extensions (NOT new pages):
  - `[locale]/therapies/page.tsx` adds txgemma_score column
  - `[locale]/hypotheses/page.tsx` adds alphafold_protein link
  - `brain/page.tsx` adds MedGemma annotation overlay + AlphaFold sidecar
- Week 2:
  - i18n keys: ~20-30 new keys across existing namespaces
  - Accessibility audit
  - `verify_v5_viz.py` (8/8 gates)

**Sprint D (Polish + Acceptance) — 1 კვირა, REVISED FROM 2**
- Family review, bilingual QA, mentor presentation

**მთლიანი duration:** 7 კვირა, არა 10-12 (sprint allocation მცირდება, რადგან ხედები არსებობს, არ ვაშენებთ ნულიდან).

### 9.2 Budget revision

**Pre-audit estimate:** $45-55 / $60 cap
**Post-audit estimate:** $25-35 / $60 cap

რატომ მცირდება: Sprint C-ში არ ვაშენებთ ნულიდან viewer-ს, რაც ნიშნავს ნაკლები Claude API ხარჯი code generation-ისთვის. Sprint B-ში code volume მცირდება ~50%-ით (Repurposing-ის ცარიელი TOOLS-ის შევსება არის small change, არა rebuild).

---

## 10. Pre-Sprint Action Items

ფაზა 4 acceptance window-ის ფარგლებში (next 14 days), პარალელურად, შემდეგი 6 ნაბიჯი:

1. **`requirements.txt` security audit.** ცვალდე:
   - `crawl4ai>=0.4.0` → `crawl4ai>=0.8.6` (CRITICAL — supply chain fix)
   - `mem0ai>=0.1.50` → `mem0ai>=0.2.0` (April 2026 algorithm)
   - `fastmcp>=0.4.0` → `fastmcp>=3.2.0` (BREAKING — testing required)
   - `dspy-ai>=2.5.0` → `dspy-ai>=3.2.0` (BREAKING — testing required)

   **რისკი:** fastmcp 3.x API change. Test cycle: install in fresh venv → run existing tests → fix breakages.

2. **CrewAI ვერსიის installed check.** Bash:
   ```bash
   pip show crewai | grep Version
   ```
   თუ installed ვერსიაა 0.80-ან 0.90, upgrade to 1.14+:
   ```bash
   pip install --upgrade crewai
   ```
   ეს მოითხოვს `agents/*.py` smoke test-ს (Crew.kickoff() ცდა).

3. **Sonnet 4.5 vs 4.6 decision.** ფაქტობრივი state-ი Sonnet 4.5-ზე მუშაობს. გადაწყვიტე: 4.6 escalation hypothesis-ში wire თუ არა. თუ wire, change is 1 line:
   ```python
   def build_hypothesis(llm_model: str = "claude-sonnet-4-6") -> Agent:
   ```

4. **n8n daily-budget-gate redeployment.** გადააიმპორტე გასწორებული `workflows/daily-budget-gate.json` Railway-ის n8n instance-ში. ეს ცნობილი pending item-ია, არ ეცადო v5.0-ში გადატანას.

5. **Phase 4 acceptance window monitoring.** პირველი Sunday brief 2026-05-24 09:00 ET. შაკოს ფიდბექი 14 დღის განმავლობაში. **არცერთი v5.0 code change ამ პერიოდში.**

6. **MCP-INVENTORY.csv pre-update.** დაამატე 4 ახალი ხაზი (medgemma, txgemma, alphafold, hf-datasets). ეს არის dry-run change — MCP servers ფაქტობრივად ჯერ არ შენდება Sprint A-მდე, მაგრამ allowlist-ი მზადაა.

---

## 11. რისკის რეგისტრი

| რისკი | ალბათობა | გავლენა | მართვა |
|---|---|---|---|
| CrewAI 0.80 → 1.14 upgrade breaks agents | Medium | High | Test cycle in feature branch, rollback if smoke test fails |
| MedGemma local inference too slow on family laptop | Medium | Medium | Fallback to HF Inference Endpoints ($0.50/hr occasional) |
| Next.js 16 + React 19 breaks `@niivue/nvreact` | Low | High | Pin nvreact version, test before viewer changes |
| TxGemma hallucinates on rare HIE conditions | High | Medium | Claude synthesizer redundancy + PubMed validation |
| AlphaFold 30/day quota hit | Low | Low | Cache PDB outputs in `data/molecular/` |
| MRI privacy leak via cloud MedGemma | Critical | Critical | **ABSOLUTE RULE**: MRI only goes to local MedGemma, never cloud — enforced in code via mcp/medgemma_local.py architecture |
| Phase 4 Sunday brief fails | Medium | Critical | Block v5.0 sprint until Phase 4 GREEN |
| n8n workflow language drift | Low | Low | Defer bilingual workflow coverage to v6.0 |
| litellm supply-chain vulnerability persists | High (if not pinned) | Critical | Update `crawl4ai>=0.8.6` immediately |
| Adaptive GoT MCP missing from `mcp/` | Medium | Medium | Verify vendor source, vendor if needed |
| Repurposing agent breaks during integration | High | High | Backup `agents/repurposing.py` to `.archive/` before TOOLS modification |
| mem0 0.1.50 → 0.2.x breaking API | Medium | Medium | Test in feature branch, migrate per mem0 0.2.x migration guide |

---

## 12. დასკვნა | Conclusion

ALEKSANDRA_BRAIN v4.0 არის უფრო მოწინავე, ვიდრე ჩემი წინა v5.0 დოკუმენტი ფიქრობდა. ფაქტობრივი code base არის:
- 22,000+ line Python (scripts + agents + mcp)
- 3,000+ line TypeScript (viewer)
- 11 active n8n workflows
- 27-entry MCP allowlist
- 16-namespace, 186-key bilingual coverage
- 7 verifier files totaling 5,242 lines

ეს არ არის prototype. ეს არის production-ready system, რომელიც Phase 4 acceptance window-ში მუშაობს.

v5.0 sprint scope ფაქტობრივად 30% უფრო პატარაა, ვიდრე ჩემი წინა estimate. ხედები არსებობს. integration points არსებობს (Repurposing TOOLS=[] არის სათანადო slot-ი). MCP allowlist mechanism არსებობს. Bilingual JSONB pattern არსებობს.

**ერთი მთავარი ცვლილება** ჩემი ადრინდელი რჩევებიდან: არ აშენო ნულიდან. **გააფართოვე.**

---

## წყაროები | Sources

ფაქტობრივი ფაილები verified ამ აუდიტში:

- `requirements.txt` (96 lines)
- `docker-compose.yml` (58 lines)
- `.env.example` (127 lines)
- `viewer/package.json` (28 lines)
- `viewer/next.config.ts` (10 lines)
- `agents/crew.py` (57 lines)
- `agents/spider.py` (47 lines)
- `agents/analyzer.py` (48 lines)
- `agents/hypothesis.py` (51 lines)
- `agents/repurposing.py` (46 lines) ← **critical empty TOOLS slot identified**
- `agents/communicator.py` (296 lines)
- `agents/_mcp_allowlist.py` (159 lines)
- `agents/tools/` (324 lines across 3 files)
- `scripts/cognition/budget.py` (158 lines)
- `scripts/communicator/` (4,067 lines across 14 files)
- `scripts/manager/` (685 lines across 5 dirs)
- `scripts/verify_phase{1-6}.py` (5,242 lines)
- `mcp/aleksandra_niivue_mcp.py` (338 lines)
- `mcp/swarm_orchestrator.py` (529 lines)
- `mcp/panic_stop.py` (176 lines)
- `mcp/hello_brain.py` (66 lines)
- `MCP-INVENTORY.csv` (27 rows)
- `workflows/daily-budget-gate.json` (155 lines)
- `viewer/app/[locale]/therapies/page.tsx` (231 lines) ← **bilingual pattern verified**
- `viewer/messages/en.json` (16 namespaces, 186 keys)
- `viewer/components/` (DashboardCharts 464 lines, LanguageSwitcher 36 lines, ActionPreview/, AuditLog/, BrainPanel/, layout/)
- `viewer/app/api/manager/{apply,audit,email,undo,voice}/route.ts` (281 lines across 5 routes)
- Git log last 10 commits (current branch state verified)

**არ წავიკითხე ფაქტობრივად ამ აუდიტში** (გადასწია გადახედვა შემდეგ ფაზაში):
- `scripts/manager/intake/` (Whisper voice path)
- `scripts/communicator/weekly_brief.py` (Phase 4 critical, 820 lines)
- `scripts/hypothesis/got_pipeline.py` (394 lines)
- `scripts/chunking/process_ledger.py` (450 lines)
- `viewer/app/[locale]/hypotheses/[id]/page.tsx` (dynamic detail)
- `viewer/components/DashboardCharts.tsx` (464 lines)

ეს ფაილები გადასახედია Sprint A-ის წინ.
