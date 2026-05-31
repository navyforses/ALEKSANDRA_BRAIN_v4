"""Phase 7.3 Day 5 — cache.py tests."""

from __future__ import annotations

import numpy as np

from brain.sim.cache import (
    ScenarioCache,
    simulate_and_cache,
)
from brain.sim.scenario import (
    build_reference_scenario,
    compute_scenario_hash,
)


def _small_scenario():
    return build_reference_scenario().model_copy(update={"n_samples": 10})


# ---------------------------------------------------------------------------
# First call is a miss, second is a hit
# ---------------------------------------------------------------------------
def test_first_call_miss_second_hit():
    cache = ScenarioCache(max_entries=4)
    s = _small_scenario()
    summary1, arr1 = simulate_and_cache(s, cache=cache)
    stats_after_first = cache.stats()
    assert stats_after_first["misses"] == 1
    assert stats_after_first["hits"] == 0
    assert stats_after_first["current_size"] == 1

    summary2, arr2 = simulate_and_cache(s, cache=cache)
    stats_after_second = cache.stats()
    assert stats_after_second["hits"] == 1
    assert stats_after_second["misses"] == 1
    # Returned values identical (same object reference)
    assert summary1 is summary2
    assert np.array_equal(arr1, arr2)


# ---------------------------------------------------------------------------
# force_refresh bypasses cache
# ---------------------------------------------------------------------------
def test_force_refresh_bypasses_cache():
    cache = ScenarioCache(max_entries=4)
    s = _small_scenario()
    simulate_and_cache(s, cache=cache)
    summary1, arr1 = simulate_and_cache(s, cache=cache)  # hit
    summary2, arr2 = simulate_and_cache(s, cache=cache, force_refresh=True)
    # New summary object; arrays identical content (deterministic seed)
    assert summary1 is not summary2
    assert np.array_equal(arr1, arr2)


# ---------------------------------------------------------------------------
# LRU eviction kicks in at max_entries + 1
# ---------------------------------------------------------------------------
def test_lru_eviction_kicks_in():
    cache = ScenarioCache(max_entries=2)
    base = _small_scenario()
    s1 = base.model_copy(update={"horizon_days": 20})
    s2 = base.model_copy(update={"horizon_days": 30})
    s3 = base.model_copy(update={"horizon_days": 40})

    simulate_and_cache(s1, cache=cache)
    simulate_and_cache(s2, cache=cache)
    assert cache.stats()["current_size"] == 2
    simulate_and_cache(s3, cache=cache)
    stats = cache.stats()
    assert stats["current_size"] == 2
    assert stats["evictions"] == 1

    # s1 should have been evicted (LRU); re-run is a miss
    pre_misses = cache.stats()["misses"]
    simulate_and_cache(s1, cache=cache)
    assert cache.stats()["misses"] == pre_misses + 1


# ---------------------------------------------------------------------------
# Cache stats hit_ratio after sequence
# ---------------------------------------------------------------------------
def test_cache_stats_hit_ratio():
    cache = ScenarioCache(max_entries=4)
    s = _small_scenario()
    # 1 miss + 3 hits = hit_ratio 3/4
    simulate_and_cache(s, cache=cache)
    simulate_and_cache(s, cache=cache)
    simulate_and_cache(s, cache=cache)
    simulate_and_cache(s, cache=cache)
    stats = cache.stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 3
    assert abs(stats["hit_ratio"] - 0.75) < 1e-9


# ---------------------------------------------------------------------------
# Cache key is the scenario hash exactly
# ---------------------------------------------------------------------------
def test_cache_key_is_scenario_hash():
    cache = ScenarioCache(max_entries=4)
    s = _small_scenario()
    simulate_and_cache(s, cache=cache)
    expected_hash = compute_scenario_hash(s)
    hit = cache.get(expected_hash)
    assert hit is not None
    summary, arr = hit
    assert summary.scenario_hash == expected_hash


# ---------------------------------------------------------------------------
# clear() resets all counters
# ---------------------------------------------------------------------------
def test_cache_clear_resets():
    cache = ScenarioCache(max_entries=4)
    s = _small_scenario()
    simulate_and_cache(s, cache=cache)
    simulate_and_cache(s, cache=cache)
    cache.clear()
    stats = cache.stats()
    assert stats == {
        "hits": 0,
        "misses": 0,
        "evictions": 0,
        "current_size": 0,
        "hit_ratio": 0.0,
    }
