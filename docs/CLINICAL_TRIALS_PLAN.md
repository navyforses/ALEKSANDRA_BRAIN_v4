# Clinical Trials Enrollment Board — გეგმა / Plan

> სტატუსი: **A + B ფაზა SHIPPED (code-complete) — 2026-06-15.**
> A: matcher + verifier + `/research/trials` (live on Vercel). seed 117 ctgov → **31 eligible / 28 needs-review / 58 ineligible**; verifier 6/6. commits `7b02fb4` + `8dc3fa4`.
> B: new-eligible Telegram alerts + status monitoring + matcher wired into perception_tick (6h) + clinical-trials section in Weekly Brief. commits `6095c33` + `cc87044`.
> Seed for a future GSD phase (mirrors how `docs/I18N_PLAN.md` seeded Phase 6).
> Author context: codebase research 2026-06-15 (two Explore passes over `viewer/` + `scripts/`).

---

## 1. მიზანი / Goal

ქართულად: კვლევების გვერდს ემატება **ქვე-გვერდი „სამედიცინო კვლევები"**, სადაც სისტემა აქვეყნებს **მხოლოდ ისეთ კლინიკურ კვლევებს (clinical trials), რომლებშიც ალექსანდრას ჩართვა შესაძლებელია**. ბოტი მუდმივად აკვირდება შესაბამის წყაროებს და ყოველკვირეულად ანახლებს სიას — აღწერით, დეტალებითა და ბმულებით.

> განსხვავება: არსებული „კვლევის" გვერდი = **სამეცნიერო ლიტერატურა** (papers/ანალიზი). ახალი ქვე-გვერდი = **ჩასართავი კლინიკური კვლევები** (trials).

EN: A `Clinical Trials` sub-page under the existing research route that surfaces **only clinical trials Aleksandra is eligible to enroll in**, continuously monitored and refreshed weekly with description, study detail, and provenance links.

**Core Value alignment:** "არასოდეს გამოგვრჩეს სანდო მკურნალობის lead." Enrollable trials are the highest-value lead type.

---

## 2. რა არსებობს უკვე / What already exists (good news)

| კომპონენტი | მდგომარეობა | ფაილი |
|---|---|---|
| ClinicalTrials.gov fetcher (recruiting only) | ✅ მუშაობს (6სთ-ში) | [scripts/fetch_ctgov.py](../scripts/fetch_ctgov.py) |
| `clinical_trials` ცხრილი (eligibility ველებით) | ⚠️ schema-ში არის, **ცარიელი / live-status გადასამოწმებელი** | [scripts/schema.sql](../scripts/schema.sql) L455–507 |
| RLS (family read / service write) | ✅ | [scripts/migrations/008_phase3_tables_and_rls.sql](../scripts/migrations/008_phase3_tables_and_rls.sql) L107–114 |
| viewer research list pattern | ✅ (mirror this) | [viewer/app/[locale]/research/page.tsx](../viewer/app/%5Blocale%5D/research/page.tsx), [viewer/lib/data.ts](../viewer/lib/data.ts) |
| Supabase server read helper `getRows()` | ✅ | [viewer/lib/supabase.ts](../viewer/lib/supabase.ts) |
| nav (`NAV` array) | ✅ | [viewer/components/shell/AppShell.tsx](../viewer/components/shell/AppShell.tsx) L23–29 |
| bilingual field helper `displayField()` | ✅ | [viewer/lib/i18n.ts](../viewer/lib/i18n.ts) |
| Weekly Brief loop (Sun 13:00 UTC) | ✅ | [scripts/communicator/weekly_brief.py](../scripts/communicator/weekly_brief.py), [workflows/weekly_brief.json](../workflows/weekly_brief.json) |
| Telegram alert primitive | ✅ | `_telegram()` in [scripts/perception_tick.py](../scripts/perception_tick.py) |

**ctgov fetcher already extracts** (into `evidence_ledger.payload_metadata` JSONB): `nct_id, title, official_title, overall_status, start_date, completion_date, phases, study_type, interventions[], min_age, max_age, sex, healthy_volunteers, locations_sample[]`, plus the `query` that surfaced it.

**Current QUERY_SETS** (already condition-targeted): Hypoxic Ischemic Encephalopathy · Infantile Spasms · Cerebral Palsy + (stem cell OR cord blood) · Neonatal Encephalopathy · Vigabatrin/infantile spasms.

### რა აკლია / Gaps to build
1. **Sync + eligibility matcher** — `evidence_ledger` (ctgov rows) → `clinical_trials` with computed eligibility.
2. **Viewer sub-page** `/research/trials`.
3. **Weekly refresh + alerts** wiring for trials specifically.

---

## 3. დადასტურებული გადაწყვეტილებები / Locked decisions

| # | კითხვა | პასუხი |
|---|---|---|
| D1 | მოცვა / filter | **მხოლოდ მკაცრად შესაფერისი** მთავარ სიაში (ასაკი + დიაგნოზი + recruiting + ლოკაცია გადის) |
| D1b | ბუნდოვანი შემთხვევები | ცალკე **„გადასამოწმებელი" (needs-review)** სექცია — lead არ იკარგება ჩუმად (Core Value) |
| D2 | გეოგრაფია | **აშშ + საერთაშორისო (მონიშნული)** — US prioritized, intl shown with a badge |
| D3 | შეტყობინება | **გვერდი + Telegram + ყოველკვირეული Brief** ახალ შესაფერის კვლევაზე |
| D4 | წყარო (MVP) | ClinicalTrials.gov (უკვე გაწიმ). EU CTR/სხვა → B ფაზის შემდგომ backlog |
| D5 | სამედ. გადაწყვეტილება | სისტემა **surface/rank/explain** — ჩართვას **ექიმი/ოჯახი** წყვეტს (ურღვევი წესი) |

**Eligibility status mapping** (`clinical_trials.aleksandra_status`):
- `identified` → passed all auto-checks → **main list**
- `evaluating` → ambiguous (e.g., unparseable age string, exclusion criteria we cannot parse) → **needs-review section**
- `ineligible` → clear disqualifier (age out of range, condition unrelated, no accessible site) → **hidden from page, kept in DB** with `eligibility_issues`

---

## 4. მონაცემთა მოდელი / Data model

ცხრილი `clinical_trials` უკვე არსებობს schema-ში სწორი ველებით. **Pre-flight (Task A0): დავადასტუროთ, რომ live DB-ში applied არის** (PostgREST `GET /rest/v1/clinical_trials?limit=1` → 200). თუ 404 (იხ. AGENTS.md ღია საკითხი #1), ჯერ migration უნდა გაეშვას.

გამოყენებული ველები:

```
nct_id (UNIQUE)        title              brief_summary
overall_status         phase              study_type
intervention_name      therapy_id (FK)
min_age  max_age        eligibility_criteria
locations (JSONB)       aleksandra_eligible (bool)
eligibility_issues (TEXT[])                aleksandra_status (enum)
pi_name pi_email coordinator_name coordinator_email
start_date estimated_completion last_updated
last_checked status_changed    created_at updated_at
```

ბილინგვური ველები (`title`, `brief_summary`, `eligibility_criteria`) ინახება `{en, ka}` JSONB-ად (იგივე pattern, რაც papers/therapies — migrations 026–027). **ახალი migration:** ამ 3 ველის `TEXT → JSONB` (თუ ჯერ TEXT-ია) + ka თარგმანის backfill.

---

## 5. შესაფერისობის ლოგიკა / Eligibility matcher

ახალი სკრიპტი `scripts/trials/eligibility_matcher.py` (Python — შეუძლია რეალური თარიღი/ასაკი). თითო ctgov row-ზე:

1. **ასაკი / Age** — parse `min_age`/`max_age` ("0 Years", "36 Months") → თვეებად; ალექსანდრას ასაკი (DOB **2026: 2025-08-28**) თვეებში გაშვების დღეს; შეამოწმე `min ≤ age ≤ max`. parse-ვერ-მოხერხდა → `evaluating` (NOT hidden).
2. **დიაგნოზი / Condition** — already pre-filtered by fetcher QUERY_SETS; cross-check trial conditions vs {HIE, hypoxic-ischemic, neonatal encephalopathy, cystic encephalomalacia, infantile spasms, cerebral palsy}. no overlap → `ineligible (condition)`.
3. **სტატუსი / Recruiting** — `overall_status ∈ {RECRUITING, NOT_YET_RECRUITING, ENROLLING_BY_INVITATION, ACTIVE_NOT_RECRUITING}`. სხვა → `ineligible (closed)`.
4. **ლოკაცია / Location** — `locations` → `is_us` / `is_international` flags. ორივე ჩანს გვერდზე; intl იღებს badge-ს. (geo არ ფილტრავს, მხოლოდ ნიშნავს — D2.)
5. **გამორიცხვა / Exclusions** — free-text `eligibility_criteria` exclusion scan (best-effort keyword pass). ეჭვი → `evaluating`, NOT `ineligible`.

**კონსერვატიული წესი (Core Value):** კვლევა იმალება (`ineligible`) **მხოლოდ მკაფიო დისკვალიფიკატორზე**. ბუნდოვანი ყოველთვის → `evaluating` (needs-review), არასოდეს ჩუმად წაშლა.

`eligibility_issues` ივსება ყველა ჩავარდნილ კრიტერიუმზე (audit trail).

---

## 6. A ფაზა — „დადე რაც არის" / Phase A (vertical slice — ships value)

| # | Task | ფაილ(ებ)ი |
|---|---|---|
| A0 | Pre-flight: `clinical_trials` live? + (თუ საჭიროა) migration: 3 ველი → JSONB | `scripts/migrations/0NN_trials_jsonb.sql` |
| A1 | Eligibility matcher + sync (`evidence_ledger` → `clinical_trials`) | `scripts/trials/eligibility_matcher.py` |
| A2 | KA backfill (title/summary/eligibility) translator primitive-ით, budget-gated | matcher-ში / `scripts/trials/translate_trials.py` |
| A3 | One-off seed run → ცხრილი ცოცხალი მონაცემებით ივსება | (CLI run) |
| A4 | viewer fetcher `fetchClinicalTrials(locale)` | `viewer/lib/data.ts` |
| A5 | ქვე-გვერდი `/research/trials` (main list + needs-review section) | `viewer/app/[locale]/research/trials/page.tsx` |
| A6 | nav entry „სამედიცინო კვლევები" | `viewer/components/shell/AppShell.tsx` |
| A7 | i18n namespace `Trials` (EN + KA) | `viewer/messages/{en,ka}.json` |
| A8 | verifier script | `scripts/verify_trials.py` |

**A ფაზის შედეგი:** მუშა გვერდი, რომელიც აჩვენებს რეალურ შესაფერის კვლევებს, წყაროს ბმულებით, ორ ენაზე.

---

## 7. B ფაზა — „ავტომატი" / Phase B (automation)

| # | Task | ფაილ(ებ)ი |
|---|---|---|
| B1 | matcher ავტომატურად perception_tick-ის შემდეგ (fetch → match) | `scripts/perception_tick.py` |
| B2 | ახალი-შესაფერისი detection (diff vs DB) → Telegram ping | `scripts/trials/eligibility_matcher.py` |
| B3 | „Clinical trials for Aleksandra" სექცია Weekly Brief-ში | `scripts/communicator/weekly_brief.py` |
| B4 | სტატუსის მონიტორინგი (recruiting → closed) `last_checked`/`status_changed`-ით | matcher |
| B5 | (optional) PI/coordinator outreach draft hook (Gmail draft-only, PHI-redacted) | `scripts/communicator/` |

> Phase B-ს დიდი ნაწილი უკვე "თითქმის" აქ არის: perception_tick 6სთ-ში ეშვება, Weekly Brief loop verified, Telegram primitive მუშაობს. ძირითადად დაკავშირებაა.

---

## 8. გვერდის დიზაინი / Page design (`/research/trials`)

```
─────────────────────────────────────────────
 სამედიცინო კვლევები / Clinical Trials
 ალექსანდრასთვის შესაფერისი, აქტიური კვლევები
─────────────────────────────────────────────
 [ შესაფერისი N ]   [ გადასამოწმებელი M ]      ← ორი ჯგუფი / two buckets

 ┌───────────────────────────────────────────┐
 │ Cord Blood for HIE        [RECRUITING] 🇺🇸 │
 │ Phase II · ასაკი 0–24თვე · Duke University │
 │ მოკლე აღწერა… (ka)                          │
 │ ✓ ასაკი ✓ დიაგნოზი ✓ ლოკაცია               │
 │ NCT04XXXXXX ↗ clinicaltrials.gov            │
 └───────────────────────────────────────────┘
 …

 ── გადასამოწმებელი (needs review) ───────────
 ┌───────────────────────────────────────────┐
 │ … [ENROLLING] 🌍 intl                       │
 │ ⚠ ასაკის კრიტერიუმი გასარკვევია             │
 └───────────────────────────────────────────┘
```

Server component, `getTranslations("Trials")`, `fetchClinicalTrials(locale)` → `getRows("clinical_trials", { aleksandra_status: "in.(identified,evaluating)", order: "last_updated.desc" })`. Bilingual via `displayField`. Each card: provenance link `https://clinicaltrials.gov/study/<nct_id>`.

---

## 9. ორენოვნება / Bilingual handling

- **UI chrome** (headers, labels, badges): next-intl namespace `Trials`, EN+KA.
- **Trial content** (ctgov is English): key fields (`title`, `brief_summary`, `eligibility_criteria`) translated to KA on ingest via the existing translator primitive (direct `anthropic.messages.create`, same as migrations 014/015) — **budget-gated** (`check_daily_budget`). English always retained; KA is additive.

---

## 10. რისკები და ღია საკითხები / Risks & open items

1. **`clinical_trials` live-status** — schema-შია, მაგრამ AGENTS.md #1 ამბობს ზოგი ცხრილი 404. → Task A0 ამოწმებს.
2. **მონაცემების მოცულობა ახლა** — perception ბოლო ხანს ჩავარდნილი იყო (Railway B.1 RED + CI fallback fail). **დღეს გასწორებული CI fallback** ამას აღადგენს. seed-ისთვის შესაძლოა საჭირო გახდეს ერთი ხელით `fetch_ctgov` run.
3. **Eligibility free-text** — exclusion criteria parse არასრულყოფილია → კონსერვატიული წესი (ეჭვი = needs-review).
4. **Translation cost** — KA backfill იწვევს Anthropic token-ხარჯს → budget gate; დიდი თავდაპირველი backfill ერთჯერადად.
5. **PHI** — outreach drafts (B5) მხოლოდ Communicator-ის redaction-ის შემდეგ; Telegram-ში PHI არ მიდის.

---

## 11. მიღების კრიტერიუმი / Acceptance (Phase A)

- [x] `clinical_trials` live + populated from existing ctgov evidence. (117 rows)
- [x] `/research/trials` რენდერდება: main list (eligible) + needs-review bucket. (31 + 28)
- [x] თითო კვლევას: სათაური, აღწერა, ფაზა, სტატუსი, ლოკაცია(US/intl badge), eligibility, NCT ბმული.
- [x] EN + KA; nav entry მუშაობს; `npm run build` მწვანე.
- [x] `scripts/verify_trials.py` მწვანე. (6/6)
- [x] ყველა surfaced კვლევას provenance. (NCT link)

---

## 12. ღირებულება / Cost

- A ფაზა: ~ერთი translator backfill batch (token cost, budget-gated) + dev. პროექტის cap $60-დან ~12% დახარჯულია.
- B ფაზა: მარგინალური (perception უკვე ეშვება; translate მხოლოდ ახალ trial-ებზე).

---

## 13. შემდეგი ნაბიჯი / Next step

**A + B ფაზა დასრულდა** (code-complete).
- A: გვერდი ცოცხლად Vercel-ზე (`/ka/research/trials` · `/en/research/trials`), 31+28 კვლევა.
- B: matcher ავტომატურად perception_tick-ში (6სთ); ახალ შესაფერის კვლევაზე Telegram + Weekly Brief სექცია; სტატუს-მონიტორინგი (re-fetched trials). Telegram baseline seeded → spam არ იქნება.

**B4 limitation:** სრულად დახურული (აღარ-fetch-ვადი) კვლევის სტატუსი ვერ ახლდება ავტომატურად — per-trial re-check ctgov-ზე deferred.

**Deferred / შემდგომი backlog:** B5 PI/coordinator outreach draft (Gmail draft-only, PHI-redacted) · A2 trial აღწერების KA თარგმანი (budget-gated) · EU CTR/სხვა registries.
