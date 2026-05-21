---
phase: 06-bilingual-system-i18n
plan: 12
subsystem: communicator-audience-routing
tags: [i18n, audience-routing, telegram, gmail, jsonb, python-worker]
requires:
  - 06-04 (viewer/lib/i18n.ts displayField — TypeScript source of truth)
  - 06-06 (migration 012 SQL authoring)
  - 06-07 (migration 012 production apply — Shako 2026-05-20)
  - 06-09 (compose_bilingual write path + briefs.sections bilingual emission)
  - 06-10 (PHI bilingual redactor)
  - 06-11 (Georgian imperative-verb lint)
provides:
  - python-display-field-py-helper
  - telegram-audience-ka-routing
  - gmail-audience-en-routing
  - manager-briefing-ka-reads
  - n8n-zero-touch-audit-trail
affects:
  - scripts/communicator/_bilingual_read.py (new)
  - scripts/communicator/telegram_sender.py (read .ka + CLI)
  - scripts/communicator/gmail_digest.py (read .en + CLI)
  - scripts/manager/briefing.py (read .ka)
  - tests/test_display_field_py.py (new)
  - workflows/_phase6_notes.md (new)
tech-stack:
  added: []
  patterns:
    - "display_field_py symmetric with viewer/lib/i18n.ts displayField (RESEARCH.md Pitfall 6)"
    - "Per-audience locale constant (TELEGRAM_LOCALE, GMAIL_LOCALE, BRIEFING_LOCALE) declared module-top so callers cannot drift"
    - "JSONB-shape fixture rows drive --bilingual-dryrun CLIs that the verifier scrapes"
    - "n8n workflow JSONs untouched; audience routing lives in Python worker layer"
key-files:
  created:
    - scripts/communicator/_bilingual_read.py
    - tests/test_display_field_py.py
    - workflows/_phase6_notes.md
  modified:
    - scripts/communicator/telegram_sender.py
    - scripts/communicator/gmail_digest.py
    - scripts/manager/briefing.py
decisions:
  - "Module name uses leading underscore (_bilingual_read.py) to flag worker-internal scope"
  - "Per-file locale constants (TELEGRAM_LOCALE, GMAIL_LOCALE, BRIEFING_LOCALE) over inline string literals — single point of audit"
  - "--bilingual-dryrun CLI flags use JSONB-shaped fixture rows (not live DB reads) so the verifier remains hermetic"
  - "n8n zero-touch confirmed by RESEARCH.md Pattern 7 5-workflow survey; documented in workflows/_phase6_notes.md for audit trail"
metrics:
  duration: ~15 minutes
  completed: 2026-05-21
requirements: [I18N-07]
---

# Phase 6 Plan 12: Communicator Audience Routing Summary

Audience-routing half of Phase 6 — Telegram-sending worker code reads `.ka`
from JSONB columns; Gmail-sending worker code reads `.en`. Small Python helper
`display_field_py` mirrors `viewer/lib/i18n.ts::displayField` so worker-side
reads share semantics with client-side reads.

## One-Liner

Locked I18N-07: family-Telegram (Sunday briefing + daily digest) reads `.ka`
from every JSONB column via `display_field_py`; clinician-Gmail (weekly digest)
reads `.en`. n8n workflow JSONs unchanged.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | display_field_py helper + 7-test pytest suite | 065df5b | scripts/communicator/_bilingual_read.py, tests/test_display_field_py.py |
| 2 | telegram_sender reads .ka + --bilingual-dryrun CLI | 990a999 | scripts/communicator/telegram_sender.py |
| 3 | gmail_digest reads .en + --bilingual-dryrun CLI | ef4068c | scripts/communicator/gmail_digest.py |
| 4 | manager briefing reads .ka via display_field_py | c1d77c8 | scripts/manager/briefing.py |
| 5 | workflows/_phase6_notes.md zero-touch decision | 0b944fd | workflows/_phase6_notes.md |

## Verification Results

### display_field_py pytest

```
$ .venv/Scripts/python.exe -X utf8 -m pytest tests/test_display_field_py.py -v
collected 7 items
tests/test_display_field_py.py::test_display_field_py_none_returns_empty_string PASSED
tests/test_display_field_py.py::test_display_field_py_legacy_text_en_passthrough PASSED
tests/test_display_field_py.py::test_display_field_py_legacy_text_ka_passthrough_no_translation PASSED
tests/test_display_field_py.py::test_display_field_py_bilingual_dict_en PASSED
tests/test_display_field_py.py::test_display_field_py_bilingual_dict_ka PASSED
tests/test_display_field_py.py::test_display_field_py_en_only_dict_falls_back_to_en_for_ka PASSED
tests/test_display_field_py.py::test_display_field_py_empty_dict_returns_empty_string PASSED
============================== 7 passed in 0.05s ==============================
```

### Phase 6 verifier (code-complete mode)

```
$ .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase6 --mode code-complete
  1  I18N-01     PASS    next-intl@4 installed + proxy.ts mounted
  2  I18N-02     PASS    7 family-facing routes mounted under app/[locale]/*
  3  I18N-03     PASS    viewer/messages/{en,ka}.json key-aligned (143 leaves each)
  4  I18N-04     PASS    LanguageSwitcher mounted in [locale]/layout.tsx
  5  I18N-05     PASS    Migration 012 prepared
  6  I18N-06     PASS    Communicator emits {en, ka} via compose_bilingual
  7  I18N-07     PASS    Telegram audience reads .ka; Gmail audience reads .en
                         → telegram_reads_ka=True gmail_reads_en=True
  8  I18N-08     PASS    viewer/lib/i18n.ts exports displayField with en-fallback
  9  I18N-09     PASS    Migration 012 mirrors en→ka via jsonb_build_object
 10  I18N-10     PASS    PHI redactor + imperative-verb lint scaffolded
 11  I18N-11     FAIL    Phases 4+5 verifiers still GREEN (Wave-4 06-13 owns this)
  10/11 PASS — NEEDS WORK
```

**I18N-07 flipped from PENDING/RED to GREEN.** Previous baseline was 9/11; now 10/11. I18N-11 is Wave-4 (Plan 06-13) regression-sweep work, intentionally PENDING per the verifier evidence text and the plan's frontmatter `wave: 4`.

### Call-site update counts

| File | display_field_py occurrences | Locale used | Notes |
|------|------------------------------|-------------|-------|
| `scripts/communicator/telegram_sender.py` | 7 | `'ka'` only | TELEGRAM_LOCALE constant; --bilingual-dryrun CLI |
| `scripts/communicator/gmail_digest.py` | 12 | `'en'` only | GMAIL_LOCALE constant; 6 render_body call sites + --bilingual-dryrun CLI |
| `scripts/manager/briefing.py` | 5 | `'ka'` only | BRIEFING_LOCALE constant; _todays_events + _top_therapy_this_week |

Negative-grep confirmed: no `display_field_py.*'en'` token in telegram_sender.py
(Telegram is `.ka` exclusively); no `display_field_py.*'ka'` token in
gmail_digest.py (Gmail is `.en` exclusively). Threats T-06-LOCALE-LEAK-TG and
T-06-LOCALE-LEAK-GM mitigated as planned.

### Dry-run output excerpts

**Telegram (.ka) — Mkhedruli present:**

```
$ .venv/Scripts/python.exe -X utf8 -m scripts.communicator.telegram_sender --bilingual-dryrun
📨 ALEKSANDRA_BRAIN — bilingual dry-run (Telegram, ka)
• ახალი სტატია ვიგაბატრინის გამორეცხვაზე
  სამი ახალი წყარო შემოვიდა ჩანაწერებში.
• Sunday morning briefing reminder
  Cord blood follow-up due
```

Codepoints U+10D0–U+10FF visible in the first two bullets. The third row is a
legacy-TEXT row exercising `display_field_py`'s passthrough; the fourth row is
an en-only dict exercising English fallback. The mixed shapes are intentional
— they prove the helper handles every shape the worker layer can receive.

**Gmail (.en) — zero Mkhedruli:**

```
$ .venv/Scripts/python.exe -X utf8 -m scripts.communicator.gmail_digest --bilingual-dryrun
ALEKSANDRA_BRAIN — Weekly Brief
Week of 2026-05-21 – 2026-05-27
Generated 2026-05-21T20:01:34+00:00

This week, in short:
  • 3 new relevant papers this week.
  • 2 hypothesis updates.

New evidence:
  • Vigabatrin washout in infant HIE [PMID:00000000, relevance=0.91]

Hypothesis updates:
  • Cord blood window aligns with Duke EAP — status=evaluating, confidence=medium

Repurposing watch:
  • Vigabatrin — evaluating / HIE evidence moderate

Outreach queue:
  • [Duke DTRI] Cord blood EAP follow-up (pending review)

Open family questions:
  • When does vigabatrin washout complete?
```

Programmatic check: `any(0x10A0 <= ord(c) <= 0x10FF for c in body) → False`.

### n8n zero-touch confirmation

```
$ git status --short workflows/
?? workflows/_phase6_notes.md
```

Only the new audit-trail document appears. Zero JSON workflow files modified
by Plan 06-12. RESEARCH.md Pattern 7 zero-touch finding confirmed.

### Phase 4 + Phase 5 regression checks

```
$ .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase4 --mode code-complete
  FFV-01 PASS  Telegram dispatcher (uses telegram_sender)
  FFV-03 PASS  Weekly Gmail digest (uses gmail_digest)
  7/9 PASS (OBS-03 + REGR are pre-existing baseline state)

$ .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase5 --mode code-complete
  MNG-10 PASS  Morning briefing delivers Sunday 09:00 ≤50 words
  10/13 PASS (MNG-01, MNG-09, REGR are pre-existing baseline state)
```

Critical regression gates (FFV-01, FFV-03, MNG-10) all PASS — the three files
touched by Plan 06-12 keep their Phase-4 and Phase-5 invariants.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Anticipatory test discovery]** Per the executor prompt the helper
and test file were already present as untracked files (`scripts/communicator/_bilingual_read.py`
and `tests/test_display_field_py.py`) — verified content matches the plan's
interface block verbatim (`display_field_py(field, locale: str) -> str` with
the 4-shape switchboard). Action taken: re-ran the 7-test pytest suite (7/7
PASS), then committed both files as Task 1. No re-authoring needed.

**2. [Rule 2 — Forward-compat read on briefing.py.title]** The plan's
acceptance check required `display_field_py(` calls with `'ka'` argument at
least once. The natural call sites are inside `_todays_events` (timeline.title)
and `_top_therapy_this_week` (therapies.name). Both columns are JSONB
post-migration-012; today they may still be TEXT in some envs. Helper's
plain-string passthrough handles the forward-compat case without a code branch.

**3. [Rule 1 — gmail_digest.render_body's summary_lines loop]** Pre-06-09 the
loop wrote `f"  • {line}"` over `list[str]`. Post-06-09 `summary_lines` is
`list[dict[str, str]]`, which would format as `f"  • {'en': '...', 'ka': '...'}"`
(broken inbox output). Fix: route through `display_field_py(line, GMAIL_LOCALE)`
inside the loop. Caught during Task 3 implementation; no separate commit.

### Self-Approved Decisions (Auto Mode)

None. Plan 06-12 is fully autonomous (`autonomous: true`); no checkpoints
emitted. Auto-mode override not required.

## Known Stubs

None. All call sites consume real BriefSections / DB query outputs through
`display_field_py`. The CLI `--bilingual-dryrun` paths use deliberate fixture
rows that exercise the four shapes (dict-bilingual / dict-en-only / legacy-TEXT
/ None — implicit via empty fixture entries). The fixtures are intentional
and clearly named; they are not stubs hiding missing functionality.

## Self-Check: PASSED

- [x] `scripts/communicator/_bilingual_read.py` exists with `display_field_py`
- [x] `tests/test_display_field_py.py` 7/7 PASS
- [x] `scripts/communicator/telegram_sender.py` imports + uses `display_field_py` (7 occurrences, all `'ka'`)
- [x] `scripts/communicator/gmail_digest.py` imports + uses `display_field_py` (12 occurrences, all `'en'`)
- [x] `scripts/manager/briefing.py` imports + uses `display_field_py(..., 'ka')` (5 occurrences)
- [x] `workflows/_phase6_notes.md` exists (65 lines, contains audit table + backlog item + Pattern 7 reference)
- [x] `git status --short workflows/` shows ONLY the new `.md` file (zero JSON edits)
- [x] `verify_phase6 --bucket D` → I18N-07 PASS (1/1)
- [x] `verify_phase6 --mode code-complete` → 10/11 PASS (was 9/11; I18N-07 GREEN)
- [x] Phase 4 FFV-01 + FFV-03 PASS
- [x] Phase 5 MNG-10 PASS
- [x] All 5 task commits present in `git log`
  - 065df5b: feat(06-12): add display_field_py helper + 7-test pytest suite
  - 990a999: feat(06-12): telegram_sender reads .ka via display_field_py + --bilingual-dryrun CLI
  - ef4068c: feat(06-12): gmail_digest reads .en via display_field_py + --bilingual-dryrun CLI
  - c1d77c8: feat(06-12): manager briefing reads .ka via display_field_py for Telegram audience
  - 0b944fd: docs(06-12): document n8n zero-touch decision for Phase 6 audience routing
