"""Phase 7.3 Layer B Day 10 -- TVB adapter unit + conditional live tests.

Two test tiers:

  1. **Mocked / pure-Python** (always run): dry-run path, mask helpers,
     compute_seizure_onset_rate, schema validation, DRY_RUN evidence
     write, handler dispatch.
  2. **Conditional live** (marked ``@pytest.mark.skipif(not _DOCKER_OR_IMAGE_AVAILABLE)``):
     real ``docker run`` against ``thevirtualbrain/tvb-run:latest``;
     skipped when Docker or the image is unavailable.

The live test runs a 1-second TVB simulation (NOT the 60-second spec
target -- that's exercised by ``verify_phase_7_3`` check 8). 60-second
sims take ~20-30s wall but each adds a docker pull / image load cost on
cold CI; the 1-second test confirms the full pipeline end-to-end while
keeping the brain/ pytest sweep snappy.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch

import numpy as np
import pytest

from brain.sim.tvb_adapter import (
    TVB_CONTAINER_PREFIX,
    TVB_DEFAULT_REGION_COUNT,
    TVB_IMAGE,
    TVBSimulationError,
    TVBSimulationRequest,
    TVBSimulationResult,
    TVBUnavailableError,
    apply_hie_lesion_mask,
    check_docker_available,
    check_tvb_image_available,
    compute_seizure_onset_rate,
    handle_tvb_simulation_request,
    list_available_connectomes,
    load_default_connectome_metadata,
    record_tvb_simulation_as_evidence,
    run_tvb_simulation,
    synthetic_hie_lesion_mask_for_aleksandra,
)

_DOCKER_OR_IMAGE_AVAILABLE = (
    check_docker_available() and check_tvb_image_available()
)
_SKIP_REASON_LIVE = (
    "Docker daemon or TVB image not available; live TVB test skipped"
)


# ---------------------------------------------------------------------------
# Probe helpers
# ---------------------------------------------------------------------------
def test_check_docker_available_runs_without_throwing() -> None:
    """``check_docker_available`` must always return a bool; never raise."""
    result = check_docker_available()
    assert isinstance(result, bool)


def test_check_tvb_image_available_runs_without_throwing() -> None:
    """Same contract for ``check_tvb_image_available``."""
    result = check_tvb_image_available()
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# compute_seizure_onset_rate
# ---------------------------------------------------------------------------
def test_compute_seizure_onset_rate_zero_for_flat_signal() -> None:
    """Flat signal has zero z-variance and yields rate 0."""
    n_time, n_regions = 100, 4
    activity = np.zeros((n_time, n_regions), dtype=np.float64)
    time_ms = np.linspace(0.0, 1_000.0, n_time)
    rate = compute_seizure_onset_rate(activity, time_ms=time_ms)
    assert rate == 0.0


def test_compute_seizure_onset_rate_detects_spikes() -> None:
    """A signal with deliberate spikes produces a positive per-minute rate."""
    n_time, n_regions = 200, 2
    rng = np.random.default_rng(7)
    activity = rng.normal(0.0, 0.1, size=(n_time, n_regions))
    # Inject 5 spikes per region.
    for r in range(n_regions):
        for ts in (20, 60, 100, 140, 180):
            activity[ts, r] += 5.0
    time_ms = np.linspace(0.0, 1_000.0, n_time)  # 1 second
    rate = compute_seizure_onset_rate(activity, time_ms=time_ms)
    # 5 spikes in 1s per region -> ~300 events/min, but the threshold + z
    # math may detect fewer. Sanity range: positive and below the cap.
    assert rate > 0.0
    assert rate < 1000.0


def test_compute_seizure_onset_rate_handles_empty() -> None:
    assert compute_seizure_onset_rate(np.array([]), time_ms=np.array([])) == 0.0


# ---------------------------------------------------------------------------
# apply_hie_lesion_mask
# ---------------------------------------------------------------------------
def test_apply_hie_lesion_mask_shape() -> None:
    mask = apply_hie_lesion_mask(
        100, cyst_indices=[0, 5, 50, 99], strength=0.7
    )
    assert mask.shape == (100,)
    assert mask[0] == pytest.approx(0.7)
    assert mask[5] == pytest.approx(0.7)
    assert mask[50] == pytest.approx(0.7)
    assert mask[99] == pytest.approx(0.7)
    # Untouched indices stay zero.
    assert mask[1] == 0.0
    assert int((mask > 0).sum()) == 4


def test_apply_hie_lesion_mask_out_of_range_clamped(capsys) -> None:
    """Out-of-range indices are skipped + warned, not raised."""
    mask = apply_hie_lesion_mask(
        10, cyst_indices=[3, 10, -1, 99], strength=0.4
    )
    # Only index 3 is in [0, 10).
    assert mask[3] == pytest.approx(0.4)
    assert int((mask > 0).sum()) == 1
    captured = capsys.readouterr()
    assert "out of range" in captured.err


def test_apply_hie_lesion_mask_strength_clamped() -> None:
    """Strength above 1.0 is clamped to 1.0."""
    mask = apply_hie_lesion_mask(5, cyst_indices=[0], strength=99.0)
    assert mask[0] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# synthetic_hie_lesion_mask_for_aleksandra
# ---------------------------------------------------------------------------
def test_synthetic_hie_lesion_mask_deterministic() -> None:
    """Same input -> same output (hash-seeded RNG)."""
    a = synthetic_hie_lesion_mask_for_aleksandra(998)
    b = synthetic_hie_lesion_mask_for_aleksandra(998)
    assert np.array_equal(a, b)


def test_synthetic_hie_lesion_mask_about_10pct() -> None:
    """~10% of regions inhibited (allow +/- 1 for integer division)."""
    mask = synthetic_hie_lesion_mask_for_aleksandra(998)
    n_inhibited = int((mask > 0).sum())
    expected = 998 // 10  # 99
    assert n_inhibited == expected
    # Strength is 0.4 per docstring.
    assert mask[mask > 0][0] == pytest.approx(0.4)


def test_synthetic_hie_lesion_mask_small_region_count() -> None:
    """Mask is at least 1 inhibited region even for tiny connectomes."""
    mask = synthetic_hie_lesion_mask_for_aleksandra(5)
    assert int((mask > 0).sum()) >= 1


# ---------------------------------------------------------------------------
# TVBSimulationRequest schema
# ---------------------------------------------------------------------------
def test_tvb_simulation_request_validates() -> None:
    req = TVBSimulationRequest(
        duration_ms=1_000, region_count=76, model_name="WilsonCowan"
    )
    assert req.duration_ms == 1_000
    assert req.region_count == 76
    assert req.model_name == "WilsonCowan"


def test_tvb_simulation_request_rejects_extra_fields() -> None:
    with pytest.raises(Exception):  # pydantic.ValidationError
        TVBSimulationRequest(duration_ms=1_000, unexpected_field="x")


def test_tvb_simulation_request_rejects_oversize_duration() -> None:
    with pytest.raises(Exception):
        TVBSimulationRequest(duration_ms=400_000)  # > 5 min sim time


def test_tvb_simulation_request_rejects_negative_index() -> None:
    with pytest.raises(Exception):
        TVBSimulationRequest(
            duration_ms=1_000, inhibited_region_indices=[5, -1, 7]
        )


# ---------------------------------------------------------------------------
# Dry-run simulation path
# ---------------------------------------------------------------------------
def test_dry_run_simulation_returns_valid_result() -> None:
    req = TVBSimulationRequest(duration_ms=1_000, region_count=20)
    result = run_tvb_simulation(req, dry_run=True)
    assert isinstance(result, TVBSimulationResult)
    assert len(result.time_ms) > 0
    assert len(result.region_activity) > 0
    assert result.container_id == "DRY_RUN"
    assert result.wall_time_seconds < 1.0
    # Synthetic path injects spikes, so rate must be positive.
    assert result.seizure_onset_rate_per_min > 0.0
    assert result.notes and result.notes[0].startswith("DRY_RUN")


def test_run_tvb_simulation_dry_run_no_docker_calls() -> None:
    """Verify ``dry_run=True`` short-circuits before any subprocess call."""
    req = TVBSimulationRequest(duration_ms=1_000)
    with patch("brain.sim.tvb_adapter.subprocess.run") as mock_run:
        result = run_tvb_simulation(req, dry_run=True)
        assert mock_run.call_count == 0
    assert result.container_id == "DRY_RUN"


def test_tvb_unavailable_error_when_image_missing() -> None:
    """Docker reachable + image missing + dry_run=False -> TVBUnavailableError."""
    req = TVBSimulationRequest(duration_ms=1_000)
    with patch(
        "brain.sim.tvb_adapter.check_docker_available", return_value=True
    ), patch(
        "brain.sim.tvb_adapter.check_tvb_image_available", return_value=False
    ):
        with pytest.raises(TVBUnavailableError):
            run_tvb_simulation(req, dry_run=False)


def test_run_tvb_simulation_falls_back_to_dry_run_when_docker_missing() -> None:
    """Docker daemon unreachable -> synthetic result (no exception)."""
    req = TVBSimulationRequest(duration_ms=1_000)
    with patch(
        "brain.sim.tvb_adapter.check_docker_available", return_value=False
    ):
        result = run_tvb_simulation(req, dry_run=False)
    assert result.container_id == "DRY_RUN"


# ---------------------------------------------------------------------------
# handler dispatch
# ---------------------------------------------------------------------------
def test_handle_tvb_simulation_request_dry_run() -> None:
    payload: dict = {
        "duration_ms": 500,
        "region_count": 10,
        "dry_run": True,
    }
    out = handle_tvb_simulation_request(payload)
    assert isinstance(out, dict)
    assert "seizure_onset_rate_per_min" in out
    assert "region_activity" in out
    assert out["container_id"] == "DRY_RUN"
    # Output must be JSON-safe.
    json.dumps(out)


def test_handle_tvb_simulation_request_rejects_invalid_payload() -> None:
    with pytest.raises(Exception):  # ValidationError or RuntimeError
        handle_tvb_simulation_request(
            {"duration_ms": 5, "dry_run": True}  # below ge=10
        )


# ---------------------------------------------------------------------------
# Day 10 -- belief evidence cross-link
# ---------------------------------------------------------------------------
def test_record_tvb_simulation_as_evidence_dry_run(monkeypatch) -> None:
    """DRY_RUN sentinel when SUPABASE_DB_URL is unset."""
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    req = TVBSimulationRequest(duration_ms=1_000, region_count=20)
    result = run_tvb_simulation(req, dry_run=True)
    sentinel = record_tvb_simulation_as_evidence(
        result=result,
        source_ref="tvb_test_run",
        observed_at=datetime(2026, 5, 25, tzinfo=timezone.utc),
    )
    assert sentinel.startswith("DRY_RUN:")
    # Hash is deterministic for the same (dim, source, ref, value).
    sentinel_2 = record_tvb_simulation_as_evidence(
        result=result,
        source_ref="tvb_test_run",
        observed_at=datetime(2026, 5, 25, tzinfo=timezone.utc),
    )
    assert sentinel == sentinel_2


def test_record_tvb_simulation_as_evidence_rejects_bad_floor() -> None:
    req = TVBSimulationRequest(duration_ms=1_000)
    result = run_tvb_simulation(req, dry_run=True)
    with pytest.raises(ValueError):
        record_tvb_simulation_as_evidence(
            result=result, confidence_floor=2.0
        )


# ---------------------------------------------------------------------------
# Day 7 -- connectome adapter (DRY_RUN-safe)
# ---------------------------------------------------------------------------
def test_list_available_connectomes_returns_zip_names() -> None:
    """Always returns a list of .zip filenames (live or DRY_RUN)."""
    names = list_available_connectomes()
    assert isinstance(names, list)
    if names:  # live or DRY_RUN both populate
        for n in names:
            assert n.endswith(".zip")


def test_load_default_connectome_metadata_shape() -> None:
    meta = load_default_connectome_metadata()
    assert meta["region_count"] == TVB_DEFAULT_REGION_COUNT
    assert meta["filename"] == f"connectivity_{TVB_DEFAULT_REGION_COUNT}.zip"
    assert "Hagmann" in meta["source"]
    assert "TODO" in meta["source"]


def test_constants_match_dispatch_contract() -> None:
    assert TVB_IMAGE == "thevirtualbrain/tvb-run:latest"
    assert TVB_DEFAULT_REGION_COUNT == 998
    assert TVB_CONTAINER_PREFIX == "tvb-aleksandra-"


# ---------------------------------------------------------------------------
# Live TVB Docker tests (skip when Docker / image absent)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    not _DOCKER_OR_IMAGE_AVAILABLE, reason=_SKIP_REASON_LIVE
)
def test_live_tvb_simulation_1_second_completes() -> None:
    """Real Docker round-trip: 1-second TVB sim on 76 regions completes
    fast (smoke baseline ~14 s including container startup)."""
    req = TVBSimulationRequest(
        duration_ms=1_000, region_count=76, model_name="Generic2dOscillator"
    )
    result = run_tvb_simulation(req, dry_run=False)
    assert result.wall_time_seconds < 300.0
    assert len(result.region_activity) > 0
    assert len(result.time_ms) > 0
    assert result.container_id.startswith(TVB_CONTAINER_PREFIX)
    assert result.container_id != "DRY_RUN"
