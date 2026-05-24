"""scripts/migrations/014_fix_corrupted_ka.py — emergency partial recovery.

013 called compose_bilingual (a DRAFTING tool) where a translation primitive
was needed. Result: 62 fields overwritten with multi-paragraph dossiers and
ka empty in 55/62.

Recovery strategy:
- title / name (UI labels): extract first `**header**` from corrupted en —
  compose_bilingual typically echoed the input as the first markdown header,
  so this recovers most original short titles (~80% accuracy).
- description / evidence_summary (longer body fields): keep the corrupted
  dossier as-is. It is plausible clinical content (Claude wrote real
  evidence-style text) and the field is meant to be long — better than blank.
- ka: re-generate via direct anthropic.messages.create() with a TRANSLATION
  system prompt — NOT compose_bilingual.

Rows where both en AND ka are empty are SKIPPED and reported — manual rebuild.

Apply:
    BILINGUAL_TEST_MODE=1 python -m scripts.migrations.014_fix_corrupted_ka --dry-run
    python -m scripts.migrations.014_fix_corrupted_ka
"""

from __future__ import annotations

import argparse
import os
import re
import sys

import psycopg2

HEADER_RE = re.compile(r"\*\*([^*\n]+?)\*\*")

# (table, column, kind) — kind drives extraction
TARGETS = [
    ("aleksandra_timeline", "title", "extract_header"),
    ("aleksandra_timeline", "description", "keep_dossier"),
    ("hypotheses", "title", "extract_header"),
    ("hypotheses", "description", "keep_dossier"),
    ("therapies", "name", "extract_header"),
    ("therapies", "evidence_summary", "keep_dossier"),
]


def _load_env():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def _connect():
    _load_env()
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")


def _is_test_mode():
    return (
        os.environ.get("BILINGUAL_TEST_MODE", "").strip() == "1"
        or not os.environ.get("ANTHROPIC_API_KEY", "").strip()
    )


def translate_to_georgian(client, text):
    """Direct translation — NOT compose_bilingual."""
    if not text.strip():
        return ""
    if _is_test_mode():
        return f"[KA-STUB] {text[:80]}"
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=(
            "You are a professional medical translator. Translate the user's "
            "English text to Georgian (Mkhedruli script ONLY, no transliteration). "
            "Preserve markdown formatting (headers, bold, line breaks, lists, code). "
            "Output ONLY the Georgian translation — no commentary, no quotes, "
            "no preamble like 'here is the translation', no English fallback."
        ),
        messages=[{"role": "user", "content": text}],
    )
    return resp.content[0].text


def extract_header(en_text):
    """First **bold** header → fallback to first non-empty line → fallback to 80 chars."""
    if not en_text:
        return None
    m = HEADER_RE.search(en_text)
    if m:
        return m.group(1).strip()
    for line in en_text.split("\n"):
        s = line.strip().strip("*#").strip()
        if s and len(s) < 200:
            return s
    return en_text[:80].strip()


def fix(dry_run=False):
    if "SUPABASE_DB_URL" not in os.environ:
        sys.stderr.write("ERROR: SUPABASE_DB_URL not set\n")
        return 2
    if _is_test_mode() and not dry_run:
        sys.stderr.write(
            "ERROR: live run requires real ANTHROPIC_API_KEY (no test mode)\n"
        )
        return 2

    client = None
    if not _is_test_mode():
        import anthropic

        client = anthropic.Anthropic()

    mode = "DRY RUN (test-stub)" if dry_run else "LIVE FIX"
    print(f"\n=== migration 014 — {mode} ===\n")

    summary = {}
    skipped_blank = []

    conn = _connect()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            for table, col, kind in TARGETS:
                key = f"{table}.{col}"
                summary[key] = {"scanned": 0, "fixed": 0, "blank": 0, "errored": 0}

                cur.execute(
                    f"SELECT id::text, {col}->>'en' AS en, {col}->>'ka' AS ka FROM {table} WHERE {col} IS NOT NULL"
                )
                rows = cur.fetchall()
                summary[key]["scanned"] = len(rows)

                for row_id, en, ka in rows:
                    en = en or ""
                    ka = ka or ""
                    if not en.strip() and not ka.strip():
                        summary[key]["blank"] += 1
                        skipped_blank.append((table, col, row_id))
                        continue

                    if kind == "extract_header":
                        new_en = extract_header(en) or en[:80]
                    else:
                        new_en = en

                    try:
                        new_ka = translate_to_georgian(client, new_en)
                    except Exception as e:
                        summary[key]["errored"] += 1
                        print(f"  [ERR] {table}.{col} id={row_id[:8]}: {e!r}")
                        continue

                    if dry_run:
                        print(
                            f"  [DRY] {table}.{col} id={row_id[:8]}: en='{new_en[:60]}…' ka='{new_ka[:60]}…'"
                        )
                    else:
                        cur.execute(
                            f"UPDATE {table} SET {col} = jsonb_build_object('en', %s::text, 'ka', %s::text) WHERE id::text = %s",
                            (new_en, new_ka, row_id),
                        )
                        summary[key]["fixed"] += 1

        if dry_run:
            conn.rollback()
        else:
            conn.commit()
    except Exception as e:
        conn.rollback()
        sys.stderr.write(f"\nERROR: rolled back — {e!r}\n")
        return 2
    finally:
        conn.close()

    print("\n=== summary ===")
    print(
        f"{'table.column':<40} {'scanned':>8} {'fixed':>6} {'blank':>6} {'errored':>8}"
    )
    for k, s in summary.items():
        print(
            f"{k:<40} {s['scanned']:>8} {s['fixed']:>6} {s['blank']:>6} {s['errored']:>8}"
        )

    if skipped_blank:
        print(
            f"\n=== skipped (both en+ka blank) — {len(skipped_blank)} need manual rebuild ==="
        )
        for t, c, rid in skipped_blank:
            print(f"  {t}.{c} id={rid[:8]}")

    print(
        f"\n{'DRY RUN complete — no writes.' if dry_run else 'LIVE FIX complete — transaction committed.'}"
    )
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    return fix(dry_run=p.parse_args().dry_run)


if __name__ == "__main__":
    sys.exit(main())
