# Migration 011 — Diff Review (Phase 5 Day 1) · შენი ნებართვაა საჭირო

**თარიღი:** 2026-05-17
**ფაილი:** [scripts/migrations/011_manager_actions_and_intake_drops.sql](../scripts/migrations/011_manager_actions_and_intake_drops.sql)
**ტესტი:** [tests/test_migration_011_manager.py](../tests/test_migration_011_manager.py) — 8 ცალი test case
**Status:** ⏸ **გადახედვის ლოდინი** — production-ში ჯერ არ გავუშვებ
**მოქმედება საჭიროა:** შენი "ვამტკიცებ migration 011" ან "შეცვალე ეს-ეს" → შემდეგ ვუშვებ migration-ს

---

## TL;DR ქართულად (1 პუნქტი)

ვამატებთ **ორ ახალ ცარიელ ცხრილს** — `intake_drops` (BRAIN პანელში ჩამოგდებული ფაილები/ხმა/ტექსტი) და `manager_actions` (ყოველი მოქმედება რასაც BRAIN ქმნის შენი სახელით). ერთიც და მეორეც PHI-redactor-ის უკან არის: უსაფრთხო ფილტრის გარეშე **ვერც ერთი ხაზი ვერ ჩაიწერება** (DB-level CHECK constraint აიძულებს). ძველი ცხრილებიც, ძველი ტრიგერებიც, ძველი workflow-ებიც **ხელუხლებელია** — Phase 0/1/2/3/4-ის არცერთი ნაკადი არ ირღვევა.

ერთი წინადადებით: "Phase 5-ის audit trail-ის საფუძველი — ვამატებთ ცარიელ მაგიდებს, ვერაფერს ვუცვლით ძველს".

---

## რას ცვლის

### 1. ცხრილი 1 — `intake_drops` (Phase 5 ფაილების ჟურნალი)

ყოველი ფაილი/ფოტო/ხმოვანი ჩანაწერი/ემაილი/ტექსტი რომელსაც BRAIN პანელში ჩავუშვებ — ერთი row აქ.

```sql
CREATE TABLE intake_drops (
  id                  UUID PRIMARY KEY,
  manager_user_id     TEXT NOT NULL,             -- შენი hardcoded id env-დან
  input_type          TEXT NOT NULL,             -- pdf | photo | voice | email | text
  filename            TEXT,
  r2_artifact_path    TEXT,                       -- Cloudflare R2-ში cold copy
  content_hash        TEXT,                       -- dedup-ისთვის
  raw_content         TEXT,                       -- REDACTED ტექსტი
  parsed_entities     JSONB,                     -- დასიშფრული მონაცემები
  proposed_actions    JSONB,                     -- რა შემოგთავაზებს BRAIN
  status              TEXT DEFAULT 'pending',    -- pending|approved|rejected|applied|expired
  phi_redacted        BOOLEAN DEFAULT FALSE,     -- ⚠ CHECK = TRUE აიძულებს
  redactions_count    INTEGER DEFAULT 0,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  resolved_at         TIMESTAMPTZ
);
```

**უსაფრთხოების ბურჯი:** `CONSTRAINT intake_drops_must_redact CHECK (phi_redacted = TRUE)`. თუ apppligation-ი ცდის რომ ჩაწეროს row რომელშიც `phi_redacted=FALSE`, **PostgreSQL უარყოფს**. ეს იგივე pattern-ია რასაც Phase 3-ში `outreach_log`, `alerts_log` და `briefs` ცხრილებზე გვაქვს.

**ინდექსები (3):**
- `idx_intake_drops_manager_created` — შენი drop-ების ჟურნალის სიჩქარისთვის
- `idx_intake_drops_pending` — მხოლოდ pending drop-ები (partial)
- `idx_intake_drops_content_hash` — dedup ჩარჩო

---

### 2. ცხრილი 2 — `manager_actions` (BRAIN-ის ყოველი მოქმედების ჟურნალი)

ყოველი update/insert/draft რომელსაც BRAIN სცემს შენი სახელით — **ერთი row აქ**. `before_payload` და `after_payload` ინახავს მონაცემს undo-სთვის.

```sql
CREATE TABLE manager_actions (
  id                  UUID PRIMARY KEY,
  manager_user_id     TEXT NOT NULL,
  action_type         TEXT NOT NULL,     -- create|update|draft_email|add_event|add_milestone|
                                         -- add_contact|log_pattern|dismiss|apply_intake_drop|reverse
  target_table        TEXT NOT NULL,
  target_record_id    UUID,
  before_payload      JSONB,             -- რა იყო update-ამდე
  after_payload       JSONB,             -- რა გახდა update-ის შემდეგ
  source_input        TEXT,              -- voice|pdf|photo|email|text|api|briefing
  source_metadata     JSONB,
  intake_drop_id      UUID REFERENCES intake_drops(id),   -- FK provenance
  approved_at         TIMESTAMPTZ,
  reversed_at         TIMESTAMPTZ,       -- undo დადგა → ეს დროა
  reversed_by         TEXT,
  created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

**Undo contract (Phase 5 plan §"Day 5"):**
- მხოლოდ ბოლო 30 row და მხოლოდ ბოლო 24 საათში შესაძლებელია undo.
- Undo ქმნის **ახალ** row-ს `action_type='reverse'`-ით; ორიგინალ row-ს უსვამს `reversed_at`-ს.
- Double-undo შეუძლებელია (ერთხელ რომ `reversed_at` დადგა — დადგა სამუდამოდ).
- რევერსირებული მოქმედებები **სამუდამოდ** რჩება queryable (immutable trail).

**ინდექსები (3):**
- `idx_manager_actions_manager_created` — შენი activity feed-ის სიჩქარისთვის
- `idx_manager_actions_undoable` (partial: `reversed_at IS NULL`) — undo-window query-ის ჩარჩო. ⚠ 24 საათის filter-ი query-დან მოდის რადგან `now()` volatile არ შეიძლება partial index-ში
- `idx_manager_actions_intake_drop` (partial: `intake_drop_id IS NOT NULL`) — drop → action უკუ-მიდევნება

---

### 3. RLS — Row-Level Security

ორივე ცხრილზე იგივე pattern რაც migration 008-ში:

```sql
CREATE POLICY ..._service_all  FOR ALL    TO service_role     USING (true) WITH CHECK (true);
CREATE POLICY ..._family_read  FOR SELECT TO authenticated    USING (true);
```

ანონ ცდილობა (apikey გარეშე) — **rows ვერ ნახავს**. სერვისი (service_role key) — სრული წვდომა. ოჯახის წევრი (authenticated user, თუ ოდესმე ექნება) — მხოლოდ READ.

⚠ **მნიშვნელოვანი:** Phase 5 hardcoded `manager_user_id` env-დან მუშაობს. Supabase Auth ცხრილს არ ვაკოპირებთ (`auth.users` ცარიელია Phase 0-4-ში). ეს ნიშნავს რომ "var-მა მისცემს დანახულობას ვის რას" — application-side filter-ი, არა DB-side. ერთი ოპერატორი ვართ ახლა, ერთი ოპერატორი ვიქნებით Phase 5-ში.

---

### 4. Trigger-ი — **არც ერთი ცვლილება**

`runs.block_runs_mutation` (migration 009) **ხელუხლებელია**. `manager_actions` და `intake_drops` განცალკევებული ცხრილებია; მათ append-only protection არ აქვთ, რადგან Phase 5-ის ნაკადი `status` ცვლის (pending → approved → applied) და `reversed_at`-ს უსვამს. ეს მუტაცია **გათვალისწინებულია**.

`runs` ცხრილი **არ ეხება**. Phase 0 FND-04, Phase 4 OBS-01-ის გეიტი **არ ირღვევა**.

---

## რას არ ცვლის

✅ `runs` — ხელუხლებელია
✅ `papers`, `therapies`, `hypotheses`, `contacts`, `outreach_log`, `alerts_log`, `briefs` — ხელუხლებელია
✅ `aleksandra_timeline`, `evidence_ledger`, `kv_state`, `paper_chunks` — ხელუხლებელია
✅ Triggers — `block_runs_mutation` ისეთივეა როგორი იყო migration 009-ის შემდეგ
✅ Workflows (n8n) — ხელუხლებელია; weekly_brief, daily_digest, daily_spend_report, outreach_review_queue ისე მუშაობს როგორც Phase 4 Step B-ში
✅ Pre-existing RLS policies — ხელუხლებელია, თუ უკვე `*_service_all` + `*_family_read` pattern-ში არიან

---

## რას ვერ შემოვა Phase 5 აპლიკაციაში

❌ **Medication dose change** — entity router (Day 4) ვერც-არასდროს ვერ auto-apply-ს. მხოლოდ preview card + შენი click "Apply"
❌ **Drug name change** — იგივე, NEVER auto
❌ **Auto-send email** — yet again NEVER. Gmail draft-ი ხდება, თვითონ send-ი არ ხდება
❌ **Raw audio storage** — ხმოვანი ჩანაწერი **არასოდეს არ ინახება**; Whisper transcribe-ი → redacted text → drop, ხოლო ბაიტები მეხსიერებიდან ქრება

---

## Apply-ი როგორ ხდება

```bash
# 1. შენი approval ჯერ
# 2. შემდეგ ვუშვებ:
psql "$SUPABASE_DB_URL" -f scripts/migrations/011_manager_actions_and_intake_drops.sql

# 3. შემდეგ smoke test:
curl -s -H "apikey: $SUPABASE_ANON_KEY" \
  "$SUPABASE_URL/rest/v1/manager_actions?select=id&limit=1"
# მოლოდინი: HTTP 401 ან ცარიელი body 200 — NEVER row

curl -s -H "apikey: $SUPABASE_ANON_KEY" \
  "$SUPABASE_URL/rest/v1/intake_drops?select=id&limit=1"
# მოლოდინი: HTTP 401 ან ცარიელი body 200

# 4. შემდეგ test suite:
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_migration_011_manager.py -v
# მოლოდინი: 8 PASS
```

---

## თუ რამე ცუდად წავიდა

Rollback სკრიპტი ფაილის ბოლოშია, comment-ში. ცხრილების სრული წაშლა:

```sql
DROP TABLE IF EXISTS manager_actions;
DROP TABLE IF EXISTS intake_drops;
```

ვინაიდან Phase 5 ცხრილებში **არცერთი production-data არ წერია ჯერ** (Day 1-ის სცენარია), rollback სრულიად რისკ-უფასოა.

---

## დღევანდელი ცარიელი test result-ი

Migration 011 ჯერ არ applied — pytest skips:

```
tests/test_migration_011_manager.py:: 8 skipped
```

Apply-ის შემდეგ:

```
tests/test_migration_011_manager.py:: 8 passed
```

---

## შენი ვერდიქტი

გადახედე ფაილს `scripts/migrations/011_manager_actions_and_intake_drops.sql` და დაწერე:

- **"ვამტკიცებ migration 011"** → ვაპლაი ვუშვებ ეტაპობრივად:
  1. `psql` migration apply (idempotent, BEGIN/COMMIT ერთი transaction-ი)
  2. anon smoke test (4 curl)
  3. pytest 8/8
  4. `verify_phase5.py --mode code-complete` — MNG-01 + MNG-12 უნდა იყოს GREEN
  5. Day 1 commit (atomic)

- **"შეცვალე X"** → ცვლილებები + ხელახლა გადახედვა.

- **"გადადე"** → migration ფაილს ვტოვებ რეპოში; tests RED დარჩება; Day 1 commit ცხრილების apply-ის გარეშე ვერ ხდება. Day 2 დაიწყება ცარიელი ცხრილების გარეშე → blocker.
