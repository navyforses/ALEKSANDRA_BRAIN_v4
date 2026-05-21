"""
phi_redactor.py — Phase 3 CGM-02 PHI redactor.

Deterministic. Reads the recipient's `consent_*` flags from the contacts table
(or accepts an in-memory ConsentFlags object for unit tests). Strips or
substitutes PHI unless the matching consent flag is True.

Default identity used everywhere consent_full_name=False:
    "A.J., 8-month-old infant with severe HIE"

PHI categories handled
----------------------
1. Patient name — first + last variants → "A.J."
2. DOB day (e.g. 28.08.2025, Aug 28 2025, 28/08/2025, 28 აგვისტო 2025)
   → "Aug 2025" (preserves month/year, drops day)
3. MRN literal (7616818) or "MRN: <digits>" → "[REDACTED:MRN]"
4. Hospital names from a fixed list → "a U.S. hospital" unless
   consent_hospital_names
5. Doctor names — passed in via ConsentFlags.known_doctor_names or
   discovered from the contacts table where contact_type='clinician' →
   "a clinician" unless consent_doctor_names
6. Street addresses (regex) → "[REDACTED:address]"
7. Any reference to viewer/*.nii(.gz)|.dcm files → BLOCK (RedactionResult.blocked=True)

Return contract
---------------
RedactionResult(
    text=str,            # the redacted text
    redactions=[Redaction(category, original, replacement, span)],
    blocked=bool,        # True if a hard-block pattern fired
)

A blocked draft must never persist. The Communicator pipeline raises before
inserting into outreach_log / alerts_log / briefs.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import psycopg2


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ConsentFlags:
    """Family-controlled consent set for a single recipient."""

    consent_full_name: bool = False
    consent_doctor_names: bool = False
    consent_hospital_names: bool = False
    known_doctor_names: tuple[str, ...] = ()


@dataclass
class Redaction:
    category: str
    original: str
    replacement: str
    span: tuple[int, int]


@dataclass
class RedactionResult:
    text: str
    redactions: list[Redaction] = field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None


DEFAULT_IDENTITY = "A.J., 8-month-old infant with severe HIE"


# ---------------------------------------------------------------------------
# Pattern catalog
# ---------------------------------------------------------------------------
# Patient identity — Aleksandra / Jincharadze and their Georgian forms.
_NAME_PATTERNS = [
    r"\bAleksandra\s+Jincharadze\b",
    r"\bAleksandra\s+J\.",
    r"\bAleksandra\b",
    r"\bJincharadze\b",
    r"ალექსანდრა\s+ჯინჭარაძე",
    r"ალექსანდრა",
    r"ჯინჭარაძე",
]

# DOB — day of August 2025 in multiple formats.
_DOB_PATTERNS = [
    r"\b28[./-]0?8[./-]2025\b",
    r"\b0?8[./-]28[./-]2025\b",
    r"\bAug(?:ust)?\s+28(?:,)?\s+2025\b",
    r"\b28\s+Aug(?:ust)?\s+2025\b",
    r"\b28\s+აგვისტო\s+2025\b",
    r"\b28[./-]08[./-]25\b",
]
_DOB_REPLACEMENT = "Aug 2025"

# Hard MRN.
_MRN_PATTERNS = [
    r"\b7616818\b",
    r"\bMRN[:\s]+\d{6,8}\b",
    r"\bMRN\s*#?\s*\d{6,8}\b",
]
_MRN_REPLACEMENT = "[REDACTED:MRN]"

# Hospitals — both English + Georgian forms.
#
# Phase 6 / I18N-10 widening:
#   - Suffix anchor `\b` replaced with lookahead `(?=\b|-)` to allow Georgian
#     genitive / instrumental suffix glue (e.g. `Boston Medical Center-ის`,
#     `BMC-ში`, `Duke-ის`). The lookahead does not consume the suffix so the
#     surrounding case marker remains in the redacted output.
#   - Georgian transliteration variants added: ბოსტონის სამედიცინო ცენტრი
#     (BMC), ფილოქსენიის სახლი (Philoxenia House), დიუკი (Duke).
#   - Standalone `Duke` added (covers `Duke-ის EAP` and any other bare
#     reference) — earlier patterns only matched `Duke EAP` or
#     `Duke (University) Medical Center/Hospital`.
_HOSPITAL_PATTERNS = [
    r"\bBoston Medical Center(?=\b|-)",
    r"\bBMC(?=\b|-)",
    r"\bDuke (?:University )?(?:Medical Center|Hospital)(?=\b|-)",
    r"\bDuke EAP(?=\b|-)",
    r"\bDuke(?=\b|-)",
    r"\bWisconsin (?:Virtual )?A2(?=\b|-)",
    r"\bPhiloxenia House(?=\b|-)",
    r"\bBumrungrad(?=\b|-)",
    # Georgian transliterations (Mkhedruli) — no \b because \b is ASCII-only.
    r"ბოსტონის სამედიცინო ცენტრი",
    r"ფილოქსენიის სახლი",
    r"დიუკი",
]
_HOSPITAL_REPLACEMENT = "a U.S. hospital"

# Clinician names — Phase 6 / I18N-10 addition.
#
# Earlier the redactor relied on `consent.known_doctor_names` (populated by the
# Supabase `contacts` table) to scrub doctor identities. That is fine in
# production but it leaks PHI in tests + early-startup contexts where the DB
# isn't reachable. RESEARCH.md Pattern 8 and the phi_ka.yaml fixture
# `ექიმი Dr. Hien-მა გვირჩია` require a deterministic literal-list fallback.
#
# Suffix uses `(?=\b|-)` so Georgian genitive / ergative glue (e.g.
# `Dr. Hien-მა`, `Dr. Maypole-ის`) still resolves to "a clinician".
_CLINICIAN_PATTERNS = [
    r"\bDr\.\s+Hien(?=\b|-)",
    r"\bDr\.\s+August(?=\b|-)",
    r"\bDr\.\s+Jack\s+Maypole(?=\b|-)",
    r"\bDr\.\s+Maypole(?=\b|-)",
    r"\bJeanette\s+Heitman(?=\b|-)",
]
_CLINICIAN_REPLACEMENT = "a clinician"

# Street address heuristic — number followed by Street/St/Avenue/Boulevard
_ADDRESS_PATTERN = (
    r"\b\d{1,5}\s+[A-Z][A-Za-z0-9.\- ]+\s+"
    r"(?:Street|St\.?|Avenue|Ave\.?|Boulevard|Blvd\.?|Road|Rd\.?|Drive|Dr\.?|Lane|Ln\.?|Way|Ct\.?)\b"
)
_ADDRESS_REPLACEMENT = "[REDACTED:address]"

# Block trigger — viewer/*.nii / .nii.gz / .dcm references.
_BLOCK_PATTERN = (
    r"viewer[\\/][^\s\)]+?\.(?:nii(?:\.gz)?|dcm)\b"
    r"|(?<![A-Za-z0-9])(?:[^\s/\\]+\.(?:nii(?:\.gz)?|dcm))\b"
)


# ---------------------------------------------------------------------------
# Consent flag loader
# ---------------------------------------------------------------------------
def load_consent_flags(contact_id: str | None) -> ConsentFlags:
    """Fetch consent flags for a contact. None contact_id → all-False defaults.

    Also returns the list of known clinician names from the contacts table so
    the redactor can scrub doctor identities if consent_doctor_names=False.
    """
    if contact_id is None:
        clinician_names = _load_clinician_names()
        return ConsentFlags(known_doctor_names=clinician_names)

    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT consent_full_name, consent_doctor_names, consent_hospital_names
                FROM contacts WHERE id = %s
                """,
                (contact_id,),
            )
            row = cur.fetchone()
        clinician_names = _load_clinician_names(conn=conn)
    finally:
        conn.close()

    if row is None:
        return ConsentFlags(known_doctor_names=clinician_names)
    return ConsentFlags(
        consent_full_name=bool(row[0]),
        consent_doctor_names=bool(row[1]),
        consent_hospital_names=bool(row[2]),
        known_doctor_names=clinician_names,
    )


def _load_clinician_names(conn=None) -> tuple[str, ...]:
    """Return all full_name + short_name values from contacts where role=clinician."""
    owns = False
    if conn is None:
        conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
        owns = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT full_name, short_name FROM contacts
                WHERE contact_type = 'clinician'
                """
            )
            names: list[str] = []
            for full_name, short_name in cur.fetchall():
                if full_name:
                    names.append(full_name)
                if short_name:
                    names.append(short_name)
        return tuple(sorted(set(names)))
    finally:
        if owns:
            conn.close()


# ---------------------------------------------------------------------------
# Core redact()
# ---------------------------------------------------------------------------
def redact(text: str, *, consent: ConsentFlags | None = None) -> RedactionResult:
    """Apply the PHI redaction pipeline.

    `consent` is a ConsentFlags object. Pass `load_consent_flags(contact_id)`
    for production calls, or build one manually for unit tests.
    """
    if consent is None:
        consent = ConsentFlags()

    redactions: list[Redaction] = []
    out = text

    # 1. Hard-block: viewer/*.nii(.gz)/.dcm references — refuse to draft.
    m = re.search(_BLOCK_PATTERN, out)
    if m:
        return RedactionResult(
            text=out,
            redactions=[],
            blocked=True,
            block_reason=f"MRI artifact reference: {m.group(0)!r}",
        )

    # 2. Patient name → "A.J." unless consent_full_name.
    if not consent.consent_full_name:
        for pat in _NAME_PATTERNS:
            out = _redact_pattern(out, pat, "A.J.", "name", redactions)

    # 3. DOB day → "Aug 2025".
    for pat in _DOB_PATTERNS:
        out = _redact_pattern(out, pat, _DOB_REPLACEMENT, "dob", redactions)

    # 4. MRN → [REDACTED:MRN].
    for pat in _MRN_PATTERNS:
        out = _redact_pattern(out, pat, _MRN_REPLACEMENT, "mrn", redactions)

    # 5. Hospital names → "a U.S. hospital" unless consent_hospital_names.
    if not consent.consent_hospital_names:
        for pat in _HOSPITAL_PATTERNS:
            out = _redact_pattern(
                out, pat, _HOSPITAL_REPLACEMENT, "hospital", redactions
            )

    # 6. Doctor names → "a clinician" unless consent_doctor_names.
    #    Two sources combined: the deterministic literal list (_CLINICIAN_PATTERNS,
    #    safe under no-DB / test conditions) and the DB-derived
    #    `consent.known_doctor_names` (production augmentation).
    if not consent.consent_doctor_names:
        for pat in _CLINICIAN_PATTERNS:
            out = _redact_pattern(
                out, pat, _CLINICIAN_REPLACEMENT, "doctor", redactions
            )
        for name in consent.known_doctor_names:
            pat = r"\b" + re.escape(name) + r"(?=\b|-)"
            out = _redact_pattern(out, pat, "a clinician", "doctor", redactions)

    # 7. Street address → [REDACTED:address].
    out = _redact_pattern(
        out, _ADDRESS_PATTERN, _ADDRESS_REPLACEMENT, "address", redactions
    )

    return RedactionResult(text=out, redactions=redactions, blocked=False)


def _redact_pattern(
    text: str,
    pattern: str,
    replacement: str,
    category: str,
    redactions: list[Redaction],
) -> str:
    """Substitute every match of `pattern` and record each redaction span."""
    compiled = re.compile(pattern, flags=re.IGNORECASE)
    matches = list(compiled.finditer(text))
    if not matches:
        return text
    # Walk in reverse so spans stay valid as we replace.
    new = text
    for m in reversed(matches):
        redactions.append(
            Redaction(
                category=category,
                original=m.group(0),
                replacement=replacement,
                span=(m.start(), m.end()),
            )
        )
        new = new[: m.start()] + replacement + new[m.end() :]
    return new


def redact_bilingual(
    pair: dict[str, str],
    consent: ConsentFlags | None = None,
) -> dict:
    """Run redact() on both halves of a {en, ka} pair and OR-block.

    Returns:
        {
          "en": RedactionResult,
          "ka": RedactionResult,
          "blocked_or": bool,           # True if EITHER half blocked
          "blocked_reasons": list[str], # block_reason strings for blocked halves,
                                        # prefixed with "en:" / "ka:" so callers can
                                        # tell which side tripped.
        }

    Callers (agents/communicator.py, scripts/manager/briefing.py per 06-09 Task 3)
    must check `blocked_or` and raise BEFORE persisting the bilingual pair.

    Phase 6 / I18N-10 — closes RESEARCH.md Pitfall 5 ("PHI redactor scanned only
    English half"). The single-string `redact()` API is unchanged; this helper
    is a pure wrapper that calls it twice and aggregates the result.
    """
    if consent is None:
        consent = ConsentFlags()

    en_result = redact(pair.get("en", ""), consent=consent)
    ka_result = redact(pair.get("ka", ""), consent=consent)

    blocked_or = en_result.blocked or ka_result.blocked
    blocked_reasons: list[str] = []
    if en_result.blocked:
        blocked_reasons.append(f"en: {en_result.block_reason}")
    if ka_result.blocked:
        blocked_reasons.append(f"ka: {ka_result.block_reason}")

    return {
        "en": en_result,
        "ka": ka_result,
        "blocked_or": blocked_or,
        "blocked_reasons": blocked_reasons,
    }


__all__ = [
    "ConsentFlags",
    "Redaction",
    "RedactionResult",
    "DEFAULT_IDENTITY",
    "load_consent_flags",
    "redact",
    "redact_bilingual",
]
