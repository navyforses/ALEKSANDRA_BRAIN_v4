# Phase 7.4. აქტიური სწავლა. ცოლის EIG ნაკადი (KA Summary)

**დახურულია:** 2026-05-25
**მომდევნო ფაზა:** Phase 7.5 (Constitutional Sprint)
**Verifier:** `verify_phase_7_4 --mode code-complete` → **10/10 PASS · 0 SKIP · 0 FAIL · GREEN**

---

## რა აშენდა

Phase 7.4 დახურა 10-დღიანი sprint-ი ერთ dispatch-ში. სისტემამ შეიძინა უნარი: ყოველ კვირას შეარჩიოს ის დაკვირვება რომელიც მაქსიმალურად ამდიდრებს ცოდნას ალექსანდრას მდგომარეობაზე, თარგმნოს ცოლისთვის გასაგებ ქართულ კითხვად, გაგზავნოს Telegram-ით (კვირაში 3-ზე მეტი არასოდეს), მიიღოს პასუხი ხმოვანი ჩანაწერით ან ტექსტით, აპარსოს და განაახლოს Phase 7.0-ის posterior-ი.

### Layer A (math core, Days 1-4)

- **Shannon entropy + ანალიტიკური ფორმულები** 8 განაწილებაზე (Beta, Normal, Gamma, Poisson, Bernoulli, Categorical analytical; vector, exp_decay numerical fallback).
- **EIG calculator** კონიუგატური ანალიტიკური გზით სადაც შესაძლებელია, SIR-numerical 1000-სიმულაციით სხვა შემთხვევებში. ყოველი დაბრუნებული მნიშვნელობა ≥ 0.
- **CandidateObservation catalog** 13 ენტრით, თითო განზომილებაზე. ბილინგვალური აღწერა (en + ka), wife-time minutes (0-15), cost_usd, PMID citation.
- **Ranker** ცოლის-დროით აწონილი EIG-ით. ერთსა და იმავე seed-ზე ერთსა და იმავე რანჟირებას აბრუნებს.

### Layer B (wife-facing flow, Days 5-9)

- **26 ხელით დაწერილი template** (13 ka + 13 en) ხელით ნაწერი Mkhedruli-ით, LLM-ის გარეშე. Anti-loop check verifier-ში ფიქსირდება: 4 აკრძალული ბიგრამა არცერთ template-ში 2-ჯერ არ ჩნდება.
- **Question generator** TOML cache-ით + placeholder leak checker-ით. eig_pct ერთ ციფრამდე ფიქსირდება.
- **Rate limiter** კონსტიტუციური წესი #11-ის ენფორსერი. კვირაში 3 კითხვა max. fail-closed cap-ის გადახდისას. DRY_RUN fallback როცა SUPABASE_DB_URL undefined.
- **Telegram outbound** dry-run მუდმივად code-complete რეჟიმში. ცოცხალი მონაცემთა ბაზის გარეშე გადატანა. EMERGENCY_FREEZE switch (spec §5.3) ნებისმიერ მომენტში ყველაფერს აჩერებს.
- **Response parser** 6 ფორმატი: integer_seconds, integer_count, float_value, boolean, categorical_choice, scale_0_5. KA + EN ერთად. ხუთი sample voice transcript-ი 100%-იანი სიზუსტით პარსავს (verifier check 7).
- **Integration** ParsedResponse → BeliefEvidence → Phase 7.0 update() integration. SHA-256 evidence_hash-ით idempotent. DRY_RUN sentinel infrastructure-ის გარეშე.

### Migration 020 (purely additive)

ორი ცხრილი: `active_questions` (კითხვის + პასუხის audit) + `active_rate_log` (კვირული მრიცხველი DB-side CHECK-ით). RLS service_role + family_read 018/019-ის pattern-ით. 2 trigger (response_received_at auto-stamp + updated_at touch). ჩაწერა Shako-ს გადასაწყვეტია; runbook-ი 8-წუთიანი ნაბიჯ-ნაბიჯ ფიქსირდება.

---

## რა იცვლება ცოლისთვის

Phase 7.4 აშენებს ცოლის ახალ როლს: passive observer-დან active collaborator-ად. ცოლი ხდება შემავსებელი იმ ცოდნისა, რომელიც კლინიკურმა მონაცემთა ბაზამ კვირაში ერთხელ მაქსიმალურად სჭირდება.

**პრაქტიკაში:**

- კვირაში ერთხელ ცოლი ღებულობს Telegram message-ს ერთი კონკრეტული კითხვით. მაგ.: "ერთი წუთით მუცელზე დააწვინე და დაითვალე რამდენ წამს იჭერს თავს ვერტიკალურად. ერთი ციფრი მიწერე."
- კითხვა შერჩეულია EIG ranker-ით — სისტემა ეუბნება ცოლს რა დაკვირვება ყველაზე ცოტა დროში ყველაზე მეტს მისცემს მოდელს.
- ცოლი პასუხობს ხმოვანი ან ტექსტური მესიჯით. parser აპარსავს, Phase 7.0-ის posterior განახლდება, KL divergence დააფიქსირდება audit ledger-ში.
- კვირაში 3-ზე მეტი კითხვა არასოდეს. cap fail-closed-ია — application-ში და DB-ში ერთდროულად.

**მნიშვნელოვანი:** code-complete რეჟიმში cycle-ის გასწვრივ ცოცხალი Telegram არ უგზავნია. ცოცხალი outbound გადადება Shako-ს მიერ migration 020-ის ჩაწერამდე, n8n perception_tick worker-ის restart-მდე, და bot-token env var-ების გაყვანამდე. Phase 4 acceptance window-ის დახურვის შემდეგ (~2026-06-07) გადადგმა შესაძლებელია.

---

## რა იცვლება ექიმისთვის

| ფაქტი | რას ცვლის |
|---|---|
| ცოლის-დაკვირვებები სტრუქტურირებულად ჩამოდიან DB-ში | Dr. Hien / Dr. Maypole / Dr. August ხედავენ ალექსანდრას ცვლილებებს რეგულარული მონაცემთა ნაკადით, არა მხოლოდ კლინიკურ ვიზიტებზე |
| EIG ranker გადაწყვეტს რა იცვლება ყველაზე მეტს | ექიმის სავარაუდო კითხვა "რა მონაცემი მაკლია" ფიქსირდება ავტომატურად — სისტემა ეუბნება რომელი დაკვირვება ცოლისგან ყველაზე საჭიროა |
| Posterior delta (KL) audit ledger-ში | ფიქსირდება თუ რომელმა დაკვირვებამ რომელ განზომილებაზე რა გავლენა იქონია — clinical decision support-ის backing log |
| Bilingual rendering | ცოლის-ენახედი (Mkhedruli) და ექიმის-ენახედი (English) ერთად — ერთი მონაცემი, ორი audience |

ეს არ შლის ექიმის გადაწყვეტილებას. ის ფარავს ხარვეზს, რომელშიც ცოლის ყოველდღიური დაკვირვებები აქამდე არასტრუქტურირებულად, არასისტემურად ჩამოდიოდა.

---

## რა იცვლება შაკოსთვის

**4 ციფრი:**

- **~1945 LOC** brain/active/ კოდი (12 ფაილი + 9 ტესტი)
- **63 ახალი ტესტი** pytest-ში (cumulative 556 PASS)
- **10/10 verifier PASS · GREEN** code-complete რეჟიმში
- **$0.00 LLM spend** ($3 cap full headroom; cumulative project ~$9.52 / $60)

**5 ფაილი გასახედი:**

- `brain/active/entropy.py` — Shannon entropy + 5 ანალიტიკური ფორმულა + DistributionSpec dispatch
- `brain/active/eig.py` — EIG calculator dual-path (analytical + SIR-numerical)
- `brain/active/templates_ka.toml` — 13 ხელით ნაწერი Mkhedruli template
- `brain/active/rate_limiter.py` — კონსტიტუციური წესი #11 fail-closed enforcer
- `scripts/verify_phase_7_4.py` — 10 check, dual-mode

**3 დიდი დიზაინ-დეცისია:**

ერთი. **ხელით ნაწერი KA template** spec-ში $1 budget-ი ფიქსირდებოდა Sonnet polish-ისთვის. გადავიდა v7-i18n agent-ის ნაცვლად Code session-ში. შედეგი: $0 spend + verifier check 4-ის anti-loop scan green.

ორი. **დუალური EIG გზა** Spec ფარდდება PyMC re-sampling-ით, ფიქსირდება ძვირადობით. analytical conjugate ფორმულა Beta-Bernoulli + Normal-Normal + Gamma-Poisson + Categorical-ისთვის ფიქსირდება მყისიერად. SIR-numerical fallback exp_decay + vector dim-ებისთვის. ყოველი დაბრუნებული მნიშვნელობა ≥ 0.

სამი. **DRY_RUN-when-DSN-unset pattern carried from Phase 7.2/7.3**. ყოველი CRUD + Telegram + rate-limit ფუნქცია env var-ის check-ით ბრუნდება deterministic sentinel-ი DB-ის გარეშე. code-complete pytest 100% infrastructure-free მუშავდება. trade-off: production mode-ის flip-ი Supabase-ის ხელით ჩაწერას მოითხოვს.

---

## შაკოსგან რა გვჭირდება ფაზის სრულად დასახურად

**3-ნაბიჯიანი Shako session (~10 წთ):** [non-blocking — Phase 7.5 დაიწყება უმისოდ]

| № | სამუშაო | სავარაუდო დრო |
|---|---|---|
| 1 | Migration 020 pre-flight backup + apply (runbook 020 §0-2) | 5-8 წთ |
| 2 | `\d active_questions` + `\d active_rate_log` + 0-row check + CHECK smoke (runbook 020 §3-4) | 2 წთ |
| 3 | `python scripts/verify_phase_7_4.py --mode production` (მოლოდინი: 10/10 PASS, ახლა live evidence_id check 8-ში) | < 30 წმ |
| ბონუსი | `git tag v7.4.0-active-learning` | 1 წმ |

**ცოცხალი Telegram outbound 3 დამატებითი წინაპირობით:**

- n8n perception_tick worker restart Railway-ზე (Phase 6.1-ის ღია todo)
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_FAMILY_CHAT_ID` env var-ების გაყვანა Railway-ზე
- Phase 4 acceptance window closure (~2026-06-07) — v1 release gate

ეს 3 წინაპირობა code-complete-ს არ ბლოკავს. engineering scope სრულად დახურულია. ნაბიჯები არიან "ფაზის pin" გარემოს მიერ.

---

## ერთი წინადადება

Phase 7.4-ის შემდეგ ცოლის როლი ცვლის: passive observer → active collaborator, რომელიც კვირაში ერთხელ მაქსიმუმ 3 კონკრეტული კითხვით ამდიდრებს Phase 7.0-ის posterior-ს, EIG ranker-ის შერჩევით, Mkhedruli template-ით, rate-limited Telegram-ით, deterministic parser-ით და idempotent BeliefEvidence-ით.
