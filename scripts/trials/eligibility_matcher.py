"""
eligibility_matcher.py — Phase A wave 1: ctgov → clinical_trials sync + matcher.

Reads every ClinicalTrials.gov row already captured in evidence_ledger
(source_type='ctgov', payload_metadata JSONB) and maps each into a
clinical_trials record with a *computed eligibility decision* for
Aleksandra. The result is UPSERTed into clinical_trials (idempotent on
nct_id) so re-running never duplicates.

Core Value alignment ("never miss a lead"): the decision is deliberately
conservative. A trial is only hidden (`ineligible`) on a CLEAR
disqualifier — closed status, or an age range Aleksandra clearly falls
outside of. Any ambiguity (unparseable age criteria) routes to
`evaluating` (needs-review), never silent removal. Location is purely
informational (D2) and never disqualifies on its own.

Phase B wave 1 adds, on top of the Phase A sync:
  * New-eligible detection (B2): diff each computed status against the
    prior clinical_trials row; a trial that is *newly* `identified`
    (absent before, or previously not `identified`) is a fresh lead.
  * Status monitoring (B4): if a known trial's `overall_status` changed
    since last sync, flag the upserted row (`status_changed = true`) and
    record the transition. A previously-`identified` trial that is now
    `ineligible` (e.g. became non-recruiting) is a "no longer open" lead.
  * Telegram alerts: `--notify` sends a PHI-free, family-friendly Georgian
    ping when there is ≥1 new lead (or ≥1 prior lead now closed);
    `--notify-dry` prints the would-be message without sending. When there
    is nothing new, NOTHING is sent (no spam).

Phase C wave 1 adds FULL data + bilingual translation (mirrors how papers do it):
  * Full ctgov detail from R2 (C2): fetch_ctgov.py already uploaded the FULL
    study JSON to R2; its `raw_artifact_url` (s3://bucket/ctgov/<nct>.json) is
    on the evidence_ledger row. We GET that object and extract the real
    brief_summary, detailed_description, full eligibility_criteria text,
    conditions list, ALL locations, and PI / coordinator contacts + dates. On
    ANY R2 / parse failure we fall back to the thin payload_metadata projection
    (Phase A behaviour) — the matcher never crashes on a missing artifact.
  * Bilingual fields (C2): for displayed trials (status in identified /
    evaluating) the family-facing fields (title, brief_summary,
    detailed_description, eligibility_criteria) are stored as JSONB {en, ka}
    via build_bilingual(en) (the EXACT helper papers use — budget-gated,
    sanitizes ka, en-only fallback). Ineligible trials are stored en-only
    ({"en": text, "ka": ""}) to avoid translation cost. conditions stay EN
    (short medical terms; stored as a JSONB array).
  * Self-healing + cost-stable (C2): build_bilingual is only called for a field
    when its ka is currently EMPTY/missing in the existing row. If a good ka is
    already present, it is reused (NO re-translation), so the 6h tick converges
    translations over time without re-spending. build_bilingual is budget-gated;
    on BudgetExceeded it falls back to en-only and the next tick retries.

Usage
-----
    .venv/Scripts/python.exe -m scripts.trials.eligibility_matcher --self-test
    .venv/Scripts/python.exe -m scripts.trials.eligibility_matcher --dry-run
    .venv/Scripts/python.exe -m scripts.trials.eligibility_matcher --limit 10
    .venv/Scripts/python.exe -m scripts.trials.eligibility_matcher --notify-dry
    .venv/Scripts/python.exe -m scripts.trials.eligibility_matcher --notify
    .venv/Scripts/python.exe -m scripts.trials.eligibility_matcher          # live seed

Phase C: requires migration 028 applied first (the family-facing columns must be
JSONB before the matcher PATCHes {en, ka} into them). Set PYTHONUTF8=1 on Windows
so Mkhedruli prints. A backfill run needs no --notify.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import date, datetime, timezone
from typing import Any

import httpx

from scripts.extraction.gemini_translator import has_georgian, is_messy
from scripts.extraction.translate import build_bilingual
from scripts.ledger import (
    _get_r2_client,
    _supabase_creds,
    _supabase_headers,
    load_env,
)

# Family-facing trials page (public viewer). Surfaced in Telegram alerts so
# the family can jump straight to the list. No PHI — trials are public data.
VIEWER_TRIALS_URL = (
    "https://viewer-git-main-shakos-projects-82dad3f2.vercel.app/ka/research/trials"
)

# ---------------------------------------------------------------------------
# Patient constants — Aleksandra
# ---------------------------------------------------------------------------
DOB = date(2025, 8, 28)  # 2025-08-28
DAYS_PER_MONTH = 30.4375  # mean Gregorian month (365.25 / 12)

# Recruiting-ish statuses considered "open" for enrollment purposes.
OPEN_STATUSES = {
    "RECRUITING",
    "NOT_YET_RECRUITING",
    "ENROLLING_BY_INVITATION",
    "ACTIVE_NOT_RECRUITING",
}

# Country tokens that count as a US site.
US_COUNTRY_TOKENS = {"united states", "usa", "u.s.", "u.s.a."}


# ---------------------------------------------------------------------------
# Age parsing
# ---------------------------------------------------------------------------
def parse_age_to_months(s: str | None) -> float | None:
    """Parse a ClinicalTrials.gov age string to months.

    Handles "N Years/Year", "N Months/Month", "N Weeks/Week",
    "N Days/Day" (case-insensitive). Empty / "N/A" / None → None (unknown).

      years  → n * 12
      months → n
      weeks  → n * 7 / 30.4375
      days   → n / 30.4375
    """
    if s is None:
        return None
    text = s.strip()
    if not text or text.upper() in {"N/A", "NA", "NONE"}:
        return None

    m = re.search(r"(\d+(?:\.\d+)?)\s*(year|month|week|day)s?", text, re.IGNORECASE)
    if not m:
        return None
    n = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "year":
        return n * 12.0
    if unit == "month":
        return n
    if unit == "week":
        return n * 7.0 / DAYS_PER_MONTH
    if unit == "day":
        return n / DAYS_PER_MONTH
    return None


def aleksandra_age_months(today: date | None = None) -> int:
    """Aleksandra's age in whole months as of `today` (default: now, UTC)."""
    if today is None:
        today = datetime.now(timezone.utc).date()
    days = (today - DOB).days
    return int(days / DAYS_PER_MONTH)


# ---------------------------------------------------------------------------
# Location flags
# ---------------------------------------------------------------------------
def _country_of(location: str) -> str:
    """Best-effort country extraction from a "Facility, Country" / "Facility (Country)"
    sample string. Returns the trailing token, lowercased and stripped."""
    if not location:
        return ""
    # fetch_ctgov writes "facility (country)"; older rows may use "facility, country".
    paren = re.search(r"\(([^)]*)\)\s*$", location)
    if paren:
        return paren.group(1).strip().lower()
    if "," in location:
        return location.rsplit(",", 1)[-1].strip().lower()
    return location.strip().lower()


def location_flags(locations_sample: list[str] | None) -> tuple[bool, bool]:
    """Return (is_us, is_international) from a locations_sample array.

    is_us: any sampled site is in the United States.
    is_international: any sampled site is in a country other than the US.
    """
    is_us = False
    is_international = False
    for loc in locations_sample or []:
        country = _country_of(str(loc))
        if not country:
            continue
        if country in US_COUNTRY_TOKENS:
            is_us = True
        else:
            is_international = True
    return is_us, is_international


# ---------------------------------------------------------------------------
# R2 full-study fetch (Phase C — full ctgov detail)
# ---------------------------------------------------------------------------
def _parse_s3_url(url: str) -> tuple[str, str] | None:
    """Split an ``s3://bucket/key/path`` URL into ``(bucket, key)``.

    Returns None for anything that is not an s3:// URL (e.g. an http URL or an
    empty/None value). fetch_ctgov writes ``s3://<bucket>/ctgov/<nct_id>.json``.
    """
    if not url or not isinstance(url, str):
        return None
    s = url.strip()
    if not s.startswith("s3://"):
        return None
    rest = s[len("s3://") :]
    if "/" not in rest:
        return None
    bucket, key = rest.split("/", 1)
    if not bucket or not key:
        return None
    return bucket, key


def fetch_full_study(raw_artifact_url: str | None) -> dict[str, Any] | None:
    """Fetch + parse the FULL ctgov study JSON from R2.

    `raw_artifact_url` is the evidence_ledger.raw_artifact_url
    (``s3://<bucket>/ctgov/<nct_id>.json``). Returns the parsed study dict, or
    None on ANY failure (not an s3 url, R2 read error, bad JSON). The caller
    treats None as "no full record" and falls back to payload_metadata, so a
    missing / unreadable artifact NEVER crashes the matcher (Core Value: a
    transient R2 blip must not drop a lead).
    """
    parsed = _parse_s3_url(raw_artifact_url or "")
    if not parsed:
        return None
    bucket, key = parsed
    try:
        client = _get_r2_client()
        obj = client.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()
        return json.loads(body)
    except Exception as e:  # noqa: BLE001 — full detail is best-effort
        print(f"  [warn] R2 fetch failed for {key} ({type(e).__name__}: {e})")
        return None


def _normalize_date(d: str | None) -> str | None:
    """Normalize a ctgov date string to a full ``YYYY-MM-DD`` (PostgreSQL DATE).

    ClinicalTrials.gov frequently returns PARTIAL dates — ``YYYY`` or
    ``YYYY-MM`` — which Postgres rejects for a DATE column ("invalid input
    syntax for type date"). We complete them to the first of the period:
      "2028"       -> "2028-01-01"
      "2028-03"    -> "2028-03-01"
      "2028-03-15" -> "2028-03-15"  (unchanged)
    Anything that does not look like a year-prefixed date returns None (so a
    junk value never blocks the whole upsert).
    """
    if not d:
        return None
    s = str(d).strip()
    if re.fullmatch(r"\d{4}", s):
        return f"{s}-01-01"
    if re.fullmatch(r"\d{4}-\d{2}", s):
        return f"{s}-01"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    return None


def _date_of(struct: Any) -> str | None:
    """Pull + normalize the `.date` string out of a ctgov *DateStruct dict."""
    if isinstance(struct, dict):
        return _normalize_date(struct.get("date"))
    return None


def extract_full_fields(study: dict[str, Any]) -> dict[str, Any]:
    """Extract the rich Phase C fields from a FULL ctgov study JSON.

    Mirrors fetch_ctgov._study_to_metadata's module layout
    (protocolSection.*), but pulls the FULL text fields and ALL locations /
    contacts (not the truncated sample the Phase A projection kept).

    Returns a dict of *English* values:
      brief_summary, detailed_description, eligibility_criteria : str | None
      conditions          : list[str]
      locations           : list[{facility, city, state, country, status}]
      locations_sample    : list["facility (country)"]  (for location_flags)
      pi_name, pi_email, coordinator_name, coordinator_email : str | None
      start_date, estimated_completion, last_updated : str | None
    """
    proto = study.get("protocolSection", {}) or {}
    desc = proto.get("descriptionModule", {}) or {}
    elig = proto.get("eligibilityModule", {}) or {}
    cond = proto.get("conditionsModule", {}) or {}
    contacts = proto.get("contactsLocationsModule", {}) or {}
    status = proto.get("statusModule", {}) or {}

    # --- locations: ALL of them, structured ---
    locations: list[dict[str, Any]] = []
    locations_sample: list[str] = []
    for loc in contacts.get("locations", []) or []:
        if not isinstance(loc, dict):
            continue
        facility = (loc.get("facility") or "").strip()
        country = (loc.get("country") or "").strip()
        locations.append(
            {
                "facility": facility or None,
                "city": (loc.get("city") or "").strip() or None,
                "state": (loc.get("state") or "").strip() or None,
                "country": country or None,
                "status": (loc.get("status") or "").strip() or None,
            }
        )
        # location_flags() reads "facility (country)" — keep that shape working.
        locations_sample.append(f"{facility} ({country})")

    # --- contacts: PI (overallOfficials) + coordinator (centralContacts) ---
    pi_name = pi_email = None
    officials = contacts.get("overallOfficials", []) or []
    pi = None
    for off in officials:
        if isinstance(off, dict) and (off.get("role") or "").upper() == (
            "PRINCIPAL_INVESTIGATOR"
        ):
            pi = off
            break
    if pi is None and officials and isinstance(officials[0], dict):
        pi = officials[0]
    if isinstance(pi, dict):
        pi_name = (pi.get("name") or "").strip() or None
        pi_email = (pi.get("email") or "").strip() or None

    coordinator_name = coordinator_email = None
    central = contacts.get("centralContacts", []) or []
    if central and isinstance(central[0], dict):
        coordinator_name = (central[0].get("name") or "").strip() or None
        coordinator_email = (central[0].get("email") or "").strip() or None

    conditions = [str(c).strip() for c in (cond.get("conditions") or []) if c]

    return {
        "brief_summary": (desc.get("briefSummary") or "").strip() or None,
        "detailed_description": (desc.get("detailedDescription") or "").strip() or None,
        "eligibility_criteria": (elig.get("eligibilityCriteria") or "").strip() or None,
        "conditions": conditions,
        "locations": locations,
        "locations_sample": locations_sample,
        "pi_name": pi_name,
        "pi_email": pi_email,
        "coordinator_name": coordinator_name,
        "coordinator_email": coordinator_email,
        "start_date": _date_of(status.get("startDateStruct")),
        "estimated_completion": _date_of(status.get("completionDateStruct")),
        "last_updated": _date_of(status.get("lastUpdatePostDateStruct")),
    }


# ---------------------------------------------------------------------------
# Bilingual {en, ka} field helpers (Phase C — mirrors papers)
# ---------------------------------------------------------------------------
def _ka_of(value: Any) -> str:
    """Best-effort ka string from an existing row's JSONB/text field value.

    Accepts a {en, ka} dict, a JSON-text string of that shape, or a plain
    scalar (returns "" — no ka yet). Used to decide whether a field already has
    a usable ka so we can SKIP re-translation (cost-stable self-healing).
    """
    if isinstance(value, dict):
        ka = value.get("ka")
        return str(ka).strip() if ka else ""
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                d = json.loads(s)
                if isinstance(d, dict):
                    return str(d.get("ka") or "").strip()
            except json.JSONDecodeError:
                return ""
    return ""


def _en_of(value: Any) -> str:
    """Best-effort en string from a {en, ka} dict / JSON-text / plain scalar.

    Used for PHI-free Telegram alerts and logs, which want the plain English
    title rather than the {en, ka} JSONB the row now stores.
    """
    if value is None:
        return ""
    if isinstance(value, dict):
        return str(value.get("en") or "").strip()
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                d = json.loads(s)
                if isinstance(d, dict):
                    return str(d.get("en") or "").strip()
            except json.JSONDecodeError:
                return s
        return s
    return str(value).strip()


def bilingual_field(
    en_text: str | None,
    *,
    translate: bool,
    prior_value: Any = None,
) -> dict[str, str] | None:
    """Build a {en, ka} dict for one family-facing field.

    Parameters
    ----------
    en_text      : the authoritative English text (None → None, preserving the
                   nullable column; "" → {"en": "", "ka": ""}).
    translate    : whether this trial is DISPLAYED (identified/evaluating). When
                   False (ineligible) we store en-only ({"en": text, "ka": ""})
                   to avoid translation cost.
    prior_value  : the existing row's value for this field (JSONB dict / text).
                   If it already carries a good ka AND the en is unchanged, we
                   REUSE that ka (no re-translation) — this makes the 6h tick
                   converge translations over time without re-spending.

    On budget exhaustion / translator failure, build_bilingual() (the helper
    papers use) returns en-only; the next tick retries (self-healing).
    """
    if en_text is None:
        return None
    en = en_text.strip()
    if not en:
        return {"en": "", "ka": ""}

    prior_ka = _ka_of(prior_value)
    # A prior ka is only worth reusing if it is GENUINELY Georgian (Mkhedruli)
    # and clean. Migration 028 mirrors en→ka (English) so the Georgian site is
    # not blank pre-backfill; that mirror must NOT be mistaken for a real
    # translation, or we would store English-as-Georgian and never translate.
    if prior_ka and has_georgian(prior_ka) and not is_messy(prior_ka):
        prior_en = ""
        if isinstance(prior_value, dict):
            prior_en = str(prior_value.get("en") or "").strip()
        # Reuse unless the English source changed (then the ka is stale and is
        # re-translated, but only for displayed trials).
        if not translate or prior_en == en:
            return {"en": en, "ka": prior_ka}

    if not translate:
        return {"en": en, "ka": ""}

    # Translate (budget-gated inside build_bilingual; en-only fallback on failure).
    out = build_bilingual(en)
    if out is None:  # only when en is None, which we already handled
        return {"en": en, "ka": ""}
    return out


# ---------------------------------------------------------------------------
# Mapping + eligibility decision
# ---------------------------------------------------------------------------
def _join_list(value: Any, limit: int | None = None) -> str | None:
    """Join a list into a comma string; pass through plain strings; None → None."""
    if value is None:
        return None
    if isinstance(value, list):
        items = [str(v) for v in value if v]
        if limit is not None:
            items = items[:limit]
        return ", ".join(items) if items else None
    text = str(value).strip()
    return text or None


def map_and_evaluate(
    source_id: str,
    payload: dict[str, Any],
    age_months: int,
    now_iso: str,
    *,
    full: dict[str, Any] | None = None,
    prior_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map one evidence_ledger ctgov row → a clinical_trials record dict with a
    computed eligibility decision.

    Parameters
    ----------
    payload    : the thin evidence_ledger.payload_metadata projection
                 (always present; Phase A fallback source).
    full       : the rich fields extracted from the FULL ctgov study JSON in R2
                 (extract_full_fields output), or None when the artifact could
                 not be read — then we degrade to the `payload` projection.
    prior_row  : the existing clinical_trials row (for self-healing ka reuse and
                 to avoid wiping a good ka with an empty re-translation).

    Family-facing text fields (title, brief_summary, detailed_description,
    eligibility_criteria) are stored as JSONB {en, ka}: translated for displayed
    trials (identified/evaluating), en-only for ineligible ones (cost control).
    """
    payload = payload or {}
    full = full or {}
    prior_row = prior_row or {}

    nct_id = (payload.get("nct_id") or source_id or "").strip()
    title_en = (
        payload.get("title")
        or payload.get("official_title")
        or nct_id
        or "(untitled trial)"
    )
    overall_status = payload.get("overall_status") or None

    phase = _join_list(payload.get("phases"))
    study_type = _join_list(payload.get("study_type"))
    intervention_name = _join_list(payload.get("interventions"), limit=5)

    min_age = payload.get("min_age")
    max_age = payload.get("max_age")
    sex = payload.get("sex")
    hv = payload.get("healthy_volunteers")

    # --- full ctgov detail (R2), with graceful fallback to the projection ---
    # brief_summary: full briefSummary if we have it, else the official title.
    brief_summary_en = (
        full.get("brief_summary") or payload.get("official_title") or None
    )
    detailed_description_en = full.get("detailed_description") or None
    # eligibility_criteria: the FULL free-text criteria from ctgov if available;
    # otherwise the thin synthetic age/sex string (Phase A behaviour).
    eligibility_criteria_en = full.get("eligibility_criteria") or (
        f"Age {min_age or '?'}-{max_age or '?'}; sex={sex or '?'}; "
        f"healthy_volunteers={hv if hv is not None else '?'}"
    )
    conditions = full.get("conditions") or None

    # Locations: prefer the FULL structured list from R2; fall back to the thin
    # locations_sample. location_flags() works off "facility (country)" strings.
    if full.get("locations"):
        locations = full["locations"]
        locations_sample = full.get("locations_sample") or []
    else:
        locations_sample = payload.get("locations_sample") or []
        if not isinstance(locations_sample, list):
            locations_sample = [locations_sample]
        locations = locations_sample

    # --- eligibility computation ---
    status_norm = (overall_status or "").strip().upper()
    status_ok = status_norm in OPEN_STATUSES

    min_m = parse_age_to_months(min_age if isinstance(min_age, str) else None)
    max_m = parse_age_to_months(max_age if isinstance(max_age, str) else None)
    lower = min_m if min_m is not None else 0.0
    upper = max_m if max_m is not None else math.inf
    age_clearly_out = (min_m is not None and age_months < lower) or (
        max_m is not None and age_months > upper
    )
    age_unknown = min_m is None and max_m is None

    is_us, is_international = location_flags(locations_sample)

    issues: list[str] = []

    if not status_ok:
        status = "ineligible"
        issues.append(f"not actively recruiting (status={overall_status or 'unknown'})")
    elif age_clearly_out:
        status = "ineligible"
        issues.append(
            f"age out of range (Aleksandra ~{age_months}mo vs "
            f"{min_age or '?'}-{max_age or '?'})"
        )
    elif age_unknown:
        status = "evaluating"
        issues.append("age criteria could not be parsed — needs review")
    else:
        status = "identified"

    # Location is informational only (D2): never flips the decision, but is
    # recorded so the family/clinician sees travel implications.
    if is_international and not is_us:
        issues.append("international site only (no US location in sample)")
    elif not is_us and not is_international:
        issues.append("no location data available")

    aleksandra_eligible = status == "identified"

    # --- bilingual {en, ka} (C2) ---
    # Displayed trials (identified / evaluating) get a ka translation; ineligible
    # ones are en-only (cost control). Self-healing: bilingual_field reuses a
    # good ka from the prior row when the en is unchanged (no re-translation).
    displayed = status in ("identified", "evaluating")
    title = bilingual_field(
        title_en, translate=displayed, prior_value=prior_row.get("title")
    )
    brief_summary = bilingual_field(
        brief_summary_en,
        translate=displayed,
        prior_value=prior_row.get("brief_summary"),
    )
    detailed_description = bilingual_field(
        detailed_description_en,
        translate=displayed,
        prior_value=prior_row.get("detailed_description"),
    )
    eligibility_criteria = bilingual_field(
        eligibility_criteria_en,
        translate=displayed,
        prior_value=prior_row.get("eligibility_criteria"),
    )

    rec: dict[str, Any] = {
        "nct_id": nct_id,
        "title": title,
        "brief_summary": brief_summary,
        "detailed_description": detailed_description,
        "conditions": conditions,
        "overall_status": overall_status,
        "phase": phase,
        "study_type": study_type,
        "intervention_name": intervention_name,
        "min_age": str(min_age) if min_age is not None else None,
        "max_age": str(max_age) if max_age is not None else None,
        "eligibility_criteria": eligibility_criteria,
        "locations": locations,
        "aleksandra_eligible": aleksandra_eligible,
        "eligibility_issues": issues,
        "aleksandra_status": status,
        "last_checked": now_iso,
        # Full ctgov contacts + dates. ALWAYS present (value or None) so every
        # record in a batch has the SAME key set — PostgREST bulk upsert rejects
        # a batch whose objects have differing keys (PGRST102 "All object keys
        # must match"). R2 is the source of truth for these and is re-read every
        # tick, so writing the fresh value (or NULL when ctgov omitted it) is
        # correct and idempotent — it never loses data the artifact still holds.
        "pi_name": full.get("pi_name"),
        "pi_email": full.get("pi_email"),
        "coordinator_name": full.get("coordinator_name"),
        "coordinator_email": full.get("coordinator_email"),
        "start_date": full.get("start_date"),
        "estimated_completion": full.get("estimated_completion"),
        "last_updated": full.get("last_updated"),
        # carry derived flags for the summary printer (NOT a DB column)
        "_is_us": is_us,
        "_is_international": is_international,
    }

    return rec


# ---------------------------------------------------------------------------
# Supabase I/O
# ---------------------------------------------------------------------------
def fetch_ctgov_rows(limit: int = 1000) -> list[dict[str, Any]]:
    """Read all evidence_ledger ctgov rows.

    Selects ``raw_artifact_url`` too (Phase C) so the matcher can fetch the FULL
    study JSON from R2 for each trial.
    """
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/evidence_ledger",
        params={
            "source_type": "eq.ctgov",
            "select": "source_id,payload_metadata,raw_artifact_url",
            "limit": str(limit),
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(
            f"fetch_ctgov_rows failed: HTTP {r.status_code}: {r.text[:300]}"
        )
    return r.json()


def fetch_prior_rows() -> dict[str, dict[str, Any]]:
    """Read existing clinical_trials rows' bilingual fields for self-healing.

    Returns ``{nct_id: {title, brief_summary, detailed_description,
    eligibility_criteria}}`` so bilingual_field() can REUSE a good ka without
    re-translating (cost-stable convergence over the 6h tick). Fails SOFT: on
    any error returns {} (every field is then treated as having no prior ka, so
    translation simply runs — never a crash, never a silent lost lead).
    """
    try:
        url, key = _supabase_creds()
        out: dict[str, dict[str, Any]] = {}
        page = 0
        while True:
            r = httpx.get(
                f"{url}/rest/v1/clinical_trials",
                params={
                    "select": (
                        "nct_id,title,brief_summary,"
                        "detailed_description,eligibility_criteria"
                    ),
                    "order": "nct_id.asc",
                    "limit": "1000",
                    "offset": str(page * 1000),
                },
                headers=_supabase_headers(key, prefer="count=none"),
                timeout=30,
            )
            if r.status_code != 200:
                print(
                    f"  [warn] fetch_prior_rows HTTP {r.status_code}; "
                    "translations will run without ka reuse"
                )
                return out
            rows = r.json()
            for row in rows:
                nct = (row.get("nct_id") or "").strip()
                if nct:
                    out[nct] = row
            if len(rows) < 1000:
                break
            page += 1
        return out
    except Exception as e:  # noqa: BLE001 — best-effort reuse source
        print(f"  [warn] fetch_prior_rows failed ({type(e).__name__}: {e}); no reuse")
        return {}


def upsert_trials(records: list[dict[str, Any]]) -> int:
    """Batch UPSERT records into clinical_trials on conflict nct_id.

    Strips the internal underscore-prefixed helper keys before writing.
    Returns the number of rows the server echoed back.
    """
    if not records:
        return 0
    url, key = _supabase_creds()
    clean = [{k: v for k, v in rec.items() if not k.startswith("_")} for rec in records]
    r = httpx.post(
        f"{url}/rest/v1/clinical_trials",
        params={"on_conflict": "nct_id"},
        json=clean,
        headers=_supabase_headers(
            key, prefer="resolution=merge-duplicates,return=representation"
        ),
        timeout=60,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(
            f"upsert_trials failed: HTTP {r.status_code}: {r.text[:500]}"
        )
    try:
        return len(r.json())
    except ValueError:
        return len(clean)


def fetch_prior_state() -> dict[str, dict[str, Any]]:
    """Read the current clinical_trials rows we care about for diffing.

    Returns ``{nct_id: {"aleksandra_status": ..., "overall_status": ...}}``.
    Used to detect (B2) newly-eligible trials and (B4) overall_status
    transitions before we upsert the freshly-computed records. On any error
    we fail SOFT: an empty dict means "no prior knowledge", which makes the
    very first automated run treat everything as known-baseline-only (the
    Phase A seed already populated the table), avoiding notification spam.
    """
    try:
        url, key = _supabase_creds()
        r = httpx.get(
            f"{url}/rest/v1/clinical_trials",
            params={
                "select": "nct_id,aleksandra_status,overall_status",
                "limit": "10000",
            },
            headers=_supabase_headers(key, prefer="count=none"),
            timeout=30,
        )
        if r.status_code != 200:
            print(
                f"  [warn] fetch_prior_state HTTP {r.status_code}; "
                "treating as no prior knowledge"
            )
            return {}
        out: dict[str, dict[str, Any]] = {}
        for row in r.json():
            nct = (row.get("nct_id") or "").strip()
            if not nct:
                continue
            out[nct] = {
                "aleksandra_status": row.get("aleksandra_status"),
                "overall_status": row.get("overall_status"),
            }
        return out
    except Exception as e:  # noqa: BLE001 — best-effort diff source
        print(f"  [warn] fetch_prior_state failed ({type(e).__name__}: {e}); no prior")
        return {}


# ---------------------------------------------------------------------------
# Telegram (best-effort) — mirrors perception_tick._telegram
# ---------------------------------------------------------------------------
def _telegram(msg: str) -> bool:
    """Send a Telegram message best-effort. Never raises.

    Reads TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID from the environment and
    POSTs to sendMessage. Returns True if the request was made and accepted,
    False otherwise (missing creds / network error / non-2xx). Trials are
    public data, so messages contain NO PHI.
    """
    load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("  [warn] Telegram creds missing — alert not sent")
        return False
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "disable_web_page_preview": True},
            timeout=10,
        )
        return r.status_code in (200, 201)
    except Exception as e:  # noqa: BLE001 — alerts must never crash the matcher
        print(f"  [warn] Telegram send failed ({type(e).__name__}: {e})")
        return False


def build_notification(
    newly_eligible: list[dict[str, Any]],
    status_changes: list[dict[str, Any]],
) -> str | None:
    """Build a concise, PHI-free, family-friendly Georgian Telegram message.

    Returns None when there is nothing worth pinging about: no new leads AND
    no previously-eligible trial that has since closed. The caller treats
    None as "send NOTHING" (no spam).
    """
    # "No longer open" = a trial that WAS identified and is now ineligible.
    closed_leads = [
        c for c in status_changes if c.get("was_eligible") and c.get("now_ineligible")
    ]

    if not newly_eligible and not closed_leads:
        return None

    lines: list[str] = []
    if newly_eligible:
        lines.append(
            f"🔬 ახალი შესაფერისი კლინიკური კვლევა ალექსანდრასთვის: {len(newly_eligible)}"
        )
        for t in newly_eligible[:5]:
            title = (t.get("title") or "").strip() or "(უსათაურო კვლევა)"
            nct = (t.get("nct_id") or "").strip()
            lines.append(f"• {title} ({nct})" if nct else f"• {title}")
        if len(newly_eligible) > 5:
            lines.append(f"…და კიდევ {len(newly_eligible) - 5}")

    if closed_leads:
        if lines:
            lines.append("")
        lines.append(f"⚠️ აღარ მონაბირებს: {len(closed_leads)}")
        for t in closed_leads[:5]:
            title = (t.get("title") or "").strip() or "(უსათაურო კვლევა)"
            nct = (t.get("nct_id") or "").strip()
            lines.append(f"• {title} ({nct})" if nct else f"• {title}")

    lines.append("")
    lines.append(VIEWER_TRIALS_URL)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_status = {"identified": 0, "evaluating": 0, "ineligible": 0}
    id_us = 0
    id_intl = 0
    for rec in records:
        st = rec["aleksandra_status"]
        by_status[st] = by_status.get(st, 0) + 1
        if st == "identified":
            if rec.get("_is_us"):
                id_us += 1
            elif rec.get("_is_international"):
                id_intl += 1
    return {
        "total": len(records),
        "by_status": by_status,
        "identified_us": id_us,
        "identified_intl": id_intl,
    }


def _print_summary(summary: dict[str, Any], *, dry_run: bool, written: int) -> None:
    bs = summary["by_status"]
    print()
    print("Clinical-trial eligibility summary:")
    print(f"  mode               {'DRY-RUN (no write)' if dry_run else 'LIVE upsert'}")
    print(f"  total processed    {summary['total']}")
    print(f"  identified         {bs.get('identified', 0)}")
    print(f"  evaluating         {bs.get('evaluating', 0)}")
    print(f"  ineligible         {bs.get('ineligible', 0)}")
    print(f"  identified · US    {summary['identified_us']}")
    print(f"  identified · intl  {summary['identified_intl']}")
    if not dry_run:
        print(f"  rows upserted      {written}")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
def run(
    *,
    dry_run: bool = False,
    limit: int | None = None,
    notify: bool = False,
    notify_dry: bool = False,
) -> dict[str, Any]:
    """Sync ctgov → clinical_trials, detect new/closed leads, optionally alert.

    Parameters
    ----------
    dry_run     : compute + print, do NOT write to the DB.
    limit       : process only the first N ledger rows (None/0 = all).
    notify      : send a Telegram alert when there is something new/closed.
    notify_dry  : build + print the alert text but DO NOT send (testing).

    Returns a summary dict::

        {"processed": N, "identified": X, "evaluating": Y, "ineligible": Z,
         "newly_eligible": [{"nct_id","title"}, ...],
         "status_changes": [{"nct_id","title","old_status","new_status",...}, ...],
         "written": int, "notified": bool}
    """
    load_env()
    age_months = aleksandra_age_months()
    now_iso = datetime.now(timezone.utc).isoformat()

    # B2/B4: snapshot the existing table BEFORE upserting so we can diff.
    prior = fetch_prior_state()
    # C2: existing rows' bilingual fields, for self-healing ka reuse.
    prior_rows = fetch_prior_rows()

    rows = fetch_ctgov_rows()
    if limit and limit > 0:
        rows = rows[:limit]

    records: list[dict[str, Any]] = []
    newly_eligible: list[dict[str, Any]] = []
    status_changes: list[dict[str, Any]] = []

    # C2: translation coverage stats over the DISPLAYED (translated) fields.
    BILINGUAL_FIELDS = (
        "title",
        "brief_summary",
        "detailed_description",
        "eligibility_criteria",
    )
    xlate = {"ka_filled": 0, "en_only": 0, "r2_full": 0, "r2_fallback": 0}

    for row in rows:
        full = extract_full_fields(fetch_full_study(row.get("raw_artifact_url")) or {})
        if full.get("brief_summary") or full.get("eligibility_criteria"):
            xlate["r2_full"] += 1
        else:
            xlate["r2_fallback"] += 1

        rec = map_and_evaluate(
            source_id=row.get("source_id", ""),
            payload=row.get("payload_metadata") or {},
            age_months=age_months,
            now_iso=now_iso,
            full=full,
            prior_row=prior_rows.get(
                (row.get("payload_metadata") or {}).get("nct_id")
                or row.get("source_id")
            ),
        )

        # Tally ka coverage for displayed trials only (ineligible are en-only by
        # design, so they would skew the "did translation work?" signal).
        if rec["aleksandra_status"] in ("identified", "evaluating"):
            for f in BILINGUAL_FIELDS:
                val = rec.get(f)
                if not isinstance(val, dict) or not val.get("en"):
                    continue
                if _ka_of(val):
                    xlate["ka_filled"] += 1
                else:
                    xlate["en_only"] += 1

        nct = rec["nct_id"]
        new_status = rec["aleksandra_status"]
        new_overall = (rec.get("overall_status") or "").strip().upper() or None
        prev = prior.get(nct)
        prev_alek = prev.get("aleksandra_status") if prev else None
        prev_overall = (
            ((prev.get("overall_status") or "").strip().upper() or None)
            if prev
            else None
        )

        # --- B2: newly-eligible detection ---
        # A trial is a fresh lead if it is NOW 'identified' and either we have
        # never seen it, or it was something other than 'identified' before.
        if new_status == "identified" and prev_alek != "identified":
            newly_eligible.append({"nct_id": nct, "title": _en_of(rec["title"])})

        # --- B4: overall_status monitoring ---
        # Only known trials can have a *change*; a brand-new row is not a
        # "change" (it is captured by newly_eligible above).
        #
        # LIMITATION (B4): the matcher only sees trials the ctgov fetcher
        # re-surfaces. The fetcher queries recruiting-style statuses, so a
        # trial that fully closes may stop being returned — in which case its
        # clinical_trials row RETAINS its last-known overall_status and is
        # NOT re-checked here (no transition is detected for it). Full
        # per-trial re-verification against ClinicalTrials.gov (a direct
        # GET /studies/{nct} for every known nct_id) is deferred to avoid the
        # extra API calls; it is the correct future fix for silent closures.
        changed = bool(prev) and (new_overall != prev_overall)
        rec["status_changed"] = changed
        if changed:
            status_changes.append(
                {
                    "nct_id": nct,
                    "title": _en_of(rec["title"]),
                    "old_status": prev_overall,
                    "new_status": new_overall,
                    # A previously-eligible trial that is now ineligible is a
                    # "no longer open" lead — surfaced prominently in alerts.
                    "was_eligible": prev_alek == "identified",
                    "now_ineligible": new_status == "ineligible",
                }
            )

        records.append(rec)

    summary = summarize(records)
    written = 0
    if not dry_run:
        written = upsert_trials(records)

    print(f"Aleksandra age at run: ~{age_months} months (DOB {DOB.isoformat()})")
    _print_summary(summary, dry_run=dry_run, written=written)
    print(f"  newly eligible     {len(newly_eligible)}")
    print(f"  status changes     {len(status_changes)}")
    print(f"  R2 full / fallback {xlate['r2_full']} / {xlate['r2_fallback']}")
    print(
        f"  ka fields filled   {xlate['ka_filled']}  "
        f"(en-only/fallback: {xlate['en_only']})"
    )

    # --- Telegram notify (B2/B4) ---
    notified = False
    if notify or notify_dry:
        message = build_notification(newly_eligible, status_changes)
        if notify_dry:
            print()
            print("=== Telegram (DRY — not sent) ===")
            print(message if message else "(no notification — nothing new)")
        elif notify:
            if message:
                notified = _telegram(message)
                print(f"  telegram sent      {notified}")
            else:
                print("  telegram           skipped (nothing new)")

    bs = summary["by_status"]
    return {
        "processed": summary["total"],
        "identified": bs.get("identified", 0),
        "evaluating": bs.get("evaluating", 0),
        "ineligible": bs.get("ineligible", 0),
        "newly_eligible": newly_eligible,
        "status_changes": status_changes,
        "written": written,
        "notified": notified,
        "translation": xlate,
        # kept for backwards-compat with any Phase A caller
        "summary": summary,
        "records": records,
    }


# ---------------------------------------------------------------------------
# Self-test (only behind --self-test)
# ---------------------------------------------------------------------------
def _self_test() -> int:
    assert parse_age_to_months("0 Years") == 0, parse_age_to_months("0 Years")
    assert parse_age_to_months("36 Months") == 36, parse_age_to_months("36 Months")
    assert parse_age_to_months("2 Years") == 24, parse_age_to_months("2 Years")
    assert parse_age_to_months("") is None
    assert parse_age_to_months(None) is None
    assert parse_age_to_months("N/A") is None
    # case-insensitivity + singular units
    assert parse_age_to_months("1 year") == 12
    assert parse_age_to_months("1 Month") == 1
    # weeks / days conversions
    assert abs(parse_age_to_months("4 Weeks") - (4 * 7 / DAYS_PER_MONTH)) < 1e-9
    assert abs(parse_age_to_months("30 Days") - (30 / DAYS_PER_MONTH)) < 1e-9
    # location flags
    us, intl = location_flags(["Duke University (United States)"])
    assert us and not intl, (us, intl)
    us, intl = location_flags(["Some Hospital (Germany)"])
    assert (not us) and intl, (us, intl)
    us, intl = location_flags(["A (United States)", "B (Canada)"])
    assert us and intl, (us, intl)

    # --- Phase C: s3 URL parsing ---
    assert _parse_s3_url("s3://my-bucket/ctgov/NCT01.json") == (
        "my-bucket",
        "ctgov/NCT01.json",
    )
    assert _parse_s3_url("https://example.com/x.json") is None
    assert _parse_s3_url("") is None
    assert _parse_s3_url(None) is None
    assert _parse_s3_url("s3://only-bucket") is None

    # --- Phase C: full-study extraction (pure parse, no I/O) ---
    study = {
        "protocolSection": {
            "descriptionModule": {
                "briefSummary": "Brief here.",
                "detailedDescription": "Long detail here.",
            },
            "eligibilityModule": {
                "eligibilityCriteria": "Inclusion: ... Exclusion: ..."
            },
            "conditionsModule": {"conditions": ["HIE", "Cerebral Palsy"]},
            "statusModule": {
                "startDateStruct": {"date": "2025-01-01"},
                "completionDateStruct": {"date": "2027-12-31"},
                "lastUpdatePostDateStruct": {"date": "2026-06-01"},
            },
            "contactsLocationsModule": {
                "overallOfficials": [
                    {
                        "name": "Dr. Lead",
                        "role": "PRINCIPAL_INVESTIGATOR",
                        "email": "lead@x.org",
                    },
                    {"name": "Dr. Other", "role": "STUDY_DIRECTOR"},
                ],
                "centralContacts": [{"name": "Coord A", "email": "coord@x.org"}],
                "locations": [
                    {
                        "facility": "Duke",
                        "city": "Durham",
                        "state": "NC",
                        "country": "United States",
                        "status": "RECRUITING",
                    },
                    {
                        "facility": "Charité",
                        "city": "Berlin",
                        "country": "Germany",
                        "status": "RECRUITING",
                    },
                ],
            },
        }
    }
    f = extract_full_fields(study)
    assert f["brief_summary"] == "Brief here."
    assert f["detailed_description"] == "Long detail here."
    assert "Exclusion" in f["eligibility_criteria"]
    assert f["conditions"] == ["HIE", "Cerebral Palsy"]
    assert len(f["locations"]) == 2 and f["locations"][0]["facility"] == "Duke"
    assert f["locations_sample"] == ["Duke (United States)", "Charité (Germany)"]
    assert f["pi_name"] == "Dr. Lead" and f["pi_email"] == "lead@x.org"
    assert f["coordinator_name"] == "Coord A"
    assert f["start_date"] == "2025-01-01"
    assert f["estimated_completion"] == "2027-12-31"
    assert f["last_updated"] == "2026-06-01"
    # location_flags must work off the new richer locations_sample
    us, intl = location_flags(f["locations_sample"])
    assert us and intl, (us, intl)
    # empty study → all-None / empty, never a crash
    empty = extract_full_fields({})
    assert empty["brief_summary"] is None and empty["conditions"] == []

    # --- Phase C: partial-date normalization (ctgov returns YYYY / YYYY-MM) ---
    assert _normalize_date("2028") == "2028-01-01"
    assert _normalize_date("2028-03") == "2028-03-01"
    assert _normalize_date("2028-03-15") == "2028-03-15"
    assert _normalize_date("") is None
    assert _normalize_date(None) is None
    assert _normalize_date("garbage") is None
    # a partial completionDate must flow through extract_full_fields cleanly
    partial = extract_full_fields(
        {
            "protocolSection": {
                "statusModule": {"completionDateStruct": {"date": "2028-03"}}
            }
        }
    )
    assert partial["estimated_completion"] == "2028-03-01", partial

    # --- Phase C: _en_of / _ka_of on {en,ka} dict / json-text / scalar ---
    assert _en_of({"en": "E", "ka": "K"}) == "E"
    assert _ka_of({"en": "E", "ka": "K"}) == "K"
    assert _en_of('{"en": "E", "ka": "K"}') == "E"
    assert _ka_of('{"en": "E", "ka": "K"}') == "K"
    assert _en_of("plain") == "plain"
    assert _ka_of("plain") == ""
    assert _en_of(None) == "" and _ka_of(None) == ""

    # --- Phase C: bilingual_field (no-translate + reuse paths only; no API) ---
    # None preserves nullable column
    assert bilingual_field(None, translate=True) is None
    # empty string → deliberate empty cell
    assert bilingual_field("", translate=True) == {"en": "", "ka": ""}
    # ineligible (translate=False) with no prior → en-only
    assert bilingual_field("Title", translate=False) == {"en": "Title", "ka": ""}
    # displayed + prior ka present + en unchanged → REUSE (no translation call)
    reuse = bilingual_field(
        "Title", translate=True, prior_value={"en": "Title", "ka": "სათაური"}
    )
    assert reuse == {"en": "Title", "ka": "სათაური"}, reuse
    # ineligible but prior ka exists → keep the good ka (don't wipe it)
    keep = bilingual_field(
        "Title", translate=False, prior_value={"en": "Title", "ka": "სათაური"}
    )
    assert keep == {"en": "Title", "ka": "სათაური"}, keep
    # the migration's en-mirror ka (English, no Mkhedruli) is NOT a real
    # translation: for an ineligible (no-translate) trial it must NOT be reused,
    # so we fall through to en-only rather than storing English-as-Georgian.
    mirror = bilingual_field(
        "Title", translate=False, prior_value={"en": "Title", "ka": "Title"}
    )
    assert mirror == {"en": "Title", "ka": ""}, mirror

    # --- build_notification (B2/B4) ---
    # nothing new → no message (no spam)
    assert build_notification([], []) is None
    # a status change that is NOT an eligible→closed transition → still silent
    assert (
        build_notification(
            [],
            [
                {
                    "nct_id": "NCT1",
                    "title": "X",
                    "old_status": "RECRUITING",
                    "new_status": "ACTIVE_NOT_RECRUITING",
                    "was_eligible": True,
                    "now_ineligible": False,
                }
            ],
        )
        is None
    )
    # a new lead → message contains the headline, the NCT, and the viewer link
    msg = build_notification([{"nct_id": "NCT2", "title": "Cord Blood for HIE"}], [])
    assert msg is not None
    assert "NCT2" in msg and "Cord Blood for HIE" in msg
    assert VIEWER_TRIALS_URL in msg
    assert "1" in msg.splitlines()[0]
    # an eligible→closed transition → "no longer open" block present
    closed = build_notification(
        [],
        [
            {
                "nct_id": "NCT3",
                "title": "Closed Study",
                "old_status": "RECRUITING",
                "new_status": "TERMINATED",
                "was_eligible": True,
                "now_ineligible": True,
            }
        ],
    )
    assert closed is not None
    assert "NCT3" in closed and "აღარ მონაბირებს" in closed

    print("[OK] self-test passed")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute + print summary, do NOT write to the DB.",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only the first N ledger rows (0 = all).",
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="Run the pure-function assertions and exit (no DB access).",
    )
    ap.add_argument(
        "--notify",
        action="store_true",
        help="Send a Telegram alert when there is ≥1 new/closed lead.",
    )
    ap.add_argument(
        "--notify-dry",
        action="store_true",
        help="Build + print the would-be Telegram alert WITHOUT sending it.",
    )
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    run(
        dry_run=args.dry_run,
        limit=args.limit,
        notify=args.notify,
        notify_dry=args.notify_dry,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
