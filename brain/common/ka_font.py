"""brain/common/ka_font.py — on-demand Georgian (Mkhedruli) font provisioner.

ReportLab's built-in fonts (Helvetica / Times / Courier) carry no Georgian
glyphs, so any KA PDF (e.g. build_family_handover_pdf, the weekly brief KA
summary lines) renders U+10A0–10FF as tofu boxes. Rather than commit a ~400KB
binary into the repo, we PROVISION the font:

    download Noto Sans Georgian (OFL) on demand → verify against a pinned
    SHA256 → cache under a gitignored dir → register with ReportLab.

Why a checksum, not just a download: it is the do-not-fabricate guarantee. A
corrupted or MITM'd download fails loudly (FontProvisionError) instead of
silently drawing boxes the family would mistake for real text.

Safe-by-default:
  - URL + checksum are env-overridable (ALEKSANDRA_KA_FONT_URL /
    ALEKSANDRA_KA_FONT_SHA256) so a moved mirror is a config fix, not a code
    change — and so we never have to hardcode a hash we cannot verify here.
  - When a pin is set it is ENFORCED (constant-time). When it is left empty the
    first download logs the computed hash (trust-on-first-use) so Shako can
    paste it in to harden. `python -m brain.common.ka_font --print-hash`
    prints it without touching a PDF.
  - Offline / download disabled: ensure_ka_font(strict=True) raises a clear
    FontProvisionError (use for KA-language docs that would otherwise be tofu);
    strict=False returns None so EN-only PDFs still render (today's behavior) —
    never a silent tofu page.

This module imports cleanly without ReportLab installed (a shim TTFError keeps
the except clause valid); the real ReportLab calls happen inside ensure_ka_font.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import shutil
import urllib.error
import urllib.request
from pathlib import Path

LOG = logging.getLogger(__name__)

try:  # keep importable even where ReportLab is not installed
    from reportlab.pdfbase.ttfonts import TTFError
except Exception:  # pragma: no cover - reportlab always present in PDF paths

    class TTFError(Exception):  # type: ignore[no-redef]
        pass


FONT_FAMILY = "NotoSansGeorgian"
_REGULAR_FILENAME = "NotoSansGeorgian-Regular.ttf"

# Cache lives next to other brain assets; gitignored (see .gitignore).
CACHE_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# Best-effort default mirror (Noto Sans Georgian, OFL). Env-overridable so a
# moved/renamed mirror is a one-line config fix; the optional net smoke test
# (KA_FONT_NET_TEST=1) is what actually verifies URL + digest in CI/manually.
_DEFAULT_URL = (
    "https://raw.githubusercontent.com/notofonts/georgian/main/fonts/"
    "NotoSansGeorgian/full/ttf/NotoSansGeorgian-Regular.ttf"
)

# Module-level idempotency: registerFont is process-global in ReportLab.
_REGISTERED = False


class FontProvisionError(RuntimeError):
    """Raised when the Georgian font cannot be provisioned/verified."""


def _font_url() -> str:
    return os.environ.get("ALEKSANDRA_KA_FONT_URL", "").strip() or _DEFAULT_URL


def _pin_sha256() -> str:
    return os.environ.get("ALEKSANDRA_KA_FONT_SHA256", "").strip()


def _download_allowed(explicit: bool | None) -> bool:
    if explicit is not None:
        return explicit
    raw = os.environ.get("ALEKSANDRA_FONT_DOWNLOAD", "1").strip().lower()
    return raw not in ("0", "false", "no", "")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_checksum(path: Path, pin: str, *, unlink_on_fail: bool) -> None:
    actual = _sha256(path)
    if not pin:
        LOG.warning(
            "KA font is not pinned — computed sha256=%s. Set "
            "ALEKSANDRA_KA_FONT_SHA256 (or the module pin) to enforce it.",
            actual,
        )
        return
    if not hmac.compare_digest(actual, pin):
        if unlink_on_fail:
            path.unlink(missing_ok=True)
        raise FontProvisionError(
            f"KA font checksum mismatch: expected {pin}, got {actual}"
        )


def _download(url: str, dest: Path) -> None:
    """Download `url` to `dest` atomically (.part → os.replace). Stdlib only."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "aleksandra_brain/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp, open(tmp, "wb") as fh:
        shutil.copyfileobj(resp, fh)
    os.replace(tmp, dest)


def _ensure_cached(*, allow_download: bool | None = None) -> Path:
    path = CACHE_DIR / _REGULAR_FILENAME
    pin = _pin_sha256()
    if path.exists() and path.stat().st_size > 0:
        if pin:  # verify a warm cache only when we have something to verify against
            _verify_checksum(path, pin, unlink_on_fail=True)
        if path.exists():
            return path
    if not _download_allowed(allow_download):
        raise FontProvisionError(
            f"KA font not cached at {path} and download is disabled "
            f"(ALEKSANDRA_FONT_DOWNLOAD=0)."
        )
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _download(_font_url(), path)
    _verify_checksum(path, pin, unlink_on_fail=True)
    return path


def ensure_ka_font(
    *, allow_download: bool | None = None, strict: bool = False
) -> str | None:
    """Register the Georgian font family with ReportLab; return its name or None.

    allow_download: None → honor env ALEKSANDRA_FONT_DOWNLOAD (default on).
    strict: True → raise FontProvisionError on any failure (use for KA-language
            docs that would otherwise render tofu). False → log + return None so
            EN-only output keeps rendering (zero regression vs today).
    """
    global _REGISTERED
    if _REGISTERED:
        return FONT_FAMILY
    try:
        path = _ensure_cached(allow_download=allow_download)
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        pdfmetrics.registerFont(TTFont(FONT_FAMILY, str(path)))
        # No separate bold/italic file — map them to the regular face so headings
        # render Georgian (regular weight) rather than tofu. ASCII headers that
        # need true bold keep using Helvetica-Bold at the call site.
        pdfmetrics.registerFontFamily(
            FONT_FAMILY,
            normal=FONT_FAMILY,
            bold=FONT_FAMILY,
            italic=FONT_FAMILY,
            boldItalic=FONT_FAMILY,
        )
        _REGISTERED = True
        return FONT_FAMILY
    except (FontProvisionError, OSError, urllib.error.URLError, TTFError) as e:
        if strict:
            raise FontProvisionError(str(e)) from e
        LOG.warning(
            "KA font unavailable (%s); PDFs fall back to EN-only / Latin glyphs.", e
        )
        return None


def _print_hash() -> int:
    """Download (if needed) and print the cached font's sha256 — for pinning."""
    logging.basicConfig(level=logging.INFO)
    try:
        path = _ensure_cached()
    except FontProvisionError as e:
        print(f"could not provision font: {e}")
        return 1
    print(f"{_REGULAR_FILENAME}  sha256={_sha256(path)}")
    print("Pin via: ALEKSANDRA_KA_FONT_SHA256=<hash>  (or edit the module).")
    return 0


if __name__ == "__main__":
    import sys

    if "--print-hash" in sys.argv:
        sys.exit(_print_hash())
    # Default: provision + register, report outcome.
    name = ensure_ka_font(strict=False)
    print(f"registered: {name}" if name else "font NOT provisioned (see warnings)")
