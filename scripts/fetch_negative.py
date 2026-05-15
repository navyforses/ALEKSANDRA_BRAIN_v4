"""
fetch_negative.py — PRC-06 negative-evidence retrieval branch.

For every actively-tracked therapy in the Supabase `therapies` table
(aleksandra_status IN receiving, planned, evaluating), build a small
set of negation-flavoured PubMed queries and run them through the
fetch_pubmed pipeline with mode='negative'. Resulting ledger rows
share the source_id with any matching positive-branch row but live
under (source_id, source_type, mode='negative') so the unique index
permits both.

Negation patterns used per therapy:
  - "<name> no effect"
  - "<name> null result"
  - "<name>[ti] AND Retracted Publication[ptyp]"

Aliases inside parentheses (e.g. "Keppra (levetiracetam)") are added
as separate seeds — Keppra-the-brand and levetiracetam-the-INN often
surface different counter-evidence.

Usage
-----
    .venv/Scripts/python.exe -m scripts.fetch_negative                # all active therapies
    .venv/Scripts/python.exe -m scripts.fetch_negative --retmax 2     # keep volume tight
    .venv/Scripts/python.exe -m scripts.fetch_negative --therapies 2  # first N therapies
"""

from __future__ import annotations

import argparse
import re
import sys

import httpx

from scripts.fetch_pubmed import run as fetch_pubmed_run
from scripts.ledger import _supabase_creds, _supabase_headers, load_env

ACTIVE_STATUSES = ("receiving", "planned", "evaluating")


def _list_active_therapies() -> list[str]:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/therapies",
        params={
            "select": "name,aleksandra_status",
            "aleksandra_status": f"in.({','.join(ACTIVE_STATUSES)})",
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=15,
    )
    if r.status_code != 200:
        raise RuntimeError(
            f"therapies query failed: HTTP {r.status_code}: {r.text[:200]}"
        )
    rows = r.json()
    names: list[str] = []
    for row in rows:
        name = (row.get("name") or "").strip()
        if name:
            names.append(name)
    return names


def _seeds_from_name(raw: str) -> list[str]:
    """
    Extract one or more search seeds from a therapy name like:
      "Keppra (levetiracetam)" -> ["Keppra", "levetiracetam"]
      "Duke EAP — cord blood"  -> ["cord blood"]
      "Metformin (cross-disease)" -> ["Metformin"]
    """
    # Split on em-dash / en-dash / hyphen-with-spaces: take the meaningful tail
    parts = re.split(r"\s+[—–-]\s+", raw)
    head = parts[-1] if parts else raw

    seeds: list[str] = []
    m = re.match(r"(.+?)\s*\(([^)]+)\)\s*$", head)
    if m:
        primary = m.group(1).strip()
        aliases = m.group(2).strip()
        if primary:
            seeds.append(primary)
        # alias may itself be a parenthetical comment like "(cross-disease)"
        if aliases and not re.match(r"(cross-disease|inn)", aliases, re.I):
            seeds.append(aliases)
    else:
        seeds.append(head.strip())

    # Drop empties + dedup while preserving order
    out: list[str] = []
    for s in seeds:
        s = s.strip()
        if s and s not in out:
            out.append(s)
    return out


def _negative_queries(seed: str) -> list[str]:
    return [
        f'{seed} "no effect"',
        f'{seed} "null result"',
        f'{seed}[ti] AND "Retracted Publication"[ptyp]',
    ]


def run(retmax: int = 2, therapies_limit: int = 0) -> dict[str, int]:
    load_env()
    therapies = _list_active_therapies()
    if therapies_limit > 0:
        therapies = therapies[:therapies_limit]

    print(f"negative branch: {len(therapies)} active therapies")

    all_queries: list[str] = []
    for t in therapies:
        for seed in _seeds_from_name(t):
            all_queries.extend(_negative_queries(seed))

    print(f"  built {len(all_queries)} negative queries")
    return fetch_pubmed_run(queries=all_queries, retmax=retmax, mode="negative")


def _print_counts(counts: dict[str, int]) -> None:
    print()
    print("Negative-evidence fetch summary:")
    for k, v in counts.items():
        print(f"  {k:18} {v}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--retmax", type=int, default=2, help="PMIDs per negative query")
    ap.add_argument(
        "--therapies",
        type=int,
        default=0,
        help="Run only the first N active therapies (0 = all)",
    )
    args = ap.parse_args()
    counts = run(retmax=args.retmax, therapies_limit=args.therapies)
    _print_counts(counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
