# PHASE_7_7_BUG_LOG.md - Acceptance Window Bug Log

> **Status:** Phase 7.7 acceptance-window template. Shako fills during Day 5 bug bash
> and Day 6 remediation. The verifier (`scripts/verify_phase_7_7.py` check_7_7_05 +
> check_7_7_06) flips SKIP -> PASS when the `<TO BE FILLED IN BY SHAKO DURING
> ACCEPTANCE WINDOW>` marker is removed AND the P0+P1 total <= 5 (or 100% resolved).

**Phase ID:** 7.7
**Owner:** Shako
**Scope:** any bug surfaced Days 1-9 across all 8 routes, both locales, all 13 rules

---

## Severity rubric (spec §2.3)

| Severity | Definition | SLA |
|---|---|---|
| P0 | data corruption, constitutional rule violation, MRI leak risk | fix Day 6 |
| P1 | core flow broken (no posterior update, sim returns wrong CI, KA missing) | fix Day 6-7 |
| P2 | UX friction, slow render, copy issue | defer to v7.1 backlog |
| P3 | cosmetic | backlog |

## Status legend

| Status | Meaning |
|---|---|
| OPEN | filed, not yet fixed |
| FIXING | PR open or branch in progress |
| FIXED | PR merged to main, deployed |
| WONTFIX | accepted as v7.1 backlog or rejected |

## Bug table

> Replace the placeholder rows below. Keep the column count exactly 7 so
> `check_7_7_06` regex parses severity + status correctly.

| ID | Severity | Route | Description | Reproducer | Fix commit | Status |
|---|---|---|---|---|---|---|
| BUG-01 | <P0/P1/P2/P3> | <route or `n/a`> | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | <sha or `n/a`> | OPEN |
| BUG-02 | <P0/P1/P2/P3> | <route or `n/a`> | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | <sha or `n/a`> | OPEN |
| BUG-03 | <P0/P1/P2/P3> | <route or `n/a`> | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | <sha or `n/a`> | OPEN |
| BUG-04 | <P0/P1/P2/P3> | <route or `n/a`> | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | <sha or `n/a`> | OPEN |
| BUG-05 | <P0/P1/P2/P3> | <route or `n/a`> | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | <sha or `n/a`> | OPEN |

## Daily tally

| Day | P0 new | P1 new | P2 new | P3 new | Resolved |
|---|---|---|---|---|---|
| 1 | 0 | 0 | 0 | 0 | 0 |
| 2 | 0 | 0 | 0 | 0 | 0 |
| 3 | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | _ | _ | _ | _ |
| 4 | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | _ | _ | _ | _ |
| 5 | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | _ | _ | _ | _ |
| 6 | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | _ | _ | _ | _ |
| 7 | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | _ | _ | _ | _ |
| 8 | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | _ | _ | _ | _ |
| 9 | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | _ | _ | _ | _ |

## Verifier read pattern

`check_7_7_06` parses rows of the form:

```
| <id> | P0 | <route> | <desc> | <repro> | <sha> | OPEN |
```

Severity (P0 / P1) and Status (OPEN / FIXING / FIXED / WONTFIX) are
counted by regex. P2 and P3 do NOT block closure.
