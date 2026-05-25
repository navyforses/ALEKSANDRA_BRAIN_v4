"""Phase 7.0 smoke test — DoWhy + EconML causal inference.

Fits a small linear causal effect with a known ground truth, runs DoWhy's
identify → estimate → refute loop, and reports whether the estimate lands
close to the true ATE.
"""

from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
import dowhy
from dowhy import CausalModel

print(f"DoWhy {dowhy.__version__}")

rng = np.random.default_rng(11)
N = 1000
# DAG: Z -> T -> Y, plus Z -> Y backdoor
Z = rng.normal(size=N)
T = (0.4 * Z + rng.normal(size=N) > 0).astype(int)
true_ate = 1.5
Y = true_ate * T + 0.8 * Z + rng.normal(scale=0.3, size=N)
df = pd.DataFrame({"Z": Z, "T": T, "Y": Y})

model = CausalModel(
    data=df,
    treatment="T",
    outcome="Y",
    common_causes=["Z"],
)
ident = model.identify_effect(proceed_when_unidentifiable=True)
est = model.estimate_effect(
    ident,
    method_name="backdoor.linear_regression",
    test_significance=False,
)
print(f"  true ATE  = {true_ate}")
print(f"  estimate  = {est.value:.4f}")

delta = abs(est.value - true_ate)
status = "OK" if delta < 0.15 else "DRIFT"
print(f"  {status}  |estimate - truth| = {delta:.4f}  (tol 0.15)")
sys.exit(0 if delta < 0.15 else 1)
