# Phase 7.3 — Simulation Engine: Monte Carlo + TVB Docker (3 კვირა)

> **ფაზის ID:** 7.3
> **სახელი:** Simulation Engine — Monte Carlo over Posteriors + TVB Docker Neural-Mass Simulation
> **ვადა:** 21 დღე (3 კვირა), 2026-10-18 → 2026-11-07
> **მთავარი deliverable:** ფენა A — PyMC Monte Carlo 10,000-sample scenario rollout; ფენა B — TheVirtualBrain Docker neural-mass simulation; Simulation Studio API
> **წინაპირობა:** Phase 7.2 verifier 12/12 PASS · DoWhy do() API ცოცხალი
> **LLM ბიუჯეტი:** $4
> **ფიზიკური ბიუჯეტი:** +$10/თვე (TVB Docker Railway-ზე) ან $0 (ლოკალური ღამის ცდები)

---

## 0. ფაზის სახელი, ვადა, წინაპირობა

### 0.1 სკოპი

ფაზა აშენებს ციფრული ტყუპის "წინ წახვევის" ფუნქციას: ექიმის სცენარი (`{vigabatrin: day 200, cord_blood: day 280, physio: daily}`) იქცევა 10,000 Monte Carlo trajectory-ად 400 დღემდე, თითო trajectory აერთიანებს Phase 7.0-ის posterior-ს Phase 7.2-ის do-operator-ით; პარალელურად TVB Docker აანგარიშებს ნეირონული მასების დონის სიმულაციას რჩეული ცვლადებისთვის (seizure frequency, brainstem activity).

### 0.2 ფაზის ვადა

| საზომი | მნიშვნელობა |
|---|---|
| სტარტი | 2026-10-18 |
| დასრულება | 2026-11-07 |
| სამუშაო დღეები | 15 |
| შაკოს ფოკუს საათები | ~50 |
| Verifier gate | Phase 7.4-მდე 13/13 PASS |

### 0.3 წინაპირობების checklist

| # | წინაპირობა | სტატუსი |
|---|---|---|
| 1 | Phase 7.2 closure | gate |
| 2 | TVB Docker image pulled | [TVB DockerHub](https://hub.docker.com/r/thevirtualbrain/tvb-run) |
| 3 | Railway $10/თვე upgrade approved (or local-only mode) | შაკოს decision |
| 4 | Posteriors for 13 dims sampled | ✅ Phase 7.0 |
| 5 | SCMs available (≥ 1 reference SCM) | ✅ Phase 7.2 |
| 6 | TVB-C++ backend optional check | [TVB-C++ Wiley 2026](https://advanced.onlinelibrary.wiley.com/doi/10.1002/advs.202406440) |

---

## 1. დღიური Breakdown (15 დღე)

### კვირა 1 — Monte Carlo engine (Days 1-5)

| Day | ფოკუსი | ნაბიჯი | Outcome |
|---|---|---|---|
| 1 | Scenario specification | `brain/sim/scenario.py` — `Scenario(interventions:[Intervention], horizon_days:int, n_samples:int)` Pydantic | reference scenario instantiated |
| 2 | Trajectory generator | `brain/sim/trajectory.py` — for each sample: draw from 13-d posterior, apply do() per intervention, integrate to horizon | 100-sample test runs in <60s |
| 3 | Aggregator | per-day mean, sd, hdi_80, hdi_95 across trajectories | summary DataFrame |
| 4 | Comparison engine | scenario A vs scenario B → delta + p(A > B) per outcome | reference comparison report |
| 5 | Caching | scenario_hash → cached result; replay returns in <1s | cache hit ratio measured |

### კვირა 2 — TVB Docker integration (Days 6-10)

| Day | ფოკუსი | ნაბიჯი | Outcome |
|---|---|---|---|
| 6 | TVB Docker bootstrap | `docker run -d --name tvb thevirtualbrain/tvb-run:2.9.x` | container healthy |
| 7 | Connectome adapter | use TVB default connectome (Hagmann 998-region) as Aleksandra-specific connectome unavailable; flag as placeholder | report committed |
| 8 | Region mask for HIE | apply lesion mask (Phase 1 MRI segmentation) → reduce activity in cystic regions | masked connectome saved |
| 9 | Simulation API | `POST /api/sim/tvb` → `{regions, duration_ms, perturbations} → time-series JSON` | endpoint returns within 5 min for 60s simulation |
| 10 | TVB → belief feedback | TVB seizure-onset-rate output → EvidenceItem for `seizure_frequency` dim | belief update triggered |

### კვირა 3 — Simulation Studio API + Verifier (Days 11-15)

| Day | ფოკუსი | ნაბიჯი | Outcome |
|---|---|---|---|
| 11 | Studio scenario CRUD | `POST/GET/DELETE /api/sim/scenarios` — save named scenarios | 5 sample scenarios saved |
| 12 | Multi-scenario comparison API | `POST /api/sim/compare` with ≥ 2 scenario IDs | matrix output |
| 13 | Histogram export | each scenario emits 13 PNG histograms (ArviZ + Plotly server-side) | snapshots saved |
| 14 | Budget guard | per-run sample cap (n_samples ≤ 10,000), reject larger requests | guard tested |
| 15 | Verifier + exit report | 13/13 PASS, tag `v7.3.0-simulation-engine` | green |

---

## 2. Deliverables

### 2.1 კოდი

| ფაილი | LOC |
|---|---|
| `brain/sim/__init__.py` | 5 |
| `brain/sim/scenario.py` | 200 |
| `brain/sim/trajectory.py` | 380 |
| `brain/sim/aggregator.py` | 180 |
| `brain/sim/compare.py` | 160 |
| `brain/sim/tvb_adapter.py` | 320 |
| `brain/sim/api.py` (FastAPI) | 300 |
| `brain/sim/viz.py` (Plotly server-side) | 180 |
| `brain/sim/cache.py` | 100 |
| `brain/sim/tests/` (≥ 20 tests) | 600 |
| `migrations/019_sim_tables.sql` | 90 |
| `scripts/verify_phase_7_3.py` | 320 |
| `infra/tvb-docker-compose.yml` | 40 |

ჯამური LOC: ~2785.

### 2.2 SQL

```sql
-- migrations/019_sim_tables.sql
CREATE TABLE scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    scenario_json JSONB NOT NULL,
    scenario_hash TEXT NOT NULL UNIQUE,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE simulation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID REFERENCES scenarios(id),
    engine TEXT NOT NULL CHECK (engine IN ('monte_carlo','tvb','combined')),
    n_samples INT,
    duration_ms_sim INT,
    elapsed_seconds NUMERIC,
    summary_json JSONB NOT NULL,
    completed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE simulation_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_a_id UUID REFERENCES scenarios(id),
    scenario_b_id UUID REFERENCES scenarios(id),
    delta_json JSONB NOT NULL,
    p_a_better_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE scenarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulation_comparisons ENABLE ROW LEVEL SECURITY;
```

### 2.3 Scenario format example

```json
{
  "name": "vigabatrin_d200_cordblood_d280_physio_daily",
  "interventions": [
    {"type": "drug", "name": "vigabatrin", "start_day": 200, "dose_mg_kg": 50},
    {"type": "cell_therapy", "name": "cord_blood", "infusion_day": 280},
    {"type": "rehab", "name": "physiotherapy", "frequency": "daily", "start_day": 1}
  ],
  "horizon_days": 400,
  "n_samples": 10000,
  "engines": ["monte_carlo"],
  "outcomes": ["cyst_volume","seizure_frequency","eye_tracking","gmfcs","bayley_cog"]
}
```

### 2.4 Output example (matches ARCHITECTURE §4.2)

| Dimension | Day-400 expected | 80% CI |
|---|---|---|
| Cyst volume | 11.5% | 9.8 – 13.4% |
| Seizure frequency | 0.4/day | 0.2 – 0.9 |
| Eye tracking | 8.2 sec | 5.5 – 11.0 |
| GMFCS | 3.1 | 2 – 4 |
| Bayley cognition | 65 | 55 – 78 |

---

## 3. Blocking Dependencies

| დამოკიდებულება | ბლოკავს | Mitigation |
|---|---|---|
| Phase 7.0 posteriors | Monte Carlo input | gate |
| Phase 7.2 do-operator | trajectory intervention logic | gate |
| TVB Docker image | Phase 7.3 ფენა B | local fallback if Railway not approved |
| Railway $10 budget | TVB hosted | local-only mode = $0 |
| Aleksandra MRI segmentation (Phase 1) | TVB region mask | ✅ available |
| Plotly server-side rendering (kaleido) | histogram PNG export | `uv add kaleido` |

---

## 4. Verifier Checklist (13 ცდა)

| # | Check ID | აღწერა | PASS criterion |
|---|---|---|---|
| 1 | `check_7_3_01` | Scenario schema validation | reject invalid scenario in <100ms |
| 2 | `check_7_3_02` | 100-sample MC run | completes < 60s |
| 3 | `check_7_3_03` | 10,000-sample MC run | completes < 10 min |
| 4 | `check_7_3_04` | Aggregator output | per-day mean+sd+hdi80+hdi95 for all 13 dims |
| 5 | `check_7_3_05` | Comparison engine | p(A > B) ∈ [0,1] for all 13 outcomes |
| 6 | `check_7_3_06` | Cache hit | repeated scenario_hash returns in <1s |
| 7 | `check_7_3_07` | TVB container health | `docker ps` shows healthy or local skip flag |
| 8 | `check_7_3_08` | TVB simulation | 60s sim completes in <5 min |
| 9 | `check_7_3_09` | TVB → belief feedback | belief_evidence row created |
| 10 | `check_7_3_10` | Histogram export | 13 PNGs per scenario, size > 10 KB |
| 11 | `check_7_3_11` | n_samples cap enforced | n_samples=20000 rejected with 422 |
| 12 | `check_7_3_12` | Per-run uncertainty guard | if avg posterior sd > 50% mean, refuse simulation (RULE 10) |
| 13 | `check_7_3_13` | Regression | Phase 1-7.2 verifiers all GREEN |

---

## 5. Rollback Strategy

### 5.1 Triggers

| Trigger | Severity | Action |
|---|---|---|
| Day 2: trajectory generator produces NaN | CRITICAL | restart with simpler 5-dim subset; flag as Phase 7.3 v1 scope reduction |
| Day 6: TVB Docker > 2 GB image, Railway plan insufficient | MEDIUM | drop to local-only mode; defer hosted TVB to Phase 8 |
| Day 9: TVB simulation > 30 min per run | HIGH | reduce duration_ms or region count; flag TVB-C++ backend as required for Phase 8 |
| Day 15: verifier ≤ 10/13 | HIGH | 1-week extension; if TVB checks fail, ship MC-only and defer TVB |

### 5.2 Rollback SQL

```sql
BEGIN;
DROP TABLE IF EXISTS simulation_comparisons CASCADE;
DROP TABLE IF EXISTS simulation_runs CASCADE;
DROP TABLE IF EXISTS scenarios CASCADE;
COMMIT;
```

### 5.3 TVB container cleanup

```bash
docker stop tvb && docker rm tvb
docker rmi thevirtualbrain/tvb-run:2.9.x  # optional, frees ~3 GB
```

### 5.4 Compatibility

Phase 7.0-7.2 unchanged; Phase 7.3 additive.

---

## 6. LLM Spend Tracking

### 6.1 Cap

| კატეგორია | Cap |
|---|---|
| Total | $4 |
| Per-day | $0.50 |
| Per-call | $0.30 |

### 6.2 Breakdown

| Activity | Calls | Model | Cost |
|---|---|---|---|
| Day 1 scenario schema review | 3 | Sonnet 4.5 | $0.60 |
| Day 6-7 TVB Docker config debug | 4 | Sonnet 4.5 | $0.80 |
| Day 9 TVB output interpretation | 5 | Opus 4.5 | $1.50 |
| Day 13 Plotly viz code-review | 3 | Sonnet 4.5 | $0.60 |
| Day 15 KA exit report | 2 | Sonnet 4.5 | $0.50 |
| **Total** | **~17** | — | **$4.00** |

### 6.3 Cumulative project

| ფაზა | Cap | Cumulative |
|---|---|---|
| Through 7.2 | $72 | ~$20 |
| Phase 7.3 | $4 | $24 |

---

## 7. Sprint Retrospective Template

`docs/PHASE_7_3_RETROSPECTIVE.md`.

### 7.1 Metrics

| Metric | Target | Actual |
|---|---|---|
| Verifier PASS | 13/13 | __/13 |
| LLM spend | ≤ $4 | __ |
| 10K-sample MC runtime | < 10 min | __ |
| TVB 60s sim runtime | < 5 min | __ |
| Scenarios saved | ≥ 5 | __ |
| Cache hit ratio | ≥ 30% | __% |
| Compute cost (Railway TVB) | ≤ $10/თვე | __ |

### 7.2 Sections

- What worked / didn't
- TVB hosting decision (local vs Railway) — finalized
- Scope of Phase 7.3 if reduced (MC-only?)
- Carry-forward to Phase 7.4 (active learning needs simulation EIG)

---

## 8. წყაროები

### 8.1 Simulation tooling

- [TheVirtualBrain documentation](https://docs.thevirtualbrain.org/)
- [TVB DockerHub](https://hub.docker.com/r/thevirtualbrain/tvb-run)
- [TVB-C++ backend Wiley 2026](https://advanced.onlinelibrary.wiley.com/doi/10.1002/advs.202406440)
- [PyMC predictive sampling](https://www.pymc.io/projects/docs/en/stable/api/generated/pymc.sample_posterior_predictive.html)

### 8.2 Connectome reference

- [Hagmann P. et al. 998-region connectome PLoS Bio 2008](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.0060159)

### 8.3 Visualization

- [Plotly Python docs](https://plotly.com/python/)
- [Kaleido image export](https://github.com/plotly/Kaleido)
- [ArviZ posterior plots](https://www.arviz.org/en/latest/api/plots.html)

### 8.4 Clinical scenario sources

- [Vigabatrin pediatric dose PMID 32713850](https://pubmed.ncbi.nlm.nih.gov/32713850/)
- [Cord blood infusion Duke EAP protocol](https://www.dukehealth.org/locations/marcus-center-cellular-cures) — protocol details via Phase 4 outreach
- [Physiotherapy frequency Cochrane 2022 PMID 36165493](https://pubmed.ncbi.nlm.nih.gov/36165493/) (verify pre-citation)

### 8.5 პროექტის ფაილები

- [72_PHASE_7_2_CAUSAL_LAYER_3W.md](./72_PHASE_7_2_CAUSAL_LAYER_3W.md)
- [ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md §7](../../ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md)

---

**შემდეგი:** [74_PHASE_7_4_ACTIVE_LEARNING_2W.md](./74_PHASE_7_4_ACTIVE_LEARNING_2W.md)
