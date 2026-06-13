"""scripts/migrations/024_fix_papers_title_ka.py — repair papers.title.ka.

(Numbered 024, not 018 — 018 is already taken by 018_scm_tables.sql.)

Context
-------
Migration 017_papers_jsonb.sql converts papers.title TEXT -> JSONB {en, ka}.
The live TEXT column holds a MIX of two shapes:
  - plain English titles                  (older rows / direct fetch inserts)
  - build_bilingual() dicts that PostgREST stringified into JSON-text, e.g.
    '{"en":"X","ka":"Y"}'                  (rows written via process_ledger)

017's naive `jsonb_build_object('en', title, 'ka', title)` mirror therefore
produces:
  - plain rows  -> {"en":"English title", "ka":"English title"}   (ka == en mirror)
  - json-text   -> {"en":'{"en":"X","ka":"Y"}', "ka":'<same>'}    (en double-encoded)

This one-shot backfill normalizes EVERY papers.title to a clean JSONB {en, ka}:
  1. unwrap any double-encoded en/ka (the json-text rows)
  2. strip leading markdown ("#..# ", "**") from ka
  3. (re)translate ka from en when ka is blank, an English mirror, or still bad
  4. PATCH the row with a proper JSONB object

Scope: papers.title ONLY (abstract deferred — operator decision 2026-06-12).

Why REST, not psql
------------------
The Supavisor pooler password in SUPABASE_DB_URL fails auth (known "pooler
drift"), so psql / psycopg2 cannot connect. Every read + write here goes
through the PostgREST endpoint with the service-role key (which works and
bypasses RLS), matching scripts/communicator/ensure_family_contact.py.

Translation
-----------
scripts.extraction.translate.translate_to_georgian with an INJECTED anthropic
client -> forces the sonnet-4-6 strict path with the reframed
"translation utility ... do not refuse" system prompt (the 014/015 lesson).
Refusals raise TranslationFailed (content=[] / stop_reason='refusal' handled
inside the helper). On failure the English is kept and the id is logged — an
invented ka is NEVER written; a blank ka is preferred over a fabricated one.

Safety
------
  - --dry-run (default) prints the plan and a few REAL sample translations.
  - --apply writes. It REFUSES to run while papers.title is still TEXT (017
    not yet applied) so a dict is never re-stringified back into a TEXT column.
  - check_daily_budget() gate lives inside translate_to_georgian; a hard
    per-run --limit is also available.
  - Per-row PATCH; one row's failure never blocks the rest.

Usage
-----
  python -m scripts.migrations.024_fix_papers_title_ka                 # dry run
  python -m scripts.migrations.024_fix_papers_title_ka --apply
  python -m scripts.migrations.024_fix_papers_title_ka --apply --limit 5
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

# --------------------------------------------------------------------------- #
# env + REST plumbing
# --------------------------------------------------------------------------- #


def _load_env() -> None:
    """Populate os.environ from ./.env or ../.env (mirrors audit_data_quality)."""
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
    url = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""
    return url, key


def _rest(
    method: str, path: str, base: str, key: str, body: object | None = None
) -> list:
    """Minimal PostgREST call with the service-role key (bypasses RLS)."""
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


def _title_is_jsonb(base: str, key: str) -> bool:
    """Authoritative column-type check via the PostgREST OpenAPI schema."""
    req = urllib.request.Request(
        f"{base}/rest/v1/",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/openapi+json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        spec = json.loads(resp.read().decode("utf-8"))
    defs = spec.get("definitions") or spec.get("components", {}).get("schemas", {})
    fmt = (defs.get("papers", {}).get("properties", {}).get("title", {}) or {}).get(
        "format"
    )
    return fmt == "jsonb"


# --------------------------------------------------------------------------- #
# value normalization
# --------------------------------------------------------------------------- #

_MD_HEADER = re.compile(r"^\s*#{1,6}\s+")


def _coerce_en_ka(value: object) -> tuple[str | None, str | None]:
    """Return (en, ka) from a title value that may be a JSONB dict, a JSON-text
    string, or a plain string — unwrapping one level of double-encoding."""
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

    # Unwrap a double-encoded en (017 wrapped a JSON-text row): en itself is
    # the literal '{"en":"X","ka":"Y"}'. Prefer the inner values.
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


def _clean_ka(text: str | None) -> str:
    """Strip leading markdown header markers and bold markers from a ka title."""
    if not text:
        return ""
    s = str(text).strip()
    s = _MD_HEADER.sub("", s)
    s = s.replace("**", "")
    return s.strip()


def _has_georgian(text: str | None) -> bool:
    return any("Ⴀ" <= ch <= "ჿ" for ch in (text or ""))


def _has_cjk(text: str | None) -> bool:
    return any("　" <= ch <= "鿿" for ch in (text or ""))


# Commentary the translator sometimes prepends instead of just translating.
_KA_COMMENTARY = (
    "გთხოვთ",
    "მოდი,",
    "თარგმანი:",
    "translation",
    "I cannot",
    "I'm unable",
)


def _ka_is_messy(ka: str | None) -> bool:
    """A clean title is one Mkhedruli line. Flag multi-line / markdown /
    horizontal-rule / model-commentary / stray-CJK outputs for a re-translate."""
    if not ka:
        return False
    if "\n" in ka or "---" in ka or "##" in ka or ka.lstrip().startswith("#"):
        return True
    if _has_cjk(ka):
        return True
    return any(m in ka for m in _KA_COMMENTARY)


def _titleize(text: str) -> str:
    """Reduce a translator response to a single clean title line: take the
    first paragraph, drop markdown / quotes / alternative-version separators."""
    s = (text or "").strip()
    for sep in ("\n---", "\n\n", "\n"):
        if sep in s:
            s = s.split(sep, 1)[0].strip()
    s = _MD_HEADER.sub("", s).replace("**", "").strip()
    return s.strip("\"'").strip()


# A title-specific system prompt — unlike scripts/extraction/translate.py it does
# NOT ask to "preserve markdown", which is what made sonnet-4-6 elaborate a few
# titles into essays / multi-version answers in the first place.
_TITLE_SYSTEM = (
    "You translate a single research-paper TITLE from English to Georgian "
    "(Mkhedruli script only). Output ONLY the Georgian title on ONE line — no "
    "commentary, no alternative versions, no markdown, no quotes, no '---', no "
    "explanation. If the English is truncated, translate only what is given. "
    "Use ONLY Georgian Mkhedruli letters plus Latin letters/digits for proper "
    "nouns and acronyms; never use Chinese, Japanese, or any other script. "
    "The text is descriptive scientific terminology, not medical advice; do not "
    "refuse."
)


def _translate_title_strict(client, en: str, max_tokens: int = 200) -> str:
    """Direct sonnet-4-6 call with the title-only prompt. Raises on refusal."""
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=_TITLE_SYSTEM,
        messages=[
            {"role": "user", "content": f"Translate this title to Georgian:\n\n{en}"}
        ],
    )
    blocks = [b for b in resp.content if getattr(b, "type", None) == "text"]
    if not blocks or not blocks[0].text.strip():
        from scripts.extraction.translate import TranslationFailed

        raise TranslationFailed(f"empty/refusal (stop_reason={resp.stop_reason})")
    return _titleize(blocks[0].text)


def _ka_needs_translation(en: str | None, ka_clean: str) -> bool:
    """True when ka is missing, an English mirror, non-Georgian, or still
    looks like a corrupted blob rather than a title."""
    if not ka_clean:
        return True
    if en and ka_clean.strip() == en.strip():
        return True
    if not _has_georgian(ka_clean):
        return True
    if len(ka_clean) > 400 or ka_clean.count("\n") >= 3:
        return True
    return False


# --------------------------------------------------------------------------- #
# planning
# --------------------------------------------------------------------------- #


class Plan:
    __slots__ = ("rid", "en", "cur_ka", "ka_clean", "needs_xlate", "needs_write")

    def __init__(self, rid, en, cur_ka, ka_clean, needs_xlate, needs_write):
        self.rid = rid
        self.en = en
        self.cur_ka = cur_ka
        self.ka_clean = ka_clean
        self.needs_xlate = needs_xlate
        self.needs_write = needs_write


def _build_plan(rows: list[dict]) -> list[Plan]:
    plans: list[Plan] = []
    for r in rows:
        rid = str(r.get("id") or "")
        en, ka = _coerce_en_ka(r.get("title"))
        ka_clean = _clean_ka(ka)
        needs_xlate = _ka_needs_translation(en, ka_clean)

        # A write is needed when the stored value is NOT already a clean dict
        # equal to our target, OR when ka must change.
        stored = r.get("title")
        already_clean_dict = (
            isinstance(stored, dict)
            and stored.get("en") == en
            and stored.get("ka") == ka_clean
            and not needs_xlate
        )
        needs_write = bool(en) and not already_clean_dict
        plans.append(Plan(rid, en, ka, ka_clean, needs_xlate, needs_write))
    return plans


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #


def run(*, apply_changes: bool, limit: int | None, samples: int) -> int:
    _load_env()
    base, key = _config()
    if not base or not key:
        sys.stderr.write("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set\n")
        return 2

    is_jsonb = _title_is_jsonb(base, key)
    print(f"[024] papers.title column format: {'jsonb' if is_jsonb else 'TEXT'}")

    if apply_changes and not is_jsonb:
        sys.stderr.write(
            "\nREFUSING --apply: papers.title is still TEXT.\n"
            "Run scripts/migrations/017_papers_jsonb.sql in the Supabase SQL\n"
            "Editor first (see scripts/migrations/024_runbook.md), then re-run\n"
            "with --apply. Writing a dict into a TEXT column would re-create the\n"
            "JSON-as-text corruption this script exists to fix.\n"
        )
        return 3

    if apply_changes and not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        sys.stderr.write("ERROR: ANTHROPIC_API_KEY required for --apply\n")
        return 2

    rows = _rest("GET", "papers?select=id,title&limit=5000", base, key)
    print(f"[024] fetched {len(rows)} papers")

    plans = _build_plan(rows)
    to_write = [p for p in plans if p.needs_write]
    to_xlate = [p for p in to_write if p.needs_xlate]
    strip_only = [p for p in to_write if not p.needs_xlate]
    no_en = [p for p in plans if not p.en]

    print("\n=== plan ===")
    print(f"  total papers            : {len(plans)}")
    print(f"  rows needing a write    : {len(to_write)}")
    print(f"    - need ka translation : {len(to_xlate)}")
    print(f"    - structure/strip only: {len(strip_only)}")
    print(f"  rows already clean      : {len(plans) - len(to_write)}")
    if no_en:
        print(
            f"  ⚠ rows with no en (skipped): {len(no_en)}  e.g. {[p.rid[:8] for p in no_en[:5]]}"
        )

    if not apply_changes:
        # Show a few real sample translations so quality can be eyeballed.
        sample_pool = to_xlate[:samples]
        if sample_pool and os.environ.get("ANTHROPIC_API_KEY", "").strip():
            import anthropic

            from scripts.extraction.translate import (
                TranslationFailed,
                translate_to_georgian,
            )

            client = anthropic.Anthropic()
            print(
                f"\n=== {len(sample_pool)} SAMPLE translations (DRY RUN — not written) ==="
            )
            for p in sample_pool:
                try:
                    # _clean_ka strips any leading "# "/"**" the translator adds:
                    # titles must never carry markdown (it is the corruption mode).
                    ka = _clean_ka(
                        translate_to_georgian(p.en, client=client, max_tokens=512)
                    )
                    print(f"  [{p.rid[:8]}]")
                    print(f"    en: {p.en[:110]}")
                    print(f"    ka: {ka[:140]}")
                except TranslationFailed as e:
                    print(f"  [{p.rid[:8]}] TRANSLATION FAILED: {e}")
        elif sample_pool:
            print("\n(set ANTHROPIC_API_KEY to preview sample translations)")
        print("\n[024] DRY RUN — pass --apply to write. No rows changed.")
        return 0

    # --------------------------------------------------------------------- #
    # apply
    # --------------------------------------------------------------------- #
    import anthropic

    from scripts.cognition.budget import BudgetExceeded
    from scripts.extraction.translate import TranslationFailed, translate_to_georgian

    client = anthropic.Anthropic()
    targets = to_write[:limit] if limit else to_write

    translated = stripped = failures = patched = 0
    failed_ids: list[str] = []

    for idx, p in enumerate(targets, 1):
        short = p.rid[:8]
        ka_final = p.ka_clean

        if p.needs_xlate:
            try:
                # Strip any markdown the translator prepends — a title is never
                # markdown; an un-stripped "# " is the corruption we are fixing.
                ka_final = _clean_ka(
                    translate_to_georgian(p.en, client=client, max_tokens=512)
                )
                if not ka_final:
                    raise TranslationFailed("empty after markdown strip")
                translated += 1
            except BudgetExceeded:
                sys.stderr.write(
                    f"[024] BUDGET EXCEEDED at row {idx} — stopping. "
                    "Re-run tomorrow or raise DAILY_BUDGET_USD; it is resume-safe.\n"
                )
                break
            except TranslationFailed as e:
                # Keep en, do NOT invent ka. Still fix structure (ka cleaned/blank).
                failures += 1
                failed_ids.append(short)
                ka_final = p.ka_clean if _has_georgian(p.ka_clean) else ""
                sys.stderr.write(f"  [{short}] translate failed: {e}\n")
        else:
            stripped += 1

        try:
            _rest(
                "PATCH",
                f"papers?id=eq.{urllib.parse.quote(p.rid)}",
                base,
                key,
                {"title": {"en": p.en, "ka": ka_final}},
            )
            patched += 1
            mark = "xlate" if p.needs_xlate else "strip"
            print(
                f"[{idx}/{len(targets)}] {short} ({mark}) ka={ka_final[:60]!r}",
                flush=True,
            )
        except urllib.error.HTTPError as e:
            failures += 1
            failed_ids.append(short)
            sys.stderr.write(f"  [{short}] PATCH HTTP {e.code}: {e.reason}\n")

    print("\n=== 024 summary ===")
    print(f"  rows patched          : {patched}")
    print(f"  ka translated         : {translated}")
    print(f"  structure/strip only  : {stripped}")
    print(f"  failures (en kept)    : {failures}")
    if failed_ids:
        print(f"  failed ids            : {', '.join(failed_ids[:40])}")
    return 0 if failures == 0 else 1


def run_polish(*, apply_changes: bool) -> int:
    """Second-pass repair: find rows whose ka is multi-line / markdown /
    commentary / stray-CJK (a misbehaving first-pass translation) and
    re-translate them with the strict single-line title prompt."""
    _load_env()
    base, key = _config()
    if not base or not key:
        sys.stderr.write("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set\n")
        return 2
    if apply_changes and not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        sys.stderr.write("ERROR: ANTHROPIC_API_KEY required for --apply\n")
        return 2

    rows = _rest("GET", "papers?select=id,title&limit=5000", base, key)
    messy = []
    for r in rows:
        t = r.get("title")
        if isinstance(t, dict) and _ka_is_messy(t.get("ka")):
            messy.append(r)
    print(f"[024-polish] {len(messy)} rows with messy ka")
    for r in messy:
        t = r["title"]
        print(f"  [{str(r['id'])[:8]}] en={str(t.get('en'))[:60]!r}")

    if not apply_changes:
        print("\n[024-polish] DRY RUN — pass --apply to re-translate. No rows changed.")
        return 0

    import anthropic

    from scripts.extraction.translate import TranslationFailed

    client = anthropic.Anthropic()
    fixed = failures = 0
    failed_ids: list[str] = []
    for r in messy:
        rid = str(r["id"])
        short = rid[:8]
        en = r["title"].get("en")
        if not en:
            continue
        try:
            ka = _translate_title_strict(client, en)
            if not ka or _ka_is_messy(ka) or not _has_georgian(ka):
                raise TranslationFailed(f"still messy after strict retry: {ka[:60]!r}")
        except TranslationFailed as e:
            failures += 1
            failed_ids.append(short)
            sys.stderr.write(f"  [{short}] {e}\n")
            continue
        _rest(
            "PATCH",
            f"papers?id=eq.{urllib.parse.quote(rid)}",
            base,
            key,
            {"title": {"en": en, "ka": ka}},
        )
        fixed += 1
        print(f"  fixed [{short}] -> {ka[:70]!r}", flush=True)

    print("\n=== 024-polish summary ===")
    print(f"  rows re-translated : {fixed}")
    print(f"  still failing      : {failures}  {failed_ids}")
    return 0 if failures == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--apply", action="store_true", help="Write changes (default: dry run)."
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Patch at most N rows (cost-bounded test).",
    )
    ap.add_argument(
        "--samples", type=int, default=3, help="Sample translations to show in dry run."
    )
    ap.add_argument(
        "--polish",
        action="store_true",
        help="Second pass: re-translate rows whose ka is multi-line / markdown / "
        "commentary / stray-CJK using the strict single-line title prompt.",
    )
    args = ap.parse_args()
    if args.polish:
        return run_polish(apply_changes=args.apply)
    return run(apply_changes=args.apply, limit=args.limit, samples=args.samples)


if __name__ == "__main__":
    raise SystemExit(main())
