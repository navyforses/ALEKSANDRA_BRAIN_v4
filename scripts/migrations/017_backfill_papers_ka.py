"""scripts/migrations/017_backfill_papers_ka.py — translate existing papers.

After scripts/migrations/017_papers_jsonb.sql lands, every row in `papers`
has title.ka == title.en and abstract.ka == abstract.en (raw mirror). This
script iterates those rows and replaces the `ka` half with a real Georgian
translation using the shared `scripts.extraction.translate` helper.

Idempotent: only processes rows where `ka == en` (i.e. not yet translated).
Re-running picks up where the previous run stopped.

Safety rails:
  - Hard-stop after MAX_ERRORS consecutive empty/refusal responses.
  - Daily-budget gate before every translate call.
  - Single transaction per row (failure rolls back only that row).
  - DRY-RUN mode (default) prints what would change without writing.

Apply:
    # dry run first to confirm the row count
    python -m scripts.migrations.017_backfill_papers_ka

    # commit
    python -m scripts.migrations.017_backfill_papers_ka --apply

    # resume after interruption
    python -m scripts.migrations.017_backfill_papers_ka --apply
"""

from __future__ import annotations

import argparse
import os
import sys

import psycopg2

from scripts.extraction.translate import (
    BudgetExceeded,
    TranslationFailed,
    translate_to_georgian,
)

MAX_CONSECUTIVE_ERRORS = 3
TITLE_MAX_TOKENS = 512
ABSTRACT_MAX_TOKENS = 2048


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def _connect():
    _load_env()
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")


def _fetch_pending(cur, limit: int | None) -> list[tuple[str, str, str | None]]:
    """Return rows where ka == en for at least one of title/abstract."""
    q = (
        "SELECT id::text, title->>'en', abstract->>'en' "
        "FROM papers "
        "WHERE title->>'en' = title->>'ka' "
        "   OR (abstract IS NOT NULL AND abstract->>'en' = abstract->>'ka') "
        "ORDER BY ingested_at ASC NULLS LAST"
    )
    if limit:
        q += f" LIMIT {int(limit)}"
    cur.execute(q)
    return [(r[0], r[1], r[2]) for r in cur.fetchall()]


def run(*, apply_changes: bool, limit: int | None) -> int:
    if "SUPABASE_DB_URL" not in os.environ:
        sys.stderr.write("ERROR: SUPABASE_DB_URL not set\n")
        return 2
    if apply_changes and not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        sys.stderr.write("ERROR: ANTHROPIC_API_KEY required for --apply\n")
        return 2

    import anthropic

    client = anthropic.Anthropic() if apply_changes else None

    conn = _connect()
    conn.autocommit = False

    consecutive_errors = 0
    translated_titles = 0
    translated_abstracts = 0
    failures: list[str] = []

    try:
        with conn.cursor() as cur:
            pending = _fetch_pending(cur, limit)
            print(f"[017-backfill] {len(pending)} papers with untranslated ka")
            if not apply_changes:
                print("[017-backfill] DRY RUN — pass --apply to commit")

            for idx, (paper_id, title_en, abstract_en) in enumerate(pending, 1):
                short_id = paper_id[:8]
                print(f"[{idx}/{len(pending)}] {short_id}", flush=True)

                if not apply_changes:
                    continue

                try:
                    title_ka = translate_to_georgian(
                        title_en,
                        client=client,
                        max_tokens=TITLE_MAX_TOKENS,
                    )
                    if abstract_en:
                        abstract_ka = translate_to_georgian(
                            abstract_en,
                            client=client,
                            max_tokens=ABSTRACT_MAX_TOKENS,
                        )
                    else:
                        abstract_ka = None
                except BudgetExceeded:
                    sys.stderr.write(
                        "[017-backfill] BUDGET EXCEEDED — stopping. "
                        "Resume tomorrow or raise DAILY_BUDGET_USD.\n"
                    )
                    break
                except TranslationFailed as e:
                    consecutive_errors += 1
                    failures.append(f"{short_id}: {e}")
                    sys.stderr.write(f"  [fail] {e}\n")
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        sys.stderr.write(
                            f"[017-backfill] HARD STOP — "
                            f"{consecutive_errors} consecutive failures\n"
                        )
                        break
                    continue

                consecutive_errors = 0

                cur.execute(
                    "UPDATE papers "
                    "SET title = jsonb_set(title, '{ka}', to_jsonb(%s::text)) "
                    "WHERE id = %s::uuid",
                    (title_ka, paper_id),
                )
                translated_titles += 1

                if abstract_ka is not None:
                    cur.execute(
                        "UPDATE papers "
                        "SET abstract = jsonb_set("
                        "  abstract, '{ka}', to_jsonb(%s::text)) "
                        "WHERE id = %s::uuid",
                        (abstract_ka, paper_id),
                    )
                    translated_abstracts += 1

                conn.commit()
    finally:
        conn.close()

    print("\n=== 017-backfill summary ===")
    print(f"  titles translated:    {translated_titles}")
    print(f"  abstracts translated: {translated_abstracts}")
    print(f"  failures:             {len(failures)}")
    for f in failures[:10]:
        print(f"    - {f}")
    return 0 if not failures else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--apply",
        action="store_true",
        help="Actually translate and write (default is dry-run preview).",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after translating this many papers (for cost-bounded test runs).",
    )
    args = p.parse_args()
    return run(apply_changes=args.apply, limit=args.limit)


if __name__ == "__main__":
    sys.exit(main())
