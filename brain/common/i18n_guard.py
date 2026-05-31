"""Phase 7.5 Rule #5 - Bilingual parity guard.

Every text leaf that surfaces to a human MUST exist in both `en` and
`ka`. Phase 6 introduced JSONB `{en: ..., ka: ...}` columns + per-key
parallel dictionary keys (`messages/en.json` + `messages/ka.json`); this
guard codifies the runtime check so a payload that omits one language
cannot reach the Telegram sender or the PDF builder.

Two enforcement entry points:

    1. ``require_bilingual_parity(payload)`` - recursively walks the
       payload; any leaf with a "text"-like key (text / title /
       description / body / summary) must either be inside a
       `{en, ka}` dict OR have a sibling `<key>_en` + `<key>_ka` pair.

    2. ``verify_jsonb_bilingual(value)`` - strict check on the Phase 6
       JSONB shape: dict must have exactly the two keys `en` + `ka`
       with both non-empty strings.

Reference:
    docs/PHASE_6_EXIT_REPORT.md (Phase 6 i18n + JSONB pattern)
    docs/PHASE_6_KA_SUMMARY.md  (anti-loop discipline references)
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class BilingualParityError(ValueError):
    """Raised when a payload violates Rule #5 (bilingual parity)."""


# ---------------------------------------------------------------------------
# Text-leaf keys that must be bilingual
# ---------------------------------------------------------------------------
# Conservative list. Add new keys only by inventing them OR amending this
# tuple. Over-flagging acceptable; under-flagging is the dangerous side.
TEXT_LEAF_KEYS: tuple[str, ...] = (
    "text",
    "title",
    "description",
    "body",
    "summary",
    "label",
    "headline",
    "message",
)


def verify_jsonb_bilingual(value: dict[str, Any]) -> bool:
    """Strict check on Phase 6 JSONB shape `{en: <non-empty str>, ka: ...}`.

    Returns True iff the dict has EXACTLY keys `{en, ka}` with both
    values being non-empty strings.
    """
    if not isinstance(value, dict):
        return False
    if set(value.keys()) != {"en", "ka"}:
        return False
    en, ka = value.get("en"), value.get("ka")
    if not isinstance(en, str) or not en.strip():
        return False
    if not isinstance(ka, str) or not ka.strip():
        return False
    return True


def _has_parallel_keys(parent: dict[str, Any], base_key: str) -> bool:
    """True iff parent contains both `<base>_en` and `<base>_ka` non-empty."""
    en_key = f"{base_key}_en"
    ka_key = f"{base_key}_ka"
    if en_key not in parent or ka_key not in parent:
        return False
    en_val = parent.get(en_key)
    ka_val = parent.get(ka_key)
    if not isinstance(en_val, str) or not en_val.strip():
        return False
    if not isinstance(ka_val, str) or not ka_val.strip():
        return False
    return True


def _walk_for_parity(
    payload: Any, path: str, bad_paths: list[str]
) -> None:
    """Recursively walk payload; flag text-leaf keys lacking bilingual form."""
    if isinstance(payload, dict):
        for k, v in payload.items():
            sub_path = f"{path}.{k}" if path else str(k)
            # If this key is a known text-leaf key with a string value,
            # it must EITHER be a JSONB {en,ka} dict (handled below in
            # the recursive descent when v is dict) OR have parallel
            # keys in the parent dict (handled here).
            if isinstance(k, str) and k in TEXT_LEAF_KEYS:
                if isinstance(v, str) and v.strip():
                    # Bare string at a text-leaf - need _en + _ka siblings.
                    if not _has_parallel_keys(payload, k):
                        bad_paths.append(sub_path)
                elif isinstance(v, dict):
                    # Dict value: must be a bilingual JSONB shape.
                    if not verify_jsonb_bilingual(v):
                        bad_paths.append(sub_path)
            _walk_for_parity(v, sub_path, bad_paths)
    elif isinstance(payload, list):
        for i, item in enumerate(payload):
            _walk_for_parity(item, f"{path}[{i}]", bad_paths)


def require_bilingual_parity(payload: dict[str, Any]) -> None:
    """Raise BilingualParityError on any text-leaf without en+ka parity.

    A text-leaf is acceptable iff:
        * The value is a JSONB-shaped dict ``{en: <str>, ka: <str>}``
          where both strings are non-empty (verify_jsonb_bilingual).
        * OR the parent dict has parallel ``<key>_en`` + ``<key>_ka``
          siblings, both non-empty strings.

    Anything else (en-only, ka-only, empty string, missing entirely)
    raises BilingualParityError.
    """
    if not isinstance(payload, dict):
        raise TypeError(
            f"require_bilingual_parity expects dict; "
            f"got {type(payload).__name__}"
        )
    bad_paths: list[str] = []
    _walk_for_parity(payload, "", bad_paths)
    if bad_paths:
        raise BilingualParityError(
            f"Phase 7.5 Rule #5: {len(bad_paths)} text-leaf path(s) "
            f"missing bilingual parity (need {{en,ka}} dict OR "
            f"<key>_en + <key>_ka siblings): {bad_paths}"
        )


__all__ = [
    "BilingualParityError",
    "TEXT_LEAF_KEYS",
    "require_bilingual_parity",
    "verify_jsonb_bilingual",
]
