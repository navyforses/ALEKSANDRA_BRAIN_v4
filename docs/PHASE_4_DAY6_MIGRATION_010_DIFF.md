# Migration 010 — Diff Review (Day 6 addendum) · შენი ნებართვის ლოდინში

**თარიღი:** 2026-05-17
**ფაილი:** [scripts/migrations/010_delivery_originating_run_id.sql](../scripts/migrations/010_delivery_originating_run_id.sql)
**კონტექსტი:** Migration 009 დაიდო `runs.digest_id` (forward pointer) — მაგრამ verify_phase4 OBS-02 ელის backward pointers (`alerts_log.originating_run_id` და სხვ.). სტრუქტურულად backward უფრო სწორია: ერთი agent run შეიძლება ბადებდეს რამდენიმე delivery-ს.
**Status:** ⏸ **შენი approval-ის ლოდინში** — production-ში ჯერ არ ვუშვებ
**მოქმედება საჭიროა:** "ვამტკიცებ migration 010"

---

## TL;DR — 1 აბზაცი

სამივე delivery ცხრილს (`alerts_log`, `outreach_log`, `briefs`) ვუმატებთ ერთ ნულობად სვეტს `originating_run_id UUID REFERENCES runs(id)`. ეს არის backward FK — ყოველი message/draft/brief აქედან მიუთითებს runs row-ზე, რომელმაც გამოაცა. სვეტი INSERT-ის დროს იწერება, არასოდეს არ იცვლება — ანუ append-only invariant-ი ცხრილებზე უცვლელია. სრულდება Phase 4 OBS-02 contract: "ყოველი მიწოდებული digest იცის ვინ შექმნა, 2 click-ის სიშორეზე".

---

## რას ცვლის ცხრილოვნად

| ცხრილი | ცვლილება | რა გვაძლევს |
|---|---|---|
| `alerts_log` | + `originating_run_id UUID FK → runs(id)`, + partial index | ყოველი Telegram მესიჯი იცის რომელ run-მა გამოაცა |
| `outreach_log` | + `originating_run_id UUID FK → runs(id)`, + partial index | ყოველი Gmail draft იცის რომელ run-მა შექმნა |
| `briefs` | + `originating_run_id UUID FK → runs(id)`, + partial index | ყოველი Weekly Brief PDF იცის რომელი weekly_brief_trigger იყო |

FK constraint აქვს `ON DELETE RESTRICT` — runs row-ის წაშლა ვერ მოხდება სანამ მისი back-references არსებობს (და DELETE on runs უკვე blocked-ია trigger-ით, ანუ ეს double-belt-and-braces დაცვაა).

---

## რატომ უსაფრთხოა

| საფრთხე | დაცვა |
|---|---|
| სვეტი retroactively iqcvleba ვინმემ | append-only contract უცვლელია — `runs.digest_id` trigger ცხრილს ეხება, არა delivery ცხრილებს. მაგრამ delivery ცხრილებზე ჩვენი კოდი INSERT-ის დროს მხოლოდ ერთხელ წერს და არასოდეს არ ცვლის. RLS service_role-ისთვისაა, anon-მა ვერც წაიკითხავს |
| ისტორიული row-ები (გადაცემული Phase 4-ის Day 1-4 sprint-ის ფარგლებში) | NULL დარჩება — სვეტი nullable-ია, partial index `WHERE originating_run_id IS NOT NULL` მათ უგულებელყოფს. verifier-ი ეძებს last 7 days, ანუ ახალი row-ები ჩაითვლება. დღევანდელი state: ისე და ისე 0 prod deliveries არსებობს — backward fill არ გვჭირდება |
| FK ის ლოგიკურად აიძულებს runs-ის Delete-ი | DELETE on runs უკვე blocked-ია trigger-ით (OBS-01). FK მხოლოდ double-confirms |

---

## ტესტი

გავაფართოვებ `tests/test_migration_009_trigger.py`-ს ან ცალკე ფაილში `tests/test_migration_010_backward_pointers.py` ჩავამატებ 4 ცალ test case-ი:

1. სამივე ცხრილს აქვს `originating_run_id` სვეტი
2. INSERT-ი `originating_run_id`-ის გარეშე ისევ მუშაობს (nullable)
3. INSERT-ი მცდარი (არ არსებული) `originating_run_id`-ით — FK constraint violation
4. INSERT-ი ვალიდური `originating_run_id`-ით — წარმატება + read-back

---

## Rollback გეგმა

ფაილის ბოლოს კომენტარშია სრული reverse SQL. სამივე ცხრილს თავის სვეტი + ინდექსი + FK constraint წაიშლება. Migration 009 უცვლელად რჩება — მისი strict trigger ისევ მუშაობს.

---

## განხორციელების ნაბიჯები (approval-ის შემდეგ)

1. `psql $SUPABASE_DB_URL -f scripts/migrations/010_delivery_originating_run_id.sql`
2. სვეტების verification: `\d alerts_log`, `\d outreach_log`, `\d briefs`
3. tests/test_migration_010_backward_pointers.py დაწერა + pytest run → 4/4
4. **3 Communicator patches:**
   - `scripts/communicator/telegram_sender.py` — `_insert_alerts_log(...)` ფუნქცია იღებს ახალ `originating_run_id` პარამეტრს, `dispatch()` უგზავნის
   - `scripts/communicator/gmail_digest.py` — outreach_log INSERT-ი იღებს `originating_run_id`
   - `scripts/communicator/weekly_brief.py` (ან sრvenever briefs row created) — briefs INSERT-ი იღებს `originating_run_id`
5. **caller patches:** `dispatch()` და სხვა wrappers რომელიც runs row-ს ქმნის → უგზავნის id-ი delivery layer-ს
6. Quick prod smoke: 1 fixture-სიდან Telegram dispatch → assert alerts_log.originating_run_id non-null
7. `verify_phase4 --gate obs-02` → GREEN expected
8. Full regression
9. Day 6 commit (migration 010 + tests + 3 communicator patches)

---

## ვადასტურებ?

- ✅ "ვამტკიცებ migration 010"-ი → ვუშვებ migration + Communicator patches
- 🟡 "შეცვალე X" → ცვლილება + მეორე review
- 🔴 "შეჩერდი" → rollback migration 009 + restart Day 6 designe
