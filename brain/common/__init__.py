"""Phase 7.5 Constitutional layer - physical enforcement of 13 inviolable rules.

This package collects the application-side enforcement points for the
v7 constitution. The matrix:

    Rule #1  MRI client-only         viewer/middleware.ts (NOT here)
    Rule #2  Voice review            scripts/migrations/021 (DB trigger)
    Rule #3  Citation mandatory      brain/common/schemas.py
    Rule #4  Confidence intervals    brain/common/formatter.py
    Rule #5  Bilingual parity        brain/common/i18n_guard.py
    Rule #6  PHI filter              brain/common/phi_guard.py
    Rule #7  Budget hard stop        brain/common/budget_guard.py
    Rule #8  Belief needs evidence   brain/belief/update.py (mod)
    Rule #9  Hypothesis >= 3 sources scripts/migrations/022 (DB CHECK)
    Rule #10 Simulation uncertainty  brain/sim/api.py (mod)
    Rule #11 Question rate cap       scripts/migrations/022b (DB CHECK + trig)
    Rule #12 PDF >= 5 primary        brain/common/pdf_guard.py
    Rule #13 Verifier CI gate        .github/workflows/verify_all.yml
    meta     Override audit          scripts/migrations/023 + overrides.py

Single import surface: ``from brain.common.guards import ...``.

Reference:
    v7_architecture/70_PHASES/75_PHASE_7_5_CONSTITUTIONAL_2W.md
    .claude/agents/v7-constitution.md
"""

from __future__ import annotations
