"""Phase 7.3 Day 1 — Scenario specification + canonical hash.

Pydantic models describing one Monte Carlo simulation scenario: a list of
interventions (drug / cell-therapy / rehab / manual-dimension-shift), a
horizon in days, an outcome subset, and an n_samples cap.

The reference scenario mirrors spec section 2.3 verbatim:
``vigabatrin_d200_cordblood_d280_physio_daily``; small n_samples=100 is
used in tests, with 10_000 reserved for production runs (cap enforced by
verifier check 11).

Citation hygiene:
    - Every intervention.mechanism_citation, when present, must contain
      one of ``pubmed.ncbi.nlm.nih.gov``, ``doi.org`` or ``PMID:``.
    - The reference scenario cites only PMIDs already grounded in
      ``brain.causal.scm.build_reference_scm``
      (``7686614`` Lippa-Loftis GABA-T mechanism;
       ``32713850`` Pellock infantile-spasms age-of-onset;
       ``19489084`` Hensch neuroplasticity critical periods).

PHI hygiene:
    - Scenario carries no Aleksandra-specific values. Interventions are
      typed concepts (vigabatrin, cord_blood, physiotherapy) and the
      day-grid is generic post-NICU.

Reference:
    - v7_architecture/70_PHASES/73_PHASE_7_3_SIMULATION_ENGINE_3W.md
      section 1 layer A and section 2.3 scenario JSON example.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from brain.belief.schema import load_dimensions_from_toml


# ---------------------------------------------------------------------------
# Intervention type alias
# ---------------------------------------------------------------------------
InterventionType = Literal[
    "drug",
    "cell_therapy",
    "rehab",
    "manual_dimension_shift",
]

FrequencyLiteral = Literal["daily", "weekly", "monthly", "once"]


# ---------------------------------------------------------------------------
# Cached dimension-name set (loaded once from TOML; no DB call)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _known_dimension_names() -> frozenset[str]:
    """Return the set of dimension names from ``dimensions.toml`` (cached)."""
    dims = load_dimensions_from_toml()
    return frozenset(d.name for d in dims)


# ---------------------------------------------------------------------------
# Intervention
# ---------------------------------------------------------------------------
class Intervention(BaseModel):
    """One intervention applied within a Scenario.

    Validators enforce per-type required fields:
        - ``drug`` requires ``dose_mg_kg``
        - ``cell_therapy`` requires ``infusion_day`` OR ``start_day``
          (if both set, they must equal)
        - ``manual_dimension_shift`` requires both ``target_dimension``
          and ``dimension_delta``

    Citation requirement: if ``mechanism_citation`` is set, it must contain
    one of ``pubmed.ncbi.nlm.nih.gov``, ``doi.org`` or ``PMID:``.
    """

    model_config = ConfigDict(extra="forbid")

    type: InterventionType
    name: str = Field(..., min_length=1)
    start_day: int = Field(..., ge=0)
    dose_mg_kg: Optional[float] = None
    infusion_day: Optional[int] = None
    frequency: Optional[FrequencyLiteral] = "once"
    target_dimension: Optional[str] = None
    dimension_delta: Optional[float] = None
    effect_per_dim: dict[str, float] = Field(default_factory=dict)
    duration_days: Optional[int] = None
    mechanism_citation: Optional[str] = None

    @field_validator("mechanism_citation")
    @classmethod
    def _citation_shape(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        markers = ("pubmed.ncbi.nlm.nih.gov", "doi.org", "PMID:")
        if not any(m in v for m in markers):
            raise ValueError(
                "mechanism_citation must contain one of "
                "'pubmed.ncbi.nlm.nih.gov', 'doi.org' or 'PMID:' "
                f"(got: {v!r})"
            )
        return v

    @model_validator(mode="after")
    def _validate_by_type(self) -> "Intervention":
        if self.type == "drug":
            if self.dose_mg_kg is None:
                raise ValueError(
                    "intervention type 'drug' requires dose_mg_kg"
                )
        elif self.type == "cell_therapy":
            # infusion_day OR start_day required; if both, they must equal
            if self.infusion_day is None and self.start_day is None:
                raise ValueError(
                    "intervention type 'cell_therapy' requires "
                    "infusion_day or start_day"
                )
            if (
                self.infusion_day is not None
                and self.start_day is not None
                and self.infusion_day != self.start_day
            ):
                raise ValueError(
                    "infusion_day and start_day disagree "
                    f"({self.infusion_day} != {self.start_day})"
                )
        elif self.type == "manual_dimension_shift":
            if self.target_dimension is None or self.dimension_delta is None:
                raise ValueError(
                    "intervention type 'manual_dimension_shift' requires "
                    "both target_dimension and dimension_delta"
                )
            known = _known_dimension_names()
            if self.target_dimension not in known:
                raise ValueError(
                    f"target_dimension {self.target_dimension!r} not in "
                    f"known dimensions ({sorted(known)})"
                )
        return self

    def effective_start_day(self) -> int:
        """Return the day this intervention first activates.

        cell_therapy uses ``infusion_day`` when set; otherwise falls back
        to ``start_day``. All other types use ``start_day``.
        """
        if self.type == "cell_therapy" and self.infusion_day is not None:
            return int(self.infusion_day)
        return int(self.start_day)


# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------
class Scenario(BaseModel):
    """One Monte Carlo scenario.

    Attributes:
        name: short scenario identifier (snake_case recommended).
        description: human-readable rationale (excluded from hash).
        interventions: ordered list (order is semantic and hashed).
        horizon_days: simulation horizon, capped at 2000 (5+ years).
        n_samples: hard-capped at 10_000 (verifier check 11).
        outcomes: subset of the 13 dimension names from ``dimensions.toml``.
        random_seed: RNG seed; excluded from hash so changing the seed
            does NOT bust the cache by default.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    interventions: list[Intervention]
    horizon_days: int = Field(..., ge=1, le=2000)
    n_samples: int = Field(..., ge=10, le=10_000)
    outcomes: list[str]
    random_seed: Optional[int] = 42

    @field_validator("outcomes")
    @classmethod
    def _outcomes_subset_of_dims(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("outcomes must contain at least one dimension")
        known = _known_dimension_names()
        unknown = [name for name in v if name not in known]
        if unknown:
            raise ValueError(
                f"unknown outcome dimension(s): {unknown}; "
                f"must be subset of {sorted(known)}"
            )
        return v


# ---------------------------------------------------------------------------
# Canonical hash
# ---------------------------------------------------------------------------
def compute_scenario_hash(scenario: Scenario) -> str:
    """SHA-256 of canonical JSON of the Scenario.

    Excludes ``name``, ``description`` and ``random_seed`` so:
        - two scenarios with identical interventions/horizon/n_samples/
          outcomes collide -> cache hit
        - changing the seed does NOT bust the cache by default

    Intervention order IS part of the hash (semantic: applying
    physiotherapy-then-vigabatrin differs from the reverse).
    """
    payload = scenario.model_dump(
        exclude={"name", "description", "random_seed"}
    )
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Reference scenario (PHI-free, spec section 2.3)
# ---------------------------------------------------------------------------
def build_reference_scenario() -> Scenario:
    """Vigabatrin + cord-blood + daily physiotherapy reference scenario.

    Mirrors spec section 2.3 with horizon_days=400 and a small
    n_samples=100 suitable for tests. Production runs use n_samples=10_000
    (capped by verifier check 11).

    Citations used here all originate in ``brain/causal/scm.py``:

        - ``PMID:32713850`` Pellock infantile-spasms age-of-onset (vigabatrin)
        - ``PMID:7686614``  Lippa-Loftis GABA-T inhibition (vigabatrin)
        - ``PMID:19489084`` Hensch neuroplasticity critical periods (physio)

    Cord-blood mechanism is left without a citation field because no
    Phase-7.2 PMID covers it; cord-blood is logged as ``cell_therapy``
    name-only until Phase 4 Duke outreach yields a primary citation.
    """
    interventions = [
        Intervention(
            type="drug",
            name="vigabatrin",
            start_day=200,
            dose_mg_kg=50.0,
            frequency="daily",
            duration_days=180,
            effect_per_dim={"seizure_freq_per_day": -0.05},
            mechanism_citation=(
                "PMID:7686614 (https://pubmed.ncbi.nlm.nih.gov/7686614/); "
                "PMID:32713850 (https://pubmed.ncbi.nlm.nih.gov/32713850/)"
            ),
        ),
        Intervention(
            type="cell_therapy",
            name="cord_blood",
            start_day=280,
            infusion_day=280,
            frequency="once",
        ),
        Intervention(
            type="rehab",
            name="physiotherapy",
            start_day=1,
            frequency="daily",
            effect_per_dim={
                "head_control_seconds": 0.02,
                "muscle_tone_hammersmith": 0.01,
            },
            mechanism_citation=(
                "PMID:19489084 (https://pubmed.ncbi.nlm.nih.gov/19489084/)"
            ),
        ),
    ]

    return Scenario(
        name="vigabatrin_d200_cordblood_d280_physio_daily",
        description=(
            "Reference scenario per Phase 7.3 spec section 2.3. "
            "Vigabatrin day-200 onset, cord-blood single infusion day-280, "
            "daily physiotherapy from day-1. PHI-free."
        ),
        interventions=interventions,
        horizon_days=400,
        n_samples=100,
        outcomes=[
            "cyst_volume_pct",
            "seizure_freq_per_day",
            "eye_tracking_seconds",
            "gmfcs_level",
            "bayley_cognitive",
        ],
        random_seed=42,
    )


__all__ = [
    "Intervention",
    "InterventionType",
    "FrequencyLiteral",
    "Scenario",
    "compute_scenario_hash",
    "build_reference_scenario",
]
