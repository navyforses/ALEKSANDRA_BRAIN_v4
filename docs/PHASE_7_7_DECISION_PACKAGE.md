# PHASE_7_7_DECISION_PACKAGE.md - v7.0 Launch Decision

> **Status:** Phase 7.7 acceptance-window template. Shako completes Day 9 + Day 10.
> The verifier does NOT directly read this file; it is the human decision record that
> closes the v7.0 milestone.

**Phase ID:** 7.7
**Decision owner:** Shako
**Decision deadline:** Day 10 (2027-01-09)
**Decision options:** GO / EXTEND / NO-GO

---

## 1. Decision matrix (spec §4.1)

> Map verifier result + persona acceptance to a decision.

| Result | Action |
|---|---|
| 10/10 PASS, >= 1 doctor YES, wife positive | **GO** -- production deploy Day 10 |
| 8-9/10 PASS, doctor NOT YET (specific gap) | **EXTEND** -- 1-week sprint for specific gap |
| <= 7/10 OR doctor REJECT OR wife negative | **NO-GO** -- rollback to v6.1, post-mortem, replan |

## 2. Evidence pointers

### 2.1 Phase 7.7 verifier result

- Latest run timestamp: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- JSON log: `v7_architecture/foundation_logs/verify_phase_7_7_<ts>.json`
- Result: <X PASS / Y SKIP / Z FAIL>
- Pointer: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

### 2.2 Cumulative verifier coverage

- Target (full production): 180
- Target (code-complete scope): 90
- Actual: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- Breakdown: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

### 2.3 Wife acceptance (`docs/SESSION_NOTES_WIFE.md`)

| Criterion | Grade |
|---|---|
| 1. Understood "what is the twin?" | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| 2. Status Cockpit useful | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| 3. active-question respected time | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| 4. CI trust | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| 5. KA copy natural | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |

Verdict: wife positive / neutral / negative -- <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

### 2.4 Doctor acceptance

`docs/SESSION_NOTES_MAYPOLE_1.md` line: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
`docs/SESSION_NOTES_MAYPOLE_2.md` line: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
`docs/SESSION_NOTES_NEUROLOGY.md` line (optional): <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

### 2.5 Bug bash

- P0 total: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- P1 total: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- P0+P1 100% resolved by Day 9: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- P2/P3 deferred to v7.1: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

### 2.6 Constitutional rule violations

- Active constitutional overrides at Day 10: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- check_7_7_09 status: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

### 2.7 LLM spend

- Phase 7.7 actual: $<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> / $2 cap
- Project cumulative: $<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> / $60 cap

## 3. Risk register at decision time

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | low/med/high | low/med/high | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | low/med/high | low/med/high | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |

## 4. Carry-forward (regardless of decision)

| # | Item | Phase target |
|---|---|---|
| 1 | Phase 7.6 frontend (12 verifier checks) | v7.1 OR pre-launch hotfix |
| 2 | Migrations 020 / 021 / 022 / 022b / 023 applied to production | Shako Day 11 |
| 3 | n8n perception_tick worker restart on Railway | Shako Day 11 |
| 4 | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |

## 5. Final decision

**Decision:** <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>   <!-- one of GO / NO-GO / EXTEND -->
**Decided by:** Shako
**Date:** <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
**Rationale (>= 100 words):**

<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

## 6. Launch / rollback / extend command record

### 6.1 GO scenario - v7.0 production launch commands

```bash
# DO NOT execute from inside a code-complete dispatch.
# These are the commands Shako runs by hand on Day 10 GO.

# git tag -a v7.0.0 -m "v7.0 production launch - Phase 7.7 closure"
# git push origin main
# git push origin v7.0.0
# (Vercel auto-deploys on push to main)
```

### 6.2 NO-GO scenario - rollback commands

```bash
# 1) Flip viewer/lib/flags.ts to NO-GO state (all 7.6-route flags = false).
# 2) Commit + push:
# git commit -am "rollback(v7.0): NO-GO decision per Phase 7.7 decision package"
# git push origin main
# 3) Tag the rollback state:
# git tag -a "v7.0.0-NOGO-$(date +%Y%m%d)" -m "Phase 7.7 NO-GO; flags off"
# git push origin "v7.0.0-NOGO-$(date +%Y%m%d)"
```

### 6.3 EXTEND scenario - 1-week extension scope

Open `docs/PHASE_7_7_EXTENSION_SCOPE.md` and fill specific gaps + re-acceptance criteria.
Re-run this decision package at end of extension.
