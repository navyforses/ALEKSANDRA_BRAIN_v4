# ALEKSANDRA_BRAIN — სისტემის სრული რენტგენი 🧠

> ეს დოკუმენტი ხსნის, **როგორ მუშაობს მთელი სისტემა** — თავიდან ბოლომდე.
> წაიკითხავს ნებისმიერი ადამიანი (არაპროგრამისტიც), მაგრამ შიგნით ყველა
> ტექნიკური დეტალია — რომელ AI-ს ვიყენებთ, რომელ ბაზას, რომელ MCP სერვერს.
>
> 📊 ვიზუალური სქემა: [`architecture_xray_ka.svg`](architecture_xray_ka.svg)
> (გახსენი ბრაუზერში — ერთ ეკრანზე ხედავ მთელ მანქანას)

---

## 🚗 მთავარი მეტაფორა — მანქანის გაშლილი სქემა

წარმოიდგინე მანქანა, რომელიც **თვითონ ეძებს გზას, თვითონ ფიქრობს და თვითონ
წერს წერილებს**. ალექსანდრას სისტემა ზუსტად ასეთია — მუდმივად მომუშავე
"მკვლევარი მანქანა", რომელიც ეძებს ალექსანდრას მკურნალობის შესაძლებლობებს.

მონაცემი მიედინება **ერთი მიმართულებით**, 5 ფენაში:

```
👁 აღქმა  →  🧠 მეხსიერება  →  🤖 აზროვნება  →  ✍️ მოქმედება  →  🖥 პორტალი
 (ეძებს)      (ინახავს)        (აანალიზებს)     (წერს/აგზავნის)   (აჩვენებს)
```

ხოლო ყველაფერს ქვემოდან იცავს **⚖️ კონსტიტუცია** (წესები + ბიუჯეტი + დაცვა),
და ბოლოს ყველაფერი **👨‍⚕️ ექიმთან** მიდის — ის იღებს გადაწყვეტილებას.

---

## 1️⃣ აღქმა — ვინ ეძებს და აგროვებს მასალას

ეს არის სისტემის **"თვალები"**. აქ რობოტები დადიან ინტერნეტში და სამეცნიერო
სტატიებს აგროვებენ.

| ინსტრუმენტი | რას აკეთებს | მარტივად |
|---|---|---|
| **Crawl4AI** | მთავარი scraper, უფასო, ლოკალური | "ობობა" რომელიც საიტებს კითხულობს |
| **NCBI E-Utilities** | PubMed / ClinicalTrials-ის ოფიციალური API | სამედიცინო ბაზებიდან სტატიების აღება |
| **Firecrawl** | ფასიანი fallback (JS-ით დატვირთული საიტები) | მაშინ ერთვება, როცა Crawl4AI ვერ უმკლავდება |
| **Browser Use** | paywall-ის გვერდის ავლა | ფასიან სტატიებში "შესვლა" |
| **RAGFlow** | PDF → ნაჭრები → entities | სტატიის ფაილს ჭრის გასაანალიზებლად |

**ვინ მართავს:** **n8n** (Railway-ზე) — `perception_6h` workflow ყოველ
6 საათში ავტომატურად უშვებს ძიებას. სულ **11 n8n workflow** მუშაობს
(`perception_6h`, `chunking_trigger`, `extraction_trigger` და სხვ.).

> ⚠️ **ცნობილი caveat:** `perception_tick` worker Railway-ზე გადასატვირთია —
> cron 7 დღე არ ისვრის (`verify_phase2_5 B.1 RED`). Shako-ს deferred action.

---

## 2️⃣ მეხსიერება — სად და როგორ ინახება

ნაპოვნი მასალა **სამ პარალელურ ბაზაში** იწერება, თითო თავისი დანიშნულებით.
ეს არ არის დუბლირება — თითო ბაზა სხვადასხვა კითხვაზე პასუხობს.

| საცავი | რას ინახავს | რატომ ის |
|---|---|---|
| **Neo4j + Graphiti** | ცოდნის **გრაფი** (entities + facts + კავშირები) | "ვინ-რას-უკავშირდება". `confidence decay` — ფაქტი დროში "ბერდება". **568 entities · 307 facts** |
| **Qdrant** | **ვექტორები** (სტატიების embedding) | "მსგავსზე ძიება". fastembed ლოკალურად, უფასო. **5,302 ვექტორი** |
| **Supabase Postgres** | მეტამონაცემები, ledger, audit | "ცხრილური ჭეშმარიტება". **15 ცხრილი, RLS დაცვა, migrations 008→015** |
| **LightRAG** | graph + vector ერთ query-ში | აგენტებს უმარტივებს ცხოვრებას |
| **mem0** | 5 აგენტის **საერთო მეხსიერება** | აგენტებს შორის კონტექსტი |
| **Cloudflare R2** | raw ფაილები (HTML, PDF) | zero-egress storage (KV deprecated) |

> 🔒 **მნიშვნელოვანი:** MRI/DICOM **არასოდეს ინახება სერვერზე** — მხოლოდ
> ბრაუზერში (იხ. ფენა 5).

---

## 3️⃣ აზროვნება — რომელი AI აანალიზებს

აქ არის სისტემის **"ტვინი"**. ორი ნაწილია: კლასიკური **5 აგენტი** + ახალი
**v7 მსჯელობის ძრავა** (ბაიესი/მიზეზობრიობა/სიმულაცია).

### 🤖 CrewAI — 5 აგენტი (ძრავა: Claude Sonnet)

| აგენტი | როლი |
|---|---|
| 🕷 **Spider** | Research Paper Hunter — ახალ კვლევებს პოულობს (5,301 chunk) |
| 🔬 **Analyzer** | Evidence Quality Assessor — მტკიცებულების ხარისხს აფასებს |
| 💡 **Hypothesis** | Cross-Disease Pattern Finder — კავშირებს პოულობს (10 hyp · 3 promising) |
| 💊 **Repurposing** | Drug Discovery — წამლების ახალ გამოყენებას ეძებს (12 cand · 5 validated) |
| 📢 **Communicator** | Family Liaison — ოჯახისთვის თარგმნა (ორენოვანი EN/KA) |

**რომელი მოდელი:**
- **Claude Sonnet 4.5** (`claude-sonnet-4-5`) — default ყველა აგენტისთვის
- **Claude Sonnet 4.6** (`claude-sonnet-4-6`) — escalation რთულ შემთხვევებზე (ხარჯის gate-ით)
- **DSPy** — prompt-ების ოპტიმიზაცია
- **Adaptive GoT MCP** — ჰიპოთეზის DAG-ად დაშლა

### 🧬 v7 მსჯელობის ტვინი (Phase 7.0–7.4)

ეს არის სისტემის ყველაზე ღრმა ნაწილი — **არა მხოლოდ "პოვნა", არამედ "მსჯელობა"**:

| მოდული | რას აკეთებს |
|---|---|
| **PyMC / NumPyro** | ბაიესის **რწმენის** ძრავა — 13-განზომილებიანი schema, posterior update |
| **DoWhy / Pearl SCM** | **მიზეზობრიობა** — `do()` ინტერვენცია, counterfactual ("რა მოხდებოდა, რომ...") |
| **TVB Docker** | ტვინის **neural-mass სიმულაცია** — HIE lesion-mask region inhibition |
| **Shannon EIG** | **აქტიური კითხვები** — entropy-ით ითვლის "რომელი კითხვა მოგვცემს ყველაზე მეტ ინფორმაციას" |
| **Monte Carlo** | ტრაექტორიის ძრავა — scenario aggregator |

### 🔌 Custom MCP სერვერები (FastMCP-ით)

- `aleksandra_niivue_mcp` — MRI viewer-თან ინტეგრაცია
- `swarm_orchestrator` — აგენტების ორკესტრაცია
- `panic_stop` — გადაუდებელი გაჩერება
- **სულ 52 MCP arsenal:** 23 registry + 19 GitHub + 5 AI-Pulse + 5 custom

---

## 4️⃣ მოქმედება — ვინ წერს ანალიზს და უგზავნის ოჯახს

ანალიზის შემდეგ **Communicator აგენტი** + **`compose_bilingual`** (Claude-ის
strict tool_use) წერს **ორენოვან {en, ka}** ტექსტს, შემდეგ აგზავნის:

| არხი | რას აგზავნის | ენა |
|---|---|---|
| **📄 Weekly Brief / Manager Briefing** | ReportLab PDF, **კვირას 09:00 ET** | ორივე |
| **Telegram Bot** | push + `ask_user` + Whisper ხმოვანი intake | ქართული (`.ka`) |
| **Gmail MCP** | digest + ექიმთან outreach (compose-only OAuth) | ინგლისური (`.en`) |
| **Notion MCP** | ოჯახის knowledge base (96 contacts) | — |
| **Google Calendar** | მკურნალობის timeline (vigabatrin washout, Duke EAP) | — |
| **Booking / Kiwi** | Duke EAP მგზავრობა (Tbilisi ↔ Boston ↔ Durham) | — |

> 🔒 შეტყობინებებში **PHI არასოდეს** გადის — PHI redactor ფილტრავს.

---

## 5️⃣ პორტალი — რას ხედავს ოჯახი და ექიმი

ეს არის **ვებ-საიტი** (Next.js, ორენოვანი, Vercel-ზე). **24 გვერდი**,
დაჯგუფებული 6 კატეგორიად:

### 👨‍👩‍👧 ოჯახის ყოველდღიური
`today` (დღეს) · `dashboard` (მთავარი კოკპიტი) · `timeline` (ქრონოლოგია) · `snapshot`

### 🧠 ციფრული ტყუპი (Bayesian)
`twin` (ტყუპის სტატუსი) · `drift` (რწმენის ცვლა) · `active-questions` (აქტიური კითხვები, EIG)

### 🔗 მიზეზობრიობა & სიმულაცია
`causal` (მიზეზობრივი გრაფი — DAG, 571 node) · `simulate` (სიმულაციის სტუდია — TVB, react-flow)

### 🔬 კვლევა & მტკიცებულება
`hypotheses` (ჰიპოთეზები) · `therapies` (თერაპიები) · `papers` (სტატიები) ·
`knowledge` (ცოდნა) · `evidence-map` (მტკიცებულების რუკა) · `cohorts` (კოჰორტები)

### 🧬 სამედიცინო 3D
`brain` — ✅ **NiiVue MRI viewer ცოცხალია** (Phase 11): client-side `.nii`/`.nii.gz`
loader `@niivue/niivue` 0.69-ით + drag-drop + ორენოვანი UI; brain_regions ცხრილი კონტექსტად.
React Three Fiber ანატომიური shells — 🔴 ჯერ არ არის (მომავალი).
> 🔒 **MRI მხოლოდ ბრაუზერში — არასოდეს სერვერზე** (loadFromFile, ატვირთვა არ ხდება; `check-no-remote-fetch` GREEN)

### 🛠 ოპერაცია & დაცვა
`alerts` (გაფრთხილებები) · `audit` (აუდიტის ჟურნალი) · `data-integrations` ·
`settings` (პარამეტრები) · `support` · `resources` · `how-it-works` (როგორ მუშაობს)

**Tech:** `app/[locale]/*` · next-intl (KA+EN) · Plotly · vis-network · react-flow

---

## ⚖️ კონსტიტუცია + უსაფრთხოება (ყველგან გავლებული)

ეს **ცალკე ფენა არ არის** — ეს არის "ნერვული სისტემა", რომელიც ყველაფერს
აკონტროლებს (Phase 7.5):

- **13 ხელშეუხებელი წესის ფიზიკური აღსრულება** — CSP headers, Next.js
  middleware, Postgres triggers + CHECK + RLS. სისტემა **ვერ** დაარღვევს წესს
  ტექნიკურად, არა მხოლოდ "დისციპლინით".
- **PHI redactor** (regex + ქართული suffix-glue) — პერსონალური მონაცემი არ გადის.
- **ბიუჯეტის hard-stop** — `check_daily_budget()` ყოველი LLM call-ის წინ. სულ **~$7–8 / $60 cap**.
- **panic_stop** · i18n parity middleware · override audit table · GitHub Actions CI gates.
- **89/89 cumulative verifier coverage** (Phase 1–6.1).

---

## 👨‍⚕️ ბოლო წერტილი — ექიმი იღებს გადაწყვეტილებას

> სისტემა მხოლოდ **აღმოაჩენს, აფასებს და ხსნის** — **არ ნიშნავს მკურნალობას.**
> ყველა სამედიცინო გადაწყვეტილებას **რეალური ექიმი** იღებს.
>
> პრინციპი: **„Unknown potential" — არა „limited outcomes".**
> MRI სტრუქტურული დაზიანება ≠ ფუნქციური ლიმიტი.

---

## 🔄 ერთი წინადადებით — სრული ნაკადი

> **n8n** ყოველ 6 სთ უშვებს **Crawl4AI/PubMed**-ს → სტატია იწერება
> **Neo4j + Qdrant + Supabase**-ში → **CrewAI 5 აგენტი (Claude Sonnet 4.5/4.6)**
> + **v7 ბაიესის/მიზეზობრივი ტვინი** აანალიზებს → **Communicator + compose_bilingual**
> წერს ორენოვან **Weekly Brief**-ს → **Telegram / Gmail / Notion** გადასცემს ოჯახს →
> **24-გვერდიანი Next.js პორტალი** აჩვენებს (MRI მხოლოდ ბრაუზერში) →
> ყველაფერს **კონსტიტუცია + ბიუჯეტი** აკონტროლებს → **ექიმი იღებს გადაწყვეტილებას.**

---

*განახლდა: 2026-05-31 · წყარო: CLAUDE.md + რეალური repo (`viewer/`, `agents/`, `mcp/`, `workflows/`)*
