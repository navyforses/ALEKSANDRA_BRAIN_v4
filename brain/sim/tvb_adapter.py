"""Phase 7.3 Layer B — TheVirtualBrain (TVB) Docker neural-mass simulation.

This module wraps the ``thevirtualbrain/tvb-run:latest`` Docker container in
a synchronous, framework-agnostic Python API that mirrors the Layer A /
Layer C surfaces (Pydantic request + result, DRY_RUN fallback, deterministic
hashing, framework-agnostic handler).

Days 6-10 surface (single-module budget per Phase 7.3 spec §2.1 ~320 LOC):

  * Day 6  -- container bootstrap: ``check_docker_available``,
            ``check_tvb_image_available``, ``run_tvb_simulation``
  * Day 7  -- connectome adapter: ``list_available_connectomes``,
            ``load_default_connectome_metadata``
  * Day 8  -- HIE lesion-mask region inhibition:
            ``apply_hie_lesion_mask``,
            ``synthetic_hie_lesion_mask_for_aleksandra``
  * Day 9  -- simulation API: ``handle_tvb_simulation_request``
  * Day 10 -- TVB -> belief feedback: ``record_tvb_simulation_as_evidence``

Hard rules (CLAUDE.md + dispatch):

  * **No PHI**. Aleksandra's MRI is client-side only. The HIE lesion mask
    is SYNTHETIC -- a hash-deterministic 998-element binary inhibition
    vector. Do NOT replace ``synthetic_hie_lesion_mask_for_aleksandra``
    with a real per-patient mask server-side.
  * **No fabricated facts.** The 998-region connectivity inside the TVB
    image is the Hagmann 998-region connectome (Hagmann et al. PLoS Biol
    2008 -- citation in spec §8.2; no PMID grounded in this repo yet,
    flagged with a TODO marker rather than guessed).
  * **Sync only**, no asyncio; one short-lived ``docker run --rm``
    container per simulation; auto-cleanup via ``--rm`` and
    ``tempfile.TemporaryDirectory``.
  * **5-min wall-time cap** per simulation (``timeout=300``); raises
    :class:`TVBSimulationTimeout`.
  * **DRY_RUN fallback** when Docker is unreachable or the caller passes
    ``dry_run=True`` -- returns a deterministic synthetic result that
    callers can verify in unit tests without Docker.

Container invocation pattern (the TVB image ships under
``/home/tvb-root/`` and requires both conda activation and the in-tree
``activate.sh`` PYTHONPATH bootstrap before ``from tvb.simulator.lab
import *`` works):

    docker run --rm --name tvb-aleksandra-<uuid> \\
        -v <tmpdir>:/work \\
        thevirtualbrain/tvb-run:latest \\
        bash -c "source /opt/conda/etc/profile.d/conda.sh \\
                 && conda activate tvb-run \\
                 && cd /home/tvb-root/tvb_bin && source ./activate.sh \\
                 && python /work/run.py"

Reference:
  * v7_architecture/70_PHASES/73_PHASE_7_3_SIMULATION_ENGINE_3W.md §1
    Layer B (Days 6-10), §2.1 LOC budget, §4 checks 7/8/9.
  * brain/causal/cross_link.py (mirrored Day 10 belief-evidence pattern).
  * brain/sim/persistence.py (mirrored DRY_RUN-when-DSN-unset contract).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator

from brain.belief.persistence import (
    BeliefEvidence,
    compute_evidence_hash,
    write_evidence,
)
from brain.belief.schema import load_dimensions_from_toml


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TVB_IMAGE = "thevirtualbrain/tvb-run:latest"
"""Docker image tag. Spec called for ``2.9.x``; the locally-pulled image is
``latest`` (TVB 2.11.0). The upstream image is flagged
``Updates discontinued after version 26.7.x`` in its DockerHub readme --
this is a documented deviation; tracked as MVP carry-forward."""

TVB_DEFAULT_REGION_COUNT = 998
"""Hagmann 998-region connectome. The TVB image ships
``connectivity_998.zip`` alongside the 76/80/96/192-region defaults; the
998-region file is the spec-mandated connectome and is selected by default
inside the container script."""

TVB_CONTAINER_PREFIX = "tvb-aleksandra-"
"""Prefix for spawned container names. Tests confirm post-run
``docker ps --filter name=tvb-aleksandra-`` is empty (containers are
``--rm`` self-deleting)."""

TVB_SIMULATION_TIMEOUT_S = 300
"""Hard wall-time cap per spec §4 check 8 (60-second sim must complete
within 5 minutes wall)."""

_MAX_REGION_ACTIVITY_TIME_POINTS = 100
"""JSON-size guard on returned ``region_activity`` matrix."""

_MAX_REGION_ACTIVITY_REGIONS = 32
"""JSON-size guard on returned ``region_activity`` matrix."""

_ALLOWED_MODELS = ("Generic2dOscillator", "WilsonCowan", "JansenRit")


# ---------------------------------------------------------------------------
# Custom errors
# ---------------------------------------------------------------------------
class TVBUnavailableError(RuntimeError):
    """Raised when Docker is reachable but the TVB image is missing
    (or when Docker itself is unreachable AND ``dry_run=False``)."""


class TVBSimulationTimeout(RuntimeError):
    """Raised when ``run_tvb_simulation`` exceeds
    :data:`TVB_SIMULATION_TIMEOUT_S` wall."""


class TVBSimulationError(RuntimeError):
    """Raised when the in-container TVB script exits non-zero."""


# ---------------------------------------------------------------------------
# Pydantic request / result
# ---------------------------------------------------------------------------
class TVBSimulationRequest(BaseModel):
    """One TVB simulation request.

    Fields:
        duration_ms: simulation length in TVB-internal milliseconds (NOT
            wall time), capped at 5 min sim time.
        region_count: 2..998; clamped to the connectivity file that
            actually loads (currently 76 default + 998 Hagmann).
        inhibited_region_indices: HIE lesion mask -- region indices whose
            outgoing weights get scaled by ``(1 - inhibition_strength)``.
        inhibition_strength: 0=no effect, 1=fully silenced.
        perturbations: free-form dict forwarded to the container script;
            currently supports ``stimulus_region`` and
            ``stimulus_amplitude`` (TVB stimulus pulse).
        random_seed: numpy RNG seed for the dry-run synthetic path AND for
            the in-container TVB integrator; defaults to 7.
        model_name: TVB neural-mass model class name; restricted to the
            three that ship inside the image: Generic2dOscillator (default,
            fastest), WilsonCowan, JansenRit.
    """

    model_config = ConfigDict(extra="forbid")

    duration_ms: int = Field(..., ge=10, le=300_000)
    region_count: int = Field(default=998, ge=2, le=998)
    inhibited_region_indices: list[int] = Field(default_factory=list)
    inhibition_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    perturbations: dict[str, Any] = Field(default_factory=dict)
    random_seed: Optional[int] = 7
    model_name: Literal[
        "Generic2dOscillator", "WilsonCowan", "JansenRit"
    ] = "Generic2dOscillator"

    @field_validator("inhibited_region_indices")
    @classmethod
    def _indices_non_negative(cls, v: list[int]) -> list[int]:
        bad = [i for i in v if i < 0]
        if bad:
            raise ValueError(
                f"inhibited_region_indices must be >=0; got {bad}"
            )
        return v


class TVBSimulationResult(BaseModel):
    """One TVB simulation result. JSON-safe (region_activity is truncated
    to :data:`_MAX_REGION_ACTIVITY_TIME_POINTS` x
    :data:`_MAX_REGION_ACTIVITY_REGIONS`)."""

    model_config = ConfigDict(extra="forbid")

    request: TVBSimulationRequest
    time_ms: list[float]
    region_activity: list[list[float]]
    seizure_onset_rate_per_min: float
    wall_time_seconds: float
    container_id: str
    model_name: str
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Day 6 -- Docker / image availability probes
# ---------------------------------------------------------------------------
def check_docker_available() -> bool:
    """Return True if ``docker version`` exits 0 within 10 s."""
    docker = shutil.which("docker")
    if docker is None:
        return False
    try:
        r = subprocess.run(
            [docker, "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    return r.returncode == 0 and bool(r.stdout.strip())


def check_tvb_image_available() -> bool:
    """Return True if ``docker images -q TVB_IMAGE`` returns a non-empty
    image ID. Returns False if Docker itself is unreachable."""
    docker = shutil.which("docker")
    if docker is None:
        return False
    try:
        r = subprocess.run(
            [docker, "images", "-q", TVB_IMAGE],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    return r.returncode == 0 and bool(r.stdout.strip())


# ---------------------------------------------------------------------------
# Day 7 -- Connectome adapter
# ---------------------------------------------------------------------------
def list_available_connectomes() -> list[str]:
    """Return the list of connectivity zip filenames bundled in the TVB
    image. DRY_RUN value (when Docker unavailable) lists the seven we
    confirmed by smoke probe: 66/68/76/80/96/192/998 regions."""
    if not check_docker_available() or not check_tvb_image_available():
        return [
            "connectivity_66.zip",
            "connectivity_68.zip",
            "connectivity_76.zip",
            "connectivity_80.zip",
            "connectivity_96.zip",
            "connectivity_192.zip",
            "connectivity_998.zip",
        ]
    docker = shutil.which("docker")
    assert docker is not None  # narrow for type-checkers
    probe = (
        "import os; "
        "p='/home/tvb_data/tvb_data/connectivity'; "
        "print('|'.join(sorted(f for f in os.listdir(p) if f.endswith('.zip'))))"
    )
    try:
        r = subprocess.run(
            [docker, "run", "--rm", TVB_IMAGE, "python", "-c", probe],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    if r.returncode != 0:
        return []
    last = (r.stdout or "").strip().splitlines()
    if not last:
        return []
    return last[-1].split("|")


def load_default_connectome_metadata() -> dict[str, Any]:
    """Return metadata about the connectome the adapter selects by
    default. Spec-mandated default is the Hagmann 998-region connectome.

    Citation: Hagmann P. et al., PLoS Biology 2008. PMID not yet grounded
    in this repo -- TODO marker rather than guess (per dispatch rules)."""
    return {
        "region_count": TVB_DEFAULT_REGION_COUNT,
        "filename": f"connectivity_{TVB_DEFAULT_REGION_COUNT}.zip",
        "source": (
            "Hagmann et al. PLoS Biology 2008 "
            "(998-region whole-brain connectome). "
            "TODO(citation): PMID not yet grounded in repo."
        ),
        "deviation_note": (
            "TVB image's connectivity_998.zip emits readers WARNINGs about "
            "missing 'average_orientations', 'cortical' and 'hemispheres' "
            "files. Those fields are not required for Generic2dOscillator "
            "/ WilsonCowan / JansenRit simulations; the warnings are "
            "benign and reproducible."
        ),
    }


# ---------------------------------------------------------------------------
# Day 8 -- HIE lesion mask
# ---------------------------------------------------------------------------
def apply_hie_lesion_mask(
    region_count: int,
    *,
    cyst_indices: list[int],
    strength: float = 0.5,
) -> np.ndarray:
    """Build an inhibition mask vector for use as ``weights *= (1 - mask)``.

    Args:
        region_count: number of regions in the loaded connectivity.
        cyst_indices: region indices to inhibit. Out-of-range indices are
            clamped (warned to stderr) -- this is permissive by design so
            the caller does not need to re-validate after a connectome
            switch.
        strength: 0=no inhibition, 1=fully silenced. Clamped to [0, 1].

    Returns:
        1-D float ndarray of length ``region_count`` with ``strength`` at
        every clamped-in-range index and 0 elsewhere.
    """
    if region_count < 1:
        raise ValueError(f"region_count must be >=1; got {region_count}")
    strength = float(max(0.0, min(1.0, strength)))
    mask = np.zeros(region_count, dtype=np.float64)
    out_of_range: list[int] = []
    for idx in cyst_indices:
        if 0 <= idx < region_count:
            mask[idx] = strength
        else:
            out_of_range.append(int(idx))
    if out_of_range:
        print(
            f"[tvb_adapter] apply_hie_lesion_mask: {len(out_of_range)} "
            f"index/indices out of range [0, {region_count}); skipping: "
            f"{out_of_range[:10]}{'...' if len(out_of_range) > 10 else ''}",
            file=sys.stderr,
        )
    return mask


_SYNTHETIC_MASK_SEED_TOKEN = "aleksandra-hie-synthetic-2026"


def synthetic_hie_lesion_mask_for_aleksandra(
    region_count: int = TVB_DEFAULT_REGION_COUNT,
) -> np.ndarray:
    """Return a HAND-CURATED SYNTHETIC HIE lesion mask placeholder.

    Real Aleksandra MRI segmentation is client-side-only per CLAUDE.md
    privacy rule; do NOT replace this function with a per-patient mask
    server-side. The mask is hash-seeded on the literal token
    :data:`_SYNTHETIC_MASK_SEED_TOKEN` so the same call returns the same
    vector across runs (deterministic) without claiming anatomical
    validity for any specific patient.

    Coverage: ~10% of regions inhibited at strength 0.4.

    Returns:
        1-D float ndarray of length ``region_count``.
    """
    seed = int.from_bytes(
        hashlib.sha256(_SYNTHETIC_MASK_SEED_TOKEN.encode("utf-8")).digest()[:8],
        "big",
    ) % (2**32)
    rng = np.random.default_rng(seed)
    n_inhibited = max(1, region_count // 10)
    indices = rng.choice(region_count, size=n_inhibited, replace=False).tolist()
    return apply_hie_lesion_mask(
        region_count, cyst_indices=indices, strength=0.4
    )


# ---------------------------------------------------------------------------
# Day 9 -- Simulation API
# ---------------------------------------------------------------------------
def compute_seizure_onset_rate(
    region_activity: np.ndarray,
    *,
    time_ms: np.ndarray,
    threshold_z: float = 3.0,
    min_inter_spike_ms: float = 50.0,
) -> float:
    """Estimate seizure-onset rate (events / minute) from region activity.

    Per-region z-score; count above-threshold peaks separated by at least
    ``min_inter_spike_ms``; average across regions; convert to per-minute
    rate using the elapsed time-span. Returns 0.0 for empty / degenerate
    input.

    Args:
        region_activity: 2-D ndarray of shape ``(n_time, n_regions)``.
        time_ms: 1-D ndarray of sampling times in milliseconds, length
            ``n_time``.
        threshold_z: per-region z-score threshold for spike detection.
        min_inter_spike_ms: refractory window between counted spikes.
    """
    arr = np.asarray(region_activity, dtype=np.float64)
    if arr.size == 0 or arr.ndim != 2:
        return 0.0
    t = np.asarray(time_ms, dtype=np.float64)
    if t.size < 2 or arr.shape[0] != t.size:
        return 0.0
    duration_ms = float(t[-1] - t[0])
    if duration_ms <= 0.0:
        return 0.0
    duration_min = duration_ms / 60_000.0
    dt_ms = duration_ms / max(1, t.size - 1)
    refractory_samples = max(1, int(round(min_inter_spike_ms / dt_ms)))

    mu = arr.mean(axis=0, keepdims=True)
    sigma = arr.std(axis=0, keepdims=True)
    sigma = np.where(sigma < 1e-12, 1.0, sigma)
    z = (arr - mu) / sigma

    total_spikes = 0
    n_regions = arr.shape[1]
    for r in range(n_regions):
        above = z[:, r] > threshold_z
        if not above.any():
            continue
        last_spike_idx = -refractory_samples - 1
        for i in np.where(above)[0]:
            if i - last_spike_idx >= refractory_samples:
                total_spikes += 1
                last_spike_idx = int(i)
    avg_spikes_per_region = total_spikes / float(n_regions)
    return float(avg_spikes_per_region / duration_min)


# In-container TVB script template. The TVB image requires conda + an
# in-tree PYTHONPATH activator before ``from tvb.simulator.lab import *``
# works, so the host wraps this script with a bash one-liner; the script
# itself is plain Python and prints a single ``TVBOUT:<json>`` line on
# stdout for the host to parse.
_TVB_RUN_SCRIPT_TEMPLATE = r"""
import json, sys, time
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from tvb.simulator.lab import (
    connectivity, models, simulator, monitors, coupling, integrators,
)

params = json.loads(r'''__PARAMS_JSON__''')
duration_ms = float(params["duration_ms"])
region_count_requested = int(params["region_count"])
inhibited = list(params.get("inhibited_region_indices", []))
inhibition_strength = float(params.get("inhibition_strength", 0.5))
model_name = str(params.get("model_name", "Generic2dOscillator"))
seed = params.get("random_seed", 7)
if seed is not None:
    np.random.seed(int(seed))

# Connectome selection -- prefer the requested region count; fall back to 76
# if the larger file is missing for any reason (smoke confirmed 998 exists).
candidates = [
    f"connectivity_{region_count_requested}.zip",
    "connectivity_76.zip",
]
conn = None
chosen = None
for fname in candidates:
    try:
        conn = connectivity.Connectivity.from_file(fname)
        chosen = fname
        break
    except Exception:
        continue
if conn is None:
    print("TVBOUT:" + json.dumps({"error": "no connectome loaded"}))
    sys.exit(2)
conn.configure()
actual_regions = int(conn.number_of_regions)

# Apply HIE lesion mask -- damp outgoing weights for inhibited regions.
if inhibited:
    mask = np.zeros(actual_regions, dtype=np.float64)
    for idx in inhibited:
        if 0 <= int(idx) < actual_regions:
            mask[int(idx)] = inhibition_strength
    # Apply column-wise so OUTGOING weights of inhibited regions are damped.
    conn.weights = conn.weights * (1.0 - mask[np.newaxis, :])

model_cls = {
    "Generic2dOscillator": models.Generic2dOscillator,
    "WilsonCowan": models.WilsonCowan,
    "JansenRit": models.JansenRit,
}[model_name]

sim = simulator.Simulator(
    model=model_cls(),
    connectivity=conn,
    coupling=coupling.Linear(a=np.array([0.0152])),
    integrator=integrators.HeunDeterministic(dt=0.5),
    monitors=(monitors.TemporalAverage(period=1.0),),
)
sim.configure()

t0 = time.time()
(t_arr, data), = sim.run(simulation_length=duration_ms)
inner_wall = time.time() - t0

# data shape: (n_time, n_state_vars, n_regions, n_modes); take first state var, first mode.
ts = np.asarray(t_arr, dtype=float)
activity = np.asarray(data[:, 0, :, 0], dtype=float)

# Down-sample for JSON budget: target <=100 time-points * <=32 regions.
n_time, n_regions = activity.shape
if n_time > 100:
    stride = max(1, n_time // 100)
    ts_out = ts[::stride][:100]
    activity_out = activity[::stride, :][:100, :]
else:
    ts_out = ts
    activity_out = activity
if n_regions > 32:
    region_stride = max(1, n_regions // 32)
    activity_out = activity_out[:, ::region_stride][:, :32]

payload = {
    "actual_regions": actual_regions,
    "connectome_filename": chosen,
    "model_name": model_name,
    "inner_wall_seconds": round(inner_wall, 3),
    "time_ms": ts_out.tolist(),
    "region_activity": activity_out.tolist(),
}
print("TVBOUT:" + json.dumps(payload))
""".strip()


def _build_in_container_script(req: TVBSimulationRequest) -> str:
    """Materialise the in-container Python script with request-specific
    parameters substituted in.

    JSON-payload substitution rather than f-string interpolation so the
    template stays valid Python on the host side (no curly-brace
    escaping)."""
    params = {
        "duration_ms": int(req.duration_ms),
        "region_count": int(req.region_count),
        "inhibited_region_indices": list(req.inhibited_region_indices),
        "inhibition_strength": float(req.inhibition_strength),
        "model_name": str(req.model_name),
        "random_seed": req.random_seed,
    }
    return _TVB_RUN_SCRIPT_TEMPLATE.replace(
        "__PARAMS_JSON__", json.dumps(params)
    )


def _dry_run_result(
    req: TVBSimulationRequest, reason: str
) -> TVBSimulationResult:
    """Synthetic result for dry-run / Docker-unavailable callers.

    Sinusoidal region activity with deterministic spike injections so that
    :func:`compute_seizure_onset_rate` returns a non-trivial positive
    rate. Effective inhibition factor reduces the synthetic rate."""
    rng = np.random.default_rng(req.random_seed or 7)
    n_time = min(_MAX_REGION_ACTIVITY_TIME_POINTS, max(2, req.duration_ms // 10))
    n_regions = min(_MAX_REGION_ACTIVITY_REGIONS, req.region_count)
    time_ms = np.linspace(0.0, float(req.duration_ms), n_time)
    base = np.sin(2 * np.pi * time_ms[:, None] / 200.0)  # ~5 Hz
    noise = rng.normal(0.0, 0.05, size=(n_time, n_regions))
    activity = base + noise
    # Inject one spike per region every ~200 ms.
    for r in range(n_regions):
        for spike_t in range(50, n_time, 20):
            activity[spike_t, r] += 5.0
    inhibition_factor = 1.0 - (
        req.inhibition_strength * min(1.0, len(req.inhibited_region_indices) / 10.0)
    )
    raw_rate = compute_seizure_onset_rate(
        activity, time_ms=time_ms, threshold_z=3.0, min_inter_spike_ms=50.0
    )
    return TVBSimulationResult(
        request=req,
        time_ms=time_ms.tolist(),
        region_activity=activity.tolist(),
        seizure_onset_rate_per_min=float(raw_rate * inhibition_factor),
        wall_time_seconds=0.01,
        container_id="DRY_RUN",
        model_name=req.model_name,
        notes=[f"DRY_RUN synthetic result: {reason}"],
    )


def run_tvb_simulation(
    req: TVBSimulationRequest,
    *,
    dry_run: bool = False,
) -> TVBSimulationResult:
    """Run one TVB simulation via ``docker run --rm``.

    Args:
        req: typed :class:`TVBSimulationRequest`.
        dry_run: when True (or when Docker is unreachable), return a
            synthetic result without invoking Docker.

    Raises:
        TVBUnavailableError: Docker is reachable but the TVB image is
            missing and ``dry_run`` is False.
        TVBSimulationTimeout: the in-container script exceeded
            :data:`TVB_SIMULATION_TIMEOUT_S` wall.
        TVBSimulationError: the in-container script exited non-zero or
            produced no parseable ``TVBOUT:`` line.
    """
    if dry_run:
        return _dry_run_result(req, reason="dry_run=True")
    if not check_docker_available():
        return _dry_run_result(req, reason="docker daemon not reachable")
    if not check_tvb_image_available():
        raise TVBUnavailableError(
            f"TVB image {TVB_IMAGE!r} not pulled; "
            f"run: docker pull {TVB_IMAGE}"
        )

    docker = shutil.which("docker")
    assert docker is not None  # narrow for type-checkers
    container_name = f"{TVB_CONTAINER_PREFIX}{uuid.uuid4().hex[:8]}"
    script_src = _build_in_container_script(req)

    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "run.py").write_text(script_src, encoding="utf-8")
        bash_cmd = (
            "source /opt/conda/etc/profile.d/conda.sh "
            "&& conda activate tvb-run "
            "&& cd /home/tvb-root/tvb_bin && source ./activate.sh "
            "&& python /work/run.py"
        )
        cmd = [
            docker, "run", "--rm",
            "--name", container_name,
            "-v", f"{td}:/work",
            TVB_IMAGE,
            "bash", "-c", bash_cmd,
        ]
        t0 = time.time()
        try:
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TVB_SIMULATION_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            # Best-effort cleanup; --rm will reap when stop returns.
            subprocess.run(
                [docker, "stop", container_name],
                capture_output=True, timeout=15, check=False,
            )
            raise TVBSimulationTimeout(
                f"TVB simulation exceeded {TVB_SIMULATION_TIMEOUT_S}s wall "
                f"(container={container_name}, duration_ms={req.duration_ms})"
            ) from exc
        wall = time.time() - t0
        if r.returncode != 0:
            tail = (r.stderr or "")[-400:]
            raise TVBSimulationError(
                f"TVB container exit={r.returncode} "
                f"(container={container_name}); stderr tail: {tail}"
            )
        payload_line = next(
            (
                line for line in (r.stdout or "").splitlines()
                if line.startswith("TVBOUT:")
            ),
            None,
        )
        if payload_line is None:
            tail = (r.stdout or "")[-300:]
            raise TVBSimulationError(
                f"no TVBOUT line in container stdout "
                f"(container={container_name}); stdout tail: {tail}"
            )
        payload = json.loads(payload_line[len("TVBOUT:"):])
        if "error" in payload:
            raise TVBSimulationError(
                f"container reported error: {payload['error']}"
            )

    time_ms_arr = np.asarray(payload["time_ms"], dtype=np.float64)
    activity_arr = np.asarray(payload["region_activity"], dtype=np.float64)
    onset_rate = compute_seizure_onset_rate(
        activity_arr,
        time_ms=time_ms_arr,
        threshold_z=3.0,
        min_inter_spike_ms=50.0,
    )
    notes = [
        f"connectome_file={payload.get('connectome_filename')}",
        f"actual_regions={payload.get('actual_regions')}",
        f"inner_wall_seconds={payload.get('inner_wall_seconds')}",
    ]
    return TVBSimulationResult(
        request=req,
        time_ms=time_ms_arr.tolist(),
        region_activity=activity_arr.tolist(),
        seizure_onset_rate_per_min=float(onset_rate),
        wall_time_seconds=round(float(wall), 3),
        container_id=container_name,
        model_name=str(payload.get("model_name", req.model_name)),
        notes=notes,
    )


def handle_tvb_simulation_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Framework-agnostic handler for HTTP/CLI front-ends.

    Validates the payload against :class:`TVBSimulationRequest`, runs the
    simulation (honouring ``dry_run`` if present at the top level of the
    payload), and returns the JSON-safe ``model_dump()`` of the result."""
    flag_dry_run = bool(payload.pop("dry_run", False))
    req = TVBSimulationRequest(**payload)
    result = run_tvb_simulation(req, dry_run=flag_dry_run)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Day 10 -- TVB -> belief feedback
# ---------------------------------------------------------------------------
_SEIZURE_DIM_NAME = "seizure_freq_per_day"


def _resolve_seizure_dim_id() -> int:
    """Resolve the ``seizure_freq_per_day`` dimension id from the TOML
    catalog (no DB call). Falls back to id=3 (its position in the
    spec-mandated 13-D catalog) if the resolver cannot find the name."""
    try:
        dims = load_dimensions_from_toml()
    except Exception:  # pragma: no cover -- defensive
        return 3
    for i, dim in enumerate(dims, start=1):
        if dim.name == _SEIZURE_DIM_NAME:
            return i
    return 3


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def record_tvb_simulation_as_evidence(
    *,
    result: TVBSimulationResult,
    target_dimension_id: Optional[int] = None,
    source_ref: Optional[str] = None,
    observed_at: Optional[datetime] = None,
    confidence_floor: float = 0.3,
) -> str:
    """Persist a TVB simulation result as a ``belief_evidence`` row.

    Mirrors :func:`brain.causal.cross_link.record_causal_estimate_as_evidence`:

      * source = ``"tvb_sim"`` (whitelisted in
        :data:`brain.belief.persistence.ALLOWED_EVIDENCE_SOURCES`).
      * Deterministic ``compute_evidence_hash``-keyed idempotency.
      * Returns ``"DRY_RUN:<hash>"`` when ``SUPABASE_DB_URL`` is unset.

    Confidence heuristic: longer wall times -> noisier estimate ->
    lower confidence. Floor: ``confidence_floor``. Ceiling: 0.85.
    """
    if not (0.0 <= confidence_floor <= 1.0):
        raise ValueError(
            f"confidence_floor must lie in [0, 1]; got {confidence_floor!r}"
        )
    dim_id = (
        int(target_dimension_id)
        if target_dimension_id is not None
        else _resolve_seizure_dim_id()
    )
    ref = source_ref or f"tvb_run_{result.container_id}"
    when = observed_at or datetime.now(timezone.utc)

    value: dict[str, Any] = {
        "seizure_onset_rate_per_min": float(result.seizure_onset_rate_per_min),
        "duration_ms": int(result.request.duration_ms),
        "region_count": int(result.request.region_count),
        "wall_time_seconds": float(result.wall_time_seconds),
        "model_name": str(result.model_name),
        "container_id": str(result.container_id),
    }
    confidence = _clip(
        0.5 - 0.001 * float(result.wall_time_seconds),
        confidence_floor,
        0.85,
    )
    evidence_hash = compute_evidence_hash(
        dim_id, "tvb_sim", ref, value
    )

    if not os.environ.get("SUPABASE_DB_URL"):
        sentinel = f"DRY_RUN:{evidence_hash}"
        print(
            "[tvb_adapter] SUPABASE_DB_URL unset -- skipping write_evidence; "
            f"returning {sentinel}",
            file=sys.stderr,
        )
        return sentinel

    ev = BeliefEvidence(
        dimension_id=dim_id,
        source="tvb_sim",
        source_ref=ref,
        value=value,
        evidence_hash=evidence_hash,
        confidence=confidence,
        observed_at=when,
    )
    return write_evidence(ev)


__all__ = [
    # constants
    "TVB_IMAGE",
    "TVB_DEFAULT_REGION_COUNT",
    "TVB_CONTAINER_PREFIX",
    "TVB_SIMULATION_TIMEOUT_S",
    # errors
    "TVBUnavailableError",
    "TVBSimulationTimeout",
    "TVBSimulationError",
    # models
    "TVBSimulationRequest",
    "TVBSimulationResult",
    # day 6
    "check_docker_available",
    "check_tvb_image_available",
    "run_tvb_simulation",
    # day 7
    "list_available_connectomes",
    "load_default_connectome_metadata",
    # day 8
    "apply_hie_lesion_mask",
    "synthetic_hie_lesion_mask_for_aleksandra",
    # day 9
    "compute_seizure_onset_rate",
    "handle_tvb_simulation_request",
    # day 10
    "record_tvb_simulation_as_evidence",
]
