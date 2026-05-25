# Phase 7.0 — Belief State Foundation (4 კვირა)

> **ფაზის ID:** 7.0
> **სახელი:** Belief State Foundation
> **ვადა:** 28 დღე (4 კვირა), 2026-08-15 → 2026-09-12 (ვერსიის სტარტი v6.1-ის closure-ის შემდეგ)
> **მთავარი deliverable:** PyMC ბაიესისეული backend + 13-განზომილებიანი სქემა + posterior update loop
> **წინაპირობა:** v6.1 დახურული (2026-05-24 ✅), v4-ის 89/89 verifier უცვლელად მუშაობს
> **LLM ბიუჯეტი:** $5 ცდისთვის (hard stop)
> **ფიზიკური ბიუჯეტი:** ფაზაში $0 ნამატი (PyMC ლოკალური; TVB Docker გადადის ფაზა 7.3-ში)
>
> ### ⚠️ Foundation status update (2026-05-24)
>
> v7 Foundation **25/25 PASS** — git tag `v7-foundation-ready`. იხ. [`v7_architecture/foundation_logs/00_FOUNDATION_STATUS.md`](../foundation_logs/00_FOUNDATION_STATUS.md).
>
> ფაქტობრივი deviation-ი ამ ფაილისგან:
> - **PyMC pin 5.16.* → 5.18+** (Foundation-ში 5.18+ უკვე დაყენებულია; ეს ფაილში "Day 2"-ად მონიშნულია, რეალურად DONE)
> - **causalnex dropped → pgmpy>=0.1.25** (pandas<2 conflict; Phase 7.2-ში ეფექტი)
> - **jax[metal] → jax[cpu]** (Windows + Intel Arc, no JAX backend)
> - **TVB image 10.6 GB** (doc-ში "2 GB" იყო) + container port `8080` (NOT 8888) — Phase 7.3-ში გათვალე
> - **TVB base image deprecated** ("Updates discontinued after 26.7.x") — Phase 7.3-ში revisit
> - **PyMC fallback to pure-Python sampler** (g++ missing on host) — Phase 7.0 sampler perf check-ში გათვალე
>
> ფაქტობრივი DONE Phase 7.0-დან:
> - **Day 1 (uv + repo scaffold)**: `uv` დაყენებული, `.venv-v7` (Python 3.12.13) ცოცხალი
> - **Day 2 (PyMC install)**: PyMC 5.18+, NumPyro, JAX, ArviZ ყველა import-OK (15/15 PASS)
> - **Day 3 (smoke test)**: `v7_architecture/foundation_logs/smoke_pymc.py` PASS — NUTS 2chains×1000 = 21s, posterior means within tolerance of synthetic truth
>
> Phase 7.0-ის **რეალური სტარტი = Day 4** (numerical sanity check vs analytical Beta-Binomial). **ფაქტობრივი დარჩენილი work: 17 დღე** 20-ის ნაცვლად.

---

## 0. ფაზის სახელი, ვადა, წინაპირობა

### 0.1 სკოპი ერთი წინადადებით

ფაზა აშენებს ციფრული ტყუპის მათემატიკურ ფუნდამენტს — 13 ცვლადის ერთობლივი posterior განაწილებას PyMC-ში — და ნერგავს ბაიესისეული განახლების loop-ს, რომელიც ცნობის შემოსვლისას (MRI ანგარიში, ცოლის ხმოვანი ჩანაწერი, კვლევითი სტატია) prior → likelihood → posterior გადასვლას აანგარიშებს.

### 0.2 ფაზის ვადა

| საზომი | მნიშვნელობა |
|---|---|
| სავარაუდო სტარტი | 2026-08-15 (v6.1 closure + 12 კვირა buffer) |
| დასრულება | 2026-09-12 |
| სამუშაო დღეები | 20 (5 დღე/კვირაში × 4) |
| შაკოს fokus saatebi | ~60 (3 სთ/დღე × 20) |
| Verifier gate | Phase 7.1-ის სტარტამდე უნდა გავიდეს 11/11 |

### 0.3 წინაპირობების checklist

| # | წინაპირობა | წყარო | სტატუსი |
|---|---|---|---|
| 1 | v6.1 დახურული 89/89 verifier-ით | [CLAUDE.md Phase VI.1](../../CLAUDE.md) | ✅ 2026-05-24 |
| 2 | Python 3.12.13 + `.venv-v7` ლოკალურად | [Foundation log 03](../foundation_logs/) | ✅ Foundation 2026-05-24 |
| 3 | uv package manager | [astral-sh/uv](https://github.com/astral-sh/uv) | ✅ Foundation |
| 4 | PyMC 5.18+ / NumPyro / JAX[cpu] / ArviZ imports | `03_imports_check.log` | ✅ 15/15 PASS Foundation |
| 5 | PyMC NUTS sampler smoke test | `foundation_logs/smoke_pymc.py` | ✅ 21s 2chains×1000 PASS |
| 6 | Supabase Postgres write access | v6 migration 012 RLS | ✅ |
| 7 | Neo4j AuraDB Free credentials | [Neo4j Aura console](https://console.neo4j.io/) | ✅ (Phase 2) |
| 8 | PubMed E-Utilities API key | [NCBI account](https://www.ncbi.nlm.nih.gov/account/) | ✅ (Phase 1) |
| 9 | $5 LLM ბიუჯეტი approved | შაკოს confirmation | pending |
| 10 | Backup of Phase 2 Neo4j snapshot | `scripts/backup_neo4j.py` | required pre-day-4 |

---

## 1. დღიური Breakdown (Day-by-Day, 20 სამუშაო დღე)

### კვირა 1 — Environment + PyMC bootstrap (Days 1-5)

| Day | ფოკუსი | მთავარი ნაბიჯი | მისაღწევი outcome |
|---|---|---|---|
| ~~1~~ | ~~Repo scaffolding~~ | ~~uv init~~ **+ `mkdir -p brain/belief/{models,priors,evidence,tests}` (still TODO)** | ✅ uv DONE Foundation · folder skeleton TODO |
| ~~2~~ | ~~PyMC ინსტალაცია~~ | ~~`uv add pymc arviz numpy scipy`~~ | ✅ DONE Foundation — PyMC 5.18+, NumPyro, JAX[cpu], ArviZ live |
| ~~3~~ | ~~"Hello Bayes" smoke test~~ | ~~Beta-Binomial trial~~ | ✅ DONE — [`smoke_pymc.py`](../foundation_logs/smoke_pymc.py) 21s 2chains×1000, posterior Δ ≤ 0.053 |
| 4 | Numerical sanity | Compare PyMC posterior to closed-form Beta-Binomial analytical solution (Foundation smoke didn't do this) | abs diff < 0.005 |
| 5 | Postgres connection adapter | `belief/persistence.py` — write trace summaries to `belief_traces` table (new migration 016) | migration applied, RLS unchanged |

> **Effective Week 1 start = Day 4.** Days 1-3 absorbed by Foundation work (2026-05-24, 25/25 PASS). Buffer days increase from 8 → 11.

### კვირა 2 — 13-D Schema design + prior elicitation (Days 6-10)

| Day | ფოკუსი | მთავარი ნაბიჯი | მისაღწევი outcome |
|---|---|---|---|
| 6 | Dimension catalog | `belief/schema.py` — `Dimension` Pydantic class with `name`, `distribution`, `prior_params`, `units`, `valid_range` | 13 instances loaded from `belief/dimensions.toml` |
| 7 | Prior research — DIMs 1-5 | ცისტი (Beta), brainstem (Categorical), seizures (Poisson), tone (Normal), eye-track (Gamma) — extract priors from [BONBID-HIE dataset paper](https://www.nature.com/articles/s41597-024-03986-7) | priors.toml populated for 5 |
| 8 | Prior research — DIMs 6-10 | head-control, GMFCS, Bayley, feeding, respiratory — sources: [GMFCS reference Palisano 1997 PMID 9183258](https://pubmed.ncbi.nlm.nih.gov/9183258/), [Bayley-III norms PMID 17852163](https://pubmed.ncbi.nlm.nih.gov/17852163/) | priors.toml populated for 10 |
| 9 | Prior research — DIMs 11-13 | CSF biomarkers vector ([Massaro 2018 PMID 30341027](https://pubmed.ncbi.nlm.nih.gov/30341027/)), neuroplasticity exp-decay, family-readiness Categorical | priors.toml populated all 13 |
| 10 | Sensitivity sweep | Vary each prior by ±20% — confirm posterior stays inside plausible clinical range | sweep report committed |

### კვირა 3 — Bayesian update loop + Evidence ingestion (Days 11-15)

| Day | ფოკუსი | მთავარი ნაბიჯი | მისაღწევი outcome |
|---|---|---|---|
| 11 | Evidence schema | `belief/evidence.py` — `EvidenceItem(source, dimension, value, likelihood_fn, timestamp, confidence)` | Pydantic strict-mode validated |
| 12 | Likelihood functions | Per-distribution likelihood closures (Binomial for cyst, Poisson rate for seizures, etc.) | 13 likelihood callables registered |
| 13 | Update API | `belief.update(evidence: EvidenceItem) -> PosteriorDelta` calling `pm.sample(2000, tune=1000, cores=2)` | API returns within 30s for single dim |
| 14 | Persistence + idempotency | Trace summaries (mean, sd, hdi_3%, hdi_97%) → `belief_traces`; (dim, evidence_hash) UNIQUE | replay-safe |
| 15 | Multi-dim joint model | First joint model: `(cyst_volume, GMFCS, Bayley)` with Pearson correlation prior ([Pisano 2024 PMID 38502489](https://pubmed.ncbi.nlm.nih.gov/38502489/)) | joint posterior sampled |

### კვირა 4 — Integration, ArviZ viz, Verifier (Days 16-20)

| Day | ფოკუსი | მთავარი ნაბიჯი | მისაღწევი outcome |
|---|---|---|---|
| 16 | Evidence adapter — MRI report | Parse Phase 1 `mri_reports` table → `EvidenceItem` for cyst_volume DIM | 1 historic report ingested |
| 17 | Evidence adapter — voice note | Parse Phase 5 `intake_drops` (voice transcripts) → `EvidenceItem` for tone, eye-track, head-control | 3 historic notes ingested |
| 18 | ArviZ static plots | `belief/viz.py` — `plot_posterior`, `plot_trace`, `plot_forest` exported as PNG to `belief/snapshots/` ([ArviZ gallery](https://www.arviz.org/en/latest/examples/index.html)) | 13 PNGs generated |
| 19 | Verifier script | `verify_phase_7_0.py` — 11 checks (see §4) | 11/11 PASS locally |
| 20 | Documentation + handoff | Write `docs/PHASE_7_0_EXIT_REPORT.md` + handoff for Phase 7.1 | commit + tag `v7.0.0-belief-foundation` |

### 1.x სალდო (buffer days, optional)

ფაზაში ჩადებულია 8 დღე buffer (5 დღე/კვირაში × 4 - 20 work days). buffer გამოიყენება:
- prior elicitation-ის გადახედვაზე თუ clinical-validation feedback BMC-დან მოვა
- PyMC sampler divergence-ის debugging-ზე (typical risk: მცირე N → high divergent transitions)
- ArviZ rhat > 1.01 fix-ზე

---

## 2. დღევანდელი Deliverables (კონკრეტული artifact list)

### 2.1 კოდი (committed to repo)

| ფაილი | მიზანი | სავარაუდო LOC |
|---|---|---|
| `brain/belief/__init__.py` | Package marker | 5 |
| `brain/belief/schema.py` | `Dimension`, `DistributionSpec` Pydantic models | 120 |
| `brain/belief/dimensions.toml` | 13 dim definitions (distribution, prior_params, units) | 130 |
| `brain/belief/priors.toml` | Per-dim prior hyperparameters with citation field | 200 |
| `brain/belief/evidence.py` | `EvidenceItem` + likelihood function registry | 180 |
| `brain/belief/models.py` | PyMC model factory: `build_model(dim) -> pm.Model` | 250 |
| `brain/belief/update.py` | `update(evidence) -> PosteriorDelta` API | 150 |
| `brain/belief/persistence.py` | Postgres adapter (`belief_traces`, `belief_evidence`) | 180 |
| `brain/belief/viz.py` | ArviZ wrappers, PNG export | 100 |
| `brain/belief/tests/` | pytest suite (≥15 tests) | 400 |
| `scripts/verify_phase_7_0.py` | 11-check verifier | 250 |
| `migrations/016_belief_tables.sql` | `belief_traces`, `belief_evidence`, `belief_dimensions` | 80 |

ჯამური LOC: ~2045 (Python) + 80 (SQL) + 410 (TOML).

### 2.2 დოკუმენტაცია

| ფაილი | მთავარი შინაარსი |
|---|---|
| `docs/PHASE_7_0_EXIT_REPORT.md` | Verifier 11/11 PASS evidence, key metrics, deviations |
| `docs/PHASE_7_0_PRIORS_RATIONALE.md` | Per-dimension prior choice with primary-source citation |
| `docs/PHASE_7_0_KA_SUMMARY.md` | ქართული summary ცოლის/შაკოს გადახედვისთვის |
| Updated `CLAUDE.md` Phase VII.0 line | სტატუსი + verifier count + spend |

### 2.3 მონაცემთა ბაზის ცვლილებები

```sql
-- migration 016_belief_tables.sql (sketch)
CREATE TABLE belief_dimensions (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    distribution TEXT NOT NULL,
    prior_params JSONB NOT NULL,
    units TEXT,
    valid_min NUMERIC,
    valid_max NUMERIC,
    citation TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE belief_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dimension_id INT REFERENCES belief_dimensions(id),
    source TEXT NOT NULL,  -- 'mri_report' | 'voice_note' | 'research_paper'
    source_ref TEXT NOT NULL,
    value JSONB NOT NULL,
    evidence_hash TEXT UNIQUE NOT NULL,  -- idempotency
    confidence NUMERIC CHECK (confidence BETWEEN 0 AND 1),
    observed_at TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE belief_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dimension_id INT REFERENCES belief_dimensions(id),
    evidence_id UUID REFERENCES belief_evidence(id),
    posterior_mean NUMERIC NOT NULL,
    posterior_sd NUMERIC NOT NULL,
    hdi_3 NUMERIC NOT NULL,
    hdi_97 NUMERIC NOT NULL,
    n_samples INT NOT NULL,
    rhat NUMERIC NOT NULL,
    ess_bulk NUMERIC NOT NULL,
    arviz_summary JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS inherited from migration 008
ALTER TABLE belief_dimensions ENABLE ROW LEVEL SECURITY;
ALTER TABLE belief_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE belief_traces ENABLE ROW LEVEL SECURITY;
```

### 2.4 Smoke-test artifact (Day 3)

`v7_architecture/foundation_logs/smoke_pymc.py` უკვე არსებობს. Day 3-ზე extend-დება Beta(2, 8) prior + 10 ცდის Binomial observation → posterior `Beta(2+k, 8+n-k)` analytical comparison.

---

## 3. Blocking Dependencies

### 3.1 ტექნოლოგიური დამოკიდებულებები

| დამოკიდებულება | მიზანი | ბლოკავს რას | Mitigation / სტატუსი |
|---|---|---|---|
| **PyMC 5.18+** (actual) | core sampler | ყველაფერი | ✅ pinned in `requirements-v7.txt`; Foundation verified |
| ArviZ 0.20.x | trace diagnostics + viz | Day 18-20 | ✅ installed; fallback to manual matplotlib if API breaks |
| NumPy compat | PyMC compat | sampler init | ✅ resolved in Foundation install (15/15 imports) |
| Postgres `pgcrypto` extension | UUID generation in migration 016 | Day 5 | `CREATE EXTENSION IF NOT EXISTS pgcrypto` (Supabase has it preinstalled) |
| Python 3.12.13 | PyMC 5.x baseline | install | ✅ `.venv-v7` ready |
| C++ compiler (g++/MSVC) | PyMC NUTS C-backend speed | Day 4+ sampler perf | ⚠️ NOT installed; PyMC falls back to pure-Python sampler (slower but functional). Install MSVC Build Tools if Day 4-5 sampling > 2 min |

### 3.2 მონაცემთა დამოკიდებულებები

| დამოკიდებულება | წყარო | ბლოკავს რას | Status |
|---|---|---|---|
| Aleksandra MRI report (Day-30, Day-90, Day-180) | Phase 1 `mri_reports` | Day 16 evidence adapter | ✅ 3 reports ingested in v4 |
| Voice notes Day-1 → Day-270 | Phase 5 `intake_drops` | Day 17 evidence adapter | ✅ ~30 notes available |
| GMFCS Palisano 1997 priors | [PMID 9183258](https://pubmed.ncbi.nlm.nih.gov/9183258/) | Day 8 | open access via PubMed |
| Bayley-III norms | [PMID 17852163](https://pubmed.ncbi.nlm.nih.gov/17852163/) | Day 8 | abstract only — supplement with [Albers & Grieve 2007](https://pubmed.ncbi.nlm.nih.gov/17852163/) |
| BONBID-HIE 133-patient dataset | [Nature Sci Data 2024](https://www.nature.com/articles/s41597-024-03986-7) | Day 7 | open access |
| CSF biomarker reference | [Massaro 2018 PMID 30341027](https://pubmed.ncbi.nlm.nih.gov/30341027/) | Day 9 | abstract + full-text via Boston Medical Library |

### 3.3 ადამიანური დამოკიდებულებები

| ვინ | რა | როდის | რა მოხდება თუ არ მოვა |
|---|---|---|---|
| შაკო | $5 LLM ბიუჯეტის confirm | Day 0 (pre-start) | gate, ფაზა არ იწყება |
| შაკო | Day 5 migration 016 apply on Supabase | Day 5 morning | Day 5-20 ბლოკდება persistence-ზე |
| Dr. Maypole (BMC) — optional | Prior elicitation feedback | Day 10 | sensitivity sweep რჩება inferential, არა clinical-validated |
| ცოლი | nothing required this phase | — | — |

### 3.4 დამოკიდებულებების გრაფი

```
Day 1-2 (env) → Day 3-5 (smoke + persistence)
                          ↓
Day 6-10 (schema + priors) ← Day 7-9 ბლოკავს Day 11-15
                          ↓
Day 11-15 (update API + likelihoods)
                          ↓
Day 16-17 (evidence adapters) ← Phase 1+5 data ready (✅)
                          ↓
Day 18 (ArviZ viz)
                          ↓
Day 19 (verifier) ← ALL prior days
                          ↓
Day 20 (docs + tag)
```

---

## 4. Verifier Checklist (11 ცდა, 11/11 PASS gate)

Verifier script: `scripts/verify_phase_7_0.py`. Mode: `--mode code-complete`.

| # | Check ID | აღწერა | PASS criterion | Failure remediation |
|---|---|---|---|---|
| 1 | `check_7_0_01` | PyMC import + version | `pymc.__version__` matches `5.16.*` | reinstall `uv add pymc==5.16.*` |
| 2 | `check_7_0_02` | 13 dimensions registered | `SELECT count(*) FROM belief_dimensions = 13` | rerun `python -m brain.belief.bootstrap` |
| 3 | `check_7_0_03` | All 13 priors have primary-source citation | `belief_dimensions.citation NOT NULL AND LIKE '%PMID%' OR LIKE '%doi.org%' OR LIKE '%github%'` | populate `priors.toml` citation field |
| 4 | `check_7_0_04` | Beta-Binomial analytical match | PyMC posterior mean vs closed-form diff < 0.005 | check sampler tune steps + chains |
| 5 | `check_7_0_05` | Sampler convergence | All 13 dims: `rhat < 1.01` AND `ess_bulk > 400` | increase samples to 4000, tune to 2000 |
| 6 | `check_7_0_06` | Idempotency | Re-running update with same `evidence_hash` returns existing trace, no new row | check UNIQUE constraint + upsert logic |
| 7 | `check_7_0_07` | Likelihood functions complete | 13 callables registered in `LIKELIHOOD_REGISTRY` | add missing dim handler |
| 8 | `check_7_0_08` | Posterior delta computed | `update()` returns `PosteriorDelta(mean_shift, kl_divergence)` for every dim | verify return type |
| 9 | `check_7_0_09` | Historic evidence ingested | ≥3 MRI + ≥3 voice notes parsed into `belief_evidence` without error | rerun adapters with debug logs |
| 10 | `check_7_0_10` | ArviZ PNG snapshots | 13 PNGs exist in `belief/snapshots/` with size > 5 KB each | check matplotlib backend (`Agg` for headless) |
| 11 | `check_7_0_11` | RLS preserved | `belief_*` tables have RLS enabled, policies match migration 008 pattern | apply RLS in migration 016 |

### 4.1 Verifier output format (sample)

```text
=== verify_phase_7_0 (mode: code-complete) ===
[PASS] check_7_0_01 pymc.__version__ = 5.16.2
[PASS] check_7_0_02 dimensions registered = 13/13
[PASS] check_7_0_03 priors with citation = 13/13
[PASS] check_7_0_04 beta-binomial diff = 0.0021 (< 0.005)
[PASS] check_7_0_05 sampler convergence rhat_max = 1.008, ess_min = 612
[PASS] check_7_0_06 idempotency replay = 0 new rows on duplicate hash
[PASS] check_7_0_07 likelihood registry size = 13/13
[PASS] check_7_0_08 posterior delta returned for 13 update calls
[PASS] check_7_0_09 historic evidence = 3 mri + 4 voice ingested
[PASS] check_7_0_10 arviz snapshots = 13 PNGs (avg 38 KB)
[PASS] check_7_0_11 RLS enabled on belief_dimensions, belief_evidence, belief_traces
=== TOTAL 11/11 PASS · GREEN ===
```

### 4.2 Local pre-commit hook

```bash
# .git/hooks/pre-push (excerpt)
python scripts/verify_phase_7_0.py --mode code-complete || {
    echo "❌ verify_phase_7_0 FAILED — push blocked";
    exit 1;
}
```

---

## 5. Rollback Strategy

### 5.1 Trigger conditions (when to rollback)

| Trigger | Severity | მოქმედება |
|---|---|---|
| Day 5: migration 016 corrupts existing tables | CRITICAL | immediate full DB rollback (see 5.2) |
| Day 10: priors lead to posterior outside clinically-plausible range AND fix > 2 days | HIGH | revert priors.toml to v0, restart Day 7 |
| Day 15: sampler divergence > 5% on joint model | MEDIUM | drop joint model, ship 13 univariate models for Phase 7.0, defer joint to Phase 7.1 |
| Day 19: verifier ≤ 8/11 PASS AND no clear path to 11/11 within buffer | HIGH | tag `v7.0.0-belief-foundation-RC1`, extend phase by 1 week, do not start Phase 7.1 |
| Any: $5 LLM hard stop hit | HIGH | freeze all Anthropic calls, finish remaining work deterministically (priors are research-driven, not LLM-driven) |

### 5.2 DB rollback procedure

```sql
-- rollback_016.sql (write Day 5 before applying)
BEGIN;
DROP TABLE IF EXISTS belief_traces CASCADE;
DROP TABLE IF EXISTS belief_evidence CASCADE;
DROP TABLE IF EXISTS belief_dimensions CASCADE;
-- pgcrypto extension stays (used elsewhere)
COMMIT;
```

**Pre-flight requirement (Day 5 before apply):**
```bash
pg_dump $SUPABASE_DB_URL --schema-only -f .planning/backups/pre_016_schema.sql
pg_dump $SUPABASE_DB_URL --data-only --table='intake_*' --table='manager_*' -f .planning/backups/pre_016_data.sql
```

Per [CLAUDE.md Phase VI.1 incident lesson](../../CLAUDE.md), Supabase Free has **no automatic backups** — manual `pg_dump` is mandatory before every migration.

### 5.3 Code rollback procedure

```bash
git revert <commit-sha-range>  # do NOT reset --hard; preserve audit trail
git tag -a v7.0.0-rollback-$(date +%Y%m%d) -m "Phase 7.0 rollback at Day X for reason Y"
git push origin main v7.0.0-rollback-$(date +%Y%m%d)
```

### 5.4 v6.1 compatibility guarantee

Phase 7.0 **არ შლის** ერთ ფაილსაც v6.1-დან. ფაზაში დამატებული ფაილები:
- ემატება `brain/belief/` (ახალი namespace)
- ემატება `migrations/016_*` (additive only — no `ALTER TABLE` on Phase 1-6 tables)
- ემატება `scripts/verify_phase_7_0.py` (separate verifier)

v6.1 verifier ფაზის ბოლოს ისევ უნდა იყოს 89/89 PASS. ეს არის Phase 7.0-ის implicit acceptance gate.

### 5.5 Decision tree

```
Verifier result?
├── 11/11 PASS → proceed to Phase 7.1 (Day 21+)
├── 9-10/11 PASS → 3-day extension, fix specific check, re-verify
├── 6-8/11 PASS → 1-week extension, escalate to შაკოს review
└── ≤5/11 PASS → ROLLBACK, post-mortem doc, replan Phase 7.0 v2
```

---

## 6. LLM Spend Tracking

### 6.1 ფაზის ბიუჯეტი

| კატეგორია | Cap | Hard stop |
|---|---|---|
| Total LLM spend for Phase 7.0 | $5 | $5 (block at $4.50 with alert) |
| Per-day max | $1 | enforced via LiteLLM gate (v6.0 mechanism) |
| Single call max | $0.25 | reject + log |

### 6.2 სავარაუდო spend breakdown

| Activity | Estimated calls | Model | Est. cost |
|---|---|---|---|
| Day 7-9: prior-research literature summaries | 6 | Sonnet 4.5 | $1.50 |
| Day 11-13: likelihood function code-review assistance | 4 | Sonnet 4.5 | $0.80 |
| Day 16-17: evidence adapter edge-case discussion | 3 | Sonnet 4.5 | $0.60 |
| Day 19: verifier failure debug (contingency) | 4 | Sonnet 4.5 | $0.80 |
| Day 20: KA exit-report drafting | 2 | Sonnet 4.5 | $0.50 |
| Buffer / unplanned | — | — | $0.80 |
| **Total estimate** | **19** | — | **$5.00** |

### 6.3 Spend ledger (template)

| Date | Day | Activity | Model | Tokens (in/out) | Cost ($) | Cumulative ($) | Notes |
|---|---|---|---|---|---|---|---|
| 2026-08-15 | 1 | env setup | — | 0/0 | 0.00 | 0.00 | no LLM call |
| ... | ... | ... | ... | ... | ... | ... | ... |

ფაქტობრივი ledger ჩაიწერება `docs/PHASE_7_0_SPEND_LEDGER.md`-ში, განახლდება ყოველდღე end-of-day-ის წინ.

### 6.4 Hard-stop enforcement

Reuse v6.0-ის `scripts/cognition/budget.py` + LiteLLM gate. ცვლილება Phase 7.0-ის specific cap-ისთვის:

```python
# brain/belief/budget.py
PHASE_7_0_CAP_USD = 5.00
PHASE_7_0_ALERT_USD = 4.50

def check_belief_budget(today_spend: float, phase_cumulative: float) -> bool:
    if phase_cumulative >= PHASE_7_0_CAP_USD:
        raise BudgetExceededError(f"Phase 7.0 cap ${PHASE_7_0_CAP_USD} hit; halt")
    if phase_cumulative >= PHASE_7_0_ALERT_USD:
        send_telegram_alert(f"⚠️ Phase 7.0 spend ${phase_cumulative:.2f} / ${PHASE_7_0_CAP_USD}")
    return True
```

### 6.5 Project cumulative tracking

| ფაზა | Cap | Spent | % |
|---|---|---|---|
| Phases 1-6.1 cumulative | $60 | ~$7-8 | 12% |
| Phase 7.0 | $5 | TBD | TBD |
| **Project total after 7.0** | **$65** | **target ≤ $13** | **≤ 20%** |

---

## 7. Sprint Retrospective Template

ფაზის Day 20-ის ბოლოს შაკო ავსებს `docs/PHASE_7_0_RETROSPECTIVE.md` ფაილს ქვემოთ მოცემული შაბლონით.

### 7.1 Quantitative metrics

| საზომი | Target | Actual | Delta | Notes |
|---|---|---|---|---|
| Verifier checks PASS | 11/11 | __/11 | __ | — |
| LLM spend ($) | ≤ 5.00 | __ | __ | — |
| Work days used | 20 | __ | __ | (buffer used: __ days) |
| Phase 1-6 verifier still GREEN | 89/89 | __/89 | __ | regression test |
| Lines of code added | ~2535 | __ | __ | — |
| Tests written | ≥15 | __ | __ | pytest count |
| Sampler convergence (rhat max) | < 1.01 | __ | __ | across 13 dims |
| Sampler convergence (ess min) | > 400 | __ | __ | across 13 dims |

### 7.2 What went well

- _ (3-5 bullets, factual, with file/PR references)
- _
- _

### 7.3 What did not go well

- _ (3-5 bullets, root cause + fix, not blame)
- _
- _

### 7.4 Decisions made during the sprint

| Decision | Reason | Reversal cost | Logged in |
|---|---|---|---|
| ex: Drop joint model from Phase 7.0 | sampler divergence > 5% | low (defer to 7.1) | DECISION_LOG.md |

### 7.5 Surprises (positive and negative)

- _ (things you didn't predict — gold for future planning)

### 7.6 Carry-forward to Phase 7.1

| Item | Type | Owner | Deadline |
|---|---|---|---|
| ex: joint cyst×GMFCS×Bayley model | tech-debt | შაკო | Phase 7.1 Day 5 |
| ex: BMC clinical review of priors | external | Dr. Maypole | Phase 7.1 Day 14 |

### 7.7 Process changes for Phase 7.1

- _ (concrete process changes, not platitudes)
- _

### 7.8 Open questions (route to A3_OPEN_QUESTIONS.md)

- _
- _

---

## 8. წყაროები (Bibliography)

### 8.1 ბაიესისეული backend tooling

- [PyMC documentation v5.16](https://www.pymc.io/projects/docs/en/stable/) — primary sampler reference
- [PyMC GitHub releases](https://github.com/pymc-devs/pymc/releases) — version compatibility
- [ArviZ documentation v0.20](https://www.arviz.org/en/latest/) — trace diagnostics + viz
- [NumPyro JAX backend docs](https://num.pyro.ai/en/latest/) — alternative if PyMC speed insufficient
- [Stan reference manual](https://mc-stan.org/docs/reference-manual/) — convergence diagnostics theory

### 8.2 ბაიესისეული მეთოდოლოგია

- Kruschke J. _Doing Bayesian Data Analysis_ 2nd ed. (2015) Academic Press — pedagogical foundation
- Gelman A. et al. _Bayesian Data Analysis_ 3rd ed. (2013) CRC Press — reference
- [Bayesian Methods for Hackers (Davidson-Pilon)](https://github.com/CamDavidsonPilon/Probabilistic-Programming-and-Bayesian-Methods-for-Hackers) — open-access PyMC examples

### 8.3 HIE clinical priors

- [BONBID-HIE Nature Sci Data 2024](https://www.nature.com/articles/s41597-024-03986-7) — 133-patient dataset for cyst-volume prior
- [Palisano R. et al. _GMFCS reliability_ Dev Med Child Neurol 1997 PMID 9183258](https://pubmed.ncbi.nlm.nih.gov/9183258/)
- [Bayley N. _Bayley-III_ 2006 — Pearson](https://www.pearsonassessments.com/store/usassessments/en/Store/Professional-Assessments/Cognition-%26-Neuro/Bayley-Scales-of-Infant-and-Toddler-Development-%7C-Third-Edition/p/100000123.html)
- [Albers C.A. & Grieve A.J. _Test Review: Bayley-III_ J Psychoeducational Assessment 2007 PMID 17852163](https://pubmed.ncbi.nlm.nih.gov/17852163/)
- [Massaro A.N. et al. _CSF biomarkers in neonatal HIE_ Pediatr Res 2018 PMID 30341027](https://pubmed.ncbi.nlm.nih.gov/30341027/)
- [Pisano T. et al. _MRI-outcome correlation in HIE_ 2024 PMID 38502489](https://pubmed.ncbi.nlm.nih.gov/38502489/)

### 8.4 Digital twin / belief state literature

- [Bauer P. et al. _Digital Twins in Earth System Science_ Nature 2024](https://www.nature.com/articles/s41746-024-01073-0) — digital twin design patterns
- [Pearl J. _Causality_ 2nd ed. (2009) Cambridge UP](https://bayes.cs.ucla.edu/BOOK-2K/) — foundation for Phase 7.2

### 8.5 პროექტის ფაილები

- [ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md](../../ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md) — sections 3, 4.1
- [ALEKSANDRA_BRAIN_v7_FILE_PLAN.md](../../ALEKSANDRA_BRAIN_v7_FILE_PLAN.md) — overall roadmap
- [AI_BRAIN.md](../AI_BRAIN.md) — system prompt
- [CLAUDE.md](../../CLAUDE.md) — project state
- [docs/PHASE_6_EXIT_REPORT.md](../../docs/PHASE_6_EXIT_REPORT.md) — closest analog for verifier structure

### 8.6 ტექნიკური წინაპირობები

- [uv package manager (Astral)](https://github.com/astral-sh/uv) — Python env management
- [Supabase migrations docs](https://supabase.com/docs/guides/cli/local-development) — migration apply procedure
- [pgcrypto extension docs](https://www.postgresql.org/docs/current/pgcrypto.html) — UUID generation

---

## ვერსიის შენიშვნა

ეს არის Phase 7.0-ის v1.0 plan. დაიწერა 2026-05-24 v7.0 architecture freeze-ის ფარგლებში. ცვლილებები ფიქსირდება `v7_architecture/00_MASTER/03_CHANGELOG.md`-ში (იქმნება სესია 1-ში).

**შემდეგი ფაზის ფაილი:** [71_PHASE_7_1_MEMORY_REFACTOR_2W.md](./71_PHASE_7_1_MEMORY_REFACTOR_2W.md) (ამავე სესიაში იქმნება ან მომდევნოში).
