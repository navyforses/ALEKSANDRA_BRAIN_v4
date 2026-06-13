"""scripts/migrations/025_repair_bilingual_ka.py — general bilingual ka repair.

A professional, table-driven successor to 024 (which fixed papers.title only).
After migration 017 made papers.title/abstract JSONB, the remaining bilingual
JSONB fields across the family-facing tables still carry the Phase-6.1
`compose_bilingual` damage and untranslated mirrors:

  - therapies.name           — multi-paragraph dossiers, 2 semantic mistranslations,
                               2 unusable en ("**" / fully blank)
  - therapies.evidence_summary — blank ka where en exists
  - hypotheses.title         — leading-markdown + 2 English mirrors
  - aleksandra_timeline.title — leading-markdown (translation otherwise correct)
  - papers.abstract          — 499 en==ka mirrors (untranslated), 109 null

Per field we choose the *least destructive* correct action:

  keep      — ka is already good; only strip a leading "# "/"**" (LOSSLESS, no API)
  translate — ka is blank / an English mirror / a dossier / non-Georgian / has
              stray CJK / commentary → (re)translate from en
  flag      — en itself is unusable (garbage "**" or fully blank) → leave it,
              report for manual rebuild; NEVER invent content

Field "kind":
  title — one Mkhedruli line. Strict single-line prompt (_TITLE_SYSTEM), first
          line only, no markdown/commentary/CJK.
  prose — abstracts / summaries. Faithful translation via the shared
          scripts.extraction.translate.translate_to_georgian (markdown-aware),
          then a leading-header strip; multi-line is allowed, CJK/commentary
          is not.

Field "strategy":
  auto        — keep-if-good-else-translate (used where existing translations
                are trustworthy: timeline, hypotheses, abstracts)
  retranslate — always re-translate from en (used for therapies.name, whose ka
                holds dossiers AND silent semantic errors a heuristic can't see;
                en is the short authoritative source)

REST-only (psql/psycopg2 unusable — Supavisor pooler password fails auth).
Budget-guarded, resume-safe, refusal-safe. Backup lives in
/tmp/aleksandra_ka_backup2/ (captured before this script writes).

Usage:
  python -m scripts.migrations.025_repair_bilingual_ka                      # dry run, all tables
  python -m scripts.migrations.025_repair_bilingual_ka --table therapies    # one table
  python -m scripts.migrations.025_repair_bilingual_ka --table therapies --apply
  python -m scripts.migrations.025_repair_bilingual_ka --table papers --field abstract --apply
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from scripts.extraction.gemini_translator import (
    TranslationFailed,
    translate_prose,
    translate_title,
)

# --------------------------------------------------------------------------- #
# config — what to repair
# --------------------------------------------------------------------------- #

TABLES: dict[str, dict] = {
    "therapies": {
        "id_col": "id",
        "fields": [
            # "auto" for ongoing/scheduled runs (idempotent: only fixes broken
            # rows, skips clean ones — no churn, near-zero cost). The one-time
            # "retranslate" cleanup that fixed the silent mistranslations was
            # already applied 2026-06-13; pass --retranslate-names to force it.
            {"name": "name", "kind": "title", "strategy": "auto"},
            {"name": "evidence_summary", "kind": "prose", "strategy": "auto"},
        ],
    },
    "hypotheses": {
        "id_col": "id",
        "fields": [
            {"name": "title", "kind": "title", "strategy": "auto"},
            {"name": "description", "kind": "prose", "strategy": "auto"},
        ],
    },
    "aleksandra_timeline": {
        "id_col": "id",
        "fields": [
            {"name": "title", "kind": "title", "strategy": "auto"},
            {"name": "description", "kind": "prose", "strategy": "auto"},
        ],
    },
    "papers": {
        "id_col": "id",
        "fields": [
            {"name": "title", "kind": "title", "strategy": "auto"},
            {"name": "abstract", "kind": "prose", "strategy": "auto"},
        ],
    },
}

TITLE_MAX_TOKENS = 256
PROSE_MAX_TOKENS = 4096  # headroom so long abstracts are never truncated mid-sentence
TITLE_TRANSLATE_THRESHOLD = 350  # a title longer than this (after clean) is a blob

# --------------------------------------------------------------------------- #
# env + REST
# --------------------------------------------------------------------------- #


def _load_env() -> None:
    for candidate in (Path.cwd() / ".env", Path.cwd().parent / ".env"):
        try:
            for line in candidate.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, _, v = s.partition("=")
                k = k.strip()
                if k and os.environ.get(k) is None:
                    os.environ[k] = v.strip().strip("'\"")
        except OSError:
            pass


def _config() -> tuple[str, str]:
    return (os.environ.get("SUPABASE_URL") or "").rstrip("/"), os.environ.get(
        "SUPABASE_SERVICE_ROLE_KEY"
    ) or ""


def _rest(
    method: str, path: str, base: str, key: str, body: object | None = None
) -> list:
    url = f"{base}/rest/v1/{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("apikey", key)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("Prefer", "return=minimal")
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (trusted host)
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw else []


# --------------------------------------------------------------------------- #
# normalization helpers
# --------------------------------------------------------------------------- #

_MD_HEADER = re.compile(r"^\s*#{1,6}\s+")
_MD_HEADER_ML = re.compile(r"(?m)^\s*#{1,6}\s+")  # header markers on every line (prose)
_KA_COMMENTARY = (
    "გთხოვთ მიაწოდოთ",
    "მოდი, უფრო",
    "თარგმანი:",
    "I cannot",
    "I'm unable",
    "I am unable",
)


def _has_georgian(text: str | None) -> bool:
    return any("Ⴀ" <= ch <= "ჿ" for ch in (text or ""))


def _has_cjk(text: str | None) -> bool:
    return any("　" <= ch <= "鿿" for ch in (text or ""))


def _has_cyrillic(text: str | None) -> bool:
    # Georgian (U+10A0–10FF) never overlaps Cyrillic (U+0400–04FF); any Cyrillic
    # in a "Georgian" string is a translation artifact (e.g. "МРТ" for "MRI").
    return any("Ѐ" <= ch <= "ӿ" for ch in (text or ""))


def _coerce_en_ka(value: object) -> tuple[str | None, str | None]:
    """(en, ka) from a JSONB dict / JSON-text string / plain string, unwrapping
    one level of double-encoding."""
    en: object = None
    ka: object = None
    if isinstance(value, dict):
        en, ka = value.get("en"), value.get("ka")
    elif isinstance(value, str):
        s = value.strip()
        if s.startswith("{"):
            try:
                d = json.loads(s)
            except json.JSONDecodeError:
                d = None
            if isinstance(d, dict):
                en, ka = d.get("en"), d.get("ka")
            else:
                en = value
        else:
            en = value
    elif value is not None:
        en = str(value)
    if isinstance(en, str) and en.strip().startswith("{"):
        try:
            inner = json.loads(en.strip())
        except json.JSONDecodeError:
            inner = None
        if isinstance(inner, dict) and ("en" in inner or "ka" in inner):
            if not (
                isinstance(ka, str) and ka.strip() and not ka.strip().startswith("{")
            ):
                ka = inner.get("ka")
            en = inner.get("en")
    en_s = en if isinstance(en, str) else (None if en is None else str(en))
    ka_s = ka if isinstance(ka, str) else (None if ka is None else str(ka))
    return en_s, ka_s


def _clean_en(en: str | None, kind: str) -> str:
    """Recover a usable English source. Empty if en is garbage ('**', '')."""
    if not en:
        return ""
    s = str(en).strip().replace("**", "").strip()
    if not s or s in ("*", "-", "—"):
        return ""
    s = _MD_HEADER.sub("", s).strip()
    if kind == "title":
        s = s.split("\n", 1)[0].strip()  # a title is one line; drop trailing junk
    return s.strip()


def _clean_ka(text: str | None, kind: str) -> str:
    """Lossless cosmetic clean: strip a leading markdown header and bold markers.
    For a title also collapse to the first line."""
    if not text:
        return ""
    s = str(text).strip()
    if kind == "title":
        s = _MD_HEADER.sub("", s)
        if "\n" in s:
            s = s.split("\n", 1)[0]
    else:
        # prose keeps paragraphs but loses markdown section headers on any line
        s = _MD_HEADER_ML.sub("", s)
    s = s.replace("**", "").strip()
    return s


def _ka_messy(ka: str | None) -> bool:
    if not ka:
        return False
    if _has_cjk(ka) or _has_cyrillic(ka):
        return True
    return any(m in ka for m in _KA_COMMENTARY)


# --------------------------------------------------------------------------- #
# translation — delegated to the Gemini translator bot (gemini-3.5-flash).
# translate_title / translate_prose are imported at the top of the module;
# both apply the strict prompts + markdown/CJK/Cyrillic guards and raise
# TranslationFailed on a refusal or guard failure (caller then keeps en).
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# decision
# --------------------------------------------------------------------------- #


def decide(value: object, kind: str, strategy: str) -> tuple[str, str, str]:
    """Return (action, en_clean, ka_keep). action in {keep, translate, flag, skip}."""
    en_raw, ka_raw = _coerce_en_ka(value)
    en = _clean_en(en_raw, kind)
    ka_clean = _clean_ka(ka_raw, kind)

    if not en:
        # No usable English source. A title/name needs an en to be trustworthy
        # (its ka may be a leftover dossier fragment) → flag for manual rebuild.
        if kind == "title":
            return "flag", "", ka_clean
        # prose: a good standalone ka is acceptable; otherwise flag.
        if ka_clean and _has_georgian(ka_clean) and not _ka_messy(ka_clean):
            return "keep", "", ka_clean
        return "flag", "", ka_clean

    if strategy == "retranslate":
        return "translate", en, ka_clean

    # auto
    if not ka_clean:
        return "translate", en, ""
    if ka_clean.strip() == en.strip() or not _has_georgian(ka_clean):
        return "translate", en, ka_clean
    if _ka_messy(ka_clean):  # CJK / commentary
        return "translate", en, ka_clean
    if kind == "title" and (
        "\n" in ka_clean or len(ka_clean) > TITLE_TRANSLATE_THRESHOLD
    ):
        return "translate", en, ka_clean
    return "keep", en, ka_clean


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #


def _process_field(
    *,
    table: str,
    field: dict,
    base: str,
    key: str,
    apply_changes: bool,
    limit: int | None,
) -> dict:
    fname, kind, strategy = field["name"], field["kind"], field["strategy"]
    id_col = TABLES[table]["id_col"]
    rows = _rest("GET", f"{table}?select={id_col},{fname}&limit=5000", base, key)

    actions = {"keep": [], "translate": [], "flag": [], "skip": []}
    for r in rows:
        value = r.get(fname)
        en_raw, _ = _coerce_en_ka(value)
        if value is None and en_raw is None:
            actions["skip"].append(r)
            continue
        action, en, ka_keep = decide(value, kind, strategy)
        # Skip no-op keeps: stored value already equals the clean target.
        if action == "keep":
            en_write = en or _coerce_en_ka(value)[0]
            if (
                isinstance(value, dict)
                and value.get("en") == en_write
                and value.get("ka") == ka_keep
            ):
                action = "skip"
        r["_decision"] = (action, en, ka_keep)
        actions[action].append(r)

    print(f"\n=== {table}.{fname} [{kind}/{strategy}] ({len(rows)} rows) ===")
    print(
        f"  keep={len(actions['keep'])} translate={len(actions['translate'])} "
        f"flag={len(actions['flag'])} skip(null)={len(actions['skip'])}"
    )
    if actions["flag"]:
        print(
            f"  ⚠ FLAG (unusable en — manual rebuild): {[r[id_col][:8] for r in actions['flag']]}"
        )

    todo = actions["keep"] + actions["translate"]
    if not apply_changes:
        for r in actions["translate"][:3]:
            _, en, _ = r["_decision"]
            print(f"  would translate [{r[id_col][:8]}]: en={en[:70]!r}")
        print("  (dry run — no writes)")
        return {
            "keep": len(actions["keep"]),
            "translate": len(actions["translate"]),
            "flag": len(actions["flag"]),
            "patched": 0,
            "failures": 0,
            "failed": [],
        }

    from scripts.cognition.budget import BudgetExceeded

    if limit:
        todo = todo[:limit]
    patched = kept = translated = failures = 0
    failed: list[str] = []
    for i, r in enumerate(todo, 1):
        rid = str(r[id_col])
        short = rid[:8]
        action, en, ka_keep = r["_decision"]
        try:
            if action == "translate":
                ka_final = (
                    translate_title(en) if kind == "title" else translate_prose(en)
                )
                translated += 1
            else:  # keep
                ka_final = ka_keep
                en = en or _coerce_en_ka(r.get(fname))[0]
                kept += 1
        except BudgetExceeded:
            sys.stderr.write(
                f"[025] BUDGET EXCEEDED at {table}.{fname} row {i} — stop (resume-safe)\n"
            )
            break
        except TranslationFailed as e:
            failures += 1
            failed.append(short)
            sys.stderr.write(f"  [{short}] {e}\n")
            continue
        _rest(
            "PATCH",
            f"{table}?{id_col}=eq.{urllib.parse.quote(rid)}",
            base,
            key,
            {fname: {"en": en, "ka": ka_final}},
        )
        patched += 1
        tag = "xlate" if action == "translate" else "keep "
        print(f"  [{i}/{len(todo)}] {short} ({tag}) {ka_final[:60]!r}", flush=True)

    print(
        f"  --> patched={patched} (translated={translated} kept={kept}) failures={failures}"
    )
    return {
        "keep": kept,
        "translate": translated,
        "flag": len(actions["flag"]),
        "patched": patched,
        "failures": failures,
        "failed": failed,
    }


def run(
    *,
    table: str | None,
    field: str | None,
    apply_changes: bool,
    limit: int | None,
    retranslate_names: bool = False,
) -> int:
    _load_env()
    base, key = _config()
    if not base or not key:
        sys.stderr.write("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set\n")
        return 2
    if apply_changes and not (
        os.environ.get("OPENROUTER_API_KEY", "").strip()
        or os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("GOOGLE_AI_STUDIO_KEY", "").strip()
    ):
        sys.stderr.write(
            "ERROR: set OPENROUTER_API_KEY (production) or GEMINI_API_KEY "
            "(direct Google) for --apply — the translator bot needs one\n"
        )
        return 2

    targets = [table] if table else list(TABLES)
    overall_fail = 0
    for tname in targets:
        if tname not in TABLES:
            sys.stderr.write(f"unknown table {tname}\n")
            return 2
        for f in TABLES[tname]["fields"]:
            if field and f["name"] != field:
                continue
            # one-time forced re-translation of therapies.name (semantic fix)
            if retranslate_names and tname == "therapies" and f["name"] == "name":
                f = {**f, "strategy": "retranslate"}
            res = _process_field(
                table=tname,
                field=f,
                base=base,
                key=key,
                apply_changes=apply_changes,
                limit=limit,
            )
            overall_fail += res["failures"]
    print("\n[025] done." + ("" if apply_changes else "  (DRY RUN — pass --apply)"))
    return 0 if overall_fail == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--table", default=None, help="Limit to one table (default: all).")
    ap.add_argument(
        "--field", default=None, help="Limit to one field within the table."
    )
    ap.add_argument("--apply", action="store_true", help="Write (default: dry run).")
    ap.add_argument(
        "--limit", type=int, default=None, help="Patch at most N rows per field."
    )
    ap.add_argument(
        "--retranslate-names",
        action="store_true",
        help="One-time: force re-translation of every therapies.name from en "
        "(fixes silent mistranslations a heuristic cannot see). Off by default "
        "so scheduled runs stay idempotent.",
    )
    args = ap.parse_args()
    return run(
        table=args.table,
        field=args.field,
        apply_changes=args.apply,
        limit=args.limit,
        retranslate_names=args.retranslate_names,
    )


if __name__ == "__main__":
    raise SystemExit(main())
