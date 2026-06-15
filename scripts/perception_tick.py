"""
perception_tick.py — Phase 1 orchestrator.

Runs all perception passes in sequence:
  1. fetch_pubmed                (PRC-01)
  2. fetch_ctgov                 (PRC-02)
  3. perception.sources.ctis     (Phase E — EU CTIS)
  4. perception.sources.isrctn   (Phase E — UK ISRCTN)
  5. fetch_preprints             (PRC-03)
  6. gap_filler                  (PRC-04 + PRC-05)
  7. fetch_negative              (PRC-06)
Then the trials eligibility matcher runs, ingesting ctgov + ctis + isrctn from
evidence_ledger (cross-registry dedup + bilingual build) — see
docs/CLINICAL_TRIALS_SOURCES_RESEARCH.md.

Before any HTTP call: budget gate check against Supabase `runs` for a
recent `budget_lock` / `killed_by_budget_gate` row. If one exists,
halts the whole tick with exit_status='halted_by_budget' and posts
a Telegram alert. Otherwise runs all passes, sums the counts, and
inserts a single `runs` row at the end (the runs table is append-only;
we record start/end on one row at completion).

Phase 1 token cost is 0 — none of these fetchers call Claude. The
budget gate is still respected because Phase 2+ will add reasoning
calls and we want the same pre-flight check in place from the start.

Usage
-----
    .venv/Scripts/python.exe -m scripts.perception_tick                # full tick
    .venv/Scripts/python.exe -m scripts.perception_tick --small        # tight caps (dev)
    .venv/Scripts/python.exe -m scripts.perception_tick --no-telegram  # silence summary
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone

import httpx

from scripts.ledger import _supabase_creds, _supabase_headers, load_env


# ---------------------------------------------------------------------------
# Budget gate check
# ---------------------------------------------------------------------------
def _budget_locked() -> bool:
    """
    Return True if a `kind='budget_lock'` row exists in `runs` since
    midnight UTC today. The n8n daily-budget-gate workflow writes these
    when the daily token spend exceeds DAILY_BUDGET_USD; the daily reset
    naturally clears yesterday's locks at UTC midnight. We don't conflate
    them with old fire-drill rows or our own halted ticks.
    """
    midnight = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    cutoff = midnight.isoformat()
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/runs",
        params={
            "select": "id,start_time",
            "kind": "eq.budget_lock",
            "start_time": f"gte.{cutoff}",
            "order": "start_time.desc",
            "limit": "1",
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=10,
    )
    if r.status_code != 200:
        # If we can't check, fail open — don't block the tick on a transient
        # Supabase blip. The Phase 0 budget drill already exercises hard-lock
        # paths so this is a soft pre-flight.
        print(f"  [warn] budget gate check returned HTTP {r.status_code}; failing open")
        return False
    return bool(r.json())


# ---------------------------------------------------------------------------
# runs row writer (append-only — single row at completion)
# ---------------------------------------------------------------------------
def _write_run(
    *,
    start: datetime,
    end: datetime,
    exit_status: str,
    counts_by_step: dict[str, dict[str, int]],
    exit_reason: str | None = None,
) -> str | None:
    url, key = _supabase_creds()
    body = {
        "kind": "perception_tick",
        "agent_id": "perception_tick",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "exit_status": exit_status,
        "token_cost": 0,  # Phase 1 makes zero Claude calls
        "tokens_input": 0,
        "tokens_output": 0,
    }
    if exit_reason:
        body["exit_reason"] = exit_reason
    # draft_link is a free TEXT col; stash the JSON summary here so the family
    # can read the per-pass counts straight off the runs row.
    body["draft_link"] = json.dumps(counts_by_step, sort_keys=True)
    r = httpx.post(
        f"{url}/rest/v1/runs",
        json=body,
        headers={
            **_supabase_headers(key),
            "Prefer": "return=representation",
        },
        timeout=10,
    )
    if r.status_code in (200, 201):
        try:
            return r.json()[0]["id"]
        except Exception:
            return None
    print(f"  [warn] failed to write runs row: HTTP {r.status_code}: {r.text[:200]}")
    return None


# ---------------------------------------------------------------------------
# Telegram (best-effort)
# ---------------------------------------------------------------------------
def _telegram(msg: str) -> None:
    load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg},
            timeout=5,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Step runners with isolation — one bad source must not kill the tick
# ---------------------------------------------------------------------------
def _safe_run(label: str, fn, **kwargs):
    print(f"\n=== {label} ===")
    try:
        return fn(**kwargs)
    except Exception as e:
        traceback.print_exc()
        return {"error": f"{type(e).__name__}: {e}"}


def run(*, small: bool = False, no_gap: bool = False) -> dict:
    load_env()
    start = datetime.now(timezone.utc)
    print(f"perception_tick start: {start.isoformat()}")

    if _budget_locked():
        end = datetime.now(timezone.utc)
        run_id = _write_run(
            start=start,
            end=end,
            exit_status="killed_by_budget_gate",
            counts_by_step={},
            exit_reason="budget_lock row present at tick start",
        )
        _telegram("🛑 perception_tick HALTED — budget gate is locked. No fetches ran.")
        return {
            "exit_status": "killed_by_budget_gate",
            "run_id": run_id,
            "counts": {},
        }

    # Lazy-import each fetcher so a syntax error in one doesn't block the others
    # at module-load time.
    from scripts.fetch_ctgov import run as fetch_ctgov_run
    from scripts.fetch_negative import run as fetch_negative_run
    from scripts.fetch_preprints import run as fetch_preprints_run
    from scripts.fetch_pubmed import run as fetch_pubmed_run

    if small:
        pubmed_kwargs = {"retmax": 3, "queries": [], "mode": "positive"}
        # ^ note: queries is overridden below to ALL_QUERIES[:3] for dev runs
        from scripts.fetch_pubmed import ALL_QUERIES

        pubmed_kwargs["queries"] = ALL_QUERIES[:3]
        ctgov_kwargs = {"page_size": 3, "queries": None}
        # fetch_ctgov.run uses default QUERY_SETS if queries is None — slice via "queries:N" arg
        from scripts.fetch_ctgov import QUERY_SETS

        ctgov_kwargs["queries"] = QUERY_SETS[:2]
        # Phase E: tight caps for the new registry fetchers in --small dev runs.
        ctis_kwargs = {"size": 5, "max_pages": 1}
        isrctn_kwargs = {"limit": 25, "max_offset": 0}
        preprints_kwargs = {"max_per_feed": 3}
        gap_kwargs = {"hours": 6, "limit": 3}
        neg_kwargs = {"retmax": 2, "therapies_limit": 2}
    else:
        pubmed_kwargs = {"retmax": 10}
        ctgov_kwargs = {"page_size": 10}
        ctis_kwargs = {"size": 20, "max_pages": 3}
        isrctn_kwargs = {"limit": 100, "max_offset": 100}
        preprints_kwargs = {"max_per_feed": 10}
        gap_kwargs = {"hours": 6, "limit": 20}
        neg_kwargs = {"retmax": 2, "therapies_limit": 0}

    # Phase E: lazy-import the pluggable registry fetchers (isolation — a syntax
    # error in one source must not block the others at module-load time).
    from scripts.perception.sources.ctis import run as fetch_ctis_run
    from scripts.perception.sources.isrctn import run as fetch_isrctn_run

    counts: dict[str, dict[str, int]] = {}
    counts["pubmed"] = _safe_run("PubMed (PRC-01)", fetch_pubmed_run, **pubmed_kwargs)
    counts["ctgov"] = _safe_run(
        "ClinicalTrials.gov (PRC-02)", fetch_ctgov_run, **ctgov_kwargs
    )
    # Phase E: EU CTIS + UK ISRCTN — each isolated; one failure != whole tick.
    counts["ctis"] = _safe_run("EU CTIS (Phase E)", fetch_ctis_run, **ctis_kwargs)
    counts["isrctn"] = _safe_run(
        "UK ISRCTN (Phase E)", fetch_isrctn_run, **isrctn_kwargs
    )
    counts["preprints"] = _safe_run(
        "bioRxiv + medRxiv RSS (PRC-03)", fetch_preprints_run, **preprints_kwargs
    )
    if no_gap:
        # OPS-4: the worker-independent GitHub Actions fallback skips gap-fill —
        # Crawl4AI/Playwright are too heavy for CI; PubMed/CTgov/preprints still
        # flow so the Core Value pipeline survives a Railway outage.
        counts["gap_filler"] = {"skipped": "no_gap"}
        print("\n=== Crawl4AI gap-fill (PRC-04+05) === skipped (--no-gap)")
    else:
        from scripts.gap_filler import run as gap_filler_run

        counts["gap_filler"] = _safe_run(
            "Crawl4AI gap-fill (PRC-04+05)", gap_filler_run, **gap_kwargs
        )
    counts["negative"] = _safe_run(
        "Negative-evidence branch (PRC-06)", fetch_negative_run, **neg_kwargs
    )

    # Phase B wave 1: after the fetch passes have refreshed evidence_ledger,
    # re-run the clinical-trials eligibility matcher so the /research/trials
    # board stays current and new/closed leads ping Telegram. This makes ZERO
    # Claude calls (pure DB diff + Telegram), so it sits outside the token
    # budget and is fine to always run. Wrapped in _safe_run for isolation —
    # a matcher failure must never kill the tick. notify=True emits a family
    # alert only when there is something genuinely new (the Phase A seed of 59
    # trials is already the baseline, so the first automated run stays quiet).
    from scripts.trials.eligibility_matcher import run as trials_match_run

    counts["trials_match"] = _safe_run(
        "Trials eligibility match (Phase B)", trials_match_run, notify=True
    )

    end = datetime.now(timezone.utc)
    dt_seconds = int((end - start).total_seconds())

    # Aggregate for the summary line
    def _g(step: str, key: str) -> int:
        return int(counts.get(step, {}).get(key, 0) or 0)

    pubmed_n = _g("pubmed", "ledger_inserted")
    ctgov_n = _g("ctgov", "ledger_inserted")
    ctis_n = _g("ctis", "ledger_inserted")
    isrctn_n = _g("isrctn", "ledger_inserted")
    preprints_n = _g("preprints", "ledger_inserted")
    gap_n = _g("gap_filler", "ledger_inserted")
    neg_n = _g("negative", "ledger_inserted")
    total = pubmed_n + ctgov_n + ctis_n + isrctn_n + preprints_n + gap_n + neg_n

    # Phase B: surface the trials match outcome on the summary line.
    tm = counts.get("trials_match", {}) or {}
    new_leads = len(tm.get("newly_eligible", []) or []) if isinstance(tm, dict) else 0
    closed_leads = (
        sum(
            1
            for c in (tm.get("status_changes") or [])
            if c.get("was_eligible") and c.get("now_ineligible")
        )
        if isinstance(tm, dict)
        else 0
    )

    summary_line = (
        f"🕷️ perception_tick OK  +{total} rows in {dt_seconds}s\n"
        f"  pubmed={pubmed_n}  ctgov={ctgov_n}  ctis={ctis_n}  isrctn={isrctn_n}\n"
        f"  preprints={preprints_n}  gap-fill={gap_n}  negative={neg_n}\n"
        f"  trials: new={new_leads}  closed={closed_leads}"
    )

    run_id = _write_run(
        start=start,
        end=end,
        exit_status="completed",
        counts_by_step=counts,
    )

    print()
    print("─" * 60)
    print(summary_line)
    print(f"runs row id: {run_id}")
    print("─" * 60)
    _telegram(summary_line)

    return {
        "exit_status": "completed",
        "run_id": run_id,
        "counts": counts,
        "total_new_rows": total,
        "duration_seconds": dt_seconds,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--small", action="store_true", help="Dev caps (3 queries each)")
    ap.add_argument(
        "--no-telegram",
        action="store_true",
        help="Skip Telegram summary (testing only)",
    )
    ap.add_argument(
        "--no-gap",
        action="store_true",
        help="Skip the Crawl4AI gap-fill pass (worker-independent CI fallback)",
    )
    args = ap.parse_args()

    if args.no_telegram:
        # Stub the telegram function locally
        global _telegram

        def _telegram(_msg: str) -> None:
            return

    result = run(small=args.small, no_gap=args.no_gap)
    return 0 if result["exit_status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
