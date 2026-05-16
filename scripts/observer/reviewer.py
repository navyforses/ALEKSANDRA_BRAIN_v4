"""
Observer Bot — diff reviewer.

`review_diff()` sends a unified diff through Haiku 4.5 with the project
rules injected. Returns a list of Finding objects.

If any finding is CRITICAL, the caller can invoke `deep_review()` to
escalate to Sonnet 4.5 with the full file context for a more reliable
verdict.

Both functions route through `scripts.cognition.llm.call_claude` so the
spend is recorded in `runs.token_cost` and the daily-budget gate applies.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from scripts.cognition.llm import call_claude
from scripts.observer.config import (
    ESCALATE_MODEL,
    MAX_TOKENS_DEEP,
    MAX_TOKENS_REVIEW,
    PROJECT_RULES,
    REVIEW_MODEL,
    SEVERITIES,
)


@dataclass
class Finding:
    severity: str  # CRITICAL | WARN | INFO
    line: int | None
    problem: str
    fix: str
    source: str = "haiku"  # which model produced this finding

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "line": self.line,
            "problem": self.problem,
            "fix": self.fix,
            "source": self.source,
        }


@dataclass
class ReviewResult:
    path: str
    findings: list[Finding] = field(default_factory=list)
    escalated: bool = False
    error: str | None = None

    @property
    def has_critical(self) -> bool:
        return any(f.severity == "CRITICAL" for f in self.findings)

    @property
    def has_actionable(self) -> bool:
        return any(f.severity in {"CRITICAL", "WARN"} for f in self.findings)


_PROMPT_REVIEW = """You are a code reviewer for ALEKSANDRA_BRAIN — a medical
research AI for HIE (hypoxic-ischemic encephalopathy) treatment discovery.
The system is being edited concurrently by another LLM (ChatGPT). Your job
is to catch mistakes BEFORE they ship, but you must NOT propose unrelated
refactors or "while you're there" cleanup. Stick to the diff.

{rules}

You will see a unified diff for {path}. Return ONLY a JSON array of
findings — no prose, no markdown fences, just the array.

Schema:
[
  {{
    "severity": "CRITICAL" | "WARN" | "INFO",
    "line": <int or null, line number in the new file>,
    "problem": "<one sentence, what is wrong>",
    "fix": "<one sentence, concrete suggestion>"
  }}
]

Severity ladder:
  CRITICAL  → violates one of the rules above, OR is a runtime bug
              (NameError, TypeError, missing await on async fn,
               SQL injection, leaked secret, append-only-table mutation).
  WARN      → likely bug, suspicious pattern, or wrong column name.
  INFO      → style nit, redundant comment, missing docstring. Use SPARINGLY.

If the diff is fine, return [].

DIFF:
```diff
{diff}
```
"""


_PROMPT_DEEP = """You are a senior code reviewer for ALEKSANDRA_BRAIN. A
faster model already flagged CRITICAL findings on {path}; your job is to
verify them, refine them, and add any deeper issues it missed.

{rules}

Prior findings from the fast pass:
{prior}

Full current file content (post-edit):
```
{content}
```

Return ONLY a JSON array of findings in the same schema as before. Drop
any prior finding you cannot confirm. Add new findings only for genuine
problems. No prose.
"""


def _strip_code_fences(text: str) -> str:
    """LLMs sometimes wrap JSON in ```json ... ```. Strip it."""
    text = text.strip()
    if text.startswith("```"):
        # find the first newline after the opening fence
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1 :]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _parse_findings(raw: str, *, source: str) -> tuple[list[Finding], str | None]:
    """Parse the LLM's JSON-array response. Returns (findings, error_msg)."""
    cleaned = _strip_code_fences(raw)
    if not cleaned:
        return [], None
    # Tolerate leading "Here is..." accidentally emitted before the array
    match = re.search(r"(\[.*\])", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(1)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return [], f"JSON parse failed: {e} (raw head: {raw[:200]!r})"

    if not isinstance(data, list):
        return [], f"expected JSON array, got {type(data).__name__}"

    findings: list[Finding] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        sev = str(item.get("severity", "INFO")).upper()
        if sev not in SEVERITIES:
            sev = "INFO"
        line_raw = item.get("line")
        try:
            line = int(line_raw) if line_raw is not None else None
        except (ValueError, TypeError):
            line = None
        problem = str(item.get("problem", "")).strip()
        fix = str(item.get("fix", "")).strip()
        if not problem:
            continue
        findings.append(
            Finding(severity=sev, line=line, problem=problem, fix=fix, source=source)
        )
    return findings, None


def review_diff(path: str, diff: str) -> ReviewResult:
    """
    Fast-pass review of a unified diff with Haiku 4.5.

    Caller should check `result.has_critical` and optionally invoke
    `deep_review()` to refine with Sonnet 4.5.
    """
    result = ReviewResult(path=path)
    prompt = _PROMPT_REVIEW.format(rules=PROJECT_RULES, path=path, diff=diff)
    try:
        raw = call_claude(
            prompt=prompt,
            model=REVIEW_MODEL,
            max_tokens=MAX_TOKENS_REVIEW,
            agent_id="observer-review",
        )
    except Exception as exc:
        result.error = f"{type(exc).__name__}: {exc}"
        return result

    result.findings, parse_err = _parse_findings(raw, source="haiku")
    if parse_err:
        result.error = parse_err
    return result


def deep_review(path: str, file_content: str, prior: list[Finding]) -> ReviewResult:
    """
    Sonnet 4.5 verifies + refines fast-pass CRITICAL findings using the
    full file context. Caller decides when to invoke this (typically on
    `prior_result.has_critical`).
    """
    result = ReviewResult(path=path, escalated=True)
    prior_dump = json.dumps([f.to_dict() for f in prior], indent=2)
    prompt = _PROMPT_DEEP.format(
        rules=PROJECT_RULES, path=path, prior=prior_dump, content=file_content
    )
    try:
        raw = call_claude(
            prompt=prompt,
            model=ESCALATE_MODEL,
            max_tokens=MAX_TOKENS_DEEP,
            agent_id="observer-deep",
        )
    except Exception as exc:
        result.error = f"{type(exc).__name__}: {exc}"
        return result

    result.findings, parse_err = _parse_findings(raw, source="sonnet")
    if parse_err:
        result.error = parse_err
    return result
