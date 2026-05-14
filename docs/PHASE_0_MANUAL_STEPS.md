# Phase 0 — ხელით სამუშაო (ბრაუზერი + Wallet)

> კოდი + სქემები უკვე ჩაწერილია repo-ში. ეს ფაილი — სია, **რას ვაკეთებთ ბრაუზერში
> და რომელ სერვისებში ვრეგისტრირდებით**, რათა Phase 0 ცოცხალი გახდეს.
>
> სავარაუდო დრო ერთჯერადი setup-ისთვის: **3-4 საათი** (განაწილებული 2-3 დღეზე).

---

## 0. წინაპირობები

ერთხელ:

- [ ] **Node.js 20+** დაყენებული: https://nodejs.org → LTS
- [ ] **Python 3.11+** დაყენებული: https://python.org
- [ ] **Docker Desktop** დაყენებული: https://docker.com/products/docker-desktop
- [ ] **Git** დაყენებული: https://git-scm.com
- [ ] **GitHub account** მზადაა: github.com (`jincharadzeshako` — უკვე გვაქვს)
- [ ] **ერთი ბანკის ბარათი** ხელთ რომელიც $5-50/თვის გადარიცხვას აანალოგებს — Railway-სთვის

ლოკალური repo-ს setup:

```bash
# 1. dependencies
pip install -r requirements.txt
npm install

# 2. pre-commit hooks (FND-07)
pip install pre-commit
pre-commit install

# 3. გადააკოპირე .env.example → .env (ცარიელი key-ებით)
cp .env.example .env
```

---

## 1. Supabase project (FND-05, OBS-01)

**ლინკი:** https://supabase.com/dashboard

1. „Start your project" → GitHub-ით login
2. „New project":
   - **სახელი:** `aleksandra-brain`
   - **Region:** `us-east-1` (Boston-ის ახლოს)
   - **DB password:** დააგენერირე ძლიერი, შეინახე 1Password-ში
3. დაელოდე 2 წუთს — პროექტი მზადდება
4. Settings → API → დააკოპირე `.env`-ში:
   - `Project URL` → `SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_URL`
   - `anon public key` → `SUPABASE_ANON_KEY` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `service_role key` → `SUPABASE_SERVICE_ROLE_KEY`
5. Settings → Database → Connection string → URI → დააკოპირე → `SUPABASE_DB_URL`
6. ლოკალურად გაუშვი migration-ი:
   ```bash
   bash scripts/migrate.sh
   ```
   ბოლოს უნდა ნახო: `✓ migrations applied successfully`

**ვერიფიკაცია:** Supabase Table Editor-ში ხედავ 11 ცხრილს (10 schema.sql-დან + 1 `runs`).
→ დაწვრილებით: [RUNBOOK-supabase.md](RUNBOOK-supabase.md)

---

## 2. Telegram bot (FND-03)

**ლინკი:** https://t.me/BotFather

1. გახსენი @BotFather Telegram-ში
2. `/newbot` → დასახელება: `Aleksandra Brain` → username: `aleksandra_brain_bot` (ან მსგავსი ხელმისაწვდომი)
3. დააკოპირე bot token → `.env` → `TELEGRAM_BOT_TOKEN`
4. შექმენი ან გახსენი ოჯახის ჯგუფი → დაამატე ბოტი
5. ჯგუფში დაწერე ერთი მესიჯი (მაგ. „test")
6. ბრაუზერში გახსენი:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
   იპოვე `"chat":{"id":-1001234567890,...}` — ეს number-ი → `.env` → `TELEGRAM_CHAT_ID`
7. ბრაუზერში გახსენი:
   ```
   https://api.telegram.org/bot<TOKEN>/setMyCommands?commands=[{"command":"stop","description":"halt all running agents"}]
   ```

**ვერიფიკაცია:** ჯგუფში დაწერე `/stop` — ბოტი (ჯერ არ უპასუხებს, ეს n8n setup-ის შემდეგ მუშაობს, §4)

---

## 3. Anthropic API (`ANTHROPIC_API_KEY` + Admin key)

**ლინკი:** https://console.anthropic.com

1. Sign up GitHub-ით
2. Settings → API Keys → „Create Key" → სახელი: `aleksandra-brain-main`
   - დააკოპირე → `.env` → `ANTHROPIC_API_KEY`
3. Settings → API Keys → „Admin Keys" → „Create Admin Key" → სახელი: `aleksandra-brain-usage-readonly`
   - დააკოპირე → `.env` → `ANTHROPIC_USAGE_API_KEY`
4. Billing → დაამატე $5 prepaid (test-ისთვის)

**ვერიფიკაცია:** ლოკალურად:
```bash
python -c "import os; from anthropic import Anthropic; print(Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY')).messages.create(model='claude-haiku-4-5-20251001', max_tokens=8, messages=[{'role':'user','content':'hi'}]).content[0].text)"
```
უპასუხებს „Hello" ან მსგავსს → ✅

---

## 4. n8n on Railway (FND-04)

**ლინკი:** https://railway.app

1. Sign up GitHub-ით
2. „New Project" → „Deploy from template" → მოძებნე „n8n"
3. ან: „Empty project" → „New Service" → „Docker Image" → `n8nio/n8n:latest`
4. ცვლადები (Variables):
   ```
   N8N_BASIC_AUTH_ACTIVE=true
   N8N_BASIC_AUTH_USER=admin
   N8N_BASIC_AUTH_PASSWORD=<strong-password>
   N8N_HOST=<railway-generated-domain>.up.railway.app
   N8N_PROTOCOL=https
   WEBHOOK_URL=https://<railway-domain>
   ```
5. ცვლადები ჩვენი workflow-სთვის:
   ```
   TELEGRAM_BOT_TOKEN=<იგივე .env-დან>
   TELEGRAM_CHAT_ID=<იგივე .env-დან>
   DAILY_BUDGET_USD=1.50
   ```
6. Deploy → მიიღე public URL → `.env` → `N8N_URL`
7. Deploy-ის შემდეგ n8n UI-ში: Settings → API → „Create new API key" →
   სახელი: `aleksandra-brain` → დააკოპირე → `.env` → `N8N_API_KEY`

### 4a. daily-budget-gate workflow import

n8n UI-ში:

1. Workflows → „Import from File" → ატვირთე `workflows/daily-budget-gate.json`
2. გახსენი workflow → „Anthropic Usage" node → Credentials → "Create new"
   - Auth type: Header Auth
   - Name: `x-api-key`
   - Value: `ANTHROPIC_USAGE_API_KEY`-ი (sk-ant-admin-...)
3. "Active" toggle → ჩართე
4. „Execute Workflow" → ერთხელ გაუშვი ხელით

**ვერიფიკაცია:** n8n-ში Execution log-ში ხედავ რომ workflow გადის. Telegram-ში
შეტყობინება არ მოდის (რადგან $0.00 < $1.50).

### 4b. panic_stop daemon

ლოკალურად სცადე:

```bash
python -m mcp.panic_stop --listen
```

გადაერთვა „Listening for /stop ..." რეჟიმში. Telegram-ში დაწერე `/stop` —
უნდა ნახო terminal-ში „[YYYY-MM-DD HH:MM:SS] /stop received" + Telegram-ში
„🛑 გავაჩერე ყველაფერი" შეტყობინება.

**მუდმივი ჩართვისთვის:** Railway-ზე ცალკე Python service-ად deploy-ის ან n8n-ის
Telegram trigger node-ით (Phase 1-ში გადააქცევთ).

---

## 5. Neo4j AuraDB Free (Phase 0-ში მზადება)

**ლინკი:** https://neo4j.com/cloud/aura-free/

> შენიშვნა: Neo4j Phase 0-ის სავალდებულო კომპონენტი არ არის, მაგრამ Phase 2-ში
> კრიტიკულია. ახლავე setup-ის გაკეთება ერთიანი onboarding-ის ნაწილია.

1. „Start Free" → GitHub login
2. „Create Free Instance" → version: 5 → name: `aleksandra-brain`
3. დააკოპირე Connection URI, Username (default `neo4j`), Password
4. `.env`-ში:
   ```
   NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=<from console>
   ```

**ვერიფიკაცია:**
```bash
python -c "from neo4j import GraphDatabase; import os; d=GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USERNAME'), os.getenv('NEO4J_PASSWORD'))); d.verify_connectivity(); print('OK')"
```

---

## 6. Qdrant (Phase 0-ში მზადება)

ლოკალურად Docker-ით:

```bash
docker compose up qdrant -d
```

ბრაუზერში: http://localhost:6333/dashboard → ხედავ UI-ს? ✅

`.env`-ში default-ად ნათქვამია:
```
QDRANT_URL=http://localhost:6333
```

---

## 7. Cloudflare R2 (Phase 1-ში პირველად, ახლა setup)

**ლინკი:** https://dash.cloudflare.com

1. Sign up → email + password
2. R2 Object Storage → „Get Started" → დაამატე payment method (free tier-ში 10 GB)
3. „Create bucket" → name: `aleksandra-brain-storage` → region: ENAM (eastern North America)
4. R2 → Settings → API Tokens → „Create API Token" → name: `aleksandra-brain` →
   permissions: Object Read & Write → TTL: 1 year
5. `.env`-ში:
   ```
   CLOUDFLARE_ACCOUNT_ID=<from dashboard right sidebar>
   CLOUDFLARE_R2_ACCESS_KEY_ID=<from token>
   CLOUDFLARE_R2_SECRET_ACCESS_KEY=<from token>
   CLOUDFLARE_R2_BUCKET=aleksandra-brain-storage
   ```

---

## 8. GitHub Actions ჩართვა

GitHub repo-ში:

1. Settings → Actions → General → „Allow all actions"
2. Settings → Secrets and variables → Actions → დაამატე:
   - `ANTHROPIC_USAGE_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - (და სხვა მგრძნობიარე ცვლადები)

ეს ცვლადები CI-ის pipeline-ში ხელმისაწვდომი ხდება, **მაგრამ არცერთი ცვლადი
git-ში არ ჩანს**.

---

## 9. Fire drill (Phase-exit gate)

ყველაფერი setup-ის შემდეგ — fire drill:

```bash
# A. Telegram /stop drill
python -m scripts.fire_drill --telegram
# (გადახედე terminal-ში დაწერილ instruction-ს და გადადი Telegram-ში /stop-ის გასაგზავნად)

# B. Budget gate drill
# n8n-ში → daily-budget-gate → variables → BUDGET_LOCKED → ხელით „true"
python -m scripts.fire_drill --budget
```

ორივე უნდა გაჩერდეს 60 წამში. შედეგი ჩაწერე [PHASE_0_EXIT_REPORT.md](PHASE_0_EXIT_REPORT.md)-ში.

---

## 10. დასასრულს — ფაზის გადახურვა

თუ `PHASE_0_EXIT_REPORT.md`-ში ყველა 8/8 checkbox მწვანეა:

```bash
git add docs/PHASE_0_EXIT_REPORT.md
git commit -m "docs(phase-0): exit report signed — Phase 0 closed"
git push

# გადადი Phase 1-ის დაგეგმვაზე
/gsd:plan-phase 1
```

---

## დასახმარებლად

- კოდის გასაგებად: [docs/PHASE_0_PLAN.md](PHASE_0_PLAN.md) — წინა ვერსიის ნარატივი
- ბრძანებების reference: [docs/PHASE_0_HANDOUT.md](PHASE_0_HANDOUT.md) — წინა ვერსიის ცხელი prompts
- ცეცხლის ჩამქრობი: [docs/RUNBOOK-kill-switch.md](RUNBOOK-kill-switch.md)
- Supabase: [docs/RUNBOOK-supabase.md](RUNBOOK-supabase.md)
- გეგმის შემუშავება: [.planning/PROJECT.md](../.planning/PROJECT.md), [.planning/REQUIREMENTS.md](../.planning/REQUIREMENTS.md), [.planning/ROADMAP.md](../.planning/ROADMAP.md)

---

*ბოლო განახლება: 2026-05-13 — Phase 0 ფაილების შემოწმება დასრულდა, ფიზიკური setup დაიწყება.*
