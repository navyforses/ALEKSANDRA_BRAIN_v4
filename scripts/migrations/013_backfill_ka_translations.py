"""
scripts/migrations/013_backfill_ka_translations.py — Phase 6.1 I18N-14.

One-time LLM backfill of ka content for the 6 JSONB columns that migration
012 mirrored deterministically (`ka = en`). Reads rows where `col->>'en' =
col->>'ka'` AND `en` is non-empty, calls `compose_bilingual` to get a real
Georgian translation, and updates the JSONB to `{en, ka}` with the new pair.

Idempotent: rows where `en != ka` are already real translations and are
skipped on re-run.

Apply (Shako-supervised; see scripts/migrations/013_runbook.md):
    BILINGUAL_TEST_MODE=1 python -m scripts.migrations.013_backfill_ka_translations --dry-run
    python -m scripts.migrations.013_backfill_ka_translations

Safety rails (all Phase 6 reuse):
- scripts.cognition.budget.check_daily_budget fires INSIDE compose_bilingual
  (FND-04 ceiling); BudgetExceeded rolls back the transaction.
- scripts.communicator.phi_redactor.redact_bilingual on the composed pair
  before UPDATE; blocked fields skipped (defence-in-depth — these tables
  carry no PHI per Phase 3 audit).
- Single BEGIN/COMMIT transaction; on any exception → ROLLBACK; no partial
  writes.
- --dry-run / BILINGUAL_TEST_MODE=1 → zero writes, $0 LLM (compose_bilingual
  returns a deterministic stub when BILINGUAL_TEST_MODE=1 or
  ANTHROPIC_API_KEY is unset).
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import TYPE_CHECKING

import psycopg2

from scripts.communicator.bilingual import compose_bilingual
from scripts.communicator.phi_redactor import redact_bilingual

if TYPE_CHECKING:  # pragma: no cover
    from anthropic import Anthropic


# 6 (table, column) targets — the columns migration 012 converted to JSONB
# with `ka = en` mirror. Match the migration 012 SQL.
TARGETS: list[tuple[str, str]] = [
    ("aleksandra_timeline", "title"),
    ("aleksandra_timeline", "description"),
    ("hypotheses", "title"),
    ("hypotheses", "description"),
    ("therapies", "name"),
    ("therapies", "evidence_summary"),
]


def _load_env() -> None:
    """Mirror weekly_brief.py's load_env contract — best-effort .env loader."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def _connect():
    _load_env()
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")


def _truncate(s: str, n: int = 60) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _is_test_mode() -> bool:
    """Match compose_bilingual's test-mode trigger so the runbook can preview."""
    if os.environ.get("BILINGUAL_TEST_MODE", "").strip() == "1":
        return True
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return True
    return False


def _make_client() -> "Anthropic | None":
    """Construct an Anthropic client unless we are in test mode."""
    if _is_test_mode():
        return None
    try:
        import anthropic
    except ImportError:
        sys.stderr.write(
            "ERROR: anthropic SDK is required outside test mode. Install: pip install anthropic\n"
        )
        sys.exit(2)
    return anthropic.Anthropic()


def backfill(dry_run: bool = False) -> int:
    """Run the backfill. Returns process exit code (0 success, 1 partial, 2 fatal)."""

    if "SUPABASE_DB_URL" not in os.environ:
        sys.stderr.write(
            "ERROR: SUPABASE_DB_URL not set. This script connects to production\n"
            "Supabase; set the service-role connection string before running.\n"
            "See scripts/migrations/013_runbook.md ## Prerequisites.\n"
        )
        return 2

    client = _make_client()
    test_mode = _is_test_mode()

    header = (
        "DRY RUN — no writes, $0 spend (test-mode stub)" if dry_run else "LIVE BACKFILL"
    )
    if test_mode and not dry_run:
        header = "LIVE BACKFILL (test-mode stub — compose_bilingual returns [KA-PLACEHOLDER])"
    print(f"\n=== migration 013 — {header} ===\n")

    summary: dict[str, dict[str, int]] = {}
    blocked: list[tuple[str, str, str, list[str]]] = []  # (table, col, id, reasons)

    conn = _connect()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            for table, col in TARGETS:
                key = f"{table}.{col}"
                summary[key] = {
                    "scanned": 0,
                    "eligible": 0,
                    "updated": 0,
                    "blocked": 0,
                    "skipped_translated": 0,
                }

                cur.execute(
                    f"""
                    SELECT id::text, {col}->>'en' AS en_text
                    FROM {table}
                    WHERE {col} IS NOT NULL
                      AND length(trim({col}->>'en')) > 0
                    """
                )
                rows = cur.fetchall()
                summary[key]["scanned"] = len(rows)

                for row_id, en_text in rows:
                    # Re-read ka to compute eligibility (avoid two SELECTs per row)
                    cur.execute(
                        f"SELECT {col}->>'ka' FROM {table} WHERE id::text = %s",
                        (row_id,),
                    )
                    ka_text_row = cur.fetchone()
                    ka_text = ka_text_row[0] if ka_text_row else None

                    if ka_text != en_text:
                        # Already translated (or null) — skip per idempotency contract
                        summary[key]["skipped_translated"] += 1
                        continue

                    summary[key]["eligible"] += 1

                    pair = compose_bilingual(prompt=en_text, client=client)

                    red = redact_bilingual(pair)
                    if red["blocked_or"]:
                        summary[key]["blocked"] += 1
                        blocked.append((table, col, row_id, red["blocked_reasons"]))
                        continue

                    new_en = pair["en"]
                    new_ka = pair["ka"]

                    if dry_run:
                        print(
                            f"  [DRY] {table}.{col} id={row_id[:8]}…: "
                            f"en={_truncate(new_en)!r} → ka={_truncate(new_ka)!r}"
                        )
                    else:
                        cur.execute(
                            f"""
                            UPDATE {table}
                            SET {col} = jsonb_build_object('en', %s::text, 'ka', %s::text)
                            WHERE id::text = %s
                            """,
                            (new_en, new_ka, row_id),
                        )
                        summary[key]["updated"] += 1

        if dry_run:
            conn.rollback()
        else:
            conn.commit()
    except Exception as exc:
        conn.rollback()
        sys.stderr.write(f"\nERROR: rolled back — {exc!r}\n")
        return 2
    finally:
        conn.close()

    print("\n=== per-table summary ===")
    print(
        f"{'table.column':<40} {'scanned':>8} {'eligible':>9} {'updated':>8} {'blocked':>8} {'skipped':>8}"
    )
    for key, s in summary.items():
        print(
            f"{key:<40} {s['scanned']:>8} {s['eligible']:>9} "
            f"{s['updated']:>8} {s['blocked']:>8} {s['skipped_translated']:>8}"
        )

    if blocked:
        print(f"\n=== PHI-redactor blocked ({len(blocked)}) ===")
        for table, col, row_id, reasons in blocked:
            print(f"  {table}.{col} id={row_id[:8]}… → {reasons}")

    if dry_run:
        print("\nDRY RUN complete — no writes, rollback issued.")
    else:
        print("\nLIVE BACKFILL complete — transaction committed.")
        if test_mode:
            print(
                "\n⚠ test-mode: ka written as '[KA-PLACEHOLDER] …'. "
                "Re-run without BILINGUAL_TEST_MODE=1 + a real ANTHROPIC_API_KEY for real Georgian."
            )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill ka content for migration-012 mirror rows via compose_bilingual."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended UPDATEs without writing; transaction rolled back at end.",
    )
    args = parser.parse_args()
    return backfill(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
