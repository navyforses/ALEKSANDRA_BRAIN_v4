"""Python-side mirror of viewer/lib/i18n.ts displayField.

Used by Telegram / Gmail / manager-briefing worker code to resolve a
bilingual JSONB field to a single locale string with English fallback.

Source contract: RESEARCH.md Pitfall 6 (Phase 6 — Bilingual System i18n).

The leading underscore on the module name marks this helper Communicator-
internal: it is not a general-purpose JSON utility, it is the worker-side
twin of the TypeScript helper at viewer/lib/i18n.ts. Both share the same
behavior across the 4 input shapes:

  - None           -> ''
  - str (legacy)   -> str (passthrough, no translation)
  - dict           -> field[locale] or field['en'] or ''
  - anything else  -> str(field) (defensive str-coercion)

The viewer helper accepts BilingualField = string | {en?, ka?} | null;
this helper must accept the same four shapes so worker-side reads behave
identically to client-side reads. See Plan 06-12-PLAN.md for the audit
trail.
"""

from __future__ import annotations

from typing import Any


def display_field_py(field: Any, locale: str) -> str:
    """Resolve a bilingual JSONB field to a locale-specific string.

    Tolerates legacy TEXT (plain string), a bilingual dict ({en, ka}),
    an en-only dict ({en}), and None. Symmetric with viewer/lib/i18n.ts
    displayField — RESEARCH.md Pitfall 6.

    Args:
        field: dict with {en, ka} keys, plain str (legacy TEXT), or None.
        locale: 'en' or 'ka'.

    Returns:
        Locale-resolved string; empty string if `field` is None.
    """
    if field is None:
        return ""
    if isinstance(field, str):
        return field  # legacy TEXT row tolerance
    if isinstance(field, dict):
        return field.get(locale) or field.get("en") or ""
    return str(field)


__all__ = ["display_field_py"]
