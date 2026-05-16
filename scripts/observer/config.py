"""
Observer Bot — configuration constants.

Tunable knobs live here so the watcher / reviewer / notifier modules
stay focused on their respective concerns.
"""

from __future__ import annotations

from pathlib import Path

# --- Paths -----------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Ignore prefixes (relative to repo root). Any path that startswith one of
# these is never reviewed.
IGNORE_DIRS = {
    ".planning",
    ".venv",
    "node_modules",
    ".git",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    ".pre-commit-cache",
    ".observer",  # the bot's own output
    ".handoffs",
    "docs/archive",
    "dist",
    "build",
    ".next",
    ".vercel",
    ".cache",
    "viewer/.next",
}

# Ignore exact path-matches (relative to repo root). Things like
# "handoff.md" that we don't want reviewed every save.
IGNORE_FILES = {
    "handoff.md",
    "CLAUDE.md",
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "uv.lock",
    ".gitignore",
}

# Ignore suffixes. Generated, binary, or otherwise un-reviewable.
IGNORE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".lock",
    ".log",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".nii",
    ".nii.gz",
    ".dcm",
    ".onnx",
    ".pt",
}

# --- Timings ---------------------------------------------------------------

POLL_INTERVAL_S = 10  # how often the watcher scans the tree
DEBOUNCE_S = 30  # how long a file must be stable before review
MIN_DIFF_LINES = 3  # skip trivial whitespace-only / 1-line diffs
MAX_DIFF_BYTES = 60_000  # truncate huge diffs (~15K tokens of input)

# --- Models ----------------------------------------------------------------

REVIEW_MODEL = "claude-haiku-4-5-20251001"
ESCALATE_MODEL = "claude-sonnet-4-5"
ESCALATE_ON = {"CRITICAL"}  # severities that trigger a Sonnet deep-dive
MAX_TOKENS_REVIEW = 1500
MAX_TOKENS_DEEP = 3000

# --- Cost guards -----------------------------------------------------------

# Per-file throttle: if the same file is reviewed N times within window,
# the bot starts skipping it to avoid runaway spend during a churning
# editing session.
PER_FILE_MAX_REVIEWS = 5
PER_FILE_WINDOW_S = 600

# Session-level kill switch (USD added by this observer process).
SESSION_HARD_CAP_USD = 5.0

# --- Output ----------------------------------------------------------------

LOG_DIR = REPO_ROOT / ".observer" / "findings"
STATE_PATH = REPO_ROOT / ".observer" / "state.json"

# Severities (canonical order — used for sort + color routing)
SEVERITIES = ("CRITICAL", "WARN", "INFO")
TELEGRAM_SEVERITIES = {"CRITICAL", "WARN"}  # don't ping family on INFO


# --- Project rules (injected into the review prompt) -----------------------

PROJECT_RULES = """
ALEKSANDRA_BRAIN — non-negotiable project rules (mark violation as CRITICAL):

1. **Privacy**: MRI / DICOM data is CLIENT-SIDE ONLY. Server-side persistence
   of `.nii`, `.nii.gz`, `.dcm` paths or uploads = CRITICAL.

2. **Source integrity**: every surfaced fact must carry provenance
   (ledger_id, pmid, ct_id, doi, or chunk_id). Fabricated drug names,
   trial IDs, or made-up source URLs = CRITICAL.

3. **Anthropic models** — use these exact IDs:
   - `claude-sonnet-4-5`              (default reasoning)
   - `claude-sonnet-4-6`              (hard cases only)
   - `claude-haiku-4-5-20251001`      (cheap classifiers)
   Using `claude-sonnet-4-20250514` (retires 2026-06-15) = CRITICAL.

4. **LLM call routing**: every Anthropic call goes through
   `scripts/cognition/llm.py` (`call_claude` or `make_instrumented_async_anthropic`).
   Bare `anthropic.Anthropic()` outside that file = CRITICAL.

5. **Network**: Neo4j and Qdrant URLs MUST force IPv4 on Windows via
   `.replace('localhost', '127.0.0.1')`. Missing this = CRITICAL.

6. **Secrets**: no hardcoded API keys, service-role keys, or bearer
   tokens. Anything matching `sk-`, `service_role`, `eyJ...` in source
   code = CRITICAL.

7. **Postgres column conventions** (Phase 0 schema):
   - `papers.source_url` and `papers.pdf_storage_path` (NOT `papers.r2_path`)
   - `runs.start_time` (NOT `runs.started_at`)
   - `evidence_ledger.ingested_at` (NOT `evidence_ledger.created_at`)
   - `hypotheses.confidence_level` is TEXT CHECK in
     ('high','moderate','low','very_low') — NOT a float.
   Wrong column name = WARN (likely PGRST204 at runtime).

8. **Verifier discipline**: NEVER mutate `verify_phase*.py` to lower a
   threshold to make a failing check pass. Lowering an assertion = CRITICAL.

9. **Append-only audit**: `runs` table has PATCH/DELETE triggers that
   reject mutation. Any code calling `_supabase_patch('runs', ...)` or
   `DELETE FROM runs` = CRITICAL.

10. **Frontend**: never `fetch()` from inside `viewer/` to any URL that
    is not the same Vercel deployment (FND-02). External fetches in the
    viewer = CRITICAL.
"""
