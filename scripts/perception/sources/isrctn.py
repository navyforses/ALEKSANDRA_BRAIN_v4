"""isrctn.py — UK ISRCTN clinical-trial fetcher (source_type="isrctn").

Pulls trials from the UK ISRCTN registry query API for Aleksandra's condition
facets, normalizes EACH trial into the SAME ``payload_metadata`` shape +
vocabulary as ``scripts/fetch_ctgov.py``, uploads the FULL raw query-result XML
fragment to R2, and writes one ``evidence_ledger`` row per trial
(source_type="isrctn", source_id=ISRCTN number).

Verified pattern (docs/CLINICAL_TRIALS_SOURCES_RESEARCH.md, hit live 2026-06-15,
HTTP 200, namespace ``http://www.67bricks.com/isrctn``):

  GET https://www.isrctn.com/api/query/format/default?q=condition:<facet>&limit=&offset=
      → <allTrials totalCount="N"><fullTrial><trial ...>...</trial></fullTrial>...

Honest handling (matches the research doc's gaps + Core Value):
  * ISRCTN has NO recruiting-status element (the trialStatus: filter returns 0).
    We COMPUTE status from ``recruitmentStart`` / ``recruitmentEnd`` vs. today and
    map to fetch_ctgov's vocabulary: start ≤ today ≤ end → RECRUITING; today <
    start → NOT_YET_RECRUITING; today > end → COMPLETED; missing dates → "" so the
    matcher routes to ``evaluating`` (never silently dropped).
  * Age: ``ageRange`` ("Neonate") + optional ``lowerAgeLimit`` / ``upperAgeLimit``
    (value+unit) → ctgov-style "N Years"/"N Months" strings where derivable;
    "Neonate" → min "0 Years"; unmappable → None (→ evaluating).
  * ``externalRefs`` (DOI / eudraCTNumber / clinicalTrialsGovNumber / irasNumber /
    secondaryNumbers) are collected into ``secondary_ids`` for cross-registry dedup
    (ACUMEN is ISRCTN61218504 AND in CTIS as ctNumber 2025-520538-49-00).

Usage
-----
    PYTHONUTF8=1 .venv/Scripts/python.exe -m scripts.perception.sources.isrctn
    PYTHONUTF8=1 .venv/Scripts/python.exe -m scripts.perception.sources.isrctn --limit 50
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from typing import Any

import httpx

from scripts.ledger import (
    compute_hash,
    insert_ledger_row,
    known_sources,
    load_env,
    upload_artifact,
)
from scripts.perception.sources import CONDITION_FACETS, USER_AGENT

ISRCTN_QUERY = "https://www.isrctn.com/api/query/format/default"
NS = {"i": "http://www.67bricks.com/isrctn"}
NS_URI = "http://www.67bricks.com/isrctn"

SOURCE_TYPE = "isrctn"
RETRIEVAL_METHOD = "isrctn_query_api"


# ---------------------------------------------------------------------------
# XML helpers (namespace-aware)
# ---------------------------------------------------------------------------
def _find(el: ET.Element | None, path: str) -> ET.Element | None:
    return el.find(path, NS) if el is not None else None


def _text(el: ET.Element | None, path: str) -> str | None:
    node = _find(el, path)
    if node is None or node.text is None:
        return None
    t = node.text.strip()
    return t or None


def _findall(el: ET.Element | None, path: str) -> list[ET.Element]:
    return el.findall(path, NS) if el is not None else []


# ---------------------------------------------------------------------------
# Status computation (ISRCTN has no status field — infer from dates)
# ---------------------------------------------------------------------------
def _parse_iso_date(s: str | None) -> date | None:
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s.strip())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def compute_status(
    recruitment_start: str | None,
    recruitment_end: str | None,
    *,
    today: date | None = None,
) -> str:
    """Map ISRCTN recruitment dates → ctgov status vocabulary.

    start ≤ today ≤ end → RECRUITING; today < start → NOT_YET_RECRUITING;
    today > end → COMPLETED; missing/unparseable → "" (matcher → evaluating).
    Conservative: when only an end date is present and it is in the future we
    still treat it as RECRUITING (over-surface, never drop).
    """
    if today is None:
        today = datetime.now(timezone.utc).date()
    start = _parse_iso_date(recruitment_start)
    end = _parse_iso_date(recruitment_end)
    if start is None and end is None:
        return ""
    if start is not None and today < start:
        return "NOT_YET_RECRUITING"
    if end is not None and today > end:
        return "COMPLETED"
    # start ≤ today (or unknown start) AND today ≤ end (or unknown end, future-ish)
    return "RECRUITING"


# ---------------------------------------------------------------------------
# Age mapping
# ---------------------------------------------------------------------------
_AGE_RANGE_MIN = {
    "neonate": "0 Years",
    "preterm": "0 Years",
    "child": "0 Years",
    "infant": "0 Years",
    "all": None,
    "mixed": None,
    "adult": "18 Years",
    "senior": "65 Years",
}


def _age_limit_to_ctgov(node: ET.Element | None) -> str | None:
    """An ISRCTN <lowerAgeLimit>/<upperAgeLimit> → "N Years"/"N Months" string.

    These elements (when present) carry a numeric value + a unit. Returns None
    when absent or unparseable so the matcher's age-unknown rule applies.
    """
    if node is None:
        return None
    val = (node.text or "").strip()
    unit = (node.get("unit") or node.get("type") or "").strip().lower()
    m = re.search(r"(\d+(?:\.\d+)?)", val)
    if not m:
        return None
    n = m.group(1).rstrip("0").rstrip(".") if "." in m.group(1) else m.group(1)
    if "year" in unit or unit in ("y", "yr", "yrs"):
        return f"{n} Years"
    if "month" in unit or unit in ("m", "mo"):
        return f"{n} Months"
    if "week" in unit or unit in ("w", "wk"):
        return f"{n} Weeks"
    if "day" in unit or unit in ("d",):
        return f"{n} Days"
    # no unit → assume years (ISRCTN's common case)
    return f"{n} Years"


def map_age(part: ET.Element | None) -> tuple[str | None, str | None]:
    """Derive (min_age, max_age) ctgov-style strings from ISRCTN participants.

    Prefers explicit lowerAgeLimit/upperAgeLimit; falls back to the coarse
    ``ageRange`` category ("Neonate" → min "0 Years"). Unmappable → (None, None)
    so the matcher routes to ``evaluating`` (never silently excluded).
    """
    lower = _age_limit_to_ctgov(_find(part, "i:lowerAgeLimit"))
    upper = _age_limit_to_ctgov(_find(part, "i:upperAgeLimit"))
    if lower is None:
        ar = (_text(part, "i:ageRange") or "").strip().lower()
        for key, val in _AGE_RANGE_MIN.items():
            if key in ar:
                lower = val
                break
    return lower, upper


# ---------------------------------------------------------------------------
# Secondary-id collection (dedup)
# ---------------------------------------------------------------------------
def _collect_secondary_ids(trial: ET.Element) -> list[str]:
    """Gather sibling-registry ids from ISRCTN <externalRefs> for dedup."""
    out: list[str] = []

    def add(val: str | None) -> None:
        if not val:
            return
        s = val.strip()
        if s and s not in out:
            out.append(s)

    refs = _find(trial, "i:externalRefs")
    if refs is not None:
        add(_text(refs, "i:doi"))
        add(_text(refs, "i:eudraCTNumber"))
        add(_text(refs, "i:clinicalTrialsGovNumber"))
        iras = _text(refs, "i:irasNumber")
        if iras:
            add(f"IRAS:{iras}")
        for sn in _findall(_find(refs, "i:secondaryNumbers"), "i:secondaryNumber"):
            num = (sn.text or "").strip()
            ntype = (sn.get("numberType") or "").strip()
            if num:
                add(f"{ntype}:{num}" if ntype else num)
    return out


# ---------------------------------------------------------------------------
# Normalize one <trial> → payload_metadata
# ---------------------------------------------------------------------------
def _phase_to_ctgov(phase_text: str | None) -> list[str]:
    if not phase_text:
        return []
    t = phase_text.lower()
    phases: list[str] = []
    if re.search(r"phase\s*iv|phase\s*4", t):
        phases.append("PHASE4")
    if re.search(r"phase\s*iii|phase\s*3", t):
        phases.append("PHASE3")
    if re.search(r"phase\s*ii(?!i)|phase\s*2", t):
        phases.append("PHASE2")
    if re.search(r"phase\s*i(?!i|v)|phase\s*1", t):
        phases.append("PHASE1")
    return list(dict.fromkeys(phases))


def normalize(trial: ET.Element) -> tuple[str, dict[str, Any]]:
    """Normalize one ISRCTN <trial> element → (isrctn_number, payload_metadata)."""
    isrctn_id = (_text(trial, "i:isrctn") or "").strip()
    if not isrctn_id:
        return "", {}

    desc = _find(trial, "i:trialDescription")
    design = _find(trial, "i:trialDesign")
    part = _find(trial, "i:participants")
    cond = _find(trial, "i:conditions")
    interv = _find(trial, "i:interventions")

    title = (
        _text(desc, "i:title")
        or _text(desc, "i:scientificTitle")
        or f"ISRCTN{isrctn_id}"
    )
    official_title = _text(desc, "i:scientificTitle") or title
    acronym = _text(desc, "i:acronym")
    if acronym and acronym.lower() not in title.lower():
        title = f"{acronym}: {title}"

    recruitment_start = _text(part, "i:recruitmentStart")
    recruitment_end = _text(part, "i:recruitmentEnd")
    overall_status = compute_status(recruitment_start, recruitment_end)

    min_age, max_age = map_age(part)

    gender = (_text(part, "i:gender") or "").strip()
    sex = None
    if gender:
        gl = gender.lower()
        if gl == "all" or ("female" in gl and "male" in gl):
            sex = "ALL"
        elif "female" in gl:
            sex = "FEMALE"
        elif "male" in gl:
            sex = "MALE"

    # interventions: drugNames / interventionType live under <intervention> child
    # nodes (interventions/intervention/{drugNames,interventionType,...}).
    interventions: list[str] = []
    interv_phase = None
    for iv in _findall(interv, "i:intervention"):
        for tag in ("i:drugNames", "i:interventionType"):
            v = _text(iv, tag)
            if v and v not in interventions:
                interventions.append(v)
        interv_phase = interv_phase or _text(iv, "i:phase")
    interventions = interventions[:5]

    # locations: trialCentres carry facility names (richer than CTIS); fall back
    # to recruitmentCountries.
    locations_sample: list[str] = []
    centres = _find(part, "i:trialCentres")
    for tc in _findall(centres, "i:trialCentre"):
        name = (_text(tc, "i:name") or "").strip()
        country = (_text(tc, "i:country") or "").strip()
        if name or country:
            locations_sample.append(f"{name} ({country})")
    if not locations_sample:
        rc = _find(part, "i:recruitmentCountries")
        for c in _findall(rc, "i:country"):
            cn = (c.text or "").strip()
            if cn:
                locations_sample.append(f"({cn})")
    locations_sample = locations_sample[:10]

    phases = _phase_to_ctgov(interv_phase or _text(design, "i:phase"))
    study_type = _text(design, "i:primaryStudyDesign")

    # conditions (EN) for provenance / matcher conditions field. The texts live
    # under conditions/condition/{description,diseaseClass1,diseaseClass2}.
    conditions: list[str] = []
    for cnode in _findall(cond, "i:condition"):
        for tag in ("i:description", "i:diseaseClass1", "i:diseaseClass2"):
            v = _text(cnode, tag)
            if v and v not in conditions:
                conditions.append(v)

    # eligibility free text
    inc = _text(part, "i:inclusion")
    exc = _text(part, "i:exclusion")
    elig_parts = []
    if inc:
        elig_parts.append("Inclusion: " + inc)
    if exc:
        elig_parts.append("Exclusion: " + exc)
    eligibility = "\n".join(elig_parts).strip() or None

    brief_summary = _text(desc, "i:plainEnglishSummary") or _text(
        desc, "i:studyHypothesis"
    )

    secondary_ids = _collect_secondary_ids(trial)

    last_updated = None
    lu = trial.get("lastUpdated")
    if lu:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", lu)
        if m:
            last_updated = m.group(1)

    meta: dict[str, Any] = {
        "nct_id": f"ISRCTN{isrctn_id}",  # native id home (no NCT)
        "title": title,
        "official_title": official_title,
        "overall_status": overall_status,
        "start_date": _parse_iso_date(recruitment_start).isoformat()
        if _parse_iso_date(recruitment_start)
        else None,
        "completion_date": _parse_iso_date(recruitment_end).isoformat()
        if _parse_iso_date(recruitment_end)
        else None,
        "phases": phases,
        "study_type": study_type or "INTERVENTIONAL",
        "interventions": interventions,
        "min_age": min_age,
        "max_age": max_age,
        "sex": sex,
        "healthy_volunteers": None,
        "locations_sample": locations_sample,
        "has_full_text": True,
        # Phase E registry fields
        "registry": SOURCE_TYPE,
        "registry_id": isrctn_id,
        "secondary_ids": secondary_ids,
        # ISRCTN-specific provenance
        "isrctn_brief_summary": brief_summary,
        "isrctn_eligibility_criteria": eligibility,
        "isrctn_conditions": conditions,
        "isrctn_last_updated": last_updated,
    }
    return isrctn_id, meta


def _trial_to_xml_bytes(full_trial: ET.Element) -> bytes:
    """Serialize a single <fullTrial> element back to bytes for R2 storage."""
    ET.register_namespace("", NS_URI)
    return ET.tostring(full_trial, encoding="utf-8")


# ---------------------------------------------------------------------------
# Run loop
# ---------------------------------------------------------------------------
def run(
    conditions: tuple[str, ...] | None = None,
    *,
    limit: int = 100,
    max_offset: int = 300,
    mode: str = "positive",
) -> dict[str, int]:
    """Fetch ISRCTN trials for Aleksandra's condition facets → R2 + evidence_ledger.

    Returns a counts dict (same shape as fetch_ctgov.run).
    """
    if conditions is None:
        conditions = CONDITION_FACETS
    load_env()

    counts = {
        "queries_run": 0,
        "studies_found": 0,
        "new_studies": 0,
        "ledger_inserted": 0,
        "duplicates": 0,
        "errors": 0,
    }

    headers = {"User-Agent": USER_AGENT, "Accept": "application/xml"}
    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for condition in conditions:
            counts["queries_run"] += 1
            new_for_q = 0
            found_for_q = 0
            try:
                offset = 0
                while offset <= max_offset:
                    r = client.get(
                        ISRCTN_QUERY,
                        params={
                            "q": f"condition:{condition}",
                            "limit": str(limit),
                            "offset": str(offset),
                        },
                        timeout=60,
                    )
                    r.raise_for_status()
                    root = ET.fromstring(r.content)
                    full_trials = root.findall("i:fullTrial", NS)
                    if not full_trials:
                        break
                    found_for_q += len(full_trials)
                    counts["studies_found"] += len(full_trials)

                    # batch dedup (fail-open) on this page's ISRCTN numbers
                    page_ids: list[str] = []
                    parsed: list[tuple[ET.Element, str, dict[str, Any]]] = []
                    for ftr in full_trials:
                        trial = ftr.find("i:trial", NS)
                        if trial is None:
                            continue
                        sid, meta = normalize(trial)
                        if not sid:
                            continue
                        page_ids.append(sid)
                        parsed.append((ftr, sid, meta))
                    already = known_sources(page_ids, SOURCE_TYPE, mode=mode)

                    for ftr, sid, meta in parsed:
                        if sid in already:
                            counts["duplicates"] += 1
                            continue
                        try:
                            payload = _trial_to_xml_bytes(ftr)
                            h = compute_hash(payload)
                            artifact_url = upload_artifact(
                                SOURCE_TYPE, sid, payload, "xml", mode=mode
                            )
                            ok = insert_ledger_row(
                                source_id=sid,
                                source_type=SOURCE_TYPE,
                                retrieval_method=RETRIEVAL_METHOD,
                                content_hash=h,
                                raw_artifact_url=artifact_url,
                                mode=mode,
                                query=f"condition:{condition}",
                                payload_metadata=meta,
                            )
                            if ok:
                                counts["new_studies"] += 1
                                counts["ledger_inserted"] += 1
                                new_for_q += 1
                            else:
                                counts["duplicates"] += 1
                        except Exception as e:  # noqa: BLE001
                            print(f"  [err] ISRCTN ledger write failed {sid}: {e}")
                            counts["errors"] += 1

                    if len(full_trials) < limit:
                        break
                    offset += limit
                    time.sleep(0.5)  # be polite between pages
            except Exception as e:  # noqa: BLE001 — one facet failure ≠ source crash
                print(
                    f"  [err] ISRCTN query failed for {condition!r}: "
                    f"{type(e).__name__}: {e}"
                )
                counts["errors"] += 1
            print(
                f"  facet: {condition[:40]:<40}  found={found_for_q:3d}  new={new_for_q}"
            )
            time.sleep(0.5)  # be polite between facets

    return counts


def _print_counts(counts: dict[str, int]) -> None:
    print()
    print("UK ISRCTN fetch summary:")
    for k, v in counts.items():
        print(f"  {k:18} {v}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=100, help="trials per query page")
    ap.add_argument(
        "--max-offset", type=int, default=300, help="max offset to page through"
    )
    ap.add_argument(
        "--conditions", type=int, default=0, help="run only first N condition facets"
    )
    ap.add_argument("--mode", choices=("positive", "negative"), default="positive")
    args = ap.parse_args()

    facets = (
        CONDITION_FACETS
        if args.conditions == 0
        else CONDITION_FACETS[: args.conditions]
    )
    counts = run(
        conditions=facets, limit=args.limit, max_offset=args.max_offset, mode=args.mode
    )
    _print_counts(counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
