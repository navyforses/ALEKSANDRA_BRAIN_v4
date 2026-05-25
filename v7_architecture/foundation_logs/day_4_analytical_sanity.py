"""Phase 7.0 Day 4 — Beta-Binomial analytical sanity check.

Verifies that PyMC's MCMC posterior matches the closed-form analytical
posterior for the Beta-Binomial conjugate model across 4 stress-test
scenarios.

Math contract (Gelman et al., BDA3 §2.1; Kruschke, Doing Bayesian Data
Analysis 2nd ed., ch.6):

    Prior:        p ~ Beta(alpha, beta)
    Likelihood:   k | p ~ Binomial(n, p)
    Posterior:    p | k ~ Beta(alpha + k, beta + n - k)

PASS criterion per scenario:
    abs(pymc_mean - analytical_mean) < 0.005
    rhat < 1.01
    ess_bulk > 400

Exits 0 if all 4 scenarios PASS, 1 otherwise.

No PHI — synthetic conjugate scenarios only.
"""

from __future__ import annotations

import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pymc as pm
import arviz as az
import scipy.stats as st


# ---------------------------------------------------------------------------
# Scenario grid — 4 Beta-Binomial cases stressing different prior/data shapes
# ---------------------------------------------------------------------------
SCENARIOS = [
    # (label, alpha_prior, beta_prior, n_trials, k_successes, description)
    ("A", 2.0, 8.0, 20, 4, "moderate-info Beta(2,8)  + 4/20"),
    ("B", 1.0, 1.0, 30, 15, "uniform Beta(1,1)       + 15/30"),
    ("C", 10.0, 2.0, 20, 2, "strong prior Beta(10,2) + 2/20  (tension)"),
    ("D", 0.5, 0.5, 100, 50, "Jeffreys Beta(0.5,0.5) + 50/100"),
]

DELTA_MEAN_TOL = 0.005
RHAT_TOL = 1.01
ESS_BULK_MIN = 400.0


def run_scenario(label: str, alpha: float, beta: float, n: int, k: int):
    """Run one Beta-Binomial PyMC fit and return diagnostics dict."""
    # Analytical conjugate posterior
    a_post = alpha + k
    b_post = beta + n - k
    analytical_mean = a_post / (a_post + b_post)
    analytical_sd = float(st.beta(a_post, b_post).std())

    # PyMC model
    t0 = time.perf_counter()
    with pm.Model():
        p = pm.Beta("p", alpha=alpha, beta=beta)
        pm.Binomial("obs", n=n, p=p, observed=k)
        trace = pm.sample(
            draws=2000,
            tune=1000,
            chains=2,
            cores=1,
            progressbar=False,
            random_seed=7,
        )
    elapsed = time.perf_counter() - t0

    post_p = trace.posterior["p"]
    pymc_mean = float(post_p.mean())
    pymc_sd = float(post_p.std())

    summary = az.summary(trace, var_names=["p"], round_to=4)
    rhat = float(summary.loc["p", "r_hat"])
    ess_bulk = float(summary.loc["p", "ess_bulk"])

    delta_mean = abs(pymc_mean - analytical_mean)
    delta_sd = abs(pymc_sd - analytical_sd)

    passed = delta_mean < DELTA_MEAN_TOL and rhat < RHAT_TOL and ess_bulk > ESS_BULK_MIN

    return {
        "label": label,
        "pymc_mean": pymc_mean,
        "pymc_sd": pymc_sd,
        "analytical_mean": float(analytical_mean),
        "analytical_sd": analytical_sd,
        "delta_mean": delta_mean,
        "delta_sd": delta_sd,
        "rhat": rhat,
        "ess_bulk": ess_bulk,
        "elapsed_s": elapsed,
        "passed": passed,
    }


def main() -> int:
    print(
        f"PyMC {pm.__version__}  |  ArviZ {az.__version__}  |  SciPy {st.__name__.split('.')[0]} OK"
    )
    print("Phase 7.0 Day 4 — Beta-Binomial analytical sanity (4 scenarios)")
    print("=" * 78)

    total_t0 = time.perf_counter()
    results = []
    for label, alpha, beta, n, k, desc in SCENARIOS:
        print(f"\n[Scenario {label}] {desc}")
        print(f"  prior Beta({alpha}, {beta}) | observed {k}/{n}")
        res = run_scenario(label, alpha, beta, n, k)
        results.append(res)
        status = "OK  " if res["passed"] else "FAIL"
        print(
            f"  [{status}] PyMC mean={res['pymc_mean']:.4f} "
            f"(sd={res['pymc_sd']:.4f}) vs "
            f"analytical mean={res['analytical_mean']:.4f} "
            f"(sd={res['analytical_sd']:.4f}) | "
            f"delta_mean={res['delta_mean']:.4f} | "
            f"rhat={res['rhat']:.4f} | "
            f"ess={res['ess_bulk']:.0f} | "
            f"{res['elapsed_s']:.1f}s"
        )

    total_elapsed = time.perf_counter() - total_t0

    print("\n" + "=" * 78)
    print(
        f"Tolerances: delta_mean < {DELTA_MEAN_TOL} | "
        f"rhat < {RHAT_TOL} | ess_bulk > {ESS_BULK_MIN:.0f}"
    )
    n_pass = sum(1 for r in results if r["passed"])
    print(f"Pass rate: {n_pass}/{len(results)}")
    print(f"Total wall time: {total_elapsed:.1f}s")

    if n_pass == len(results):
        print("\nVERDICT: ALL PASS — PyMC matches analytical posterior.")
        return 0
    failed = [r["label"] for r in results if not r["passed"]]
    print(f"\nVERDICT: FAIL — scenarios failed: {', '.join(failed)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
