# RUNBOOK — წითელი ღილაკი (kill-switch + ბიუჯეტი)

> ერთგვერდიანი მითითება. როცა რამე უცნაური ხდება — გახსენი ეს ფაილი ჯერ.

---

## 1. რა არის წითელი ღილაკი

ALEKSANDRA_BRAIN-ს ორი დამოუკიდებელი მცველი აქვს:

1. **Telegram `/stop`** — ხელით აჩერებ, როცა რაიმე უცნაურია
2. **ბიუჯეტის ჭერი** — ავტომატურად აჩერებს, თუ ხარჯი $1.50/დღეს გადააჭარბა

ორივეს ერთი ამოცანა აქვს: სანამ გავიგებთ რა ხდება, **გავაჩერო ყველაფერი.**

---

## 2. როგორ შევაჩერო ხელით (`/stop`)

1. გახსენი ოჯახის Telegram ჯგუფი
2. დაწერე: `/stop`
3. დაელოდე ~10 წამს
4. ბოტი დაგიწერს: „🛑 გავაჩერე ყველაფერი. გათიშული workflow-ები: N. შემდეგი cron ვერ გაეშვება."
5. თუ 60 წამში პასუხი არ მოვიდა → იხილე §6 „რა ვუყო, თუ /stop არ მუშაობს"

---

## 3. რა ხდება როცა `/stop`-ი მუშაობს

თანმიმდევრულად:

- ყველა აქტიური n8n workflow გადადის `Inactive` სტატუსზე → შემდეგი cron არ ეშვება
- Supabase-ის `runs` ცხრილში ჩაიწერება ერთი row: `{kind: "kill_switch", exit_status: "killed_by_panic_stop:telegram_/stop"}`
- Telegram-ში მოგვდის დასტური

**მნიშვნელოვანი:** `/stop` **არ** გათიშავს Supabase-ს, Neo4j-ს, Qdrant-ს — მონაცემები რჩება უსაფრთხოდ. გათიშავს მხოლოდ ავტომატიზაციას (n8n).

---

## 4. ხელახლა ჩართვა

`/stop`-ის შემდეგ სისტემა **არ ეშვება ავტომატურად.** ეს მიზანმიმართულია — გვინდა მშვიდად შევხედო რა მოხდა.

ხელახლა ჩასართავად:

1. გახსენი n8n dashboard (URL `.env`-ის `N8N_URL`-ში)
2. შედი → workflow-ების ჩამონათვალში
3. თითოეული რომელიც `Inactive` სტატუსზეა — დააწექი toggle-ს „Active"
4. გადაამოწმე: შემდეგ cron tick-ზე workflow ეშვება

თუ არ ხარ დარწმუნებული რომელი workflow უნდა ჩაირთოს — დაელოდე ექიმს/ტექნიკურს. სისტემა გათიშული მდგომარეობით უსაფრთხოა.

---

## 5. ბიუჯეტის ჭერი ($1.50/დღე)

n8n-ის `daily-budget-gate` workflow ყოველ 30 წუთში ერთხელ ამოწმებს:

- Supabase `runs.token_cost` rows since 00:00 UTC
- მხოლოდ `kind in (agent_run, fire_drill, llm_call)` rows ითვლება
- თუ პასუხი > $1.50:
  - Supabase `runs`-ში იწერება `kind='budget_lock'`
  - Telegram-ში მოგვდის წითელი შეტყობინება „🔴 ბიუჯეტი დაბლოკილია"
- ყველა Anthropic call code-side helper-ით ჯერ იძახებს `check_daily_budget()`-ს

შემდეგი დღის 00:00 UTC-ზე ჭერი ავტომატურად ნულდება (ახალი დღე, ახალი ხარჯი).

**მიმდინარე caveat (2026-05-16):** Phase 2.5A verifier ადასტურებს spend
instrumentation-ს, მაგრამ deployed n8n `daily-budget-gate`-ში JSON-body
expression bug ჯერ კიდევ ფიქსირდება. სანამ workflow owner არ დაადასტურებს
ცოცხალ fix-ს, `budget_lock` rows შეიძლება ისევ simulator/fire-drill გზით
იყოს დასამოწმებელი. Code-side `check_daily_budget()` guard მაინც აქტიურია.

### ჭერი წითლდება — რა ვუყო

1. Supabase-ში ნახე დღევანდელი `runs` rows: `agent_run`, `fire_drill`, `llm_call`
2. პარალელურად გადაამოწმე Anthropic Usage Dashboard: console.anthropic.com → Usage
3. იპოვე რომელი workflow ან agent loop-ი ხარჯავს ზედმეტად
4. დაგვიკავშირდი ან ხელით გათიშე ის workflow n8n-ში
5. ხელახლა ჩასართავად — დაელოდე 00:00 UTC-ს

---

## 6. რა ვუყო, თუ `/stop` არ მუშაობს

თუ 60 წამში პასუხი არ მოვიდა:

**A. შემოწმე Telegram bot-ის სტატუსი**

- BotFather-ში → `/mybots` → ჩვენი ბოტი → ჩართულია?
- ბოტი არის ოჯახის ჯგუფში? Admin?

**B. გათიშე n8n პირდაპირ**

- გახსენი n8n dashboard
- Settings → API → დააწექი `Disable all workflows` (თუ ვერსიაში არის) ან თითოეული workflow-ი ხელით `Inactive`

**C. გათიშე Railway deployment (ბირთვი)**

- Railway dashboard → ALEKSANDRA_BRAIN პროექტი → n8n service
- დააწექი `Stop` ღილაკს
- ეს გაათიშავს n8n-ს მთლიანად, ყველა workflow ცდელობას შეწყვეტს

**D. გათიშე Anthropic API key**

- console.anthropic.com → API Keys → შეცვალე main key-ის სტატუსი → `Revoke`
- ეს ნიშნავს რომ ნებისმიერი მცდელობა, ვინც კიდევ უშვებს workflow-ს, ვერ მიიღებს პასუხს
- შემდეგ ხელახლა იქმნება ახალი key და `.env`-ში იცვლება

---

## 7. გადაამოწმე ერთხელ თვეში

Fire drill-ი ერთხელ თვეში — გავიდე ცხოვრებაში ერთხელ:

1. დაუგზავნე Telegram-ში `/stop`
2. დარწმუნდი რომ 60 წამში ჩერდება
3. ხელახლა ჩართე n8n-ში
4. ჩასვი ეს ანგარიში `docs/PHASE_0_EXIT_REPORT.md`-ში

თუ ერთხელ ცეცხლი ნამდვილად დაიწყო — ეს იყო ჩვენი ერთადერთი დაცვა.

---

*დაკავშირებული ფაილები:*
- [mcp/panic_stop.py](../mcp/panic_stop.py) — kill-switch implementation
- [workflows/daily-budget-gate.json](../workflows/daily-budget-gate.json) — ბიუჯეტის ჭერი
- [scripts/fire_drill.py](../scripts/fire_drill.py) — ვარჯიშის სკრიპტი
