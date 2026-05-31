"""Phase 7.0 smoke test — PyMC + NumPyro + ArviZ end-to-end.

Fits a tiny Bayesian linear regression with NUTS and prints the posterior
summary. Confirms the Bayesian backend can actually sample and that the
JAX/NumPyro inference path wires together.
"""

from __future__ import annotations

import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pymc as pm
import arviz as az

rng = np.random.default_rng(7)
N = 200
true_alpha, true_beta, true_sigma = 1.0, 2.5, 0.7
x = rng.normal(size=N)
y = true_alpha + true_beta * x + rng.normal(scale=true_sigma, size=N)

print(f"PyMC {pm.__version__}  |  ArviZ {az.__version__}")
print(f"data: N={N}  true alpha={true_alpha} beta={true_beta} sigma={true_sigma}")

t0 = time.perf_counter()
with pm.Model() as model:
    alpha = pm.Normal("alpha", 0, 5)
    beta = pm.Normal("beta", 0, 5)
    sigma = pm.HalfNormal("sigma", 1)
    pm.Normal("y", mu=alpha + beta * x, sigma=sigma, observed=y)
    trace = pm.sample(
        draws=500,
        tune=500,
        chains=2,
        cores=1,
        progressbar=False,
        random_seed=7,
    )
elapsed = time.perf_counter() - t0

summary = az.summary(trace, var_names=["alpha", "beta", "sigma"], round_to=3)
print(f"\nsampling took {elapsed:.1f}s")
print(summary.to_string())

# Sanity check: posterior means within 0.2 of truth
post = trace.posterior
checks = [
    ("alpha", float(post["alpha"].mean()), true_alpha, 0.2),
    ("beta", float(post["beta"].mean()), true_beta, 0.2),
    ("sigma", float(post["sigma"].mean()), true_sigma, 0.2),
]
ok = True
for name, est, truth, tol in checks:
    delta = abs(est - truth)
    status = "OK" if delta < tol else "DRIFT"
    print(
        f"  {status:5s} {name}: posterior={est:.3f}  truth={truth}  delta={delta:.3f}"
    )
    if delta >= tol:
        ok = False
sys.exit(0 if ok else 1)
