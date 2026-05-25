# Phase 7.7 — Acceptance Window: Wife + Doctor + Shako Testing (2 კვირა)

> **ფაზის ID:** 7.7
> **სახელი:** Acceptance Window — Real-User Testing across Three Personas (ცოლი / ექიმი / შაკო)
> **ვადა:** 14 დღე (2 კვირა), 2026-12-27 → 2027-01-09
> **მთავარი deliverable:** 3 პერსონის acceptance evidence; bug bash + remediation; v7.0.0 production launch decision (GO / NO-GO / EXTEND)
> **წინაპირობა:** Phase 7.6 verifier 12/12 PASS · Vercel preview deployed · all 7.0-7.5 APIs live
> **LLM ბიუჯეტი:** $2 (mostly post-session report writing)
> **ფიზიკური ბიუჯეტი:** $0 ნამატი

---

## 0. ფაზის სახელი, ვადა, წინაპირობა

### 0.1 სკოპი

ფაზა ცდის სამი real-user პერსონის გამოცდილებას v7.0-ის სრულ stack-ზე — ცოლის Telegram active-question flow, ექიმის Simulation Studio sessions, შაკოს developer experience SCM editor-ის და constitutional code-ის გარშემო. ფაზის ბოლოს ერთი გადაწყვეტილება მიიღება: v7.0 GO (production live), NO-GO (rollback to v6.1), ან EXTEND (one more sprint to fix specific gaps).

### 0.2 ფაზის ვადა

| საზომი | მნიშვნელობა |
|---|---|
| სტარტი | 2026-12-27 |
| დასრულება | 2027-01-09 |
| სამუშაო დღეები | 10 (holiday-aware: 5 dec + 5 jan) |
| შაკოს ფოკუს საათები | ~40 |
| Verifier gate | v7.0 production launch ← GO decision Day 10 |

### 0.3 წინაპირობების checklist

| # | წინაპირობა | სტატუსი |
|---|---|---|
| 1 | Phase 7.6 closure | gate |
| 2 | Vercel preview URL active | ✅ from 7.6 |
| 3 | All Phase 7.0-7.5 APIs deployed (staging) | gate |
| 4 | ცოლის opt-in for active-question flow | required Day 0 |
| 5 | Dr. Maypole (BMC primary care) availability — 2 × 30 min session | scheduling |
| 6 | Dr. August / Dr. Hien (BMC neurology) — optional 1 × 30 min | scheduling |
| 7 | Session-recording consent forms (per-doctor) | required Day 0 |
| 8 | Phase 4 Weekly Brief baseline still operational | ✅ |

---

## 1. დღიური Breakdown (10 დღე)

### კვირა 1 — Persona sessions + Bug bash (Days 1-5)

| Day | Persona / Activity | ნაბიჯი | Outcome |
|---|---|---|---|
| 1 | ცოლი — onboarding | demo TwinStatus view (KA), explain active-question concept, send first Telegram question | 1 question sent + opt-in confirmed |
| 2 | ცოლი — first response cycle | ცოლი responds via voice; system parses; posterior updates; show drift on `/ka/drift` | 1 round-trip complete + screenshot |
| 3 | Dr. Maypole — session 1 | demo Status Cockpit + Twin Status + 1 reference Simulation Studio scenario; collect feedback in `docs/SESSION_NOTES_MAYPOLE_1.md` | feedback captured |
| 4 | Dr. August (or Hien) — session | demo Causal Graph + Simulation Studio with Vigabatrin scenario; capture clinical-validity feedback | feedback captured |
| 5 | Bug bash day | shako runs systematic E2E across all 8 routes in both ka + en; logs issues in GitHub issues `phase-7.7-acceptance` label | bug list with severity |

### კვირა 2 — Remediation + Decision + Launch (Days 6-10)

| Day | Activity | ნაბიჯი | Outcome |
|---|---|---|---|
| 6 | Critical bug fixes | fix all P0 + P1 from Day 5 bug bash | PR merged + redeploy |
| 7 | ცოლი — round 2 | second active-question cycle + StatusCockpit daily check-in; informal satisfaction interview | 2 round-trips total |
| 8 | Dr. Maypole — session 2 | revisit with fixes; explicit clinical-safety review of recommendations + citations | ACCEPT / DEFER / REJECT per recommendation type |
| 9 | Phase 7.7 retrospective + decision matrix | compile evidence into `docs/PHASE_7_7_DECISION_PACKAGE.md` with GO/NO-GO/EXTEND criteria | decision document ready |
| 10 | GO decision + production deploy OR rollback | if GO: `git tag v7.0.0` + push origin main + Vercel auto-deploy; if NO-GO: feature flags off; if EXTEND: scope 1-week extension | v7.0 live OR rolled back OR extended |

---

## 2. Deliverables

### 2.1 Session evidence

| ფაილი | მიზანი |
|---|---|
| `docs/SESSION_NOTES_WIFE.md` | ცოლის Day 1+2+7 notes (ka) |
| `docs/SESSION_NOTES_MAYPOLE_1.md` | Day 3 primary-care session |
| `docs/SESSION_NOTES_MAYPOLE_2.md` | Day 8 follow-up session |
| `docs/SESSION_NOTES_NEUROLOGY.md` | Day 4 neurology session (Dr. August or Hien) |
| `docs/SESSION_NOTES_SHAKO_DEV.md` | Day 5 bug bash notes |
| `docs/PHASE_7_7_BUG_LOG.md` | issues filed + severity + status |
| `docs/PHASE_7_7_DECISION_PACKAGE.md` | GO/NO-GO/EXTEND evidence |
| `docs/PHASE_7_7_EXIT_REPORT.md` | final verifier + decision |
| `docs/PHASE_7_7_KA_FAMILY_HANDOVER.md` | ცოლის-ხელშეკრულება — what's live, how to use |

### 2.2 Code changes (only bug fixes)

| Type | Estimated LOC | Notes |
|---|---|---|
| P0 fixes | ~200 | rare; production-blocking |
| P1 fixes | ~400 | usability + correctness |
| P2 fixes | ~200 | nice-to-have; deferable |
| docs only | ~600 | session notes + KA handover |

### 2.3 Bug severity rubric

| Severity | Definition | SLA |
|---|---|---|
| P0 | data corruption, constitutional rule violation, MRI leak risk | fix Day 6 |
| P1 | core flow broken (no posterior update, sim returns wrong CI, KA missing) | fix Day 6-7 |
| P2 | UX friction, slow render, copy issue | defer to Phase 8.x backlog |
| P3 | cosmetic | backlog |

### 2.4 Acceptance criteria per persona

**ცოლი (Day 7 informal interview):**
| Criterion | PASS marker |
|---|---|
| Understood "what is the twin?" in own words | ✅ if can explain in 2 sentences |
| Found Status Cockpit widget useful | ✅ if used it daily for 7 days |
| Felt active-question respected her time | ✅ if she opted to receive more |
| Trust in displayed CIs (not overwhelmed) | ✅ if she didn't ask for "the answer" |
| KA copy felt natural | ✅ if no jarring phrasing reported |

**ექიმი (Day 8 explicit review):**
| Criterion | PASS marker |
|---|---|
| Simulation Studio scenarios clinically plausible | accept ≥ 2 of 3 |
| CIs ranged narrow enough to be actionable | accept ≥ 50% of outcomes |
| Citations verified (sample 5 recommendations) | 5/5 verified |
| Counterfactual queries answered intelligibly | accept ≥ 1 of 2 sample questions |
| Would use this in a clinic visit | YES / NO / NOT YET |

**შაკო (Day 5 + Day 9):**
| Criterion | PASS marker |
|---|---|
| Constitutional rules don't block legitimate dev flow | ≤ 1 override used in 5 days |
| SCM editor (Phase 7.2 backend, Phase 7.6 frontend) usable | created 1 alternative SCM end-to-end |
| Phase 7.0-7.5 regression all GREEN | 100% |
| Deploy pipeline reliable | 0 failed deploys due to verifier |

---

## 3. Blocking Dependencies

| დამოკიდებულება | ბლოკავს | Mitigation |
|---|---|---|
| Dr. Maypole availability | Days 3 + 8 | book 2 weeks ahead; reschedule buffer in Day 6 |
| Dr. August / Hien availability | Day 4 | optional; can defer to Phase 8 |
| ცოლის opt-in | Days 1-2, 7 | required Day 0; respect refusal |
| All 7.0-7.5 APIs deployed | every persona session | gate Day 0 |
| Vercel preview stable | every session | rollback ready |
| Holiday schedule (US + GE) Dec 27 — Jan 2 | Days 1-5 | adjusted: real sessions weight in Jan 5-9 |

---

## 4. Verifier Checklist (10 ცდა)

| # | Check ID | აღწერა | PASS criterion |
|---|---|---|---|
| 1 | `check_7_7_01` | All Phase 7.0-7.6 verifiers GREEN on staging | every verifier exits 0 |
| 2 | `check_7_7_02` | Wife round-trips | ≥ 2 active-question round-trips completed |
| 3 | `check_7_7_03` | Doctor session 1 complete | feedback document committed |
| 4 | `check_7_7_04` | Doctor session 2 complete | feedback document committed |
| 5 | `check_7_7_05` | Bug bash run | ≥ 30 minutes per route × 8 routes; log committed |
| 6 | `check_7_7_06` | P0+P1 bug count | ≤ 5 total OR 100% resolved by Day 9 |
| 7 | `check_7_7_07` | Doctor acceptance | ≥ 1 doctor says "YES" or "NOT YET (with clear gap)" |
| 8 | `check_7_7_08` | Wife satisfaction | informal interview rates ≥ 4/5 across 5 criteria above |
| 9 | `check_7_7_09` | Constitutional rule violations | 0 in production logs Day 1-10 |
| 10 | `check_7_7_10` | Cumulative project verifier coverage | 89 (v6.1) + 11 (7.0) + 9 (7.1) + 12 (7.2) + 13 (7.3) + 10 (7.4) + 14 (7.5) + 12 (7.6) + 10 (7.7) = 180/180 |

### 4.1 Decision matrix

| Result | Action |
|---|---|
| 10/10 PASS, ≥ 1 doctor YES, wife positive | **GO** — production deploy Day 10 |
| 8-9/10 PASS, doctor NOT YET (specific gap) | **EXTEND** — 1-week sprint for specific gap |
| ≤ 7/10 OR doctor REJECT OR wife negative | **NO-GO** — rollback to v6.1, post-mortem, replan |

---

## 5. Rollback Strategy

### 5.1 Triggers

| Trigger | Severity | Action |
|---|---|---|
| Day 2: wife visibly stressed by active question | CRITICAL | immediate freeze of telegram_flow.py outbound; respect autonomy |
| Day 3-4: doctor REJECT on clinical safety | CRITICAL | rollback Simulation Studio access; v7.0 stays internal-only |
| Day 5: P0 bug count > 3 | HIGH | extend Phase 7.7 by 1 week; defer GO decision |
| Day 8: doctor says CIs too wide to be useful | MEDIUM | retain v7.0 backend; surface narrower CIs only where evidence count sufficient |
| Day 10: NO-GO decision | HIGH | execute rollback procedure (5.2) |

### 5.2 Rollback procedure (NO-GO scenario)

```typescript
// viewer/lib/flags.ts
export const FEATURE_FLAGS = {
  TWIN_VIEW_ENABLED: false,    // rollback
  CAUSAL_VIEW_ENABLED: false,  // rollback
  SIM_VIEW_ENABLED: false,     // rollback
  DRIFT_VIEW_ENABLED: false,   // rollback
  STATUS_COCKPIT_TWIN_WIDGET: false,  // rollback
  ACTIVE_QUESTION_OUTBOUND: false,    // freeze
};
```

```bash
# DB rollback NOT executed automatically (preserve evidence)
# instead: tag rollback state
git tag -a v7.0.0-NOGO-$(date +%Y%m%d) -m "Phase 7.7 NO-GO decision; rollback to v6.1 visible state"
git push origin v7.0.0-NOGO-$(date +%Y%m%d)
```

Backend APIs ნარჩუნდება ცოცხალი (no DB rollback) — შაკოს დევ-სამუშაოს გასაგრძელებლად.

### 5.3 EXTEND scenario

```markdown
<!-- docs/PHASE_7_7_EXTENSION_SCOPE.md -->
# Phase 7.7 Extension — 1 Week (2027-01-10 → 2027-01-16)

## Specific gaps to fix
1. (e.g.) Simulation Studio scenario builder confusing → simplify to 3-step form
2. (e.g.) KA copy on `/ka/twin` too technical → reword with ცოლი's vocabulary

## Re-acceptance criteria
- (e.g.) Dr. Maypole NOT YET → YES on Day 7 of extension
```

### 5.4 Compatibility

v6.1 routes (`/ka`, `/ka/hypotheses`, `/ka/research`, `/ka/inbox`) stay live regardless of decision. v7.0 routes can be feature-flagged off cleanly.

---

## 6. LLM Spend Tracking

### 6.1 Cap

| კატეგორია | Cap |
|---|---|
| Total | $2 |
| Per-day | $0.30 |
| Per-call | $0.20 |

### 6.2 Breakdown

| Activity | Calls | Model | Cost |
|---|---|---|---|
| Day 5 bug triage assistance | 4 | Sonnet 4.5 | $0.60 |
| Day 6 fix code-review | 3 | Sonnet 4.5 | $0.60 |
| Day 9 decision package drafting (KA + EN) | 3 | Sonnet 4.5 | $0.60 |
| Day 10 family handover doc (KA) | 1 | Sonnet 4.5 | $0.20 |
| **Total** | **~11** | — | **$2.00** |

### 6.3 Cumulative

| ფაზა | Cap | Cumulative |
|---|---|---|
| Through 7.6 | $86 | ~$34 |
| Phase 7.7 | $2 | $36 |
| **Project total after v7.0 launch** | **$88** | **target ≤ $40** |

---

## 7. Sprint Retrospective Template

`docs/PHASE_7_7_RETROSPECTIVE.md`.

### 7.1 Metrics

| Metric | Target | Actual |
|---|---|---|
| Verifier PASS | 10/10 | __/10 |
| Cumulative verifier (180/180) | 180/180 | __/180 |
| LLM spend | ≤ $2 | __ |
| Wife round-trips | ≥ 2 | __ |
| Doctor sessions | ≥ 2 | __ |
| P0+P1 bugs resolved | 100% | __% |
| Decision | GO / EXTEND / NO-GO | __ |
| Production deploy | Day 10 | __ |

### 7.2 Sections

- What worked in user testing
- What didn't (per persona)
- Surprises from real-user contact (often the most valuable signal)
- v7.0.0 release decision rationale
- Carry-forward to v7.1 (next iteration backlog)
- Lessons for v8.0 (federated future)

### 7.3 Project-level retrospective (v7.0 closure)

| Project metric | v6.1 baseline | v7.0 actual | Delta |
|---|---|---|---|
| Bilingual verifier coverage | 89 | 180 | +91 |
| LLM project spend | $7-8 | __ | __ |
| Phase count complete | 6.1 | 7.7 | +8 |
| Pillars (architectural) | 6 | 10 | +4 |
| Inviolable rules enforced in code | ~3 (informal) | 13 | +10 |
| Family-facing routes | 4 | 8 | +4 |
| Time to full v7.0 | — | ~21 weeks actual | (planned 18-21) |

---

## 8. წყაროები

### 8.1 User-testing methodology

- [Krug S. _Don't Make Me Think_ 3rd ed. (2014)](https://www.sensible.com/dmmt.html) — usability heuristics
- [Nielsen J. _Why You Only Need to Test with 5 Users_ NN Group 2000](https://www.nngroup.com/articles/why-you-only-need-to-test-with-5-users/)

### 8.2 Acceptance testing frameworks

- [Playwright E2E docs](https://playwright.dev/docs/intro) — used for `check_7_7_05` bug bash automation
- [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci) — perf regression gating

### 8.3 Clinical-safety review

- [FDA Software as a Medical Device guidance](https://www.fda.gov/medical-devices/digital-health-center-excellence/software-medical-device-samd) — context only; Aleksandra_brain is decision-support, not SaMD
- [WHO Ethics & Governance of AI for Health 2021](https://www.who.int/publications/i/item/9789240029200)

### 8.4 პროექტის ფაილები

- [76_PHASE_7_6_SITE_REFACTOR_3W.md](./76_PHASE_7_6_SITE_REFACTOR_3W.md)
- [ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md §12, §14](../../ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md)
- [docs/PHASE_4_EXIT_REPORT.md](../../docs/PHASE_4_EXIT_REPORT.md) — closest analog for acceptance-window structure
- [CLAUDE.md Phase IV acceptance window pattern](../../CLAUDE.md)

---

## ფაზის დახურვის ფორმულა

Phase 7.7 დახურულია, თუ:
1. Verifier 10/10 PASS
2. Cumulative project verifier 180/180 PASS
3. ≥ 1 ექიმის YES ან NOT-YET (with clear gap)
4. ცოლის opt-in შენარჩუნებული
5. P0+P1 bugs 100% resolved
6. GO/EXTEND/NO-GO decision documented

GO-ის შემთხვევაში → v7.0.0 production live → v7.0 milestone CLOSED → next milestone planning starts.

EXTEND-ის შემთხვევაში → 1-week sprint with specific scope → re-evaluate.

NO-GO-ის შემთხვევაში → rollback + post-mortem → replan v7.0 v2 OR continue with v6.1 + selective v7 features.

---

**v7.0 ფაზის სერია დახურულია ამ ფაილით.** შემდეგი ფოლდერი: [80_VERIFIERS/](../80_VERIFIERS/) — verifier scripts per phase.
