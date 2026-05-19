# Phase 5 SPEC — BRAIN AI Manager Assistant + Persistent UX Layer (DRAFT)

> **Status:** `DRAFT — pending Phase 4 close + 14-day acceptance outcome`
> **Stored:** 2026-05-17 (during Phase 4 Day-4 sprint; Phase 4 verifier at 2/9)
> **Source:** Shako-supplied kickoff (verbatim below).
> **Do NOT execute** until preconditions cleared (see §0).
> **Cross-refs:** [.planning/PHASE_5_INPUTS.md](../PHASE_5_INPUTS.md) (Gemini scaffold inventory), [docs/PHASE_4_VERIFICATION_REPORT.md](../../docs/PHASE_4_VERIFICATION_REPORT.md) (current Phase 4 status).

---

## 0. Preconditions — what must be true before this SPEC runs

The kickoff text below opens with `Phase 4 verification completed: All 6 verifiers green (Phases 0/1/2/2.5/3/4)`. **This is not yet true as of 2026-05-17.** Live audit results:

| Kickoff claim | Reality at 2026-05-17 |
|---|---|
| "All 6 verifiers green" | `verify_phase4` = **2/9 PASS** (Day 4/7 of Phase 4 sprint) |
| "5 main routes live: Today, Brain, Knowledge, Therapies, Timeline" | Live routes: `/`, `/dashboard`, `/papers`, `/therapies`, `/timeline`, `/hypotheses`. **Today / Brain / Knowledge do not yet exist.** |
| "3D Digital Twin functional with NiiVue + R3F + TVB" | None of these are wired. `BrainPanel.tsx` / `page.tsx` exist as **UI shells untracked at repo root** (Gemini scaffold — see PHASE_5_INPUTS.md) |
| "Three view modes operational: Parent / Doctor / Researcher" | UI buttons only in `page.tsx`; no backing logic |
| "Multilingual UI: KA / EN / FR / RU" | Backend language detection (en/ka/fr) works for **outbound** drafts (CGM-07); UI shipped today is **English-only** |
| "Communicator agent live" | ✅ True — Phase 3 closed 11/11 |
| "Phase 4 Capability inheritance: Daily cap 5 outreach drafts" | ✅ True — CGM-09 enforces |

**Trigger to lift DRAFT status:** all of:
1. `python -m scripts.verify_phase4 --gate all` → **9/9 PASS**
2. 14-day Phase 4 acceptance window completes (window opens Sunday 2026-05-24 with first real Weekly Brief; closes ~2026-06-07)
3. Acceptance outcome documented: ≥ 1 credible treatment lead surfaced to family that wouldn't have been found via ChatGPT + Google Scholar in the same window
4. Shako-issued explicit go-ahead: "Phase 5 plan-phase დაიწყე"

Only when all four are checked, this SPEC unfreezes and `gsd-spec-phase` / `gsd-plan-phase` may run against it.

---

## 1. Reconciliation with existing Gemini scaffold

The 5 capabilities below already have **partial code on disk** from the 2026-05-16 Gemini session. Mapping:

| Phase 5 Capability | Existing scaffold | What's already there | What's missing |
|---|---|---|---|
| Cap 1: Smart Drop Zone | `BrainPanel.tsx` (drop input shell), `mcp/aleksandra_niivue_mcp.py` (FastMCP NIfTI loader) | DropZone UI shell, FastMCP NIfTI tool | PDF parser, OCR, email parser, voice route, entity router, preview cards |
| Cap 2: Persistent Activity Log | none specific | none | manager_actions table (migration 009), ActivityFeed, Undo, /audit-log page |
| Cap 3: Morning Briefing | `scripts/communicator/weekly_brief.py` (related but different cadence) | Weekly Brief renderer (Phase 3) | Daily 09:00 briefing script (≤50 words), n8n manager_briefing workflow |
| Cap 4: Voice-First Input | none | none | Whisper integration, MediaRecorder, push-to-talk |
| Cap 5: Email Drafting | `scripts/communicator/outreach_drafter.py` (Phase 3) | Compose-only Gmail draft with cap=5 + PHI redaction + banned phrases | BRAIN panel surface for "Write to X about Y" intent |

**Implication for plan-phase:** the kickoff says "build only these five" but Capability 5 is **largely done** (Phase 3 outreach_drafter). Plan-phase should treat Cap 5 as integration, not greenfield.

**Required cleanup pass first** (see [.planning/PHASE_5_INPUTS.md](../PHASE_5_INPUTS.md) §"Required cleanup pass") — 10 items including dual-layout collision, Tailwind config reconciliation, the "limited outcomes" framing in `server.py`, MCP-INVENTORY registration. These cleanup items are **prerequisites for Day 1**, not part of Day 1.

---

## 2. Open issues to resolve before plan-phase

These are questions the SPEC silently assumes but must be answered explicitly:

1. **5 routes vs 7 routes.** Kickoff says "Routes /today, /brain, /knowledge, /therapies, /timeline already exist" and "No new pages built in Phase 5. Only the BRAIN panel and the audit-log page." But /today, /brain, /knowledge do **not** exist today. Two interpretations:
   - (a) Phase 5 charter expands silently to include building those 3 routes → conflicts with constraint #5
   - (b) Phase 5 acceptance is gated on those 3 routes existing → Phase 5 cannot start until they are built somewhere (Phase 4.5 mini-sprint? part of Day 1 cleanup pass?)

   **Decision required at plan-phase entry.** Recommend (b) with explicit Day 0 cleanup pass.

2. **Auth model for `user_id uuid REFERENCES auth.users(id)`** in migration 009. Phase 0-4 used service-role writes + family-read via `authenticated` role; there is **no Supabase Auth user table populated yet**. Either:
   - (a) Wire Supabase Auth (magic link for Shako) — new dependency, ~2 hours
   - (b) Use a single hardcoded `manager_user_id` (`Patient` node analog) — simpler, ships in 30 min
   - (c) Drop the FK and use service-role writes everywhere — simplest, weakest audit

3. **Whisper API** — cost model. Whisper is OpenAI; the stack is Anthropic-first. Options:
   - (a) OpenAI Whisper API (~$0.006/min — for 50 min/week ≈ $1.20/mo, well in budget)
   - (b) `whisper.cpp` local — zero API cost, requires installer on Shako's machine
   - (c) Claude Sonnet 4.5 multimodal audio (not available as of audit knowledge cutoff — verify)

   **MCP-INVENTORY.csv update required either way.**

4. **Realtime activity feed** uses Supabase realtime subscriptions. Free tier allows 200 concurrent realtime connections — single-user OK, but the `viewer/` currently uses **anon-role REST polling** (`getRows`/`getCount`). Add realtime client wrapper + RLS policy for realtime.

5. **`auth.uid()` in RLS policies** requires Supabase Auth wired (see #2). If we pick (b) or (c) for #2, the RLS in the kickoff's migration 009 has to be rewritten to use `current_setting('app.manager_user', true)` or similar.

6. **MNG-02 target `4+ entities in <30s`** for a PDF — Claude Sonnet 4.5 multimodal PDF input cost: ~$0.01/page for a 5-page discharge summary. Hard cap $15 for the whole sprint allows ~1500 pages worth of testing. Fine.

7. **Capability 1 includes "📸 Photo of medication bottle → OCR → match to therapies table"**. Therapies table currently has 12 candidates including Vigabatrin + cord blood. Match strategy unspecified — Levenshtein? embedding? name_aliases column already exists per Phase 2.5. Recommend embedding match against `therapies.name + name_aliases` via existing Qdrant infra.

8. **Mobile bottom drawer** (constraint #10) collides with current viewer/ layout that is `max-w-7xl` desktop-first. Mobile responsive is a substantial re-layout, not a Day 7 add-on. **Either** dedicate Day 6.5 to it, **or** descope mobile out of Phase 5.

9. **`auth.users` RLS + the existing `family_read TO authenticated` policies on 14 tables** — adding `manager_actions` with per-user RLS introduces a second auth model. Phase 0 trust boundary is one auth.

10. **PHI redactor scope expansion.** Phase 3 PHI redactor handles 5 patterns (name, DOB, MRN, hospital, MRI block). Voice transcripts may contain new PHI patterns (address, phone, doctor cell). Need pattern audit + new fixtures.

---

## 3. Verbatim kickoff text (Shako, 2026-05-17)

The text below is preserved exactly as Shako delivered it. All edits / cleanups / open issues live above this line; the body below is the source of truth for SPEC clarification.

---

# ALEKSANDRA_BRAIN — Phase 5 Kickoff
## BRAIN AI Manager Assistant + Persistent UX Layer

## CONTEXT

Phase 4 verification completed:
- All 6 verifiers green (Phases 0/1/2/2.5/3/4)
- 5 main routes live: Today, Brain, Knowledge, Therapies, Timeline
- 3D Digital Twin functional with NiiVue + R3F + TVB
- MRI processing isolated to browser/sandbox (PHI never leaves client)
- Three view modes operational: Parent / Doctor / Researcher
- Multilingual UI: KA / EN / FR / RU with intelligent recipient routing
- Communicator agent live: source-grounded summaries, PHI redacted,
  manual-send only

Phase 5 transforms the static interface into a conversational interface.
The user no longer navigates pages and fills forms — the user drops files,
speaks, or types one sentence, and BRAIN updates everything.

## DESIGN AGREEMENT (finalized 2026-05-16 design session)

The visual system was finalized:
- Mayo Clinic + Notion + Linear cleanliness, never sci-fi
- Light mode primary, generous whitespace
- Inter (EN/FR/RU/numbers) + BPG Nino (KA) typography
- Semantic color palette: red/orange/green/blue/purple/yellow/gray
- 8px grid system, soft shadows, subtle borders

The BRAIN AI Assistant panel was specified as:
- 35% width, right-side, persistent across all 5 pages
- Collapsible to 60px thin sidebar
- Three sections: status header, scrollable activity feed, multi-modal input
- Always-visible microphone and drop zone

═══════════════════════════════════════════════════
PHASE 5 SCOPE — 5 CAPABILITIES (MVP)
═══════════════════════════════════════════════════

Per finalized design recommendation: build only these five. Everything
beyond is Phase 6+.

## Capability 1: Smart Drop Zone

The killer interaction. User drops anything → BRAIN parses → preview cards
→ one-click apply.

Supported input types:
- 📄 PDF (discharge summary, lab report, MRI report) → text extraction +
  entity recognition
- 📸 Photo of medication bottle → OCR → match to therapies table
- 📸 Photo of medical document → vision API → structured field extraction
- 📧 Forwarded email (.eml file) → parse → calendar/contacts/timeline update
- 📹 Voice memo → Whisper transcription → entity extraction
- 📋 Pasted text → natural language → entity extraction

The pattern:
User drops file → 2-3 second processing →
preview card "Found N things to update" →
each finding as an inline action card with checkbox →
"Update all" button OR per-card approval

Implementation:
- Drop zone present in BRAIN panel, expands when dragging
- Files routed through `scripts/manager/intake/` parsers
- Vision uses Claude Sonnet 4.5 multimodal
- OCR fallback: Tesseract for plain text
- Output cards include: target page, target field, before/after, source link

## Capability 2: Persistent Activity Log

Every BRAIN action visible. No silent writes.

Activity feed format:
🟢 just now · "Reading BMC_Discharge_Summary.pdf — 4 updates ready"
🕐 5 min ago · "Updated Therapy → Vigabatrin dose to 400mg" [Undo]
🕐 17 min ago · "Added Timeline event: 2026-04-08 BMC discharge" [Undo]
🕐 1 hour ago · "Drafted reply to Sydney Crane (Draft saved)" [Open]

Each entry:
- Timestamp (relative + absolute on hover)
- Action description (plain language)
- Affected page (clickable link)
- Undo button (active for last 30 actions, 24h window)
- Source (which input triggered the action)

Backend: every BRAIN action writes to `manager_actions` table with full
reversal payload. Undo restores from payload.

## Capability 3: Morning Briefing

Sunday 09:00 (per Shako's locked decision) — three lines, max.

Format:
Good morning, Shako. Day 261.
📅 Today: Nutrition visit 10:30 (Helen)
🔬 Overnight: 3 new papers, 1 high relevance
⚠️ Sydney 8 days no reply — draft follow-up?

Strict rules:
- Maximum 3 bullets
- Never more than 50 words total
- Each line must lead to a concrete action OR be informational only
- Delivered to BRAIN panel chat history AND Telegram
- Time auto-adjusts to user's current timezone (Boston / Durham / Paris)

Implementation:
- `scripts/manager/briefing.py` runs Sunday 09:00 local
- Pulls from: today's calendar, last 24h evidence_ledger, contact follow-up timer
- Output capped at 50 words by hard limit

## Capability 4: Voice-First Input

The 2am scenario. Aleksandra has a seizure. Shako is exhausted. Typing
fails. Voice works.

Specification:
- Large microphone button in BRAIN panel input area
- Hold-to-record (push-to-talk style)
- Visual waveform feedback during recording
- Whisper API for transcription (≤500ms latency target)
- Entity extraction routes to appropriate table
- Confirmation toast: "Logged: small seizure 1.5 min, hand movement"
- Pattern check runs in background, surfaces if pattern detected

Mobile priority: voice button is the largest interactive element on mobile
viewport.

## Capability 5: Email Drafting (never auto-sends)

User: "Write to Sydney about Duke timing"

BRAIN:
1. Analyzes prior conversation tone from past emails
2. Pulls latest relevant updates (Vigabatrin washout status, Aleksandra
   readiness, calendar)
3. Drafts in recipient's language (per contact record)
4. Saves to Gmail drafts via API
5. Shows preview card in BRAIN panel: subject, recipient, opening line
6. User clicks "Open in Gmail" → reviews → sends manually

NEVER:
- Auto-sends
- Sends without preview shown
- Includes PHI beyond what contact record permits

Daily cap: 5 outreach drafts (inherited from Phase 3).

═══════════════════════════════════════════════════
EXPLICITLY NOT IN PHASE 5
═══════════════════════════════════════════════════

These were considered and deferred per design discussion:

❌ Pattern recognition automatic alerts (Phase 6 — needs data baseline)
❌ Wearable integration (Phase 7+ — hardware dependency)
❌ Family Council mode multi-user simultaneous (Phase 6 — sync complexity)
❌ Anonymous peer comparison (Phase 7+ or never — privacy)
❌ Cross-doctor coordination (Phase 7+ — political complexity)
❌ Insurance form automation (manual remains — regulatory risk)
❌ Researcher outreach automation (manual drafts only — relationship risk)
❌ Therapy quality scoring (Phase 6 — premature, needs months of data)
❌ Emergency mode UI switch (Phase 6 — distinct workstream)
❌ Privacy filtering per family member (Phase 6 — adds complexity)

Manager must reject any agent proposal to build these in Phase 5.

═══════════════════════════════════════════════════
ARCHITECTURE
═══════════════════════════════════════════════════

## New backend scripts (`scripts/manager/`)
scripts/manager/
├── init.py
├── intake/
│   ├── pdf_parser.py          # PDF → structured fields
│   ├── image_ocr.py           # Photo OCR
│   ├── voice_transcribe.py    # Whisper integration
│   ├── email_parser.py        # .eml → entities
│   └── text_extractor.py      # Plain text NLU
├── routing/
│   ├── entity_router.py       # Which table gets the update
│   ├── preview_builder.py     # Builds inline action cards
│   └── apply_action.py        # Executes approved actions
├── activity/
│   ├── log_action.py          # Writes to manager_actions
│   ├── undo.py                # Reverses an action
│   └── audit_query.py         # Audit log page backend
├── briefing.py                # Sunday 09:00 morning brief
└── email_draft.py             # Gmail API draft writer

## New Supabase tables (migration 009)

```sql
-- migration 009: BRAIN manager actions

CREATE TABLE manager_actions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  action_type text NOT NULL CHECK (action_type IN (
    'create','update','draft_email','add_event','add_milestone',
    'add_contact','log_pattern','dismiss'
  )),
  target_table text NOT NULL,
  target_record_id uuid,
  before_payload jsonb,
  after_payload jsonb,
  source_input text,        -- 'voice'|'pdf'|'photo'|'email'|'text'
  source_metadata jsonb,    -- filename, transcript, etc
  user_id uuid REFERENCES auth.users(id),
  approved_at timestamptz,
  reversed_at timestamptz,
  reversed_by uuid REFERENCES auth.users(id),
  created_at timestamptz DEFAULT now()
);

CREATE INDEX idx_manager_actions_user_created
  ON manager_actions(user_id, created_at DESC);

CREATE INDEX idx_manager_actions_undoable
  ON manager_actions(user_id, created_at DESC)
  WHERE reversed_at IS NULL
  AND created_at > now() - interval '24 hours';

-- RLS: user sees only own actions
ALTER TABLE manager_actions ENABLE ROW LEVEL SECURITY;
CREATE POLICY manager_actions_owner_read ON manager_actions
  FOR SELECT USING (user_id = auth.uid());
CREATE POLICY manager_actions_owner_write ON manager_actions
  FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE TABLE intake_drops (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id),
  input_type text NOT NULL,
  filename text,
  r2_artifact_path text,
  raw_content text,
  parsed_entities jsonb,
  proposed_actions jsonb,
  status text DEFAULT 'pending'
    CHECK (status IN ('pending','approved','rejected','applied')),
  created_at timestamptz DEFAULT now(),
  resolved_at timestamptz
);

ALTER TABLE intake_drops ENABLE ROW LEVEL SECURITY;
CREATE POLICY intake_drops_owner ON intake_drops
  FOR ALL USING (user_id = auth.uid());
```

## Frontend changes (`viewer/`)
viewer/
├── app/
│   ├── layout.tsx                  # Add BRAIN panel as root layout child
│   ├── audit-log/page.tsx          # New: full audit history
│   └── [existing routes]
├── components/
│   ├── BrainPanel/
│   │   ├── index.tsx               # Main panel container
│   │   ├── PanelHeader.tsx         # Status + collapse
│   │   ├── ActivityFeed.tsx        # Scrollable chat history
│   │   ├── ActionCard.tsx          # Inline preview cards
│   │   ├── DropZone.tsx            # Drag-drop file zone
│   │   ├── InputBar.tsx            # Text + voice + attach
│   │   └── VoiceRecorder.tsx       # Push-to-talk mic
│   ├── ActionPreview/
│   │   ├── PreviewCardList.tsx     # Container for proposed actions
│   │   ├── FieldDiff.tsx           # Before/after field comparison
│   │   └── BatchApplyButton.tsx
│   └── AuditLog/
│       ├── ActionRow.tsx
│       └── UndoButton.tsx
└── lib/
├── brain/
│   ├── intake.ts               # Upload drop to backend
│   ├── voice.ts                # Browser MediaRecorder + Whisper
│   ├── apply.ts                # POST approved actions
│   └── undo.ts                 # Reverse action
└── realtime.ts                  # Supabase realtime for activity feed

## n8n workflows (new)

- `manager_briefing.json` — Sunday 09:00 morning brief generation
- `intake_cleanup.json` — Daily 02:00 archive resolved intake_drops older
  than 30 days

═══════════════════════════════════════════════════
QUALITY GATES (verify_phase5.py)
═══════════════════════════════════════════════════

12 gates, all must pass:

| Gate | Description |
|------|-------------|
| MNG-01 | BRAIN panel renders on all 5 main routes |
| MNG-02 | Drop PDF → 4+ entities extracted in <30s |
| MNG-03 | Drop medication photo → drug name OCR'd correctly on 5/5 samples |
| MNG-04 | Voice 5s → transcribed in <2s with ≥90% accuracy on labeled set |
| MNG-05 | Forwarded email parser extracts: sender, date, action items |
| MNG-06 | Preview cards show before/after diff before apply |
| MNG-07 | One-click "Apply all" writes all changes to correct tables |
| MNG-08 | Activity feed updates in realtime (Supabase subscription) |
| MNG-09 | Undo restores previous state on last 30 actions |
| MNG-10 | Morning briefing delivers Sunday 09:00 with ≤50 words |
| MNG-11 | Email draft saves to Gmail drafts, NEVER auto-sends |
| MNG-12 | PHI redactor runs on every voice transcript and OCR output |

═══════════════════════════════════════════════════
EXECUTION PLAN — 7 WORKING DAYS
═══════════════════════════════════════════════════

## Day 1 (Foundation)
- Migration 009 applied (manager_actions, intake_drops, RLS)
- `scripts/manager/` skeleton + tests
- verify_phase5.py skeleton (12 gates all RED initially)
- BRAIN panel scaffold in viewer (visible but inert)

## Day 2 (Intake parsers)
- pdf_parser.py + tests on real BMC discharge summary
- image_ocr.py + tests on medication bottle photos
- email_parser.py + tests on Sydney email
- text_extractor.py + tests
- Gates MNG-02, MNG-03, MNG-05 → GREEN

## Day 3 (Voice + browser integration)
- voice_transcribe.py with Whisper API
- VoiceRecorder.tsx component (browser MediaRecorder)
- InputBar.tsx with hold-to-record
- Gate MNG-04 → GREEN

## Day 4 (Routing + preview cards)
- entity_router.py — entities to target tables
- preview_builder.py — generates inline action cards
- PreviewCardList.tsx + ActionCard.tsx + FieldDiff.tsx
- Gates MNG-06, MNG-07 → GREEN

## Day 5 (Activity log + undo)
- log_action.py writes manager_actions on every change
- ActivityFeed.tsx with Supabase realtime subscription
- undo.py implementation
- UndoButton.tsx
- AuditLog page (/audit-log)
- Gates MNG-08, MNG-09 → GREEN

## Day 6 (Briefing + email)
- briefing.py generates Sunday 09:00 message
- manager_briefing.json n8n workflow
- email_draft.py with Gmail API integration
- Gates MNG-10, MNG-11 → GREEN

## Day 7 (Integration + verification)
- BRAIN panel mounted in viewer/app/layout.tsx (visible on all routes)
- PHI redactor wired into all intake paths
- Full verify_phase5.py run
- Regression: all 6 prior verifiers must remain green
- Gate MNG-01, MNG-12 → GREEN
- Phase 5 Exit Report
- Shako Acceptance Test:
  - Real PDF drop → real entity extraction → real apply
  - Real voice memo → real transcription → real timeline event
  - Real Sunday morning briefing delivered

═══════════════════════════════════════════════════
HARD CONSTRAINTS
═══════════════════════════════════════════════════

1. **Budget cap:** $15 total LLM spend across all 7 days. Hard stop at $12.
2. **No auto-send for emails.** Drafts only. User clicks Send.
3. **No silent writes.** Every action logged to manager_actions.
4. **PHI redactor runs on every parsed input** before persistence.
5. **No new pages built** in Phase 5. Only the BRAIN panel and the audit-log
   page. Routes /today, /brain, /knowledge, /therapies, /timeline already exist.
6. **No scope creep into deferred capabilities** (see list above).
7. **All migrations human-approved** before apply on production.
8. **Voice transcripts NEVER persisted as raw audio.** Only text after
   transcription, with PHI redacted.
9. **Realtime activity feed** must use Supabase realtime subscriptions, not
   polling.
10. **Mobile responsive on Day 7** — BRAIN panel becomes bottom drawer
    swipe-up on screens <768px.

═══════════════════════════════════════════════════
MULTI-AGENT EXECUTION
═══════════════════════════════════════════════════

MANAGER (BRAIN_MANAGER) coordinates. Worker agents:

- **MIGRATION_AGENT** — Day 1 migration 009
- **INTAKE_AGENT** — Day 2 parsers (PDF, OCR, email, text)
- **VOICE_AGENT** — Day 3 Whisper + MediaRecorder
- **ROUTING_AGENT** — Day 4 entity router + preview cards
- **ACTIVITY_AGENT** — Day 5 log + undo + audit page
- **BRIEFING_AGENT** — Day 6 morning briefing + email drafts
- **INTEGRATION_AGENT** — Day 7 mount + regression
- **VERIFIER_AGENT** — continuous across all 7 days

Manager protocol (unchanged):
- Diff review after each agent commit
- Run relevant verifier
- Regression check (Phases 0-4)
- Send correction command if needed
- Block scope expansion

═══════════════════════════════════════════════════
DESIGN COMPLIANCE
═══════════════════════════════════════════════════

The frontend agent MUST follow finalized design specs:

**Panel dimensions:**
- Desktop: 35% width, right side
- Tablet: 30% width, collapsible
- Mobile: bottom drawer, swipe-up to expand full screen

**Panel structure:**
┌──────────────────┐
│ 🧠 BRAIN  🟢 active │  ← Header (sticky)
├──────────────────┤
│                  │
│  Activity feed   │  ← Middle (scrollable)
│  + chat history  │
│  + action cards  │
│                  │
├──────────────────┤
│ 📎 Drop here     │  ← Footer (sticky)
│ ────────  🎤    │
└──────────────────┘

**Typography:**
- Inter for English, French, Russian, numbers
- BPG Nino for Georgian
- 14px small / 16px body / 18px emphasis

**Colors (semantic, consistent with prior phases):**
- Activity dot status: 🟢 active / 🟡 processing / 🔴 error
- Action card borders: green left border for completed, blue for pending
- Undo button: subtle gray text, not destructive red

**Interaction patterns:**
- Drop zone highlights blue on dragenter
- Voice button pulses cyan when recording
- Preview cards slide in from top of feed
- Realtime updates animate in (fade + slight slide)
- Undo button appears next to each action for 30 most recent

**Accessibility:**
- WCAG 2.1 AA minimum
- Keyboard: Tab cycles through input → voice → drop zone → activity feed
- Voice button has visible label (not just icon)
- Color paired with text/icon (never color alone)

═══════════════════════════════════════════════════
MULTILINGUAL HANDLING
═══════════════════════════════════════════════════

BRAIN panel respects language settings established in Phase 4:

| Surface | Language source |
|---------|----------------|
| Panel UI strings | User's UI language preference (default KA) |
| User's typed input | User's choice, auto-detected for response language |
| User's voice input | Auto-detected, transcribed in detected language |
| Action card descriptions | User's UI language |
| Email drafts | Recipient's language (from contact record) |
| Morning briefing | User's UI language |
| Audit log entries | User's UI language |

Multi-language test cases:
- Voice memo in Georgian → KA transcript → KA activity log entry → KA preview cards
- Drop English PDF → English entities extracted → KA action card descriptions
- Draft email to French researcher → FR draft body → KA confirmation message

═══════════════════════════════════════════════════
TRUST ARCHITECTURE (locked from design phase)
═══════════════════════════════════════════════════

Three layers, all mandatory:

**Layer 1: Visibility**
- Every BRAIN action visible in activity feed
- No silent database writes
- Source of every change traceable

**Layer 2: Confirmation thresholds**
- Auto-execute: clear facts (label OCR, date extraction)
- Preview + 1-click confirm: field updates affecting multiple pages
- Explicit approval: emails, file deletions, third-party API calls
- Never auto: medical decisions, money spending, sharing data

**Layer 3: Audit + Undo**
- Dedicated /audit-log page
- 30-action undo window, 24h reversal possible
- Permanent immutable log (even reversed actions kept for audit)

═══════════════════════════════════════════════════
FINAL DELIVERABLES
═══════════════════════════════════════════════════

At Day 7 end, Manager produces:

1. `verify_phase5.py` → 12/12 green
2. All 6 prior verifiers → still green (regression clean)
3. `docs/PHASE_5_EXIT_REPORT.md` — technical exit report
4. `docs/PHASE_5_COMPLETION_KA.md` — Georgian non-technical for Shako:
   - One-sentence summary
   - What BRAIN can now do (plain language with concrete examples)
   - Demo scenarios (PDF drop, voice memo, morning briefing, email draft)
   - What works today (table)
   - Known limitations (deferred capabilities)
   - Cost recap
   - Decisions needed before Phase 6
   - One-paragraph closing on what this means for Aleksandra

5. Real demo evidence committed to repo:
   - Sample PDF drop → entities extracted → screenshots
   - Sample voice memo → transcription log
   - First real Sunday morning briefing delivered
   - First real email draft saved to Gmail (not sent)

═══════════════════════════════════════════════════
KICKOFF
═══════════════════════════════════════════════════

Begin Day 1: Foundation.

Before writing any code: produce `TRIAGE_PLAN_PHASE_5.md` with:
- Detailed day-by-day breakdown
- Agent assignments
- Dependency graph (Day 2 depends on Day 1, etc.)
- Quality gate checkpoints per day
- Budget tracking plan (max $15, hard stop $12)
- Design compliance checklist for frontend work

Show me `TRIAGE_PLAN_PHASE_5.md` before executing Day 1.

I review and approve → execute Day 1 through Day 7.

Final commit: `docs/PHASE_5_COMPLETION_KA.md` (Georgian, plain language,
for Shako) + demo evidence in repo.

---

## 4. What happens next (post-DRAFT)

When the 4 preconditions in §0 are met, the routing is:

1. Shako issues "Phase 5 plan-phase დაიწყე".
2. Operator (me) re-reads this SPEC + [.planning/PHASE_5_INPUTS.md](../PHASE_5_INPUTS.md).
3. Operator resolves the 10 open issues in §2 with explicit decisions, captured back into this file as `## 2.1 Resolutions`.
4. Operator runs `gsd-spec-phase` (if Shako wants the ambiguity-scored SPEC.md) or `gsd-plan-phase` directly (if §2 resolutions are fully unambiguous).
5. `TRIAGE_PLAN_PHASE_5.md` is produced as part of plan-phase output, **not** before — the kickoff's "show me TRIAGE first" line is honoured at that point.
6. Shako approves the plan; execution begins Day 1.

Until then this file is frozen as `Status: DRAFT`.
