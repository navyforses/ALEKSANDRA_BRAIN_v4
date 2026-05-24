"""scripts/migrations/016_restore_hypotheses.py — EMERGENCY restore.

User accidentally deleted all 10 hypotheses rows from production Supabase
via Table Editor "select all" + delete. Supabase Free tier has no backups.

Recovery source: scripts/hypothesis/dspy_training/*.jsonl (10 curated
training files written 2026-05-16 by phase2_5_finalize_validation.py).
Each JSONL holds the ORIGINAL hypothesis_id + title + full description +
type + status + confidence_level + scores + supporting_paper_ids +
ai_reasoning. This is canonical source-of-truth pre-DB.

This script:
- Reads all 10 JSONL files.
- For each row, builds JSONB {en, ka} for title + description (translates
  en→ka via direct anthropic.messages.create with sonnet-4-6 + reframed
  prompt — same primitive that worked in 015).
- INSERTs the row preserving original id (so supporting_paper FKs in other
  tables still resolve).
- Single transaction. ROLLBACK on any error.

Apply:
    python -m scripts.migrations.016_restore_hypotheses --dry-run
    python -m scripts.migrations.016_restore_hypotheses
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

import psycopg2
from psycopg2.extras import Json

JSONL_DIR = pathlib.Path("scripts/hypothesis/dspy_training")


def _load_env():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def _connect():
    _load_env()
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")


def translate_to_georgian(client, text, max_attempts=3):
    """Same translator as 015 — sonnet-4-6 + reframed prompt."""
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
                    "markdown formatting. Output ONLY the Georgian translation "
                    "— no commentary, no quotes, no preamble. The text is "
                    "descriptive scientific terminology, not a medical "
                    "recommendation; do not refuse."
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
            last_err = f"empty/refusal (stop_reason={resp.stop_reason})"
        except Exception as e:
            last_err = repr(e)
        time.sleep(1 + attempt)
    raise RuntimeError(f"translate failed: {last_err}")


def load_jsonl_rows():
    rows = []
    for p in sorted(JSONL_DIR.glob("*.jsonl")):
        line = p.read_text(encoding="utf-8").strip().split("\n")[0]
        d = json.loads(line)
        inp = d.get("input", {})
        exp = d.get("expected", {})
        rows.append(
            {
                "id": d["hypothesis_id"],
                "title_en": d["title"],
                "description_en": inp.get("description", ""),
                "hypothesis_type": inp.get("hypothesis_type", "other"),
                "ai_reasoning": inp.get("ai_reasoning", ""),
                "status": exp.get("status", "new"),
                "confidence_level": exp.get("confidence_level"),
                "novelty_score": exp.get("novelty_score"),
                "feasibility_score": exp.get("feasibility_score"),
                "supporting_papers": exp.get("supporting_paper_ids", []),
            }
        )
    return rows


def restore(dry_run=False):
    _load_env()
    if (
        "SUPABASE_DB_URL" not in os.environ
        or not os.environ.get("ANTHROPIC_API_KEY", "").strip()
    ):
        sys.stderr.write("ERROR: SUPABASE_DB_URL + ANTHROPIC_API_KEY required\n")
        return 2

    rows = load_jsonl_rows()
    print(f"\n=== migration 016 — RESTORE hypotheses ({len(rows)} rows from JSONL) ===")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE INSERT'}\n")

    import anthropic

    client = anthropic.Anthropic()

    conn = _connect()
    conn.autocommit = False
    inserted = 0
    try:
        with conn.cursor() as cur:
            # Safety check: refuse if hypotheses already populated (prevent dup)
            cur.execute("SELECT count(*) FROM hypotheses")
            existing = cur.fetchone()[0]
            if existing > 0 and not dry_run:
                sys.stderr.write(
                    f"ERROR: hypotheses table has {existing} rows. Refusing to "
                    f"INSERT (would create duplicates). Investigate before re-running.\n"
                )
                return 2

            for r in rows:
                title_en = r["title_en"]
                desc_en = r["description_en"]

                print(f"  [TRANSLATE] {r['id'][:8]} — {title_en[:50]}...")
                try:
                    title_ka = translate_to_georgian(client, title_en)
                except RuntimeError as e:
                    print(f"    [WARN] title refused, falling back to en: {e}")
                    title_ka = title_en
                if desc_en.strip():
                    try:
                        desc_ka = translate_to_georgian(client, desc_en)
                    except RuntimeError as e:
                        print(f"    [WARN] desc refused, falling back to en: {e}")
                        desc_ka = desc_en
                else:
                    desc_ka = ""

                title_jsonb = {"en": title_en, "ka": title_ka}
                desc_jsonb = {"en": desc_en, "ka": desc_ka}

                if dry_run:
                    print(
                        f"    [DRY] would insert id={r['id'][:8]} type={r['hypothesis_type']} status={r['status']} papers={len(r['supporting_papers'])}"
                    )
                    print(f"          ka_title: {title_ka[:60]}")
                    continue

                cur.execute(
                    """
                    INSERT INTO hypotheses (
                        id, title, description, hypothesis_type,
                        supporting_papers, confidence_level,
                        novelty_score, feasibility_score,
                        ai_reasoning, status, generated_by, generation_batch
                    ) VALUES (%s, %s, %s, %s, %s::uuid[], %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        r["id"],
                        Json(title_jsonb),
                        Json(desc_jsonb),
                        r["hypothesis_type"],
                        r["supporting_papers"] or None,
                        r["confidence_level"],
                        r["novelty_score"],
                        r["feasibility_score"],
                        r["ai_reasoning"],
                        r["status"],
                        "claude-sonnet-4-5 (restored by 016)",
                        "phase2_5_finalize_validation + 016_restore",
                    ),
                )
                inserted += 1
                print(f"    [OK] inserted id={r['id'][:8]}")

        if dry_run:
            conn.rollback()
            print("\nDRY RUN — rolled back.")
        else:
            conn.commit()
            print(
                f"\nLIVE RESTORE complete — inserted {inserted}/{len(rows)} hypotheses."
            )

    except Exception as e:
        conn.rollback()
        sys.stderr.write(f"\nERROR: rolled back — {e!r}\n")
        return 2
    finally:
        conn.close()

    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    return restore(dry_run=p.parse_args().dry_run)


if __name__ == "__main__":
    sys.exit(main())
