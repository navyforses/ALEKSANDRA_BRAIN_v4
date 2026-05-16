"""
Observer Bot — main polling loop.

Watches the repo for file changes (via filesystem mtime + git status),
debounces them, and routes each settled change through the reviewer +
notifier pipeline. Read-only by design — never edits source files.

Usage
-----
    .venv/Scripts/python.exe -X utf8 -m scripts.observer.watcher
    .venv/Scripts/python.exe -X utf8 -m scripts.observer.watcher --pr 42
    .venv/Scripts/python.exe -X utf8 -m scripts.observer.watcher --once
    .venv/Scripts/python.exe -X utf8 -m scripts.observer.watcher --review FILE

Stop with Ctrl-C. State persists in .observer/state.json so re-runs don't
re-review files that were already cleared in a prior session.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from scripts.ledger import load_env
from scripts.observer.config import (
    DEBOUNCE_S,
    IGNORE_DIRS,
    IGNORE_FILES,
    IGNORE_SUFFIXES,
    MAX_DIFF_BYTES,
    MIN_DIFF_LINES,
    PER_FILE_MAX_REVIEWS,
    PER_FILE_WINDOW_S,
    POLL_INTERVAL_S,
    REPO_ROOT,
    SESSION_HARD_CAP_USD,
    STATE_PATH,
)
from scripts.observer.notifier import emit
from scripts.observer.reviewer import deep_review, review_diff


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
@dataclass
class WatchState:
    # path -> content sha256 of the last version we reviewed
    seen_hashes: dict[str, str] = field(default_factory=dict)
    # path -> deque of recent review timestamps for throttling
    recent_reviews: dict[str, deque[float]] = field(default_factory=dict)

    def to_disk(self) -> None:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "seen_hashes": self.seen_hashes,
            "recent_reviews": {k: list(v) for k, v in self.recent_reviews.items()},
        }
        STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def from_disk(cls) -> WatchState:
        if not STATE_PATH.exists():
            return cls()
        try:
            payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return cls()
        return cls(
            seen_hashes=dict(payload.get("seen_hashes", {})),
            recent_reviews={
                k: deque(v, maxlen=PER_FILE_MAX_REVIEWS * 2)
                for k, v in payload.get("recent_reviews", {}).items()
            },
        )


# ---------------------------------------------------------------------------
# Path filtering
# ---------------------------------------------------------------------------
def should_ignore(rel_path: str) -> bool:
    if rel_path in IGNORE_FILES:
        return True
    parts = rel_path.replace("\\", "/").split("/")
    for prefix in IGNORE_DIRS:
        prefix_parts = prefix.split("/")
        if (
            len(parts) >= len(prefix_parts)
            and parts[: len(prefix_parts)] == prefix_parts
        ):
            return True
    for suf in IGNORE_SUFFIXES:
        if rel_path.endswith(suf):
            return True
    return False


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------
def _run_git(args: list[str]) -> str:
    cp = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if cp.returncode != 0:
        return ""
    return cp.stdout


def find_changed_paths() -> list[str]:
    """Use git status to find changed/untracked files. Faster + lower
    false-positive than a full mtime scan in a real repo."""
    out = _run_git(["status", "--porcelain"])
    changed: list[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        # Format: "XY path" or "XY orig -> new" for renames
        rest = line[3:]
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1]
        rest = rest.strip().strip('"')
        if not rest or should_ignore(rest):
            continue
        # Only files (skip dirs that show up rarely)
        full = REPO_ROOT / rest
        if full.is_file():
            changed.append(rest)
    return changed


def get_diff(rel_path: str) -> str:
    """Unified diff vs HEAD. For untracked files, treat as wholly-new."""
    diff = _run_git(["diff", "--no-color", "HEAD", "--", rel_path])
    if diff:
        return diff[:MAX_DIFF_BYTES]
    # Untracked? Emit a synthetic diff so the reviewer sees the new content
    full = REPO_ROOT / rel_path
    try:
        content = full.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    header = f"--- /dev/null\n+++ b/{rel_path}\n"
    body = "".join(f"+{line}\n" for line in content.splitlines())
    return (header + body)[:MAX_DIFF_BYTES]


def _diff_changed_line_count(diff: str) -> int:
    n = 0
    for line in diff.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")) and line.strip(" +-"):
            n += 1
    return n


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


# ---------------------------------------------------------------------------
# Throttling
# ---------------------------------------------------------------------------
def is_throttled(state: WatchState, rel_path: str, now: float) -> bool:
    window = state.recent_reviews.setdefault(
        rel_path, deque(maxlen=PER_FILE_MAX_REVIEWS * 2)
    )
    # Drop timestamps older than the window
    while window and (now - window[0]) > PER_FILE_WINDOW_S:
        window.popleft()
    return len(window) >= PER_FILE_MAX_REVIEWS


def stamp_review(state: WatchState, rel_path: str, now: float) -> None:
    state.recent_reviews.setdefault(
        rel_path, deque(maxlen=PER_FILE_MAX_REVIEWS * 2)
    ).append(now)


# ---------------------------------------------------------------------------
# Spend tracker
# ---------------------------------------------------------------------------
def _spend_today_usd() -> float:
    try:
        from scripts.cognition.budget import check_daily_budget
    except Exception:
        return 0.0
    try:
        spent, _ = check_daily_budget(threshold_usd=999.0)
        return float(spent)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Per-file review pipeline
# ---------------------------------------------------------------------------
def review_one(
    rel_path: str,
    *,
    state: WatchState,
    enable_telegram: bool,
    pr_number: int | None,
    skip_clean: bool,
) -> bool:
    """Returns True if a review actually ran."""
    full = REPO_ROOT / rel_path
    if not full.is_file():
        return False

    try:
        content = full.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"[observer] cannot read {rel_path}: {exc}", file=sys.stderr)
        return False

    content_hash = sha256(content)
    if state.seen_hashes.get(rel_path) == content_hash:
        return False  # already reviewed this exact content

    diff = get_diff(rel_path)
    if not diff:
        return False
    if _diff_changed_line_count(diff) < MIN_DIFF_LINES:
        # whitespace-only / 1-line edit; not worth the spend
        state.seen_hashes[rel_path] = content_hash
        return False

    now = time.time()
    if is_throttled(state, rel_path, now):
        print(
            f"[observer] throttled {rel_path} "
            f"({PER_FILE_MAX_REVIEWS} reviews / {PER_FILE_WINDOW_S}s)",
            flush=True,
        )
        return False

    result = review_diff(rel_path, diff)
    stamp_review(state, rel_path, now)

    if result.has_critical and not result.error:
        deep = deep_review(rel_path, content, result.findings)
        if not deep.error and deep.findings:
            result = deep

    emit(
        result,
        enable_telegram=enable_telegram,
        pr_number=pr_number,
        skip_clean=skip_clean,
    )
    state.seen_hashes[rel_path] = content_hash
    state.to_disk()
    return True


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def watch_loop(args: argparse.Namespace) -> int:
    load_env()
    state = WatchState.from_disk()
    print(
        f"[observer] watching {REPO_ROOT}  "
        f"poll={POLL_INTERVAL_S}s  debounce={DEBOUNCE_S}s  "
        f"telegram={'on' if not args.no_telegram else 'off'}  "
        f"pr={args.pr or '-'}"
    )
    pending: dict[str, float] = {}  # rel_path -> last-change timestamp
    start_spend = _spend_today_usd()
    try:
        while True:
            changed = find_changed_paths()
            now = time.time()
            for path in changed:
                pending[path] = now

            ready = [p for p, ts in pending.items() if (now - ts) >= DEBOUNCE_S]
            for path in ready:
                pending.pop(path, None)
                try:
                    review_one(
                        path,
                        state=state,
                        enable_telegram=not args.no_telegram,
                        pr_number=args.pr,
                        skip_clean=args.skip_clean,
                    )
                except Exception as exc:
                    print(
                        f"[observer] review crash {path}: "
                        f"{type(exc).__name__}: {exc}",
                        file=sys.stderr,
                    )

            spent = _spend_today_usd() - start_spend
            if spent >= SESSION_HARD_CAP_USD:
                print(
                    f"[observer] session spent ${spent:.4f} ≥ "
                    f"${SESSION_HARD_CAP_USD:.2f} cap — stopping",
                    flush=True,
                )
                return 0

            if args.once:
                return 0
            time.sleep(POLL_INTERVAL_S)
    except KeyboardInterrupt:
        print("\n[observer] stopped (Ctrl-C)")
        state.to_disk()
        return 0


def review_single(args: argparse.Namespace) -> int:
    """One-shot review of a specific path. No polling."""
    load_env()
    rel_path = args.review
    # Normalize to a repo-relative path
    p = Path(rel_path)
    if p.is_absolute():
        try:
            rel_path = str(p.resolve().relative_to(REPO_ROOT))
        except ValueError:
            print(f"[observer] {rel_path} is outside repo {REPO_ROOT}")
            return 2
    rel_path = rel_path.replace("\\", "/")
    if should_ignore(rel_path):
        print(f"[observer] {rel_path} matches an ignore pattern")
        return 0
    state = WatchState()  # ephemeral, don't pollute persistent state
    ran = review_one(
        rel_path,
        state=state,
        enable_telegram=not args.no_telegram,
        pr_number=args.pr,
        skip_clean=False,
    )
    if not ran:
        print(f"[observer] {rel_path} has no reviewable diff (or already clean)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Observer Bot — watch & review")
    ap.add_argument(
        "--pr",
        type=int,
        default=None,
        help="If set, also post findings to this GitHub PR via gh CLI",
    )
    ap.add_argument(
        "--once",
        action="store_true",
        help="Scan once, review everything currently changed, exit",
    )
    ap.add_argument(
        "--review",
        type=str,
        default=None,
        help="One-shot review of a specific file path (skips polling)",
    )
    ap.add_argument(
        "--no-telegram",
        action="store_true",
        help="Disable Telegram delivery (useful when smoke-testing)",
    )
    ap.add_argument(
        "--skip-clean",
        action="store_true",
        help=(
            "Don't print a 'clean' line for files with no findings — "
            "reduces terminal noise during big saves"
        ),
    )
    args = ap.parse_args()

    if os.name != "nt":
        # ANSI on POSIX terminals works by default; on Windows the print
        # stream usually does too in modern terminals, but we don't gate it.
        pass

    if args.review:
        return review_single(args)
    return watch_loop(args)


if __name__ == "__main__":
    sys.exit(main())
