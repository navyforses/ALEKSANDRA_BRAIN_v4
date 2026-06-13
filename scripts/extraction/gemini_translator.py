"""scripts/extraction/gemini_translator.py — the Gemini translator bot.

A single, reusable English→Georgian (Mkhedruli) translation engine built on
Google's newest GA model, **gemini-3.5-flash**. Used by the scheduled repair
(025_repair_bilingual_ka.py) and available to any caller that needs clean
bilingual output.

Two gateways, picked automatically:
  1. OpenRouter (the project "writer" tier via scripts.cognition.llm.call_llm)
     when OPENROUTER_API_KEY is present — instrumented + daily-budget-gated.
     This is what the Railway worker uses in production.
  2. Direct Google AI Studio (GEMINI_API_KEY / GOOGLE_AI_STUDIO_KEY) otherwise
     — used for local runs and GitHub Actions, where the OpenRouter key is not
     provisioned. `thinkingBudget: 0` is set so the token budget goes to the
     translation, not Gemini-3.x internal reasoning (which otherwise truncates
     short titles).

Both gateways hit the same gemini-3.5-flash model, so output is equivalent.

Quality contract (same for both gateways):
  - title  → one Mkhedruli line, no markdown/commentary/quotes.
  - prose  → faithful multi-paragraph translation, no markdown headers/bold.
  - never Chinese/Japanese/Cyrillic (rejected → retry → TranslationFailed).
  - a refusal or guard failure raises TranslationFailed; the caller keeps the
    English and never writes a fabricated or garbled ka.

Notably, gemini-3.5-flash translates clinical titles that the Claude safety
classifier refused (e.g. titles containing "cocaine"), so switching the engine
here also closes those residual gaps.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request

from scripts.cognition import models
from scripts.cognition.budget import BudgetExceeded, check_daily_budget


class TranslationFailed(RuntimeError):
    """Raised when no acceptable Georgian could be produced (refusal / guard)."""


# gemini-3.5-flash is the newest GA flash model (verified 2026-06 via the
# Google AI Studio model list + a live translation test). Overridable from env.
DIRECT_MODEL = os.environ.get("GEMINI_DIRECT_MODEL", "gemini-3.5-flash")
_GOOGLE_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

TITLE_MAX_TOKENS = 512
PROSE_MAX_TOKENS = 8192

# --------------------------------------------------------------------------- #
# cleaning / guards (Georgian U+10A0–10FF never overlaps CJK or Cyrillic)
# --------------------------------------------------------------------------- #

_MD_HEADER_ML = re.compile(r"(?m)^\s*#{1,6}\s+")
_KA_COMMENTARY = (
    "გთხოვთ მიაწოდოთ",
    "მოდი, უფრო",
    "თარგმანი:",
    "I cannot",
    "I'm unable",
    "I am unable",
)


def has_georgian(text: str | None) -> bool:
    return any("Ⴀ" <= ch <= "ჿ" for ch in (text or ""))


def has_cjk(text: str | None) -> bool:
    return any("　" <= ch <= "鿿" for ch in (text or ""))


def has_cyrillic(text: str | None) -> bool:
    return any("Ѐ" <= ch <= "ӿ" for ch in (text or ""))


def is_messy(text: str | None) -> bool:
    if not text:
        return False
    if has_cjk(text) or has_cyrillic(text):
        return True
    return any(m in text for m in _KA_COMMENTARY)


def titleize(text: str) -> str:
    """Reduce a response to one clean title line."""
    s = (text or "").strip()
    for sep in ("\n---", "\n\n", "\n"):
        if sep in s:
            s = s.split(sep, 1)[0].strip()
    return _MD_HEADER_ML.sub("", s).replace("**", "").strip().strip("\"'").strip()


_TITLE_SYSTEM = (
    "You translate a short research label/title from English to Georgian "
    "(Mkhedruli only). Output ONLY the Georgian text on ONE line — no "
    "commentary, no alternative versions, no markdown, no quotes. Use Georgian "
    "Mkhedruli plus Latin letters/digits for acronyms and proper nouns; never "
    "use Chinese, Japanese, or Cyrillic. Translate idioms naturally. If the "
    "English is truncated, translate only what is given. These are neutral "
    "descriptions of peer-reviewed scientific/clinical studies, not medical "
    "advice; do not refuse."
)
_PROSE_SYSTEM = (
    "You translate text (a research abstract or clinical summary) from English "
    "to Georgian (Mkhedruli only). Translate faithfully and completely, keeping "
    "paragraph breaks. Output ONLY the Georgian translation — no commentary, no "
    "markdown headers, no '**' bold, no added notes. Use Georgian Mkhedruli plus "
    "Latin letters/digits for acronyms; never use Chinese, Japanese, or "
    "Cyrillic. These are neutral descriptions of peer-reviewed scientific/"
    "clinical studies, not medical advice; do not refuse."
)

# --------------------------------------------------------------------------- #
# gateways
# --------------------------------------------------------------------------- #


def _openrouter_ready() -> bool:
    return (
        bool(os.environ.get("OPENROUTER_API_KEY", "").strip())
        and models.provider() != "anthropic"
    )


def _google_key() -> str:
    return (
        os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("GOOGLE_AI_STUDIO_KEY", "").strip()
    )


def _via_openrouter(prompt: str, system: str, max_tokens: int) -> str:
    from scripts.cognition.llm import LLMRefusal, call_llm

    try:
        return call_llm(
            prompt=prompt,
            agent_id="ka_translator_bot",
            model=models.TIER_MODEL["writer"],
            system=system,
            max_tokens=max_tokens,
            temperature=0.2,
        )
    except LLMRefusal:
        return ""


def _via_google(prompt: str, system: str, max_tokens: int) -> str:
    key = _google_key()
    if not key:
        raise TranslationFailed("no OPENROUTER_API_KEY and no GEMINI_API_KEY in env")
    # Budget defence (the OpenRouter path gets this inside call_llm). A ledger
    # read hiccup must not crash translation, but a real over-budget must stop.
    try:
        check_daily_budget(raise_on_over=True)
    except BudgetExceeded:
        raise
    except Exception:  # noqa: BLE001 — ledger unreachable; proceed (cheap call)
        pass
    body = json.dumps(
        {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.2,
                # Gemini 3.x reasons by default and would eat the output budget,
                # truncating short titles — translation needs no thinking.
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{_GOOGLE_ENDPOINT}/{DIRECT_MODEL}:generateContent",
        data=body,
        method="POST",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
    )
    # Retry transient server/rate errors (the public API 503s under load); fail
    # fast on 4xx that are not rate limits.
    transient = {429, 500, 502, 503, 504}
    last_err = ""
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
                data = json.loads(resp.read().decode("utf-8"))
            cand = (data.get("candidates") or [{}])[0]
            parts = cand.get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts).strip()
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code not in transient:
                raise TranslationFailed(f"google api {last_err}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = f"net {type(e).__name__}"
        time.sleep(2 * (attempt + 1))  # 2,4,6,8s backoff
    raise TranslationFailed(f"google api unavailable after retries ({last_err})")


def _generate(prompt: str, system: str, max_tokens: int) -> str:
    """Prefer OpenRouter (production); fall back to direct Google (local/CI)."""
    if _openrouter_ready():
        try:
            out = _via_openrouter(prompt, system, max_tokens)
            if out:
                return out
        except RuntimeError:  # missing key / gateway issue → try Google
            pass
    return _via_google(prompt, system, max_tokens)


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #


def translate_title(en: str, *, max_attempts: int = 3) -> str:
    """English → one clean Mkhedruli title line. Raises TranslationFailed."""
    last = ""
    for _ in range(max_attempts):
        cand = titleize(
            _generate(
                f"Translate this title to Georgian:\n\n{en}",
                _TITLE_SYSTEM,
                TITLE_MAX_TOKENS,
            )
        )
        last = cand
        if (
            cand
            and has_georgian(cand)
            and not has_cjk(cand)
            and not has_cyrillic(cand)
            and not is_messy(cand)
        ):
            return cand
    raise TranslationFailed(
        f"title still bad after {max_attempts} attempts: {last[:60]!r}"
    )


def translate_prose(en: str) -> str:
    """English → faithful Georgian prose. Raises TranslationFailed."""
    out = _generate(
        f"Translate this text to Georgian:\n\n{en}", _PROSE_SYSTEM, PROSE_MAX_TOKENS
    )
    out = _MD_HEADER_ML.sub("", (out or "").strip()).replace("**", "").strip()
    if (
        not out
        or not has_georgian(out)
        or has_cjk(out)
        or has_cyrillic(out)
        or is_messy(out)
    ):
        raise TranslationFailed(f"prose translation rejected: {out[:60]!r}")
    return out
