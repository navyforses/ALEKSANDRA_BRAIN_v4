# ALEKSANDRA_BRAIN — Phase 3 Triage Plan
## Cognition & Communication (7 working days)

**Date:** 2026-05-16 (drafted) → 2026-05-17 start
**Manager:** BRAIN_MANAGER
**Budget cap:** $12 total LLM spend, hard stop $10
**Owner-locked decisions:** see kickoff brief 2026-05-16
**Approval requirement:** Manager must show this plan to Shako before Day 1 executes.

---

## 1. Day 0 — Baseline Commit (prerequisite, ~15 minutes)

Phase 3 Readiness Sprint produced uncommitted work. Before Phase 3 implementation
starts, that work must land as a clean git baseline so deviations during Phase 3
are attributable.

Three logical commits:

| # | Commit subject | Files |
| --- | --- | --- |
| 1 | `chore(phase-2.5): sync docs to verified phase 2.5 reality` | `CLAUDE.md`, `README.md`, `.planning/ROADMAP.md`, `docs/PHASE_2_EXIT_REPORT.md`, `docs/PHASE_2_5_EXIT_REPORT.md`, `docs/RUNBOOK-kill-switch.md`, `docs/archive/*`, deleted `docs/ACTIVITY_DIAGNOSTIC_PLAN.md` and `docs/PHASE_2_LIVE_AUDIT.md` |
| 2 | `fix(phase-2.5A): n8n budget gate counts llm_call + add r2 endpoint to env example` | `workflows/daily-budget-gate.json`, `.env.example` |
| 3 | `feat(phase-2.5C): minimal /papers /therapies /timeline routes + nav consistency` | `viewer/app/papers/page.tsx`, `viewer/app/therapies/page.tsx`, `viewer/app/timeline/page.tsx`, `viewer/app/dashboard/page.tsx`, `viewer/app/hypotheses/page.tsx` |
| 4 | `docs(phase-3): readiness sprint artifacts (triage, plan, handout, readiness, scope, security, KA report)` | `TRIAGE_PLAN.md`, `docs/PHASE_3_PLAN.md`, `docs/PHASE_3_HANDOUT.md`, `docs/PHASE_3_READINESS.md`, `docs/SCOPE_DECISIONS.md`, `docs/SECURITY_AUDIT.md`, `docs/PHASE_3_READINESS_REPORT_KA.md` |

(That's 4 commits, not 3 — splitting #2 out from #3 keeps the budget-gate fix
isolated, which matters if it needs to be reverted independently.)

Day 0 gate: `git status` clean except for in-flight Phase 3 work after these
commits land. No new commits until Day 1 starts.

---

## 2. Day-by-Day Breakdown

### Day 1 — 2026-05-17 — Migration & Contacts Foundation

**Owner agent:** MIGRATION_AGENT (Manager-supervised)

**Tasks:**
1. Write `scripts/migrations/008_phase3_tables_and_rls.sql` covering:
   - **RLS tighten:** drop `"Service role full access" USING (true)` policies on
     `papers`, `therapies`, `pathways`, `brain_regions`, `hypotheses`, `contacts`,
     `relationships`, `clinical_trials`, `ingestion_log`, `discovery_reports`.
     Replace with two policies each: `*_service_all TO service_role FOR ALL` and
     `*_family_read TO authenticated FOR SELECT`.
   - **New table `outreach_log`** with explicit `phi_redacted BOOLEAN NOT NULL DEFAULT false`,
     `CONSTRAINT must_redact CHECK (phi_redacted = true)`, `language TEXT NOT NULL`,
     `gmail_draft_id TEXT`, `sent_at TIMESTAMPTZ`, `sent_by TEXT`,
     `trigger_event_id UUID`, `trigger_kind TEXT`, `confidence NUMERIC(3,2)`.
   - **New table `alerts_log`** with `tier TEXT CHECK (tier IN ('T0','T1','T2','T3','T4'))`,
     `confidence NUMERIC(3,2)`, `payload JSONB`, `delivered_at TIMESTAMPTZ`,
     `blocked_reason TEXT`, `phi_redacted BOOLEAN NOT NULL DEFAULT false`,
     `CONSTRAINT must_redact CHECK (phi_redacted = true)`.
   - **New table `briefs`** with `brief_week DATE NOT NULL UNIQUE`,
     `pdf_r2_path TEXT NOT NULL`, `sections JSONB NOT NULL`, `phi_redacted BOOLEAN NOT NULL DEFAULT false`,
     `CONSTRAINT must_redact CHECK (phi_redacted = true)`.
   - **Contacts table extension:** add `consent_full_name BOOLEAN DEFAULT false`,
     `consent_doctor_names BOOLEAN DEFAULT false`, `consent_hospital_names BOOLEAN DEFAULT false`,
     `outreach_language TEXT DEFAULT 'en'`, `last_contacted_at TIMESTAMPTZ`,
     `outreach_count INTEGER DEFAULT 0`.
   - **Indexes:** `outreach_log(contact_id, drafted_at)`, `alerts_log(tier, delivered_at)`,
     `briefs(brief_week)`.
   - All three new tables: RLS ENABLED, `*_service_all TO service_role`,
     `*_family_read TO authenticated FOR SELECT`.

2. **Migration human-OK gate:** Manager shows SQL diff to Shako. Run only after
   explicit approval. If approved, run in this order:
   - `psql $SUPABASE_DB_URL -f scripts/migrations/008_phase3_tables_and_rls.sql`
   - Smoke-test: anon GET on `papers`, `therapies`, `hypotheses` returns 401 or empty.

3. **Notion → Supabase contacts import:**
   - `scripts/import_contacts_from_notion.py` — idempotent, dedupe by email.
   - Default `consent_*` flags = `false`. Shako per-contact opt-in later.
   - Default `outreach_language = 'en'` unless name pattern strongly suggests otherwise.
   - Dry-run mode (`--dry-run`) prints what would import without writing.
   - Real run requires `--confirm` flag.

4. **`scripts/verify_phase3.py` skeleton** with 10 gates all initially RED.
   Follows the same pattern as `verify_phase2_5` — `--gate all`, `--gate CGM-NN`,
   table output with PASS/FAIL.

**Day 1 quality gate:**
- Migration 008 applied; RLS smoke test passes; CGM-10 turns GREEN.
- Contacts table has ≥75 rows (allow some Notion noise to be filtered).
- `verify_phase3.py --gate all` runs (output: 1/10 — only CGM-10 green).
- No regression: `verify_phase1` + `verify_phase2` + `verify_phase2_5` still green.

**Budget for Day 1:** $0 LLM spend (pure SQL + Python import + skeleton).

---

### Day 2 — 2026-05-18 — Safety Layers (parallel)

**Owner agents:** REDACTOR_AGENT + CONFIDENCE_AGENT + BANNED_PHRASE_AGENT
(can run truly in parallel — files are disjoint)

**Tasks:**

A. `scripts/communicator/phi_redactor.py` (REDACTOR_AGENT):
   - Input: raw text + recipient `contact_id` (None for internal).
   - Lookup `contacts.consent_*` flags for that contact.
   - Strip / redact unless the matching consent flag is `true`:
     - Full given name "Aleksandra" → "A.J." (unless `consent_full_name`)
     - DOB day patterns (`28.08.2025`, `Aug 28`, `28 აგვისტო`) → "Aug 2025"
     - MRN patterns (`MRN`, `7616818`, 7-digit standalone in clinical context)
     - Hospital names from configured list (BMC, Duke, Wisconsin) → "a U.S. hospital"
       unless `consent_hospital_names`
     - Doctor names from `contacts` where role=clinician → "a clinician"
       unless `consent_doctor_names`
     - Street addresses (regex on `\d+ .+(Street|St\.|Ave|Boulevard)`)
     - Any `viewer/.+\.nii(\.gz)?` or `.dcm` mentions → blocked outright
   - Returns `RedactionResult(text: str, redactions: list[Redaction], blocked: bool)`.
   - Default rule: when in doubt, redact.

B. `scripts/communicator/confidence_classifier.py` (CONFIDENCE_AGENT):
   - Pure-function scoring, no LLM call.
   - Inputs: `evidence_grade` (1-6 tier from ranking), `source_count`,
     `source_recency_years`, `direct_relevance`, `citation_round_trip_passed`.
   - Output: `score ∈ [0.0, 1.0]`.
   - Deterministic formula documented in docstring.
   - Labeled test set: `tests/fixtures/confidence_examples.jsonl` with ≥30 manually
     scored examples drawn from the existing 5 confirmed hypotheses + 12 therapy
     candidates + 326 ledger rows.

C. `scripts/communicator/banned_phrases.py` (BANNED_PHRASE_AGENT):
   - Hard list (case-insensitive, whole-phrase match):
     - "you should", "we suggest", "we recommend", "Aleksandra should",
       "outcome will be", "she will", "this proves", "this means you must",
       "start [a-z]+ treatment", "stop [a-z]+ medication", "increase the dose",
       "decrease the dose", "replace .* with"
     - Georgian: "უნდა მიიღოს", "უნდა შეწყდეს", "უნდა გაიზარდოს", "ვურჩევთ"
     - French: "vous devriez", "nous recommandons"
   - Returns `BannedPhraseResult(passed: bool, violations: list[Violation])`.
   - Test set: 30 known-bad strings + 30 known-good strings, ≥95% accuracy.

**Day 2 quality gate:**
- CGM-02 (PHI redactor) GREEN.
- CGM-06 (confidence classifier returns [0,1]) GREEN.
- CGM-08 (banned phrase detector) GREEN.
- No regression on prior verifiers.
- Now 4/10 green.

**Budget for Day 2:** $0 LLM spend (all deterministic).

---

### Day 3 — 2026-05-19 — Summarize + Language Routing

**Owner agent:** SUMMARIZER_AGENT

**Tasks:**

1. `scripts/communicator/language.py` — language detection (`langdetect` library —
   already in stack? if not, add justified). Maps detected to {'en', 'fr', 'ka'}.
   Falls back to `'en'` if confidence low.

2. `scripts/communicator/summarize.py` — core function:
   ```
   summarize(evidence_ids: list[UUID], recipient_kind: str, language: str)
     -> SummaryDraft(text, citations, confidence, banned_passed, redacted_text, blocked)
   ```
   - Retrieves evidence via the existing `retrieve(query, t_at=...)` facade (no
     bypassing into Graphiti/Qdrant directly).
   - Builds a structured prompt to Claude Sonnet 4.5: every claim → 1+ citation.
   - System prompt forbids: clinical advice, predictions, off-label framing,
     unsourced claims.
   - Output schema enforced via Anthropic tool-use (structured JSON).
   - Runs through `banned_phrases.check()` → if fail, retry once with fix-prompt,
     then block.
   - Runs through `confidence_classifier.score()` → records score.
   - Runs through `phi_redactor.redact(text, recipient_contact_id)` → records
     redactions.
   - Persists `runs` row with `kind='llm_call'`, `agent_id='communicator'`,
     `token_cost` populated.

3. Wire `agents/communicator.py` to expose tools:
   - `generate_summary(evidence_ids, recipient, language) -> SummaryDraft`
   - `redact_phi(text, contact_id) -> RedactionResult`
   - The other tools (`classify_tier`, `save_outreach_draft`, `render_weekly_brief`)
     come online Day 4–6.

4. Test fixture: `tests/fixtures/summarize_inputs.jsonl` with 10 sample inputs
   (mix of validated hypothesis, drug candidate, paper); run each, inspect output.

**Day 3 quality gate:**
- CGM-01 (every output has ≥1 citation per claim) GREEN.
- CGM-07 (language detection routes 30 samples correctly) GREEN.
- No regression.
- Now 6/10 green.

**Budget for Day 3:** $1–$2 LLM spend (10 summaries × ~$0.10 each, plus 1–2
retries for banned-phrase fix-prompts).

---

### Day 4 — 2026-05-20 — Tier Router

**Owner agent:** TIER_AGENT

**Tasks:**

1. `scripts/communicator/tier_router.py`:
   ```
   classify(event: Event) -> TierDecision(tier, confidence, reason)
   ```
   - **Rule-based first, LLM fallback for ambiguity.**
   - Rules:
     - PHI leak / blocked phrase / source round-trip fail → **T0**.
     - Confidence < 0.50 → **T4** by default (weekly appendix/internal review).
     - `event.kind` in `{trial_deadline_24h, researcher_reply, med_safety_alert, bmc_urgent}` AND `confidence >= 0.85`
       AND today's T1 count < 1 → **T1**.
     - `event.kind` in T1 list but T1 cap reached today → **T2** with `reason='t1_cap_reached'`.
     - `event.kind == 'action_within_7d'` AND `confidence >= 0.70` → **T2**.
     - `event.kind == 'significant_update'` → **T3**.
     - Everything else with non-trivial confidence → **T4** (weekly).
     - Quiet hours rule: T2 between 22:00–08:00 → defer to next 08:00 batch.
   - LLM fallback only when rule output is `ambiguous`.

2. T1 cap enforcement queries `alerts_log` for today:
   ```sql
   SELECT count(*) FROM alerts_log
   WHERE tier = 'T1' AND delivered_at >= today_start_utc
   ```
   If count >= 1, downgrade.

3. Labeled accuracy set: `tests/fixtures/tier_router_events.jsonl` with 100
   events. Hand-labeled by Manager from existing ledger/hypothesis/therapy
   rows. CGM-03 requires ≥90% accuracy match.

4. `workflows/tier_router_hook.json` — n8n webhook that Python posts each
   event to; n8n returns the tier decision asynchronously. (Or — simpler —
   Python calls directly and n8n only handles the *delivery* per tier.
   **Manager decision: keep Python authoritative; n8n only delivers.**)

**Day 4 quality gate:**
- CGM-03 (tier router ≥90% on 100 events) GREEN.
- T1 cap of 1/day enforced in code (proven by integration test).
- No regression.
- Now 7/10 green.

**Budget for Day 4:** $0.50 LLM spend (only the ambiguous-case fallback).

---

### Day 5 — 2026-05-21 — Outreach Drafts (Gmail API)

**Owner agent:** OUTREACH_AGENT

**Tasks:**

1. **Gmail API setup decision:** Use `google-api-python-client` directly (not
   Gmail MCP). Reason: we need precise control of draft creation, the OAuth
   flow needs to be initialized once, and MCP adds an indirection layer
   that isn't worth it for a single-purpose draft writer. Gmail MCP can
   be revisited Year-2 for inbox monitoring.
   - **New dep justified:** `google-api-python-client`, `google-auth`,
     `google-auth-oauthlib`. Add to `requirements.txt`. Document OAuth setup
     in `docs/RUNBOOK-gmail-api.md`.
   - OAuth scopes: `gmail.compose` only (NOT `gmail.send` — we don't auto-send).

2. `scripts/communicator/outreach_drafter.py`:
   ```
   draft_outreach(contact_id, evidence_ids, purpose, language) -> OutreachDraft
   ```
   - Calls `summarize()` with `recipient_kind='researcher'` or `'clinician'`.
   - Applies `phi_redactor` with the contact's consent flags.
   - Renders Gmail draft via API.
   - Inserts `outreach_log` row with `phi_redacted=true`, `gmail_draft_id=...`.
   - Updates `contacts.last_contacted_at` and increments `outreach_count`.

3. **Daily cap of 5 enforced:**
   ```sql
   SELECT count(*) FROM outreach_log
   WHERE drafted_at >= today_start_utc
   ```
   If count >= 5, return `OutreachDraft(blocked=True, reason='daily_cap_reached')`.

4. `workflows/outreach_review_queue.json` — daily 18:00 cron, Telegram message
   to Shako: "Today: 3 outreach drafts ready. /review to see them."

**Day 5 quality gate:**
- CGM-04 (Gmail drafts created, visible to Shako, NOT sent) GREEN.
- CGM-09 (daily cap of 5 enforced) GREEN.
- No regression.
- Now 9/10 green.

**Budget for Day 5:** $1.50 LLM spend (5 test drafts × $0.30; some re-runs).

---

### Day 6 — 2026-05-22 — Weekly Brief PDF

**Owner agent:** BRIEF_AGENT

**Tasks:**

1. **PDF library decision:** `weasyprint`. Reason: HTML+CSS templates, matches
   the "deterministic HTML or Markdown template" line in PHASE_3_PLAN.md,
   and keeps the brief design editable without Python changes.
   - **New dep justified:** `weasyprint`. Add to `requirements.txt`.
   - Document Windows install caveats (GTK runtime) in `docs/RUNBOOK-weasyprint.md`.

2. `scripts/communicator/weekly_brief.py`:
   ```
   render_weekly_brief(week_start: date) -> BriefArtifact(pdf_path, r2_path, sections)
   ```
   - Pulls last 7 days of T4 events from `alerts_log`.
   - Pulls top-3 papers by `relevance_score` ingested in week.
   - Pulls hypothesis status changes from `hypotheses` table.
   - Pulls outreach summary from `outreach_log`.
   - Pulls 0–3 family questions from a new optional `family_questions` table
     OR from a YAML at `scripts/communicator/questions_queue.yaml`. **Manager
     decision: start with YAML to avoid another migration.**
   - Renders each section. Empty sections render "No new items this week"
     (CGM-05 requires this).
   - Uploads PDF to R2 at `r2://aleksandra-brain-storage/briefs/{week_start}.pdf`.
   - Inserts `briefs` row with `phi_redacted=true`.

3. **Template:** `scripts/communicator/templates/weekly_brief.html` —
   1-page summary + citation appendix at the end. Citation appendix lists
   every PMID/DOI/NCT/URL referenced anywhere in the brief.

4. `workflows/weekly_brief.json` — Sunday 09:00 local time
   (timezone-aware: starts as `America/New_York` while in Boston/Durham, but
   the cron itself runs in UTC and the workflow computes local). Delivers via:
   - Telegram message with file attachment
   - Email backup (Gmail draft if auto-send disabled, otherwise Gmail send)
   - **Default for months 1–6: Telegram only + Gmail draft. Shako manually
     forwards the email if desired.**

5. **First dry-run:** generate brief from test fixtures. Visual review with
   Manager. Then a real dry-run from actual current week.

**Day 6 quality gate:**
- CGM-05 (Weekly Brief renders end-to-end) GREEN.
- Citation appendix lists every referenced source.
- No regression.
- Now 10/10 green.

**Budget for Day 6:** $1.50 LLM spend (1 dry-run brief + 1 real brief ≈ $0.50 each
plus iteration).

---

### Day 7 — 2026-05-23 — Verification & Exit

**Owner agent:** VERIFIER_AGENT (continuous), Manager (closing)

**Tasks:**

1. Full regression run:
   ```
   .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase1
   .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2 --gate all
   .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2_5 --gate all
   .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase3 --gate all
   ```
   Target: 10 + 19 + 16 + 10 = **55/55 green**.

2. If any RED, dispatch correction; re-test until green or escalate to Shako.

3. **First real Weekly Brief delivered Sunday 2026-05-24 09:00 ET.**
   (Sunday falls *after* Day 7 — the Saturday 2026-05-23 task is "everything
   ready for the auto-render on Sunday morning".)

4. **First real outreach draft reviewed by Shako.** Manager picks the most
   defensible candidate from `outreach_log` (cleanest evidence, established
   researcher, no PHI concerns) for Shako to review.

5. Write `docs/PHASE_3_EXIT_REPORT.md` (technical, English, same format
   as PHASE_2_EXIT_REPORT.md).

6. Write `docs/PHASE_3_COMPLETION_KA.md` (Georgian, non-technical, same
   format as `docs/PHASE_3_READINESS_REPORT_KA.md`):
   - One-sentence summary
   - What got built (plain language)
   - What works today (table)
   - Known issues
   - Cost & time recap
   - Decisions needed before Phase 4
   - Closing paragraph on meaning for Aleksandra

**Day 7 quality gate:**
- 55/55 verifiers green.
- Both exit reports written.
- First Weekly Brief queued for Sunday delivery.
- First outreach draft staged for Shako review.

**Budget for Day 7:** $0.50 (re-runs only).

---

## 3. Dependency Graph

```
Day 0 (Baseline commit)
   │
   ▼
Day 1 (Migration 008 + Contacts + verify_phase3 skeleton)
   │      Provides: outreach_log, alerts_log, briefs tables, ≥75 contacts
   │
   ├──► Day 2 (PHI Redactor)         ─┐
   ├──► Day 2 (Confidence Classifier) ├─ truly parallel, disjoint files
   └──► Day 2 (Banned Phrases)        ─┘
                │
                ▼
         Day 3 (Summarize + Language)
            requires: redactor, classifier, banned phrases
                │
                ▼
         Day 4 (Tier Router)
            requires: classifier (for thresholds)
                │
                ▼
         Day 5 (Outreach Drafter) ◄── requires: summarize + redactor + contacts
                │
                ▼
         Day 6 (Weekly Brief) ◄── requires: summarize + tier router + redactor
                │
                ▼
         Day 7 (Full Verification + Exit Reports)
```

**Critical path:** Day 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 (7 days).
**Parallelism in Day 2 saves no calendar time** (we're already on the critical
path) but reduces risk by making three small surface-area changes instead of
one large one.

---

## 4. Quality Gate Checkpoints

Manager's QA protocol at end of each day (same as Phase 3 Readiness Sprint):

1. **Diff review** — change matches assigned task.
2. **Scope check** — no agent expanded beyond what was asked.
3. **Verifier run** — relevant `verify_phase3 --gate CGM-NN` passes.
4. **Regression run** — `verify_phase1` + `verify_phase2` + `verify_phase2_5` still green.
5. **Documentation check** — does the change need a doc update (RUNBOOK, README, ROADMAP)?

If any check fails, Manager issues a correction command and re-reviews
after the fix. No work moves to the next day until current day is green.

Cumulative gate count target:

| Day | Cumulative gates green | New gates |
| --- | --- | --- |
| 1 | 1/10 | CGM-10 (migration + RLS) |
| 2 | 4/10 | CGM-02, CGM-06, CGM-08 |
| 3 | 6/10 | CGM-01, CGM-07 |
| 4 | 7/10 | CGM-03 |
| 5 | 9/10 | CGM-04, CGM-09 |
| 6 | 10/10 | CGM-05 |
| 7 | 10/10 | (re-verify all + regression) |

---

## 5. Budget Tracking Plan

**Cap:** $12 total LLM spend across all 7 days. Hard stop $10.

| Day | Estimated spend | Cumulative | Trigger if exceeded |
| --- | --- | --- | --- |
| 0 | $0.00 | $0.00 | — |
| 1 | $0.00 | $0.00 | — |
| 2 | $0.00 | $0.00 | — |
| 3 | $2.00 | $2.00 | Pause if >$3 |
| 4 | $0.50 | $2.50 | Pause if >$4 |
| 5 | $1.50 | $4.00 | Pause if >$6 |
| 6 | $1.50 | $5.50 | Pause if >$8 |
| 7 | $0.50 | $6.00 | Pause if >$10 (hard stop) |
| **Buffer** | $4.00 | $10.00 | Reserved for retries/fixes |

**Daily check:** Manager queries `runs` at end of each day:
```sql
SELECT sum(token_cost) FROM runs
WHERE kind = 'llm_call'
  AND start_time >= '2026-05-17'::date
```

If cumulative > daily trigger, Manager pauses, escalates to Shako with a
diagnostic (which call, which prompt, what blew up).

**The n8n daily-budget-gate fix from Day 0 commit** must be deployed to n8n
server before Day 3 starts. Python-side `check_daily_budget()` is the active
guard regardless.

---

## 6. Agent Assignments

| Agent | Day | Files owned | Read-only access |
| --- | --- | --- | --- |
| MIGRATION_AGENT | 1 | `scripts/migrations/008_*.sql`, `scripts/import_contacts_from_notion.py`, `scripts/verify_phase3.py` (skeleton) | All others |
| REDACTOR_AGENT | 2 | `scripts/communicator/phi_redactor.py`, `tests/fixtures/redactor_examples.jsonl` | All others |
| CONFIDENCE_AGENT | 2 | `scripts/communicator/confidence_classifier.py`, `tests/fixtures/confidence_examples.jsonl` | All others |
| BANNED_PHRASE_AGENT | 2 | `scripts/communicator/banned_phrases.py`, `tests/fixtures/banned_*.jsonl` | All others |
| SUMMARIZER_AGENT | 3 | `scripts/communicator/summarize.py`, `scripts/communicator/language.py`, `agents/communicator.py` (tool wiring) | All others |
| TIER_AGENT | 4 | `scripts/communicator/tier_router.py`, `tests/fixtures/tier_router_events.jsonl`, `workflows/tier_router_hook.json` | All others |
| OUTREACH_AGENT | 5 | `scripts/communicator/outreach_drafter.py`, `workflows/outreach_review_queue.json`, `docs/RUNBOOK-gmail-api.md`, `requirements.txt` (gmail deps only) | All others |
| BRIEF_AGENT | 6 | `scripts/communicator/weekly_brief.py`, `scripts/communicator/templates/weekly_brief.html`, `workflows/weekly_brief.json`, `docs/RUNBOOK-weasyprint.md`, `requirements.txt` (weasyprint only), `scripts/communicator/questions_queue.yaml` | All others |
| VERIFIER_AGENT | 1–7 | `scripts/verify_phase3.py` (after MIGRATION_AGENT seeds skeleton on Day 1) — read-only thereafter | All |

**No agent edits files outside its column without Manager approval.**

---

## 7. Hard Constraints (Manager-enforced)

1. **Migration 008 needs explicit Shako approval** before `psql` runs.
2. **Gmail OAuth scope = `gmail.compose` only**, never `gmail.send` in months 1–6.
3. **Every `outreach_log` / `alerts_log` / `briefs` insert must have `phi_redacted=true`.**
   The CHECK constraint enforces it at DB level; the application must call
   `phi_redactor` before insert.
4. **No new dependencies** beyond `google-api-python-client` (+ auth libs) and
   `weasyprint` (Day 5 and Day 6 respectively). Each justified above.
5. **Budget hard stop at $10.** Manager halts execution if exceeded.
6. **Tier-1 cap of 1/day** enforced in `tier_router.py`, proven by integration test.
7. **No schema change** outside migration 008. If a need is discovered mid-sprint,
   it's deferred to a Phase 3.5 sprint, not stuffed in.
8. **No deletion** of any pre-existing file without Manager approval and a
   SCOPE_DECISIONS entry.
9. **`verify_phase1` + `verify_phase2` + `verify_phase2_5` must remain green
   every single day.** Any regression is a Day-stop.
10. **All commits use Conventional Commits** (`feat(phase-3):`, `fix(phase-3):`,
    `docs(phase-3):`).

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Notion contacts have malformed emails | Medium | Low | Dry-run mode + email validation step in import; skip-and-log invalid rows |
| weasyprint fails on Windows | Medium | Medium | Pre-Day-6 smoke test on a hello-world PDF; fall back to ReportLab if blocking |
| Gmail OAuth setup blocks Day 5 | Medium | Medium | Manager kicks off OAuth flow on Day 1 evening as a parallel task; if blocked by Sat, Day 5 ships drafts as JSON-in-Supabase only, Gmail wiring deferred to Phase 3.5 |
| LLM banned-phrase fix-prompt loops | Low | Medium | Hard retry cap = 1; if second attempt still has banned phrase, block and log |
| Migration 008 breaks anon access the viewer relied on | Low | High | Viewer uses service-role server-side, so RLS tighten is fine; CGM-10 explicitly tests anon 401 *and* service-role 200 to prevent both failure modes |
| Tier router hand-labeled accuracy set is biased | Medium | Medium | Manager labels 100; Shako spot-checks 10; if Shako disagrees on ≥2 of 10, relabel before CGM-03 measures accuracy |
| Confidence formula is wrong | Medium | Low | Day 2 ships with a transparent formula; Day 7 exit report includes a rubric review so Shako can adjust constants in Phase 3.5 |
| Weekly Brief generates on Saturday before fresh data lands | Low | Low | `weekly_brief.json` cron is set to Sunday 09:00 local, not Saturday |

---

## 9. What Phase 3 Does NOT Do (explicit out-of-scope)

- **No auto-send** of any outbound email or Telegram for months 1–6.
- **No clinician chat / Q&A interface.**
- **No MRI integration** beyond the existing client-side viewer routes.
- **No Adaptive GoT MCP** integration.
- **No LightRAG retrieval rewrite.**
- **No 6-MCP drug repurposing** expansion.
- **No Notion write-back** (Notion stays read-only mirror).
- **No new viewer pages** (the three from Readiness Sprint suffice).
- **No mobile push notifications** (Telegram is the family channel).
- **No multi-language UI** in the viewer (English chrome only).

These are NOT failures — they are intentional scope discipline.

---

## 10. Definition of Done

Phase 3 is closed when ALL of these hold:

- [ ] `verify_phase3 --gate all` returns 10/10 PASS.
- [ ] `verify_phase1` + `verify_phase2` + `verify_phase2_5` still green.
- [ ] Migration 008 applied; RLS smoke test confirms anon 401 on base tables.
- [ ] ≥75 contacts in Supabase with default `consent_*` = false.
- [ ] First real Weekly Brief PDF rendered, in R2, delivered Sunday 2026-05-24.
- [ ] First real outreach draft staged in Gmail drafts, visible to Shako.
- [ ] No T1 alert sent in the first week that violates the 1/day cap.
- [ ] `docs/PHASE_3_EXIT_REPORT.md` written.
- [ ] `docs/PHASE_3_COMPLETION_KA.md` written (Georgian, non-technical).
- [ ] Total LLM spend < $10.

---

## 11. Approval Block

This plan executes only after Shako says "approved" (or equivalent).

If Shako wants changes, Manager edits this file and reshows. No Day 1 work
starts without approval.

**Pending Shako decisions on this plan:**
- Are the agent assignments OK?
- Is the budget split acceptable?
- Is `weasyprint` (vs `ReportLab`) acceptable?
- Is `google-api-python-client` direct (vs Gmail MCP) acceptable?
- Should the family_questions queue be a YAML file (Manager recommendation)
  or a new Supabase table?

**Approval signal:** Shako replies "approved" or "approved with changes: …".

---

**End of TRIAGE_PLAN_PHASE_3.md.**
