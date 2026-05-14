#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# migrate.sh — apply Supabase migrations in order
#
# Usage:
#   ./scripts/migrate.sh                # apply against $SUPABASE_DB_URL
#   ./scripts/migrate.sh --dry-run      # print SQL files that would run
#
# Requires:
#   - psql on PATH (Postgres client)
#   - SUPABASE_DB_URL in .env (Settings → Database → Connection string)
#     e.g. postgresql://postgres:[pw]@db.[ref].supabase.co:5432/postgres
#
# Order:
#   1. scripts/schema.sql                            (baseline, 10 tables)
#   2. scripts/migrations/001_runs_append_only.sql   (Phase 0 OBS-01)
#   3. scripts/migrations/002_*.sql                  (future migrations)
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "$0")/.."

# Load .env into the shell so $SUPABASE_DB_URL is available
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${SUPABASE_DB_URL:-}" ]]; then
  echo "ERROR: SUPABASE_DB_URL not set in .env"
  echo "       Supabase Dashboard → Settings → Database → Connection string"
  exit 1
fi

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

apply() {
  local file="$1"
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "would apply: $file"
    return
  fi
  echo "applying:   $file"
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f "$file"
}

# 1. Baseline (idempotent — uses CREATE TABLE IF NOT EXISTS implicitly via Supabase)
apply scripts/schema.sql

# 2. Sequential migrations
for f in scripts/migrations/*.sql; do
  [[ -e "$f" ]] || continue
  apply "$f"
done

if [[ $DRY_RUN -eq 0 ]]; then
  echo ""
  echo "✓ migrations applied successfully"
fi
