# Phase 7.3. Simulation Engine. Layers A + C (KA Summary)

**დახურულია:** 2026-05-25
**მომდევნო ფაზა:** Phase 7.3 Layer B (TheVirtualBrain Docker, ცალკე dispatch) + Phase 7.4 (Active Queries, ~2 კვირა)
**Verifier:** `verify_phase_7_3 --mode code-complete` → **10/13 PASS · 3 SKIP · 0 FAIL · GREEN** (Layer B-ის 3 ცდა SKIP-ი TVB Docker-ის გასაშვებად ცალკე სესია მოითხოვს)

---

## რა აშენდა

Phase 7.3 ფარავს 15-დღიან sprint-ს, რომელიც აშენებს Monte Carlo trajectory engine-ს Phase 7.2-ის SCM-ზე და Phase 7.0-ის 13-განზომილებიან posterior-ზე. ფაზა გაიყო სამ ფენად: Layer A (Days 1-5, MC core), Layer B (Days 6-10, TVB neural-mass simulation), Layer C (Days 11-15, Studio + viz + verifier).

ამ სესიამ აშენა Layer A-ის გასწვრივ Layer C. Layer B (TVB Docker) ცალკე dispatch-ი მოითხოვს — `docker run` უფლება + Railway slot ამ სესიის სკოპში არ ფიქსირდება.

### Layer A (Days 1-5, წინა სესია)

- **Scenario Pydantic** + 4 ტიპის Intervention (`drug`, `cell_therapy`, `rehab`, `manual_dimension_shift`).
- **Trajectory generator** numpy-direct samplers-ით (PyMC overhead-ის გარეშე) 100 sample-ი 0.8 წმ-ში, 10000 sample-ი 11.6 წმ-ში.
- **Aggregator** ArviZ HDI 80% + 95% + mean + sd per (outcome, day). Reference scenario 5 outcomes × 401 დღე = 2005 OutcomeSummary რიგი.
- **Compare engine** A vs B per outcome per day, p(A better than B), interpretation ∈ {A_better, B_better, tie, ambiguous}.
- **In-process LRU cache** scenario_hash-ით, 32 entry capacity, cache hit 0.1 ms-ში.

### Layer C (Days 11-15, ეს სესია)

- **Migration 019 SQL** — 3 ახალი ცხრილი (`scenarios`, `simulation_runs`, `simulation_comparisons`), purely additive, RLS migration 018-ის pattern-ით.
- **Studio CRUD persistence** `brain/sim/persistence.py`-ში — `save_scenario`, `get_scenario`, `list_scenarios`, `delete_scenario`, `save_simulation_run`, `save_scenario_comparison`. DRY_RUN sentinel-ი როდესაც `SUPABASE_DB_URL` unset (Phase 7.2-ის precedent-ი).
- **Framework-agnostic Studio API handlers** `brain/sim/api.py`-ში — Pydantic request / response Pydantic models + 3 handler ფუნქცია (`handle_save_scenario`, `handle_list_scenarios`, `handle_compare_scenarios`). FastAPI dependency-ი არ შეიქმნა (Phase 7.6 frontend-ი mount-ი იცის).
- **Budget guard** — `BudgetGuardError` მაშინ raise-დება როცა `n_samples > 10_000` ან 13-დან 7-ზე ნაკლები dim-ი აკმაყოფილებს `sd/mean <= 0.5`-ს. Reference scenario გადის ზუსტად 7/13 boundary-ით.
- **matplotlib PNG export** `brain/sim/viz.py`-ში — `render_scenario_histogram`, `render_scenario_summary_panel`, `render_comparison_panel`. PNG-ი 25-29 KB-ი (verifier check 10 floor 10 KB).
- **13-check verifier** (`scripts/verify_phase_7_3.py`) dual-mode (code-complete + production); JSON log emit-ი `v7_architecture/foundation_logs/`-ში.

### დიზაინ-დეცისიები

ცენტრალური: **DRY_RUN-when-`SUPABASE_DB_URL`-unset pattern** Phase 7.2-დან გადმოვიდა. ყოველი persistence ფუნქცია DB-ის გარეშე ბრუნდება deterministic `"DRY_RUN:<sha256>"` sentinel-ი. code-complete pytest 100% infra-ფრიე მუშავდება.

ცვლილება: **Plotly → matplotlib substitution**. Phase 7.3 spec ფარდდება Plotly + Kaleido server-side rendering-ით, მაგრამ `.venv-v7` arsenal-ში Plotly არ არის. matplotlib უკვე `brain/belief/viz.py`-ის hard dep-ი, PNG-ი min 25 KB ფაქტურდება. spec-ის შინაარსი (PNG snapshot-ი) დაცული.

**Hard delete** scenarios-ისთვის, soft-tombstone-ი არა. Scenarios — user input, Studio UX-ი delete-ი მოითხოვს. Audit lineage `simulation_runs.completed_at`-ში ცხოვრობს. Migration 019-ი `ON DELETE CASCADE` FK-ით runs + comparisons-ი ავტომატურად reap-დება.

---

## რა იცვლება ცოლისთვის

Phase 7.3 თავად **არ ცვლის** ცოლის ყოველდღიურ გამოცდილებას. Telegram briefing-ი, viewer-ი, weekly brief, ყველაფერი იგივე ნაკადით მიდის, რადგან Simulation Studio API frontend-ში არ exposed-ი არ არის Phase 7.6-მდე.

რას აშენებს მომავლისთვის: Phase 7.3-ის შემდეგ BRAIN-ი ფლობს "forward simulation" შესაძლებლობას. ექიმის სავარაუდო კითხვა "თუ vigabatrin-ი ჯერჯერობით day-200-ში დავიწყე და day-280-ში cord blood infusion-ი ექნა, რა გვექნება day-400-ში?" გადადის 10000 Monte Carlo trajectory-ში Phase 7.0-ის posterior-ი + Phase 7.2-ის do() operator-ით, ბრუნდება scenario summary 5 outcome-ით (cyst volume, seizure freq, eye tracking, GMFCS, Bayley cognitive) + per-day HDI 80% / 95%. ეს უნარი Phase 7.4-ში "active queries"-ით გაფართოვდება და Phase 7.6-ში viewer-ში გამოჩნდება Simulation Studio panel-ით.

---

## რა იცვლება ექიმისთვის

| ფაქტი | ცვლის რას |
|---|---|
| Scenario CRUD API exposed | Dr. Hien / Dr. Maypole / Dr. August შეძლებენ ჩამოწერონ თავიანთი ჰიპოთეტური scenario-ი ("vigabatrin earlier", "cord blood later", "physio twice daily"), დაფიქსირონ system-ში named scenario-ად |
| 10K MC trajectory < 12 წმ | რეალურ დროში "what if" კითხვა ბრუნდება 5 outcome-ით + 80% / 95% CI-ით |
| `compare_scenarios` p(A better) | ორი scenario-ის შედარება (e.g. "current plan" vs "alternative") ფიქსირდება pairwise p(A>B) per outcome, interpretation-ით {A_better / B_better / tie / ambiguous} |
| Budget guard | scenario-ის n_samples > 10000 ცდა ან uncertainty > 50% mean ცდა fast-fail BudgetGuardError-ით — clinician იღებს clear feedback თუ ჰიპოთეზა computationally ან inferentially ცარიელია |

ეს არ შლის ექიმის გადაწყვეტილებას. ის ფარავს იმ ხარვეზს, რომ ვიდრე Phase 7.3-მდე "vigabatrin earlier-ი დახმარდება?" იყო hypothetical-ი ცოდნის გრაფში. Phase 7.3-ის შემდეგ ის ფიქსირდება observational posterior-ით + structural causal model-ით + 10000 forward-projection trajectory-ით + cached comparison-ით.

---

## რა იცვლება შაკოსთვის

**4 ციფრი:**
- **~1765 LOC** ჯამში Days 11-15-ში (persistence 480 + api 286 + viz 230 + verifier 535 + tests 596 + migration 019 SQL 175 + runbook 142 + __init__ update)
- **493 / 493 fast pytest PASS** (449 baseline + 44 ახალი brain/sim/tests-ში; zero regression)
- **10/13 verifier PASS + 3 SKIP** (Layer B-ის 3 SKIP-ი TVB Docker-ის გასაშვებად ცალკე dispatch-ი მოითხოვს)
- **$0.00 LLM spend** 5-დღიან Days 11-15 phase-ში ($4 cap full headroom; total project ~$9.52 / $60 cap, ~16%)

**4 ფაილი გასახედი:**
- `brain/sim/persistence.py` — Studio CRUD + scenario_hash idempotency + DRY_RUN fallback. 20 ტესტი.
- `brain/sim/api.py` — Pydantic handlers + BudgetGuardError + check_simulation_budget. 16 ტესტი.
- `brain/sim/viz.py` — matplotlib PNG histogram + summary panel + A-vs-B comparison panel. 8 ტესტი.
- `scripts/verify_phase_7_3.py` — 13 check, dual-mode (code-complete + production), JSON log emit-ი.

**3 დიდი დიზაინ-დეცისია:**

ერთი. **Plotly → matplotlib substitution**. Spec ფარდდება server-side Plotly + Kaleido-ით, მაგრამ ცარიელ venv-ში Plotly არ არის. matplotlib უკვე belief layer-ში მუშავდება, PNG-ი 25-29 KB-ი ფაქტურდება (10 KB floor verifier check 10-ის). შინაარსი დაცული, infra change-ი 0.

ორი. **DRY_RUN-when-DSN-unset pattern carried from Phase 7.2**. ყოველი CRUD ფუნქცია `os.environ.get('SUPABASE_DB_URL')` check-ით ბრუნდება `"DRY_RUN:<sha256>"` sentinel-ი DB-ის გარეშე. code-complete pytest 100% infrastructure-free მუშავდება. trade-off: production mode-ში check-ის flip-ი ცალკე verifier run-ი მოითხოვს (`--mode production`).

სამი. **Hard delete on scenarios** (vs Phase 7.2 SCM-ის NotImplementedError soft-tombstone). Scenario-ი user input-ი, audit data-ი არა. Studio UX-ი delete-ი მოითხოვს. Migration 019-ი `ON DELETE CASCADE` FK-ით runs + comparisons-ი automatically reap-დება. audit lineage `simulation_runs.completed_at` + `summary_json`-ში ფიქსირდება.

---

## შაკოსგან რა გვჭირდება ფაზის სრულად დასახურად

**4-ნაბიჯიანი Supabase სესია (~10 წთ მთლიანი):**

| № | სამუშაო | სავარაუდო დრო |
|---|---|---|
| 1 | `SUPABASE_DB_URL` env var-ის გაყვანა Supabase Console-დან | 30 წმ |
| 2 | Pre-flight backup: `pg_dump --schema-only > .planning/backups/pre_019/schema.sql` + `--data-only > .../data.sql` | 1-3 წთ |
| 3 | Migration apply: `psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/019_sim_tables.sql` | < 5 წმ |
| 4 | Verification: `\d scenarios` + `\d simulation_runs` + `\d simulation_comparisons` + 3 SELECT count(*) (expect 0) + cross-check migration 016 + 018 ცხრილების row count | 3-5 წთ |
| 5 | `python scripts/verify_phase_7_3.py --mode production` (მოლოდინი: 10/13 PASS + 3 SKIP) | < 30 წმ |
| ბონუსი | `git tag v7.3.0-simulation-engine-layer-a-c` | 1 წმ |

ეს 5 ნაბიჯი არ ბლოკავს Phase 7.4-ის დაწყებას. engineering scope Layer A + Layer C-ისთვის დახურულია. ნაბიჯები არიან "ფაზის pin" გარემოს მიერ.

**მეორე dispatch (Layer B, TVB Docker, ~5 დღე):**

| № | სამუშაო | ხანგრძლივობა |
|---|---|---|
| 1 | `docker pull thevirtualbrain/tvb-run:2.9.x` | 5-10 წთ (~3 GB image) |
| 2 | `brain/sim/tvb_adapter.py` build (~320 LOC) | 3 დღე |
| 3 | TVB → belief_evidence wiring | 1 დღე |
| 4 | Verifier re-run, SKIP gates flip to PASS | 1 დღე |

დეტალური runbook: [scripts/migrations/019_runbook.md](../scripts/migrations/019_runbook.md).

---

## ფული

| ხარჯი | რაოდენობა |
|---|---|
| Phase 7.3 Layer C Days 11-15 LLM spend | **~$0.00 / $4 cap** (100% headroom) |
| Phase 7.3 Layer A Days 1-5 LLM spend (წინა სესია) | ~$0.00 (deterministic implementation) |
| პროექტის სრული spend | **~$9.52 / $60 cap** (~16% across 11 phases) |
| DB / ინფრასტრუქტურის ნამატი | $0.00 (იგივე Supabase Free) |
| Compute (Monte Carlo 10K samples) | $0.00 (ლოკალური numpy) |

რატომ ფაზა იაფი დადგა Days 11-15: deterministic Python implementation (Pydantic + psycopg2 + numpy + matplotlib). LLM call-ი არ მოხდა code generation-ში, Monte Carlo simulation deterministic numpy samplers-ით ფარდება, Studio CRUD სრულად ფიქსირებული schema-ზე გაშვებულია.

---

## უსაფრთხოების კედლები

| კედელი | სტატუსი |
|---|---|
| MRI client-side only | აქტიური (Phase 7.3 ვიუერს არ ეხება) |
| PHI redactor + ქართული lint Phase 6-დან | აქტიური; sim modules PHI-ფრიე reference scenario-ით მუშავდება |
| Phase 7.0/7.1/7.2 verifier regression | 10/11 + 8/9 + 12/12 PASS code-complete (carry-over) |
| Phase 1-6.1 verifier regression | 89/89 PASS code-complete (carry-over) |
| Backup pre-flight | `pg_dump` mandatory migration 019-ის apply-ის წინ |
| Hard delete (scenarios) cascades to runs + comparisons | migration 019 FK `ON DELETE CASCADE` |
| service_role RLS bypass policy | migration 019 ენგობს migration 018-ის pattern-ს |
| Budget guard refuses oversized + high-uncertainty scenarios | `BudgetGuardError` API handler-ში |

---

## სად მიდიხართ შემდეგ

| ფაზა | სამუშაო | სავარაუდო ხანგრძლივობა |
|---|---|---|
| **Phase 4 acceptance window** | მონიტორდება closure-მდე (~2026-06-07). v1 release gate. | ~2 კვირა (პარალელურად) |
| **Phase 7.0 / 7.1 / 7.2 / 7.3 production-mode flip** | 4 migration apply-ი (016 + 017 + 018 + 019) ერთად ~30 წთ-ი | ~30-45 წთ |
| **Phase 7.3 Layer B (TVB Docker)** | TheVirtualBrain Docker integration + mechanistic ODE simulation + belief writeback | ~5 დღე (ცალკე dispatch) |
| **Phase 7.4 Active Queries** | "სად ndoba dabalia?" → Telegram-ში შეკითხვა ცოლისთვის (EIG ცოდნის გრაფზე, sim output-ი input) | ~2 კვირა |
| **Phase 7.5 Multi-objective optimization** | "რომელი scenario-ი ფლობს best (cognition * 0.4 + motor * 0.3 + family_readiness * 0.3)?" | ~2 კვირა |
| **Phase 7.6 Frontend mount** | Simulation Studio panel viewer-ში, sandbox-ი + PNG snapshot-ი + comparison view | ~3 კვირა |

---

📄 დეტალური ანგარიში: [docs/PHASE_7_3_LAYER_A_C_EXIT_REPORT.md](PHASE_7_3_LAYER_A_C_EXIT_REPORT.md)
📋 Retrospective + carry-forwards: [docs/PHASE_7_3_LAYER_A_C_RETROSPECTIVE.md](PHASE_7_3_LAYER_A_C_RETROSPECTIVE.md)
🔧 Migration 019 runbook: [scripts/migrations/019_runbook.md](../scripts/migrations/019_runbook.md)
🧠 Simulation engine: [brain/sim/](../brain/sim/)
✅ Verifier: [scripts/verify_phase_7_3.py](../scripts/verify_phase_7_3.py)
