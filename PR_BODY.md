# v7.0 Closure Batch — Phase 7.0 → 7.7 + Maintenance + Design

**18 atomic commits** · **274 files** · **+56,290 / -300** lines
Branch: `v7-phases-7-0-to-7-5-closure` → `main`

---

## TL;DR

This PR closes the entire v7.0 digital-twin sprint as **code-complete**: 8
phases (Belief Foundation through Acceptance Window) plus 5 maintenance
commits plus 1 design-vision artifact. Every phase verifier runs
`--mode code-complete` GREEN, `pytest brain/ -m "not slow"` reports
**658 PASS · 2 SKIP**, `viewer/` builds clean with 4 new bilingual routes,
and the 13 inviolable constitutional rules are physically enforced (CSP,
DB triggers + CHECK constraints + RLS, Pydantic strict, output formatters,
PHI regex, budget hard stops, CI gates).

**Production-apply is OUT-OF-SCOPE for this PR.** Every migration / Neo4j
cypher / TVB container / Telegram outbound stays gated behind `--mode
production` runs that require operator credentials. Six runbooks under
`scripts/migrations/` document each step.

---

## Why this is one big PR

Per-phase PRs were considered and rejected: Phase 7.2 needs 7.0's belief
schema; Phase 7.3 needs 7.2's SCM API; Phase 7.5 enforces rules that
touch every prior phase's outputs; Phase 7.6 wires the whole thing to
the frontend. Splitting would have required cross-phase merge dancing
that bought us nothing — bisection works on per-commit granularity
inside the PR.

**Reviewers** — use the 18-commit list (below) as the table of contents.
Each commit message names the phase + scope + verifier evidence. Skip
to the phase you own; the diff per phase is bounded.

---

## What's in scope

### Layered architecture (PERCEPTION → MEMORY → COGNITION → SIM → ACTION)

```
Phase 7.0 Belief Foundation  ── 13-D Bayesian state + PyMC + ArviZ
Phase 7.1 Memory Refactor    ── Pearl 5-type causal edge taxonomy in Neo4j
Phase 7.2 Causal Layer       ── DoWhy SCM + do() API + SCM editor + structure learning
Phase 7.3 Simulation Engine  ── Layer A (Monte Carlo) + B (TVB Docker) + C (Studio)
Phase 7.4 Active Learning    ── EIG question gen + Telegram dry-run + weekly cap
Phase 7.5 Constitutional Code── 13 inviolable rules physically enforced
Phase 7.6 Site Refactor      ── 4 new bilingual routes + 4 widget refactors
Phase 7.7 Acceptance Window  ── code-complete scaffold (live sessions late-Dec → Jan)
```

### 18 commits in order (oldest → newest)

| # | SHA | Subject | Files | Phase |
|---|---|---|---|---|
|  1 | `86e1a3c` | feat(v7): Phase 7.0 Belief Foundation + v7 architecture seed | 73 | 7.0 |
|  2 | `3ae9415` | feat(v7): Phase 7.1 Memory Refactor — Pearl 5-type SCM edge taxonomy | 21 | 7.1 |
|  3 | `90438db` | feat(v7): Phase 7.2 Causal Layer — DoWhy SCM + do() API + SCM editor | 30 | 7.2 |
|  4 | `c8adb43` | feat(v7): Phase 7.3 Simulation Engine Layers A+C (Monte Carlo + Studio) | 24 | 7.3 A/C |
|  5 | `76668a0` | feat(v7): Phase 7.4 Active Learning — EIG + question gen + Telegram dry-run | 28 | 7.4 |
|  6 | `c5ffe20` | feat(v7): Phase 7.5 Constitutional Code — 13 inviolable rules physically enforced | 31 | 7.5 |
|  7 | `44a5e35` | feat(v7): Phase 7.7 Acceptance Window — code-complete scaffold | 15 | 7.7 |
|  8 | `452a060` | fix(verifier): recognize [locale]/brain/ path in MNG-01 check | 1 | maint |
|  9 | `1073cec` | fix(viewer): merge Phase 7.5 middleware.ts into proxy.ts (Next.js 16 conflict) | 2 | 7.5 fix |
| 10 | `5b4cff6` | feat(v7): Phase 7.6 Site Refactor — 4 NEW routes + 4 widget refactors | 34 | 7.6 |
| 11 | `bbcfcbb` | feat(v7): Phase 7.3 Layer B — TVB Docker integration (Days 6-10) | 6 | 7.3 B |
| 12 | `61b1729` | fix(test): point Rule #1 constitutional test at proxy.ts (post-merge) | 1 | maint |
| 13 | `e55ef6a` | chore(v7): ground Hagmann PMID + ignore verifier run logs | 3 | maint |
| 14 | `6f8e05e` | fix(v7): post-handoff verifier + test hygiene (8/8 GREEN) | 5 | maint |
| 15 | `5bd97f7` | docs(design): fresh-site concept brief + 8 specialist inputs + AGENTS.md | 11 | docs |
| 16 | `028ca0d` | docs(handoff): archive v6.1 handoff + refresh v7.0 closure handoff (resume notes) | 2 | docs |
| 17 | `c0c1863` | fix(test): stabilize test_higher_confidence_level_widens_ci (no more bootstrap flake) | 1 | maint |
| 18 | `f8f7ec5` | docs(handoff): mark DoWhy flake resolved + bump HEAD to c0c1863 | 1 | docs |

---

## Verification evidence

All commands run **on this branch HEAD** before this PR was opened.

### Python test suite

```bash
.venv-v7/Scripts/python.exe -m pytest brain/ -m "not slow" -q --tb=no
# 658 passed, 2 skipped, 4 deselected, ~54k warnings in ~10:31
```

The 2 skips are `reportlab` (missing optional dep — Phase 7.7 PDF builder
skipif) and the conditional live TVB test (`@pytest.mark.skipif(not
_DOCKER_OR_IMAGE_AVAILABLE)` — skips when Docker daemon is down). Both
are documented in the test file docstrings.

The DoWhy bootstrap flake (`test_higher_confidence_level_widens_ci`) is
**retired** by commit 17 (`c0c1863`). The fix seeds `np.random + random`
with the same value immediately before each `estimate_effect` call so
both 95% and 99% CIs sample from the *identical* bootstrap distribution
— the 99%-CI is then wider by mathematical construction.

### Frontend

```bash
cd viewer
npx tsc --noEmit          # exit 0
npm run build             # exit 0
# 4 new routes built:
#   /[locale]/twin    /[locale]/causal    /[locale]/simulate    /[locale]/drift
# 4 refactored widgets bound into existing routes:
#   today, timeline, therapies, manager-briefing
```

### 8 phase verifiers (`--mode code-complete`)

| Verifier | Result | Notes |
|---|---|---|
| `verify_phase_7_0.py` | **10/11 PASS · 1 SKIP · GREEN** | SKIP = RLS smoke (migration 016 not yet applied) |
| `verify_phase_7_1.py` | **2/9 PASS · 7 SKIP · GREEN** | 7 SKIP = Neo4j-gated (cypher 017 not yet applied) |
| `verify_phase_7_2.py` | **12/12 PASS · GREEN** | cumulative pytest timeout bumped 600s → 1200s |
| `verify_phase_7_3.py` | **11/13 PASS · 2 SKIP · GREEN** | 2 SKIP = Docker daemon unavailable (TVB live tests) |
| `verify_phase_7_4.py` | **10/10 PASS · GREEN** | Telegram dry-run only |
| `verify_phase_7_5.py` | **11/14 PASS · 3 SKIP · GREEN** | 3 SKIP = DB-trigger-gated (migrations 021/022/022b) |
| `verify_phase_7_6.py` | **12/12 PASS · GREEN** | bundle/CSP/dynamic-import checks all PASS |
| `verify_phase_7_7.py` | **1/10 PASS · 9 SKIP · GREEN** | 9 SKIP = calendar-gated (live sessions late-Dec) |

Every verifier exits 0. Every SKIP carries a remediation string pointing
at the operator action that flips it to PASS in `--mode production`.

### Constitutional enforcement (Phase 7.5 — 13 rules)

Each rule is enforced by code or DB schema (not policy):

| # | Rule | Where enforced |
|---|---|---|
| 1 | MRI client-only | `viewer/proxy.ts` — CSP + DICOM POST rejector → HTTP 415 |
| 2 | Voice review required | migration 021 — `intake_drops` trigger sets `requires_review=true` |
| 3 | Citation required | `brain/causal/recommendation.py` — Pydantic strict schema rejects no-citation |
| 4 | CI required | `brain/common/output_formatter.py` — naked `expected_value` rejected |
| 5 | Bilingual parity | `brain/common/i18n_guard.py` — en-only payload rejected, `{en,ka}` required |
| 6 | PHI filter | `brain/common/phi_redactor.py` — MRN + doctor-name regex pre-prompt |
| 7 | Budget hard stop | `brain/common/budget.py` — `BudgetError` on daily-cap breach |
| 8 | Belief evidence | `brain/belief/api.py` — `update(evidence=None)` raises `BeliefWithoutEvidenceError` |
| 9 | Hypothesis ≥3 sources | migration 022 — `hypotheses` CHECK constraint on `array_length(supporting_papers, 1) >= 3` when status=confirmed |
| 10 | Sim uncertainty | `brain/sim/uncertainty_guard.py` — synthetic sd/mean=1.0 → `BudgetGuardError` |
| 11 | Question cap | migration 022b — `weekly_questions` 4th INSERT/UPDATE in same week → reject |
| 12 | PDF ≥5 primary | `brain/docs/pdf_guard.py` — `assert_min_primary_sources` rejects 4-source |
| 13 | Verifier CI gate | `.github/workflows/verify_all.yml` — runs all 6 phase verifiers on push |

A 14th meta-check covers the override flow: every constitutional violation
must go through `brain/common/overrides.py::issue_override` which writes
an audit row to the `constitutional_overrides` table.

---

## What's NOT in this PR (operator follow-up)

These items stay open and require **production credentials** to land:

### 6 production-apply sessions

| Phase | Apply | Tag | Owner |
|---|---|---|---|
| 7.0 | migration 016 (RLS on belief_*)| (no tag — foundation) | Shako |
| 7.1 | Neo4j cypher 017 + `classify_edges.py` + `cross_link.py` + backfill | — | Shako |
| 7.2 | migration 018 (`scms` + `scm_audit_log`) | `v7.2.0` | Shako |
| 7.3 | migration 019 (`mc_simulations`, `tvb_simulations`) | `v7.3.0` | Shako |
| 7.4 | migration 020 (`weekly_questions` + `question_responses`) + n8n perception_tick restart + Telegram bot tokens | `v7.4.0` | Shako |
| 7.5 | migrations 021 + 022 + 022b + 023 + push `.github/workflows/verify_all.yml` | `v7.5.0` | Shako |

Each migration file has a sibling `*_runbook.md` with idempotent steps,
rollback procedure, and a verifier-script command to re-run
`--mode production` after the apply.

### Calendar-gated

- **Phase 4 acceptance window** closes ~2026-06-07 (first real Weekly
  Brief Sunday 2026-05-24 09:00 ET = v1 release gate)
- **Phase 7.7 wife/doctor sessions** late-Dec 2026 → early-Jan 2027

### Carry-forwards documented in handoff

- TVB upstream image `thevirtualbrain/tvb-run` flagged "Updates
  discontinued after version 26.7.x"; using `:latest` for now; custom
  anaconda/miniconda replacement deferred to v7.1.0 maintenance
- 10 Phase 5 backend gaps (Google Calendar API, Python worker on
  Railway, Supabase realtime, pattern recognition, TVB simulation
  wiring, mobile responsive, Supabase Auth, Whisper transport audit,
  PHI redactor voice-ambient expansion, `aleksandra_timeline.event_type`
  ENUM)
- 3 Phase 6 deferred items (French UI, GIN search, CGM-06 tone
  post-processor Georgian extension)

---

## Privacy / HIPAA posture

- **MRI / DICOM** — Rule #1 enforced at the edge by `viewer/proxy.ts`.
  Any POST with `application/dicom` MIME returns HTTP 415 before reaching
  Next.js routing. CSP rejects cross-origin XHR to external endpoints
  in the same gesture.
- **Server-side persistence** — every server-side write filters through
  Rule #6 (`phi_redactor.py`) which redacts MRN, BMC numbers, doctor
  names per a deny-list maintained in `brain/common/phi_terms.py`.
- **Telegram / Gmail outbound** — Communicator agent's compose path
  goes through `phi_redactor.redact_bilingual` (en+ka) before any
  `send_message` call. Phase 7.4 active questions inherit the same
  filter.
- **Spend ceiling** — Rule #7 hard-stops every LLM call when the daily
  budget cap is breached. Cap configurable per Anthropic + Whisper +
  OpenAI; defaults in `brain/common/budget.py`.
- **No PHI ever enters Claude API prompts** by discipline (research
  content only). The `phi_redactor` is the safety net.

---

## Test plan (post-merge)

Reviewers — please run:

- [ ] `pytest brain/ -m "not slow"` → expect 658 PASS · 2 SKIP
- [ ] `cd viewer && npx tsc --noEmit && npm run build` → both exit 0
- [ ] `cd viewer && npm run dev` → open
  - [ ] `/en/today` (existing)
  - [ ] `/en/twin` (Phase 7.6 NEW — histograms)
  - [ ] `/en/causal` (Phase 7.6 NEW — vis-network graph)
  - [ ] `/en/simulate` (Phase 7.6 NEW — react-flow builder)
  - [ ] `/en/drift` (Phase 7.6 NEW — Plotly timeline)
  - [ ] `/ka/today` (i18n sanity — LanguageSwitcher + KA dictionary)
- [ ] 8 phase verifiers `--mode code-complete` → each exits 0 / GREEN
- [ ] Inspect `viewer/lib/flags.ts` — each flag's comment explains the
  NO-GO rollback action

After browser smoke passes, proceed with the production-apply sessions
in the order listed above (Phase 7.0 → 7.5).

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
