# Phase 7.1 — Causal Edge Taxonomy (Pearl SCM, 5 types)

> **Phase:** 7.1 Memory Refactor — Day 2
> **Source:** Pearl J. *Causality* 2nd ed. (2009) Cambridge UP, ch. 4
> **Replaces:** Phase 2 flat `CO_OCCURS_WITH` / `RELATED_TO` edges (Graphiti default)
> **Target:** Re-classify ~307 facts across 568 nodes during Days 4-9
> **Author:** v7-causal (subagent)
> **Status:** DRAFT pending Shako sign-off (Day 3 gate)

## 0. Why this exists

Phase 2 used Graphiti's default `Episode.add()` writes, producing flat relational edges
(`CO_OCCURS_WITH`, `RELATED_TO`) with no causal direction, no mechanism, no
confidence — adequate for graph search and retrieval, but **incompatible with
do-calculus**. Phase 7.2's DoWhy layer cannot identify estimands on a
non-directed graph: it needs a DAG over typed causal edges with explicit
confounders.

The taxonomy below is the **minimal sufficient set** for Pearl 2009 ch. 4
SCMs: every other relation Phase 7.2's estimators need (`backdoor`, `frontdoor`,
`instrumental variable`) is derivable from these five types via `nx.DiGraph`
ancestry queries.

## 1. The five edge types

### 1.1 CAUSES — direct monotonic positive causal effect

- **Pearl notation:** `X → Y`, where increasing `X` causes `Y` to increase (or `X` presence causes `Y` presence).
- **Re-class rule:** edge between two entities where the source UPREGULATES, PRODUCES, ELEVATES, INCREASES, INDUCES, TRIGGERS, or RESULTS IN the target.
- **DAG role:** primary edge; appears in every backdoor adjustment set.
- **Examples (Aleksandra domain):**
  - `(HIE)-[CAUSES]->(Cystic encephalomalacia)` — `time_lag_days: 7-21`
  - `(Hypothermia therapy)-[CAUSES]->(Neuroprotection)` — `time_lag_days: 0`
  - `(Seizure)-[CAUSES]->(Neuronal damage)` — `mechanism: "excitotoxicity"`
- **Anti-pattern:** never use CAUSES for bidirectional, correlation-only, or unsigned-effect edges. If the sign is unknown, leave the edge as Phase-2 `CO_OCCURS_WITH` until evidence resolves direction.

### 1.2 INHIBITS — direct monotonic negative causal effect

- **Pearl notation:** `X ⊣ Y`, where increasing `X` causes `Y` to decrease (or `X` presence causes `Y` absence).
- **Re-class rule:** source DECREASES, SUPPRESSES, BLOCKS, ANTAGONIZES, DOWNREGULATES, or REDUCES the target.
- **DAG role:** treated identically to `CAUSES` for ancestry purposes; the sign lives in the property `effect_sign = -1`.
- **Examples (Aleksandra domain):**
  - `(Vigabatrin)-[INHIBITS]->(GABA-T enzyme)` — `mechanism: "irreversible covalent bond"`, PMID 7686614
  - `(Anti-seizure med)-[INHIBITS]->(Seizure frequency)`
  - `(Hypothermia therapy)-[INHIBITS]->(Apoptotic cascade)` — `time_lag_days: 0`
- **Anti-pattern:** do not flip an `INHIBITS` to `CAUSES` by relabeling the target ("vigabatrin causes low GABA-T" is sloppy; the canonical edge is `INHIBITS GABA-T`).

### 1.3 MEDIATES — indirect causal effect via intermediate node

- **Pearl notation:** `X → M → Y`, where `M` sits on the causal path.
- **Re-class rule:** the relationship between `X` and `Y` is mechanistically explained by an intermediate variable `M` that is itself a graph node.
- **DAG role:** required for **frontdoor adjustment** when backdoor variables are unobservable.
- **Modeling convention (double-edge bookkeeping):** materialize as TWO edges in Neo4j —
  - `(X)-[CAUSES]->(M)`
  - `(M)-[CAUSES]->(Y)`
  - …AND ALSO add `(X)-[MEDIATES {via_node: M.id}]->(Y)` as a convenience edge for SCM lookups.
- The `MEDIATES` edge is **derived**, not authoritative. The two `CAUSES` edges are the source of truth; `MEDIATES` is a denormalized index. `brain/memory/edge_taxonomy.py` (Day 4) enforces the invariant:
  > "For every `MEDIATES {via_node: M}` from X to Y, both `(X)-[CAUSES]->(M)` and `(M)-[CAUSES]->(Y)` must exist (or `INHIBITS` if the sign is negative on either segment)."
- **Examples (Aleksandra domain):**
  - `(Cord blood)-[MEDIATES {via_node: 'IGF-1'}]->(Neuroplasticity)` — `mechanism: "paracrine IGF-1 release"`, PMID 33012876
  - `(Hypothermia)-[MEDIATES {via_node: 'Reduced cerebral metabolism'}]->(Improved outcome)`

### 1.4 CONFOUNDS — common cause of both endpoints

- **Pearl notation:** `Z → X, Z → Y` — Z is a confounder of the X↔Y relationship.
- **Re-class rule:** a third variable causally influences BOTH endpoints; DoWhy's backdoor identification must include confounders in the adjustment set.
- **DAG role:** the **most operationally critical** type. Phase 7.2's `CausalModel.identify_effect()` will silently produce biased estimates if confounders are missing.
- **Modeling convention:** stored as ONE edge from `Z` to the **treatment** endpoint, with a property `also_confounds: [outcome_node_id, …]` listing every outcome `Z` jointly confounds. This avoids edge-doubling while keeping the (Z, X, Y) triple discoverable.
- **Examples (Aleksandra domain):**
  - `(Neuroplasticity window age)-[CONFOUNDS {also_confounds: ['Seizure outcome']}]->(Vigabatrin response)` — age is a confounder of both treatment response and outcome.
  - `(HIE severity)-[CONFOUNDS {also_confounds: ['Outcome']}]->(Treatment uptake)` — severity influences which treatments families choose AND outcomes directly.
- **Anti-pattern:** treating `CONFOUNDS` as a synonym for `CAUSES` two times. The Cypher constraint requires `also_confounds` to be non-empty.

### 1.5 MODERATES — modifies the strength of another edge (effect modifier)

- **Pearl notation:** `Z` modifies the `X → Y` effect magnitude (not direction).
- **Re-class rule:** the relationship between `X` and `Y` differs across levels of `Z`, but `Z` does not itself cause `Y`.
- **DAG role:** **not part of the DoWhy DAG** — moderation is handled at estimation time via stratified or interaction-term estimators. The edge exists in Neo4j as metadata for the estimator to query.
- **Modeling convention:** edge points from `Z` to the **target** of the moderated edge, with property `moderates_edge` = deterministic hash of the moderated triple, computed as `sha256(f"{source.id}|{target.id}|{type}")[:16]`. (Neo4j relationships lack native string IDs.)
- **Examples (Aleksandra domain):**
  - `(Age)-[MODERATES {moderates_edge: 'a4f2…b913'}]->(Vigabatrin response)` — effect strongest <12 months.
  - `(CYP2C9 variant)-[MODERATES {moderates_edge: '3e1c…f0d2'}]->(Phenytoin clearance)` — pharmacogenomics.
- **Anti-pattern:** using MODERATES when the moderator also causes the outcome directly. If `Z` causes `Y` AND moderates `X → Y`, store TWO edges: `(Z)-[CAUSES]->(Y)` plus `(Z)-[MODERATES]->(Y)`.

## 2. Mandatory edge properties (every causal edge — 4 fields)

| Property | Type | Constraint | Example | Source of truth |
|---|---|---|---|---|
| `confidence` | numeric (double) | `0.0 ≤ x ≤ 1.0` | `0.85` | application layer; default `0.5` for LLM-classified, `0.9` for human-verified |
| `citation` | text | non-empty; PubMed/DOI/URL marker required | `"PMID:7686614"` | re-classification pipeline injects from Phase 2 ledger; v7-librarian backfills gaps in Day 7 |
| `mechanism` | text | nullable; brief biology phrase | `"irreversible GABA-T inhibition"` | LLM-extracted from cited paper abstract, capped 200 chars |
| `time_lag_days` | integer | nullable; `-1` if unknown but discrete; `null` if N/A | `7` | extracted from paper or set by domain default (`0` for pharmacological, `7-21` for tissue change) |

### 2.1 Optional type-specific properties

| Edge type | Extra property | Required? |
|---|---|---|
| `INHIBITS` | `effect_sign = -1` | optional (implied by edge type, but stored for symmetric estimator math) |
| `MEDIATES` | `via_node` (node id of intermediate) | **required** — enforced by Cypher constraint |
| `CONFOUNDS` | `also_confounds` (list of outcome node ids) | **required** — must be non-empty list |
| `MODERATES` | `moderates_edge` (16-char hash of moderated triple) | **required** — enforced by Cypher constraint |

### 2.2 Why range constraints (0 ≤ confidence ≤ 1) live in the app, not Cypher

Neo4j Aura **Free / Community** does not support range constraints on
relationship properties (only existence constraints). The Phase 7.1 plan's
Day 1 illustrative Cypher (`REQUIRE r.confidence >= 0 AND r.confidence <= 1`)
will fail at apply time. We enforce existence at the DB layer (migration 017)
and range at the application layer (`brain/memory/edge_taxonomy.py`,
Day 4). v7-devops + Shako will pin this in the runbook so post-apply
verification reads only `SHOW CONSTRAINTS` for existence.

## 3. Decision tree for re-classifying a Phase 2 edge

Given a flat `(A)-[CO_OCCURS_WITH|RELATED_TO]->(B)` edge:

1. **Mechanism exists?** Is there a documented mechanism (in Phase 2 evidence ledger or PubMed abstract) for A affecting B?
   - No → **DELETE** edge (correlation-only; no causal claim survives).
   - Yes → continue.
2. **Direction?** Does a change in A cause a change in B (not vice-versa, not both)?
   - No / unsure → **DELETE** (not causal). If bidirectional and biologically real, flag for manual triage (out of Day 4-6 scope).
   - Yes → continue.
3. **Sign?** Does A INCREASE B (→ **CAUSES**) or DECREASE B (→ **INHIBITS**)?
   - Pick one; never both on the same edge pair.
4. **Mechanism via intermediate?** Is there a known intermediate node M on the path?
   - Yes → re-class as **MEDIATES** + split to two `CAUSES`/`INHIBITS` edges per §1.3 invariant.
   - No → keep as direct `CAUSES`/`INHIBITS`.
5. **Third-variable check.** Is there a Z (already a node in the graph) known to causally influence both A and B?
   - Yes → also add `(Z)-[CONFOUNDS {also_confounds: [B.id]}]->(A)`.
6. **Effect-modifier check.** Does the strength of A→B vary by some Z (already a node)?
   - Yes → add `(Z)-[MODERATES {moderates_edge: hash(A,B,CAUSES/INHIBITS)}]->(B)`.

Steps 5 and 6 are **additive only** — they never delete or replace the A→B edge.

## 4. LLM-assistance budget for re-classification

- Phase 7.1 Day 4-6 budget: **$1.20** for ~45 ambiguous-edge LLM calls (Haiku 4.5).
- Deterministic rules (regex on Phase 2 fact text + verb lexicon) handle the first ≥85% of edges.
- LLM ONLY when:
  - Edge involves > 2 candidate types after deterministic pass
  - Mechanism text is missing AND the cited paper title is unclear
  - The deterministic verb lexicon mis-fires (e.g., "associated with" can map to CAUSES, CONFOUNDS, or DELETE)
- If LLM exceeds 15% of total edges, the run halts and v7-causal re-tunes the lexicon. Anti-pattern explicitly flagged in role doc.

## 5. Known limitations (deferred to v7.2 DoWhy work)

1. **MEDIATES double-edge bookkeeping** — needs a Cypher constraint to keep `(X)-[CAUSES]->(M)`, `(M)-[CAUSES]->(Y)`, and `(X)-[MEDIATES]->(Y)` in sync. Neo4j Community lacks multi-edge constraints, so `brain/memory/edge_taxonomy.py` provides a `validate_mediates_invariant()` function called from the test suite + on every batch insert.
2. **MODERATES referencing edge IDs** — Neo4j relationships have no native string IDs across migrations. We use a deterministic SHA-256 hash (first 16 chars) of `(source.id, target.id, type)` so the moderator can survive node-id changes only if endpoints don't change. A node rename forces re-hashing.
3. **Bidirectional causal edges** (rare in biology, but real for feedback loops, e.g., seizure ↔ inflammation) — current taxonomy assumes DAG. Two-way causation needs feedback-loop modeling (cyclic SCM); **out of scope for v7.0**. Edges flagged as bidirectional during Day 4-6 land in a `causal_review_queue` table for manual resolution by a clinician collaborator.
4. **Temporal Pearl SCMs** — `time_lag_days` is stored but DoWhy 0.11 does not natively reason about lag. Phase 7.2 will use it for sanity checks (e.g., reject estimands where effect precedes cause) but not for full DTSCM (dynamic treatment regime) inference.
5. **Multi-citation edges** — `citation` is a single text field. Edges supported by multiple papers concatenate as `"PMID:123,PMID:456"`. A future schema may normalize this to a join table.

## 6. Hand-off to Day 4-6 (re-classification execution)

The application layer (`brain/memory/edge_taxonomy.py`, scope of Day 4) must
enforce, at every write path:

1. Edge type ∈ `{CAUSES, INHIBITS, MEDIATES, CONFOUNDS, MODERATES}` (enum validator).
2. `0.0 ≤ confidence ≤ 1.0` (Cypher cannot range-check).
3. `citation` non-empty and matches `^(PMID:\d+|DOI:.+|https?://.+)$` regex.
4. For `MEDIATES`: `validate_mediates_invariant(via_node)` — both segment edges exist.
5. For `CONFOUNDS`: `also_confounds` non-empty AND every listed node id exists.
6. For `MODERATES`: `moderates_edge` is a 16-hex-char string AND the referenced edge exists.
7. DAG invariant: post-write, `nx.is_directed_acyclic_graph(loaded_graph)` returns `True`. Reject the batch (transactional) on any cycle.

## 7. Citations

- Pearl J. *Causality* 2nd ed. (2009) Cambridge UP — foundation
- Pearl J., Glymour M., Jewell N. *Causal Inference in Statistics: A Primer* (2016) Wiley — accessible intro
- DoWhy concepts docs: https://www.pywhy.org/dowhy/v0.11.1/user_guide/intro.html
- Vigabatrin mechanism: [PMID 7686614](https://pubmed.ncbi.nlm.nih.gov/7686614/)
- Cord blood IGF-1 mediation: [PMID 33012876](https://pubmed.ncbi.nlm.nih.gov/33012876/)
- Phase 7.1 plan: `v7_architecture/70_PHASES/71_PHASE_7_1_MEMORY_REFACTOR_2W.md`

## 8. Sign-off

| Role | Signature | Date | Comment |
|---|---|---|---|
| v7-causal (drafter) | auto | 2026-05-25 | initial taxonomy per Pearl 2009 ch. 4 |
| Shako (gate) | pending | Day 3 | gates Day 4 re-classification start |
| v7-bayes (cross-link) | pending | Day 9 | confirms `dimension_ref` FK pattern is mutually agreeable |
