---
status: pending
created: 2026-06-02
resolves_phase: maintenance
source: docs/RUNBOOK-sonnet-spend-incident-2026-06-02.md
owner: executor agent (code-only changes)
priority: P2 (operational hygiene; post-incident hardening)
estimated_window: 30 minutes (one PR, one verifier run)
related_pr: navyforses/ALEKSANDRA_BRAIN_v4#9
---

# Raise daily budget cap + add cache-aware pricing

## Context

PR #9 fixed the dedup-before-translate bug that drove Sonnet 4-6 spend to ~$67/day on 2026-06-01. Two follow-up items surfaced during that investigation:

1. **`DEFAULT_DAILY_BUDGET_USD = 1.50`** in `scripts/cognition/budget.py:51` is now a regression risk in the OPPOSITE direction. Post-fix steady-state spend is ~$1-2/day from legitimate Sonnet/Haiku calls (translate + Graphiti + relevance scoring + briefing). Any legitimate burst — e.g., 20 new papers fetched in one perception_6h tick — will trip the gate and halt the whole research loop, since each new paper now legitimately pays for 2 Sonnet 4-6 translates (~$0.005 each = $0.10/burst on top of the baseline). Recommend raising to **$5.00**, which still catches the 2026-06-01 regression shape (was $67/day) but gives 3-4× headroom for legitimate research bursts.

2. **Cache-aware pricing missing from `_PRICING_USD_PER_M_TOKENS`** in `scripts/cognition/llm.py:57-67`. PR #9 wired `cache_control={"type": "ephemeral"}` on the translate SYSTEM_PROMPT, and the translate `_record_call()` wrapper rolls cache_creation + cache_read tokens into `input_tokens`. But the pricing formula in `_compute_cost_usd()` treats them all at the flat input rate ($3/M for Sonnet) — Anthropic actually charges:
   - `cache_creation_input_tokens`: **$3.75/M** (1.25× input)
   - `cache_read_input_tokens`: **$0.30/M** (0.10× input)
   
   Today this is zero drift (SYSTEM_PROMPT is 95 tokens — below the Sonnet 1024-token cache threshold — so cache_* fields stay 0). But if any caller wraps a larger system prompt in `cache_control`, our `runs.token_cost` will silently overestimate by up to 10× on cache hits.

Neither item is blocking. Together they take ~30 min.

## Acceptance

### Change 1: budget cap raise
- [ ] `scripts/cognition/budget.py:51` `DEFAULT_DAILY_BUDGET_USD: float = 5.00` (was `1.50`)
- [ ] `workflows/daily-budget-gate.json:50` JS code `cap = parseFloat($env.DAILY_BUDGET_USD || '5.00')` (was `'1.50'`)
- [ ] `docs/RUNBOOK-kill-switch.md` — update the "$1.50/დღე" reference
- [ ] `scripts/verify_phase2_5.py` A.2 — check the new cap (if any hardcoded reference)

### Change 2: cache-aware pricing
- [ ] Refactor `_compute_cost_usd()` signature to accept `cache_creation_input_tokens` and `cache_read_input_tokens` separately.
- [ ] Update `_PRICING_USD_PER_M_TOKENS` to a structured form:
  ```python
  ("claude-sonnet-4-6", {
      "input": 3.00,
      "cache_write_5m": 3.75,
      "cache_read": 0.30,
      "output": 15.00,
  }),
  ```
- [ ] Update `_record_call()` signature to take cache token counts.
- [ ] Update `translate.py` to pass cache counts to `_record_call()` separately (currently it rolls them into `input_tokens`).
- [ ] Update `scripts/cognition/llm.py:call_claude` wrapper similarly.
- [ ] Add a unit test in `tests/test_llm_cost.py` covering all four token classes for Sonnet 4-6 and Haiku 4-5.

## Verifier impact

- [ ] `verify_phase2_5 A.2` — confirm cap-raise doesn't break the `today_spend > 0` invariant.
- [ ] `verify_phase3` — confirm budget gate still raises BudgetExceeded at the new threshold.

## References

- Anthropic prompt caching pricing: https://docs.claude.com/en/docs/build-with-claude/prompt-caching#pricing
- PR #9: navyforses/ALEKSANDRA_BRAIN_v4#9
- Incident runbook: `docs/RUNBOOK-sonnet-spend-incident-2026-06-02.md`
