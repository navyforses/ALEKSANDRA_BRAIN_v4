# Migration 017 (Cypher) — Causal edge schema for Neo4j AuraDB
Phase 7.1 Day 3.

## Prerequisites

1. Phase 7.0 verifier 11/11 GREEN (production mode)
2. NEO4J_URI + NEO4J_USERNAME + NEO4J_PASSWORD env vars set (from Aura Console)
3. `cypher-shell` installed: https://neo4j.com/docs/operations-manual/current/tools/cypher-shell/

## Pre-flight (MANDATORY)

```bash
# Verify connection + counts
NEO4J_URI='neo4j+s://<your-aura>.databases.neo4j.io' \
  NEO4J_USERNAME='neo4j' \
  NEO4J_PASSWORD='<your-password>' \
  .venv-v7/Scripts/python.exe scripts/backup_neo4j.py --dry-run
# Expected: ~568 nodes + ~307 relationships

# Take full backup
.venv-v7/Scripts/python.exe scripts/backup_neo4j.py
# Output: .planning/backups/pre_71/neo4j_snapshot_*.json + manifest.txt

# ALSO take an Aura Console snapshot for belt-and-suspenders rollback
# Open https://console.neo4j.io/ -> your instance -> Snapshots -> Create
```

## Apply migration 017

```bash
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
  -f scripts/migrations/cypher/017_causal_edges.cypher
# Expected: ~15 CREATE CONSTRAINT + 3 CREATE INDEX lines; no errors
```

## Post-apply verification

### Cypher smoke (immediate)

```bash
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
  --format plain <<'EOF'
SHOW CONSTRAINTS;
SHOW INDEXES;
MATCH (n:CausalNode) RETURN count(n) AS causal_nodes;  // expect 0 pre-Day-4
MATCH ()-[r:CO_OCCURS_WITH|RELATED_TO]-() RETURN count(r) AS legacy_edges;  // expect ~307 pre-Day-6
EOF
```

### Phase 7.1 production verifier (after Days 4-6 mutations land)

After `scripts/refactor/classify_edges.py` + `cross_link.py` + the
Day-4 CausalNode label upgrade have run, the 7 currently-SKIPed Neo4j
checks flip to live execution:

```bash
NEO4J_URI='neo4j+s://<your-aura>.databases.neo4j.io' \
NEO4J_USERNAME='neo4j' \
NEO4J_PASSWORD='<your-password>' \
.venv-v7/Scripts/python.exe scripts/verify_phase_7_1.py --mode production
# Expected: 9/9 PASS, 0 SKIP, 0 FAIL, exit code 0
# (was 2/9 PASS + 7 SKIP in --mode code-complete)
```

## Rollback

```bash
# 1. Drop the new constraints + indexes
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" <<'EOF'
DROP CONSTRAINT causal_node_id;
DROP INDEX causal_node_dimension;
DROP INDEX causal_node_name;
DROP CONSTRAINT edge_causes_confidence;
DROP CONSTRAINT edge_causes_citation;
DROP CONSTRAINT edge_inhibits_confidence;
DROP CONSTRAINT edge_inhibits_citation;
DROP CONSTRAINT edge_mediates_confidence;
DROP CONSTRAINT edge_mediates_citation;
DROP CONSTRAINT edge_mediates_via_node;
DROP CONSTRAINT edge_confounds_confidence;
DROP CONSTRAINT edge_confounds_citation;
DROP CONSTRAINT edge_moderates_confidence;
DROP CONSTRAINT edge_moderates_citation;
DROP CONSTRAINT edge_moderates_target;
EOF

# 2. If actual data damage occurred (Day 4-6 mutations), restore from snapshot
# via Aura Console UI (the JSON snapshot is a belt-and-suspenders companion)
```

## SLA

- backup_neo4j.py runtime: ~30-90 sec (depends on graph size + network)
- migration 017 apply: <5 sec
- post-apply verify: <10 sec
- Total Shako time: ~10 min
