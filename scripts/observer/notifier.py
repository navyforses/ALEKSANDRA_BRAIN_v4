"""
Observer Bot — 4-channel finding emitter.

`emit()` writes a `ReviewResult` to:
  1. Terminal (color-coded by severity).
  2. Daily log file `.observer/findings/YYYY-MM-DD.log`.
  3. Telegram (CRITICAL + WARN only, gated by env).
  4. GitHub PR comment (only if `--pr <N>` was passed and a real
     finding fires; INFO suppressed).

Channels are best-effort: failure to post to one never blocks the others.
"""

from __future__ import annotations

import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

import httpx

from scripts.ledger import load_env
from scripts.observer.config import (
    LOG_DIR,
    TELEGRAM_SEVERITIES,
)
from scripts.observer.reviewer import Finding, ReviewResult


# --- Terminal colors -------------------------------------------------------
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[31m"
_YEL = "\033[33m"
_CYN = "\033[36m"
_GRY = "\033[90m"


def _color_for(severity: str) -> str:
    return {
        "CRITICAL": _RED + _BOLD,
        "WARN": _YEL,
        "INFO": _GRY,
    }.get(severity, "")


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _today() -> str:
    return dt.date.today().isoformat()


# --- Channel 1: terminal ---------------------------------------------------
def _emit_terminal(result: ReviewResult) -> None:
    badge = "[observer]"
    if result.error:
        print(f"{_RED}{badge} ERROR{_RESET} {result.path}: {result.error}", flush=True)
        return
    if not result.findings:
        print(
            f"{_GRY}{badge} clean{_RESET} {result.path}"
            + (" (escalated)" if result.escalated else ""),
            flush=True,
        )
        return
    tag = f"{_GRY}sonnet{_RESET}" if result.escalated else f"{_DIM}haiku{_RESET}"
    print(
        f"\n{badge} {result.path} {tag} — {len(result.findings)} finding(s)",
        flush=True,
    )
    for f in result.findings:
        loc = f":{f.line}" if f.line else ""
        col = _color_for(f.severity)
        print(f"  {col}{f.severity}{_RESET}{loc}  {f.problem}", flush=True)
        if f.fix:
            print(f"    {_CYN}→{_RESET} {f.fix}", flush=True)


# --- Channel 2: daily log file ---------------------------------------------
def _emit_log(result: ReviewResult) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{_today()}.log"
    lines = [f"[{_now_iso()}] {result.path} escalated={result.escalated}"]
    if result.error:
        lines.append(f"  ERROR: {result.error}")
    elif not result.findings:
        lines.append("  clean")
    else:
        for f in result.findings:
            loc = f":{f.line}" if f.line else ""
            lines.append(f"  [{f.severity}]{loc} {f.problem}")
            if f.fix:
                lines.append(f"      fix: {f.fix}")
    lines.append("")  # trailing blank line
    with log_path.open("a", encoding="utf-8") as fp:
        fp.write("\n".join(lines))
    return log_path


# --- Channel 3: Telegram ---------------------------------------------------
def _telegram_payload(result: ReviewResult) -> str | None:
    """Build a Telegram message for actionable findings only."""
    actionable = [f for f in result.findings if f.severity in TELEGRAM_SEVERITIES]
    if not actionable:
        return None
    head = "Observer Bot — issues in " + result.path
    if result.escalated:
        head += " (Sonnet)"
    lines = [head]
    for f in actionable:
        loc = f":{f.line}" if f.line else ""
        lines.append(f"[{f.severity}]{loc} {f.problem}")
        if f.fix:
            lines.append("  fix: " + f.fix)
    return "\n".join(lines)[:3800]  # Telegram message cap is 4096


def _emit_telegram(result: ReviewResult) -> bool:
    text = _telegram_payload(result)
    if not text:
        return False
    load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=8,
        )
        return r.status_code == 200
    except Exception as exc:
        print(f"  [telegram-fail] {type(exc).__name__}: {exc}", file=sys.stderr)
        return False


# --- Channel 4: GitHub PR --------------------------------------------------
def _pr_payload(result: ReviewResult) -> str | None:
    """Build a GitHub PR comment, suppressing INFO-only finds."""
    actionable = [f for f in result.findings if f.severity in {"CRITICAL", "WARN"}]
    if not actionable:
        return None
    severity_emoji = {"CRITICAL": "🚨", "WARN": "⚠️"}
    lines = [
        f"### Observer Bot review — `{result.path}`",
        "",
        f"_{'Sonnet 4.5 deep' if result.escalated else 'Haiku 4.5 fast'} pass — "
        f"{_now_iso()}_",
        "",
    ]
    for f in actionable:
        loc = f"`{result.path}`" + (f":L{f.line}" if f.line else "")
        emoji = severity_emoji.get(f.severity, "•")
        lines.append(f"- {emoji} **{f.severity}** {loc} — {f.problem}")
        if f.fix:
            lines.append(f"  - _fix:_ {f.fix}")
    return "\n".join(lines)


def _emit_pr(result: ReviewResult, pr_number: int) -> bool:
    body = _pr_payload(result)
    if not body:
        return False
    try:
        cp = subprocess.run(
            ["gh", "pr", "comment", str(pr_number), "--body", body],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if cp.returncode != 0:
            print(
                f"  [gh-pr-fail] exit={cp.returncode} stderr={cp.stderr.strip()[:200]}",
                file=sys.stderr,
            )
            return False
        return True
    except FileNotFoundError:
        print("  [gh-pr-fail] gh CLI not on PATH", file=sys.stderr)
        return False
    except Exception as exc:
        print(f"  [gh-pr-fail] {type(exc).__name__}: {exc}", file=sys.stderr)
        return False


# --- Public emitter --------------------------------------------------------
def emit(
    result: ReviewResult,
    *,
    enable_telegram: bool = True,
    pr_number: int | None = None,
    skip_clean: bool = False,
) -> dict:
    """
    Fan out `result` to the four channels. Returns a per-channel status
    dict so the watcher can log delivery health.
    """
    status: dict[str, object] = {
        "terminal": False,
        "log": False,
        "telegram": False,
        "pr": False,
    }

    if skip_clean and not result.findings and not result.error:
        # Don't bother emitting a noisy "clean" line. Useful when ChatGPT
        # is saving 30+ files in a burst.
        return status

    _emit_terminal(result)
    status["terminal"] = True

    log_path = _emit_log(result)
    status["log"] = str(log_path)

    if enable_telegram:
        status["telegram"] = _emit_telegram(result)

    if pr_number is not None:
        status["pr"] = _emit_pr(result, pr_number)

    return status


# Re-export Finding for callers that want it w/o reaching into reviewer
__all__ = ["emit", "Finding", "ReviewResult"]
