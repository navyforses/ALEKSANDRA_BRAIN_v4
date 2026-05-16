"""
language.py — Phase 3 CGM-07 language detection.

Deterministic. Detects which of {en, fr, ka} the input is written in. No
LLM call, no external package. Three signals:

  1. Mkhedruli / Mtavruli code blocks (U+10A0..U+10FF, U+1C90..U+1CBF) → ka
  2. French diacritics (é, è, ê, ç, à, ù, î, ô, ï) + common-word match → fr
  3. Default → en

The detector is intentionally biased toward "en" for short or ambiguous
text — the Communicator's default recipient language is English, and a
false-positive ka/fr routing on an English snippet is worse than the inverse.

Confidence:
  - "ka" requires ≥ 3 Mkhedruli code points in the input
  - "fr" requires ≥ 2 diacritics OR a hit on the French-stopword list
  - everything else returns "en"
"""

from __future__ import annotations

from dataclasses import dataclass


# Georgian Mkhedruli + Mtavruli code-point ranges
_KA_RANGES = ((0x10A0, 0x10FF), (0x1C90, 0x1CBF))

# French-only or French-strongly-associated diacritics
_FR_DIACRITICS = set("éèêëçàâùîïôœÿæÉÈÊËÇÀÂÙÎÏÔŒŸÆ")

# Small French stopword list — words that rarely appear in English texts
_FR_STOPWORDS = {
    "le",
    "la",
    "les",
    "des",
    "du",
    "de",
    "et",
    "ou",
    "pour",
    "avec",
    "dans",
    "sur",
    "est",
    "sont",
    "n'est",
    "n'a",
    "c'est",
    "qui",
    "que",
    "il",
    "elle",
    "nous",
    "vous",
    "ils",
    "elles",
    "ce",
    "cette",
    "ces",
    "une",
    "un",
    "par",
    "vers",
    "très",
    "alors",
    "ainsi",
    "donc",
}


@dataclass(frozen=True)
class LanguageDecision:
    code: str  # 'en' | 'fr' | 'ka'
    confidence: float  # 0.0..1.0
    signals: dict[str, int]


def _count_ka_codepoints(text: str) -> int:
    n = 0
    for ch in text:
        cp = ord(ch)
        if (
            _KA_RANGES[0][0] <= cp <= _KA_RANGES[0][1]
            or _KA_RANGES[1][0] <= cp <= _KA_RANGES[1][1]
        ):
            n += 1
    return n


def _count_fr_diacritics(text: str) -> int:
    return sum(1 for ch in text if ch in _FR_DIACRITICS)


def _count_fr_stopwords(text: str) -> int:
    words = [w.strip('.,;:!?"()[]') for w in text.lower().split()]
    return sum(1 for w in words if w in _FR_STOPWORDS)


def detect(text: str) -> LanguageDecision:
    """Return the detected language code + a confidence in [0,1]."""
    if not text or not text.strip():
        return LanguageDecision("en", 0.0, {})

    ka_chars = _count_ka_codepoints(text)
    fr_diacritics = _count_fr_diacritics(text)
    fr_stopwords = _count_fr_stopwords(text)

    signals = {
        "ka_codepoints": ka_chars,
        "fr_diacritics": fr_diacritics,
        "fr_stopwords": fr_stopwords,
        "text_len": len(text),
    }

    # Georgian wins outright — only Georgian writing uses these code points.
    if ka_chars >= 3:
        return LanguageDecision("ka", min(1.0, ka_chars / 10.0), signals)

    # French signal: either ≥2 diacritics, or a stopword hit even without.
    if fr_diacritics >= 2 or fr_stopwords >= 2:
        # Confidence rises with both diacritics and stopwords.
        score = min(1.0, (fr_diacritics + fr_stopwords) / 6.0)
        return LanguageDecision("fr", score, signals)

    return LanguageDecision("en", 0.6, signals)


__all__ = ["detect", "LanguageDecision"]
