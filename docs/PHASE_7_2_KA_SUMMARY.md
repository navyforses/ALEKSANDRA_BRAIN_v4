# Phase 7.2. Causal Layer. DoWhy + SCM Editor (KA Summary)

**დახურულია:** 2026-05-25
**მომდევნო ფაზა:** 7.3 (TVB Simulation Engine, ~3 კვირა)
**Verifier:** `verify_phase_7_2 --mode code-complete` → **12/12 PASS** (production gate ღიაა migration 018-ის apply-ის შემდეგ)

---

## რა აშენდა

ფაზა 7.2 ფარავს 15-დღიან sprint-ს, რომელიც აშენებს causal-inference ფენას Phase 7.1-ის Pearl 5-ტიპის ცოდნის გრაფზე. 5 module-ი, ერთი migration, ერთი verifier 13 ლეიერი, 32 ახალი ტესტი. ცენტრალური მიღწევები:

- **DoWhy CausalModel wrapper** რომელიც გადაიყვანს Pydantic SCM-ს pywhy-ის backdoor-identification API-ში.
- **do()-shekitkhva API**: ექიმის "თუ Vigabatrin-ის დოზას მოვუმატებთ?" კითხვა ფორმდება `DoQueryRequest` Pydantic-ად, return-დება `DoQueryResponse` effect + CI-ით.
- **Counterfactual API**: factual observation + intervention dict ბრუნდება predicted_outcome-ით.
- **Sensitivity refutation**: random_common_cause + placebo_treatment refuter-ი ყოველ estimate-ზე ერთად ბრუნდება.
- **belief↔causal cross-link**: causal estimate ფიქსირდება Phase 7.0-ის `belief_evidence`-ში.
- **pgmpy structure learning** (Day 11): Hill-Climb BIC + PC chi-square estimator-ი observational data-დან DAG-ის შემოწმებას იძლევა.
- **SCM persistence** (Days 12-14): versioned CRUD + audit log + revert. SCM head იცვლება ახალი version-ის INSERT-ით, არა UPDATE-ით. History 100% immutable.
- **Migration 018** (Days 12-13): 3 ახალი ცხრილი (`scms`, `scm_audit_log`, `causal_estimates`), purely additive, RLS migration 016-ის pattern-ით.
- **12-check verifier** (Day 15): dual-mode (code-complete + production); JSON log emit-ი `v7_architecture/foundation_logs/`-ში.

ცენტრალური დიზაინ-დეცისია: DRY_RUN-when-`SUPABASE_DB_URL`-unset pattern (`brain/causal/cross_link.py`-დან carry over). ყოველი persistence ფუნქცია DB-ის გარეშე ბრუნდება deterministic `"DRY_RUN:<sha256>"` sentinel-ით. code-complete ტესტები 100% infra-ფრიე მუშავდება.

---

## რა იცვლება ცოლისთვის

ფაზა 7.2 თავად **არ ცვლის** ცოლის ყოველდღიურ გამოცდილებას. Telegram briefing-ი, viewer-ი, weekly brief, ყველაფერი იგივე ნაკადით მიდის, რადგან causal API frontend-ში არ exposed-ი არ არის Phase 7.6-მდე (CausalGraph view).

რას აშენებს მომავლისთვის: 7.2-ის შემდეგ BRAIN-ი ფლობს `do()` operator-ს. ექიმის სავარაუდო კითხვა "თუ vigabatrin-ის washout-ი 60 დღით გადადო, Bayley-ის ქულას რა ეფექტი ექნება 180 დღეში?" გადადის DoWhy-ის propensity-score matching estimator-ში, ბრუნდება point estimate + 95% CI + 2-რეფუტერის sensitivity report. ეს უნარი 7.3-ში TVB simulation-ით გაფართოვდება და 7.6-ში viewer-ში გამოჩნდება.

---

## რა იცვლება ექიმისთვის

| ფაქტი | ცვლის რას |
|---|---|
| do()-shekitkhva API exposed | Dr. Hien / Dr. Maypole / Dr. August შეძლებენ ნახონ "Vigabatrin → Seizure frequency" ეფექტი DoWhy-ის backdoor adjustment-ით (Age confounder ავტომატურად identified) |
| Counterfactual API exposed | "თუ Vigabatrin-ი დაიწყო თვის წინ?" კითხვა ფორმდება structural-linear extrapolation-ით reference SCM-ზე |
| Sensitivity refutation ყოველ estimate-ზე | random_common_cause + placebo_treatment refuter-ი ფარავს basic robustness checks. Reports-ი ცალკე ჩანდება result-ში |
| Migration 018-ის შემდეგ versioned SCM editor | ექიმს შეუძლია own ჰიპოთეზის SCM ხელით შეცვალოს, history ფლობდეს, საჭიროებისას revert-ი გააკეთოს |

ეს არ შლის ექიმის გადაწყვეტილებას. ის ფარავს იმ ხარვეზს, რომ ვიდრე 7.2-მდე "Vigabatrin reduces seizures" იყო ჰიპოთეზის level-ი ცოდნის გრაფში. 7.2-ის შემდეგ ის ფიქსირდება observational data-ზე backdoor-adjusted point estimate-ით + CI-ით + 2-refuter sanity report-ით.

---

## რა იცვლება შაკოსთვის

**4 ციფრი:**
- **~1441 LOC** ჯამში Days 11-15-ში (structure_learning 254 + scm_persistence 596 + verifier 489 + __init__ update + tests 469 + migration 018 SQL + runbook 314)
- **411/411 ფასტ ტესტი PASS** (379 baseline + 32 ახალი brain/causal/tests-ში; zero regression)
- **12/12 verifier PASS** code-complete mode-ში
- **$0.00 LLM spend** 5-დღიან Days 11-15 phase-ში ($4 cap full headroom; total project ~$9.52 / $60 cap, ~16%)

**4 ფაილი გასახედი:**
- `brain/causal/structure_learning.py`. pgmpy HillClimb-BIC + PC + LearnedStructureReport (precision/recall/F1 vs reference SCM). 11 ტესტი.
- `brain/causal/scm_persistence.py`. versioned CRUD + audit log + revert + 3 multi-SCM workspace, immutable history. 21 ტესტი.
- `scripts/migrations/018_scm_tables.sql`. 3 ახალი ცხრილი, RLS, trigger. apply Shako-pending.
- `scripts/verify_phase_7_2.py`. 12 check, dual-mode (code-complete + production), JSON log emit-ი.

**3 დიდი დიზაინ-დეცისია:**

ერთი. **Immutable history**. delete/update/revert ყოველი ოპერაცია INSERT-ით ფიქსირდება, არა UPDATE-ით. `scms (name, version)` UNIQUE. revert-ი = ძველი payload-ის ხელახალი INSERT-ი ახალ version-ზე. delete = tombstone row `graph_json = {"_deleted": true}` ფორმით. trade-off: storage წილით უფრო დიდი (history გრცელდება), მაგრამ audit lineage 100% reconstructible. hard delete intentionally NOT supported (NotImplementedError raise-ი).

ორი. **DRY_RUN-when-DSN-unset pattern**. `cross_link.py`-დან Days 10-ში გადმოვიდა. ყოველი CRUD ფუნქცია `os.environ.get('SUPABASE_DB_URL')` check-ით ბრუნდება `"DRY_RUN:<sha256>"` sentinel-ი DB-ის გარეშე. code-complete pytest 100% infrastructure-free მუშავდება. trade-off: production mode-ში check-ის flip-ი ცალკე verifier run-ი მოითხოვს (`--mode production`).

სამი. **pgmpy 1.1.2 patsy column-name workaround**. `bic-g` Gaussian BIC patsy-ის გავლით ფიქსირდება, რომელიც ყოველ column-ზე `ast.parse()`-ს იძახებს. column-ის სახელი spaces / parentheses / hyphens-ით (i.e. "Age (months)", "GABA-T enzyme") SyntaxError-ს იძახებს. mitigation: `_sanitize_column_name` ფუნქცია rename map ბრუნდება, structure-ის სწავლის ბოლოს `node_name_mapping`-ით inverse-ი ერთვის `compare_structures`-ში. document-ი 7.3-სთვის თუ Aleksandra_timeline column-ი იგივე pattern-ი ფარდება.

---

## შაკოსგან რა გვჭირდება ფაზის სრულად დასახურად

**4-ნაბიჯიანი Supabase სესია (~10 წთ მთლიანი):**

| № | სამუშაო | სავარაუდო დრო |
|---|---|---|
| 1 | `SUPABASE_DB_URL` env var-ის გაყვანა Supabase Console-დან | 30 წმ |
| 2 | Pre-flight backup: `pg_dump --schema-only > .planning/backups/pre_018/schema.sql` + `--data-only > .../data.sql` | 1-3 წთ |
| 3 | Migration apply: `psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/018_scm_tables.sql` | < 5 წმ |
| 4 | Verification: `\d scms` + `\d scm_audit_log` + `\d causal_estimates` + 3 SELECT count(*) (expect 0) + 3 belief / hypotheses / therapies count check | 3-5 წთ |
| 5 | `python -m scripts.verify_phase_7_2 --mode production` (მოლოდინი: 12/12 PASS GREEN, რომელშიც check 8/9/10 ცხოვრობს DB-ში live) | < 30 წმ |
| ბონუსი | `git tag v7.2.0-causal-layer` | 1 წმ |

ეს 5 ნაბიჯი არ ბლოკავს Phase 7.3-ის დაწყებას. engineering scope დახურულია. ნაბიჯები არიან "ფაზის pin" გარემოს მიერ.

დეტალური runbook: [scripts/migrations/018_runbook.md](../scripts/migrations/018_runbook.md).

---

## ფული

| ხარჯი | რაოდენობა |
|---|---|
| Phase 7.2 Days 11-15 LLM spend | **~$0.00 / $4 cap** (100% headroom) |
| Phase 7.2 Days 1-10 LLM spend (prior session) | ~$0.00 (deterministic implementation) |
| პროექტის სრული spend | **~$9.52 / $60 cap** (~16% across 10 phases) |
| DB / ინფრასტრუქტურის ნამატი | $0.00 (იგივე Supabase Free) |
| Compute (DoWhy + pgmpy + sensitivity) | $0.00 (ლოკალური) |

რატომ ფაზა იაფი დადგა Days 11-15: deterministic Python implementation (Pydantic + psycopg2 + pgmpy + sensitivity). LLM call-ი არ მოხდა code generation-ში, structure learning-ი deterministic algorithm-ით ფარდება, SCM CRUD სრულად ფიქსირებული schema-ზე გაშვებულია.

---

## უსაფრთხოების კედლები

| კედელი | სტატუსი |
|---|---|
| MRI client-side only | აქტიური (7.2 ვიუერს არ ეხება) |
| PHI redactor + ქართული lint Phase 6-დან | აქტიური; causal modules PHI-ფრიე reference SCM-ით მუშავდება |
| Phase 7.0/7.1 verifier regression | 10/11 + 8/9 PASS code-complete (carry-over) |
| Phase 1-6.1 verifier regression | 89/89 PASS code-complete (carry-over) |
| Backup pre-flight | `pg_dump` mandatory migration 018-ის apply-ის წინ |
| Immutable history (CRUD design) | hard delete intentionally NotImplementedError |
| service_role RLS bypass policy | migration 018 ენგობს migration 016-ის pattern-ს |

---

## სად მიდიხართ შემდეგ

| ფაზა | სამუშაო | სავარაუდო ხანგრძლივობა |
|---|---|---|
| **Phase 4 acceptance window** | მონიტორდება closure-მდე (~2026-06-07). v1 release gate. | ~2 კვირა (პარალელურად) |
| **Phase 7.0 production-mode flip** | migration 016 apply + bootstrap (10/11 → 11/11) | ~30 წთ |
| **Phase 7.1 production-mode flip** | 10-ნაბიჯიანი Neo4j სესია (8/9 → 9/9) | ~1 სთ |
| **Phase 7.2 production-mode flip** | 4-ნაბიჯიანი Supabase სესია (12/12 → 12/12 production) | ~10 წთ |
| **Phase 7.3 TVB Simulation Engine** | TheVirtualBrain Docker integration + mechanistic ODE simulation + belief writeback | ~3 კვირა |
| **Phase 7.4 Active Queries** | "სად ნდობა დაბალია?" → Telegram-ში შეკითხვა ცოლისთვის | ~2 კვირა |

---

📄 დეტალური ანგარიში: [docs/PHASE_7_2_EXIT_REPORT.md](PHASE_7_2_EXIT_REPORT.md)
📋 Retrospective + carry-forwards: [docs/PHASE_7_2_RETROSPECTIVE.md](PHASE_7_2_RETROSPECTIVE.md)
🔧 Migration 018 runbook: [scripts/migrations/018_runbook.md](../scripts/migrations/018_runbook.md)
🧠 Causal layer: [brain/causal/](../brain/causal/)
✅ Verifier: [scripts/verify_phase_7_2.py](../scripts/verify_phase_7_2.py)
