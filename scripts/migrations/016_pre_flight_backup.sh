#!/usr/bin/env bash
# scripts/migrations/016_pre_flight_backup.sh
# ════════════════════════════════════════════════════════════════════════════
# Pre-flight backup before applying migration 016 (Phase 7.0 belief tables).
#
# Per Phase 6.1 incident lesson (see CLAUDE.md Phase VI.1): Supabase Free has
# NO automatic backups. Manual pg_dump is the only safety net.
#
# Usage:
#   export SUPABASE_DB_URL='postgres://postgres:<pw>@db.<proj>.supabase.co:5432/postgres'
#   bash scripts/migrations/016_pre_flight_backup.sh
#
# Outputs (.planning/backups/pre_016/):
#   schema.sql      — full schema dump (all `public.*` objects)
#   data.sql        — data-only dump of `public.*` (excludes Supabase-managed schemas)
#   rowcounts.csv   — per-table row counts (CSV for diffing post-apply)
#   manifest.txt    — date, redacted conn string, file listing
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail

: "${SUPABASE_DB_URL:?must be set to service-role connection string}"

OUT=".planning/backups/pre_016"
mkdir -p "$OUT"

echo "[1/4] pg_dump --schema-only ..."
pg_dump "$SUPABASE_DB_URL" --schema-only > "$OUT/schema.sql"

echo "[2/4] pg_dump --data-only (public schema only) ..."
pg_dump "$SUPABASE_DB_URL" --data-only \
  --exclude-schema=auth \
  --exclude-schema=storage \
  --exclude-schema=realtime \
  --exclude-schema=graphql \
  --exclude-schema=graphql_public \
  --exclude-schema=net \
  --exclude-schema=vault \
  --exclude-schema=extensions \
  --exclude-schema=pgbouncer \
  --exclude-schema=pg_toast \
  --exclude-schema=supabase_functions \
  > "$OUT/data.sql"

echo "[3/4] per-table row counts ..."
psql "$SUPABASE_DB_URL" --csv -c "
  SELECT
    tablename,
    pg_total_relation_size(quote_ident(tablename)::regclass) AS bytes,
    (xpath('/row/c/text()', xml_count))[1]::text::int AS rows
  FROM (
    SELECT
      tablename,
      query_to_xml(format('SELECT count(*) AS c FROM %I', tablename),
                   false, true, '') AS xml_count
    FROM pg_tables
    WHERE schemaname='public'
    ORDER BY tablename
  ) t
" > "$OUT/rowcounts.csv"

echo "[4/4] manifest ..."
{
  echo "Pre-flight backup for migration 016 (belief tables)"
  echo "Date:       $(date -u +%FT%TZ)"
  # Redact password but keep host fingerprint for forensic ID
  echo "Connection: $(echo "$SUPABASE_DB_URL" | sed -E 's#://[^:]+:[^@]+@#://<user>:<redacted>@#')"
  echo ""
  echo "Files in this backup:"
  ls -la "$OUT" | grep -v '^total'
  echo ""
  echo "Row counts (top 20):"
  head -n 21 "$OUT/rowcounts.csv"
} > "$OUT/manifest.txt"

echo ""
echo "[ok] Backup complete in $OUT"
echo "     schema.sql:    $(wc -l < "$OUT/schema.sql") lines"
echo "     data.sql:      $(wc -l < "$OUT/data.sql") lines"
echo "     rowcounts.csv: $(wc -l < "$OUT/rowcounts.csv") lines (including header)"
echo "     manifest:      $OUT/manifest.txt"
echo ""
echo "Next: psql \"\$SUPABASE_DB_URL\" -v ON_ERROR_STOP=1 -f scripts/migrations/016_belief_tables.sql"
