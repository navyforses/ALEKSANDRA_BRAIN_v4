# Phase 5 Exit Report — BRAIN AI Manager Assistant (engineering sprint)

**Date closed:** 2026-05-18
**Scope:** BRAIN Manager — MNG-01..12 + REGR. Multi-modal intake (PDF, OCR, voice, email, text) + entity routing + preview cards + transactional batch apply + immutable activity log with 24h undo + Sunday morning briefing + "write to X about Y" Gmail drafting.
**Sprint duration:** Day 0 cleanup + Days 1–7 (2026-05-17 → 2026-05-18 — completed in 2 calendar days with all 13 gates GREEN).

## Verdict

Phase 5 closes the engineering sprint at **`verify_phase5 --mode code-complete`** → **13/13 PASS · ALL GREEN**.

| # | Gate | Day | Status |
|---|---|---|---|
| 1 | MNG-01 BRAIN panel on every route | 0 | PASS |
| 2 | MNG-02 PDF → 4+ entities | 2 | PASS |
| 3 | MNG-03 Medication photo OCR | 2 | PASS |
| 4 | MNG-04 Voice 5 s → transcript | 3 | PASS |
| 5 | MNG-05 Email parser sender/date/items | 2 | PASS |
| 6 | MNG-06 Preview cards before/after diff | 4 | PASS |
| 7 | MNG-07 One-click Apply-all → correct tables | 4 | PASS |
| 8 | MNG-08 Activity feed updates live | 5 | PASS |
| 9 | MNG-09 Undo restores last-30 / 24h | 5 | PASS |
| 10 | MNG-10 Morning briefing Sun 09:00 ≤50w | 6 | PASS |
| 11 | MNG-11 Email draft → Gmail (never auto-send) | 6 | PASS |
| 12 | MNG-12 PHI redactor on every parsed input | 1 | PASS |
| 13 | REGR Phases 0–4 still green | — | PASS |

Production-mode gates remain natural-data-gated until Phase 5 sees real intake activity (a real PDF drop, a real voice memo, a real Sunday briefing, a real Gmail draft). Same dual-mode pattern Phase 4 established.

Prior-phase regression at Phase 5 close:

| Phase | Score | Mode |
|---|---|---|
| Phase 1 Perception | 10/10 PASS | — |
| Phase 2 Memory | 19/19 PASS | — |
| Phase 2.5 Quick wins | 16/16 PASS | — |
| Phase 3 Cognition | 11/11 PASS | — |
| Phase 4 First Family Value | 9/9 PASS | code-complete |
| **Phase 5 BRAIN Manager** | **13/13 PASS** | code-complete |

Cumulative project verifier coverage at Phase 5 close: **78/78 PASS**.

## Sprint LLM spend

| Day | Spend | Notes |
|---|---|---|
| 0 cleanup | $0 | File moves only |
| 1 foundation | $0 | DDL + skeleton |
| 2 intake parsers | $0 | LLM-cost tests gated on `PHASE5_LLM_TESTS=1` |
| 3 voice | $0 | Whisper tests gated on `PHASE5_LLM_TESTS=1` |
| 4 routing | $0 | Fuzzy match (stdlib `SequenceMatcher`), no LLM |
| 5 undo + audit | $0 | DB-only |
| 6 briefing + email | $0 | Composer deterministic; live tests dry-run |
| **Phase 5 total** | **$0 / $15 cap** | 0 % budget consumed |
| **Project cumulative** | **$4.22 / $60 cap** | ~7 % budget consumed across all phases |

## What shipped (by day)

### Day 0 — Cleanup pass (`1a5f531`)
- Moved Gemini scaffold (`BrainPanel`, `TopNav`, `layout`, `page`, `globals.css`) from repo root into `viewer/components/layout/` + `viewer/app/`.
- Ported Tailwind 3 medical palette → Tailwind 4 `@theme` directive in `viewer/app/globals.css` (red/green/orange/purple/blue/yellow).
- Created 3 placeholder routes: `/today`, `/brain`, `/knowledge`.
- Installed `lucide-react` + `react-dropzone`; deleted root-level Gemini files (BrainPanel/TopNav/layout/page/globals/tailwind.config/server.py).
- `MCP-INVENTORY.csv` +2 rows (`openai-whisper-mcp`, `manager-intake-mcp`).
- Build smoke: 10 routes compile cleanly under Next.js 16.2.6 Turbopack.

### Day 1 — Foundation (`f2a0efe`)
- **Migration 011 applied** — `intake_drops` + `manager_actions` tables. CHECK `phi_redacted=TRUE`, CHECK action_type/source_input enums, FK `manager_actions.intake_drop_id → intake_drops.id ON DELETE RESTRICT`. RLS pattern matches migration 008 (`*_service_all` + `*_family_read`).
- 6 indexes: 3 per table, including the partial undo-window index `idx_manager_actions_undoable WHERE reversed_at IS NULL`.
- `scripts/manager/` skeleton — `intake/`, `routing/`, `activity/` subpackages with contract-only docstrings.
- `scripts/verify_phase5.py` — 12 MNG-* gates + REGR. Dual-mode (production / code-complete) mirroring `verify_phase4`.
- `docs/PHASE_5_DAY1_MIGRATION_DIFF.md` — Georgian-first diff review document.
- Tests: `tests/test_migration_011_manager.py` 8/8 PASS.

### Day 2 — Intake parsers (`d4d61fb`)
- `scripts/manager/intake/_shared.py` — 5 entity dataclasses (Medication/Calendar/Contact/Timeline/PHIBlock), `redact_or_block()` adapter, `persist_intake_drop()` writer. `BlockedByRedactor` raises on `.nii/.dcm` filename mentions.
- `pdf_parser.py` — `pdfplumber` born-digital path; Claude Sonnet 4.5 vision fallback when text yield < 100 chars. Spend tracked via `_record_call`.
- `image_ocr.py` — pytesseract path; Claude vision fallback. `TESSERACT_PATH` env honored.
- `email_parser.py` — stdlib `email.policy.default`. Hard-blocks `.nii/.dcm` attachments BEFORE redaction.
- `text_extractor.py` — Claude Sonnet 4.5 with strict JSON-output prompt. Redacts BEFORE the LLM call (PHI never reaches Anthropic).
- Tests: `tests/test_intake_{pdf,ocr,email,text}.py` 14 PASS + 4 SKIP (LLM-cost / Tesseract-gated).

### Day 3 — Voice (`5fda5af`)
- `voice_transcribe.py` — OpenAI Whisper API client (`whisper-1`, `verbose_json`). Spend tracked as `runs.kind='whisper_call'` with `token_cost = duration_sec / 60 * 0.006`. `check_daily_budget(raise_on_over=True)` BEFORE network call. `redact_or_block` AFTER Whisper returns. Audio bytes never persist.
- Viewer: `VoiceRecorder.tsx` (push-to-talk MediaRecorder), `InputBar.tsx`, `voice.ts` typed client.
- `viewer/app/api/manager/voice/route.ts` — server-side route handler, runtime `nodejs`, FND-02 `/* allow-remote */` marker.
- `perception_worker.py` — `/voice-transcribe` endpoint with stdlib multipart parser (no python-multipart dep). 25 MB cap matches Whisper limit.
- Tests: `tests/test_intake_voice.py` 6 PASS + 1 SKIP.

### Day 4 — Routing + preview cards (`c884118`)
- `routing/_shared.py` — `ProposedAction` dataclass, `ALLOWED_TARGET_TABLES` allow-list, `fuzzy_best_match` (stdlib `SequenceMatcher`), `decide_auto_execute` with 4 hard rules: low-conf blocks / medication-dose+drug-name NEVER auto / contacts+hypotheses preview / calendar+timeline auto at conf ≥ 0.9.
- `entity_router.py` — Medication → therapies (match or create), Calendar → `aleksandra_timeline`, Contact → contacts, Timeline → timeline. Single Postgres connection per call.
- `preview_builder.py` — `build_cards` / `card_to_action` round-trip.
- `apply_action.py` + `apply_batch.py` — per-table writers with `manager_actions` audit row append. Batch all-or-nothing.
- Viewer: `ActionPreview/{FieldDiff,ActionCard,PreviewCardList,BatchApplyButton}.tsx` + `lib/brain/apply.ts` + `app/api/manager/apply/route.ts`.
- `perception_worker.py` — `/apply-actions` endpoint.
- Tests: 20/20 PASS (9 live-DB transactional rollback).

### Day 5 — Activity feed + undo + audit page (`cc78269`)
- `activity/log_action.py` — `log_dismiss`, `log_pattern`.
- `activity/undo.py` — `undo(manager_action_id, manager_user_id)` atomically restores or deletes target row, sets `reversed_at + reversed_by`, appends a `reverse` audit row. `UndoNotAllowed` outside 24 h / already reversed / wrong operator. `UNDO_WINDOW_HOURS=24`, `UNDO_LIST_LIMIT=30`.
- `activity/audit_query.py` — `page()` + `list_recent()` with `manager_user_id` scoping.
- Viewer: `lib/realtime.ts` polling hook (graceful-degrade fallback per Phase 5 plan risk register), `BrainPanel/ActivityFeed.tsx` (wired into the always-mounted BrainPanel), `AuditLog/{ActionRow,UndoButton}.tsx`, `lib/brain/undo.ts`, `app/audit-log/page.tsx`, `/api/manager/audit/route.ts`, `/api/manager/undo/[id]/route.ts`.
- `perception_worker.py` — `/undo-action` endpoint with 409 on `UndoNotAllowed`, 422 on `UndoError`.
- Tests: `tests/test_activity_undo.py` 8/8 PASS.

### Day 6 — Morning briefing + email drafting (`8314a65`)
- `briefing.py` — deterministic 3-bullet ≤ 50-word composer pulling `aleksandra_timeline` + `evidence_ledger` + `therapies` + `outreach_log`. Dispatch via existing `telegram_sender._send_telegram`. Appends `briefs` row + `manager_briefing` runs row.
- `workflows/manager_briefing.json` — n8n cron Sun 13:00 UTC. Pure-n8n fallback writes runs row even when Python worker is offline.
- `email_draft.py` — `parse_intent` regex covers `write/draft/email/message to X about Y` + `to X: Y` + Dr./short-name normalization. Fuzzy contact match (≥ 0.6) against `contacts.full_name + short_name + email`, then delegates to `outreach_drafter.draft_outreach`. Gmail compose-only; `MAX_DAILY_DRAFTS=5`.
- Viewer: `BrainPanel/EmailIntent.tsx` (replaces the inert input), `app/api/manager/email/route.ts`.
- `perception_worker.py` — `/morning-briefing` + `/email-intent` endpoints.
- Tests: 14/14 PASS (incl. live-DB fuzzy match against the 96 real Phase 3 contacts).

### Day 7 — Sprint close (this commit)
- Six prior-phase verifiers all re-confirmed GREEN (78/78 total).
- `docs/PHASE_5_EXIT_REPORT.md` (this file).
- `docs/PHASE_5_COMPLETION_KA.md` — Georgian plain-language status for Shako.
- `docs/PHASE_5_OPERATOR_RUNBOOK.md` — Tesseract install + Railway worker deploy + env-var setup (post-sprint operator activation).
- `.planning/ROADMAP.md` — Phase 5 marked closed.
- `CLAUDE.md` — "მიმდინარე ეტაპი" updated.

## Trust boundaries enforced

1. **PHI redactor on every intake** — `pdf_parser`, `image_ocr`, `voice_transcribe`, `email_parser`, `text_extractor` all call `redact_or_block` BEFORE persistence. DB CHECK `intake_drops_must_redact` is the second line of defense.
2. **Audio bytes never persist** — Whisper response → redactor → `intake_drops`. The audio blob is discarded the moment `transcribe()` returns.
3. **.nii/.dcm hard-block** — Either as a filename mention in any parsed text or as an email attachment, intake refuses with `BlockedByRedactor`.
4. **Medication dose / drug name = NEVER auto-execute** — `decide_auto_execute` denies regardless of confidence.
5. **Allow-list for apply** — `ALLOWED_TARGET_TABLES = {aleksandra_timeline, therapies, contacts, hypotheses, kv_state}`. `runs`, `alerts_log`, `briefs`, `manager_actions`, `intake_drops` themselves are forbidden as apply targets.
6. **Gmail compose-only** — Phase 3 OAuth scope inherited. Drafts only; never auto-send.
7. **Daily email cap 5** — `MAX_DAILY_DRAFTS` inherited from `outreach_drafter`.
8. **Undo bounded** — 24 h window, last 30 actions, single-shot (`reversed_at` once set is permanent), `manager_user_id` scoped (can't undo another operator's row).
9. **Immutable audit trail** — Reversed rows stay queryable forever. `manager_actions` is append-only-style (no DELETE path in any of the writers).
10. **FND-02 clean** — Every server-side `fetch` in the viewer is explicitly marked `/* allow-remote */`; every client-side `fetch` targets a `/api/...` self-relative URL.
11. **Budget gate on every LLM path** — `check_daily_budget(raise_on_over=True)` fires before Claude vision (PDF/OCR fallback), text extractor, AND Whisper (`whisper_call` runs row counts into the same daily cap).

## Backend gaps identified during the sprint (input for the next plan)

These are documented in detail in `C:\Users\jinch\.claude\plans\5-warm-crown.md` §"Backend gaps surfaced by this plan":

1. **Google Calendar API integration** (`briefing.py` reads `aleksandra_timeline` as a placeholder for today's appointments).
2. **Python worker on Railway deployment** — `voice_transcribe`, `apply-actions`, `undo-action`, `morning-briefing`, `email-intent` all need a running Python worker. `PHASE5_MANAGER_WORKER_URL` env on Railway is the toggle. Until deployed, the Next.js routes return HTTP 503 with `manager_worker_not_deployed`.
3. **Supabase realtime client** — `lib/realtime.ts` ships polling (4 s interval); a true `@supabase/supabase-js` Postgres Changes integration is the obvious follow-up.
4. **Pattern recognition / Hindsight memory** — `log_pattern` writes an audit row but no automated longitudinal alerts fire yet.
5. **`aleksandra_timeline.event_type` ENUM** — currently free-text; the entity router relies on `'appointment' / 'observation' / 'medication_change'` strings.
6. **TVB simulation backend** — VIS-* phase scope.
7. **Mobile responsive bottom drawer** — Phase 5.5 candidate.
8. **Supabase Auth wiring** — Phase 5 ships `MANAGER_USER_ID` env var; if the family grows the user model, real auth becomes necessary.
9. **Whisper transport audit** — vendor-lock revisit when usage scales.
10. **PHI redactor expansion for voice-ambient PHI** — Day 2 plan called for a labeled fixture suite.

## How to demo

```bash
# Engineering exit:
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase1                          # 10/10
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2                          # 19/19
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2_5                        # 16/16
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase3                          # 11/11
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase4 --mode code-complete     # 9/9
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase5 --mode code-complete     # 13/13

# Day-1..6 test suites:
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_migration_011_manager.py    # 8/8
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_intake_pdf.py tests/test_intake_ocr.py tests/test_intake_email.py tests/test_intake_text.py  # 14/4
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_intake_voice.py             # 6/1
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_routing_entity_router.py tests/test_routing_apply.py  # 20/0
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_activity_undo.py            # 8/0
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_manager_briefing.py tests/test_manager_email_intent.py  # 14/0
```

Operator activation steps are documented in [docs/PHASE_5_OPERATOR_RUNBOOK.md](PHASE_5_OPERATOR_RUNBOOK.md).
