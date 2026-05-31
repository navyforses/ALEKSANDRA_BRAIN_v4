// scripts/migrations/cypher/017_causal_edges.cypher
// Phase 7.1 Day 3 — Causal edge schema migration for Neo4j AuraDB
//
// AUTHOR:  v7-causal (subagent)
// DATE:    2026-05-25
// STATUS:  PURELY ADDITIVE — creates constraints + indexes only.
//          Does NOT modify, drop, or replace any existing Phase 2 edges
//          (CO_OCCURS_WITH / RELATED_TO). Those are re-classified by the
//          application layer (brain/memory/edge_taxonomy.py) during
//          Phase 7.1 Days 4-6, AFTER this migration is applied.
//
// APPLY:   v7-devops will help Shako run this via cypher-shell:
//
//          cypher-shell -a $NEO4J_URI -u neo4j -p $NEO4J_PASSWORD \
//            -f scripts/migrations/cypher/017_causal_edges.cypher
//
// PREREQ:  Neo4j AuraDB Free tier (community-level constraint support).
//          Migration 016 (belief tables) is unrelated (Postgres, not Neo4j) —
//          this is the FIRST Cypher migration. Future Cypher migrations
//          live alongside this file under scripts/migrations/cypher/.
//
// IDEMPOTENT: every statement uses `IF NOT EXISTS`. Safe to re-run.
//
// IMPORTANT — Neo4j AuraDB Free constraint capability:
//   - Existence constraints on relationship properties: SUPPORTED
//   - Range constraints (e.g., 0 <= x <= 1):              NOT SUPPORTED
//   Range enforcement (`0 <= confidence <= 1`, `time_lag_days >= -1`, etc.)
//   lives in `brain/memory/edge_taxonomy.py` per docs/PHASE_7_1_TAXONOMY.md §2.2.

// ============================================================================
// 1) CausalNode label — node-side schema
// ============================================================================
// Every node that becomes a CausalNode (Day 4 upgrade adds the label to
// existing 568 Phase 2 nodes via MATCH/SET) must have a unique id.

CREATE CONSTRAINT causal_node_id IF NOT EXISTS
FOR (n:CausalNode) REQUIRE n.id IS UNIQUE;

// dimension_ref → Phase 7.0 belief_dimensions(dimension_id) cross-link.
// Not a true FK in Neo4j; integrity is verified at the application layer
// (brain/causal/graph_loader.py during Phase 7.2 Day 1). Index speeds joins.

CREATE INDEX causal_node_dimension IF NOT EXISTS
FOR (n:CausalNode) ON (n.dimension_ref);

// Name index for fast lookup during Days 4-6 re-classification.

CREATE INDEX causal_node_name IF NOT EXISTS
FOR (n:CausalNode) ON (n.name);

// ============================================================================
// 2) Edge type constraints — Pearl 5-type taxonomy
// ============================================================================
// Each causal edge type has 4 mandatory properties:
//   confidence ∈ [0,1]    (range enforced at app layer)
//   citation   TEXT       (non-empty; PubMed/DOI/URL marker)
//   mechanism  TEXT       (nullable — NOT enforced here)
//   time_lag_days INT     (nullable — NOT enforced here)
//
// Type-specific additional constraints:
//   MEDIATES   → via_node REQUIRED
//   CONFOUNDS  → also_confounds REQUIRED (non-empty list, app-layer check)
//   MODERATES  → moderates_edge REQUIRED (16-hex-char hash, app-layer check)

// ----------------------------------------------------------------------------
// 2.1 CAUSES — direct monotonic positive
// ----------------------------------------------------------------------------
CREATE CONSTRAINT edge_causes_confidence IF NOT EXISTS
FOR ()-[r:CAUSES]-() REQUIRE r.confidence IS NOT NULL;

CREATE CONSTRAINT edge_causes_citation IF NOT EXISTS
FOR ()-[r:CAUSES]-() REQUIRE r.citation IS NOT NULL;

// ----------------------------------------------------------------------------
// 2.2 INHIBITS — direct monotonic negative
// ----------------------------------------------------------------------------
CREATE CONSTRAINT edge_inhibits_confidence IF NOT EXISTS
FOR ()-[r:INHIBITS]-() REQUIRE r.confidence IS NOT NULL;

CREATE CONSTRAINT edge_inhibits_citation IF NOT EXISTS
FOR ()-[r:INHIBITS]-() REQUIRE r.citation IS NOT NULL;

// ----------------------------------------------------------------------------
// 2.3 MEDIATES — indirect via intermediate node
// ----------------------------------------------------------------------------
CREATE CONSTRAINT edge_mediates_confidence IF NOT EXISTS
FOR ()-[r:MEDIATES]-() REQUIRE r.confidence IS NOT NULL;

CREATE CONSTRAINT edge_mediates_citation IF NOT EXISTS
FOR ()-[r:MEDIATES]-() REQUIRE r.citation IS NOT NULL;

// via_node identifies the intermediate M in X → M → Y.
// Double-edge invariant ((X)-CAUSES->(M) + (M)-CAUSES->(Y) must coexist)
// is enforced by brain/memory/edge_taxonomy.py::validate_mediates_invariant().

CREATE CONSTRAINT edge_mediates_via_node IF NOT EXISTS
FOR ()-[r:MEDIATES]-() REQUIRE r.via_node IS NOT NULL;

// ----------------------------------------------------------------------------
// 2.4 CONFOUNDS — common cause of both endpoints
// ----------------------------------------------------------------------------
CREATE CONSTRAINT edge_confounds_confidence IF NOT EXISTS
FOR ()-[r:CONFOUNDS]-() REQUIRE r.confidence IS NOT NULL;

CREATE CONSTRAINT edge_confounds_citation IF NOT EXISTS
FOR ()-[r:CONFOUNDS]-() REQUIRE r.citation IS NOT NULL;

// also_confounds = list of outcome node ids this Z jointly confounds with
// the edge target. Non-empty enforced at app layer (Neo4j cannot range-check
// list length). Existence ensures the property is at least set.

CREATE CONSTRAINT edge_confounds_also IF NOT EXISTS
FOR ()-[r:CONFOUNDS]-() REQUIRE r.also_confounds IS NOT NULL;

// ----------------------------------------------------------------------------
// 2.5 MODERATES — modifies the strength of another edge
// ----------------------------------------------------------------------------
CREATE CONSTRAINT edge_moderates_confidence IF NOT EXISTS
FOR ()-[r:MODERATES]-() REQUIRE r.confidence IS NOT NULL;

CREATE CONSTRAINT edge_moderates_citation IF NOT EXISTS
FOR ()-[r:MODERATES]-() REQUIRE r.citation IS NOT NULL;

// moderates_edge = sha256(f"{source.id}|{target.id}|{type}")[:16]
// Existence enforced here; hash format and target-edge-exists checked at
// app layer (brain/memory/edge_taxonomy.py::validate_moderates_target()).

CREATE CONSTRAINT edge_moderates_target IF NOT EXISTS
FOR ()-[r:MODERATES]-() REQUIRE r.moderates_edge IS NOT NULL;

// ============================================================================
// 3) Verification queries (run after apply; all idempotent / read-only)
// ============================================================================
// Copy-paste these into Neo4j Browser or cypher-shell to confirm migration
// landed cleanly.
//
//   SHOW CONSTRAINTS;
//   SHOW INDEXES;
//
//   // Pre-Day-4 expected: 0. Post-Day-4 expected: ≥568.
//   MATCH (n:CausalNode) RETURN count(n);
//
//   // Pre-Day-4 expected: 0 (empty taxonomy). Post-Day-6 expected: ~311.
//   MATCH ()-[r:CAUSES|INHIBITS|MEDIATES|CONFOUNDS|MODERATES]-()
//   RETURN type(r), count(r);
//
//   // Pre-Day-6 expected: 307 (Phase 2 originals). Post-Day-6 expected: 0.
//   MATCH ()-[r:CO_OCCURS_WITH|RELATED_TO]-() RETURN count(r);

// ============================================================================
// 4) Rollback (commented; uncomment + run only if migration must be undone)
// ============================================================================
// Safe rollback because this migration is PURELY ADDITIVE — dropping
// constraints leaves Phase 2 data untouched. Re-classified edges, if any,
// would survive but become unconstrained.
//
//   DROP CONSTRAINT causal_node_id;
//   DROP INDEX causal_node_dimension;
//   DROP INDEX causal_node_name;
//
//   DROP CONSTRAINT edge_causes_confidence;
//   DROP CONSTRAINT edge_causes_citation;
//
//   DROP CONSTRAINT edge_inhibits_confidence;
//   DROP CONSTRAINT edge_inhibits_citation;
//
//   DROP CONSTRAINT edge_mediates_confidence;
//   DROP CONSTRAINT edge_mediates_citation;
//   DROP CONSTRAINT edge_mediates_via_node;
//
//   DROP CONSTRAINT edge_confounds_confidence;
//   DROP CONSTRAINT edge_confounds_citation;
//   DROP CONSTRAINT edge_confounds_also;
//
//   DROP CONSTRAINT edge_moderates_confidence;
//   DROP CONSTRAINT edge_moderates_citation;
//   DROP CONSTRAINT edge_moderates_target;
