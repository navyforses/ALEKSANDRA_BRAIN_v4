# RUNBOOK — Supabase setup & migrations

> როცა Supabase პროექტი იქმნება ან migration განახლდება — გახსენი ეს.

---

## 1. Supabase პროექტის შექმნა (ერთხელ, ხელით)

ეს ნაბიჯები საჭიროა მხოლოდ ერთხელ — Phase 0-ის დასაწყისში.

1. ბრაუზერში გახსენი https://supabase.com/dashboard
2. „Start your project" → GitHub-ით login (jincharadzeshako)
3. „New project":
   - **სახელი:** `aleksandra-brain`
   - **რეგიონი:** `us-east-1` (Boston-ის ახლოს)
   - **DB password:** გენერირე ძლიერი password და ჩაინიშნე უსაფრთხო ადგილას (1Password / paper)
4. დაელოდე 2 წუთს — პროექტი მზადდება
5. Settings → API → დააკოპირე სამი მნიშვნელობა:
   - `Project URL` → `SUPABASE_URL`
   - `anon public key` → `SUPABASE_ANON_KEY`
   - `service_role key` → `SUPABASE_SERVICE_ROLE_KEY` (**არასოდეს გაგზავნო ჩატებში!**)
6. Settings → Database → Connection string → URI → დააკოპირე → `SUPABASE_DB_URL`
   - ფორმატი: `postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres`

---

## 2. .env ფაილში ჩაწერა

`.env.example`-დან გადააკოპირე `.env` (ეს ფაილი არასოდეს commit-დება):

```bash
cp .env.example .env
```

გახსენი `.env` და შეცვალე:

```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
SUPABASE_DB_URL=postgresql://postgres:[your-pw]@db.xxxxx.supabase.co:5432/postgres

NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...
```

---

## 3. სქემის გაშვება (პირველად)

```bash
# Linux/Mac
./scripts/migrate.sh

# Windows PowerShell
bash scripts/migrate.sh
```

რას აკეთებს:

1. იღებს `SUPABASE_DB_URL`-ს `.env`-დან
2. `psql`-ით უკავშირდება ცოცხალ Supabase-ს
3. გაუშვებს `scripts/schema.sql`-ს (10 ცხრილი, pgvector, RLS, ფუნქციები, view-ები)
4. გაუშვებს ყველა `scripts/migrations/*.sql`-ს თანმიმდევრობით
   - `001_runs_append_only.sql` — Phase 0 OBS-01 runs ცხრილი

დასასრულს ბრძანების ხედვაში წერია:

```
✓ migrations applied successfully
```

---

## 4. ვერიფიკაცია (Phase 0 success criterion #4 + #6)

### 4.1 ცხრილების შემოწმება

Supabase dashboard → Table Editor → უნდა ხედავდე:

- 10 ცხრილი schema.sql-დან: papers, contacts, therapies, brain_regions, hypotheses, clinical_trials, relationships, discovery_reports, aleksandra_timeline, ingestion_log
- 1 ცხრილი migration-დან: **runs**

### 4.2 RLS-ის ცოცხალი ტესტი (FND-05)

Supabase dashboard → SQL Editor-ში გაუშვი:

```sql
-- 1. სცადე ცრუ anon role-ით (RLS უნდა გაგიგდოს)
SET LOCAL ROLE anon;
SELECT count(*) FROM papers;           -- expected: error ან 0 rows
SELECT count(*) FROM runs;             -- expected: 0 rows (no policy granted to anon)

-- 2. სცადე service_role-ით (უნდა გადიოდეს)
RESET ROLE;
SELECT count(*) FROM papers;           -- expected: ცარიელი ცხრილი = 0, მაგრამ შეცდომის გარეშე
```

### 4.3 runs ცხრილის append-only ტესტი (OBS-01)

SQL Editor-ში:

```sql
-- 1. INSERT — გადის
INSERT INTO runs (kind, agent_id, exit_status, end_time)
VALUES ('fire_drill', 'manual_test', 'completed', NOW());

-- 2. UPDATE — უარს ეუბნება
UPDATE runs SET exit_status = 'tampered';
-- expected: ERROR: runs is append-only: UPDATE rejected

-- 3. DELETE — უარს ეუბნება
DELETE FROM runs;
-- expected: ERROR: runs is append-only: DELETE rejected
```

თუ სამივე ისე იქცევა როგორც წერია → ✅ OBS-01 + FND-05 დასრულებულია.

---

## 5. შემდგომი migration-ების დამატება

ახალი ცვლილებისთვის:

1. შექმენი ფაილი `scripts/migrations/00X_short_description.sql`
2. დაიწყე `BEGIN;`, დაასრულე `COMMIT;`
3. გამოიყენე `CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ... IF EXISTS` რომ რეპეტიტიული გაშვებამ არ ჩავარდეს
4. გაუშვი ლოკალურად: `./scripts/migrate.sh --dry-run` → დაამოწმე ფაილის რიგი
5. გაუშვი: `./scripts/migrate.sh`
6. Commit + push

migration-ის ნომრები **არ ფიგურირდება ცოცხალ schema-ში** — supabase დიდი ნომრის ცხრილს არ ინახავს. რაც გვაქვს — ფაილური სისტემაა, რომელიც წავიკითხავ რომელი ფაილი გაშვებულია უკვე ისე, რომ `IF NOT EXISTS` / `IF EXISTS` ჩვენ მიერ მართულია.

---

## 6. რა ვუყო თუ migration ჩავარდა

`psql` შეცდომების ტიპები:

- **`relation "x" already exists`** — `IF NOT EXISTS`-ის გარეშე ცდილობ ცხრილის შექმნას. შესწორე SQL → ხელახლა გაუშვი.
- **`column "x" does not exist`** — სცადე ცხრილზე ვერ აღწერია ცვლადი. ნახე schema.sql რეფერენსად.
- **`relation does not exist: runs`** — schema.sql ჯერ არ გაშვებულა. გაუშვი `./scripts/migrate.sh` ნულიდან.
- **`permission denied`** — `.env`-ში `SUPABASE_DB_URL` არასწორად ჩაწერილია. გადაამოწმე password-ი.

---

## 7. RLS პოლისების სრულყოფა

`scripts/schema.sql`-ში 10 ცხრილზე RLS დაყენებულია, მაგრამ პოლისები **ცარიელია** — ანუ ნაგულისხმევად ყველაფერი დახურულია. პოლისების დამატება საჭიროა მაშინ, როცა აპლიკაცია იწყებს Supabase-თან მუშაობას (Phase 1+).

Phase 0-ში მხოლოდ `runs` ცხრილს აქვს მკაფიო პოლისები:

```sql
runs_family_read    → SELECT, TO authenticated, USING(true)
runs_service_write  → INSERT, TO service_role, WITH CHECK(true)
```

ანუ:
- **ოჯახის წევრი** (browser-ში login-ით) → უხილავს ყველა run-ი
- **service_role** (აგენტები, n8n, panic_stop) → შეუძლია INSERT
- **anon** (login-ის გარეშე) → ვერაფერი

---

*დაკავშირებული ფაილები:*
- [scripts/schema.sql](../scripts/schema.sql) — საფუძვლიანი 10 ცხრილი
- [scripts/migrations/001_runs_append_only.sql](../scripts/migrations/001_runs_append_only.sql) — Phase 0 OBS-01
- [scripts/migrate.sh](../scripts/migrate.sh) — wrapper
- [.env.example](../.env.example) — საჭირო ცვლადები
