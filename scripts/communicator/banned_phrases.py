"""
banned_phrases.py — Phase 3 CGM-08 clinical-command-language detector.

Deterministic, no LLM. Returns BannedPhraseResult(passed, violations) for any
text that the Communicator is about to persist or render.

Hard rule: blocks clinical-command and prediction language. Communicator
must say "Review this paper" or "Discuss with clinician", never "Aleksandra
should receive X" or "this will work".

Cases covered:
  - Imperative clinical verbs (start/stop/increase/decrease/replace ...)
  - Recommendation framing ("we suggest", "you should", "we recommend")
  - Prediction framing ("Aleksandra will", "outcome will be", "this proves")
  - Patient-directed instructions ("administer", "prescribe", "diagnose")
  - Georgian translations of the same set
  - French translations of the same set

The list is whole-phrase / word-boundary regex match, case-insensitive.
False positives are accepted in favor of false negatives — better to block
a borderline draft and rewrite it than to ship a clinical command.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Violation:
    phrase: str
    matched: str
    locale: str  # 'en' | 'ka' | 'fr'


@dataclass
class BannedPhraseResult:
    passed: bool
    violations: list[Violation]


# ---------------------------------------------------------------------------
# Phrase catalog
# ---------------------------------------------------------------------------
# Each entry: (locale, regex pattern). Pattern is compiled below with re.I.
# Word-boundary anchors used where useful; longer phrases match as-is.

_PATTERNS_EN: list[str] = [
    # Recommendation framing
    r"\byou should\b",
    r"\bwe (?:suggest|recommend|advise)\b",
    r"\bit is recommended that\b",
    r"\bplease take\b",
    r"\bplease administer\b",
    # Patient-directed prescription
    r"\b(?:Aleksandra|the patient|the child)\s+should\b",
    r"\b(?:Aleksandra|the patient|the child)\s+must\b",
    # Imperative clinical verbs (verb at start of clause or after subject)
    r"\b(?:start|stop|begin|discontinue|cease|halt)\s+(?:the\s+|her\s+|his\s+|a\s+|an\s+)?(?:dose|drug|treatment|therapy|medication|infusion|injection|trial)\b",
    r"\b(?:increase|decrease|raise|lower|escalate|reduce)\s+(?:the\s+)?(?:dose|dosage|frequency)\b",
    r"\breplace\s+\w+\s+with\b",
    # Action verbs that imply prescription
    r"\b(?:administer|prescribe|dispense|inject|infuse)\b",
    r"\b(?:diagnose|diagnosed) (?:as|with)\b",
    # Prediction framing
    r"\b(?:Aleksandra|the patient|the child) will\b",
    r"\b(?:outcome|prognosis|response)\s+will\s+be\b",
    r"\bthis (?:proves|guarantees|ensures|confirms that)\b",
    r"\bcertainly will\b",
    r"\bdefinitely will\b",
    r"\b(?:she|he)\s+will\s+(?:recover|improve|respond|fail)\b",
    # Off-label framing without source
    r"\bcure\b",
    r"\bguaranteed to\b",
]

_PATTERNS_KA: list[str] = [
    # Imperatives — recipient should take/start/stop
    r"უნდა\s+მიიღოს",
    r"უნდა\s+შეწყდეს",
    r"უნდა\s+გაიზარდოს",
    r"უნდა\s+შემცირდეს",
    r"უნდა\s+ჩაუტარდეს",
    # Recommendation
    r"ვურჩევთ",
    r"გვირჩევთ",
    r"რეკომენდირებულია",
    # Prediction
    r"გამოჯანმრთელდება",
    r"აუცილებლად\s+გაუმჯობესდება",
    r"ეს\s+აღკვეთს",
    # ===== Phase 6 D-05 additions — REVIEW BEFORE ACTIVATION =====
    # Per CONTEXT.md D-05 + 06-VALIDATION.md Manual-Only Verifications,
    # Shako must sanity-check this lexicon before the lint goes live.
    # In Auto Mode for plan 06-11, the D-05 locked lexicon is auto-approved;
    # native-speaker re-verification tracked in .planning/todos/pending/.
    # RESEARCH.md Pattern 8 note on word boundaries: `\b` is Latin-aware only;
    # for Mkhedruli, existing _PATTERNS_KA entries omit `\b`. The first three
    # additions carry `\b` because they typically appear at Mkhedruli ↔ ASCII
    # script boundaries (space, punctuation, mixed-script context); the
    # remaining five match without `\b` (consistent with the existing convention).
    # TODO(shako-review): English "should" -> Georgian (you-ought, direct-instruction form)
    r"\bმართებთ\b",
    # TODO(shako-review): English "must" -> Georgian (bare 'necessarily')
    r"\bაუცილებლად\b",
    # TODO(shako-review): English "must" -> Georgian (predicative 'it is necessary')
    r"\bაუცილებელია\b",
    # TODO(shako-review): English "consider" -> Georgian (polite imperative 2pl)
    r"განიხილეთ",
    # TODO(shako-review): English "consider" -> Georgian (alt form: 'take into account')
    r"გაითვალისწინეთ",
    # TODO(shako-review): English "try" -> Georgian (polite imperative 2pl)
    r"სცადეთ",
    # TODO(shako-review): English "ask for" -> Georgian (polite imperative 2pl 'demand/ask for')
    r"მოითხოვეთ",
    # TODO(shako-review): English "request" -> Georgian (polite imperative 2pl)
    r"ითხოვეთ",
]

_PATTERNS_FR: list[str] = [
    r"\bvous devriez\b",
    r"\bnous recommandons\b",
    r"\bil est recommandé\b",
    r"\b(?:elle|il) devrait\b",
    r"\bcommencer (?:le|la|un|une) traitement\b",
    r"\barrêter (?:le|la|un|une) (?:traitement|médicament)\b",
    r"\baugmenter la dose\b",
    r"\bréduire la dose\b",
    r"\bguérison\b",
    r"\bse rétablira\b",
]


def _compile(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(p, flags=re.IGNORECASE) for p in patterns]


_COMPILED: dict[str, list[re.Pattern[str]]] = {
    "en": _compile(_PATTERNS_EN),
    "ka": _compile(_PATTERNS_KA),
    "fr": _compile(_PATTERNS_FR),
}


def check(
    text: str, *, locales: tuple[str, ...] = ("en", "ka", "fr")
) -> BannedPhraseResult:
    """Run the banned-phrase scan over the given text.

    `locales` selects which language sets to apply. Default scans all three so
    a draft accidentally written in the wrong language still gets caught.
    """
    violations: list[Violation] = []
    for locale in locales:
        for pat in _COMPILED.get(locale, ()):
            for m in pat.finditer(text):
                violations.append(
                    Violation(phrase=pat.pattern, matched=m.group(0), locale=locale)
                )
    return BannedPhraseResult(passed=len(violations) == 0, violations=violations)


__all__ = ["BannedPhraseResult", "Violation", "check"]
