"""Phase 7.3 Day 5 — In-memory LRU cache for scenario summaries + arrays.

Keyed by ``scenario_hash`` (SHA-256 from ``compute_scenario_hash``).
Persistent caching is Phase 7.3 Layer C scope (migration 019 +
``simulation_runs`` table); this layer keeps an in-process LRU only.

The cache stores BOTH the ScenarioSummary and the raw trajectory array
so callers can pass the array onward to ``compare_scenarios`` without a
re-run. Memory footprint per entry is approximately
``n_samples * n_outcomes * (horizon + 1) * 8 bytes``; for a 100-sample
reference scenario this is ~1.6 MB, well within the 32-entry budget.

Reference:
    - v7_architecture/70_PHASES/73_PHASE_7_3_SIMULATION_ENGINE_3W.md
      section 1 layer A Day 5 + verifier check 6 (replay < 1 s).
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Optional

import numpy as np

from brain.sim.aggregator import (
    ScenarioSummary,
    aggregate_trajectories,
)
from brain.sim.scenario import Scenario, compute_scenario_hash
from brain.sim.trajectory import simulate_scenario


# ---------------------------------------------------------------------------
# Cache class
# ---------------------------------------------------------------------------
class ScenarioCache:
    """In-process LRU cache for (summary, array) pairs."""

    def __init__(self, max_entries: int = 32) -> None:
        self._max_entries = int(max_entries)
        self._store: OrderedDict[str, tuple[ScenarioSummary, np.ndarray]] = (
            OrderedDict()
        )
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(
        self, scenario_hash: str
    ) -> Optional[tuple[ScenarioSummary, np.ndarray]]:
        """Return cached (summary, array) or None; touches LRU order on hit."""
        if scenario_hash in self._store:
            self._store.move_to_end(scenario_hash)
            self._hits += 1
            return self._store[scenario_hash]
        self._misses += 1
        return None

    def put(
        self,
        scenario_hash: str,
        summary: ScenarioSummary,
        arr: np.ndarray,
    ) -> None:
        """Insert (or refresh) an entry; evict oldest at capacity."""
        if scenario_hash in self._store:
            self._store.move_to_end(scenario_hash)
            self._store[scenario_hash] = (summary, arr)
            return
        self._store[scenario_hash] = (summary, arr)
        while len(self._store) > self._max_entries:
            self._store.popitem(last=False)
            self._evictions += 1

    def clear(self) -> None:
        """Drop all entries and reset counters."""
        self._store.clear()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def stats(self) -> dict:
        """Return hit / miss / eviction counters + current size + hit ratio."""
        total = self._hits + self._misses
        hit_ratio = (self._hits / total) if total > 0 else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "current_size": len(self._store),
            "hit_ratio": float(hit_ratio),
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_GLOBAL_CACHE = ScenarioCache()


def get_cached(scenario_hash: str) -> Optional[tuple[ScenarioSummary, np.ndarray]]:
    """Read from the process-wide cache."""
    return _GLOBAL_CACHE.get(scenario_hash)


def put_cached(
    scenario_hash: str,
    summary: ScenarioSummary,
    arr: np.ndarray,
) -> None:
    """Write to the process-wide cache."""
    _GLOBAL_CACHE.put(scenario_hash, summary, arr)


def cache_stats() -> dict:
    """Return process-wide cache stats."""
    return _GLOBAL_CACHE.stats()


def clear_cache() -> None:
    """Wipe the process-wide cache (intended for tests)."""
    _GLOBAL_CACHE.clear()


# ---------------------------------------------------------------------------
# High-level run + cache helper
# ---------------------------------------------------------------------------
def simulate_and_cache(
    scenario: Scenario,
    *,
    force_refresh: bool = False,
    cache: Optional[ScenarioCache] = None,
) -> tuple[ScenarioSummary, np.ndarray]:
    """Run ``simulate_scenario`` + ``aggregate_trajectories`` with cache.

    Args:
        scenario: the Scenario to run.
        force_refresh: when True, bypasses cache lookup and overwrites.
        cache: optional ScenarioCache override; defaults to the
            module-level ``_GLOBAL_CACHE``.

    Returns:
        ``(ScenarioSummary, ndarray)`` — array shape
        ``(n_samples, n_outcomes, horizon + 1)``.
    """
    cache_obj = cache if cache is not None else _GLOBAL_CACHE
    h = compute_scenario_hash(scenario)

    if not force_refresh:
        hit = cache_obj.get(h)
        if hit is not None:
            return hit

    t0 = time.perf_counter()
    arr = simulate_scenario(scenario)
    summary = aggregate_trajectories(
        arr,
        scenario=scenario,
        elapsed_seconds=time.perf_counter() - t0,
    )
    cache_obj.put(h, summary, arr)
    return summary, arr


__all__ = [
    "ScenarioCache",
    "get_cached",
    "put_cached",
    "cache_stats",
    "clear_cache",
    "simulate_and_cache",
]
