"""Phase 7.4 Day 5/6 — Bilingual question generator.

Loads `templates_ka.toml` + `templates_en.toml`, renders one question per
(dim_name, lang) request, validates that no template placeholder leaks
through to the rendered text.

Anti-loop discipline (Phase 6.1 lesson): every KA template is hand-authored
Mkhedruli. `validate_ka_template_anti_loop` enforces that none of the four
banned bigrams appear twice in the same template paragraph.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Literal, Optional


BANNED_BIGRAMS = ("ცარიელი", "ცამეტი", "ფარული", "ცდილია")
PLACEHOLDER_RE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")

DEFAULT_KA_PATH = Path(__file__).parent / "templates_ka.toml"
DEFAULT_EN_PATH = Path(__file__).parent / "templates_en.toml"


class TemplateError(KeyError):
    """Raised when a template lookup or render fails."""


# ---------------------------------------------------------------------------
# Loader (cached per path)
# ---------------------------------------------------------------------------
_CACHE: dict[tuple[str, str], dict[str, dict]] = {}


def load_templates(
    lang: Literal["ka", "en"],
    path: Optional[Path] = None,
) -> dict[str, dict]:
    """Load + cache the TOML for `lang`. Returns dict[dim_name -> entry]."""
    if path is None:
        path = DEFAULT_KA_PATH if lang == "ka" else DEFAULT_EN_PATH
    cache_key = (lang, str(path))
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    if not path.is_file():
        raise FileNotFoundError(f"templates not found: {path}")
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    _CACHE[cache_key] = data
    return data


def clear_cache() -> None:
    _CACHE.clear()


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render_question(
    *,
    dim_name: str,
    lang: Literal["ka", "en"],
    eig_pct: float,
    variables: Optional[dict] = None,
) -> str:
    """Render the template for `dim_name` in `lang`.

    Always interpolates `eig_pct` rounded to 1 decimal. Any additional
    `variables` dict is merged on top.
    """
    templates = load_templates(lang)
    if dim_name not in templates:
        raise TemplateError(
            f"no template registered for dim_name={dim_name!r} lang={lang!r}"
        )
    entry = templates[dim_name]
    if "template" not in entry:
        raise TemplateError(
            f"template entry for {dim_name} lacks 'template' key"
        )
    raw = entry["template"]
    payload: dict[str, object] = {"eig_pct": f"{float(eig_pct):.1f}"}
    if variables:
        payload.update(variables)
    try:
        rendered = raw.format(**payload)
    except KeyError as exc:
        raise TemplateError(
            f"missing variable {exc} for {dim_name}/{lang}"
        ) from exc
    return rendered


def validate_no_template_leaks(rendered: str) -> bool:
    """True iff no `{xxx}` placeholders remain in the rendered text."""
    return PLACEHOLDER_RE.search(rendered) is None


def validate_ka_template_anti_loop(text: str) -> list[str]:
    """Return the list of banned bigrams that appear >= 2 times in `text`.

    Empty list = template passes the anti-loop check.
    """
    offenders: list[str] = []
    for bigram in BANNED_BIGRAMS:
        if text.count(bigram) >= 2:
            offenders.append(bigram)
    return offenders


def render_all_dims_for_lang(
    *,
    lang: Literal["ka", "en"],
    eig_pct: float = 12.5,
) -> dict[str, str]:
    """Helper: render every registered dim_name for `lang`. Used by verifier."""
    templates = load_templates(lang)
    out: dict[str, str] = {}
    for dim_name in templates.keys():
        out[dim_name] = render_question(
            dim_name=dim_name, lang=lang, eig_pct=eig_pct
        )
    return out


__all__ = [
    "BANNED_BIGRAMS",
    "TemplateError",
    "DEFAULT_KA_PATH",
    "DEFAULT_EN_PATH",
    "load_templates",
    "clear_cache",
    "render_question",
    "validate_no_template_leaks",
    "validate_ka_template_anti_loop",
    "render_all_dims_for_lang",
]
