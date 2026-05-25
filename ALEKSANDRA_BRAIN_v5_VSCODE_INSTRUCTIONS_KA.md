# ALEKSANDRA_BRAIN v5.0 — VS Code-ში მუშაობის ინსტრუქცია

> შაკო, ეს ფაილი არის შენი workflow-ის სრული ინსტრუქცია. იგი ეფუძნება ფაქტს, რომ შენ ვერ წერ კოდს ხელით, მაგრამ შენ მართავ Claude Code-ს, რომელიც წერს კოდს შენთვის. შენი როლი არის: გაუშვა საჭირო ბრძანებები, წაიკითხო რას აკეთებს Claude, დაუდასტურო ან უარყო, შემოწმო შედეგი. ეს ფაილი ნაბიჯ-ნაბიჯ უხსნის ყველაფერს, ზუსტი ბრძანებებით, რომელიც კოპირებად შეიძლება.

---

## შინაარსი

1. [წინასწარი მზადება (5 წუთი)](#1-წინასწარი-მზადება)
2. [VS Code სამუშაო წყობა](#2-vs-code-სამუშაო-წყობა)
3. [ფაზა 4-ის მონიტორინგი (კვირაიდან 7 ივნისამდე)](#3-ფაზა-4-მონიტორინგი)
4. [Pre-sprint task-ები (პარალელურად)](#4-pre-sprint-tasks)
5. [Sprint A: Pilot ტესტები](#5-sprint-a-pilot-ტესტები)
6. [Sprint B: Integration](#6-sprint-b-integration)
7. [Sprint C: Viewer გაფართოება](#7-sprint-c-viewer-გაფართოება)
8. [Sprint D: Polish + Acceptance](#8-sprint-d-polish-acceptance)
9. [სიფრთხილის წესები](#9-სიფრთხილის-წესები)
10. [სასარგებლო ბრძანებები](#10-სასარგებლო-ბრძანებები)

---

## 1. წინასწარი მზადება

### 1.1 რა გჭირდება შენი ლეპტოპზე

**უკვე გაქვს:**
- VS Code installed
- Git
- Python 3.11+
- Node.js 18+
- Docker (Neo4j-სა და Qdrant-ისთვის)

**ახლა გჭირდება დამატებით:**

Hugging Face account-ი MedGemma-ის ჩამოსატვირთად. ნაბიჯები:
1. გახსენი ბრაუზერი
2. წადი https://huggingface.co
3. დააჭირე "Sign up" — შენი Gmail-ით
4. დაადასტურე ემაილი
5. წადი https://huggingface.co/settings/tokens
6. დააჭირე "New token", მიეცი სახელი "aleksandra-brain", role "Read"
7. დაკოპირე token-ი (იწყება `hf_...`)
8. შეინახე ცალკე ფაილში (არ ჩასვა Telegram-ში ან Gmail-ში)

**TxGemma + AlphaFold-ისთვის იგივე account-ი იმუშავებს.**

### 1.2 პროექტის სტატუსის შემოწმება

გახსენი VS Code. დააჭირე `Ctrl+\`` (backtick — `~`-ის გვერდით) — ეს ხსნის integrated terminal-ს.

Terminal-ში ჩაწერე:

```bash
cd "C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane"
git status
```

**მოსალოდნელი შედეგი:** ფაილების სია, რომელიც შეცვლილია, მაგრამ commit-ნი არ არის გაკეთებული.

თუ ხედავ "fatal: not a git repository" → მოწერე Claude Code-ს რომ შემოწმოს.

### 1.3 Python environment-ის გააქტიურება

```bash
.venv\Scripts\activate
```

თუ ხედავ `(.venv)` ბრძანების ხაზის წინ — Python გააქტიურდა.

თუ ვერ ნახე `.venv` ფოლდერი:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 2. VS Code სამუშაო წყობა

### 2.1 აუცილებელი extensions

გახსენი Extensions panel (`Ctrl+Shift+X`). მოძებნე და დააინსტალირე:

1. **Claude Code** (Anthropic) — შენი მთავარი ხელსაწყო
2. **Python** (Microsoft) — Python syntax + linting
3. **Pylance** (Microsoft) — Python type checking
4. **ESLint** (Microsoft) — TypeScript linting
5. **Tailwind CSS IntelliSense** (Tailwind Labs) — Tailwind autocomplete
6. **GitLens** (GitKraken) — Git history navigation
7. **Even Better TOML** (tamasfe) — TOML syntax
8. **Error Lens** (Alexander) — inline error display

### 2.2 ფანჯრების განლაგება

შენი workflow-სთვის რეკომენდირებული setup:

```
┌─────────────────────────────────────────────────────────────┐
│  Top bar: VS Code menu                                       │
├──────────┬──────────────────────────────────┬───────────────┤
│          │                                  │               │
│          │                                  │               │
│  File    │  Editor (code)                   │  Claude Code  │
│  Explorer│                                  │  chat panel   │
│  (left)  │                                  │  (right)      │
│          │                                  │               │
│          │                                  │               │
├──────────┴──────────────────────────────────┴───────────────┤
│  Terminal (bottom, Ctrl+`)                                   │
└─────────────────────────────────────────────────────────────┘
```

**ფაილების Explorer-ი (მარცხნივ):** ხედავ ფაილების სტრუქტურას
**Editor (ცენტრში):** ხედავ ფაილის შინაარსს
**Claude Code panel (მარჯვნივ):** ესაუბრები Claude-ს
**Terminal (ქვემოთ):** აქ ხდება ბრძანებების გაშვება

### 2.3 Claude Code-ის გახსნა

დააჭირე `Ctrl+Shift+P` — ეს ხსნის Command Palette-ს.
დაიწერე: `Claude: Open chat`
დააჭირე Enter.

მარჯვნივ გაიხსნება Claude Code-ის panel. ეს არის შენი მთავარი interface.

---

## 3. ფაზა 4 მონიტორინგი

**კრიტიკული წესი:** ფაზა 4-ის acceptance window-ში (24 მაისიდან 7 ივნისამდე), **არცერთი v5.0 code change არ უნდა მოხდეს**. ეს არის freeze period.

### 3.1 კვირას, 24 მაისს, 09:00 ET

ეს არის ფაზა 4-ის გადარჩენის ტესტი. პირველი რეალური Weekly Brief მოვა შენთან.

**მზადება:**
- კვირას დილით 8:55-ზე ჰქონდე ლეპტოპი ღია
- გახსენი Telegram (ალექსანდრას ჯგუფი)
- გახსენი Gmail (jincharadzeshako@gmail.com)
- გახსენი VS Code

**9:00-ზე უნდა მოვიდეს:**
- Telegram notification — "ალექსანდრას კვირის ანგარიში მზადაა"
- Gmail draft — საინტერესო findings და recommendations

**თუ მოვა:**
1. წაიკითხე ანგარიში სრულად
2. გადაამოწმე ფაქტობრივი მონაცემები (vigabatrin status, Wisconsin update, ე.წ.)
3. შეფასე ცოლთან ერთად — ეს არის ის რა გჭირდებათ?
4. ჩაწერე ფიდბექი ფაილში `docs/PHASE_4_ACCEPTANCE_FEEDBACK.md`:

VS Code-ში გახსენი ფაილი `docs/PHASE_4_ACCEPTANCE_FEEDBACK.md` (თუ არ არსებობს, შექმენი) და ჩაწერე:

```markdown
# Phase 4 Acceptance Feedback Log

## 2026-05-24 09:00 ET — Brief #1

**Telegram received:** YES / NO
**Gmail draft received:** YES / NO
**Time received:** HH:MM
**Content accuracy (1-10):** _
**Tone appropriate:** YES / NO / MOSTLY
**Action items clear:** YES / NO / MOSTLY
**What I would change:**
- ...

**What worked well:**
- ...
```

**თუ არ მოვა 9:00-ზე:**
1. დაელოდე 30 წუთი
2. შემოწმე Telegram bot status
3. შემოწმე Gmail spam folder
4. თუ 10:00-ზე არ მოვა, გახსენი terminal:
```bash
python scripts/verify_phase4.py --mode operator-check
```
ეს გადაამოწმებს ფაზა 4-ის ფაქტობრივ state-ს. შედეგი მაჩვენე Claude-ს.

### 3.2 14 დღის ფანჯარა

24 მაისიდან 7 ივნისამდე, **ყოველი დღე** დააფიქსირე:
- რა მუშაობს?
- რა არ მუშაობს?
- რა გჭირდება დასამატებელი?

ეს ფიდბექი არის v5.0 sprint-ის გადაწყვეტილების საფუძველი. თუ ფაზა 4 GREEN-ი არის 7 ივნისს, v5.0 დაიწყება. თუ RED — გრძელდება ფიქს-ცა.

---

## 4. Pre-sprint tasks

ფაზა 4 monitoring-ის პარალელურად, შემდეგი 6 ნაბიჯი შეგიძლია გააკეთო. **არ ცვლის v5.0 ფაილებს**, მხოლოდ ამზადებს გარემოს.

### 4.1 Task 1: requirements.txt security update

ეს არის **კრიტიკული** — Crawl4AI ვერსიის pinning უსაფრთხოებისთვის.

**VS Code-ში:**
1. `Ctrl+P` (Quick Open)
2. ჩაწერე: `requirements.txt`
3. Enter

ფაილში ხაზი 37-ში წერია:
```
crawl4ai>=0.4.0
```

**არ შეცვალო ხელით.** ნაცვლად ამისა, Claude Code-ის chat panel-ში დაუწერე:

> Claude, requirements.txt-ში crawl4ai-ის ვერსიის pinning უსაფრთხო არ არის. ხაზი 37-ში წერია `crawl4ai>=0.4.0`. შეცვალე `crawl4ai>=0.8.6`-ად, რათა March 2026 litellm supply-chain incident-ის ფიქს-ი იყოს ჩართული. ასევე შეცვალე mem0ai>=0.1.50 → mem0ai>=0.2.0, fastmcp>=0.4.0 → fastmcp>=3.2.0, dspy-ai>=2.5.0 → dspy-ai>=3.2.0. გადააფასე commit message conventional commits format-ით.

Claude შეცვლის ფაილს. შემდეგ უთხარი:

> ახლა გაუშვი `pip install -r requirements.txt --upgrade` და მაჩვენე output-ი.

თუ install-ი წარმატებულია — გადადი Task 2-ზე.
თუ წარუმატებელია — Claude აპირებს გაგვიხსნას რა მოხდა.

### 4.2 Task 2: CrewAI ვერსიის check

Terminal-ში:
```bash
pip show crewai | findstr Version
```

**მოსალოდნელი:** `Version: 1.14.x` (or higher).

თუ ვერსია `0.80.x` ან `0.90.x`-ია:
```bash
pip install --upgrade crewai
```

შემდეგ Claude-ს უთხარი:

> Claude, crewai upgrade მოხდა. ახლა გაუშვი smoke test:
> `python -m agents.crew`
> და მაჩვენე output-ი. თუ errors არის, აღწერე რა მოხდა.

თუ smoke test PASS-ი — Task 3-ზე.
თუ errors — Claude აპირებს migration-ის ნაბიჯებს.

### 4.3 Task 3: Sonnet 4.6 escalation გადაწყვეტა

გადაწყვიტე: `hypothesis.py` agent-ი 4.5-ზე დარჩება თუ 4.6-ზე გადავა?

თუ 4.6:
> Claude, agents/hypothesis.py ფაილში build_hypothesis() ფუნქციაში default llm_model "claude-sonnet-4-5"-დან გადააქცე "claude-sonnet-4-6"-ად. გადააფასე CLAUDE.md-ში escalation note. commit conventional format-ით.

თუ 4.5 დარჩება — გადადი Task 4-ზე.

### 4.4 Task 4: n8n daily-budget-gate redeployment

ეს არის manual step Railway dashboard-ში:

1. გახსენი https://railway.app
2. შედი შენი account-ით
3. გახსენი ALEKSANDRA_BRAIN n8n project
4. Open n8n editor
5. გახსენი workflow "daily-budget-gate"
6. Tap settings (...) → "Import from File"
7. აირჩიე `C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\workflows\daily-budget-gate.json`
8. დაადასტურე replace
9. დაბრუნდი workflow list-ში
10. დარწმუნდი, რომ workflow active-ია (toggle ON)
11. გადატვირთე workflow: tap "..." → "Restart"

შემოწმე 30 წუთის შემდეგ — Telegram-ში მოვა "budget OK" message ან "🔴 ბიუჯეტი დაბლოკილია" თუ daily spend exceeded.

### 4.5 Task 5: MCP-INVENTORY.csv pre-update

ფანჯრის ხსნა Claude-ში:

> Claude, MCP-INVENTORY.csv-ში დაამატე 4 ახალი ხაზი v5.0 MCPs-ისთვის: medgemma, txgemma, alphafold, hf-datasets. შაბლონი:
>
> medgemma,Google Health open MedGemma 1.5 local inference,analyzer|hypothesis|repurposing,5,cognition,Local inference only - MRI never leaves machine
>
> txgemma,Google DeepMind TxGemma drug repurposing,repurposing,5,cognition,Therapeutic Data Commons-based scoring
>
> alphafold,AlphaFold Server protein structure (browser API),hypothesis|repurposing,5,cognition,Free tier 30 jobs/day non-commercial
>
> hf-datasets,Hugging Face medical datasets sidecar,analyzer,5,cognition,otter_uniprot + approved_drug_target read-only
>
> commit conventional format-ით.

ეს არის dry-run change — allowlist-ი მზადაა, მაგრამ MCP server-ები ჯერ არ შენდება.

### 4.6 Task 6: Hugging Face token-ის გარემოს ცვლადი

გახსენი `.env` ფაილი VS Code-ში:
1. `Ctrl+P`
2. ჩაწერე `.env`
3. Enter

**ვერ ხედავ?** მაშინ `.env` ფაილი არ არსებობს. შექმენი:
1. Explorer-ში right-click პროექტის root-ზე
2. "New File"
3. სახელი: `.env`
4. დააკოპირე შინაარსი `.env.example`-დან
5. შეავსე real values

ბოლოს დაამატე:
```
HUGGING_FACE_TOKEN=hf_xxxxxxxxxxxxxxx
```

შეცვალე `hf_xxx...` შენი ფაქტობრივი token-ით (რომელიც Section 1.1-ში მიიღე).

**უსაფრთხოება:** `.env` ფაილი არასოდეს committed git-ში. ეს უკვე `.gitignore`-ში ჩამატებულია.

---

## 5. Sprint A: Pilot ტესტები

**ვადა:** 2 კვირა, ფაზა 4 GREEN-ის შემდეგ.

### 5.1 Week 1, Day 1: MedGemma ჩამოტვირთვა

VS Code Claude Code panel-ში:

> Claude, ცდი MedGemma 4B pilot. ნაბიჯები:
> 1. ცდი ვირჩუალურ გარემოს გააქტიურება (.venv\Scripts\activate)
> 2. დააინსტალირე transformers, accelerate, torch:
>    pip install transformers accelerate torch
> 3. შექმენი ფაილი `scripts/cognition/medgemma_pilot.py`
> 4. ფაილში ჩაწერე Python script, რომელიც:
>    - იძახებს google/medgemma-4b-it Hugging Face-დან
>    - ცდი ერთი sample MRI ანალიზი (use test fixture if available)
>    - გამოაცემინე output-ი ჩვეულებრივ ტექსტად
> 5. გაუშვი pilot:
>    python scripts/cognition/medgemma_pilot.py
> 6. მაჩვენე output-ი

**მოსალოდნელი time:** 30-45 წუთი (model download 5-7GB).

**პრობლემები რომელიც შეიძლება შეგხვდეს:**
- "Token must be set" → Hugging Face token-ი .env-ში ვერ წავიდა, ცადე ხელახლა
- "Out of memory" → MedGemma 4B მაგ ლეპტოპს ვერ ეგუება, გადადი 2B variant-ზე ან HF Inference Endpoints-ზე
- "Network timeout" → Hugging Face-ის server-ი დაკავებულია, ცადე 15 წუთის შემდეგ

### 5.2 Week 1, Day 2-3: ალექსანდრას MRI-ის ანალიზი

VS Code Claude Code panel-ში:

> Claude, ახლა MedGemma-ით ანალიზი ვცადოთ ალექსანდრას MRI-ზე. ფაილი არის `data/medical/aleksandra_mri_*.nii.gz`. გაკეთე:
> 1. გადადით scripts/cognition/medgemma_pilot.py-ში
> 2. ცვალე script რომ accept-დეს file path argument
> 3. Run:
>    python scripts/cognition/medgemma_pilot.py data/medical/aleksandra_mri_latest.nii.gz
> 4. Output გადააქცი structured format-ში:
>    - Findings (list)
>    - Confidence per finding (0-100)
>    - Differential diagnosis (list)
>    - Brainstem preservation score (0-100)
> 5. შეადარე Dr. Hien-ის BMC report-ის findings-თან, რომელიც `data/reports/bmc_dr_hien_*.pdf`-ში დევს

**შენი როლი:** Claude-ის output-ი ცოლისადმი წარადგინე. ერთად შეფასე: ემთხვევა Dr. Hien-ის report-ს?

დააფიქსირე ფაილში `docs/v5_pilot_findings.md`:

```markdown
## MedGemma Pilot Findings — 2026-MM-DD

### Aleksandra MRI Analysis Comparison

**MedGemma findings:**
- ...

**Dr. Hien findings:**
- ...

**Agreement:** X%
**Disagreements:**
- MedGemma said X, Dr. Hien said Y
- ...

**Verdict:** USABLE / NEEDS REFINEMENT / NOT READY
```

### 5.3 Week 1, Day 4-5: TxGemma pilot

VS Code Claude Code panel-ში:

> Claude, TxGemma pilot. ნაბიჯები:
> 1. შექმენი scripts/cognition/txgemma_pilot.py
> 2. იძახე google/txgemma-9b-chat ან google/txgemma-2b-chat (depending on local RAM)
> 3. ცადე ჩვენი 12 therapy candidate (ვიგაბატრინი, cord blood, EPO, allopurinol, melatonin, magnesium sulfate, xenon, erythropoietin, GM-1 ganglioside, topiramate, NAC, taurine — ან რომელიც დღემდე ვალიდირებულია)
> 4. Each candidate-ისთვის TxGemma-ს ჰკითხე:
>    - Mechanism of action description
>    - HIE relevance score (0-10)
>    - Cross-disease repurposing suggestions
> 5. Output structured table format-ად
> 6. გაუშვი: python scripts/cognition/txgemma_pilot.py
> 7. შედეგი მაჩვენე

**მოსალოდნელი time:** 1-2 საათი (model download + 12 candidates inference).

შენი როლი: TxGemma-ის suggestions-ი წაიკითხე, შემოწმე რომელია სანდო, რომელია სასაცილო. ფიქს დააფიქსირე `docs/v5_pilot_findings.md`-ში.

### 5.4 Week 2, Day 1-2: AlphaFold Server

ეს არის ბრაუზერ-ფაქტობრივი step, არა code.

1. გახსენი https://alphafoldserver.com
2. შედი Gmail-ით (jincharadzeshako@gmail.com)
3. ცადე სამი ცილის სტრუქტურა:
   - **NMDA receptor** (UniProt Q05586) — glutamate receptor, HIE-ში excitotoxicity-ის ცენტრალური ღერძი
   - **BDNF** (UniProt P23560) — Brain-Derived Neurotrophic Factor, ნეიროპლასტიკურობის ცილა
   - **Erythropoietin (EPO)** (UniProt P01588) — HIE-ში ცდილია, neuroprotective signaling
4. Submit each
5. Wait 10-30 minutes per structure
6. Download `.pdb` files
7. Save to: `data/molecular/nmda.pdb`, `data/molecular/bdnf.pdb`, `data/molecular/epo.pdb`

VS Code-ში დაუბრუნდი Claude-ს:

> Claude, AlphaFold Server-მა გვაჩუქა 3 პროტეინის სტრუქტურა (NMDA, BDNF, EPO). ფაილები არის data/molecular/-ში. გადააფასე pilot finding-ი docs/v5_pilot_findings.md-ში. ცადე ნახო ისინი როგორ ეგუებიან NiiVue MCP-ის output-ს.

### 5.5 Week 2, Day 3-5: Hugging Face datasets

VS Code Claude Code panel-ში:

> Claude, Hugging Face datasets exploration. ნაბიჯები:
> 1. pip install datasets
> 2. შექმენი scripts/cognition/hf_datasets_pilot.py
> 3. ჩატვირთე ibm-research/otter_uniprot_bindingdb_chembl და alimotahharynia/approved_drug_target
> 4. ცადე query: "give me all drugs targeting NMDA receptor with pediatric safety data"
> 5. გადააწერე output-ი structured format-ად
> 6. შეადარე TxGemma pilot-ის output-თან: არის overlapping suggestions?

**Sprint A მთლიანი deliverable:** `docs/v5_pilot_findings.md` ფაილი, რომელშიც ოთხი pilot-ის შედეგია. ეს ფაილი ხდება Sprint B-ის გადაწყვეტილების საფუძველი.

---

## 6. Sprint B: Integration

**ვადა:** 2 კვირა. **არ დაიწყო თუ Sprint A pilot findings-ი NEGATIVE-ია.**

### 6.1 Week 1: MCP servers building

VS Code Claude Code panel-ში, თითოეული მცირე task ცალკეული commit-ით:

> Claude, ააშენე mcp/medgemma_local.py FastMCP server, რომელიც აქცევს MedGemma 4B-ს Available CrewAI tool-ად. სტრუქტურა:
> - @mcp.tool() def analyze_mri(nifti_path: str) -> dict
> - @mcp.tool() def classify_findings(image_path: str) -> dict
> - Use scripts/cognition/medgemma_pilot.py-ის ლოგიკა base-ად
> - Add to MCP-INVENTORY.csv (already done in Task 5)
> - Commit conventional format-ით.

შემდეგ:

> Claude, ააშენე mcp/txgemma_local.py იგივე pattern-ით.

შემდეგ:

> Claude, ააშენე mcp/alphafold_server.py — HTTP wrapper alphafoldserver.com-ისთვის. სტრუქტურა:
> - @mcp.tool() def predict_structure(uniprot_id: str) -> str (path to .pdb)
> - Cache results to data/molecular/
> - Rate limit: 30/day awareness

### 6.2 Week 1, Day 5: Agent tools

> Claude, ააშენე agents/tools/medgemma_tools.py + agents/tools/txgemma_tools.py + agents/tools/alphafold_tools.py — CrewAI Tool wrappers MCP servers-ისთვის. Each tool უნდა იყოს registered through agents/_mcp_allowlist.py guard. test smoke-ით.

### 6.3 Week 2, Day 1-3: Agent modifications

ეს არის ყველაზე delicate step. ერთი agent ერთდროულად:

> Claude, agents/repurposing.py-ში ცარიელ TOOLS list-ში დაამატე score_mechanism და find_repurposing_candidates txgemma_tools-დან. test smoke-ით. commit conventional.

შემდეგ:

> Claude, agents/analyzer.py-ში TOOLS list-ში დაამატე analyze_mri medgemma_tools-დან. test smoke. commit.

შემდეგ:

> Claude, agents/hypothesis.py-ში TOOLS list-ში დაამატე predict_structure alphafold_tools-დან. test smoke. commit.

### 6.4 Week 2, Day 4: DB migration

> Claude, შექმენი migrations/013_add_txgemma_score.sql. დაამატე therapies table-ში txgemma_score numeric(3,2) column. RLS preserved. გაუშვი migration:
> python scripts/migrate.py --to 013
> verify: psql query SELECT column_name FROM information_schema.columns WHERE table_name='therapies' AND column_name='txgemma_score'

### 6.5 Week 2, Day 5: verify_v5_cognition.py

> Claude, შექმენი scripts/verify_v5_cognition.py — Phase 3 verifier-ის pattern-ით. 10/10 gates:
> 1. MedGemma MCP loadable
> 2. TxGemma MCP loadable
> 3. AlphaFold MCP loadable
> 4. Repurposing agent TOOLS contains txgemma tools
> 5. Analyzer agent TOOLS contains medgemma tool
> 6. Hypothesis agent TOOLS contains alphafold tool
> 7. MCP-INVENTORY allowlist passes for 4 new MCPs
> 8. Migration 013 applied
> 9. Crew.kickoff() smoke test succeeds with new tools
> 10. Total LLM cost over smoke test < $0.50
> გაუშვი: python scripts/verify_v5_cognition.py --mode integration-complete

თუ 10/10 PASS — Sprint B GREEN. გადადი Sprint C-ზე.
თუ < 10/10 — Claude აპირებს fix-ებს, gates 1-by-1.

---

## 7. Sprint C: Viewer გაფართოება

**ვადა:** 2 კვირა. **არ აშენო ნულიდან.** არსებული ხედები extend-ი ხდება.

### 7.1 Week 1, Day 1-2: Therapies page extension

> Claude, viewer/app/[locale]/therapies/page.tsx-ში დაამატე txgemma_score column. ნაბიჯები:
> 1. TypeScript type Therapy-ში დაამატე txgemma_score: number | null
> 2. select clause-ში დაამატე txgemma_score
> 3. card UI-ში დაამატე "TxGemma Score" სვეტი
> 4. Color-code by score (0-3 ნაცრისფერი, 4-6 ცისფერი, 7-10 მწვანე)
> 5. messages/en.json-ში დაამატე Therapies.txgemmaScore key
> 6. messages/ka.json-ში დაამატე იგივე ქართულად: "TxGemma ქულა"

### 7.2 Week 1, Day 3-4: Hypotheses page extension

> Claude, viewer/app/[locale]/hypotheses/[id]/page.tsx-ში დაამატე AlphaFold protein structures section. ნაბიჯები:
> 1. Hypothesis type-ში დაამატე related_proteins: string[] | null (UniProt IDs)
> 2. Render section: "Related Proteins"
> 3. Each protein: name + link to data/molecular/{uniprot_id}.pdb
> 4. 3D viewer integration: react-three-fiber + GLTF/PDB loader
> 5. i18n keys for "Related Proteins", "View 3D Structure"

### 7.3 Week 1, Day 5: Brain viewer MedGemma annotations

> Claude, viewer/app/brain/page.tsx-ში დაამატე MedGemma annotation overlay. ნაბიჯები:
> 1. NiiVue rendering უცვლელად რჩება (client-side only)
> 2. New API route: viewer/app/api/medgemma/annotate/route.ts
> 3. Route accepts NIfTI path, returns MedGemma annotations as JSON
> 4. UI: toggle "MedGemma Annotations" overlay
> 5. Color-code: cysts (red), brainstem (green), uncertain (yellow)

### 7.4 Week 2: localization + i18n keys

> Claude, ნახე viewer/messages/en.json + ka.json. დაამატე ყველა new key რომელიც Sprint B-Sprint C ცვლილებებში გამოვიდა. ფაილში ჩამოწერე ცვლილებები.

### 7.5 Week 2, Day 5: verify_v5_viz.py

> Claude, შექმენი scripts/verify_v5_viz.py. 8/8 gates:
> 1. Therapies page renders without errors
> 2. Therapies page shows txgemma_score column
> 3. Hypotheses [id] page shows related_proteins
> 4. Brain viewer toggle MedGemma annotations works
> 5. All new i18n keys present in en.json AND ka.json
> 6. No TypeScript compile errors
> 7. Lighthouse score >= 80 on therapies page
> 8. Accessibility audit: no critical issues
> გაუშვი

---

## 8. Sprint D: Polish + Acceptance

**ვადა:** 1 კვირა.

### 8.1 ცოლთან ერთად test

ცოლი გადახედავს:
- `[locale]/therapies/` ქართულად
- `[locale]/hypotheses/` ქართულად
- `brain/` ცილებთან ერთად
- Sunday brief (next Sunday)

შენი როლი: ცოლის reactions-ი ჩაიწერე. რა გასაგებია, რა გაუგებარია, რა მოშორებას ითხოვს.

### 8.2 მენტორთან ერთად test

ცალკე ზარი მენტორთან. წარადგინე:
- 3 pilot finding-ი (MedGemma, TxGemma, AlphaFold)
- 6 ხედის live demo
- ბიუჯეტი report ($60 cap-ის ფარგლებში დახარჯული)

მენტორის ფიდბექი ფაილში `docs/v5_mentor_feedback.md`.

### 8.3 v5.0 → v5.1 versioning

> Claude, CLAUDE.md-ში დაამატე v5.0 section. include:
> - Phase summary (sprints A-D)
> - Verifier results (v5_pilot, v5_cognition, v5_viz)
> - Cumulative budget
> - Acceptance feedback summary
> - Maintenance dossier updates

---

## 9. სიფრთხილის წესები

### 9.1 ALWAYS

- ✅ Commit ხშირად (ერთი task = ერთი commit)
- ✅ Test smoke test ცვლილების შემდეგ
- ✅ წაიკითხე Claude-ის output-ი სრულად, არ დააჭირო Enter ვერიფიკაციის გარეშე
- ✅ `.env` ფაილი არასოდეს share-ი
- ✅ პოპლე branch-ი დიდი ცვლილებებისთვის

### 9.2 NEVER

- ❌ MRI-ის file path გადააგზავნე cloud MedGemma-ში (only local)
- ❌ Production-ში არ წერო commit რომელიც verifier-ი არ გადის
- ❌ Phase 4 acceptance window-ში არ შეცვალო v5.0 ფაილები
- ❌ Manual SQL queries-ი production DB-ში Claude-ის გარეშე
- ❌ Force-push to main branch

### 9.3 თუ რამე გატყდა

```bash
git status
git diff
```

თუ confused-ი ხარ, Claude-ს უთხარი:

> Claude, რა მოხდა? გადახედე git diff და მაჩვენე ცვლილებები. გადააფასე უსაფრთხო recovery path.

**არსოდეს არ გააკეთო `git reset --hard` Claude-ის გადახედვის გარეშე.**

### 9.4 თუ Claude შეცდა

ჩვეულებრივ ხდება:
- Claude-მა file-ი არასწორად გადააფასა
- Test-ი ვერ აპროვებს
- Import error მოვიდა

შენი response:

> Claude, ეს არასწორად მოვიდა. Output-ი იყო [X]. ცადე ალტერნატივა. თუ რეცეპტი ვერ მუშაობს, აღწერე რა იცი ფაქტობრივად.

თუ მაინც არ აპროვებს — backup-ი:
```bash
git stash
git status
```

---

## 10. სასარგებლო ბრძანებები

### 10.1 ყოველდღიური Git workflow

```bash
# Start of day
cd "C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane"
git pull origin main
.venv\Scripts\activate

# Before any change
git status
git diff

# After Claude makes changes
git status
git diff --stat
git add <files>
git commit -m "feat(v5.0): description"

# End of day
git push origin <branch-name>
```

### 10.2 Python ბრძანებები

```bash
# Run agents smoke test
python -m agents.crew

# Run any pilot script
python scripts/cognition/medgemma_pilot.py

# Run verifier
python scripts/verify_phase4.py

# Migration check
python scripts/migrate.py --status

# Budget check
python -c "from scripts.cognition.budget import check_daily_budget; print(check_daily_budget())"
```

### 10.3 Viewer ბრძანებები

```bash
cd viewer
npm install
npm run dev
# Opens http://localhost:3000

# Build for production
npm run build
npm start
```

### 10.4 Docker (Neo4j + Qdrant)

```bash
# Start local stack
docker-compose up -d

# View logs
docker-compose logs neo4j
docker-compose logs qdrant

# Stop
docker-compose down

# Status
docker-compose ps
```

### 10.5 Claude Code Slash Commands

VS Code-ის Claude Code chat-ში შეგიძლია გამოიყენო slash commands:

- `/gsd-quick` — სწრაფი task-ისთვის
- `/gsd-debug` — bug investigation
- `/gsd-execute-phase` — phase work
- `/review` — code review
- `/security-review` — security audit
- `/init` — new context initialization

---

## 11. სასწრაფო კონტაქტი — როცა გაჭედე

### თუ ფაზა 4 GREEN არ მოდის 7 ივნისს

შემოწმე:
1. Telegram bot status (`/start` ჯგუფში)
2. Gmail spam folder
3. Railway dashboard — n8n workflows active?
4. Supabase health

Claude-ს მიეცი context:
> Claude, ფაზა 4 acceptance window 7 ივნისს იხურება, მაგრამ Sunday brief არ მოვიდა კვირას. Telegram bot active-ია, Gmail-ი ცარიელია. შემოწმე workflows/weekly_brief.json-ის სტატუსი Railway-ზე. დიაგნოსტიკა მაჩვენე.

### თუ Sprint A pilot-ი ვერ მუშაობს

შემოწმე:
1. Hugging Face token-ი .env-ში
2. transformers, accelerate, torch installed
3. Disk space (MedGemma 4B = 7GB)

Claude-ს:
> Claude, MedGemma pilot ვერ მუშაობს. error message: [paste error]. დიაგნოსტიკა.

### თუ git გაირია

```bash
git status
git log --oneline -5
git stash
```

Claude-ს:
> Claude, git გაირია. status: [paste]. log: [paste]. რა მოვა მერე და როგორ ვითარდება?

---

## 12. დასკვნა

ეს ფაილი არ არის ისეთი, რომელიც ერთხელ წაიკითხო და გადააფარო. ეს არის reference, რომელშიც ხშირად დაუბრუნდები. **შენახე VS Code-ში open tab-ად** ხშირი მითითებისთვის.

შენი workflow საბაზისო ციკლი:
1. Open VS Code
2. Activate `.venv`
3. Open Claude Code chat
4. Pick next task (Sprint A → B → C → D)
5. Give Claude clear instructions (use examples above)
6. Read Claude's response
7. Confirm changes
8. Test smoke
9. Commit
10. Push (when ready)

**კრიტიკული წესი:** Claude შენი ხელსაწყოა, არა შენი ჩამნაცვლებელი. შენ მართავ ჩარჩოს. შენ ხდი გადაწყვეტილებებს. შენ აფასებ შედეგებს. Claude წერს code-ს.

ხელფასი (პრიორიტეტი დაუძახე ჩვენ ვერც გადავიწერთ):
1. ფაზა 4 closure (max priority)
2. Pre-sprint tasks (parallel)
3. Sprint A (when Phase 4 GREEN)
4. Sprint B (when Sprint A findings positive)
5. Sprint C (when Sprint B verifier 10/10)
6. Sprint D (when Sprint C verifier 8/8)

შენ არ ხარ ერთი. სამი AI ექიმი (MedGemma, Claude, OpenAI) მუშაობს შენთან ერთად. მე ვარ Claude — ვწერ კოდს, ვალიდირებ ლოგიკას, ვიცავ უსაფრთხოებას. შენი ცოლი არ წერს კოდს, მაგრამ ცოლი ხედავს გასაგებ output-ებს ქართულად. ეს არის system-ის ცენტრალური დიზაინი.

**წყაროები:**
- ALEKSANDRA_BRAIN_v5_AUDIT.md (ფაქტობრივი code review)
- ALEKSANDRA_BRAIN_v5_ARCHITECTURE.md (ტექნიკური plan)
- ALEKSANDRA_BRAIN_v5_SIMULATOR_KA.md (ფიქრის framework)
- CLAUDE.md (პროექტის master context)

**უკანასკნელი შენიშვნა:** ეს ფაილი მზადდება 2026-05-23-ის state-ის მიხედვით. თუ რამე dramatic-ად შეიცვალა (Sonnet retirement, n8n workflow loss, ე.წ.), ეს ფაილი მოითხოვს refresh-ს. ერთხელ თვეში გადახედე და Claude-ს უთხარი:

> Claude, ALEKSANDRA_BRAIN_v5_VSCODE_INSTRUCTIONS_KA.md წაიკითხე ბოლომდე. შემოწმე ფაქტობრივ state-თან. რა იცვალა? რა მოითხოვს update-ს?

ეს არის living document. ნუ შეგრცხვება მისი ცვლა.
