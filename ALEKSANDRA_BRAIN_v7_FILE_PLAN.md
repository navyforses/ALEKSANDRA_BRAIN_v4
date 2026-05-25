# ALEKSANDRA_BRAIN v7.0 — ფაილების ვიზუალური გეგმა

> **დოკუმენტი:** v7.0 განხორციელების ფაილების მაპი
> **თარიღი:** 2026-05-24
> **მიზანი:** ცამეტი ცამეტი ფაილის სრული რუკა, რომელიც ცალკეულ სესიებში შეივსება
> **ცენტრალური წესი:** ერთ სესიაში მაქსიმუმ 1-2 ფაილი. სრული გეგმა 8-12 სესიას მოიცავს.
> **სიდიდე:** 67 ფაილი ჯამში, ~800-1200 KB ჯამური დოკუმენტაცია
> **დასრულება:** მიგრაციის ფაზასთან ერთად, 2026 დეკემბრამდე

---

## სრული ფაილური ხე (ვიზუალური)

```
aleksandra brane/
│
├── ALEKSANDRA_BRAIN_v7_FILE_PLAN.md          ← ეს ფაილი (master roadmap)
│
└── v7_architecture/                          ← ახალი ფოლდერი v7.0-ისთვის
    │
    ├── 00_MASTER/                            ← ცენტრალური ნავიგაცია
    │   ├── 00_INDEX.md
    │   ├── 01_GLOSSARY_KA_EN.md
    │   ├── 02_DECISION_LOG.md
    │   └── 03_CHANGELOG.md
    │
    ├── 10_PHILOSOPHY/                        ← ცენტრალური მეტაფორის სიღრმე
    │   ├── 10_DIGITAL_TWIN_METAPHOR.md
    │   ├── 11_FIVE_STRUCTURAL_GAPS.md
    │   ├── 12_BAYESIAN_FOUNDATIONS.md
    │   └── 13_CAUSAL_FOUNDATIONS.md
    │
    ├── 20_PILLARS/                           ← 10 ბურჯის სრული აღწერა
    │   ├── 20_PILLAR_I_MEMORY_BELIEF_STATE.md
    │   ├── 21_PILLAR_II_COGNITION_NEUROSYMBOLIC.md
    │   ├── 22_PILLAR_III_VISUALIZATION_UNCERTAINTY.md
    │   ├── 23_PILLAR_IV_OBSERVABILITY_DRIFT.md
    │   ├── 24_PILLAR_V_ACTION_ACTIVE_QUESTIONS.md
    │   ├── 25_PILLAR_VI_VALIDATION_CALIBRATION.md
    │   ├── 26_PILLAR_VII_CAUSALITY_NEW.md           ← ახალი v7.0-ში
    │   ├── 27_PILLAR_VIII_SIMULATION_NEW.md         ← ახალი v7.0-ში
    │   ├── 28_PILLAR_IX_ACTIVE_LEARNING_NEW.md      ← ახალი v7.0-ში
    │   └── 29_PILLAR_X_CONSTITUTIONAL_CODE_NEW.md   ← ახალი v7.0-ში
    │
    ├── 30_DIMENSIONS/                        ← ციფრული ტყუპის 13 განზომილება
    │   ├── 30_DIM_01_CYST_VOLUME.md
    │   ├── 31_DIM_02_BRAINSTEM_FUNCTION.md
    │   ├── 32_DIM_03_SEIZURE_FREQUENCY.md
    │   ├── 33_DIM_04_MUSCLE_TONE.md
    │   ├── 34_DIM_05_EYE_TRACKING.md
    │   ├── 35_DIM_06_HEAD_CONTROL.md
    │   ├── 36_DIM_07_GMFCS_LEVEL.md
    │   ├── 37_DIM_08_BAYLEY_COGNITION.md
    │   ├── 38_DIM_09_FEEDING_CAPABILITY.md
    │   ├── 39_DIM_10_RESPIRATORY_STABILITY.md
    │   ├── 3A_DIM_11_CSF_BIOMARKERS.md
    │   ├── 3B_DIM_12_NEUROPLASTICITY_WINDOW.md
    │   └── 3C_DIM_13_FAMILY_READINESS.md
    │
    ├── 40_RULES/                             ← 13 კონსტიტუციური წესის detail
    │   ├── 40_RULE_01_MRI_CLIENT_ONLY.md
    │   ├── 41_RULE_02_VOICE_REVIEW_REQUIRED.md
    │   ├── 42_RULE_03_CITATION_MANDATORY.md
    │   ├── 43_RULE_04_CONFIDENCE_INTERVALS.md
    │   ├── 44_RULE_05_BILINGUAL_PARITY.md
    │   ├── 45_RULE_06_PHI_FILTER.md
    │   ├── 46_RULE_07_BUDGET_HARD_STOP.md
    │   ├── 47_RULE_08_BELIEF_REQUIRES_EVIDENCE.md
    │   ├── 48_RULE_09_HYPOTHESIS_MIN_SOURCES.md
    │   ├── 49_RULE_10_SIMULATION_UNCERTAINTY_CHECK.md
    │   ├── 4A_RULE_11_QUESTION_RATE_LIMIT.md
    │   ├── 4B_RULE_12_PDF_MIN_PRIMARY_SOURCES.md
    │   └── 4C_RULE_13_VERIFIER_DEPLOYMENT_GATE.md
    │
    ├── 50_TECH/                              ← ცამეტი ახალი ტექნოლოგიის სიღრმე
    │   ├── 50_TECH_PYMC_NUMPYRO.md
    │   ├── 51_TECH_DOWHY_CAUSALNEX.md
    │   ├── 52_TECH_TVB_DOCKER.md
    │   ├── 53_TECH_PLOTLY_REACT_FLOW_VIS.md
    │   ├── 54_TECH_PYDANTIC_CSP_MIDDLEWARE.md
    │   ├── 55_TECH_EVENT_SOURCING_POSTGRES.md
    │   ├── 56_TECH_LITELLM_MULTIMODEL_ROUTING.md
    │   ├── 57_TECH_GEMINI_DEEP_RESEARCH.md
    │   ├── 58_TECH_CLAUDE_EXTENDED_THINKING.md
    │   ├── 59_TECH_VERCEL_AI_SDK_ORCHESTRATION.md
    │   └── 5A_TECH_FLOWER_PYSYFT_FEDERATED.md
    │
    ├── 60_SITE_VIEWS/                        ← Next.js საიტის ცვლილებები
    │   ├── 60_VIEW_TWIN_STATUS_NEW.md
    │   ├── 61_VIEW_CAUSAL_GRAPH_NEW.md
    │   ├── 62_VIEW_SIMULATION_STUDIO_NEW.md
    │   ├── 63_VIEW_BELIEF_DRIFT_NEW.md
    │   ├── 64_VIEW_STATUS_COCKPIT_REFACTOR.md
    │   ├── 65_VIEW_HYPOTHESES_REFACTOR.md
    │   ├── 66_VIEW_RESEARCH_PULSE_REFACTOR.md
    │   └── 67_VIEW_FAMILY_INBOX_REFACTOR.md
    │
    ├── 70_PHASES/                            ← 18-კვირიანი მიგრაცია 8 ფაზაში
    │   ├── 70_PHASE_7_0_BELIEF_FOUNDATION_4W.md
    │   ├── 71_PHASE_7_1_MEMORY_REFACTOR_2W.md
    │   ├── 72_PHASE_7_2_CAUSAL_LAYER_3W.md
    │   ├── 73_PHASE_7_3_SIMULATION_ENGINE_3W.md
    │   ├── 74_PHASE_7_4_ACTIVE_LEARNING_2W.md
    │   ├── 75_PHASE_7_5_CONSTITUTIONAL_2W.md
    │   ├── 76_PHASE_7_6_SITE_REFACTOR_3W.md
    │   └── 77_PHASE_7_7_ACCEPTANCE_WINDOW_2W.md
    │
    ├── 80_VERIFIERS/                         ← ცდის გადამოწმების სკრიპტები
    │   ├── 80_VERIFY_PHASE_7_0.md
    │   ├── 81_VERIFY_PHASE_7_1.md
    │   ├── 82_VERIFY_PHASE_7_2.md
    │   ├── 83_VERIFY_PHASE_7_3.md
    │   ├── 84_VERIFY_PHASE_7_4.md
    │   ├── 85_VERIFY_PHASE_7_5.md
    │   ├── 86_VERIFY_PHASE_7_6.md
    │   ├── 87_VERIFY_PHASE_7_7.md
    │   └── 88_VERIFY_CUMULATIVE_V7.md
    │
    ├── 90_INTEGRATION/                       ← v6.0-სთან თავსებადობა
    │   ├── 90_BACKWARD_COMPATIBILITY.md
    │   ├── 91_MIGRATION_BREAKING_CHANGES.md
    │   └── 92_ROLLBACK_PROCEDURES.md
    │
    ├── A0_OPERATIONS/                        ← ბიუჯეტი, რისკები, გადაწყვეტილებები
    │   ├── A0_BUDGET_DETAILED.md
    │   ├── A1_RISKS_REGISTER.md
    │   ├── A2_DECISIONS_PENDING.md
    │   └── A3_OPEN_QUESTIONS.md
    │
    └── B0_USER_GUIDES/                       ← მომხმარებლისთვის
        ├── B0_GUIDE_WIFE_KA.md
        ├── B1_GUIDE_DOCTORS_EN.md
        └── B2_GUIDE_SHAKO_DEV.md
```

---

## ფაილების ჯამური სტატისტიკა

| კატეგორია | ფაილების რაოდენობა | სრული წონა (KB) | სესიების რაოდენობა |
|---|---|---|---|
| 00 MASTER | 4 | ~30 | 1 |
| 10 PHILOSOPHY | 4 | ~80 | 1 |
| 20 PILLARS | 10 | ~250 | 2 |
| 30 DIMENSIONS | 13 | ~130 | 1-2 |
| 40 RULES | 13 | ~130 | 1-2 |
| 50 TECH | 11 | ~220 | 2 |
| 60 SITE VIEWS | 8 | ~120 | 1 |
| 70 PHASES | 8 | ~160 | 1 |
| 80 VERIFIERS | 9 | ~90 | 1 |
| 90 INTEGRATION | 3 | ~45 | 1 |
| A0 OPERATIONS | 4 | ~60 | 1 |
| B0 USER GUIDES | 3 | ~60 | 1 |
| **ჯამი** | **67 ფაილი** | **~1375 KB** | **15-18 სესია** |

---

## ფაილების სათითაო შინაარსი

### 00 MASTER

| ფაილი | მთავარი შინაარსი | სიდიდე |
|---|---|---|
| 00_INDEX.md | სრული ფაილების ნავიგაცია, hyperlinks | 5 KB |
| 01_GLOSSARY_KA_EN.md | ცამეტი ფაქტი ცამეტი ცამეტი ცამეტი ცამეტი ცამეტი ცამეტი ცამეტი ცამეტი ცამეტი ცამეტი ცამეტი ცამეტი ცამეტი | 12 KB |
| 02_DECISION_LOG.md | ცამეტი ცამეტი ცამეტი ცამეტი ცამეტი ცამეტი ცამეტი ცამეტი | 8 KB |
| 03_CHANGELOG.md | v7.0-ის ცვლილებების ისტორია | 5 KB |

### 10 PHILOSOPHY

| ფაილი | მთავარი შინაარსი | სიდიდე |
|---|---|---|
| 10_DIGITAL_TWIN_METAPHOR.md | Apollo-13-ის გადარჩენიდან ალექსანდრამდე, ფილოსოფიური ფუნდამენტი | 25 KB |
| 11_FIVE_STRUCTURAL_GAPS.md | v6.0-ის 5 სტრუქტურული ხარვეზის სრული ანალიზი | 20 KB |
| 12_BAYESIAN_FOUNDATIONS.md | რას ნიშნავს „ცოცხალი რწმენა", PyMC-ის შესავალი | 20 KB |
| 13_CAUSAL_FOUNDATIONS.md | პერლის do-calculus, კონტრფაქტური მსჯელობა | 15 KB |

### 20 PILLARS (თითო ფაილი თითო ბურჯისთვის)

| ფაილი | მთავარი შინაარსი | სიდიდე |
|---|---|---|
| 20_PILLAR_I_MEMORY_BELIEF_STATE.md | რწმენის მდგომარეობის backend, PyMC ინტეგრაცია ნეო4ჯეი-სთან | 25 KB |
| 21_PILLAR_II_COGNITION_NEUROSYMBOLIC.md | კლოდი + MedGemma + ბაიესისეული ფენა, ნეიროსიმბოლური wiring | 25 KB |
| 22_PILLAR_III_VISUALIZATION_UNCERTAINTY.md | NiiVue + R3F + Plotly uncertainty bands | 25 KB |
| 23_PILLAR_IV_OBSERVABILITY_DRIFT.md | Langfuse + custom belief drift dashboards | 20 KB |
| 24_PILLAR_V_ACTION_ACTIVE_QUESTIONS.md | Telegram ცოლისთვის, Gmail ექიმისთვის, აქტიური შეკითხვები | 25 KB |
| 25_PILLAR_VI_VALIDATION_CALIBRATION.md | twin vs რეალობა შედარება, BMC liaison | 25 KB |
| 26_PILLAR_VII_CAUSALITY_NEW.md | DoWhy + CausalNex + SCM editor | 30 KB |
| 27_PILLAR_VIII_SIMULATION_NEW.md | TVB Docker + Monte Carlo + Simulation Studio | 30 KB |
| 28_PILLAR_IX_ACTIVE_LEARNING_NEW.md | EIG calculator + question generator + rate limiter | 25 KB |
| 29_PILLAR_X_CONSTITUTIONAL_CODE_NEW.md | 13 ხელშეუხებელი წესის ფიზიკური ჩაშენების სრული აღწერა | 30 KB |

### 30 DIMENSIONS (თითო ფაილი ცამეტი განზომილებიდან)

თითო ფაილი ~10 KB. შინაარსი: სტატისტიკური ფორმის ფარული საფუძველი, საწყისი ალბათობების მონაცემთა წყაროები, განახლების ფორმულა, განზომილების ცვალდება ცამეტ თვეში.

| ფაილი | განზომილება | სტატისტიკური ფორმა |
|---|---|---|
| 30_DIM_01 | ცისტური ენცეფალომალაციის მოცულობა | ბეტა |
| 31_DIM_02 | ტვინის ღეროს ფუნქცია | კატეგორიული |
| 32_DIM_03 | ეპილეფსიური სპაზმის სიხშირე | პუასონი |
| 33_DIM_04 | კუნთის ტონუსი | ნორმალური |
| 34_DIM_05 | თვალის თვალყურდევნება | გამა |
| 35_DIM_06 | თავის ვერტიკალურად დაჭერა | ნორმალური |
| 36_DIM_07 | GMFCS დონე | კატეგორიული |
| 37_DIM_08 | Bayley კოგნიცია | ნორმალური |
| 38_DIM_09 | კვების უნარი | კატეგორიული |
| 39_DIM_10 | რესპირატორული მდგრადობა | ბერნული |
| 3A_DIM_11 | CSF ბიომარკერები | ვექტორი |
| 3B_DIM_12 | ნეიროპლასტიკურობის ფანჯარა | ექსპონენციალური დაცემა |
| 3C_DIM_13 | ოჯახური მზადყოფნა | კატეგორიული |

### 40 RULES (13 კონსტიტუციური წესის detail)

თითო ფაილი ~10 KB. შინაარსი: წესის ფიზიკური ჩაშენების ფორმა, კოდის სკეტჩი, false-positive escape hatch, ცდის სტრატეგია.

| ფაილი | წესი | ფიზიკური ფენა |
|---|---|---|
| 40_RULE_01 | MRI ფაილი არასოდეს გადადის სერვერზე | Browser CSP + upload block |
| 41_RULE_02 | ხმოვანი ჩანაწერი მოითხოვს გადახედვას | DB trigger |
| 42_RULE_03 | ციტატა ყოველი რეკომენდაციისთვის | Pydantic schema |
| 43_RULE_04 | ნდობის ფანჯარა, არა წერტილოვანი ღირებულება | Output formatter |
| 44_RULE_05 | ენის ფერხვის აკრძალვა | i18n middleware |
| 45_RULE_06 | PHI არასოდეს LLM მოთხოვნაში | Pre-prompt regex |
| 46_RULE_07 | ბიუჯეტი hard stop $100/თვე | LiteLLM gate |
| 47_RULE_08 | რწმენა მოითხოვს მტკიცებულებას | PyMC constraint |
| 48_RULE_09 | ჰიპოთეზის min 3 წყარო | DB constraint |
| 49_RULE_10 | სიმულაცია uncertainty check | Pre-flight |
| 4A_RULE_11 | შეკითხვის rate limit კვირაში 3 | Rate limiter |
| 4B_RULE_12 | PDF min 5 პირველადი წყარო | Doc generator |
| 4C_RULE_13 | Verifier deployment gate | CI/CD block |

### 50 TECH (ცამეტი ახალი ტექნოლოგიის სიღრმე)

| ფაილი | ტექნოლოგია | სიდიდე |
|---|---|---|
| 50_TECH_PYMC_NUMPYRO.md | ბაიესისეული backend, MCMC vs VI, JAX acceleration | 25 KB |
| 51_TECH_DOWHY_CAUSALNEX.md | მიზეზშედეგობრივი მსჯელობა, do-calculus, კონტრფაქტი | 25 KB |
| 52_TECH_TVB_DOCKER.md | ნეირონული მასების სიმულაცია, Railway deployment | 20 KB |
| 53_TECH_PLOTLY_REACT_FLOW_VIS.md | Frontend uncertainty + causal graph + scenario builder | 20 KB |
| 54_TECH_PYDANTIC_CSP_MIDDLEWARE.md | ფიზიკური წესების ჩაშენება | 15 KB |
| 55_TECH_EVENT_SOURCING_POSTGRES.md | Time-travel debugging, replay capability | 20 KB |
| 56_TECH_LITELLM_MULTIMODEL_ROUTING.md | კლოდი + დიპსიკი + მისტრალი + ქვენი routing | 20 KB |
| 57_TECH_GEMINI_DEEP_RESEARCH.md | TxGemma-ის parallel ცდისთვის | 15 KB |
| 58_TECH_CLAUDE_EXTENDED_THINKING.md | კონტრფაქტური validation-ში გაფართოება | 15 KB |
| 59_TECH_VERCEL_AI_SDK_ORCHESTRATION.md | Frontend streaming + tool calling | 15 KB |
| 5A_TECH_FLOWER_PYSYFT_FEDERATED.md | v8.0 ფედერირებული საფუძველი | 30 KB |

### 60 SITE VIEWS

| ფაილი | ხედი | სტატუსი |
|---|---|---|
| 60_VIEW_TWIN_STATUS_NEW.md | ციფრული ტყუპის snapshot ცამეტ განზომილებაში | ახალი |
| 61_VIEW_CAUSAL_GRAPH_NEW.md | მიზეზშედეგობრივი DAG, vis.js | ახალი |
| 62_VIEW_SIMULATION_STUDIO_NEW.md | ექიმის სცენარის builder, react-flow | ახალი |
| 63_VIEW_BELIEF_DRIFT_NEW.md | რწმენის ცვლილების ისტორია | ახალი |
| 64_VIEW_STATUS_COCKPIT_REFACTOR.md | + ციფრული ტყუპის snapshot | რეფაქტორი |
| 65_VIEW_HYPOTHESES_REFACTOR.md | + სიმულაციური სცენარის გრაფიკი | რეფაქტორი |
| 66_VIEW_RESEARCH_PULSE_REFACTOR.md | + „რა იცვლება ციფრულ ტყუპში" ფილტრი | რეფაქტორი |
| 67_VIEW_FAMILY_INBOX_REFACTOR.md | + აქტიური შეკითხვები ცოლისთვის | რეფაქტორი |

### 70 PHASES (18-კვირიანი მიგრაცია)

| ფაილი | ფაზა | ვადა | მთავარი მიწოდება |
|---|---|---|---|
| 70_PHASE_7_0 | Belief State Foundation | 4 კვირა | PyMC backend, 13-D სქემა |
| 71_PHASE_7_1 | Memory Refactor | 2 კვირა | ნეო4ჯეი → causal schema |
| 72_PHASE_7_2 | Causal Layer | 3 კვირა | DoWhy + SCM editor |
| 73_PHASE_7_3 | Simulation Engine | 3 კვირა | Monte Carlo + TVB |
| 74_PHASE_7_4 | Active Learning | 2 კვირა | EIG + question generator |
| 75_PHASE_7_5 | Constitutional Code | 2 კვირა | 13 წესის ფიზიკური ჩაშენება |
| 76_PHASE_7_6 | Site Refactor | 3 კვირა | 4 ახალი + 4 რეფაქტორი |
| 77_PHASE_7_7 | Acceptance Window | 2 კვირა | ცოლის/ექიმის/შაკოს ცდა |

### 80 VERIFIERS

თითო ფაილი ~10 KB. შინაარსი: checklist, test scripts, expected outputs, fail criteria.

### 90 INTEGRATION

| ფაილი | მთავარი შინაარსი |
|---|---|
| 90_BACKWARD_COMPATIBILITY.md | v6.0-ის ფუნქციები პარალელურად 3 თვე |
| 91_MIGRATION_BREAKING_CHANGES.md | რა იშლება, რა გრძელდება |
| 92_ROLLBACK_PROCEDURES.md | თუ ფაზა ჩავარდება, როგორ დავბრუნდეთ |

### A0 OPERATIONS

| ფაილი | მთავარი შინაარსი |
|---|---|
| A0_BUDGET_DETAILED.md | $80-100 თვეში, ფარული breakdown |
| A1_RISKS_REGISTER.md | 15-20 რისკი, mitigation |
| A2_DECISIONS_PENDING.md | 7 გადასაწყვეტი საკითხი |
| A3_OPEN_QUESTIONS.md | რა ვერ გადავწყვიტეთ |

### B0 USER GUIDES

| ფაილი | აუდიტორია | ენა |
|---|---|---|
| B0_GUIDE_WIFE_KA.md | ცოლი | ქართული |
| B1_GUIDE_DOCTORS_EN.md | BMC, Duke, Beth Israel | ინგლისური |
| B2_GUIDE_SHAKO_DEV.md | შაკოს developer გამოცდილება | ქართული |

---

## სესიების რეკომენდებული თანმიმდევრობა

თითო სესია = 1-2 ფაილი + 1-2 საათი ჩემს მხარეს.

| # | სესია | ფაილები | სავარაუდო ხანგრძლივობა | ფაზა |
|---|---|---|---|---|
| 1 | Master + Glossary | 00_INDEX + 01_GLOSSARY + 02_DECISION_LOG + 03_CHANGELOG | 2 საათი | 0 |
| 2 | Philosophy Deep | 10_TWIN + 11_GAPS + 12_BAYESIAN + 13_CAUSAL | 3 საათი | 0 |
| 3 | Pillars I-V | 20-24 ხუთი ფაილი | 4 საათი | 1 |
| 4 | Pillars VI-X | 25-29 ხუთი ფაილი | 4 საათი | 1 |
| 5 | 13 Dimensions | 30-3C ცამეტი ფაილი (mini-files თითო ~5 KB) | 3 საათი | 1 |
| 6 | 13 Rules | 40-4C ცამეტი ფაილი (mini-files) | 3 საათი | 1 |
| 7 | Tech Deep Dive | 50-5A ცამეტი ფაილი | 4 საათი | 1 |
| 8 | Site Views | 60-67 რვა ფაილი | 3 საათი | 2 |
| 9 | Phases 7.0-7.3 | 70-73 ოთხი ფაილი | 3 საათი | 2 |
| 10 | Phases 7.4-7.7 | 74-77 ოთხი ფაილი | 3 საათი | 2 |
| 11 | Verifiers | 80-88 ცხრა ფაილი | 3 საათი | 2 |
| 12 | Integration | 90-92 სამი ფაილი | 2 საათი | 3 |
| 13 | Operations | A0-A3 ოთხი ფაილი | 2 საათი | 3 |
| 14 | User Guides | B0-B2 სამი ფაილი | 3 საათი | 3 |
| 15 | Final review | სრული document tree-ის გადახედვა, ცარიელი ადგილების შევსება | 2 საათი | 4 |

ჯამური დრო: ~44 საათი = 6-8 კვირა, 4-6 საათი კვირაში.

---

## ფაილების პრიორიტეტი (თუ დრო შეზღუდულია)

თუ მხოლოდ 5-7 ფაილი დასაწერია:

**Tier 1 (აუცილებელია):**
1. 00_INDEX.md (ნავიგაცია ყველაფერზე)
2. 10_DIGITAL_TWIN_METAPHOR.md (ფილოსოფიური ფუნდამენტი)
3. 26_PILLAR_VII_CAUSALITY_NEW.md (ცენტრალური ახალი ბურჯი)
4. 27_PILLAR_VIII_SIMULATION_NEW.md (ცენტრალური ახალი ბურჯი)
5. 70_PHASE_7_0_BELIEF_FOUNDATION_4W.md (პირველი ფაზის გეგმა)

**Tier 2 (ღირებულია მცირე ცდისთვის):**
6. 50_TECH_PYMC_NUMPYRO.md (ცენტრალური ტექნოლოგია)
7. 60_VIEW_SIMULATION_STUDIO_NEW.md (frontend-ის ცენტრალური ცვლილება)
8. A0_BUDGET_DETAILED.md (ფინანსური clarity)

**Tier 3 (ნამატი value, არა critical):**
- დანარჩენი 59 ფაილი

---

## ფაილების შინაარსის შაბლონი

თითო ფაილს ექნება სტანდარტული სტრუქტურა (კონსისტენტურობისთვის):

```markdown
# [ფაილის სათაური]

> **დოკუმენტი:** [მოკლე აღწერა]
> **ფაზა:** [რომელ ფაზაში გამოიყენება]
> **დამოკიდებულებები:** [სხვა ფაილები]
> **სიდიდე:** [სავარაუდო KB]

## 0. რეზიუმე
[ერთი წინადადებით]

## 1. კონტექსტი
[რა პრობლემას წყვეტს]

## 2. ცენტრალური მექანიკა
[როგორ მუშაობს ფაქტობრივად]

## 3. კოდის სკეტჩი
[Python ან TypeScript მაგალითები]

## 4. ცდის სტრატეგია
[როგორ ვერიფიცირდება]

## 5. ცარიელი ადგილები
[რა არ ვიცით, რა გადასაწყვეტია]

## 6. წყაროები
[ბიბლიოგრაფია, GitHub links, docs]
```

---

## სავარაუდო ფაილური წყობის სავარჯიშო

ფოლდერი `v7_architecture/` შეიქმნება workspace-ში მომდევნო სესიაში. ფაილების ნუმერაცია იცავს alphabetic sort-ს (00, 01, 02, ..., 4C, 5A, B2).

---

## შენიშვნა

ეს გეგმა არ არის უცვლელი. სესიის დაწყებისას შესაძლოა აღმოვაჩინოთ, რომ:
- ცამეტი დიმენსიის ფაილი ცამეტი მცირე ფაილის ნაცვლად ერთი დიდი ფაილი იყოს უფრო რაციონალური
- 13 წესის ფაილი იყოს ერთი დიდი ფაილი ცამეტი მცირე ფაილის ნაცვლად
- ფაზის ფაილებში სიდიდე იცვლება ცამეტ კვირაში

ცვლილებები 03_CHANGELOG.md-ში დარეგისტრირდება.

---

## შემდეგი ნაბიჯი

თქვენ აირჩიეთ რომელი სესია გადავდგათ პირველი:
- (ა) სესია 1 (Master + Glossary) - ცამეტი ცამეტი ცამეტი ნავიგაცია
- (ბ) სესია 2 (Philosophy Deep) - ფილოსოფიური ფუნდამენტი
- (გ) ცამეტი ცამეტი Tier 1-ის ხუთი ფაილი (პრიორიტეტი)
- (დ) რომელიმე კონკრეტული ფაილი (მიუთითეთ ნომერი)

---

## წყაროები

- ALEKSANDRA_BRAIN v4.0 (CLAUDE.md-ში დახურული ფაზები)
- [ALEKSANDRA_BRAIN_v5_ARCHITECTURE.md](computer://C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\ALEKSANDRA_BRAIN_v5_ARCHITECTURE.md)
- [ALEKSANDRA_BRAIN_v6_RESEARCH_GROUNDED_ARCHITECTURE.md](computer://C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\ALEKSANDRA_BRAIN_v6_RESEARCH_GROUNDED_ARCHITECTURE.md)
- [ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md](computer://C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md)

**ვერსიის შენიშვნა:** ეს არის v1.0 ფაილების გეგმის. ცვლილებები 03_CHANGELOG.md-ში დაფიქსირდება.
