"""Phase 7.0 Day 6 — Dimension catalog schema + PyMC distribution factory.

Loads the 13-dimension catalog from `dimensions.toml` and provides typed
factories for building PyMC distributions from per-dimension specs.

Companion to `persistence.py`:

  - `persistence.py` owns the DB persistence layer (`BeliefDimension`
    Pydantic model, psycopg2 read/write, `evidence_hash` idempotency).
  - `schema.py` owns the IN-MEMORY catalog + PyMC bridge — it loads the
    TOML catalog, validates per-distribution prior_params shape, and
    builds PyMC random variables inside open `pm.Model()` contexts.

Design choice (Day 6): ADDITIVE. The `BeliefDimension` model stays in
persistence.py (single source of truth, no test churn). schema.py imports
it and layers complementary helpers on top.

Hard rules (from .claude/agents/v7-bayes.md + Phase 7.0 spec):

  1. Every prior REQUIRES a citation. Day 6 ships with
     "TBD-Day-{7|8|9}-librarian-{A|B|C}" placeholders; Days 7-9 v7-librarian
     work replaces them with PubMed PMIDs / DOIs. `validate_dimension_catalog`
     surfaces every stub citation so the librarian sees what's pending.
  2. No PHI — every catalog entry is a CONCEPT (cyst_volume_pct, GMFCS,
     etc.), never an Aleksandra-specific value.
  3. Pure stdlib `tomllib` (Python 3.11+). No third-party TOML reader.
  4. `to_pm()` works inside `with pm.Model():` context — tests instantiate
     each kind except `vector` (which needs a full cov matrix; deferred to
     update.py where the multivariate likelihood is built).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

import pymc as pm

from brain.belief.persistence import (  # single source of truth
    BeliefDimension,
)


# ---------------------------------------------------------------------------
# Distribution kinds (typed mirror of persistence.ALLOWED_DISTRIBUTIONS)
# ---------------------------------------------------------------------------
DISTRIBUTION_KINDS = Literal[
    "beta",
    "normal",
    "poisson",
    "categorical",
    "gamma",
    "bernoulli",
    "vector",
    "exp_decay",
]


# Required prior_params keys per distribution kind.
# Mirrored in DistributionSpec._validate_params_for_kind and Day 6 tests.
REQUIRED_PARAMS: dict[str, frozenset[str]] = {
    "beta": frozenset({"alpha", "beta"}),
    "normal": frozenset({"mu", "sigma"}),
    "poisson": frozenset({"mu"}),
    "categorical": frozenset({"probs"}),  # list[float]
    "gamma": frozenset({"alpha", "beta"}),
    "bernoulli": frozenset({"p"}),
    "vector": frozenset({"mu_vec", "sigma_vec"}),  # both list[float]
    "exp_decay": frozenset({"lam"}),  # exponential rate
}


# ---------------------------------------------------------------------------
# DistributionSpec — per-distribution PyMC factory
# ---------------------------------------------------------------------------
class DistributionSpec(BaseModel):
    """Per-distribution prior-parameter contract.

    Each `kind` has its own required `params` keys (see `REQUIRED_PARAMS`).
    `model_validator` dispatches on `kind` and refuses construction if a
    required key is missing.
    """

    model_config = ConfigDict(extra="forbid")

    kind: DISTRIBUTION_KINDS
    params: dict[str, Any]  # values may be float OR list[float]

    @model_validator(mode="after")
    def _validate_params_for_kind(self) -> "DistributionSpec":
        required = REQUIRED_PARAMS[self.kind]
        missing = required - set(self.params.keys())
        if missing:
            raise ValueError(
                f"distribution {self.kind!r} missing prior_params keys: "
                f"{sorted(missing)} (required: {sorted(required)})"
            )
        return self

    def to_pm(self, name: str, **kwargs: Any) -> Any:
        """Build a PyMC RV inside an open `pm.Model()` context.

        Returns the freshly-created PyMC random variable. Caller must already
        be inside a `with pm.Model():` block.

        Note on `vector`: this MVP routes to `pm.Normal` over a flat vector
        (independence assumption). The full `pm.MvNormal` with covariance
        matrix is the responsibility of update.py once Day 13-14 wires the
        multivariate-likelihood path. This keeps Day 6 testable without a
        cov-matrix dependency.
        """
        p = self.params

        if self.kind == "beta":
            return pm.Beta(name, alpha=p["alpha"], beta=p["beta"], **kwargs)
        if self.kind == "normal":
            return pm.Normal(name, mu=p["mu"], sigma=p["sigma"], **kwargs)
        if self.kind == "poisson":
            return pm.Poisson(name, mu=p["mu"], **kwargs)
        if self.kind == "categorical":
            return pm.Categorical(name, p=p["probs"], **kwargs)
        if self.kind == "gamma":
            return pm.Gamma(name, alpha=p["alpha"], beta=p["beta"], **kwargs)
        if self.kind == "bernoulli":
            return pm.Bernoulli(name, p=p["p"], **kwargs)
        if self.kind == "exp_decay":
            # Returns the RAW lambda RV in 'time' units (mean = 1/lam).
            # The likelihood layer (likelihoods._exp_decay_likelihood) computes
            # the deterministic resource-fraction transform exp(-lam·horizon)
            # inline and observes against the transformed value. This keeps the
            # prior in its natural parameter space while observations stay in
            # clinical resource-fraction units [0, 1]. See Day 10 sensitivity
            # sweep finding (`valid_min=0, valid_max=1` on the dimension row
            # describes the derived fraction, NOT the underlying time-remaining
            # RV whose mean ≈ 1/lam ≈ 526 days for the live catalog row).
            return pm.Exponential(name, lam=p["lam"], **kwargs)
        if self.kind == "vector":
            # MVP: independent normals over a flat vector. Update.py owns
            # the covariance-matrix path for the full MvNormal likelihood.
            mu_vec = list(p["mu_vec"])
            sigma_vec = list(p["sigma_vec"])
            if len(mu_vec) != len(sigma_vec):
                raise ValueError(
                    f"vector dim mismatch: mu_vec={len(mu_vec)} "
                    f"sigma_vec={len(sigma_vec)}"
                )
            return pm.Normal(
                name,
                mu=mu_vec,
                sigma=sigma_vec,
                shape=len(mu_vec),
                **kwargs,
            )
        raise ValueError(f"unknown distribution kind: {self.kind!r}")


# ---------------------------------------------------------------------------
# ValidationReport — output of `validate_dimension_catalog`
# ---------------------------------------------------------------------------
class ValidationReport(BaseModel):
    """Summary of a catalog-load run.

    `stubs_pending_citation` is the list of dimension names whose citation
    field still starts with "TBD-" — Days 7-9 librarian work clears this list.
    """

    model_config = ConfigDict(extra="forbid")

    total: int
    valid: int
    invalid: list[dict[str, Any]]  # [{"name": str, "error": str}, ...]
    stubs_pending_citation: list[str]
    distributions_covered: list[str]


# ---------------------------------------------------------------------------
# Catalog loader
# ---------------------------------------------------------------------------
DEFAULT_TOML_PATH = Path(__file__).parent / "dimensions.toml"


def load_dimensions_from_toml(
    path: Path | str = DEFAULT_TOML_PATH,
) -> list[BeliefDimension]:
    """Parse `dimensions.toml` into a list of `BeliefDimension`.

    Raises `pydantic.ValidationError` (re-raised) on any row that violates the
    BeliefDimension schema (e.g., unknown distribution, missing citation).
    Raises `FileNotFoundError` if the path does not exist.
    Raises `tomllib.TOMLDecodeError` on a malformed TOML file.
    """
    toml_path = Path(path)
    if not toml_path.is_file():
        raise FileNotFoundError(f"dimensions catalog not found: {toml_path}")

    with toml_path.open("rb") as fh:
        raw = tomllib.load(fh)

    rows = raw.get("dimensions", [])
    if not isinstance(rows, list):
        raise ValueError(
            f"expected `dimensions = [[...]]` array of tables, got {type(rows).__name__}"
        )

    return [BeliefDimension(**row) for row in rows]


def validate_dimension_catalog(
    dims: list[BeliefDimension],
    *,
    expected_total: int = 13,
) -> ValidationReport:
    """Cross-check a loaded catalog.

    - Counts total / valid rows.
    - Flags rows whose citation begins with "TBD-" (Day 6 placeholder slots).
    - Reports the set of distribution kinds actually used.
    - Records per-row errors when DistributionSpec validation fails for the
      row's (distribution, prior_params) pair — catches typos that
      BeliefDimension alone cannot (it only checks the distribution name,
      not the params shape).
    """
    invalid: list[dict[str, Any]] = []
    stubs: list[str] = []
    distributions: set[str] = set()

    for dim in dims:
        distributions.add(dim.distribution)

        if dim.citation.startswith("TBD-"):
            stubs.append(dim.name)

        try:
            DistributionSpec(kind=dim.distribution, params=dim.prior_params)
        except (ValidationError, ValueError) as exc:
            invalid.append({"name": dim.name, "error": str(exc)})

    valid = len(dims) - len(invalid)

    # Note: we do NOT raise on total != expected_total. The report carries
    # `total` so callers can assert it themselves (the Day 6 test does).
    return ValidationReport(
        total=len(dims),
        valid=valid,
        invalid=invalid,
        stubs_pending_citation=sorted(stubs),
        distributions_covered=sorted(distributions),
    )


def get_dimension_spec(dim: BeliefDimension) -> DistributionSpec:
    """Project a `BeliefDimension` row down to its `DistributionSpec`.

    Useful when update.py iterates priors → builds PyMC models without
    needing the catalog metadata (units, valid_min, valid_max, citation).
    """
    return DistributionSpec(kind=dim.distribution, params=dim.prior_params)


__all__ = [
    "DISTRIBUTION_KINDS",
    "REQUIRED_PARAMS",
    "DistributionSpec",
    "ValidationReport",
    "DEFAULT_TOML_PATH",
    "load_dimensions_from_toml",
    "validate_dimension_catalog",
    "get_dimension_spec",
]
