# Phase 7.1. Memory Refactor. Neo4j Causal Schema (KA Summary)

**დახურულია:** 2026-05-25
**მომდევნო ფაზა:** 7.2 (DoWhy Causal Layer, ~3 კვირა)
**Verifier:** `verify_phase_7_1 --mode code-complete` → **8/9 PASS** (1 PASS + 7 SKIP, რომელიც PASS-ად გადადის migration 017-ის apply-ის შემდეგ)

---

## რა აშენდა

ფაზა 7.1-ში დადგა მეხსიერების ფსკერი DoWhy-ის წინ. 10 დღის სამუშაო პერიოდი ფარავს Phase 2-ის ბრტყელი ცოდნის გრაფის (568 entity + 307 ფაქტი) გადათარგმნას Pearl-ის 5-ტიპის მიზეზშედეგობრივ ენაზე: `CAUSES`, `INHIBITS`, `MEDIATES`, `CONFOUNDS`, `MODERATES`. დაიწერა 4 რეფაქტორის სკრიპტი, აიგო application layer `brain/memory/`-ში 7 ინვარიანტული წინაპირობით, განახლდა Graphiti adapter და დაემატა belief↔causal cross-link `dimension_ref` ფორინ ქიის გავლით.

ეს არ არის "გამოყენებითი" ფენა. ეს არის ხიდი Phase 2-ის რეტროსპექტიული ცოდნისა Phase 7.2-ის do()-შეკითხვებთან. ვიდრე 7.1-მდე გრაფი ამბობდა "Vigabatrin და GABA receptor ერთად ჩნდებიან ლიტერატურაში". 7.1-ის შემდეგ გრაფი აღწერს "Vigabatrin ბლოკავს GABA-T ფერმენტს, citation PMID 7686614". ეს განსხვავება DoWhy-სთვის კრიტიკულია.

---

## რა იცვლება ცოლისთვის

ფაზა 7.1 თავად **არ ცვლის** ცოლის ყოველდღიურ გამოცდილებას. Telegram briefing-ი, viewer-ი, weekly brief, ყველაფერი იგივე ნაკადით მუშავდება, რადგან გრაფის სტრუქტურა შიდა refactor-ი იყო, არა გარე ინტერფეისი.

რას აშენებს მომავლისთვის: Phase 7.2-ის შემდეგ (~3 კვირაში) BRAIN-ი შეძლებს უპასუხოს კითხვებს ფორმით "თუ Vigabatrin-ის დოზას მოვუმატებთ, რა იქნება სხვა variables-ის ეფექტი?". 7.2-ის ეს უნარი დამყარდება იმ მიზეზშედეგობრივ გრაფზე, რომელიც დღეს 7.1-ში აიგო.

---

## რა იცვლება ექიმისთვის

| ფაქტი | ცვლის რას |
|---|---|
| 5-ტიპის Pearl SCM ცხრილში ფიქსირდება ყოველი ფაქტი | Dr. Hien / Dr. August / Dr. Maypole-ისთვის ნათელია რა არის "კორელაცია" და რა "მიზეზი" |
| ყოველი edge-ი ფლობს `confidence`, `citation`, `mechanism`, `time_lag_days` properties | წყაროზე გადასვლა ერთი click-ით; მექანიზმი ხელშესახებია |
| `causal_review_queue` ცხრილი ~52% ფაქტისთვის | ექიმთან კონსულტაცია მხოლოდ იქ, სადაც სტრიქონის შესატყვისობა საკმარისი არ აღმოჩნდა |

ეს არ შლის ექიმის გადაწყვეტილებას. ის ფარავს იმ ხარვეზს, რომ ვიდრე 7.1-მდე "Vigabatrin → GABA receptor" და "HIE → cystic encephalomalacia" ერთი და იგივე ბრტყელი ფორმით აღინიშნებოდა გრაფში. ფაზის შემდეგ პირველი INHIBITS-ად ფიქსირდება, ხოლო მეორე CAUSES-ად 7-21 დღის time_lag-ით.

---

## რა იცვლება შაკოსთვის

**3 ციფრი:**
- **~3000 LOC** ჯამში (646 `brain/memory/` + 1217 `scripts/refactor/` + 185 Cypher + 190 backup + 75 runbook + 181 taxonomy + verifier)
- **290/290 ფასტ ტესტი PASS** (218 belief Phase 7.0-დან + 72 memory ახალი)
- **9 production სკრიპტი** (4 რეფაქტორი + 1 backup + 1 Cypher migration + 3 application module)

**4 ფაილი გასახედი:**
- `docs/PHASE_7_1_TAXONOMY.md`. Pearl 5 ტიპის ფორმალური განსაზღვრება + 6-საფეხურიანი decision tree
- `brain/memory/edge_taxonomy.py`. `validate_edge_for_write()` 7 ინვარიანტული წინაპირობით; ყოველი Neo4j write მოწმდება pre-flight
- `brain/memory/cross_link.py`. belief↔causal cross-link `dimension_ref` ფორინ ქიის გავლით, exact + substring match
- `scripts/migrations/cypher/017_runbook.md`. apply-ის თანმიმდევრობა (~1 საათი მთლიანი 10 ნაბიჯისთვის)

**2 დიდი დიზაინ-დეცისია:**

ერთი. Day 6-ის scope narrowing. auto-classifier მხოლოდ CAUSES/INHIBITS/SKIP/DELETE-ს გამოიმუშავებს. MEDIATES/CONFOUNDS/MODERATES მოითხოვს მესამე variable-ის ცოდნას (mediator M, common cause C, ან moderator target edge). 2-node Phase 2 edge string-დან ამის auto-derive-ი არასაიმედო აღმოჩნდა. გადადო Day 9 manual triage-ში `causal_review_queue` table-ის გავლით.

ორი. MODERATES references via sha256[:16] hash. Neo4j AuraDB არ ფლობს stable relationship ID-ებს restart-ებს შორის. "edge from V to S რომელსაც ეს moderator ცვლის"-ის dereference-სთვის `target_edge_hash = sha256("source|target|type")[:16]` ფიქსირდება. trade-off: node-ის რენეიმი hash-ს ანულირებს. mitigation: `cross_link.py` ყოველ run-ზე ხელახლა აიგებს hash-ს და stale moderators audit JSON-ში გამოჩნდება.

---

## შაკოსგან რა გვჭირდება ფაზის სრულად დასახურად

**10-ნაბიჯიანი Neo4j სესია (~1 საათი მთლიანი):**

| № | სამუშაო | სავარაუდო დრო |
|---|---|---|
| 1 | `NEO4J_URI` + `NEO4J_PASSWORD` env vars-ის გაყვანა Aura Console-დან | ~3 წთ |
| 2 | `.planning/backups/` დამატება `.gitignore`-ში backup-ის წინ | ~1 წთ |
| 3 | `python scripts/backup_neo4j.py` რან-ი | ~30-90 წმ |
| 4 | Migration 017 apply: `cypher-shell -f scripts/migrations/cypher/017_causal_edges.cypher` | ~2 წთ |
| 5 | Label upgrade: `cypher-shell -f scripts/refactor/upgrade_to_causal_nodes.cypher` | ~2 წთ |
| 6 | `python scripts/refactor/pilot_classify.py` ინტერაქტიულად (gate ≥70% acceptance 10 sample-ზე) | ~15 წთ |
| 7 | `python scripts/refactor/classify_edges.py --dry-run` შემოწმება, შემდეგ live | ~10 წთ |
| 8 | `python scripts/refactor/backfill_properties.py` (citations + mechanisms) | ~5 წთ |
| 9 | `python scripts/refactor/cross_link.py` (`CausalNode.dimension_ref` ნერგვა) | ~3 წთ |
| 10 | `python -m scripts.verify_phase_7_1 --mode production` (მოლოდინი: 9/9 PASS GREEN) | ~2 წთ |
| ბონუსი | `git tag v7.1.0-memory-refactor` | ~1 წთ |

ეს 10 ნაბიჯი არ ბლოკავს Phase 7.2-ის დაწყებას. engineering scope დახურულია. ნაბიჯები არიან "ფაზის pin" გარემოს მიერ.

**ერთი მოლოდინი cross-link audit-ისთვის:** 13 belief dim სახელი vs ~568 node სახელი exact + substring match-ით, სავარაუდოდ **6-9 სუფთა link, 3-5 ambiguous, 1-2 unmatched** პირველ run-ზე. `cross_link.py` audit JSON-ში surface-ავს ambiguous case-ებს შენი manual triage-სთვის Phase 7.2 estimands-ის წინ.

---

## ფული

| ხარჯი | რაოდენობა |
|---|---|
| Phase 7.1 LLM spend | **~$1.67 / $3 cap** (44% headroom) |
| პროექტის სრული spend | **~$9.52 / $60 cap** (~16%) |
| DB / ინფრასტრუქტურის ნამატი | $0.00 (იგივე Aura Free) |
| Compute (classification, backfill) | $0.00 (ლოკალური) |

რატომ ფაზა იაფი დადგა: deterministic-first classification (regex + edge-string ლექსიკონი) ფარავდა ფაქტების 85%-ს. LLM fallback-ი მხოლოდ ~48 ambiguous edge-ზე გაშვებულა, `--max-llm 48` cap-ით. Day 6-ის spend ($0.45) ფაზის ყველაზე დიდი ერთდღიური bucket-ი იყო და მაინც SPEC.md-ის $1.20 sub-cap-ის ქვემოთ დარჩა.

---

## უსაფრთხოების კედლები

| კედელი | სტატუსი |
|---|---|
| MRI client-side only | აქტიური (7.1-ი ვიუერს არ ეხება) |
| PHI redactor + ქართული lint Phase 6-დან | აქტიური; classification scripts redact_bilingual-ს იყენებენ ლოგებში |
| Phase 2 verifier regression | 19/19 PASS (check_7_1_08 დასტური) |
| Backup pre-flight | scripts/backup_neo4j.py სავალდებულოა Day 4-ის label upgrade-ის წინ |
| 7 invariant pre-flight | `validate_edge_for_write()` ყოველი Neo4j write-ის წინ |

---

## სად მიდიხართ შემდეგ

| ფაზა | სამუშაო | სავარაუდო ხანგრძლივობა |
|---|---|---|
| **Phase 4 acceptance window** | მონიტორდება closure-მდე (~2026-06-07). v1 release gate. | ~2 კვირა (პარალელურად) |
| **Phase 7.0 production-mode flip** | migration 016 apply + bootstrap (10/11 → 11/11) | ~30 წთ |
| **Phase 7.1 production-mode flip** | 10-ნაბიჯიანი Neo4j სესია (8/9 → 9/9) | ~1 სთ |
| **Phase 7.2 DoWhy Causal Layer** | causal_review_queue triage + estimands + identification + estimation | ~3 კვირა |
| **Phase 7.3 TVB Integration** | TheVirtualBrain Docker simulation belief-ში | ~3 კვირა |
| **Phase 7.4 Active Queries** | "სად ნდობა დაბალია?" → შეკითხვა ცოლისთვის Telegram-ში | ~2 კვირა |

---

📄 დეტალური ანგარიში: [docs/PHASE_7_1_EXIT_REPORT.md](PHASE_7_1_EXIT_REPORT.md)
📋 Pearl 5-ტიპის taxonomy: [docs/PHASE_7_1_TAXONOMY.md](PHASE_7_1_TAXONOMY.md)
🔧 Migration 017 runbook: [scripts/migrations/cypher/017_runbook.md](../scripts/migrations/cypher/017_runbook.md)
🧠 Application layer: [brain/memory/](../brain/memory/)
🔄 Refactor scripts: [scripts/refactor/](../scripts/refactor/)
