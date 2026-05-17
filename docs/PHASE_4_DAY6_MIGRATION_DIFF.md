# Migration 009 — Diff Review (Day 6) · შენი ნებართვაა საჭირო

**თარიღი:** 2026-05-17
**ფაილი:** [scripts/migrations/009_runs_digest_id.sql](../scripts/migrations/009_runs_digest_id.sql)
**ტესტი:** [tests/test_migration_009_trigger.py](../tests/test_migration_009_trigger.py) — 9 ცალი test case
**Status:** ⏸ **გადახედვის ლოდინი** — production-ში ჯერ არ გავუშვებ
**მოქმედება საჭიროა:** შენი "ვამტკიცებ" ან "შეცვალე ეს-ეს" → შემდეგ ვუშვებ migration-ს

---

## TL;DR ქართულად (1 პუნქტი)

`runs` ცხრილს ვუმატებთ ერთ ახალ სვეტს `digest_id` და ერთსაც ვუცვლით append-only ტრიგერის ლოგიკას — **ისე, რომ უსაფრთხოება უფრო მაგრდება, არა სუსტდება**. DELETE ისევ აკრძალულია. UPDATE ისევ აკრძალულია. ერთადერთი ახალი რამ ნებადართულია: ნებისმიერ უკვე ჩაწერილ runs row-ს შეიძლება მიენიჭოს `digest_id` (NULL-დან რეალურ UUID-ად), მაგრამ **მხოლოდ ერთხელ** და **მხოლოდ ცალკე UPDATE-ად რომელიც სხვა არცერთ სვეტს არ შეცვლის**. ეს ცვლილება საჭიროა Phase 4-ის OBS-02 გეიტისთვის: ყოველი ოჯახამდე გადაცემული digest რომ მიუთითებდეს იმ agent run-ზე რომელმაც ის შექმნა.

ერთი წინადადებით: "runs ცხრილიდან ჯერ ცოცხლი ჩანაწერი არ ექვემდებარება მუტაციას — გარდა იმისა რომ ერთხელ შეიძლება დაუსვან წერილის id".

---

## რას ცვლის

### 1. ახალი სვეტი

```sql
ALTER TABLE runs ADD COLUMN IF NOT EXISTS digest_id UUID;
```

ნებადართულია NULL. დეფოლტი — NULL. ყოველი ახალი row თავიდანვე NULL-ით იწერება. რომელიც წერილში ნამდვილად მიდის (Telegram/Gmail/Notion), მხოლოდ ის ღებულობს `digest_id`-ს.

### 2. ორი ინდექსი

```sql
CREATE UNIQUE INDEX idx_runs_digest_id_unique ON runs(digest_id) WHERE digest_id IS NOT NULL;
CREATE INDEX idx_runs_digest_id_set ON runs(digest_id) WHERE digest_id IS NOT NULL;
```

პირველი — partial unique: ერთი delivery (e.g. erti Telegram message) მხოლოდ ერთ runs row-ს ეკუთვნის. ეს ხსნის concurrent-dispatch race-ს. მეორე — verify_phase4 OBS-02-ის ჩქარი ფილტრი.

### 3. ტრიგერის ლოგიკა — **ეს არის რეალური ცვლილება**

**ძველი:** ბრმად უარყოფს ნებისმიერ UPDATE ან DELETE:

```sql
CREATE OR REPLACE FUNCTION block_runs_mutation()
RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'runs is append-only: % rejected', TG_OP;
END;
$$ LANGUAGE plpgsql;
```

**ახალი:** პირობითი — DELETE ისევ ბრმად, UPDATE ნებადართულია **მხოლოდ** თუ:
- (a) `OLD.digest_id IS NULL` (ჯერ არ აქვს დაყენებული)
- (b) `NEW.digest_id IS NOT NULL` (რეალურ UUID-ს უსვამენ, არა NULL-ს)
- (c) **არცერთი სხვა სვეტი არ იცვლება** (`IS DISTINCT FROM` ყველა სხვა სვეტისთვის უნდა იყოს false)

თუ სამივე გავიდა — ნებადართულია. სხვა შემთხვევაში RAISE EXCEPTION.

სრული SQL [scripts/migrations/009_runs_digest_id.sql](../scripts/migrations/009_runs_digest_id.sql)-ში; აქ ვაჩვენებ მხოლოდ ცვლილების ცენტრს.

---

## რატომ უსაფრთხოა

| საფრთხე | ძველი დაცვა | ახალი დაცვა |
|---|---|---|
| ვინმე ცდილობს `runs.kind`-ის შეცვლას ისტორიის გასაყალბებლად | RAISE | RAISE (`column_X IS DISTINCT FROM column_X` მოწმდება) |
| ვინმე წერს `runs.token_cost` შემცირებაზე ბიუჯეტის გვერდის ავლის გასაკეთებლად | RAISE | RAISE |
| ვინმე ცდილობს runs row-ის წაშლას | RAISE | RAISE (DELETE ცალკეა გადამოწმებული) |
| ვინმე ცდის `digest_id`-ის გადაწერას (forge a different delivery) | N/A (column არ არსებობდა) | RAISE — `digest_id` უკვე დაყენებულია |
| ვინმე ცდის ერთდროულად `digest_id` + `exit_status` შეცვლას | N/A | RAISE — "only digest_id may be set" |
| ვინმე ცდის `digest_id`-ის ნელ-ნელად ჩამატებას NULL→UUID→სხვა UUID | N/A | RAISE — "digest_id already set on row …" |
| ორი დატაბაზიდან გადაცემული mesages იჩემებენ ერთსა და იმავე delivery-ს | N/A | UNIQUE INDEX → UniqueViolation |
| Application bug: უაზროდ უგზავნის digest_id=NULL ცარიელი UPDATE-ი | N/A | RAISE — "digest_id stayed NULL" |

**მთლიანი effect: append-only invariant უფრო მკაცრია, არა უფრო რბილი.** ერთადერთი მუტაცია რომელიც ნებადართულია არის "delivery happened" სიგნალის ერთჯერადი დაყენება.

---

## ტესტირება

ფაილი [tests/test_migration_009_trigger.py](../tests/test_migration_009_trigger.py) — 9 ცალი test case. ყოველი test ცოცხალ Supabase-ზე უკავშირდება ცალკე transaction-ში, რომელიც დაბოლოს rollback-ით იხურება — ცხრილში არცერთი test-row არ რჩება.

| # | Test | რას ამოწმებს |
|---|---|---|
| 1 | `test_01_insert_still_works` | ჩვეულებრივი INSERT ისევ მუშაობს |
| 2 | `test_02_delete_rejected` | DELETE ისევ uარყოფს |
| 3 | `test_03_ordinary_update_rejected` | UPDATE `exit_status`-ზე — uარყოფს |
| 4 | `test_04_one_shot_digest_id_allowed` | UPDATE digest_id NULL→UUID — ნებადართულია |
| 5 | `test_05_one_shot_with_other_column_change_rejected` | UPDATE digest_id + exit_status ერთად — uარყოფს |
| 6 | `test_06_double_digest_id_assignment_rejected` | მეორე UPDATE digest_id-ზე — uარყოფს |
| 7 | `test_07_clearing_digest_id_rejected` | UPDATE digest_id UUID→NULL — uარყოფს |
| 8 | `test_08_digest_id_unique` | ორი row ვერ მოითხოვს ერთსა და იმავე digest_id — UniqueViolation |
| 9 | `test_09_null_to_null_rejected` | UPDATE digest_id NULL→NULL — uარყოფს |

migration 009 უპლიკაციამდე ყველა test SKIP-ი — დააფიქსირებენ რომ `digest_id` სვეტი ჯერ არ არსებობს.

---

## Rollback გეგმა

თუ migration 009-ის გაშვების შემდეგ რამე გადახდის:

```sql
BEGIN;

-- migration 001 ფუნქცია უკან
CREATE OR REPLACE FUNCTION block_runs_mutation()
RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'runs is append-only: % rejected', TG_OP
    USING ERRCODE = 'P0001';
END;
$$ LANGUAGE plpgsql;

DROP INDEX IF EXISTS idx_runs_digest_id_set;
DROP INDEX IF EXISTS idx_runs_digest_id_unique;
ALTER TABLE runs DROP COLUMN IF EXISTS digest_id;

COMMIT;
```

ეს ფაილი ცოცხალია migration 009 SQL-ის ბოლოში კომენტარის სახით.

**მონაცემთა დაკარგვა:** rollback დაკარგავს ნებისმიერ უკვე ჩაწერილ `digest_id` მნიშვნელობას. delivery თვითონ (alerts_log, outreach_log) უცვლელი რჩება — ის ცალკე ცხრილებშია. ანუ rollback "ვიცი რომელი digest რომელ run-ით შეიქმნა"-ს დაკარგვაა, არა delivery-ის თვითონ.

---

## განხორციელების ნაბიჯები (შენი approval-ის შემდეგ)

1. ვუშვებ migration-ს:
   ```
   psql $SUPABASE_DB_URL -f scripts/migrations/009_runs_digest_id.sql
   ```
2. დაუყოვნებლივ ვადასტურებ ცვლილებებს:
   - სვეტი დაემატა: `SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='runs' AND column_name='digest_id';`
   - ფუნქცია განახლდა: `SELECT pg_get_functiondef('block_runs_mutation()'::regprocedure);`
   - ინდექსები შეიქმნა: `SELECT indexname FROM pg_indexes WHERE tablename='runs';`
3. ვუშვებ ტესტებს: `pytest tests/test_migration_009_trigger.py -v` → 9/9 PASS
4. ვაკეთებ patch-ი 3 ფაილში:
   - `scripts/communicator/telegram_sender.py` — `dispatch()` განვაახლებ რომ ჩაიწეროს alerts_log row-ის id-ი → runs.digest_id
   - `scripts/communicator/gmail_digest.py` — შესაბამისად outreach_log id
   - `scripts/communicator/notion_archiver.py` — შესაბამისად Notion page UUID
5. ვუშვებ `verify_phase4 --gate obs-02` → GREEN
6. ვუშვებ ყველა regression: phase 1-4 verifiers + pytest tests/
7. commit + push

---

## დაშავის რისკი

**ერთადერთი მაღალი რისკის ცვლილება ამ მთელ Phase 4 sprint-ში.** მიზეზი: ვცვლი OBS-01-ის core invariant-ს. თუ trigger-ის logic-ში ერთი edge case გამომრჩა, append-only contract უხილავად დაშავდება (production silently allowing UPDATE that shouldn't be allowed).

**Mitigation:**
1. 9 ცალი test case — Postgres-ის ცოცხალი ტრიგერით, არა mock-ით
2. Tests transaction-ში — არცერთი test-row არ რჩება ცხრილში
3. Rollback ერთი SQL block-ში მზადაა
4. Day 7-ში verifier-ში დავამატებ explicit append-only smoke (`UPDATE runs SET kind='x'` → expect RAISE)

---

## ვადასტურებ თუ?

გადახედე:
- [ ] SQL ფაილი ([scripts/migrations/009_runs_digest_id.sql](../scripts/migrations/009_runs_digest_id.sql))
- [ ] ტესტი ([tests/test_migration_009_trigger.py](../tests/test_migration_009_trigger.py))

თუ მოგწონს:
- ✅ "ვამტკიცებ migration 009"-ი → ვუშვებ

თუ რამის შეცვლა გინდა:
- 🟡 "შეცვალე X-ი" → ვწერ ცვლილებას + ვაცდი მეორე review-ს

თუ უარის თქმა გინდა:
- 🔴 "შეჩერდი" → ვათხუტყუნებ ფაილებს + ვწერ alternative plan
