# Phase 7.5 — Constitutional Code: 13 ფიზიკურად ჩაშენებული წესი (2 კვირა)

> **ფაზის ID:** 7.5
> **სახელი:** Constitutional Code — Physical Enforcement of 13 Inviolable Rules
> **ვადა:** 14 დღე (2 კვირა), 2026-11-22 → 2026-12-05
> **მთავარი deliverable:** 13 ხელშეუხებელი წესის ფიზიკური ჩაშენება სხვადასხვა შრეში (CSP headers, DB triggers, Pydantic schemas, rate limiters, pre-prompt regex, CI/CD gate)
> **წინაპირობა:** Phase 7.4 verifier 10/10 PASS
> **LLM ბიუჯეტი:** $3
> **ფიზიკური ბიუჯეტი:** $0 ნამატი

---

## 0. ფაზის სახელი, ვადა, წინაპირობა

### 0.1 სკოპი

ფაზა აქცევს v7 architecture §9-ის 13 წესს მითითებიდან კოდის შრის ფიზიკურ შემოწმებად, რომელიც დარღვევას შეუძლებელს ხდის. Anthropic-ის Constitutional AI-ის ფილოსოფიის გადატანა: წესი იცავს მხოლოდ მაშინ, თუ მისი დარღვევა ფიზიკურად ბლოკდება, არა მარტო მითითებაში წერია.

### 0.2 ფაზის ვადა

| საზომი | მნიშვნელობა |
|---|---|
| სტარტი | 2026-11-22 |
| დასრულება | 2026-12-05 |
| სამუშაო დღეები | 10 |
| შაკოს ფოკუს საათები | ~35 |
| Verifier gate | Phase 7.6-მდე 14/14 PASS (1 verifier per rule + 1 meta) |

### 0.3 წინაპირობების checklist

| # | წინაპირობა | სტატუსი |
|---|---|---|
| 1 | Phase 7.4 closure | gate |
| 2 | LiteLLM gate from Phase 6.1 | ✅ |
| 3 | i18n middleware from Phase 6 | ✅ |
| 4 | Pydantic strict v2 | ✅ |
| 5 | GitHub Actions CI active | ✅ |
| 6 | Supabase trigger permissions | service-role required |

---

## 1. დღიური Breakdown (10 დღე)

### კვირა 1 — Frontend + DB + Schema rules (Rules 1-7, Days 1-5)

| Day | Rule(s) | ფიზიკური შრე | ნაბიჯი |
|---|---|---|---|
| 1 | #1 MRI client-only | CSP headers + upload block | `viewer/middleware.ts` — `Content-Security-Policy: connect-src 'self' supabase.co; img-src 'self' blob:`; `<input>` reject mime types `application/dicom`, `image/nifti` from any FormData destined for `/api` |
| 2 | #2 Voice review required | DB trigger | `migrations/021_voice_review_trigger.sql` — `BEFORE INSERT ON intake_drops` set `requires_review=true` always |
| 3 | #3 Citation mandatory | Pydantic schema | `brain/common/schemas.py` — `class Recommendation(BaseModel): citation: HttpUrl = Field(..., min_length=10)` strict mode |
| 4 | #4 Confidence intervals | Output formatter | `brain/common/formatter.py` — reject any `recommendation.expected_value` without `ci_low`+`ci_high` companion |
| 5 | #5 Bilingual parity + #6 PHI filter + #7 Budget | i18n middleware + pre-prompt regex + LiteLLM gate (already partial from v6) → harden | three rules harmonized into a single `brain/common/guards.py` module |

### კვირა 2 — Belief/Simulation/Active/Hypothesis/PDF/Verifier rules (Rules 8-13, Days 6-10)

| Day | Rule(s) | ფიზიკური შრე | ნაბიჯი |
|---|---|---|---|
| 6 | #8 Belief requires evidence | PyMC update guard | `brain/belief/update.py` — refuse `update(evidence=None)` with `BeliefWithoutEvidenceError` |
| 7 | #9 Hypothesis ≥ 3 sources | DB constraint | `ALTER TABLE hypotheses ADD CONSTRAINT min_sources CHECK (jsonb_array_length(supporting_papers) >= 3) WHERE status='confirmed'` |
| 8 | #10 Simulation uncertainty check | Pre-flight | `brain/sim/api.py` — refuse if avg posterior sd > 50% of mean across 13 dims (link to Phase 7.3 check_7_3_12) |
| 9 | #11 Question rate ≤ 3/wk | DB unique + check | `migrations/022_active_rate_constraint.sql` — `CHECK (questions_sent <= 3)` on `active_rate_log`; trigger blocks 4th insert |
| 10 | #12 PDF ≥ 5 primary sources + #13 Verifier deployment gate | Doc generator + CI | `brain/docs/pdf_builder.py` rejects < 5 primary; `.github/workflows/deploy.yml` runs `verify_phase_7_*.py --all` as blocking job |

---

## 2. Deliverables

### 2.1 კოდი (13 enforcement points)

| Rule | ფაილი | ფიზიკური მექანიზმი | LOC |
|---|---|---|---|
| 1 | `viewer/middleware.ts` | CSP header + FormData inspector | 80 |
| 2 | `migrations/021_voice_review_trigger.sql` | DB BEFORE INSERT trigger | 30 |
| 3 | `brain/common/schemas.py` | Pydantic strict citation field | 60 |
| 4 | `brain/common/formatter.py` | output rejection of point estimates | 80 |
| 5 | `brain/common/i18n_guard.py` | parity check (en + ka both present) | 60 |
| 6 | `brain/common/phi_guard.py` | pre-prompt regex (extends Phase 6 redactor) | 100 |
| 7 | `brain/common/budget_guard.py` | LiteLLM hard stop (extends Phase 6.1) | 80 |
| 8 | `brain/belief/update.py` (mod) | refuse evidence-less update | +20 |
| 9 | `migrations/022_hypothesis_constraint.sql` | partial CHECK constraint | 25 |
| 10 | `brain/sim/api.py` (mod) | pre-flight uncertainty check | +30 |
| 11 | `migrations/022_active_rate_constraint.sql` | CHECK + trigger | 35 |
| 12 | `brain/docs/pdf_builder.py` (mod) | primary-source count guard | +40 |
| 13 | `.github/workflows/verify_all.yml` | CI gate workflow | 70 |
| meta | `brain/common/guards.py` | consolidated import surface | 50 |
| meta | `brain/common/tests/test_constitutional.py` | 13 + 1 tests | 400 |
| meta | `scripts/verify_phase_7_5.py` | 14-check verifier | 280 |

ჯამური LOC: ~1440.

### 2.2 Enforcement matrix (full)

| # | წესი | ფიზიკური ფენა | bypass-ის ღირებულება |
|---|---|---|---|
| 1 | MRI client-only | Browser CSP + Next.js middleware | high (browser exploit + middleware bypass) |
| 2 | Voice review required | DB trigger | high (service-role write + trigger disable) |
| 3 | Citation mandatory | Pydantic strict + 422 response | medium (schema bypass at code level) |
| 4 | Confidence intervals | Output formatter | medium |
| 5 | Bilingual parity | i18n middleware | medium |
| 6 | PHI filter | Pre-prompt regex + audit log | medium |
| 7 | Budget hard stop | LiteLLM gate | high (env-var override required) |
| 8 | Belief needs evidence | PyMC update guard | low (code path bypass) |
| 9 | Hypothesis ≥ 3 sources | Postgres CHECK constraint (partial) | very high (DDL change required) |
| 10 | Simulation uncertainty | Pre-flight check | low |
| 11 | Question rate cap | DB CHECK + trigger | very high |
| 12 | PDF ≥ 5 primary | Doc-builder count guard | medium |
| 13 | Verifier CI gate | GitHub Actions blocking | high (workflow file edit + PR approval) |

### 2.3 Escape hatch (explicit, audited)

Every rule has a documented escape hatch in `docs/PHASE_7_5_ESCAPE_HATCHES.md`:
- only შაკო (service-role + audit) can override
- override creates row in `constitutional_overrides` table
- override expires automatically after 24 hours
- override notifies ცოლი via Telegram

```sql
-- migrations/023_overrides.sql
CREATE TABLE constitutional_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_number INT NOT NULL CHECK (rule_number BETWEEN 1 AND 13),
    reason TEXT NOT NULL,
    overridden_by TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 3. Blocking Dependencies

| დამოკიდებულება | ბლოკავს | Mitigation |
|---|---|---|
| Phase 6 i18n + PHI redactor | rules 5, 6 | ✅ from v6 |
| Phase 6.1 LiteLLM gate | rule 7 | ✅ |
| Phase 7.0 update API | rule 8 | gate |
| Phase 7.3 simulation API | rule 10 | gate |
| Phase 7.4 active_rate_log | rule 11 | gate |
| GitHub Actions secrets (Supabase, Anthropic) | rule 13 CI | check |
| Next.js 16 file convention + middleware | rule 1 | ✅ from Phase 6 |

---

## 4. Verifier Checklist (14 ცდა — 13 rules + 1 meta)

| # | Check ID | აღწერა | PASS criterion |
|---|---|---|---|
| 1 | `check_7_5_01` | Rule #1 enforced | curl with `Content-Type: application/dicom` to `/api/upload` returns 415 |
| 2 | `check_7_5_02` | Rule #2 enforced | INSERT into intake_drops without `requires_review` → trigger sets true |
| 3 | `check_7_5_03` | Rule #3 enforced | Recommendation without citation → ValidationError |
| 4 | `check_7_5_04` | Rule #4 enforced | output with `expected_value` only → rejected |
| 5 | `check_7_5_05` | Rule #5 enforced | output with `en` only (no `ka`) → rejected |
| 6 | `check_7_5_06` | Rule #6 enforced | prompt with regex-matched PHI string → redacted before send |
| 7 | `check_7_5_07` | Rule #7 enforced | spend > $100/mo → LiteLLM raises BudgetError |
| 8 | `check_7_5_08` | Rule #8 enforced | `update(evidence=None)` → BeliefWithoutEvidenceError |
| 9 | `check_7_5_09` | Rule #9 enforced | UPDATE hypotheses SET status='confirmed' WHERE supporting_papers has 2 → constraint violation |
| 10 | `check_7_5_10` | Rule #10 enforced | scenario where avg posterior sd > 50% mean → 422 from sim API |
| 11 | `check_7_5_11` | Rule #11 enforced | 4th INSERT into active_rate_log same week → trigger block |
| 12 | `check_7_5_12` | Rule #12 enforced | pdf with 4 primary sources → builder raises InsufficientSourcesError |
| 13 | `check_7_5_13` | Rule #13 enforced | PR with failing verifier → GitHub Actions blocks merge |
| 14 | `check_7_5_14` | Meta: override flow | shako-issued override creates audit row + expires |

---

## 5. Rollback Strategy

### 5.1 Triggers

| Trigger | Severity | Action |
|---|---|---|
| Day 2: DB trigger blocks legitimate Phase 5 voice flow | HIGH | adjust trigger to only set flag, not block |
| Day 9: rate-limiter trigger causes lock contention | HIGH | move check to application layer; keep CHECK constraint |
| Day 13: CI gate blocks legitimate deploys (false positive) | HIGH | adjust verifier; document escape hatch usage |
| Day 10: verifier ≤ 11/14 | HIGH | 1-week extension |
| Any rule discovered to be over-restrictive in production | MEDIUM | escape hatch with audit; permanent fix in Phase 7.5.1 |

### 5.2 Rollback procedure

```sql
BEGIN;
DROP TABLE IF EXISTS constitutional_overrides CASCADE;
ALTER TABLE hypotheses DROP CONSTRAINT IF EXISTS min_sources;
ALTER TABLE active_rate_log DROP CONSTRAINT IF EXISTS questions_within_cap;
DROP TRIGGER IF EXISTS voice_review_required ON intake_drops;
COMMIT;
```

```bash
git revert <range>
# revert .github/workflows/verify_all.yml separately if CI causes deploy block
```

### 5.3 Per-rule rollback

თითო წესისთვის გადახედე `docs/PHASE_7_5_ESCAPE_HATCHES.md`-ში. Override row 24h-ში ავტომატურად იხურება.

### 5.4 Compatibility

Phase 1-7.4 unchanged. Rules ემატება ფიზიკურად — არცერთი არსებული flow არ უნდა გატყდეს.

---

## 6. LLM Spend Tracking

### 6.1 Cap

| კატეგორია | Cap |
|---|---|
| Total | $3 |
| Per-day | $0.50 |
| Per-call | $0.20 |

### 6.2 Breakdown

| Activity | Calls | Model | Cost |
|---|---|---|---|
| Day 1 CSP policy review | 3 | Sonnet 4.5 | $0.60 |
| Day 6 PyMC guard edge cases | 4 | Sonnet 4.5 | $0.80 |
| Day 7-9 SQL constraint review | 5 | Sonnet 4.5 | $0.80 |
| Day 10 CI workflow review | 3 | Sonnet 4.5 | $0.60 |
| Buffer | — | — | $0.20 |
| **Total** | **~15** | — | **$3.00** |

### 6.3 Cumulative

| ფაზა | Cap | Cumulative |
|---|---|---|
| Through 7.4 | $79 | ~$27 |
| Phase 7.5 | $3 | $30 |

---

## 7. Sprint Retrospective Template

`docs/PHASE_7_5_RETROSPECTIVE.md`.

### 7.1 Metrics

| Metric | Target | Actual |
|---|---|---|
| Verifier PASS | 14/14 | __/14 |
| LLM spend | ≤ $3 | __ |
| Rules enforced at code layer | 13/13 | __ |
| Escape hatches documented | 13 | __ |
| Override-flow round-trip < 5 min | yes | __ |
| Phase 1-7.4 regression | GREEN | __ |

### 7.2 Sections

- Per-rule notes (which were trivial, which fought back)
- False-positive count in first 14 days post-deployment
- Override usage log (Day 14 audit)
- Carry-forward to Phase 7.6 (frontend must respect rule #1 CSP for NiiVue)

---

## 8. წყაროები

### 8.1 Constitutional AI inspiration

- [Anthropic Constitutional AI paper](https://www.anthropic.com/research/constitutional-ai)
- [Bai Y. et al. _Constitutional AI: Harmlessness from AI Feedback_ 2022](https://arxiv.org/abs/2212.08073)

### 8.2 Web security

- [MDN Content-Security-Policy reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy)
- [OWASP CSP cheatsheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)
- [Next.js middleware docs](https://nextjs.org/docs/app/building-your-application/routing/middleware)

### 8.3 Postgres constraints

- [Postgres CHECK constraint docs](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [Postgres trigger docs](https://www.postgresql.org/docs/current/sql-createtrigger.html)

### 8.4 Pydantic strict mode

- [Pydantic v2 strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/)

### 8.5 CI gating

- [GitHub Actions required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)

### 8.6 პროექტის ფაილები

- [74_PHASE_7_4_ACTIVE_LEARNING_2W.md](./74_PHASE_7_4_ACTIVE_LEARNING_2W.md)
- [ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md §9](../../ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md)
- [CLAUDE.md Phase VI redactor + Phase 6.1 lessons](../../CLAUDE.md)

---

**შემდეგი:** [76_PHASE_7_6_SITE_REFACTOR_3W.md](./76_PHASE_7_6_SITE_REFACTOR_3W.md)
