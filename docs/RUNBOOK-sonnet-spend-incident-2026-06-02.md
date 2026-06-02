# RUNBOOK — Sonnet 4-6 wasted-translate spend incident

> **2026-06-02** — Anthropic CSV ჩვენებდა $67/დღე (2026-06-01) + $46/დღე (2026-06-02) Sonnet 4-6 ხარჯს. ბანკში ფიქსირდებოდა auto-recharge ~$11.87 დღეში რამდენჯერმე. ფიქსი PR #9-ში.

---

## 1. რა მოხდა (TL;DR)

`scripts/chunking/process_ledger.py:populate_papers_from_ledger()` ledger-ის ყოველი row-სთვის ეძახდა `_build_papers_row()`-ს რომელიც 2× Sonnet 4-6 translate call-ს უშვებდა (title + abstract) — **შემდეგ** ამოწმებდა, paper უკვე არსებობდა თუ არა. 30-წუთიანი `chunking_trigger` cron-ი × 326 ledger row = ~31,000 ფუჭი call/დღე.

დამატებითი ფაქტორი: `translate.py` `_record_call()`-ს არ იძახდა, ანუ `runs.token_cost` ledger-ი **ბრმა იყო ამ ხარჯისთვის** — `daily-budget-gate` ვერ ხედავდა, რომ $50+/დღე იხარჯებოდა.

## 2. რა შეიცვალა (PR #9)

| ფაილი | ცვლილება |
|---|---|
| `scripts/chunking/process_ledger.py` | New `_ledger_row_identity()` derives (source, identifier) cheaply. Dedup ხდება translate-მდე. |
| `scripts/extraction/translate.py` | (a) SYSTEM_PROMPT-ი cache_control=ephemeral-ით; (b) `_record_call()` ყოველი Anthropic call-ის შემდეგ — გადატანა runs ledger-ში; (c) cache_creation_input_tokens + cache_read_input_tokens ჯამდება input_tokens-ში. |
| `tests/test_process_ledger_dedup_order.py` | Regression test — `build_bilingual` MUST be called 0 times when all papers exist; 2 times for new papers. |

## 3. დეპლოი (Shako-სთვის)

### A. PR #9 merge-ი → main
```
https://github.com/navyforses/ALEKSANDRA_BRAIN_v4/pull/9
```
- "Ready for review" → "Squash and merge"

### B. Railway worker რესტარტი
PR main-ში მერე, Railway-ში `aleksandra-worker-production`:
1. Settings → Deployments → "Deploy main" (manual trigger), ან
2. CLI: `railway redeploy --service aleksandra-worker-production`

ფიქსი მხოლოდ მაშინ მუშაობს, როცა worker-ი ახალ კოდს იხსნის.

### C. Anthropic Console-ში verify (1 საათში)
```
https://console.anthropic.com/settings/usage
```
- Daily view → Sonnet 4-6 output token rate
- მოსალოდნელია: 3.0M/დღე → **<200K/დღე**
- მოსალოდნელია: $45/დღე → **<$2/დღე**

### D. Supabase verify (1 საათში)
```sql
-- ახალი translate calls უნდა ჩანდეს runs ledger-ში
SELECT agent_id, COUNT(*), SUM(token_cost)::numeric(10,4) AS spend
FROM runs
WHERE kind = 'llm_call'
  AND agent_id = 'translate_to_georgian'
  AND start_time >= now() - interval '1 hour'
GROUP BY 1;
```
Pre-fix: ცარიელი (translate არ წერდა).
Post-fix: არანულოვანი, თუ chunking_trigger ფაირდა.

## 4. თუ რეგრესია მოხდება

`runs.token_cost`-ი ცოცხალია → `daily-budget-gate` $1.50/დღე-ს მიაღწევს როცა spend > cap → `BudgetExceeded` raise-ი → `chunking-tick` 429-ით დაბრუნდება n8n-ში → კოდი ჩერდება ავტომატურად.

ხელით kill: ნახე `docs/RUNBOOK-kill-switch.md`.

## 5. რა შეიძლება გავიგო ამ Incident-დან

1. **ყოველი Anthropic-ის გამოყენების point-ი უნდა წერდეს `runs` ledger-ში.** იყო latent bug 2026-05-31-დან (commit `4abb001` "bilingual research papers — title + abstract en→ka at ingest"), მაგრამ ბრმად 2-დღე ხარჯავდა იმიტომ, რომ ledger-ში არ ჩანდა.
2. **Dedup ვერდადგინებამდე ნუ გაიხდი ფული.** ეს უნდა იყოს code-review-ის checklist-ში პატერნად.
3. **Cron-ის ხშირი loop-ი + paid API call = audit რეალურ ხარჯზე, არა მხოლოდ ჩვენი ფორმულაზე.** Anthropic Console CSV უნდა ემოწმებოდეს `runs.token_cost`-ს კვირაში ერთხელ მაინც.

## 6. გასაკეთებელი მომდევნოში (P2)

- [ ] `_PRICING_USD_PER_M_TOKENS` ცხრილს დაუმატე `cache_creation_input_tokens` ($3.75/M) და `cache_read_input_tokens` ($0.30/M) — cache_control ჩართულია მაგრამ ცხრილი ჯერ ფლეტ input rate-ით ითვლის.
- [ ] `DEFAULT_DAILY_BUDGET_USD = 1.50` → `5.00` — ფიქსის შემდეგ რეალური ხარჯი <$2/დღე უნდა იყოს, ანუ $5 cap-ი მაინც headroom-ი იძლევა legitimate burst-ისთვის.
- [ ] Daily reconciliation script: ყოველდღე Anthropic CSV download → შედარება `runs.token_cost`-თან → Telegram alert თუ drift >20%.

---

**წყაროები:**
- Anthropic CSV: `claude_api_tokens_2026_06.csv` (uploaded 2026-06-02 by Shako)
- Bug location: `scripts/chunking/process_ledger.py:302-313` (pre-fix)
- Fix PR: navyforses/ALEKSANDRA_BRAIN_v4#9
- Commit: `e56df7b`
