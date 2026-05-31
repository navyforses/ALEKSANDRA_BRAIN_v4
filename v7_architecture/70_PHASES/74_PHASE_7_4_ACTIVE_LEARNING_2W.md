# Phase 7.4 — Active Learning: EIG + Question Generator (2 კვირა)

> **ფაზის ID:** 7.4
> **სახელი:** Active Learning — Expected Information Gain calculator + natural-language question generator + ცოლის Telegram flow
> **ვადა:** 14 დღე (2 კვირა), 2026-11-08 → 2026-11-21
> **მთავარი deliverable:** EIG calculator 13 განზომილებაზე, question generator (KA), rate-limited Telegram outbound (≤ 3/კვ), response parser (text + voice via Phase 5 Whisper), posterior update integration
> **წინაპირობა:** Phase 7.3 verifier 13/13 PASS · simulation engine ცოცხალი
> **LLM ბიუჯეტი:** $3 (question generation deterministic templates + occasional Sonnet polish)
> **ფიზიკური ბიუჯეტი:** $0 ნამატი

---

## 0. ფაზის სახელი, ვადა, წინაპირობა

### 0.1 სკოპი

ფაზა ცვლის ცოლის როლს პასიური დაკვირვების მიმწოდებლიდან აქტიური თანამშრომლამდე: ყოველ კვირას სისტემა ანგარიშობს რომელი დაკვირვება ცამდიდრებს ცოდნას ყველაზე მეტად (Shannon entropy reduction → EIG), თარგმნის მას ცოლისთვის გასაგებ კითხვად ქართულად, აგზავნის Telegram-ით (rate cap 3/კვ — Phase 5 manager_actions flow), იღებს პასუხს ხმოვანი ჩანაწერით ან ტექსტით, აპარსავს და განაახლებს Phase 7.0-ის posterior-ს.

### 0.2 ფაზის ვადა

| საზომი | მნიშვნელობა |
|---|---|
| სტარტი | 2026-11-08 |
| დასრულება | 2026-11-21 |
| სამუშაო დღეები | 10 |
| შაკოს ფოკუს საათები | ~30 |
| Verifier gate | Phase 7.5-მდე 10/10 PASS |

### 0.3 წინაპირობების checklist

| # | წინაპირობა | სტატუსი |
|---|---|---|
| 1 | Phase 7.3 closure | gate |
| 2 | Phase 7.0 posteriors live | ✅ |
| 3 | Phase 5 Telegram bot + Whisper transport | ✅ from v4 |
| 4 | Phase 6 ka.json i18n dictionary | ✅ |
| 5 | manager_actions rate-limiter pattern | ✅ from Phase 5 |
| 6 | ცოლის opt-in confirmation | required Day 0 |

---

## 1. დღიური Breakdown (10 დღე)

### კვირა 1 — EIG calculator + Question generator (Days 1-5)

| Day | ფოკუსი | ნაბიჯი | Outcome |
|---|---|---|---|
| 1 | EIG math primer | implement Shannon entropy `H(X) = -Σ p(x) log p(x)` over PyMC posterior samples ([Lindley 1956](https://www.jstor.org/stable/2237089)) | unit test on Beta posterior |
| 2 | Pre-/post-observation entropy | for candidate observation `o`, simulate posterior given `o` → `H(X|o)` → `EIG = H(X) - E_o[H(X|o)]` | EIG per dim computed |
| 3 | Candidate observation catalog | 13 dims × possible observation types (e.g., "5-min eye-tracking video", "1-min head-control timer") | catalog persisted |
| 4 | EIG ranker | top-K observations by EIG; cost-weighted (wife time ≤ 5 min/observation) | ranked list per week |
| 5 | Question template library | per-observation natural-language template (KA + EN) ([next-intl ka.json](../../viewer/messages/ka.json) reused) | 13 × 2 = 26 templates |

### კვირა 2 — Telegram flow + Response parser + Verifier (Days 6-10)

| Day | ფოკუსი | ნაბიჯი | Outcome |
|---|---|---|---|
| 6 | Question generator API | `POST /api/active/next-question` → top-1 EIG observation rendered as KA text | endpoint live |
| 7 | Telegram outbound integration | hook into Phase 5 `telegram_sender.py`; rate-limit guard (≤ 3 per ISO week) | rate test passes |
| 8 | Response parser | Whisper transcript or text → match to expected observation format (e.g., integer seconds for eye-tracking) | parser handles 5 sample responses |
| 9 | Posterior update integration | parsed response → EvidenceItem → Phase 7.0 `update()` → new posterior + delta logged | end-to-end flow works |
| 10 | Verifier + exit report | 10/10 PASS, tag `v7.4.0-active-learning` | green |

---

## 2. Deliverables

### 2.1 კოდი

| ფაილი | LOC |
|---|---|
| `brain/active/__init__.py` | 5 |
| `brain/active/entropy.py` | 140 |
| `brain/active/eig.py` | 260 |
| `brain/active/catalog.py` | 180 |
| `brain/active/ranker.py` | 120 |
| `brain/active/question_gen.py` | 200 |
| `brain/active/templates_ka.toml` | 90 |
| `brain/active/templates_en.toml` | 90 |
| `brain/active/telegram_flow.py` | 220 |
| `brain/active/response_parser.py` | 260 |
| `brain/active/rate_limiter.py` | 100 |
| `brain/active/tests/` (≥ 15 tests) | 450 |
| `migrations/020_active_questions.sql` | 70 |
| `scripts/verify_phase_7_4.py` | 240 |

ჯამური LOC: ~2425.

### 2.2 SQL

```sql
-- migrations/020_active_questions.sql
CREATE TABLE active_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dimension_id INT REFERENCES belief_dimensions(id),
    observation_type TEXT NOT NULL,
    eig NUMERIC NOT NULL,
    rendered_ka TEXT NOT NULL,
    rendered_en TEXT NOT NULL,
    sent_at TIMESTAMPTZ,
    chat_id TEXT,
    week_iso TEXT NOT NULL,
    response_received_at TIMESTAMPTZ,
    response_raw TEXT,
    response_parsed JSONB,
    evidence_id UUID REFERENCES belief_evidence(id),
    posterior_delta_kl NUMERIC
);

CREATE INDEX active_questions_week ON active_questions(week_iso);

CREATE TABLE active_rate_log (
    week_iso TEXT PRIMARY KEY,
    questions_sent INT NOT NULL DEFAULT 0,
    cap INT NOT NULL DEFAULT 3
);

ALTER TABLE active_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE active_rate_log ENABLE ROW LEVEL SECURITY;
```

### 2.3 Template example (KA)

```toml
# brain/active/templates_ka.toml
[eye_tracking_seconds]
template = "ცოლი, ამ კვირას მინდა ვიცოდე: რამდენი წამი დაიჭირა ალექსანდრამ თვალი {object}? ეს დაამცირებს ჩვენი გაურკვევლობას მის თვალის თვალყურდევნების ტრაექტორიაზე {eig_pct}-ით."
variables = ["object", "eig_pct"]
expected_format = "integer_seconds"

[head_control_seconds]
template = "ცოლი, ერთი დაკვირვება გთხოვ: რამდენ წამს იჭერს ალექსანდრა თავს ვერტიკალურად, როცა მუცელზე ედო? ეს გვაჩვენებს მისი ღეროს ფუნქციის გაუმჯობესებას."
variables = []
expected_format = "integer_seconds"
```

### 2.4 Rate limiter contract

```python
# brain/active/rate_limiter.py
WEEKLY_CAP = 3  # constitutional rule #11

def can_send_question(week_iso: str) -> bool:
    sent = pg.fetchval(
        "SELECT questions_sent FROM active_rate_log WHERE week_iso = %s",
        week_iso
    ) or 0
    return sent < WEEKLY_CAP

def record_sent(week_iso: str) -> None:
    pg.execute("""
        INSERT INTO active_rate_log (week_iso, questions_sent)
        VALUES (%s, 1)
        ON CONFLICT (week_iso) DO UPDATE SET questions_sent = active_rate_log.questions_sent + 1
    """, week_iso)
```

---

## 3. Blocking Dependencies

| დამოკიდებულება | ბლოკავს | Mitigation |
|---|---|---|
| Phase 7.0 posteriors | EIG input | gate |
| Phase 5 Telegram + Whisper | outbound + voice parsing | ✅ from v4 |
| Phase 6 ka.json dictionary + bilingual mirror | KA template rendering | ✅ |
| ცოლის opt-in confirmation | Day 6 send | required |
| n8n cron worker on Railway | weekly trigger | currently RED in v6.1 — must restart pre-Day 6 |

---

## 4. Verifier Checklist (10 ცდა)

| # | Check ID | აღწერა | PASS criterion |
|---|---|---|---|
| 1 | `check_7_4_01` | Entropy computation | Beta(2,8) entropy matches scipy reference within 1e-6 |
| 2 | `check_7_4_02` | EIG positivity | EIG ≥ 0 for all 13 dims |
| 3 | `check_7_4_03` | Ranker output | top-K observations returned with EIG descending |
| 4 | `check_7_4_04` | Template coverage | 26 templates (13 × 2 langs) present in TOML files |
| 5 | `check_7_4_05` | Question generator | renders valid KA + EN strings, no `{placeholder}` leak |
| 6 | `check_7_4_06` | Rate limiter | 4th send attempt in same week rejected |
| 7 | `check_7_4_07` | Response parser | parses 5 sample voice transcripts correctly |
| 8 | `check_7_4_08` | Posterior update | response → EvidenceItem → new posterior with non-zero KL |
| 9 | `check_7_4_09` | Telegram dry-run | message formatted but flagged `dry_run=true` → not sent |
| 10 | `check_7_4_10` | Regression | Phase 1-7.3 verifiers GREEN |

---

## 5. Rollback Strategy

### 5.1 Triggers

| Trigger | Severity | Action |
|---|---|---|
| Day 2: EIG computation diverges | CRITICAL | revert to entropy-only ranking (no expected reduction) |
| Day 7: rate limiter bypassed in test | CRITICAL | freeze outbound flow until fix; respect constitutional rule #11 |
| Day 8: response parser < 60% accuracy on samples | HIGH | escalate to manual שאקო triage for first month; defer auto-parse |
| Day 10: verifier ≤ 7/10 | HIGH | 1-week extension |
| Any: ცოლისგან negative feedback after first send | HIGH | freeze outbound; switch to opt-in confirmation per-question |

### 5.2 Rollback procedure

```sql
BEGIN;
DROP TABLE IF EXISTS active_rate_log CASCADE;
DROP TABLE IF EXISTS active_questions CASCADE;
COMMIT;
```

```bash
git revert <range>
```

### 5.3 Telegram outbound freeze

```python
# emergency switch in brain/active/telegram_flow.py
EMERGENCY_FREEZE = True  # if True, all sends return early with log entry
```

### 5.4 Compatibility

Phase 1-7.3 unchanged. Phase 5's existing wife-flow continues operating.

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
| Day 5: KA template polish (idiomatic) | 6 | Sonnet 4.5 | $1.00 |
| Day 7: rate-limiter code review | 3 | Sonnet 4.5 | $0.60 |
| Day 8: response parser edge cases | 5 | Sonnet 4.5 | $0.80 |
| Day 10: KA exit report | 2 | Sonnet 4.5 | $0.40 |
| Buffer | — | — | $0.20 |
| **Total** | **~16** | — | **$3.00** |

### 6.3 Cumulative

| ფაზა | Cap | Cumulative |
|---|---|---|
| Through 7.3 | $76 | ~$24 |
| Phase 7.4 | $3 | $27 |

---

## 7. Sprint Retrospective Template

`docs/PHASE_7_4_RETROSPECTIVE.md`.

### 7.1 Metrics

| Metric | Target | Actual |
|---|---|---|
| Verifier PASS | 10/10 | __/10 |
| LLM spend | ≤ $3 | __ |
| Templates | 26 | __ |
| Rate cap honored (Day 10 audit) | 100% | __% |
| Response parser accuracy | ≥ 80% | __% |
| Posterior KL avg per response | > 0 | __ |
| ცოლის satisfaction (Day 14 informal check) | positive | __ |

### 7.2 Sections

- What worked / didn't
- Template tone calibration (ცოლის feedback)
- Rate-limiter false positives
- Response parser failure modes
- Carry-forward to Phase 7.5 (constitutional rule #11 must be DB-enforced, not app-enforced)

---

## 8. წყაროები

### 8.1 Active learning / Bayesian experimental design

- [Lindley D.V. _On a Measure of the Information_ Annals of Math Stat 1956](https://www.jstor.org/stable/2237089)
- [Chaloner K. & Verdinelli I. _Bayesian Experimental Design Review_ Stat Sci 1995](https://www.jstor.org/stable/2246015)
- [Bayesian Experimental Design Wikipedia](https://en.wikipedia.org/wiki/Bayesian_experimental_design)
- [BoTorch Bayesian optimization](https://botorch.org/) — reference for EIG computation patterns
- [Foster A. et al. _A Unified Stochastic Gradient Approach to Designing Bayesian-Optimal Experiments_ AISTATS 2020](https://arxiv.org/abs/1911.00294)

### 8.2 Information theory

- Cover T. & Thomas J. _Elements of Information Theory_ 2nd ed. (2006) Wiley
- [scipy.stats.entropy reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.entropy.html)

### 8.3 პროექტის წინა ფაზები

- [Phase 5 manager_actions + Whisper transport — CLAUDE.md Phase V](../../CLAUDE.md)
- [Phase 6 ka.json + bilingual rules — CLAUDE.md Phase VI](../../CLAUDE.md)
- [73_PHASE_7_3_SIMULATION_ENGINE_3W.md](./73_PHASE_7_3_SIMULATION_ENGINE_3W.md)
- [ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md §8](../../ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md)

---

**შემდეგი:** [75_PHASE_7_5_CONSTITUTIONAL_2W.md](./75_PHASE_7_5_CONSTITUTIONAL_2W.md)
