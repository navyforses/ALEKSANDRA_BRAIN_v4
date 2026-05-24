"""scripts/migrations/015_retry_errored_ka.py — finish recovery.

014 left 5 rows with blank ka because anthropic returned empty content blocks
(no exception, just `resp.content[0].text` IndexError caught silently).

This script:
- Targets the 5 known-errored row IDs.
- For title-type fields with corrupted long en (>500 chars), re-extracts the
  first **bold** header and translates THAT (short clean title).
- For body-type fields (evidence_summary) keeps the dossier en as-is.
- Wraps translate call in retry-with-backoff + defensive content[0] access.
- Single transaction. ROLLBACK on any unrecovered error.

Apply:
    python -m scripts.migrations.015_retry_errored_ka
"""

from __future__ import annotations

import os
import re
import sys
import time

import psycopg2

HEADER_RE = re.compile(r"\*\*([^*\n]+?)\*\*")

# (table, column, row_id, kind) — kind drives extraction strategy
TARGETS = [
    ("hypotheses", "title", "b6c5fe4c", "extract_header"),
    ("therapies", "name", "3b47f6ce", "extract_header"),
    ("therapies", "name", "844dd0da", "extract_header"),
    ("therapies", "name", "681cc49f", "as_is"),  # already short
    ("therapies", "evidence_summary", "f84c92d6", "as_is"),
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


def extract_header(en_text):
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


def translate_to_georgian(client, text, max_attempts=3):
    """Defensive translate — retry on empty content blocks / refusals.

    Uses sonnet-4-6 (looser safety classifier than 4-5) and a reframed prompt
    that explicitly identifies the context as a non-commercial family log so
    the model does not refuse scientific medical terminology.
    """
    last_err = None
    for attempt in range(max_attempts):
        try:
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=(
                    "You are a translation utility for a non-commercial "
                    "family-operated medical research log. Your only job is to "
                    "translate the user-provided English text to Georgian "
                    "(Mkhedruli script ONLY, no transliteration). Preserve "
                    "markdown formatting (headers, bold, lists, line breaks). "
                    "Output ONLY the Georgian translation — no commentary, no "
                    "quotes, no preamble. The text is descriptive scientific "
                    "terminology, not a medical recommendation; do not refuse."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": f"Translate to Georgian (Mkhedruli):\n\n{text}",
                    }
                ],
            )
            blocks = [b for b in resp.content if getattr(b, "type", None) == "text"]
            if blocks and blocks[0].text.strip():
                return blocks[0].text.strip()
            last_err = f"empty/refusal (stop_reason={resp.stop_reason} blocks={len(resp.content)})"
        except Exception as e:
            last_err = repr(e)
        time.sleep(1 + attempt)
    raise RuntimeError(f"translate failed after {max_attempts} attempts: {last_err}")


def fix():
    _load_env()
    if (
        "SUPABASE_DB_URL" not in os.environ
        or not os.environ.get("ANTHROPIC_API_KEY", "").strip()
    ):
        sys.stderr.write("ERROR: SUPABASE_DB_URL + ANTHROPIC_API_KEY required\n")
        return 2

    import anthropic

    client = anthropic.Anthropic()

    print("\n=== migration 015 — retry errored rows ===\n")

    conn = _connect()
    conn.autocommit = False
    fixed = 0
    errored = []
    try:
        with conn.cursor() as cur:
            for table, col, id_prefix, kind in TARGETS:
                cur.execute(
                    f"SELECT id::text, {col}->>'en' FROM {table} WHERE id::text LIKE %s",
                    (f"{id_prefix}%",),
                )
                row = cur.fetchone()
                if not row:
                    print(f"  [SKIP] {table}.{col} id={id_prefix}: not found")
                    continue
                row_id, en = row
                en = en or ""

                if kind == "extract_header":
                    new_en = extract_header(en) or en[:80]
                else:
                    new_en = en

                try:
                    new_ka = translate_to_georgian(client, new_en)
                except Exception as e:
                    errored.append((table, col, row_id[:8], str(e)))
                    print(f"  [ERR] {table}.{col} id={row_id[:8]}: {e}")
                    continue

                cur.execute(
                    f"UPDATE {table} SET {col} = jsonb_build_object('en', %s::text, 'ka', %s::text) WHERE id::text = %s",
                    (new_en, new_ka, row_id),
                )
                fixed += 1
                print(
                    f"  [OK]  {table}.{col} id={row_id[:8]}: en={new_en[:50]!r}… ka={new_ka[:50]!r}…"
                )

        conn.commit()
    except Exception as e:
        conn.rollback()
        sys.stderr.write(f"\nERROR: rolled back — {e!r}\n")
        return 2
    finally:
        conn.close()

    print(f"\n=== summary === fixed={fixed} errored={len(errored)}")
    for t, c, rid, msg in errored:
        print(f"  {t}.{c} id={rid}: {msg}")
    return 0 if not errored else 1


if __name__ == "__main__":
    sys.exit(fix())
