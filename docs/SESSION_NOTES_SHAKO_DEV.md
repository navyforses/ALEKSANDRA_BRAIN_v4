# SESSION_NOTES_SHAKO_DEV.md - Day 5 Bug Bash (Shako)

> **Status:** Phase 7.7 acceptance-window template. Shako fills during Day 5 systematic E2E.
> Pairs with `PHASE_7_7_BUG_LOG.md` (severity-tagged issue list).

**Phase ID:** 7.7
**Persona:** Shako (developer)
**Day:** 5 of 10
**Planned duration:** ~6 hours (>= 30 min per route x 8 routes x 2 locales = 16 cells)
**Scope:** systematic bug bash across all v7.0 routes in both ka + en locales

---

## 1. Pre-bash checklist

- [ ] Staging branch deployed: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- [ ] All 7.0..7.5 verifiers GREEN in CI: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- [ ] PHASE_7_7_BUG_LOG.md template open: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- [ ] BURN_DOWN ka + en dictionaries in sync: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

## 2. Route x locale coverage matrix (>= 30 min each)

> Mark each cell with `[x]` for completed. Notes column gets the bug IDs filed
> (e.g. `BUG-03, BUG-07`).

| Route | ka session | en session |
|---|---|---|
| `/` (homepage) | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| `/[locale]/twin` | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| `/[locale]/causal` | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| `/[locale]/simulate` | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| `/[locale]/drift` | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| `/[locale]/hypotheses` | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| `/[locale]/research` | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| `/[locale]/inbox` | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |

## 3. Constitutional rule violations checklist (Phase 7.5 13 rules)

> Tick each rule that the bash session attempted to provoke. NONE should fire.
> Any fire is a P0 entry in PHASE_7_7_BUG_LOG.md.

| # | Rule | Probed | Violation observed |
|---|---|---|---|
| 1 | MRI / DICOM client-only | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | n / y -> BUG-?? |
| 2 | Voice review required | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | n / y -> BUG-?? |
| 3 | Citation mandatory | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | n / y -> BUG-?? |
| 4 | CI required | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | n / y -> BUG-?? |
| 5 | Bilingual parity | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | n / y -> BUG-?? |
| 6 | PHI filter | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | n / y -> BUG-?? |
| 7 | Budget hard stop | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | n / y -> BUG-?? |
| 8 | Belief requires evidence | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | n / y -> BUG-?? |
| 9 | Hypothesis >= 3 supporting_papers | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | n / y -> BUG-?? |
| 10 | Sim uncertainty guard | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | n / y -> BUG-?? |
| 11 | Wife question cap >= 3/week | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | n / y -> BUG-?? |
| 12 | PDF >= 5 primary sources | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | n / y -> BUG-?? |
| 13 | Verifier CI gate | [ ] <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> | n / y -> BUG-?? |

## 4. Deploy-pipeline reliability (Phase 7.5 spec §2.4)

| Metric | Target | Actual |
|---|---|---|
| CI runs (Day 1-5) | >= 1 per commit | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| Failed deploys due to verifier | 0 | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| Vercel deploy time | < 5 min | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| Verifier overrides used | <= 1 | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |

## 5. SCM editor end-to-end (Phase 7.2 backend + Phase 7.6 frontend)

> spec §2.4: Shako creates >= 1 alternative SCM end-to-end.

- Alternative SCM name: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- Created via UI editor: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- Edges added: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- Citation per edge: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- Simulation Studio scenario runs against new SCM: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

## 6. Bash session summary

- Total bugs filed: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- P0 / P1 / P2 / P3 split: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- Constitutional rule violations: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- Carry-forward to Day 6 fixes: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
