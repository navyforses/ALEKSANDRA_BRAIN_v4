"""
audit_data_quality.py — read-only data-quality report for the family-facing
Supabase tables.

Answers, with live numbers, the question "how good is the data the site shows?":
  - row counts per table
  - provenance coverage   — what share of facts carry a source (the project's
                            first rule: never show a fact without one)
  - bilingual coverage    — en present / ka present / ka still an untranslated
                            English mirror / ka blank
  - corruption flags      — the Phase 6.1 failure mode where a title/name field
                            was overwritten with a multi-paragraph dossier or a
                            JSON-looking string, or where ka came back empty

It is strictly READ-ONLY (HTTP GET via the Supabase REST API) and never touches
PHI/MRI. Run it from the repo root:

    export SUPABASE_URL=...                 # or put these in ../.env / ./.env
    export SUPABASE_SERVICE_ROLE_KEY=...
    python scripts/audit_data_quality.py

Output is a plain-text report plus a one-line verdict per table.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# The JSONB {en, ka} columns created by migrations 012 (timeline / hypotheses /
# therapies) and 017 (papers). The first bilingual field of each table is the
# short "title-like" one where the Phase 6.1 dossier corruption showed up.
TABLES: dict[str, dict] = {
    "papers": {
        "bilingual": ["title", "abstract"],
        "text": ["ai_summary", "ai_aleksandra_implications"],
        "provenance_any": ["source", "source_url", "pmid", "doi"],
    },
    "hypotheses": {
        "bilingual": ["title", "description"],
        "text": ["ai_reasoning", "recommended_action"],
        "provenance_array": ["supporting_papers"],
    },
    "therapies": {
        "bilingual": ["name", "evidence_summary"],
        "text": ["mechanism_of_action", "ai_assessment"],
        "provenance_any": [
            "evidence_in_hie",
            "clinical_status",
            "best_evidence_paper_id",
        ],
    },
    "aleksandra_timeline": {
        "bilingual": ["title", "description"],
        "provenance_any": ["source", "source_url"],
    },
    "clinical_trials": {
        "text": ["title", "intervention"],
        "provenance_any": ["nct_id", "source_url"],
    },
    "brain_regions": {
        "text": ["name", "damage_description", "plasticity_notes"],
    },
    "pathways": {"text": ["name", "description"]},
    "discovery_reports": {"text": ["title", "executive_summary"]},
    "ingestion_log": {"text": ["source", "status"]},
    "manager_actions": {"text": ["action_type", "target_table"]},
    "outreach_log": {"text": ["trigger_kind", "channel"]},
    "alerts_log": {"text": ["tier", "event_kind"]},
    "briefs": {"briefs": True},
}


def load_env() -> None:
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


def config() -> tuple[str, str]:
    # .strip() guards against a secret pasted with a trailing newline (urllib
    # rejects header values containing "\n").
    url = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    return url, key


def fetch(table: str, url: str, key: str, limit: int = 5000) -> list[dict]:
    href = f"{url}/rest/v1/{table}?select=*&limit={limit}"
    req = urllib.request.Request(
        href,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (trusted Supabase host)
        return json.loads(resp.read().decode("utf-8"))


def is_blank(value: object) -> bool:
    return value is None or not str(value).strip()


def parse_bilingual(value: object) -> tuple[str | None, str | None]:
    """Return (en, ka). Handles JSONB dicts, JSON-looking strings, legacy TEXT."""
    if value is None:
        return None, None
    if isinstance(value, dict):
        return value.get("en"), value.get("ka")
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("{"):
            try:
                d = json.loads(s)
                if isinstance(d, dict):
                    return d.get("en"), d.get("ka")
            except json.JSONDecodeError:
                pass
        return value, None  # legacy TEXT = English only, ka not yet split out
    return str(value), None


def looks_corrupt(text: str | None) -> bool:
    """Heuristics for a short title/name field that was overwritten with a
    dossier or a serialized blob (the Phase 6.1 incident signature)."""
    if not text:
        return False
    s = str(text)
    if len(s) > 400:
        return True
    if s.count("\n") >= 3 or "\n\n" in s:
        return True
    if "## " in s or "**" in s:
        return True
    if s.lstrip().startswith(("{", "[")):
        return True
    return False


def pct(n: int, d: int) -> str:
    return f"{(100 * n / d):.0f}%" if d else "—"


def audit_table(name: str, spec: dict, rows: list[dict]) -> list[str]:
    n = len(rows)
    out = [f"\n=== {name}  ({n} rows) ==="]
    if n == 0:
        out.append("  (empty)")
        return out

    if spec.get("briefs"):
        with_sections = sum(1 for r in rows if r.get("sections"))
        ka_sections = 0
        for r in rows:
            sec = r.get("sections")
            if (
                isinstance(sec, dict)
                and json.dumps(sec, ensure_ascii=False).find('"ka"') >= 0
            ):
                ka_sections += 1
        out.append(
            f"  sections present : {with_sections}/{n} ({pct(with_sections, n)})"
        )
        out.append(f"  ka in sections   : {ka_sections}/{n} ({pct(ka_sections, n)})")
        return out

    for idx, field in enumerate(spec.get("bilingual", [])):
        en_ok = ka_ok = ka_mirror = ka_blank = corrupt = 0
        blank_ids: list[str] = []
        corrupt_ids: list[str] = []
        for r in rows:
            en, ka = parse_bilingual(r.get(field))
            rid = str(r.get("id") or "")[:8]
            if not is_blank(en):
                en_ok += 1
            if not is_blank(ka):
                ka_ok += 1
                if str(ka).strip() == str(en).strip():
                    ka_mirror += 1
            else:
                ka_blank += 1
                if en_ok:  # only worth fixing when there IS an English source
                    blank_ids.append(rid)
            if idx == 0 and (looks_corrupt(en) or looks_corrupt(ka)):
                corrupt += 1
                corrupt_ids.append(rid)
        ka_real = ka_ok - ka_mirror
        out.append(f"  {field} (en/ka):")
        out.append(f"      en present   : {en_ok}/{n} ({pct(en_ok, n)})")
        out.append(
            f"      ka real      : {ka_real}/{n} ({pct(ka_real, n)})"
            f"   · mirror(en==ka): {ka_mirror}   · blank: {ka_blank}"
        )
        if idx == 0:
            flag = "  ⚠" if corrupt else ""
            out.append(f"      corrupt title: {corrupt}/{n} ({pct(corrupt, n)}){flag}")
        # Remediation list — exactly which rows need a clean ka re-translation.
        if blank_ids:
            shown = ", ".join(blank_ids[:40])
            more = f" …(+{len(blank_ids) - 40})" if len(blank_ids) > 40 else ""
            out.append(f"      → FIX ka blank   [{field}]: {shown}{more}")
        if corrupt_ids:
            shown = ", ".join(corrupt_ids[:40])
            more = f" …(+{len(corrupt_ids) - 40})" if len(corrupt_ids) > 40 else ""
            out.append(f"      → FIX ka corrupt [{field}]: {shown}{more}")

    for field in spec.get("text", []):
        present = sum(1 for r in rows if not is_blank(r.get(field)))
        out.append(f"  {field:<26} present: {present}/{n} ({pct(present, n)})")

    if "provenance_any" in spec:
        cols = spec["provenance_any"]
        with_src = sum(1 for r in rows if any(not is_blank(r.get(c)) for c in cols))
        flag = "" if with_src == n else "  ⚠ some rows have no source"
        out.append(
            f"  PROVENANCE (any of {', '.join(cols)}): {with_src}/{n} ({pct(with_src, n)}){flag}"
        )

    if "provenance_array" in spec:
        col = spec["provenance_array"][0]
        with_src = sum(
            1 for r in rows if isinstance(r.get(col), list) and len(r.get(col)) > 0
        )
        flag = "" if with_src == n else f"  ⚠ {n - with_src} without {col}"
        out.append(
            f"  PROVENANCE ({col} non-empty): {with_src}/{n} ({pct(with_src, n)}){flag}"
        )

    return out


def main() -> int:
    load_env()
    url, key = config()
    if not url or not key:
        print(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set.\n"
            "Export them (or put them in .env) and re-run. This script is read-only.",
            file=sys.stderr,
        )
        return 2

    print("ALEKSANDRA_BRAIN — data quality audit (read-only)")
    print(f"target: {url}")
    lines: list[str] = []
    for name, spec in TABLES.items():
        try:
            rows = fetch(name, url, key)
        except urllib.error.HTTPError as e:
            lines.append(
                f"\n=== {name} ===\n  HTTP {e.code} — {e.reason} (table missing or RLS?)"
            )
            continue
        except Exception as e:  # noqa: BLE001
            lines.append(f"\n=== {name} ===\n  error: {type(e).__name__}: {e}")
            continue
        lines.extend(audit_table(name, spec, rows))

    print("\n".join(lines))
    print("\nLegend: 'mirror(en==ka)' = ka is still the untranslated English copy.")
    print("        'corrupt title'  = title/name overwritten by a dossier or blob.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
