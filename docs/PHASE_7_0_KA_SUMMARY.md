# Phase 7.0. ციფრული ტყუპის ფსკერი (KA Summary)

**დახურულია:** 2026-05-25
**მომდევნო ფაზა:** 7.1 (მეხსიერების რეფაქტორი, ~2 კვირა)
**Verifier:** `verify_phase_7_0 --mode code-complete` → **10/11 PASS** (1 SKIP, რომელიც PASS-ად გადადის migration 016-ის apply-ის შემდეგ)

---

## რა აშენდა

Phase 7.0-ში დადგა ციფრული ტყუპის მათემატიკური ფსკერი. 18 დღის სამუშაო პერიოდი ფარავს 5 ფენას: 13 დიმენსიის კატალოგი ლიტერატურით დასაბუთებული priors-ით, შენახვის ფენა Supabase-ში, evidence-ის განახლების API, ერთობლივი მოდელი ცვლადთა შორის კორელაციით, MRI ანგარიშის და ხმოვანი ჩანაწერის ადაპტერები. დასასრულს დაემატა ვიზუალური snapshot-ები ArviZ-ით.

ეს არ არის "გამოყენებითი" ფენა. ეს არის ფსკერი იმისთვის, რომ Phase 7.4-მა (აქტიური შეკითხვები) იცოდეს რა იცის სისტემამ Aleksandra-ზე და რა არ იცის ჯერ. ყოველი ცვლადი (cyst volume, brainstem function, seizure frequency, GMFCS level, head control, eye tracking, Bayley cognitive, muscle tone, feeding stage, apnea events, CSF biomarkers, family readiness, neuroplasticity resource) იღებს თავის prior-ს PubMed წყაროდან, ცვლის თავის posterior-ს ახალი evidence-ის შემოსვლისას, და აფიქსირებს მის ნდობის ფანჯარას ვიზუალურად.

---

## რა ცვლის ცოლისთვის

ფაზა 7.0 თავად **არ ცვლის** ცოლის ყოველდღიურ გამოცდილებას. Telegram briefing-ი, viewer-ი, weekly brief, ყველაფერი იგივე ნაკადით მუშავდება.

რას ცვლის: Phase 7.4-ის შემდეგ (~6 კვირაში) BRAIN-ი მიხვდება როდის უნდა შემოგტოვოს კონკრეტული შეკითხვა. ნაცვლად "გადახედე ალექსანდრას ფოტოს და ბავშვისთვის როგორ ფეხებზე ფიქრობ?" ღია კითხვისა, ფაზა 7.4 დასვამს მიზანმიმართულ შეკითხვებს იქ სადაც posterior-ის ნდობა დაბალია. ფაზა 7.0 აშენებს იმ "სად დაბალია ნდობა" სიგნალს.

---

## რა ცვლის ექიმისთვის

| ფაქტი | ცვლის რას |
|---|---|
| 13 დიმენსიის ცხრილი ნდობის ფანჯრით (95% HDI) | Dr. Hien / Dr. August / Dr. Maypole-ისთვის გადასაცემი snapshot, რომელშიც ჩანს რა იცის სისტემამ რა საფუძვლით |
| ყოველი prior-ის PubMed PMID | წყაროზე გადასვლა ერთი click-ით; დასაბუთება ხელშესახებია |
| ArviZ posterior + prior overlay 13 PNG | ვიზუალური evidence (სად აქვს მონაცემს ძალაუფლება ნდობის გადასაცვლელად) |

ეს არ შლის ექიმის გადაწყვეტილებას. ის ფარავს იმ ხარვეზს, რომ ვიდრე Phase 7.0-მდე ნდობა "10 hypothesis-ი ცხრილში" იყო. ფაზა 7.0-ის შემდეგ ნდობა ხდება რიცხვითი, შედარებადი, citation-ით დასაბუთებული.

---

## რა ცვლის შაკოსთვის

**3 ციფრი:**
- **3722 LOC** brain/belief/-ში (10 .py ფაილი + 1 .toml კატალოგი)
- **187/187 ტესტი PASS** (165 fast + 22 joint slow)
- **13/13 PNG snapshot** ლოკალურად (532 KB სრულად, 0 PHI)

**3 ფაილი გასახედი:**
- `brain/belief/dimensions.toml`. 13 დიმენსიის წყარო ინფორმაცია, ყოველი PMID-ით
- `brain/belief/joint.py`. ერთობლივი მოდელი LKJ კორელაციით + OrderedLogistic GMFCS-ისთვის
- `scripts/migrations/016_runbook.md`. apply-ის თანმიმდევრობა (~10 წუთი)

**1 დიდი დიზაინ-დეცისია:**
დაცული მონაცემთა ნაკადი (update API) აერთიანებს evidence_hash-ით idempotency-ს. ერთი და იგივე MRI ანგარიში 2-ჯერ რომ შემოვიდეს, posterior არ შეიცვლება. 5 injection point-ი (adapters, manager, communicator, scheduler, voice) ცალკე ფიქსირდება, ერთი ცენტრალური `update()` ფუნქცია. testability მაღალია.

---

## შაკოსგან რა გვჭირდება ფაზის სრულად დასახურად

| № | სამუშაო | სავარაუდო დრო |
|---|---|---|
| 1 | Migration 016 apply Supabase-ზე runbook-ის მიხედვით | ~10 წთ |
| 2 | Bootstrap script 13 TOML dim-ის UPSERT-ისთვის DB-ში (შენ ან მე ვაკეთებთ apply-ის შემდეგ) | ~15 წთ |
| 3 | `verify_phase_7_0 --mode production` რან-ი (check_7_0_11 უნდა გადაიფლიპოს SKIP → PASS) | ~5 წთ |

ეს 3 ნაბიჯი არ ბლოკავს ფაზა 7.1-ის დაწყებას. engineering scope დახურულია. ისინი არიან "ფაზის pin" გარემოს მიერ.

---

## ფული

| ხარჯი | რაოდენობა |
|---|---|
| Phase 7.0 LLM spend | **~$2.65 / $5 cap** (47% headroom) |
| პროექტის სრული spend | **~$7.85 / $60 cap** (~13%) |
| DB / ინფრასტრუქტურის ნამატი | $0.00 (TVB Docker გადადის 7.3-ში) |
| Compute (PyMC fits + viz) | $0.00 (ლოკალური) |

რატომ ფაზა იაფი დადგა: დღე 7–9-ში 3 librarian sub-agent პარალელურად ფარავდა 13 დიმენსიის PubMed citation-ის მოპოვებას. ეს ფაზის ხარჯის ~40% ფარავდა. ერთი Anthropic call-იც კი $0.10-ს არ გაცდენია.

---

## უსაფრთხოების კედლები

| კედელი | სტატუსი |
|---|---|
| MRI client-side only | აქტიური (Phase 7.0 viewer-ს არ ეხება) |
| PHI redactor + ქართული lint Phase 6-დან | აქტიური; voice_note ადაპტერი redact_bilingual-ს იყენებს |
| 13 PNG snapshot byte-stream PHI scan | ნულოვანი MRN, ნულოვანი `ალექსანდრა` literal, ნულოვანი DOB pattern |
| Budget gate compose-ის ფაზაში | აქტიური check_daily_budget(raise_on_over=True) Anthropic call-ის წინ |
| Migration 016 RLS | Phase 4/5/6 პატერნი (service_role write, authenticated read) |

---

## სად მიდიხართ შემდეგ

| ფაზა | სამუშაო | სავარაუდო ხანგრძლივობა |
|---|---|---|
| **Phase 4 acceptance window** | მონიტორდება closure-მდე (~2026-06-07). v1 release gate. | ~2 კვირა (პარალელურად) |
| **Phase 7.1 Memory Refactor** | Graphiti episode-ების + mem0 layer-ის გადახედვა belief-state-ის წინააღმდეგ | ~2 კვირა |
| **Phase 7.2 DAG Discovery** | pgmpy-ით ცვლადთა შორის კავშირების სტრუქტურა | ~3 კვირა |
| **Phase 7.3 TVB Integration** | TheVirtualBrain Docker simulation belief-ში | ~3 კვირა |
| **Phase 7.4 Active Queries** | "სად ნდობა დაბალია?" → შეკითხვა ცოლისთვის Telegram-ში | ~2 კვირა |

---

📄 დეტალური ანგარიში: [docs/PHASE_7_0_EXIT_REPORT.md](PHASE_7_0_EXIT_REPORT.md)
🔧 Migration 016 runbook: [scripts/migrations/016_runbook.md](../scripts/migrations/016_runbook.md)
📋 დიმენსიების კატალოგი: [brain/belief/dimensions.toml](../brain/belief/dimensions.toml)
📊 ვიზუალური snapshot-ები: [brain/belief/snapshots/](../brain/belief/snapshots/)
