# Phase 3 Readiness Plan

**Date:** 2026-05-16
**Sprint mode:** Design only
**Owned artifacts:** `docs/PHASE_3_PLAN.md`, `docs/PHASE_3_HANDOUT.md`

## Executive Verdict

Phase 3 is ready to design, but this sprint does not implement code, schemas,
workflows, or live sends. Phase 1, Phase 2, and Phase 2.5 verifiers are green;
Phase 2.5B/C/D are complete; the next step is to specify the contracts that
make family-facing cognition safe enough to build.

Phase 3 implementation should activate four user-visible capabilities:

1. Communicator activation for safe family-facing drafts.
2. Alert tier refinement for urgency, batching, and human control.
3. Email outreach automation for researcher and clinician follow-up drafts.
4. Weekly Brief PDF for a readable weekly evidence packet.

The core rule for all four is simple: no unsourced claim, no clinical decision
language, no outbound message without an auditable approval path.

## Entry Criteria

Phase 3 implementation may start only when these remain true at the beginning
of the implementation sprint:

| Criterion | Required state | Current evidence |
| --- | --- | --- |
| Phase 1 regression | `scripts.verify_phase1` passes | README lists Phase 1 closed, 10/10 PASS |
| Phase 2 memory | `scripts.verify_phase2 --gate all` passes | `docs/PHASE_2_EXIT_REPORT.md`, 19/19 PASS |
| Phase 2.5 quick wins | `scripts.verify_phase2_5 --gate all` passes | `docs/PHASE_2_5_EXIT_REPORT.md`, 16/16 PASS |
| Family-visible base | Dashboard, urgent alert run, daily digest run exist | Phase 2.5C closed |
| Validation base | Confirmed hypotheses and hydrated supporting papers exist | Phase 2.5D closed |
| Spend tracking | Positive-cost LLM rows can be written to `runs` | Phase 2.5A closed |
| Retrieval contract | Agents retrieve through `retrieve(query, t_at=...)` | Phase 2 MEM-05 |
| Source contract | Citation tuple and source stamps exist | Phase 2 MEM-01/MEM-04 |
| Stop control | Telegram/n8n kill-switch remains available | Phase 0/2 audit contract |
| Family approval policy | Human approval levels are documented before first send | New Phase 3 design requirement |

If any verifier regresses, Phase 3 implementation pauses until the regression is
fixed. Phase 3 should not paper over lower-layer failures.

## Non-Goals

- No code, migration, workflow, or infrastructure changes in this design sprint.
- No automatic medical advice, diagnosis, prescription, dosage, or therapy
  recommendation.
- No message that tells the family to start, stop, increase, decrease, or
  replace a treatment.
- No live email or Telegram send from newly designed Phase 3 flows until a human
  approval gate exists and is tested.
- No bulk email campaign, CRM rebuild, or contact enrichment project.
- No new memory architecture, direct Graphiti/Qdrant access from agents, or
  bypass of the `retrieve()` facade.
- No full 6-MCP drug repurposing expansion unless it is split into its own
  future sprint.
- No PDF containing PHI unless the redaction and approval mode explicitly allow
  it.

## Design Principles

- **Source first:** every family-facing claim must point back to a PMID, DOI,
  NCT ID, URL, or ledger row that round-trips.
- **Evidence before urgency:** urgency follows evidence tier and actionability,
  not model confidence alone.
- **Draft before send:** Phase 3 produces staged communication objects before
  any transport adapter sends them.
- **Clinicians decide:** wording must frame outputs as discussion material for
  clinicians and researchers.
- **Small surface area:** Telegram, Gmail, dashboard, and PDF are channels over
  the same evidence contract, not four separate reasoning systems.
- **Append-only audit:** every draft, approval, send, skip, and cost-bearing
  model call should write an append-only run or communication event.

## Workstream 1: Communicator Activation

### Goal

Turn the Communicator from a skeleton into a guarded drafting agent that can
prepare family-facing messages from validated evidence events.

### Inputs

- `retrieve(query, t_at=...)` results with citation stamps.
- Confirmed hypotheses and hydrated supporting papers from Phase 2.5D.
- Repurposing candidates with evidence summaries.
- Trial status changes and high-relevance ledger rows.
- Family preferences: channel, language, redaction level, quiet hours.

### Output Contract

Every Communicator draft should be represented as a structured object before it
can be rendered into Telegram, email, dashboard, or PDF.

| Field | Purpose |
| --- | --- |
| `draft_id` | Stable identifier for audit and approval |
| `source_event_id` | Link to hypothesis, therapy, trial, ledger, or workflow event |
| `audience` | `family`, `clinician`, `researcher`, or `internal` |
| `channel` | `telegram`, `email`, `dashboard`, `pdf`, or `notion` |
| `alert_tier` | Refined tier from the router |
| `title` | Short factual heading |
| `summary` | Plain-language finding |
| `why_it_matters` | Non-clinical relevance explanation |
| `evidence_items` | Source IDs, titles, dates, confidence, and evidence grade |
| `recommended_next_step` | Allowed family action such as "Discuss with clinician" |
| `forbidden_action_check` | Result of clinical-command lint |
| `phi_classification` | `none`, `minimal`, `sensitive`, or `blocked` |
| `redaction_status` | `not_needed`, `redacted`, `requires_review`, or `blocked` |
| `approval_status` | `draft`, `needs_review`, `approved`, `sent`, `skipped`, `blocked` |
| `transport_metadata` | Message ID, thread ID, PDF path, or webhook result after send |

### Language Guardrails

Allowed next-step verbs should be review-oriented:

- `Review`
- `Discuss`
- `Ask`
- `Save`
- `Track`
- `Share`
- `Schedule a clinician conversation about`

Blocked clinical-command verbs include:

- `Administer`
- `Start`
- `Stop`
- `Increase`
- `Decrease`
- `Replace`
- `Diagnose`
- `Prescribe`
- `Ignore`

The Communicator may say "This may be worth discussing with Dr. X" but must not
say "Aleksandra should receive X."

### Acceptance Target

Communicator activation is ready for implementation when the team can describe
the full dry run:

`source event -> evidence ranking -> alert tier -> draft object -> redaction -> language lint -> approval -> channel render -> append-only log`

## Workstream 2: Alert Tier Refinement

### Goal

Refine the original urgent/important/weekly model into deterministic routing
that balances safety, urgency, and family calm.

### Proposed Tiers

| Tier | Name | Channel | Timing | Examples | Approval mode |
| --- | --- | --- | --- | --- | --- |
| T0 | Blocked | None | Never sent | Failed source check, PHI leak, clinical command, duplicate | Must be fixed or discarded |
| T1 | Urgent | Telegram plus dashboard | Immediate, quiet-hours override allowed | Trial enrollment deadline, direct safety notice, clinician deadline | Templated alert may auto-stage; action text needs approval |
| T2 | Action Needed | Telegram digest plus dashboard | Same day | Borderline paper needs family include/exclude, contact follow-up due | Human approval before send |
| T3 | Important | Dashboard plus daily digest | Daily batch | New relevant paper, moderate hypothesis update, candidate status change | Batch approval |
| T4 | Weekly | Weekly Brief PDF plus email | Weekly, default Sunday 09:00 local | Evidence summary, outreach status, open questions | Approve final PDF/email |

### Routing Rules

- Failed source round-trip always routes to T0.
- PHI classification `blocked` always routes to T0.
- A duplicate event within the configured dedupe window is downgraded or skipped.
- Only high evidence plus time-sensitive actionability can route to T1.
- Medium evidence routes to T2 or T3, never T1.
- Low evidence can appear only in T4 appendix or internal review.
- Family questions use T2 unless a real deadline makes them T1.
- Outreach drafts never auto-send; they stage as T2.

### Family Controls

- Quiet hours apply to T2-T4.
- T1 may bypass quiet hours only for approved categories.
- `/stop` or equivalent kill-switch stops all outbound transports.
- A daily maximum prevents alert fatigue.
- The dashboard remains the canonical place to see skipped, staged, and sent
  items.

## Workstream 3: Email Outreach Automation

### Goal

Create a human-approved email drafting flow for researchers, clinicians, trial
coordinators, foundations, and program contacts.

### Scope

The system may draft, queue, and track emails. It should not mass-send. First
implementation should require human approval for every send.

### Inputs

- Contact list with role, institution, email, relationship, and follow-up date.
- Evidence packet relevant to the contact.
- Outreach purpose: update, question, introduction, follow-up, or thank-you.
- Family-approved redaction level.
- Prior thread context when available.

### Output Contract

| Field | Purpose |
| --- | --- |
| `outreach_id` | Stable audit ID |
| `contact_id` | Link to contact source |
| `purpose` | `question`, `follow_up`, `update`, `intro`, or `thanks` |
| `recipient_email` | Final checked address |
| `subject` | Draft subject line |
| `body_plain` | Plain text body |
| `body_html` | Optional rendered body |
| `evidence_refs` | Source IDs cited or attached |
| `phi_classification` | Redaction mode |
| `approval_status` | Draft lifecycle |
| `gmail_thread_id` | Filled after send or reply match |
| `follow_up_date` | Next suggested contact date |

### Outreach Guardrails

- No bulk mail merge in Phase 3 minimum.
- Maximum default send rate: 5 approved outbound emails per day.
- No attachments by default; link or summarize evidence instead.
- No PHI unless a family-approved recipient and redaction mode allow it.
- Every email must include a clear human-authored or human-approved intent.
- Replies should be captured for tracking, but not auto-answered.

### Acceptance Target

Email outreach is ready for implementation when one dry-run email can be staged
for a known contact, cite a validated evidence packet, pass redaction checks,
wait for approval, and log the intended follow-up date without sending.

## Workstream 4: Weekly Brief PDF

### Goal

Produce a weekly family-readable PDF that summarizes what the brain found,
what needs review, and what changed since the last brief.

### Default Sections

1. Cover: week range, generated timestamp, redaction mode, and approval status.
2. One-page summary: major changes, open decisions, and upcoming deadlines.
3. New evidence: papers, trials, and preprints grouped by relevance.
4. Hypotheses: confirmed or changed hypotheses with confidence and citations.
5. Repurposing watch: candidates worth monitoring, not treatment advice.
6. Outreach queue: sent, waiting, due, and suggested next contacts.
7. Family questions: items needing a yes/no or free-text family decision.
8. Appendix: citation table with PMID/DOI/NCT/URL, retrieval timestamp, and
   source confidence.

### Rendering Requirements

- PDF should be generated from a deterministic HTML or Markdown template.
- All claims in summary sections must appear in the appendix.
- Empty sections render as "No new items this week" rather than disappearing.
- PDF filename should include week start date and redaction mode.
- The same source packet should be renderable to dashboard and email summary.
- The approved PDF may be attached to a weekly email after the approval gate.

### Acceptance Target

Weekly Brief PDF is ready for implementation when a dry run can render a
non-empty PDF from test evidence, include citation appendix rows, pass redaction
checks, and stage the weekly email without sending.

## Dependency Map

| Dependency | Used by | Readiness | Notes |
| --- | --- | --- | --- |
| `retrieve(query, t_at=...)` | Communicator, Weekly Brief, outreach context | Ready | Single retrieval facade from Phase 2 |
| Evidence ledger citation tuple | All outbound claims | Ready | Required for source-first drafting |
| Qdrant/Graphiti stamps | Evidence traceability | Ready | Supports reverse walk to source |
| Confirmed hypotheses | Alerts, PDF, outreach | Ready | Phase 2.5D complete |
| Repurposing candidates | Alerts, PDF, outreach | Partial | Good for monitoring; full 6-MCP dossier remains future scope |
| Family dashboard | Staged items and audit view | Ready | Phase 2.5C complete |
| Telegram/n8n | T1/T2 alert transport | Ready enough | Must honor kill-switch and quiet hours |
| Gmail | Outreach and weekly email | Needs connector/runtime check | Draft-first design avoids live-send risk |
| Contact data | Outreach automation | Needs source confirmation | Must identify canonical contact store before build |
| PDF renderer | Weekly Brief | Needs implementation choice | Candidate: HTML-to-PDF with deterministic template |
| `runs.token_cost` | Budget gates | Ready | Phase 2.5A positive-cost row exists |
| Approval store | All sends | Needs implementation design | Could be Supabase table or existing workflow state |
| Redaction policy | All family/outreach surfaces | Needs family decision | Redaction modes must be approved before use |

## Proposed Implementation Order

This order is for the next implementation sprint, not this design-only sprint:

1. Define Phase 3 verifier gates and fixture data before feature code.
2. Implement source round-trip and evidence ranking gates.
3. Implement Communicator draft schema and language/redaction lint.
4. Implement alert tier router with deterministic examples.
5. Implement Weekly Brief PDF dry-run renderer.
6. Implement email outreach draft queue and approval flow.
7. Wire transports only after dry-run gates pass.
8. Run Phase 1, Phase 2, Phase 2.5, and Phase 3 verifiers together.

## Budget and Time Estimate

### Design Sprint

| Item | Estimate |
| --- | --- |
| Time | 0.5-1 working day |
| API spend | $0 expected |
| Infrastructure spend | $0 |
| Output | Two docs only |

### Phase 3 Minimum Implementation Sprint

| Workstream | Time estimate | API/cost estimate |
| --- | --- | --- |
| Verifier gates and fixtures | 0.5-1 day | $0 |
| Source round-trip and evidence ranking | 1 day | <$1 |
| Communicator schema, redaction, language lint | 1-1.5 days | $1-$3 |
| Alert tier router and dry-run logs | 0.5-1 day | <$1 |
| Weekly Brief PDF renderer | 1-1.5 days | $0-$2 |
| Email outreach draft queue | 1-2 days | $1-$3 |
| End-to-end QA and regression | 1 day | $1-$3 |
| **Total** | **6-9 working days** | **$4-$12 API spend** |

Recommended hard stop for Phase 3 minimum: $12 API spend until every outbound
quality gate is green. Monthly platform cost should remain inside the existing
MVP envelope unless a paid PDF, email, or workflow service is introduced.

## Quality Gates

Phase 3 should introduce a verifier with gates similar to these:

| Gate | Name | Pass condition |
| --- | --- | --- |
| CGM-01 | Source round-trip | PMID/DOI/NCT/URL claims resolve to original source or are blocked |
| CGM-02 | Analyzer PICO and evidence ranking | Alerts include population, intervention, comparator, outcome when applicable plus evidence grade |
| CGM-03 | Confidence gate | Only high-confidence, source-backed, actionable items can become urgent |
| CGM-04 | Communicator schema | Every outbound draft validates against the shared draft contract |
| CGM-05 | Redaction gate | PHI classification is present; blocked PHI cannot render or send |
| CGM-06 | Language lint | Clinical-command verbs are blocked; clinician-decision language is present |
| CGM-07 | Alert router | Fixture events route to T0-T4 deterministically |
| CGM-08 | Email approval | Outreach email cannot send unless approved and logged |
| CGM-09 | Weekly Brief PDF | PDF renders non-empty, has citation appendix, and stages email without sending |
| CGM-10 | Budget and regression | Cost rows are written; Phase 1/2/2.5 verifiers still pass |

## Failure Modes to Design For

| Failure | Required behavior |
| --- | --- |
| Source cannot be verified | Block as T0; do not draft as fact |
| Evidence is weak but interesting | Route to T4 appendix or T2 family question |
| Message contains clinical command | Block and require rewrite |
| PHI appears in outreach draft | Redact or block based on recipient policy |
| Telegram kill-switch is active | Stage only; no send |
| Gmail unavailable | Keep draft queued; no fallback mass-send |
| PDF renderer fails | Keep weekly email staged without attachment and mark failed |
| Budget cap reached | Stop model calls; use deterministic summaries only |

## Definition of Done for Phase 3 Minimum

Phase 3 minimum is done when:

1. `scripts.verify_phase3 --gate all` exists and passes.
2. Phase 1, Phase 2, and Phase 2.5 verifiers still pass.
3. Communicator can stage a family-facing draft from a validated event.
4. Alert tier fixtures prove T0-T4 routing, dedupe, quiet hours, and kill-switch
   behavior.
5. One outreach email can be drafted, approved in dry run, and logged without
   sending.
6. One Weekly Brief PDF can be rendered from fixture data with citation appendix.
7. Every generated communication has source IDs, redaction status, approval
   status, and budget/audit trace.
8. The final exit report states clearly that this is an information system and
   not a clinician.
