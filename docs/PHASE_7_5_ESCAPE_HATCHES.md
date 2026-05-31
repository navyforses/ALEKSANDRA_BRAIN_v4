# Phase 7.5 — Escape Hatches for the 13 Constitutional Rules

> Every rule below has a documented, audited escape hatch. Use of any
> hatch writes one row to `constitutional_overrides` (migration 023)
> with rule_number, justification (>= 20 chars), actor, 24-hour
> auto-expiry, and a Telegram notification to the wife.
>
> The hatch substrate itself (the audit table) has NO constitutional
> override. Compromising the ledger is an out-of-band incident, not an
> in-band action.

## Global override flow

```python
from brain.common.guards import issue_override

override_id = issue_override(
    rule_number=N,                  # 1..13
    reason="<>= 20-char justification>",
    overridden_by="shako",          # actor identifier
    ttl_hours=24,                   # default; max enforced by DB CHECK + INTERVAL
    notify_wife=True,               # default; calls Telegram stub (Phase 7.6 live)
)
```

Returns:
- UUID string when SUPABASE_DB_URL is set.
- `DRY_RUN:<sha>` when SUPABASE_DB_URL is unset (tests, code-complete).

## Rule-by-rule

### Rule #1 — MRI / DICOM client-only

- **Statement:** No DICOM / NIfTI / octet-stream POST to `/api/*` is accepted.
- **Override flow:** `issue_override(rule_number=1, reason=..., overridden_by="shako")` + temporarily relax `viewer/middleware.ts` FORBIDDEN_UPLOAD_CONTENT_TYPES list via a feature flag. NOT recommended; an MRI on the server breaks the privacy posture.
- **Who can override:** only Shako (service-role required to deploy middleware change).
- **TTL:** 24 hours via constitutional_overrides; the middleware change itself must be reverted before the next push.
- **Notification:** wife Telegram (Phase 7.5 stub, Phase 7.6 live).
- **Revocation:** redeploy with the original middleware, OR allow the 24-hour override row to expire.

### Rule #2 — Voice ingest review required

- **Statement:** Any intake_drops row with source IN ('voice','whisper','telegram_voice') gets requires_review=true via DB trigger.
- **Override flow:** `issue_override(rule_number=2, ...)` + `DROP TRIGGER voice_review_required ON intake_drops` (service-role required).
- **Who:** Shako (service-role on Supabase).
- **TTL:** 24 hours; recreate the trigger via migration 021 rerun after the window.
- **Notification:** wife Telegram.
- **Revocation:** rerun migration 021 to recreate the trigger.

### Rule #3 — Citation mandatory

- **Statement:** Every Recommendation MUST carry a citation containing one of pubmed.ncbi.nlm.nih.gov / doi.org / PMID: / DOI: / github.com.
- **Override flow:** `issue_override(rule_number=3, ...)` + use a plain dict instead of the typed Recommendation (last-resort path).
- **Who:** any caller, but every use logs a row.
- **TTL:** 24 hours.
- **Notification:** wife Telegram.
- **Revocation:** switch the call site back to Recommendation.

### Rule #4 — Confidence intervals required

- **Statement:** Any output with expected_value / predicted_* MUST carry ci_low + ci_high companions.
- **Override flow:** `issue_override(rule_number=4, ...)` + bypass `reject_output_without_ci` at the call site.
- **Who:** any caller.
- **TTL:** 24 hours.
- **Notification:** wife Telegram.
- **Revocation:** restore the formatter call.

### Rule #5 — Bilingual parity

- **Statement:** Every text leaf surfaced to a human MUST exist in both en and ka.
- **Override flow:** `issue_override(rule_number=5, ...)` + skip `require_bilingual_parity` at the call site.
- **Who:** any caller; expected use during a locale rollout when ka translation is pending.
- **TTL:** 24 hours.
- **Notification:** wife Telegram.
- **Revocation:** add the missing ka string and re-enable the guard.

### Rule #6 — PHI filter

- **Statement:** Every string sent to an LLM, Telegram, Gmail, PDF, or external log MUST pass `assert_no_phi`.
- **Override flow:** `issue_override(rule_number=6, ...)` + use redacted text directly (NOT the unredacted original).
- **Who:** any caller. Use cases: PHI is itself the subject of the redaction-audit log (where false positives must be inspected).
- **TTL:** 24 hours.
- **Notification:** wife Telegram.
- **Revocation:** restore the assert call.

### Rule #7 — Budget hard stop

- **Statement:** No LLM call when projected daily spend > $5 or monthly > $60.
- **Override flow:** `issue_override(rule_number=7, ...)` + bypass `check_budget_or_raise`. Strongly discouraged.
- **Who:** Shako only.
- **TTL:** 24 hours.
- **Notification:** wife Telegram.
- **Revocation:** restore the budget gate; reconcile the spend on the next billing cycle.

### Rule #8 — Belief requires evidence

- **Statement:** `update(evidence=None)` is forbidden.
- **Override flow:** `issue_override(rule_number=8, ...)` + construct a BeliefEvidence stub with confidence=0.0 (preferred path; does NOT actually bypass the rule, just satisfies the type contract).
- **Who:** any caller; an actual override is almost never required because the BeliefEvidence type is cheap to construct.
- **TTL:** 24 hours.
- **Notification:** wife Telegram.
- **Revocation:** restore the real evidence row.

### Rule #9 — Hypothesis >= 3 supporting_papers when confirmed

- **Statement:** `UPDATE hypotheses SET status='confirmed' WHERE jsonb_array_length(supporting_papers) < 3` is rejected by `min_sources_when_confirmed` CHECK constraint.
- **Override flow:** `issue_override(rule_number=9, ...)` + `ALTER TABLE hypotheses DROP CONSTRAINT min_sources_when_confirmed`, run the INSERT/UPDATE, then re-add via migration 022 rerun.
- **Who:** Shako (service-role on Supabase).
- **TTL:** 24 hours.
- **Notification:** wife Telegram.
- **Revocation:** rerun migration 022 to recreate the constraint.

### Rule #10 — Simulation uncertainty guard

- **Statement:** `check_simulation_uncertainty_constitutional` raises BudgetGuardError when empirical avg sd/mean > 0.5.
- **Override flow:** `issue_override(rule_number=10, ...)` + call `check_simulation_budget` instead (the Phase 7.3 weaker check).
- **Who:** any caller. Use case: exploratory simulation runs where uncertainty IS the question.
- **TTL:** 24 hours.
- **Notification:** wife Telegram.
- **Revocation:** restore the constitutional check.

### Rule #11 — Wife question cap >= 3/week

- **Statement:** `active_rate_log.questions_sent <= active_rate_log.cap` enforced via CHECK + trigger.
- **Override flow:** `issue_override(rule_number=11, ...)` + `UPDATE active_rate_log SET cap = cap + 1 WHERE week_iso = '<current>'` within the override window.
- **Who:** Shako (service-role on Supabase).
- **TTL:** 24 hours.
- **Notification:** wife Telegram.
- **Revocation:** the next ISO week resets the per-week counter; the cap value resets on next n8n bootstrap of the row.

### Rule #12 — PDF >= 5 primary sources

- **Statement:** `assert_min_primary_sources` raises InsufficientSourcesError when count < 5.
- **Override flow:** `issue_override(rule_number=12, ...)` + skip the call at the PDF-builder site OR pass `minimum=N` to relax temporarily.
- **Who:** any caller. Use case: an interim PDF for the family where the canonical 5-source list is still being assembled.
- **TTL:** 24 hours.
- **Notification:** wife Telegram.
- **Revocation:** restore the call with `minimum=5`.

### Rule #13 — Verifier CI gate

- **Statement:** PR with any failing verifier (7.0..7.5) blocks merge.
- **Override flow:** `issue_override(rule_number=13, ...)` + GitHub branch-protection admin merge ("merge anyway" button) OR temporarily disable required-status-check on the branch.
- **Who:** Shako (GitHub admin on aleksandra-brane).
- **TTL:** 24 hours.
- **Notification:** wife Telegram.
- **Revocation:** re-enable the required status check; the next push triggers the workflow again.

## Audit query

```sql
SELECT
  rule_number,
  reason,
  overridden_by,
  created_at,
  expires_at,
  notified_wife_at
FROM constitutional_overrides
WHERE expires_at > NOW()
ORDER BY created_at DESC;
```

## Recovery on accidental override use

1. Apply the inverse migration / restore the bypassed call.
2. Leave the override row in place (DO NOT delete) — the audit trail is the value.
3. Run `scripts/verify_phase_7_5.py --mode production` to confirm green.
4. File a short post-mortem in `.handoffs/` describing what triggered the use.
