# Phase 7.2 — Causal Layer: DoWhy + SCM Editor (3 კვირა)

> **ფაზის ID:** 7.2
> **სახელი:** Causal Layer — DoWhy Integration + SCM Editor + do-calculus API
> **ვადა:** 21 დღე (3 კვირა), 2026-09-27 → 2026-10-17
> **მთავარი deliverable:** DoWhy-ით ნაკვები SCM ფენა, do-operator API, კონტრფაქტური query endpoint, საწყისი SCM editor (CausalNex backend)
> **წინაპირობა:** Phase 7.1 verifier 9/9 PASS · causal edges populated
> **LLM ბიუჯეტი:** $4
> **ფიზიკური ბიუჯეტი:** $0 ნამატი (DoWhy + CausalNex ლოკალური; PyTorch CPU საკმარისი)

---

## 0. ფაზის სახელი, ვადა, წინაპირობა

### 0.1 სკოპი

ფაზა ნერგავს Pearl-ის do-calculus operator-ს API ფენაში: ექიმის კითხვა `P(Bayley_180 | do(Vigabatrin=true, start_day=120))` გადადის DoWhy-ის `CausalModel.estimate_effect()`-ში, აბრუნებს point-estimate + confidence interval + sensitivity report-ს. CausalNex-ით აიგება საწყისი SCM editor (Phase 7.6-ში frontend-ი).

### 0.2 ფაზის ვადა

| საზომი | მნიშვნელობა |
|---|---|
| სტარტი | 2026-09-27 |
| დასრულება | 2026-10-17 |
| სამუშაო დღეები | 15 |
| შაკოს ფოკუს საათები | ~45 |
| Verifier gate | Phase 7.3-მდე 12/12 PASS |

### 0.3 წინაპირობების checklist

| # | წინაპირობა | სტატუსი |
|---|---|---|
| 1 | Phase 7.1 closure | gate |
| 2 | CausalNode + edges populated in Neo4j | ✅ from 7.1 |
| 3 | DoWhy 0.11.1+ installable | [pywhy/dowhy](https://github.com/py-why/dowhy) |
| 4 | CausalNex pinned | [mckinsey/causalnex](https://github.com/mckinsey/causalnex) |
| 5 | PyTorch CPU wheel (≤ 200 MB) | `torch==2.4.*` |
| 6 | NetworkX 3.x | DoWhy dependency |

---

## 1. დღიური Breakdown (15 დღე)

### კვირა 1 — DoWhy bootstrap + SCM build (Days 1-5)

| Day | ფოკუსი | ნაბიჯი | Outcome |
|---|---|---|---|
| 1 | Install + smoke | `uv add dowhy==0.11.* causalnex==0.12.* torch==2.4.* networkx==3.*` + 4-node toy SCM | `import dowhy` works |
| 2 | Neo4j → NetworkX adapter | `brain/causal/graph_loader.py` reads CausalNode + edges → `nx.DiGraph` | 571-node DAG loaded |
| 3 | DAG validation | acyclicity check, connectivity, dangling-node detection | report committed |
| 4 | SCM specification | `brain/causal/scm.py` — `SCM(nodes, edges, treatment, outcome, confounders)` Pydantic | 1 reference SCM (Vigabatrin → seizure_freq) |
| 5 | DoWhy CausalModel build | `dowhy.CausalModel(data, graph, treatment, outcome).identify_effect()` returns backdoor expression | identifies 3 confounders correctly |

### კვირა 2 — do-calculus API + Counterfactuals (Days 6-10)

| Day | ფოკუსი | ნაბიჯი | Outcome |
|---|---|---|---|
| 6 | Estimation methods | linear_regression, propensity_score_matching, instrumental_variable wrapper | 3 estimators tested |
| 7 | do() API endpoint | `POST /api/causal/do` → `{treatment, value, outcome} → {effect, ci_95, method}` | FastAPI endpoint live |
| 8 | Counterfactual API | `POST /api/causal/counterfactual` — `{factual, intervention} → {predicted_outcome}` via SCM mechanism | endpoint tested |
| 9 | Sensitivity analysis | `refute_estimate` with `random_common_cause`, `placebo_treatment_refuter` | refutation report per estimate |
| 10 | Belief-state cross-link | `do()` result writes EvidenceItem to `belief_evidence` table | causal → belief flow works |

### კვირა 3 — SCM editor backend + Verifier (Days 11-15)

| Day | ფოკუსი | ნაბიჯი | Outcome |
|---|---|---|---|
| 11 | CausalNex structure learning | NOTEARS + DAGitty-style algorithm on Phase 2.5 supporting_papers data | proposed DAG vs hand-curated diff |
| 12 | SCM CRUD endpoints | `POST/GET/PATCH/DELETE /api/scm/{id}` — edit nodes + edges + properties | OpenAPI spec generated |
| 13 | Audit log + version history | every SCM mutation → `scm_audit_log` table; SCM has `version` int | rollback by version works |
| 14 | Multi-SCM workspace | user can save N SCMs (default + alternative hypotheses) | 3 SCMs persisted |
| 15 | Verifier + exit report | 12 checks PASS, tag `v7.2.0-causal-layer` | green |

---

## 2. Deliverables

### 2.1 კოდი

| ფაილი | LOC |
|---|---|
| `brain/causal/__init__.py` | 5 |
| `brain/causal/graph_loader.py` | 200 |
| `brain/causal/scm.py` | 250 |
| `brain/causal/estimators.py` | 320 |
| `brain/causal/counterfactual.py` | 180 |
| `brain/causal/sensitivity.py` | 150 |
| `brain/causal/api.py` (FastAPI router) | 280 |
| `brain/causal/structure_learning.py` (CausalNex wrapper) | 200 |
| `brain/causal/tests/` (≥ 18 tests) | 500 |
| `migrations/018_scm_tables.sql` | 100 |
| `scripts/verify_phase_7_2.py` | 280 |

ჯამური LOC: ~2465.

### 2.2 SQL schema

```sql
-- migrations/018_scm_tables.sql
CREATE TABLE scms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    version INT NOT NULL DEFAULT 1,
    description TEXT,
    graph_json JSONB NOT NULL,  -- {nodes:[], edges:[]}
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (name, version)
);

CREATE TABLE scm_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scm_id UUID REFERENCES scms(id),
    operation TEXT NOT NULL CHECK (operation IN ('create','update','delete','revert')),
    diff JSONB,
    actor TEXT NOT NULL,
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE causal_estimates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scm_id UUID REFERENCES scms(id),
    treatment TEXT NOT NULL,
    outcome TEXT NOT NULL,
    method TEXT NOT NULL,
    effect NUMERIC NOT NULL,
    ci_low NUMERIC,
    ci_high NUMERIC,
    refutation_passed BOOLEAN,
    raw_result JSONB,
    computed_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE scms ENABLE ROW LEVEL SECURITY;
ALTER TABLE scm_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE causal_estimates ENABLE ROW LEVEL SECURITY;
```

### 2.3 API contract (excerpt)

```http
POST /api/causal/do
Content-Type: application/json

{
  "scm_id": "uuid",
  "treatment": "vigabatrin",
  "treatment_value": true,
  "outcome": "seizure_frequency",
  "method": "propensity_score_matching",
  "confidence_level": 0.95
}

→ 200 OK
{
  "effect": -0.42,
  "ci_low": -0.61,
  "ci_high": -0.21,
  "units": "seizures/day",
  "method": "propensity_score_matching",
  "n_samples": 4000,
  "identified_estimand": "E[Y|do(T=1)] - E[Y|do(T=0)] = E[E[Y|T,X]]",
  "refutation": {
    "random_common_cause": "passed",
    "placebo_treatment": "passed"
  }
}
```

---

## 3. Blocking Dependencies

| დამოკიდებულება | ბლოკავს | Mitigation |
|---|---|---|
| Phase 7.1 causal edges + properties | DAG construction | gate |
| DoWhy 0.11.1+ stability | core API | pin; fallback 0.10 |
| PyTorch CPU wheel size (Railway) | deployment | use slim image; CPU-only |
| NetworkX 3.x | DAG ops | pin |
| Phase 7.0 belief tables | counterfactual writeback | required |
| Aleksandra observational data (≥ 30 voice notes + 3 MRI) | estimator input | ✅ from Phase 5 + 1 |

---

## 4. Verifier Checklist (12 ცდა)

| # | Check ID | აღწერა | PASS criterion |
|---|---|---|---|
| 1 | `check_7_2_01` | DoWhy import + version | `dowhy.__version__ ≥ 0.11.1` |
| 2 | `check_7_2_02` | Graph loader | NetworkX DAG with ≥ 568 nodes |
| 3 | `check_7_2_03` | DAG acyclicity | `nx.is_directed_acyclic_graph(g) == True` |
| 4 | `check_7_2_04` | Confounder identification | for reference SCM (Vigabatrin→seizure) 3 confounders identified |
| 5 | `check_7_2_05` | do() API | POST returns effect within 30s |
| 6 | `check_7_2_06` | Counterfactual API | POST returns predicted outcome |
| 7 | `check_7_2_07` | Sensitivity refutation | random_common_cause refuter runs without error |
| 8 | `check_7_2_08` | Belief writeback | causal estimate creates `belief_evidence` row |
| 9 | `check_7_2_09` | SCM CRUD | create + update + revert all succeed |
| 10 | `check_7_2_10` | Audit log | every SCM mutation logged |
| 11 | `check_7_2_11` | Multi-SCM | 3 SCMs persisted with unique names |
| 12 | `check_7_2_12` | Regression | Phase 1-7.1 verifiers all GREEN |

---

## 5. Rollback Strategy

### 5.1 Triggers

| Trigger | Severity | Action |
|---|---|---|
| Day 3: DAG has cycles | CRITICAL | revisit Phase 7.1 edge orientation; pause Phase 7.2 |
| Day 6: estimators all return NaN | HIGH | reduce data scope, use synthetic data for API contract validation |
| Day 9: refutation fails > 50% of estimates | MEDIUM | document as known limitation; ship API with refutation flag |
| Day 15: verifier ≤ 9/12 | HIGH | 1-week extension |

### 5.2 Rollback procedure

```sql
BEGIN;
DROP TABLE IF EXISTS causal_estimates CASCADE;
DROP TABLE IF EXISTS scm_audit_log CASCADE;
DROP TABLE IF EXISTS scms CASCADE;
COMMIT;
```

```bash
git revert <range>
```

### 5.3 Compatibility

Phase 7.0 + 7.1 unchanged. Phase 7.2 ემატება ფენად (no destructive ops).

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
| Day 4 SCM design discussion | 5 | Sonnet 4.5 | $1.00 |
| Day 7-8 API contract review | 3 | Opus 4.5 (escalation) | $1.20 |
| Day 9 refuter interpretation | 4 | Sonnet 4.5 | $0.80 |
| Day 11 NOTEARS output review | 3 | Sonnet 4.5 | $0.60 |
| Buffer | — | — | $0.40 |
| **Total** | **~15** | — | **$4.00** |

### 6.3 Project cumulative

| ფაზა | Cap | Cumulative |
|---|---|---|
| Through 7.1 | $68 | ~$16 |
| Phase 7.2 | $4 | $20 |

---

## 7. Sprint Retrospective Template

`docs/PHASE_7_2_RETROSPECTIVE.md`.

### 7.1 Metrics

| Metric | Target | Actual |
|---|---|---|
| Verifier PASS | 12/12 | __/12 |
| LLM spend | ≤ $4 | __ |
| do() API p50 latency | < 5s | __ |
| do() API p95 latency | < 30s | __ |
| Refutation pass rate | ≥ 70% | __% |
| SCMs created | ≥ 3 | __ |

### 7.2 Sections

- What worked / didn't
- DoWhy estimator chosen (linear vs PSM vs IV) — why
- Counterfactual queries answered (samples + plausibility check)
- Carry-forward to Phase 7.3 (simulation engine needs SCM as input)

---

## 8. წყაროები

### 8.1 Causal inference tooling

- [DoWhy GitHub py-why](https://github.com/py-why/dowhy) — Apache 2.0
- [DoWhy user guide](https://www.pywhy.org/dowhy/v0.11.1/user_guide/intro.html)
- [CausalNex GitHub mckinsey/causalnex](https://github.com/quantumblacklabs/causalnex)
- [EconML GitHub](https://github.com/py-why/EconML) — heterogeneous treatment effects (Phase 7.3 candidate)
- [NetworkX docs](https://networkx.org/documentation/stable/) — DAG operations

### 8.2 Causal theory

- Pearl J. _Causality_ 2nd ed. (2009) Cambridge UP
- Pearl J., Glymour M., Jewell N. _Causal Inference in Statistics: A Primer_ (2016) Wiley
- [Hernán M. & Robins J. _Causal Inference: What If_ (2020)](https://www.hsph.harvard.edu/miguel-hernan/causal-inference-book/) — open access PDF
- [NOTEARS algorithm Zheng et al. 2018](https://papers.nips.cc/paper/2018/hash/e347c51419ffb23ca3fd5050202f9c3d-Abstract.html)

### 8.3 Clinical reference for Vigabatrin reference SCM

- [Vigabatrin in infantile spasms PMID 32713850](https://pubmed.ncbi.nlm.nih.gov/32713850/)
- [Confounders in HIE seizure outcome PMID 35234567](https://pubmed.ncbi.nlm.nih.gov/35234567/) (illustrative; verify pre-citation)

### 8.4 პროექტის ფაილები

- [71_PHASE_7_1_MEMORY_REFACTOR_2W.md](./71_PHASE_7_1_MEMORY_REFACTOR_2W.md)
- [ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md §6](../../ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md)

---

**შემდეგი:** [73_PHASE_7_3_SIMULATION_ENGINE_3W.md](./73_PHASE_7_3_SIMULATION_ENGINE_3W.md)
