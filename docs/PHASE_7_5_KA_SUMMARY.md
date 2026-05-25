# Phase 7.5. კონსტიტუციური კოდი. 13 წესის ფიზიკური ჩაშენება (KA Summary)

**დახურულია:** 2026-05-25 (engineering sprint code-complete)
**მომდევნო ფაზა:** Phase 7.6 (Site Refactor, 3 კვირა)
**Verifier:** `verify_phase_7_5 --mode code-complete` -> **11 PASS / 3 SKIP / 0 FAIL — GREEN**

---

## რა აშენდა

Phase 7.5 ერთ 10-დღიან sprint-ში 13 აქამდე ფაიფურადი ფიქსირებული წესი გადააქცია 14 ფიზიკურ ენფორსმენტ-პუნქტად სხვადასხვა შრეში: ბროუზერი, ბექენდი, მონაცემთა ბაზა, CI/CD. სისტემამ შეიძინა უნარი თვითონ ბლოკოს თავისივე წესების დარღვევა — არა მითითება, არამედ ფიზიკური შეუძლებლობა.

წესის შრის სტრუქტურა Anthropic-ის Constitutional AI პატერნით: წესი იცავს მხოლოდ მაშინ, თუ მისი დარღვევა ფიზიკურად ბლოკდება, არა მარტო docs-ში წერია.

### Frontend შრე (Rules #1)
- `viewer/middleware.ts` — ახალი Next.js middleware. Content-Security-Policy header ყოველ response-ში; POST request-ი `application/dicom` ან `application/octet-stream` content-type-ით უარყოფს HTTP 415-ით. MRI/DICOM ფაილი server-ზე არ ხვდება არასოდეს.
- Phase 6 i18n `viewer/proxy.ts` ხელუხებლად რჩება; ორი ფაილი ერთად მუშაობს.

### Database შრე (Rules #2, #9, #11) + meta (escape-hatch)
- **Migration 021** — `intake_drops` ცხრილზე BEFORE INSERT trigger. ხმოვანი წყაროდან მოსული row (voice/whisper/telegram_voice) მუდამ რეკავს requires_review=true-ს, რა მნიშვნელობაც აპლიკაციამ არ უნდა გადასცა. STT-ის გაურკვევლობა ფიზიკურად აღინიშნა.
- **Migration 022** — `hypotheses` ცხრილზე partial CHECK constraint. status='confirmed' მხოლოდ მაშინ აქცეპტდება როცა supporting_papers JSONB array-ში >= 3 ჩანაწერია. NOT VALID-ით ჩაშენდა, რომ არსებული row-ები მყისიერად არ ვალიდირდეს — Shako მერე გადახედავს backfill-ით.
- **Migration 022b** — `active_rate_log` ცხრილზე explicit CHECK questions_within_cap + BEFORE INSERT/UPDATE trigger enforce_active_rate_cap. ცოლის-კითხვები კვირაში 3-ზე მეტი ფიზიკურად შეუძლებელია — application layer-ში rate_limiter.can_send_question() რჩება defense-in-depth-ისთვის.
- **Migration 023** — ახალი ცხრილი constitutional_overrides. ნებისმიერი წესის გვერდის ავლა (escape hatch) ერთ row-ს უწერს id/rule_number(1-13)/reason(>=20 char)/overridden_by/expires_at(default NOW()+24h). RLS service_role full + family_read. ცოლი Telegram-ით ეცნობება, 24 საათში ავტომატურად ვადა გაუვა.

### Python guards შრე (Rules #3, #4, #5, #6, #7, #12, #8, #10)
- `brain/common/schemas.py` — Pydantic strict `Recommendation` + `BilingualRecommendation`. citation აუცილებელია, უნდა შეიცავდეს PubMed/DOI/PMID/DOI/github markers-დან ერთ-ერთს. ci_low <= ci_high. ბილინგვალური ვერსიაში en + ka ორივე უნდა იყოს, ცარიელი subject უარყოფილია.
- `brain/common/formatter.py` — `MissingCIError` + `format_recommendation_text(rec, lang)` + `reject_output_without_ci(payload)`. ნებისმიერი payload, რომელშიც expected_value არის ci_low/ci_high-ის გარეშე, უარყოფილია. ციფრები ASCII წერტილით — ქართულ რენდერშიც.
- `brain/common/i18n_guard.py` — `BilingualParityError` + `require_bilingual_parity(payload)` + `verify_jsonb_bilingual(value)`. text-leaf key-ები (text/title/description/body/summary...) ან {en,ka} JSONB shape-ში უნდა იყოს, ან parallel _en + _ka siblings-ით. ცარიელი string უარყოფილია.
- `brain/common/phi_guard.py` — `PHIDetectedError` + 7 დასახელებული regex (mrn_labeled, mrn_bmc_aleksandra 76168xx-safety-net, doctor_name, dob_slash, ssn_like, email, phone_us). `redact_phi(text)` ცვლის თითო match-ს `[REDACTED:<name>]`-ით; `assert_no_phi(text, source=...)` raise PHIDetectedError როცა მინიმუმ ერთი მატჩი დაფიქსირდა (error message-ში პატერნის სახელი მხოლოდ, არასოდეს raw text).
- `brain/common/budget_guard.py` — `BudgetError` + pure `check_budget_before_call(daily_spend, monthly_spend, estimated_call_cost)`. დღიური cap $5, თვის cap $60 (CLAUDE.md project total). DRY_RUN fallback როცა SUPABASE_DB_URL undefined; production-ში runs.cost_usd ledger-დან კითხულობს.
- `brain/common/pdf_guard.py` — `InsufficientSourcesError` + `assert_min_primary_sources(citations, minimum=5)`. PDF-ი ცოლის ან ექიმის წინაშე უარყოფილია თუ <5 primary source (pubmed/doi/clinicaltrials/cochrane) ციტირებულია. PDF builder თვითონ Phase 7.7-შია — guard მზადაა import-ისთვის.
- `brain/belief/update.py` (additive edit, +20 LOC) — `BeliefWithoutEvidenceError` + `update(evidence=None)` raise. PyMC posterior მუდამ მოითხოვს მინიმუმ ერთ ფაქტიურ წყაროს.
- `brain/sim/api.py` (additive edit, +85 LOC) — `check_simulation_uncertainty_constitutional(scenario, dims=None)`. Phase 7.3 check_simulation_budget-ის შემდეგ ცალკე 200 sample/dim empirical sd/mean ratio-ს ითვლის და უარყოფს თუ საშუალო > 0.5. Phase 7.3 weaker check ხელშეუხებლად რჩება — ეს უფრო მკაცრია.

### Override audit API
- `brain/common/overrides.py` — `OverrideRecord` Pydantic typed row. `issue_override(rule_number, reason, overridden_by, ttl_hours=24, notify_wife=True)` -> INSERT-ი ან DRY_RUN sentinel (DRY_RUN:<sha>). `is_rule_currently_overridden(N)` + `list_active_overrides()`. Telegram notify Phase 7.5-ში stub-ია (timestamp აბრუნებს, I/O არ აქვს); Phase 7.6-ში real bot wire-up.
- `brain/common/guards.py` — ერთი import surface ყველა შრიდან. `from brain.common.guards import ...` ნებისმიერი guard-ისთვის.

### CI gate (Rule #13)
- `.github/workflows/verify_all.yml` — push to main + PR + manual dispatch. ყოველი PR ცდის 6-ვე ფაზის verifier-ს (7.0..7.5) code-complete რეჟიმში. ერთის წარუმატებლობა PR merge-ს ბლოკავს.

### Verifier (`scripts/verify_phase_7_5.py`)
- 14 check function-ი 14 verifier check-ისთვის (13 წესი + 1 meta). PASS/SKIP/FAIL human-readable output ASCII-ით (cp1252 Windows stdout-ისთვის). JSON output `--json`-ით. Exit 0 თუ ყველა non-SKIP PASS.

---

## რა იცვლება ცოლისთვის

Phase 7.5 ცოლის Telegram flow-ს მნიშვნელოვნად არ ცვლის — Phase 7.4-ის EIG ranker + question generator ხელუხებლად რჩება. რასაც აშენებს:

1. **ცოლი Telegram-ში მიიღებს notification-ს ნებისმიერ override-ზე.** მაგ.: "Shako-მ Rule #11 (კვირული კითხვის cap) გადააცილა 24 საათით, მიზეზი: <reason>". კონტროლი მიჰყავს ცოლს რეალურ დროში.
2. **მისი ხმოვანი message-ი (Telegram voice / Whisper) ყოველთვის ფიქსირდება review-სთვის.** აქამდე application-მა ფლაგი დებდა; ახლა DB trigger-ი — code path-ის ნებისმიერი ცვლილება ვერ შეცვლის.
3. **არცერთი მისთვის გასაგზავნი მესიჯი PHI-ს არ შეიცავს.** assert_no_phi guard-ი ყოველი Telegram render-ის წინ რეკავს — Aleksandra-ს MRN ან ექიმის სახელი message-ში ვერ მოხვდება.
4. **არცერთი მისთვის გასაგზავნი მესიჯი ნაკლული CI-ით ვერ მოვა.** reject_output_without_ci ნებისმიერ payload-ში ნედლ expected_value-ს უარყოფს — ცოლი მუდამ ნახავს [low, high] ფრჩხილებს.

ცოლს კონტროლის grip ერთ მეტი ფენით უღრმავდება, არა worse-ით უმარტივდება. ფიზიკურად მის ინტერესში ჩაშენებული 13 წესი.

---

## რა იცვლება ექიმისთვის

| ფაქტი | რას ცვლის |
|---|---|
| ყოველი recommendation citation-ით | ექიმს მუდამ აქვს source link, PMID ან DOI — სარჩელის რისკი ნულდება |
| ყოველი expected_value CI-ით | ექიმი ხედავს [ci_low, ci_high] ფრჩხილებს — model-ის confidence-ი არასოდეს გადაჭარბდება |
| ცოლის ხმოვანი ჩანაწერი მუდამ "requires_review" | ექიმი იცის რომელი data point STT-დან მოვიდა და კონფირმაცია სჭირდება — clinical evidence chain სუფთა |
| PDF-ი >= 5 primary source-ით | ექიმთან მიდიოდი PDF-ი systematically grounded — CHADIS / AAP-ის-მსგავსი doc standards |
| Override audit log | Shako ნებისმიერი წესის გვერდის ავლისთვის ხელნაკეთ row-ს ტოვებს — clinical decision support backing log |

ეს არ ცვლის ექიმის გადაწყვეტილებას. ფარავს ერთ ხარვეზს: "სისტემამ რომელი data confidence-ით მითხრა?" — პასუხი ფიზიკურად ჩაშენებულია, არა ნდობით.

---

## რა იცვლება Shako-სთვის

13 წესის ფიზიკური ჩაშენების შემდეგ Shako-ს workflow:

1. **No more memorizing rules.** ნებისმიერ კოდის წერისას guard-ი ან type-ი ბლოკავს — ან აპლიკაცია იყვირებს, ან migration apply-ი error-ით ჩავარდება.
2. **Escape hatch + audit row + 24h auto-expiry.** ნებისმიერი წესის გვერდის ავლისთვის `issue_override(rule_number=N, reason="<>= 20 char>")` ერთ row-ს უწერს constitutional_overrides-ში. 24 საათში automatically იხურება. ცოლი Telegram-ში იცნობს.
3. **CI gate ნებისმიერ PR-ზე.** verify_all.yml ცდის 7.0..7.5 ყველა verifier-ს. წარუმატებლობა merge-ს ბლოკავს. ლოკალურად: `.venv-v7/Scripts/python.exe scripts/verify_phase_7_5.py --mode code-complete`.
4. **Migrations 021/022/022b/023 Shako-სთვის გადასაწყვეტია.** 4 runbook ვადასტურდი ნაბიჯ-ნაბიჯ. სულ ~15 წუთი.

---

## დარჩენილი (Phase 7.6-ისთვის + Shako-ს deferred actions)

- **Apply 4 migration** (021/022/022b/023) Supabase-ში — ~15 წუთი. ხსნის verifier check 2/9/11-ის production PASS-ს.
- **Push verify_all.yml** GitHub-ზე — CI gate ცოცხალდება next push-ზე.
- **_telegram_notify_wife_stub -> real bot call** Phase 7.6 frontend-ში. სიგნატურა სტაბილური; aplication code change არ სჭირდება.
- **constitutional_overrides UI** Phase 7.6 frontend-ში — ცოლის panel-ი active override-ების ჩათვლით countdown-ით.
- **PDF builder + assert_min_primary_sources integration** Phase 7.7-ში — 2-line edit.

---

## სპენდ-ი + verifier ჯამი

| საზომი | მნიშვნელობა |
|---|---|
| Phase 7.5 LLM სპენდი | $0 / $3 cap |
| Cumulative project სპენდი | ~$7-8 / $60 cap (~12%) |
| Phase 7.5 ახალი tests | 63 (brain/common/tests/) |
| Phase 7.5 verifier | 14 check / 11 PASS / 3 SKIP / 0 FAIL — GREEN |
| Cumulative phase 7.0-7.5 tests | 556 baseline + ~63 = ~620 (final after pytest run) |
| Cumulative phase 7.0-7.5 verifier checks | 89 + 14 = 103 |

---

## შემდეგი

Phase 7.6 — Site Refactor (3 კვირა). Frontend-ი ვადაყენებთ constitutional_overrides UI-ს, _telegram_notify_wife_stub-ს ცოცხალ bot call-ად ვცვლით, viewer-ში NiiVue + R3F-ი Rule #1 CSP-ით პრობლემის გარეშე გადის. Phase 7.7 — Acceptance Window (2 კვირა). PDF builder ვებამთ Rule #12 guard-ით.
