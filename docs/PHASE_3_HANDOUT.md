# Phase 3 Handout

**Date:** 2026-05-16
**Mode:** Design only. No code changes in this sprint.

## What Is Ready

The lower layers are ready enough to design Phase 3:

- Phase 1 verifier is closed.
- Phase 2 verifier is 19/19 PASS.
- Phase 2.5 verifier is 16/16 PASS.
- Phase 2.5B/C/D are complete: perception scale-up, family-visible layer, and
  validation workflow are available.
- The dashboard, urgent alert template, daily digest run, confirmed hypotheses,
  and supporting-paper hydration give Phase 3 a safe base to design from.

## What Phase 3 Adds

Phase 3 is the first family-facing cognition layer. It should make the system
useful without making it clinically overconfident.

| Capability | Plain-language meaning | First safe version |
| --- | --- | --- |
| Communicator activation | The system can prepare messages for the family | Drafts only, with approval |
| Alert tier refinement | Alerts are sorted by urgency and calm | T0-T4 deterministic router |
| Email outreach automation | Researcher/clinician emails can be drafted | Human-approved drafts only |
| Weekly Brief PDF | A weekly packet summarizes what changed | PDF staged before email |

## Entry Criteria

Before implementation begins, the team should confirm:

- `verify_phase1`, `verify_phase2 --gate all`, and
  `verify_phase2_5 --gate all` still pass.
- `retrieve(query, t_at=...)` remains the only retrieval surface for agents.
- Source traceability is intact from claim to ledger/source.
- The Telegram/n8n stop control still works.
- Contact data source and family redaction preference are chosen.
- Human approval rules are written down before any outbound transport is wired.

## Non-Goals

- No live sends from new Phase 3 flows during design.
- No medical advice, treatment instruction, prescription, or diagnosis.
- No bulk email campaign.
- No PHI in outreach or PDFs unless explicitly approved.
- No direct agent access to Graphiti or Qdrant outside `retrieve()`.
- No Phase 2 verifier changes to make Phase 3 easier.

## The Safety Pattern

Every outbound item follows the same path:

`source event -> source check -> evidence rank -> alert tier -> draft -> redaction -> language lint -> human approval -> send or skip -> audit log`

If any step fails, the item is blocked or staged for review. It does not send.

## Alert Tiers

| Tier | Meaning | Default behavior |
| --- | --- | --- |
| T0 Blocked | Unsafe, unsourced, duplicate, or PHI-blocked | Do not send |
| T1 Urgent | High-confidence, time-sensitive, family-relevant | Immediate Telegram stage |
| T2 Action Needed | Family decision or follow-up needed soon | Same-day queue |
| T3 Important | Relevant but not urgent | Daily digest/dashboard |
| T4 Weekly | Useful context and low-pressure updates | Weekly Brief PDF |

Only high-confidence, source-backed, time-sensitive items can become T1. Medium
evidence should ask for review or wait for a digest. Low evidence belongs in the
weekly appendix or internal queue.

## Communicator Rules

The Communicator can write:

- "Review this paper."
- "Discuss this with the clinician."
- "Ask whether this trial is relevant."
- "Save this for the weekly brief."

The Communicator must not write:

- "Start this treatment."
- "Stop that medication."
- "Increase or decrease a dose."
- "This proves Aleksandra should receive X."

The voice is helpful, sourced, and calm. A real clinician signs every decision.

## Email Outreach Rules

Phase 3 email automation should draft and queue messages, not mass-send them.

The first safe version needs:

- A known contact and reason for writing.
- A source-backed evidence packet.
- A plain-text draft.
- PHI classification and redaction result.
- Human approval before send.
- Follow-up date and thread logging.

Recommended starting limit: no more than 5 approved outbound emails per day.

## Weekly Brief PDF

The weekly brief should answer five questions:

1. What changed this week?
2. What needs family attention?
3. What evidence looks strongest?
4. What outreach is waiting or due?
5. What sources support each claim?

Default sections:

- One-page summary.
- New papers and trials.
- Hypotheses and repurposing watch.
- Outreach queue.
- Family questions.
- Citation appendix.

Empty sections should say "No new items this week" instead of disappearing.

## Dependency Map

| Dependency | Why it matters | Status |
| --- | --- | --- |
| Evidence ledger and citation tuple | Grounds every claim | Ready |
| `retrieve()` facade | Prevents agent memory bypass | Ready |
| Confirmed hypotheses | Feeds alerts and weekly brief | Ready |
| Dashboard | Shows staged, skipped, sent items | Ready |
| Telegram/n8n | Sends urgent/action alerts | Ready enough |
| Gmail | Sends outreach and weekly brief | Needs runtime check |
| Contact store | Drives outreach automation | Needs canonical source |
| PDF renderer | Builds weekly artifact | Needs implementation choice |
| Approval store | Prevents accidental sends | Needs implementation design |
| Redaction policy | Controls PHI handling | Needs family decision |

## Time and Budget

Design sprint:

- Time: 0.5-1 working day.
- API spend: $0 expected.
- Output: these two docs only.

Phase 3 minimum implementation sprint:

- Time: 6-9 working days.
- API spend: $4-$12 estimated.
- Recommended hard stop: $12 until every outbound quality gate is green.
- Platform cost should stay inside the existing MVP envelope unless a new paid
  email, PDF, or workflow service is added.

## Quality Gates

Phase 3 should not be considered family-ready until these pass:

- Source round-trip for every PMID, DOI, NCT, URL, or ledger claim.
- Analyzer PICO and evidence ranking for alertable evidence.
- Confidence gate blocks weak evidence from urgent alerts.
- Communicator draft schema validates.
- PHI redaction status is present.
- Clinical-command language lint passes.
- Alert tier fixtures route T0-T4 deterministically.
- Outreach email cannot send without approval.
- Weekly Brief PDF renders with citation appendix.
- Budget logging works and Phase 1/2/2.5 verifiers still pass.

## Decisions Needed Before Build

- Weekly brief delivery day and time.
- Which T1 categories may bypass quiet hours.
- Contact store of record for outreach.
- Redaction level for family PDFs and external emails.
- Whether first implementation allows any auto-send, or stages everything for
  approval.

Recommended first implementation stance: stage everything. Let the system earn
trust before it earns autonomy.
