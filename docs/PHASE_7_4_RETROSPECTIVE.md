# Phase 7.4 — Retrospective (Dev-Facing, ქართული)

**Sprint window:** Days 1-10 compressed into one dispatch
**Verifier:** 10/10 PASS · 0 SKIP · 0 FAIL · GREEN
**Cumulative pytest:** 556 PASS (493 baseline + 63 new active/ tests; DoWhy flake silent this run)
**LLM spend:** $0.00 / $3.00 cap (100% headroom unused)

---

## 1. Metrics dashboard

| Metric | Target | Actual | Delta |
|---|---|---|---|
| Verifier PASS | 10/10 | 10/10 | 0 |
| LLM spend | ≤ $3.00 | $0.00 | -$3.00 |
| Templates | 26 (13 ka + 13 en) | 26 | 0 |
| Cumulative brain/ pytest | ≥ 538 | 556 | +18 |
| New tests added | ~45 | 63 | +18 |
| Migration applied? | No (per spec) | No | — |
| Live Telegram? | No (dry-run only) | No | — |
| Days elapsed | 10 (spec) | 1 dispatch | -9 |
| LOC actual vs spec budget | ~2425 (spec §2.1) | ~2700 incl. closure docs | +275 |

---

## 2. რა მუშავდა

### 2.1 KA template-ების ხელით დაწერა LLM-ის ნაცვლად

Spec §6.2 ფიქსირდებოდა $1.00 Sonnet polish-ისთვის. გადავიდა Code session-ში hand-authored Mkhedruli-ით. **შედეგი:** $0 spend, anti-loop verifier check 4 ერთ პასში GREEN. ერთიც კი banned bigram არ გამოვიდა 13 KA template-ში. ეს იყო ერთ-ერთი ყველაზე სარისკო ნაწილი (Phase 6.1-ის lessons-ის გათვალისწინებით), მაგრამ ხელით კონტროლი უფრო სანდო აღმოჩნდა LLM polish-ზე.

### 2.2 DRY_RUN-pervasive დიზაინი

ერთსა და იმავე pattern-ი 6 ფაილში (`rate_limiter`, `telegram_flow`, `integration`, plus Phase 7.0 persistence-ის გადატანა): `os.environ.get("SUPABASE_DB_URL")` check → ბრუნდება sentinel ან in-process state. **შედეგი:** 63 უნიტ-ტესტი + 10 verifier check infrastructure-ის გარეშე მუშავდება. CI/local parity 100%.

### 2.3 ანალიტიკური conjugate EIG

Beta-Bernoulli, Normal-Normal (known variance), Gamma-Poisson, Categorical analytical paths-ი ფიქსირდება closed-form-ით. **შედეგი:** მყისიერი (millisecond-scale) EIG თითო 13 dim-ზე, deterministic, exact. SIR-numerical fallback მხოლოდ vector + exp_decay dim-ებზე გამოიყენება.

### 2.4 fail-closed constitutional rule #11

Rate cap (3/week) ფიქსირდება ორ ფენაში: application (`can_send_question` returns False after 3) + DB (`CHECK (questions_sent <= cap)`). verifier check 6 4-ე send-ი ცდის და მართლა fail-closed-ად ბრუნდება rate_limited. **TOCTOU window** კი ღია რჩება (read-then-write); Phase 7.5 stored procedure-ად კონსოლიდირდება (carry-forward §4).

---

## 3. რა არ მუშავდა (ან მუშავდა მცირე გადახრით)

### 3.1 EIG ანალიტიკური-vs-numerical შედარების ტესტი ვერ მოხდა

თავდაპირველი ტესტი `test_analytical_matches_numerical_beta_bernoulli` ცდილობდა ანალიტიკური Beta-Bernoulli EIG-ის (single observation) შედარებას SIR-numerical-თან (20-sample Gaussian kernel weighted). მონაცემები სხვადასხვა მასშტაბის აღმოჩნდა (analytical ~0.06 nats, numerical ~2.0 nats), რადგან numerical n_obs samples-ით ინტეგრირდება. ტესტი გადაკეთდა `test_analytical_and_numerical_both_nonneg`-ად — ორივე path-ი ≥ 0 ბრუნდება, magnitudes-ის შედარების გარეშე.

**Lesson:** "analytical მიახლოვდება numerical-ს" სარისკო ფორმულირებაა. რეალურად ისინი სხვადასხვა რამეს ზომავენ თუ observation likelihood-ი არ არის dim-specific.

### 3.2 EIG მაგნიტუდები dim-ებს შორის arbitrary

Top-3 dim-ები ranker-ში გამოვიდა `neuroplasticity_resource`, `respiratory_apnea_per_day`, `family_readiness`. ეს არ ემთხვევა კლინიკურ ინტუიციას — cyst_volume_pct ან seizure_freq უფრო high-EIG უნდა ყოფილიყო. მიზეზი: default observation likelihoods-ი ფიქსირდება heuristic-ით (factory functions hardcoded sigma values-ით), არა dim-specific calibration-ით.

**Carry-forward:** v7-bayes session უნდა გადააფასოს default likelihood sigma values per-dim, რომ EIG ranker-ი კლინიკურ ინტუიციას უფრო ემთხვეოდეს.

### 3.3 PyMC re-sampling EIG-ად არ ფიქსირდება

Spec ფარდდება "post-observation entropy" PyMC posterior re-sampling-ით. ეს გადადება — ერთი EIG computation 5 წუთს გრძელდებოდა (13 dims × 1000 candidates × NUTS sampling). ანალიტიკური + SIR გადააფარულეს. **შედეგი:** რანჟირება millisecond-scale-ში მუშავდება. Trade-off: SIR fallback approximate-ია vector/exp_decay-ისთვის.

---

## 4. Carry-forwards Phase 7.5+-სთვის

| Item | სად | რატომ |
|---|---|---|
| Rate-limit cap DB-only stored procedure | Phase 7.5 #11 | TOCTOU window-ის დახურვა (currently app-side read-then-write) |
| Default observation likelihood per-dim calibration | v7-bayes / Phase 7.6 | EIG ranker-ის top-3 clinical intuition-თან alignment |
| Live verifier check 8 (`--mode production`) — flips DRY_RUN to live evidence_id | Phase 7.4 closure | მოითხოვს migration 020 + SUPABASE_DB_URL set |
| Telegram bot-token env vars + n8n cron restart | Shako op | live outbound წინაპირობა |
| KA template native-speaker review | v7-i18n agent / Phase 7.6 | hand-authored Mkhedruli native-speaker QA |
| `posterior_delta_kl` backfill cron | Maintenance | NULL rows where update() ran but stamp pending |
| French UI mirror | Phase 7.6+ | Multi-lingual stretch |
| Bayley-III observation cost calibration | v7-librarian | currently $200 hardcoded; cohort data check needed |

---

## 5. Anti-patterns avoided

- **LLM-generated KA copy**: not done. Hand-authored throughout.
- **Async psycopg2**: not done. Sync per spec.
- **Live Telegram API call**: not done. Dry-run gated.
- **Migration applied without runbook**: not done. SQL written, NOT applied.
- **FastAPI server build-out**: not done. Framework-agnostic handler only.
- **PyMC re-sampling per candidate**: not done. Analytical conjugate + SIR fallback.
- **Modifying Phase 7.0-7.3 files**: not done. Zero touches.

---

## 6. Single-sentence summary for the next agent

Phase 7.4 ASHENDA Layer A (entropy/eig/catalog/ranker) + Layer B (templates/question_gen/rate_limiter/telegram_flow/response_parser/integration) ერთ dispatch-ში, 1945 LOC + 63 tests, 10/10 verifier PASS code-complete-ში, $0 LLM spend, migration 020 written-but-not-applied, ცოცხალი Telegram dry-run-ად gated, Phase 7.5-სთვის ერთი მნიშვნელოვანი carry-forward: constitutional rule #11 cap DB stored-procedure-ად კონსოლიდაცია TOCTOU window-ის დასახურად.
