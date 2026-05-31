#!/usr/bin/env bash
# ============================================================================
# capture_post_artifacts.sh
# ----------------------------------------------------------------------------
# Post-hoc rollback-artifact capture for migration 012 (applied 2026-05-20).
# Resolves: .planning/todos/pending/2026-05-21-capture-migration-012-rollback-artifacts.md
#
# Runs Steps 1, 2, 4(sub-check 6) of scripts/migrations/012_runbook.md against
# the LIVE post-migration database. Skips Step 3 (apply) because 012 already
# landed in production on 2026-05-20.
#
# Idempotent: safe to re-run; existing files are overwritten in place.
# Dry-run-safe: pre-flight aborts BEFORE any DB connection if env/tools missing.
# Read-only against the DB: only `\d` describes and `pg_dump --data-only` reads.
# Writes ONLY to scripts/migrations/012_rollback/*.
#
# Required environment (set BEFORE invoking):
#   SUPABASE_DB_URL   service-role connection string for production Supabase
#                     e.g. postgres://service_role:...@db.<ref>.supabase.co:5432/postgres
#
# Required tools on $PATH:
#   psql       (PostgreSQL client ≥ 14)
#   pg_dump    (PostgreSQL client ≥ 14, same install as psql)
#
# Single-command usage:
#   SUPABASE_DB_URL='postgres://...' bash scripts/migrations/012_rollback/capture_post_artifacts.sh
#
# Exit codes:
#   0  every artifact written + every smoke assertion passed
#   1  pre-flight failure OR any DB error OR any assertion failure
# ============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TABLES=(aleksandra_timeline hypotheses therapies briefs)

# (table, column) pairs that migration 012 converted from text → jsonb.
# briefs.sections was already jsonb pre-012 (reshape, no TYPE change) so it is
# NOT listed here — see runbook Step 4 sub-check 1.
JSONB_COLS=(
  "aleksandra_timeline.title"
  "aleksandra_timeline.description"
  "hypotheses.title"
  "hypotheses.description"
  "therapies.name"
  "therapies.evidence_summary"
)

# Resolve the rollback dir relative to THIS script — works regardless of cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# Logging helpers (timestamped, stderr so stdout stays artifact-clean)
# ---------------------------------------------------------------------------
log()  { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }
fail() { log "FAIL: $*"; exit 1; }
ok()   { log "OK:   $*"; }

# ---------------------------------------------------------------------------
# Pre-flight — abort before touching the DB if anything is missing
# ---------------------------------------------------------------------------
log "Pre-flight: checking required tools and env vars"

command -v psql    >/dev/null 2>&1 || fail "psql not found on PATH — install PostgreSQL client ≥ 14"
command -v pg_dump >/dev/null 2>&1 || fail "pg_dump not found on PATH — install PostgreSQL client ≥ 14"

if [[ -z "${SUPABASE_DB_URL:-}" ]]; then
  fail "SUPABASE_DB_URL is unset — export the service-role connection string before invoking"
fi

# Sanity probe — fail fast if the URL is wrong / network is blocked.
if ! psql "$SUPABASE_DB_URL" -tAc "SELECT 1;" >/dev/null 2>&1; then
  fail "psql cannot reach \$SUPABASE_DB_URL — check credentials, network, and project ref"
fi
ok "pre-flight passed (psql + pg_dump present, SUPABASE_DB_URL reachable)"

# Confirm we are on service_role (not anon/authenticated) so pg_dump can read RLS-protected rows.
DB_USER="$(psql "$SUPABASE_DB_URL" -tAc 'SELECT current_user;' | tr -d '[:space:]')"
log "Connected as DB user: ${DB_USER}"
if [[ "$DB_USER" == "anon" || "$DB_USER" == "authenticated" ]]; then
  fail "SUPABASE_DB_URL points at '${DB_USER}' — use the SERVICE_ROLE connection string for full rows"
fi
ok "connected as service-role user (${DB_USER})"

mkdir -p "$OUT_DIR"

# ---------------------------------------------------------------------------
# Step 1 — \d describes → .policies.post.txt AND mirror to .policies.pre.txt
# ---------------------------------------------------------------------------
log "Step 1: capturing \\d <table> output for ${#TABLES[@]} tables"

for tbl in "${TABLES[@]}"; do
  post_file="$OUT_DIR/$tbl.policies.post.txt"
  pre_file="$OUT_DIR/$tbl.policies.pre.txt"

  if ! psql "$SUPABASE_DB_URL" -c "\\d $tbl" > "$post_file" 2>/dev/null; then
    fail "psql \\d $tbl failed — table may be missing"
  fi

  # Mirror post → pre (the todo redefines "pre" as "current operational baseline"
  # since 012 is permanent and there is no rollback target).
  cp "$post_file" "$pre_file"

  # Assertion: 'Policies:' block must be present (RLS enabled + at least one policy)
  if ! grep -q '^Policies:' "$post_file"; then
    fail "$tbl.policies.post.txt is missing 'Policies:' block — RLS regression suspected"
  fi
  ok "captured $tbl.policies.{post,pre}.txt ($(wc -l < "$post_file") lines)"
done

# ---------------------------------------------------------------------------
# Step 2 — pg_dump --data-only --column-inserts per table
# ---------------------------------------------------------------------------
log "Step 2: pg_dump --data-only for ${#TABLES[@]} tables"

for tbl in "${TABLES[@]}"; do
  dump_file="$OUT_DIR/$tbl.pre012.dump"

  if ! pg_dump "$SUPABASE_DB_URL" \
        --table="$tbl" \
        --data-only \
        --column-inserts \
        --no-owner --no-privileges \
        --file="$dump_file"; then
    fail "pg_dump failed for table $tbl"
  fi

  # Assertion: file non-empty AND first line is the pg_dump banner
  if [[ ! -s "$dump_file" ]]; then
    fail "$dump_file is empty — pg_dump produced no output"
  fi
  first_line="$(head -n 1 "$dump_file")"
  if [[ "$first_line" != "-- PostgreSQL database dump"* ]]; then
    fail "$dump_file first line is not the pg_dump banner — got: $first_line"
  fi
  ok "dumped $tbl ($(wc -c < "$dump_file") bytes)"
done

# ---------------------------------------------------------------------------
# Step 4 sub-check 6 — post_apply_smoke.txt with pg_typeof for each jsonb col
# ---------------------------------------------------------------------------
log "Step 4 sub-check 6: capturing post_apply_smoke.txt (pg_typeof + mirror invariant)"

smoke_file="$OUT_DIR/post_apply_smoke.txt"
{
  echo "# Post-apply smoke check evidence"
  echo "# Captured: $(date -u +%Y-%m-%dT%H:%M:%SZ) (UTC) by capture_post_artifacts.sh"
  echo "# Migration 012 applied on 2026-05-20; this file evidences current production state."
  echo "# Resolves: .planning/todos/pending/2026-05-21-capture-migration-012-rollback-artifacts.md"
  echo "---"
  echo
  echo "## pg_typeof per converted column (each MUST report 'jsonb')"
  echo

  for pair in "${JSONB_COLS[@]}"; do
    tbl="${pair%%.*}"
    col="${pair##*.}"
    echo "-- $pair"
    psql "$SUPABASE_DB_URL" -c \
      "SELECT '$pair' AS col, pg_typeof($col) FROM $tbl LIMIT 1;" \
      || { echo "ERROR: psql failed for $pair"; exit 1; }
    echo
  done

  echo "## I18N-09 mirror invariant (aleksandra_timeline.title->>'en' == title->>'ka')"
  echo
  psql "$SUPABASE_DB_URL" -c \
    "SELECT count(*) AS mirrored_rows FROM aleksandra_timeline WHERE title->>'en' = title->>'ka';"
  psql "$SUPABASE_DB_URL" -c \
    "SELECT count(*) AS total_rows FROM aleksandra_timeline;"
} > "$smoke_file"

# Assertion 1: 'jsonb' appears ≥ 6 times (once per converted column)
jsonb_count="$(grep -c -w jsonb "$smoke_file" || true)"
if (( jsonb_count < 6 )); then
  fail "post_apply_smoke.txt has only ${jsonb_count} 'jsonb' hits — expected ≥ 6"
fi
ok "post_apply_smoke.txt contains 'jsonb' ${jsonb_count} times (≥ 6 required)"

# Assertion 2: mirror count == total count (I18N-09)
mirrored="$(grep -A1 'mirrored_rows' "$smoke_file" | tail -n 1 | tr -d '[:space:]' || true)"
total="$(grep -A1 'total_rows' "$smoke_file" | tail -n 1 | tr -d '[:space:]' || true)"
if [[ -n "$mirrored" && -n "$total" && "$mirrored" != "$total" ]]; then
  fail "I18N-09 mirror invariant FAILED: mirrored_rows=$mirrored, total_rows=$total"
fi
ok "I18N-09 mirror invariant holds (mirrored=$mirrored, total=$total)"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
log "ALL CHECKS PASSED — artifacts written to $OUT_DIR"
log "Next: python -m scripts.verify_phase6 --mode production --bucket B"
log "Then: git add scripts/migrations/012_rollback/* && git commit -m 'chore(06-07-followup): capture migration 012 rollback artifacts post-hoc'"

exit 0
