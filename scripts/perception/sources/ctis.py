"""ctis.py — EU CTIS clinical-trial fetcher (source_type="ctis").

Pulls trials from the EU Clinical Trials Information System (CTIS) public API for
Aleksandra's condition facets, normalizes EACH trial into the SAME
``payload_metadata`` shape + vocabulary as ``scripts/fetch_ctgov.py``, uploads the
FULL raw retrieve JSON to R2, and writes one ``evidence_ledger`` row per trial
(source_type="ctis", source_id=ctNumber).

Verified two-call pattern (docs/CLINICAL_TRIALS_SOURCES_RESEARCH.md, hit live
2026-06-15, both HTTP 200):

  1. POST https://euclinicaltrials.eu/ctis-public-api/search   (paginated)
       body: {"pagination":{"page":N,"size":S},
              "sort":{"property":"decisionDate","direction":"DESC"},
              "searchCriteria":{"medicalCondition": <facet>}}
       → {"pagination":{"totalPages","nextPage",...}, "data":[{ctNumber,...}]}
  2. GET  https://euclinicaltrials.eu/ctis-public-api/retrieve/{ctNumber}
       → full nested authorizedApplication.authorizedPartI.{...} detail.

Honest handling (matches the research doc's gaps + Core Value "over-surface,
never drop"):
  * CTIS ``ctStatus`` is the AUTHORISATION lifecycle, NOT site-level recruiting.
    We map conservatively: "Authorised"/"Ongoing*"/code 2/3 → RECRUITING-equivalent
    (so an authorised trial is surfaced for review); clearly-closed
    ("Ended"/"Expired"/"Revoked"/"Suspended") → a closed ctgov status; anything
    unmappable → "" so the matcher routes it to ``evaluating`` (never dropped).
  * CTIS age is the numeric ``ageRangeCategoryCode`` whose meaning is UNVERIFIED.
    Per the research doc we emit ``min_age=max_age=None`` so the matcher's
    age-unknown rule routes the trial to ``evaluating`` (never silently excluded).
  * ``secondaryIdentifyingNumbers`` (isrctnNumber / additionalRegistries) +
    ``trialDetails.references`` / ``associatedClinicalTrials`` are collected into
    ``secondary_ids`` so cross-registry dedup (ACUMEN is in CTIS AND ISRCTN) works.

Usage
-----
    PYTHONUTF8=1 .venv/Scripts/python.exe -m scripts.perception.sources.ctis
    PYTHONUTF8=1 .venv/Scripts/python.exe -m scripts.perception.sources.ctis --size 5
    PYTHONUTF8=1 .venv/Scripts/python.exe -m scripts.perception.sources.ctis --max-pages 1
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
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

CTIS_SEARCH = "https://euclinicaltrials.eu/ctis-public-api/search"
CTIS_RETRIEVE = "https://euclinicaltrials.eu/ctis-public-api/retrieve/{ct}"

SOURCE_TYPE = "ctis"
RETRIEVAL_METHOD = "ctis_public_api"

# CTIS status → ctgov vocabulary. CONSERVATIVE: an authorised/ongoing trial is
# surfaced as recruiting-equivalent (the family/clinician confirms); only clearly
# terminal states map to a closed status; everything else → "" (→ evaluating).
# Keys are lower-cased ctStatus strings (retrieve returns "Authorised") and the
# numeric ctPublicStatusCode / ctStatus codes the search endpoint returns.
_OPEN_TERMS = {
    "authorised",
    "authorized",
    "ongoing",
    "ongoing, recruiting",
    "recruiting",
    "under evaluation",
    "active",
}
_CLOSED_TERMS = {
    "ended",
    "expired",
    "revoked",
    "suspended",
    "withdrawn",
    "terminated",
    "not authorised",
    "not authorized",
    "refused",
}
# Numeric ctStatus / ctPublicStatusCode codes seen live (2 = Authorised). Codes
# are coarse and partly UNVERIFIED, so only the well-understood open ones are
# mapped to RECRUITING; unknown codes fall through to "" (→ evaluating).
_OPEN_CODES = {"2", "3"}
_CLOSED_CODES = {"6", "7", "8", "9"}


def body(condition: str, page: int = 1, size: int = 20) -> dict[str, Any]:
    """The verified CTIS search POST body for one condition facet + page."""
    return {
        "pagination": {"page": page, "size": size},
        "sort": {"property": "decisionDate", "direction": "DESC"},
        "searchCriteria": {"medicalCondition": condition},
    }


def map_status(ct_status: Any, public_code: Any = None) -> str:
    """Map a CTIS status (string or numeric code) → ctgov vocabulary.

    Returns one of OPEN_STATUSES-compatible strings ("RECRUITING"), a closed
    status ("COMPLETED"), or "" when unmappable (the matcher then routes the
    trial to ``evaluating`` — never silently dropped). Conservative by design:
    authorised/ongoing → RECRUITING so an authorised-but-not-yet-recruiting trial
    is over-surfaced for review rather than missed (Core Value).
    """
    for raw in (ct_status, public_code):
        if raw is None:
            continue
        s = str(raw).strip().lower()
        if not s:
            continue
        if s in _OPEN_TERMS or s in _OPEN_CODES:
            return "RECRUITING"
        if s in _CLOSED_TERMS or s in _CLOSED_CODES:
            return "COMPLETED"
    return ""  # unmappable → matcher routes to evaluating


def _collect_secondary_ids(detail: dict[str, Any]) -> list[str]:
    """Gather sibling-registry ids from a CTIS retrieve JSON for dedup.

    Sources (all verified live on the ACUMEN trial): clinicalTrialIdentifiers.
    secondaryIdentifyingNumbers.isrctnNumber + .additionalRegistries, the
    eudraCt code, and trialDetails.references / associatedClinicalTrials. Returns
    a de-duplicated, order-stable list of normalized id strings.
    """
    out: list[str] = []

    def add(val: Any, prefix: str = "") -> None:
        if val is None:
            return
        s = str(val).strip()
        if not s:
            return
        s = f"{prefix}{s}" if prefix and not s.upper().startswith(prefix.upper()) else s
        if s not in out:
            out.append(s)

    aa = detail.get("authorizedApplication") or {}
    p1 = aa.get("authorizedPartI") or {}
    td = p1.get("trialDetails") or {}

    # eudraCt
    eud = aa.get("eudraCt")
    if isinstance(eud, dict):
        add(eud.get("eudraCtCode") or eud.get("code") or eud.get("number"))
    elif isinstance(eud, str):
        add(eud)

    cti = td.get("clinicalTrialIdentifiers") or {}
    sin = cti.get("secondaryIdentifyingNumbers") or {}
    if isinstance(sin, dict):
        isrctn = sin.get("isrctnNumber") or {}
        if isinstance(isrctn, dict):
            add(isrctn.get("number"))
        for ar in sin.get("additionalRegistries") or []:
            if isinstance(ar, dict):
                reg = (ar.get("otherRegistryName") or "").strip()
                num = (ar.get("number") or "").strip()
                if num:
                    add(f"{reg}:{num}" if reg else num)

    # references / associatedClinicalTrials (empty on ACUMEN but present in schema)
    for ref in td.get("references") or []:
        if isinstance(ref, dict):
            add(ref.get("number") or ref.get("identifier") or ref.get("reference"))
        elif isinstance(ref, str):
            add(ref)
    for act in td.get("associatedClinicalTrials") or []:
        if isinstance(act, dict):
            add(act.get("ctNumber") or act.get("number") or act.get("identifier"))
        elif isinstance(act, str):
            add(act)

    return out


def _phase_to_ctgov(trial_phase: str | None) -> list[str]:
    """Map a CTIS ``trialPhase`` free-text label → ctgov phase tokens.

    e.g. "Human Pharmacology (Phase I)- First administration to humans" → ["PHASE1"].
    Unmappable → []. Mirrors ctgov's ``phases`` list shape.
    """
    if not trial_phase:
        return []
    t = trial_phase.lower()
    phases: list[str] = []
    if re.search(r"phase\s*iv|phase\s*4", t):
        phases.append("PHASE4")
    if re.search(r"phase\s*iii|phase\s*3", t):
        phases.append("PHASE3")
    if re.search(r"phase\s*ii(?!i)|phase\s*2", t):
        phases.append("PHASE2")
    if re.search(r"phase\s*i(?!i|v)|phase\s*1", t):
        phases.append("PHASE1")
    return list(dict.fromkeys(phases))  # stable de-dup


def _sex_from(detail: dict[str, Any], search_gender: str | None) -> str | None:
    """Derive a ctgov-style sex string ("ALL"/"FEMALE"/"MALE") from CTIS."""
    is_f = is_m = None
    aa = detail.get("authorizedApplication") or {}
    p1 = aa.get("authorizedPartI") or {}
    td = p1.get("trialDetails") or {}
    ti = td.get("trialInformation") or {}
    pop = ti.get("populationOfTrialSubjects") or {}
    if isinstance(pop, dict):
        is_f = pop.get("isFemaleSubjects")
        is_m = pop.get("isMaleSubjects")
    if is_f and is_m:
        return "ALL"
    if is_f:
        return "FEMALE"
    if is_m:
        return "MALE"
    # fall back to the search-level "Female, Male" string
    if search_gender:
        g = search_gender.lower()
        has_f = "female" in g
        has_m = "male" in g and not g.replace("female", "").strip() == ""
        if "female" in g and re.search(r"\bmale\b", g.replace("female", "")):
            return "ALL"
        if has_f:
            return "FEMALE"
        if has_m:
            return "MALE"
    return None


def normalize(
    search_row: dict[str, Any], detail: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    """Normalize a CTIS (search_row, retrieve detail) pair → (ctNumber, metadata).

    Produces the SAME payload_metadata shape fetch_ctgov writes so the matcher's
    map_and_evaluate works unchanged, PLUS the Phase E registry fields
    (registry / registry_id / secondary_ids).
    """
    ct_number = str(search_row.get("ctNumber") or detail.get("ctNumber") or "").strip()
    if not ct_number:
        return "", {}

    aa = detail.get("authorizedApplication") or {}
    p1 = aa.get("authorizedPartI") or {}
    td = p1.get("trialDetails") or {}
    cti = td.get("clinicalTrialIdentifiers") or {}
    ti = td.get("trialInformation") or {}

    # --- title: prefer the clean public title; fall back to full / search title ---
    title = (
        (cti.get("publicTitle") or "").strip()
        or (search_row.get("ctTitle") or "").strip()
        or (cti.get("fullTitle") or "").strip()
        or ct_number
    )
    official_title = (
        (cti.get("fullTitle") or "").strip()
        or (search_row.get("ctTitle") or "").strip()
        or title
    )

    # --- status: conservative authorisation-lifecycle → ctgov vocab ---
    overall_status = map_status(
        detail.get("ctStatus") or search_row.get("ctStatus"),
        detail.get("ctPublicStatusCode") or search_row.get("trialRegion"),
    )

    # --- interventions: product names + active substances ---
    interventions: list[str] = []
    for prod in p1.get("products") or []:
        if not isinstance(prod, dict):
            continue
        name = (prod.get("productName") or "").strip()
        if name and name not in interventions:
            interventions.append(name)
        subs = prod.get("jsonActiveSubstanceNames")
        if isinstance(subs, str) and subs.strip() and subs.strip() not in interventions:
            interventions.append(subs.strip())
        elif isinstance(subs, list):
            for s in subs:
                s = str(s).strip()
                if s and s not in interventions:
                    interventions.append(s)
    if not interventions and search_row.get("product"):
        interventions = [str(search_row["product"]).strip()]
    interventions = interventions[:5]

    # --- locations: CTIS exposes COUNTRIES, not facilities ---
    locations_sample: list[str] = []
    seen_countries: set[str] = set()
    for rc in p1.get("rowCountriesInfo") or []:
        if not isinstance(rc, dict):
            continue
        cname = (rc.get("name") or "").strip()
        if cname and cname.lower() not in seen_countries:
            seen_countries.add(cname.lower())
            # "(Country)" so location_flags() (which reads the trailing paren) works.
            locations_sample.append(f"({cname})")
    if not locations_sample:
        # search-level trialCountries like ["Ireland:2"] → "(Ireland)"
        for tc in search_row.get("trialCountries") or []:
            cname = str(tc).split(":")[0].strip()
            if cname and cname.lower() not in seen_countries:
                seen_countries.add(cname.lower())
                locations_sample.append(f"({cname})")

    # --- age: ageRangeCategoryCode meaning UNVERIFIED → None → matcher.evaluating ---
    # (research doc gap A2: never silently exclude on an un-decoded age code.)
    min_age = None
    max_age = None

    sex = _sex_from(detail, search_row.get("gender"))

    secondary_ids = _collect_secondary_ids(detail)

    meta: dict[str, Any] = {
        # ctgov-compatible keys (matcher reads these unchanged)
        "nct_id": ct_number,  # native id home (no NCT for CTIS)
        "title": title,
        "official_title": official_title,
        "overall_status": overall_status,
        "start_date": _ctis_date(detail.get("decisionDate"))
        or _ctis_date(search_row.get("decisionDateOverall")),
        "completion_date": None,
        "phases": _phase_to_ctgov(search_row.get("trialPhase")),
        "study_type": "INTERVENTIONAL",  # CTIS = interventional medicinal products
        "interventions": interventions,
        "min_age": min_age,
        "max_age": max_age,
        "sex": sex,
        "healthy_volunteers": None,
        "locations_sample": locations_sample,
        "has_full_text": True,
        # Phase E registry fields
        "registry": SOURCE_TYPE,
        "registry_id": ct_number,
        "secondary_ids": secondary_ids,
        # CTIS-specific provenance (informational)
        "ctis_eligibility_criteria": _ctis_eligibility(ti),
        "ctis_objective": _ctis_objective(ti),
        "ctis_conditions": _ctis_conditions(p1),
        "ctis_sponsor": _ctis_sponsor(p1),
        "ctis_age_code": _ctis_age_code(ti),
    }
    return ct_number, meta


def _ctis_date(val: Any) -> str | None:
    """Best-effort ISO date out of a CTIS date value (ISO datetime or dd/mm/yyyy)."""
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None
    # ISO datetime "2025-09-12T16:42:41.838" → date part
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    if m:
        return m.group(1)
    # dd/mm/yyyy → yyyy-mm-dd
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def _ctis_eligibility(ti: dict[str, Any]) -> str | None:
    ec = ti.get("eligibilityCriteria") if isinstance(ti, dict) else None
    if not isinstance(ec, dict):
        return None
    inc = [
        (c.get("principalInclusionCriteria") or "").strip()
        for c in ec.get("principalInclusionCriteria") or []
        if isinstance(c, dict)
    ]
    exc = [
        (c.get("principalExclusionCriteria") or "").strip()
        for c in ec.get("principalExclusionCriteria") or []
        if isinstance(c, dict)
    ]
    parts = []
    if inc:
        parts.append("Inclusion: " + "; ".join(p for p in inc if p))
    if exc:
        parts.append("Exclusion: " + "; ".join(p for p in exc if p))
    text = "\n".join(parts).strip()
    return text or None


def _ctis_objective(ti: dict[str, Any]) -> str | None:
    obj = ti.get("trialObjective") if isinstance(ti, dict) else None
    if isinstance(obj, dict):
        m = (obj.get("mainObjective") or "").strip()
        return m or None
    return None


def _ctis_conditions(p1: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for mc in p1.get("medicalConditions") or []:
        if isinstance(mc, dict):
            c = (mc.get("medicalCondition") or "").strip()
            if c and c not in out:
                out.append(c)
    return out


def _ctis_sponsor(p1: dict[str, Any]) -> str | None:
    for sp in p1.get("sponsors") or []:
        if not isinstance(sp, dict):
            continue
        for pc in sp.get("publicContacts") or []:
            org = (pc.get("organisation") or {}) if isinstance(pc, dict) else {}
            name = (org.get("name") or "").strip()
            if name:
                return name
    return None


def _ctis_age_code(ti: dict[str, Any]) -> str | None:
    pop = ti.get("populationOfTrialSubjects") if isinstance(ti, dict) else None
    if isinstance(pop, dict):
        for ar in pop.get("ageRanges") or []:
            if isinstance(ar, dict) and ar.get("ageRangeCategoryCode"):
                return str(ar["ageRangeCategoryCode"])
    return None


def _retrieve(client: httpx.Client, ct_number: str) -> dict[str, Any] | None:
    """GET the full CTIS retrieve JSON for one ctNumber. None on any failure."""
    try:
        r = client.get(CTIS_RETRIEVE.format(ct=ct_number), timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:  # noqa: BLE001 — one bad retrieve must not kill the source
        print(f"  [err] CTIS retrieve failed for {ct_number}: {type(e).__name__}: {e}")
        return None


def run(
    conditions: tuple[str, ...] | None = None,
    *,
    size: int = 20,
    max_pages: int = 5,
    mode: str = "positive",
) -> dict[str, int]:
    """Fetch CTIS trials for Aleksandra's condition facets → R2 + evidence_ledger.

    Returns a counts dict (same shape as fetch_ctgov.run) so perception_tick can
    aggregate it uniformly.
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

    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    with httpx.Client(headers=headers) as client:
        for condition in conditions:
            counts["queries_run"] += 1
            new_for_q = 0
            found_for_q = 0
            try:
                page = 1
                while page <= max_pages:
                    r = client.post(
                        CTIS_SEARCH,
                        json=body(condition, page=page, size=size),
                        timeout=40,
                    )
                    r.raise_for_status()
                    data = r.json()
                    rows = data.get("data") or []
                    found_for_q += len(rows)
                    counts["studies_found"] += len(rows)

                    # batch dedup (fail-open) on this page's ctNumbers
                    ct_ids = [
                        str(x.get("ctNumber")).strip()
                        for x in rows
                        if x.get("ctNumber")
                    ]
                    already = known_sources(ct_ids, SOURCE_TYPE, mode=mode)

                    for srow in rows:
                        ct_number = str(srow.get("ctNumber") or "").strip()
                        if not ct_number:
                            continue
                        if ct_number in already:
                            counts["duplicates"] += 1
                            continue
                        detail = _retrieve(client, ct_number)
                        time.sleep(0.5)  # be polite between retrieve calls
                        if detail is None:
                            counts["errors"] += 1
                            continue
                        try:
                            sid, meta = normalize(srow, detail)
                            if not sid:
                                continue
                            payload = json.dumps(
                                detail, sort_keys=True, indent=2, ensure_ascii=False
                            ).encode("utf-8")
                            h = compute_hash(payload)
                            artifact_url = upload_artifact(
                                SOURCE_TYPE, sid, payload, "json", mode=mode
                            )
                            ok = insert_ledger_row(
                                source_id=sid,
                                source_type=SOURCE_TYPE,
                                retrieval_method=RETRIEVAL_METHOD,
                                content_hash=h,
                                raw_artifact_url=artifact_url,
                                mode=mode,
                                query=f"medicalCondition={condition}",
                                payload_metadata=meta,
                            )
                            if ok:
                                counts["new_studies"] += 1
                                counts["ledger_inserted"] += 1
                                new_for_q += 1
                            else:
                                counts["duplicates"] += 1
                        except Exception as e:  # noqa: BLE001
                            print(f"  [err] CTIS ledger write failed {ct_number}: {e}")
                            counts["errors"] += 1

                    pg = data.get("pagination") or {}
                    if not pg.get("nextPage"):
                        break
                    page += 1
                    time.sleep(0.5)  # be polite between pages
            except Exception as e:  # noqa: BLE001 — one facet failure ≠ source crash
                print(
                    f"  [err] CTIS search failed for {condition!r}: {type(e).__name__}: {e}"
                )
                counts["errors"] += 1
            print(
                f"  facet: {condition[:40]:<40}  found={found_for_q:3d}  new={new_for_q}"
            )
            time.sleep(0.5)  # be polite between facets

    return counts


def _print_counts(counts: dict[str, int]) -> None:
    print()
    print("EU CTIS fetch summary:")
    for k, v in counts.items():
        print(f"  {k:18} {v}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--size", type=int, default=20, help="trials per search page")
    ap.add_argument(
        "--max-pages", type=int, default=5, help="max search pages per facet"
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
        conditions=facets, size=args.size, max_pages=args.max_pages, mode=args.mode
    )
    _print_counts(counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
