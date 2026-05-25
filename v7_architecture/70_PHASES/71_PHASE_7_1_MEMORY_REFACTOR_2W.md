# Phase 7.1 — Memory Refactor: Neo4j → Causal Schema (2 კვირა)

> **ფაზის ID:** 7.1
> **სახელი:** Memory Refactor — Neo4j → Causal Schema Migration
> **ვადა:** 14 დღე (2 კვირა), 2026-09-13 → 2026-09-26
> **მთავარი deliverable:** Phase 2-ის 568 entity + 307 fact-ის რეფაქტორი causal schema-ში (`CAUSES`, `INHIBITS`, `MEDIATES`, `CONFOUNDS`, `MODERATES`) + Graphiti adapter rewrite
> **წინაპირობა:** Phase 7.0 verifier 11/11 PASS · belief_traces ცოცხალი
> **LLM ბიუჯეტი:** $3 (გადათარგმნა + edge classification deterministic; LLM გამოყენებულია მხოლოდ ambiguous მაგალითებზე)
> **ფიზიკური ბიუჯეტი:** $0 ნამატი (იგივე Aura Free)

---

## 0. ფაზის სახელი, ვადა, წინაპირობა

### 0.1 სკოპი ერთი წინადადებით

ფაზა გარდაქმნის Phase 2-ის Graphiti-ბაზირებულ `CO_OCCURS_WITH`/`RELATED_TO` ბრტყელ კავშირებს Pearl-ის SCM-თან თავსებად მიზეზშედეგობრივ edge-ებად, ნერგავს edge property-ებს (`confidence`, `mechanism`, `citation`, `time_lag_days`), და ამზადებს გრაფს DoWhy-ის (Phase 7.2) input-ისთვის.

### 0.2 ფაზის ვადა

| საზომი | მნიშვნელობა |
|---|---|
| სტარტი | 2026-09-13 |
| დასრულება | 2026-09-26 |
| სამუშაო დღეები | 10 (5 × 2) |
| შაკოს ფოკუს საათები | ~30 (3 სთ/დღე) |
| Verifier gate | Phase 7.2-მდე 9/9 PASS |

### 0.3 წინაპირობების checklist

| # | წინაპირობა | წყარო | სტატუსი |
|---|---|---|---|
| 1 | Phase 7.0 closure (11/11 PASS) | `verify_phase_7_0` | gate |
| 2 | Neo4j AuraDB Free backup (568 entities + 307 facts) | `scripts/backup_neo4j.py` | required Day 0 |
| 3 | Graphiti library pinned | `getzep/graphiti-core` ([repo](https://github.com/getzep/graphiti)) | check |
| 4 | belief_dimensions populated (13/13) | Phase 7.0 Day 6 | ✅ if 7.0 PASS |
| 5 | Causal edge taxonomy approved | `docs/PHASE_7_1_TAXONOMY.md` Day 2 | gate Day 3 |

---

## 1. დღიური Breakdown (10 სამუშაო დღე)

### კვირა 1 — Schema design + Backup + Taxonomy (Days 1-5)

| Day | ფოკუსი | მთავარი ნაბიჯი | Outcome |
|---|---|---|---|
| 1 | Backup + snapshot | `neo4j-admin database dump aleksandra --to-path=.planning/backups/pre_71/` | snapshot.dump + cypher export |
| 2 | Causal edge taxonomy | 5 edge types defined: `CAUSES`, `INHIBITS`, `MEDIATES`, `CONFOUNDS`, `MODERATES` ([Pearl 2009 ch.4](https://bayes.cs.ucla.edu/BOOK-2K/)) + property schema | `PHASE_7_1_TAXONOMY.md` |
| 3 | Cypher schema migration script | `migrations/cypher/017_causal_edges.cypher` — `CREATE CONSTRAINT`, `CREATE INDEX` | applied to dev branch |
| 4 | Entity → CausalNode label upgrade | `MATCH (n:Entity) SET n:CausalNode, n.dimension_ref = ...` | 568 nodes upgraded |
| 5 | Pilot edge classification (10 sample edges) | Manual + 1 LLM-assisted sample → validate taxonomy | 10/10 mapped |

### კვირა 2 — Bulk migration + Graphiti adapter + Verifier (Days 6-10)

| Day | ფოკუსი | მთავარი ნაბიჯი | Outcome |
|---|---|---|---|
| 6 | Bulk edge re-classification | `scripts/refactor/classify_edges.py` — deterministic rules first, LLM fallback for ambiguous (<15%) | 307 facts → causal edges |
| 7 | Edge property backfill | `confidence` from Phase 2.5 ledger, `citation` from `supporting_papers`, `mechanism` from abstract | properties populated |
| 8 | Graphiti adapter rewrite | `brain/memory/causal_adapter.py` — wraps Graphiti writes with causal-edge validation | passes Phase 2 regression |
| 9 | belief ↔ causal cross-link | `dimension_ref` on CausalNode points to `belief_dimensions.id` | join query works |
| 10 | Verifier + exit report | `verify_phase_7_1.py` 9/9 PASS + KA summary | tag `v7.1.0-memory-refactor` |

---

## 2. დღევანდელი Deliverables

### 2.1 კოდი

| ფაილი | მიზანი | LOC |
|---|---|---|
| `migrations/cypher/017_causal_edges.cypher` | Schema migration | 60 |
| `scripts/backup_neo4j.py` | Pre-migration backup | 80 |
| `scripts/refactor/classify_edges.py` | Edge re-classification | 220 |
| `scripts/refactor/backfill_properties.py` | Property backfill | 150 |
| `brain/memory/causal_adapter.py` | Graphiti wrapper | 200 |
| `brain/memory/edge_taxonomy.py` | Edge type enum + validator | 80 |
| `brain/memory/tests/test_causal_adapter.py` | pytest suite (≥10 tests) | 250 |
| `scripts/verify_phase_7_1.py` | 9-check verifier | 200 |

ჯამური LOC: ~1240.

### 2.2 დოკუმენტაცია

| ფაილი | შინაარსი |
|---|---|
| `docs/PHASE_7_1_TAXONOMY.md` | 5 edge type definition + Pearl ref + decision rules |
| `docs/PHASE_7_1_EXIT_REPORT.md` | 9/9 verifier evidence + migration stats |
| `docs/PHASE_7_1_KA_SUMMARY.md` | ცოლის/შაკოს გადახედვა |
| `docs/PHASE_7_1_SPEND_LEDGER.md` | LLM call ledger |

### 2.3 Cypher schema (ფრაგმენტი)

```cypher
// migrations/cypher/017_causal_edges.cypher
CREATE CONSTRAINT causal_node_id IF NOT EXISTS
FOR (n:CausalNode) REQUIRE n.id IS UNIQUE;

CREATE INDEX causal_node_dimension IF NOT EXISTS
FOR (n:CausalNode) ON (n.dimension_ref);

// Edge types (Pearl SCM taxonomy)
// CAUSES   — direct causal effect, monotonic positive
// INHIBITS — direct causal effect, monotonic negative
// MEDIATES — indirect via intermediate node
// CONFOUNDS — common cause of both endpoints
// MODERATES — modifies the strength of another edge

CREATE CONSTRAINT edge_confidence_range IF NOT EXISTS
FOR ()-[r:CAUSES]-() REQUIRE r.confidence >= 0 AND r.confidence <= 1;
// (repeat for INHIBITS, MEDIATES, CONFOUNDS, MODERATES)
```

### 2.4 Edge re-classification rule examples

| Phase 2 edge | Phase 7.1 edge | Property hints |
|---|---|---|
| `(Vigabatrin)-[CO_OCCURS_WITH]->(GABA receptor)` | `(Vigabatrin)-[INHIBITS]->(GABA-T enzyme)` (corrected target) | mechanism: "irreversible GABA-T inhibition" PMID 7686614 |
| `(HIE)-[RELATED_TO]->(Cystic encephalomalacia)` | `(HIE)-[CAUSES]->(Cystic encephalomalacia)` | time_lag_days: 7-21 |
| `(Cord blood)-[CO_OCCURS_WITH]->(Neuroplasticity)` | `(Cord blood)-[MEDIATES]->(Neuroplasticity)` via `(IGF-1 release)` | mechanism: "paracrine IGF-1" PMID 33012876 |
| `(Age)-[CO_OCCURS_WITH]->(Vigabatrin response)` | `(Age)-[MODERATES]-(Vigabatrin->Seizure frequency)` | strength: peaks <12 months |

---

## 3. Blocking Dependencies

| დამოკიდებულება | მიზანი | Mitigation |
|---|---|---|
| Phase 7.0 belief_dimensions ცოცხალი | `dimension_ref` foreign key | gate at Day 0 |
| Neo4j 5.26 (Aura Free) | constraint syntax | pinned; tested in dev |
| Graphiti-core API stability | adapter rewrite | pin commit hash; vendor if needed |
| Phase 2 backup integrity | rollback target | dual backup (dump + cypher export) |
| Edge taxonomy approval | Day 3 gate | შაკოს sign-off doc |

---

## 4. Verifier Checklist (9 ცდა, 9/9 PASS gate)

| # | Check ID | აღწერა | PASS criterion |
|---|---|---|---|
| 1 | `check_7_1_01` | Backup exists | `.planning/backups/pre_71/snapshot.dump` size > 1 MB |
| 2 | `check_7_1_02` | Constraint applied | `SHOW CONSTRAINTS` lists `causal_node_id` |
| 3 | `check_7_1_03` | Label upgrade | `MATCH (n:CausalNode) RETURN count(n) >= 568` |
| 4 | `check_7_1_04` | All edges re-classified | `MATCH ()-[r:CO_OCCURS_WITH]-() RETURN count(r) = 0` |
| 5 | `check_7_1_05` | Edge type distribution | sum of 5 types = 307 (± 5 merged/dropped) |
| 6 | `check_7_1_06` | Properties populated | ≥ 90% edges have non-null `confidence`, `citation` |
| 7 | `check_7_1_07` | belief cross-link | ≥ 80% CausalNodes have `dimension_ref` populated |
| 8 | `check_7_1_08` | Adapter regression | Phase 2 verifier still 19/19 PASS |
| 9 | `check_7_1_09` | Idempotency | re-run migration script → 0 changes |

### 4.1 Verifier output (sample)

```text
=== verify_phase_7_1 ===
[PASS] check_7_1_01 backup snapshot 4.2 MB
[PASS] check_7_1_02 causal_node_id constraint present
[PASS] check_7_1_03 CausalNode count = 571 (568 + 3 new from belief link)
[PASS] check_7_1_04 CO_OCCURS_WITH edges = 0
[PASS] check_7_1_05 CAUSES=142 INHIBITS=58 MEDIATES=64 CONFOUNDS=29 MODERATES=18 (sum=311, +4 split)
[PASS] check_7_1_06 properties populated 94%
[PASS] check_7_1_07 dimension_ref populated 83%
[PASS] check_7_1_08 Phase 2 verifier 19/19 PASS
[PASS] check_7_1_09 re-run 0 changes
=== 9/9 PASS ===
```

---

## 5. Rollback Strategy

### 5.1 Trigger conditions

| Trigger | Severity | მოქმედება |
|---|---|---|
| Day 4: label upgrade corrupts existing queries | CRITICAL | restore from snapshot.dump |
| Day 6: bulk re-classification < 85% accuracy | HIGH | restart with refined deterministic rules, no LLM |
| Day 8: Phase 2 verifier regression | HIGH | revert adapter, keep schema |
| Day 10: verifier ≤ 6/9 | HIGH | 1-week extension, rollback to schema-only (no property backfill) |

### 5.2 Cypher rollback procedure

```bash
# Day 0 backup created — restore takes ~5 min on Aura Free
neo4j-admin database load aleksandra \
  --from-path=.planning/backups/pre_71/ \
  --overwrite-destination=true
```

### 5.3 Code rollback

```bash
git revert <commit-sha-range>
git tag -a v7.1.0-rollback-$(date +%Y%m%d)
```

### 5.4 Compatibility guarantee

Phase 1-6.1 verifiers (89/89) **MUST** stay GREEN. Phase 7.0 verifier (11/11) **MUST** stay GREEN. Phase 7.1 adds — does not remove.

---

## 6. LLM Spend Tracking

### 6.1 Cap

| კატეგორია | Cap |
|---|---|
| Total | $3 |
| Per-day | $0.50 |
| Per-call | $0.20 |

### 6.2 Sავარაუდო breakdown

| Activity | Calls | Model | Cost |
|---|---|---|---|
| Day 6: ambiguous edge classification (~45 edges) | 45 × small | Haiku 4.5 | $1.20 |
| Day 7: citation matching (fuzzy) | 30 | Haiku 4.5 | $0.60 |
| Day 8: adapter test discussion | 3 | Sonnet 4.5 | $0.45 |
| Day 10: KA exit report | 2 | Sonnet 4.5 | $0.40 |
| Buffer | — | — | $0.35 |
| **Total** | **~80** | — | **$3.00** |

### 6.3 Hard-stop enforcement

reuse `brain/belief/budget.py` pattern from Phase 7.0; cap variable: `PHASE_7_1_CAP_USD = 3.00`.

### 6.4 Project cumulative

| ფაზა | Cap | Cumulative |
|---|---|---|
| Phases 1-7.0 | $65 | ~$13 (target) |
| Phase 7.1 | $3 | $16 |

---

## 7. Sprint Retrospective Template

`docs/PHASE_7_1_RETROSPECTIVE.md` Day-10 ბოლოს.

### 7.1 Quantitative metrics

| საზომი | Target | Actual |
|---|---|---|
| Verifier PASS | 9/9 | __/9 |
| LLM spend | ≤ $3 | __ |
| Edge re-class accuracy | ≥ 95% | __% |
| Property fill rate | ≥ 90% | __% |
| Phase 1-6.1 still GREEN | 89/89 | __/89 |
| Phase 7.0 still GREEN | 11/11 | __/11 |

### 7.2 Sections

- What went well (3-5 bullets)
- What did not (3-5 bullets + root cause)
- Decisions (table)
- Surprises
- Carry-forward to Phase 7.2 (DoWhy needs causal DAG → check edge orientation correctness)
- Process changes
- Open questions

---

## 8. წყაროები

### 8.1 Causal modeling foundations

- Pearl J. _Causality_ 2nd ed. (2009) Cambridge UP — SCM and edge taxonomy
- [Pearl J. _The Book of Why_ (2018)](https://www.basicbooks.com/titles/judea-pearl/the-book-of-why/9780465097609/) — accessible introduction
- [DoWhy concepts docs](https://www.pywhy.org/dowhy/v0.11.1/user_guide/intro.html) — input format for Phase 7.2

### 8.2 Graph database

- [Neo4j 5.26 Cypher manual](https://neo4j.com/docs/cypher-manual/5/) — constraint syntax
- [neo4j-admin backup docs](https://neo4j.com/docs/operations-manual/current/backup-restore/) — dump/load procedure
- [Graphiti-core GitHub](https://github.com/getzep/graphiti) — temporal graph wrapper

### 8.3 Pharmacology citations (used in edge property backfill)

- [Vigabatrin mechanism PMID 7686614](https://pubmed.ncbi.nlm.nih.gov/7686614/)
- [Cord blood neuroplasticity PMID 33012876](https://pubmed.ncbi.nlm.nih.gov/33012876/)
- [HIE pathophysiology Volpe 2008](https://pubmed.ncbi.nlm.nih.gov/18760734/)

### 8.4 პროექტის ფაილები

- [70_PHASE_7_0_BELIEF_FOUNDATION_4W.md](./70_PHASE_7_0_BELIEF_FOUNDATION_4W.md)
- [ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md §6](../../ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md)
- [CLAUDE.md Phase II 568 entities reference](../../CLAUDE.md)

---

**შემდეგი:** [72_PHASE_7_2_CAUSAL_LAYER_3W.md](./72_PHASE_7_2_CAUSAL_LAYER_3W.md)
