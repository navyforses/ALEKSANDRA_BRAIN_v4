// scripts/refactor/upgrade_to_causal_nodes.cypher
// Phase 7.1 Day 4 — Entity -> CausalNode label upgrade
//
// AUTHOR:  v7-causal (subagent)
// DATE:    2026-05-25
//
// PURPOSE:
//   Phase 2 Graphiti seeded ~568 :Entity nodes via Episode.add(). This script
//   ADDS the :CausalNode label to those existing nodes (Neo4j labels are
//   additive — a node keeps every label it has been assigned). It also
//   initialises three hygiene properties so the Day 6 classifier and the
//   Day 9 belief cross-link have predictable fields to read:
//
//     - dimension_ref   (string|null)   FK to belief_dimensions.name; NULL
//                                       placeholder set here; Day 9 populates.
//     - created_at      (datetime)      hygiene; rows missing this get NOW.
//
// PREREQUISITES (operator must complete BEFORE running this file):
//   1. .planning/backups/pre_71/neo4j_snapshot_*.json exists
//      (run scripts/backup_neo4j.py).
//   2. scripts/migrations/cypher/017_causal_edges.cypher was applied — the
//      CausalNode constraints + indexes must already exist. Verify with
//      `SHOW CONSTRAINTS;` — must include `causal_node_id`.
//
// IDEMPOTENT:
//   Every clause is guarded — re-running this script after a first successful
//   apply produces zero writes. The verification queries at the bottom can be
//   run repeatedly with no side effects.
//
// APPLY:
//   cypher-shell -a $NEO4J_URI -u neo4j -p $NEO4J_PASSWORD \
//     -f scripts/refactor/upgrade_to_causal_nodes.cypher
//
// ROLLBACK:
//   The label is additive. To remove only the new label (NOT the underlying
//   data), uncomment and run the block in §5. Existing :Entity label and all
//   properties survive untouched.

// ============================================================================
// 1) Label upgrade — :Entity -> add :CausalNode
// ============================================================================
// MATCH only nodes that do NOT already carry the CausalNode label so the
// statement is a no-op on re-run.

MATCH (n:Entity)
WHERE NOT n:CausalNode
SET n:CausalNode
RETURN count(n) AS nodes_upgraded;

// ============================================================================
// 2) dimension_ref placeholder — Phase 7.0 belief cross-link FK
// ============================================================================
// Day 9 (brain/causal/graph_loader.py) will populate dimension_ref by joining
// CausalNode.name against belief_dimensions.name (case-insensitive). Until
// then, we explicitly write NULL so downstream code can distinguish "field
// exists, no link yet" from "field never existed".
//
// We touch ONLY nodes where the property has never been set; Cypher's `IS NULL`
// returns true both for "absent" and "explicitly NULL", but `SET ... = NULL`
// is idempotent and free of side effects either way.

MATCH (n:CausalNode)
WHERE n.dimension_ref IS NULL
SET n.dimension_ref = NULL
RETURN count(n) AS nodes_with_dim_placeholder;

// ============================================================================
// 3) created_at hygiene — backfill missing timestamps
// ============================================================================
// Some Phase 2 nodes were written before Graphiti's episode pipeline started
// recording created_at. Stamp them now so Day 6 audit JSONL has a consistent
// time field to anchor against. Real created_at survives untouched.

MATCH (n:CausalNode)
WHERE n.created_at IS NULL
SET n.created_at = datetime()
RETURN count(n) AS nodes_with_created_at_backfilled;

// ============================================================================
// 4) Verification (read-only — safe to re-run any time)
// ============================================================================
// Expected post-apply state (assuming Phase 2 baseline of 568 entities):
//
//   legacy_entity_count == causal_node_count  (label additive on every row)
//   causal_node_count >= 568                  (Phase 2 baseline)
//   nodes_missing_dim_ref == 0                (all rows have property set —
//                                              value may still be NULL)
//   nodes_missing_created_at == 0             (post §3 backfill)

MATCH (n:Entity) RETURN count(n) AS legacy_entity_count;

MATCH (n:CausalNode) RETURN count(n) AS causal_node_count;

MATCH (n:CausalNode)
WHERE n.dimension_ref IS NULL AND NOT EXISTS { (n) WHERE n.dimension_ref IS NOT NULL }
RETURN count(n) AS nodes_with_null_dim_ref_value;

MATCH (n:CausalNode)
WHERE n.created_at IS NULL
RETURN count(n) AS nodes_missing_created_at;

// ============================================================================
// 5) Rollback (commented; uncomment only if Day 4 must be reverted)
// ============================================================================
// REMOVE drops the label only; node + :Entity label + properties survive.
// dimension_ref placeholder writes are NOT undone (NULL is the absent state).
//
//   MATCH (n:CausalNode) REMOVE n:CausalNode;
//   // (Optional) drop the dimension_ref property entirely:
//   //   MATCH (n) WHERE n.dimension_ref IS NULL REMOVE n.dimension_ref;
