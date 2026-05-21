# Phase 6 დასრულდა — Bilingual System (i18n)

**დახურულია:** 2026-05-21
**მიდევნება:** verify_phase6 --mode code-complete → **11/11 PASS · ALL GREEN**
**კუმულატიური გადაცემა:** 89/89 PASS (ყველა 7 ფაზაზე)

---

## რა შეიცვალა

Phase 6-მდე ALEKSANDRA_BRAIN იყო მთლიანად ინგლისურენოვანი — viewer-ი, briefing-ი, Telegram-ი, Gmail-ი. შენ ხშირად კითხვისას მენტალურად თარგმნიდი ან ფიქრობდი "ეს უფრო ლუარჯერ წავიკითხავდი ქართულად." Phase 6 ცვლის ამ ნაკადს: ახლა საოჯახო Telegram-ი ლაპარაკობს ქართულად, viewer-ი მიჰყვება URL-ის ენას, ხოლო ექიმებისთვის გასაგზავნი Gmail-ი რჩება ინგლისურად — ავტომატურად, ერთი ცვლის გარეშე.

### 6 ახალი შესაძლებლობა

1. **🌐 ორი-ენოვანი ვებსაიტი** — 7 საოჯახო route (dashboard, timeline, papers, therapies, hypotheses, today, knowledge) ხელმისაწვდომია `/en/*` და `/ka/*` URL-ის გავლით. URL-ი არის ენის ერთადერთი წყარო — cookie არ ინახება, შეტყობინება არ მოგდის.
2. **🗣 LanguageSwitcher header-ში** — დააჭირე `EN` ან `ქართული` — გვერდი მყისიერად გადადის, არჩევანი URL-ში ჩაიწერება, refresh-ი ინარჩუნებს ენას.
3. **📊 ბილინგვალური მონაცემთა შენახვა** — 4 დინამიკური ცხრილი (`aleksandra_timeline`, `hypotheses`, `therapies`, `briefs.sections`) ახლა ინახავს `{en, ka}` წყვილებს JSONB სვეტებში. ძველი ჩანაწერებისთვის `ka = en` (მიგრაცია 012-მა მიანიჭა).
4. **💬 ბილინგვალური Communicator** — Sunday weekly brief, daily digest, manager briefing — ყველა აწერა {en, ka} წყვილებს. ანთროპიკის strict tool_use ემიტერი (compose_bilingual) მუშავდება დაცული ბიუჯეტ-დაცვის უკან.
5. **📱 აუდიენცია-მიხედვით routing** — Telegram-ი კითხულობს `.ka`-ს (ოჯახი); Gmail-ი კითხულობს `.en`-ს (ექიმები). Per-file locale კონსტანტა (TELEGRAM_LOCALE, GMAIL_LOCALE, BRIEFING_LOCALE) — ერთი audit წერტილი. n8n workflow JSON-ები **არ შეცვლილა**.
6. **🛡 ქართული PHI redactor + imperative-verb lint** — Phase 3-ის CATASTROPHIC guard-ები ახლა მუშავდება ქართულ ტექსტზეც. 10 ქართული PHI fixture (Mkhedruli სახელი, BMC MRN 7616818, DOB) გადის redactor-ში ნულოვანი PHI გასვლით. 8 ქართული banned-imperative ლექსემა (`უნდა`, `აუცილებლად`, `განიხილეთ`, `მოითხოვეთ`, `ითხოვეთ`, `სცადეთ`, `გაითვალისწინეთ`, `მართებთ`).

---

## რა აიყვანა Sprint-ი

| ტალღა | სცენარი | შედეგი |
|---|---|---|
| Wave 1 | next-intl@4 install + locale folder move + dictionaries + LanguageSwitcher + verifier scaffold | Build OK; 14 URL ხელმისაწვდომი; 143 key × 2 locale |
| Wave 2 | Migration 012 SQL + 359-line runbook + Shako-ს მიერ production apply | 6 სვეტი → JSONB; RLS დაცული; ძველი ჩანაწერები ka=en |
| Wave 3a | PHI redactor ქართული + banned_phrases.py D-05 ლექსემა + 65-test regression | Phase 3 CGM-04 unregressed; 65/65 PASS |
| Wave 3b | compose_bilingual (Anthropic strict tool_use) + weekly_brief JSONB emission | BILINGUAL_TEST_MODE=1 deterministic stub; Option A mirror |
| Wave 4 | display_field_py + telegram_sender .ka + gmail_digest .en + zero-touch n8n | 5 workflow audit table; n8n-ი არ შეცვლილა |

---

## ფული

| ხარჯი | რაოდენობა |
|---|---|
| Phase 6 LLM spend | **< $2** (~40% headroom — $5 cap) |
| პროექტის სრული spend | **~$5–6 / $60 cap** (~10%) |

რატომ ასე იაფი? Option A (RESEARCH.md Pattern 6) აირჩა `weekly_brief` და `manager_briefing` მიერ — დეტერმინისტული ინგლისურ-პირველ თარგმანი ქართულ მირორ-ით, ნულოვანი Anthropic ხარჯი თითო რიგზე. Option B (LLM-ბაზირებული რეალური ბილინგვალური ემიტირება) დამოწმებულია `BILINGUAL_TEST_MODE=1` env-ით — ცოცხალი Anthropic-ი მუშავდება მხოლოდ რეალურ Communicator run-ებზე როცა შენ ჩართავ.

ცოცხალი მუშაობისას:
- ერთი Sunday brief ბილინგვალურად ≈ $0 (deterministic mirror)
- ერთი LLM-ბაზირებული ბილინგვალური hypothesis ≈ $0.02–0.05
- ერთი viewer გვერდის ჩატვირთვა ნებისმიერი ენით ≈ $0 (static prerender + JSONB read)

---

## უსაფრთხოების კედლები

| კედელი | სტატუსი |
|---|---|
| MRI client-side only | ✅ შენარჩუნებული — Phase 6 viewer-ი არ ცვლის |
| PHI redactor ქართულ ტექსტზე | ✅ 10 fixture PASS; Mkhedruli case marker დაცული |
| Imperative-verb lint ქართულ ტექსტზე | ✅ 8 D-05 entry; 65-test regression PASS |
| RLS migration 008 → 012-ის შემდეგ | ✅ PG 15 contract: ALTER COLUMN TYPE არ ჩამოაგდებს policy-ებს |
| Budget gate compose_bilingual-ში | ✅ check_daily_budget(raise_on_over=True) ანთროპიკის call-ის წინ |
| Phase 4 + Phase 5 regression | ✅ check_i18n_11 spawn-ობს ორივეს; 9/9 + 13/13 |

---

## დარჩა?

ფიზიკურად **არაფერი** Phase 6-ის engineering scope-დან.

**მაგრამ 2 P2 maintenance task-ი დაგრჩა:**

1. **Migration 012 rollback artifact capture** — 15-20 წუთი, ერთი psql session. შენ პოპულირებ 9 placeholder ფაილს `scripts/migrations/012_rollback/`-ში:
   - 4 post-migration `\d <table>` snapshot-ი (RLS preservation evidence)
   - 4 current-state `pg_dump --column-inserts` (selective restore)
   - 1 smoke check evidence file
   შემდეგ ხელახლა გავუშვებთ `verify_phase6 --mode production --bucket B` — I18N-05 + I18N-09 production-GREEN-ად გადადის.
   ფაილი: `.planning/todos/pending/2026-05-21-capture-migration-012-rollback-artifacts.md`

2. **ქართული lexicon native-speaker re-verify** — 10-15 წუთი. შენ ნახე 8 D-05 entry `scripts/communicator/banned_phrases.py`-ში და დაადასტურე/შეასწორე. ლექსემა მუშავდება დღესაც; gap არის "review-not-yet-done", არა "code-not-correct."
   ფაილი: `.planning/todos/pending/2026-05-21-shako-verify-06-11-lexicon.md`

ვერც ერთი არ ხდის Phase 6-ის ხურვას — ისინი არიან hygiene/audit follow-up-ები.

---

## აქამდე როგორ მუშაობდა, ახლა როგორ მუშაობს

**Phase 6-ის წინ:**
- შენ ნახე weekly brief Telegram-ში → ინგლისურად
- შენ აღნიშნე ერთი hypothesis viewer-ში → ინგლისურად
- შენ გადააფორვარდე Dr. Hien-ისთვის ემაილი → ინგლისურად
- შენ მენტალურად თარგმნე rendition-ი ბებიის/ბაბუისთვის → ხელით
- 4 ნაბიჯი, ერთი ენა, შენი თარგმანი

**Phase 6-ის შემდეგ:**
- შენ ნახე weekly brief Telegram-ში → **ქართულად, თავიდანვე**
- ბებიამ/ბაბუამ წაიკითხა იგივე Telegram → **მათ ენაზე**
- შენ გახსენი viewer `/ka/timeline` → **ქართულად**
- შენ დააჭირე `EN` ღილაკს → **იგივე გვერდი ინგლისურად**
- შენ შექმენი Gmail draft Dr. Hien-ისთვის → **ინგლისურად**, ერთი click-ით
- 0 ხელით თარგმანი. 0 ცვლა. 0 ხელახალი click.

---

## შემდეგი გეგმა

Phase 6 დახურულია. **შემდეგი ფოკუსი:**

1. **Phase 4 acceptance window** — 14-დღიანი ფანჯარა მონიტორდება closure-მდე (~2026-06-07). პირველი რეალური Weekly Brief კვირას 2026-05-24 09:00 ET. ეს არის v1 release gate.
2. **2 P2 maintenance task** (იხ. ზემოთ) — როცა მოგინდება, 25-35 წუთი ერთად.
3. **Maintenance phase planning** — 10 backend gap (Phase 5-დან) + 4 Phase 6 deferred item (AI backfill, French UI, GIN search, CGM-06 ქართული) ერთად ფორმდება შემდეგი roadmap-ის input doc-ად.

---

## კუმულატიური verifier coverage

| ფაზა | Score | Mode |
|---|---|---|
| Phase 1 Perception | 10/10 PASS | — |
| Phase 2 Memory | 19/19 PASS | — |
| Phase 2.5 Quick Wins | 16/16 PASS | — |
| Phase 3 Cognition | 11/11 PASS | — |
| Phase 4 First Family Value | 9/9 PASS | code-complete |
| Phase 5 BRAIN Manager | 13/13 PASS | code-complete |
| **Phase 6 Bilingual (i18n)** | **11/11 PASS** | code-complete |
| **სრულად** | **89/89 PASS** | — |

---

📄 დეტალური ანგარიში: [docs/PHASE_6_EXIT_REPORT.md](PHASE_6_EXIT_REPORT.md)
📋 SPEC: [.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-SPEC.md](../.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-SPEC.md)
🔧 Migration 012 runbook: [scripts/migrations/012_runbook.md](../scripts/migrations/012_runbook.md)
