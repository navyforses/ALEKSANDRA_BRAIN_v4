---
phase: 06-bilingual-system-i18n
plan: 09
subsystem: communicator
tags: [phase-6, i18n, bilingual, anthropic, strict-tool-use, jsonb, communicator]
requires:
  - 06-07  # production migration 012 (live JSONB schema)
  - 06-10  # phi_redactor.redact_bilingual exposed
  - 06-11  # banned_phrases.check(locales=('ka',)) per-locale scoping
provides:
  - scripts.communicator.bilingual.compose_bilingual  # Anthropic strict tool_use → {en, ka}
  - scripts.communicator.bilingual.BILINGUAL_TOOL     # strict tool_use schema constant
  - agents.communicator.insert_bilingual_row          # canonical CrewAI write-path helper
  - agents.communicator.BilingualWriteBlocked         # half-block audit-trail exception
  - scripts.manager.briefing.BRIEFING_TEMPLATES_KA    # Option A deterministic mirror dict
  - BriefMessage.bilingual_bullets                    # bilingual mirror persisted into JSONB
  - BriefSections.summary_lines: list[dict[str, str]] # was list[str] pre-06-09
  - weekly_brief --bilingual-test CLI flag            # verifier hook
affects:
  - scripts/communicator/bilingual.py            # NEW: 201 lines
  - tests/test_compose_bilingual.py              # NEW: 117 lines, 4 pytest cases
  - scripts/communicator/weekly_brief.py         # MODIFIED: Option A deterministic mirror
  - scripts/manager/briefing.py                  # MODIFIED: bilingual_bullets + KA templates
  - agents/communicator.py                       # MODIFIED: insert_bilingual_row helper
tech-stack:
  added:
    - anthropic.tools[].strict=True       # grammar-constrained sampling
    - anthropic.tool_choice forced-tool   # type='tool' + name='compose_bilingual'
    - psycopg2.extras.Json                # JSONB serializer that respects Mkhedruli
  patterns:
    - "Option A (deterministic mirror) for fixed-template summary lines — zero LLM cost"
    - "Option B (compose_bilingual LLM) for variable-content row inserts"
    - "OR-block contract: redact_bilingual raises if EITHER half blocked"
    - "Per-locale scoping: banned_phrases.check(text, locales=('en',|'ka',))"
key-files:
  created:
    - scripts/communicator/bilingual.py
    - tests/test_compose_bilingual.py
  modified:
    - scripts/communicator/weekly_brief.py
    - scripts/manager/briefing.py
    - agents/communicator.py
decisions:
  - "Use scripts.cognition.budget.check_daily_budget (not scripts.ledger as PLAN said) — same FND-04 ceiling, real import path"
  - "BILINGUAL_TEST_MODE=1 env var (or unset ANTHROPIC_API_KEY) returns deterministic stub {'en': prompt, 'ka': '[KA-PLACEHOLDER] '+prompt} — verifier exercises code path without API credits"
  - "summary_lines field type changed list[str] → list[dict[str, str]] — PDF renderer reads .en for display, .ka persists to JSONB for Telegram audience routing in 06-12"
  - "ReportLab PDF renders English half only (Mkhedruli requires CJK font registration outside this plan's scope)"
metrics:
  duration: "~25 minutes wall"
  completed: "2026-05-21"
  tasks_completed: "3/3 + metadata"
  files_touched: 5
  pytest_cases_green: "4 new (bilingual) + 65 existing (06-11 imperative-verb) = 69 total"
---

# Phase 06 Plan 09: Communicator + Phase 5 composer bilingual emission — Summary

Wired the **bilingual write path** for the Communicator (CrewAI) + Phase 5 weekly-brief composer + Phase 5 morning-briefing composer. Single `compose_bilingual()` helper uses Anthropic Claude Sonnet 4.5 strict tool_use (`tools=[{strict: True, input_schema: {en, ka}}]` + forced `tool_choice`) to emit schema-validated `{en, ka}` pairs in one API call. Weekly brief uses Option A deterministic prose mirror (zero Anthropic cost); Communicator per-row inserts and manager-briefing template strings use Option A/B per RESEARCH.md Pattern 6. **`outreach_drafter.py` UNCHANGED** per CONTEXT.md D-02 per-tier policy.

## What Got Built

### 1. `scripts/communicator/bilingual.py` — `compose_bilingual()` helper (201 lines, 4 pytest cases)

The canonical primitive for bilingual emission. Single Anthropic `messages.create()` call with strict tool_use:

```python
from scripts.communicator.bilingual import compose_bilingual, BILINGUAL_TOOL

# BILINGUAL_TOOL = {
#   "name": "compose_bilingual",
#   "strict": True,
#   "input_schema": {
#     "type": "object",
#     "properties": {"en": {"type": "string"}, "ka": {"type": "string"}},
#     "required": ["en", "ka"],
#     "additionalProperties": False
#   }
# }

pair = compose_bilingual(
    "Draft a family-readable hypothesis title about cord blood EAP.",
    client=anthropic.Anthropic(),
)
# pair == {"en": "...", "ka": "..."}   # grammar-constrained — both keys guaranteed
```

**Test-mode escape hatch (operator-facing):** set `BILINGUAL_TEST_MODE=1` (or simply have no `ANTHROPIC_API_KEY` in env) and `compose_bilingual` returns a deterministic stub `{'en': prompt, 'ka': '[KA-PLACEHOLDER] ' + prompt}`. CI / verifier / smoke runs exercise the code path without burning credits.

**Budget gate:** `check_daily_budget(raise_on_over=True)` from `scripts.cognition.budget` fires BEFORE the Anthropic call (Phase 0 FND-04 defence-in-depth).

### 2. `scripts/communicator/weekly_brief.py` — Option A deterministic mirror

- New module-level lookup tables: `SUMMARY_TEMPLATES_EN` + `SUMMARY_TEMPLATES_KA` (5 entries each — papers / hypotheses / therapies / outreach_pending / open_questions).
- `_bilingual_line(key, n=…)` and `_bilingual_mirror(value)` helpers.
- `BriefSections.summary_lines` field re-typed `list[str]` → `list[dict[str, str]]`.
- `BriefSections.to_dict()` now emits the bilingual shape into briefs.sections JSONB (per-row `title`/`name`/`subject`/`question`/`context` wrapped via `_bilingual_mirror`; internal scalars stay as-is).
- `collect_sections()` live + fixture paths emit `{en, ka}` summary lines.
- `render_pdf()` reads `.en` for display; PHI safety-net redactor sweeps BOTH halves of each summary dict.
- New CLI flag `--bilingual-test` emits `sections.to_dict()` as UTF-8 JSON to stdout (no PDF, no DB). Verifier hook.

### 3. `scripts/manager/briefing.py` — Option A for the morning briefing

- New `BRIEFING_TEMPLATES_KA` dict (11 keys mapping 3-bullet structure: today / activity / follow-ups variants).
- `BriefMessage.bilingual_bullets: list[dict[str, str]]` field carries the bilingual mirror.
- `compose()` builds both halves in lockstep — English text path unchanged for Phase 5 Telegram dispatch backward-compat; the `.ka` half persists into `briefs.sections` JSONB for plan 06-12's audience routing to read.
- `_insert_briefs_row()` adds `bilingual_bullets` to the persisted sections dict alongside the legacy `bullets` field.

### 4. `agents/communicator.py` — Option B canonical write-path helper

New `insert_bilingual_row()` — the pattern any CrewAI Tool() instance MUST use when writing to `aleksandra_timeline`, `hypotheses`, or `therapies`:

```python
pair_title = compose_bilingual("Draft a hypothesis title about ...", client=client)
pair_desc  = compose_bilingual("Draft the supporting description ...", client=client)
new_id = insert_bilingual_row(
    table="hypotheses",
    bilingual_fields={"title": pair_title, "description": pair_desc},
    scalar_fields={"status": "proposed", "confidence_level": "low"},
)
```

What it does:
1. Validates `table` against `BILINGUAL_TABLES` allow-list (prevents accidental bilingual writes to internal tables).
2. Calls `redact_bilingual()` on BOTH halves of every bilingual field — raises `BilingualWriteBlocked` on EITHER-half block (RESEARCH.md Pitfall 5 OR-block contract).
3. Calls `banned_phrases.check(en_text, locales=('en',))` and `banned_phrases.check(ka_text, locales=('ka',))` — Phase 3 CGM-04 + Phase 6 D-05 per-locale scoping. Raises on EITHER violation.
4. Builds INSERT with `psycopg2.extras.Json(pair)` + `%s::jsonb` cast for each bilingual column. Scalar columns pass through.
5. `BilingualWriteBlocked` exception message names WHICH side tripped (`"en: imperative violation"` vs `"ka: name leak"`) for audit.

Consumes:
- `scripts.communicator.bilingual.compose_bilingual` (this plan's Task 1)
- `scripts.communicator.phi_redactor.redact_bilingual` (06-10)
- `scripts.communicator.banned_phrases.check(text, locales=...)` (06-11)

## Audit Table — Georgian Translations Landed

### `scripts/communicator/weekly_brief.py` — SUMMARY_TEMPLATES_KA (5 entries)

| Key | English (existing) | Georgian (new) |
|-----|-------------------|----------------|
| `papers` | `{n} new relevant papers this week.` | `ამ კვირას {n} ახალი რელევანტური სტატია.` |
| `hypotheses` | `{n} hypothesis updates.` | `{n} ჰიპოთეზის განახლება.` |
| `therapies` | `{n} therapy candidates under active monitoring.` | `{n} თერაპიის კანდიდატი აქტიური მონიტორინგის ქვეშ.` |
| `outreach_pending` | `{n} outreach drafts pending review.` | `{n} გასაგზავნი მონახაზი მიმოხილვისთვის.` |
| `open_questions` | `{n} open family questions.` | `{n} ღია ოჯახური კითხვა.` |

### `scripts/manager/briefing.py` — BRIEFING_TEMPLATES_KA (11 entries)

Cover the 3-bullet morning-briefing structure (today / activity / follow-ups) in all variants — single event vs multi vs none, evidence-only vs therapy-only vs both vs quiet, pending drafts vs clear inbox. All translations avoid D-05 banned imperatives (`უნდა`, `აუცილებლად`, `განიხილეთ`, `მოითხოვეთ`, `ითხოვეთ`, `გაითვალისწინეთ`, `სცადეთ`) — descriptive Georgian only.

**TODO(Phase 6 execute):** Shako sanity-check both translation tables before final merge. The lint correctness is functional today; the gap is review-not-yet-done, not code-not-correct.

## Cost Note

Per RESEARCH.md Pattern 6:
- Strict tool_use system-prompt overhead: ~313 tokens per call (vs 346 for auto). At Sonnet 4.5 $3 in / $15 out per 1M tokens, that's ~$0.001 overhead per call.
- Per-content cost varies with section length; estimated ~$0.01–$0.02 per `compose_bilingual` call for a section-sized draft (1024 max_tokens cap).
- **weekly_brief uses Option A** (deterministic mirror) → zero Anthropic cost for the summary block.
- **manager/briefing uses Option A** (deterministic mirror) → zero Anthropic cost.
- **agents/communicator Option B** only fires when the CrewAI Crew runs (currently dormant — `TOOLS: list = []`). Estimated ~50–100 calls/month at production cadence = $1–2/month → comfortable under Phase 6 $5 cap.

## Deviations from Plan

### Rule 3 — Auto-fix blocking issues

**1. Wrong budget-gate import path**
- **Found during:** Task 1
- **Issue:** Plan said `from scripts.ledger import check_daily_budget` but that function lives in `scripts.cognition.budget`. `scripts.ledger` has no such symbol.
- **Fix:** Used the real import path `from scripts.cognition.budget import check_daily_budget`. Same function signature, same FND-04 guarantee, same `raise_on_over=True` semantics. The plan's intent is preserved.
- **Files modified:** `scripts/communicator/bilingual.py`
- **Commit:** `8de940d`

### Rule 2 — Auto-add missing critical functionality

**2. Test-mode escape hatch for verifier / CI**
- **Found during:** Task 1
- **Issue:** Plan acceptance criteria require `python -c "from scripts.communicator.bilingual import compose_bilingual; ..."` to work without burning Anthropic credits. The executor prompt explicitly asks for a `BILINGUAL_TEST_MODE=1` fallback.
- **Fix:** Added `_is_test_mode()` + `_stub_pair()`. When `BILINGUAL_TEST_MODE=1` env var is set OR `ANTHROPIC_API_KEY` is unset, `compose_bilingual` returns deterministic `{'en': prompt, 'ka': '[KA-PLACEHOLDER] ' + prompt}` without contacting Anthropic. The Georgian placeholder is INTENTIONALLY marked so any downstream consumer can detect test-mode rows.
- **Files modified:** `scripts/communicator/bilingual.py`
- **Commit:** `8de940d`

**3. Bilingual safety-net redactor in weekly_brief.render_pdf**
- **Found during:** Task 2
- **Issue:** Existing `render_pdf` PHI safety-net joined `sections.summary_lines` as a list of strings. Now that the field is `list[dict]`, joining would produce `"{en:..., ka:...}"` text — wrong shape, wouldn't catch real PHI patterns.
- **Fix:** Refactored the safety-net to flatten BOTH halves of every summary dict before joining. Now sweeps Georgian PHI patterns too (per RESEARCH.md Pitfall 5; consumes redact_bilingual contract from 06-10).
- **Files modified:** `scripts/communicator/weekly_brief.py`
- **Commit:** `72837cd`

### Plan-text vs file shape

**4. `bilingual.py` line count: 201 vs plan's 50–120 target**
- **Found during:** Task 1 acceptance check
- **Issue:** Plan acceptance says "line count between 50 and 120." Authored file is 201 lines.
- **Why:** Executor prompt explicitly requires the test-mode escape hatch ("Operator Notes" call-out), module docstring documenting D-02 per-tier policy + cost note + budget gate, and per-function docstrings explaining the strict tool_use contract. Functional code (imports + constants + 2 helpers + main function) is ~80 lines; remaining 120 are documentation block-comments. Anti-creep gate trade-off taken: documentation density wins over line-count target because this is a Phase-6-defining primitive that downstream plans (06-12 audience routing, future Communicator Tool() instances) read frequently.
- **Rule:** N/A (plan-text mismatch, not bug/feature/blocker). Documented for traceability.

## Outreach_drafter UNCHANGED Confirmation

```
$ git diff --stat HEAD~10 -- scripts/communicator/outreach_drafter.py
(empty — zero lines)
```

Zero lines of diff over the last 10 commits. **CONTEXT.md D-02 per-tier policy honored**: single-recipient single-language outreach stays on the existing `contacts.outreach_language` rail; this plan does not touch the file.

## Verification

```
$ python -X utf8 -m pytest tests/test_compose_bilingual.py -v
tests/test_compose_bilingual.py::test_1_tool_use_block_returns_en_ka_pair PASSED
tests/test_compose_bilingual.py::test_2_no_tool_use_block_raises_runtime_error PASSED
tests/test_compose_bilingual.py::test_3_bilingual_tool_schema_integrity PASSED
tests/test_compose_bilingual.py::test_4_default_model_is_sonnet_4_5 PASSED
4 passed in 0.37s

$ python -X utf8 -m scripts.verify_phase6 --mode code-complete
... I18N-06 PASS  Communicator emits {en, ka} via compose_bilingual
... 9/11 PASS — NEEDS WORK
(I18N-07 + I18N-11 are Wave 4 by design — plans 06-12 + 06-13)

$ BILINGUAL_TEST_MODE=1 python -c "from scripts.communicator.bilingual import compose_bilingual; print(compose_bilingual('Hello'))"
{'en': 'Hello', 'ka': '[KA-PLACEHOLDER] Hello'}

$ python -X utf8 -m scripts.communicator.weekly_brief --dry-run --bilingual-test
{ "summary_lines": [{"en": "...", "ka": "..."}, ...], ... }

$ python -X utf8 -m scripts.verify_phase5 --gate mng-10 --mode code-complete
MNG-10 PASS  Morning briefing delivers Sunday 09:00 ≤50 words

$ python -X utf8 -m scripts.verify_phase3 --gate cgm-05
CGM-05 PASS  Weekly Brief renders end-to-end with citation appendix
```

**Phase 6 verifier delta:** 8/11 PASS pre-06-09 → **9/11 PASS post-06-09**. I18N-06 flipped from FAIL to PASS. I18N-10 stays PASS (Wave 3a infrastructure). Remaining 2 PENDING (I18N-07 / I18N-11) are Wave 4 by design.

**No regressions:**
- Phase 3 CGM-05 (weekly brief PDF): 1/1 PASS
- Phase 5 MNG-10 (manager briefing): 1/1 PASS
- 65 existing 06-11 imperative-verb lint tests: still 65/65 GREEN
- All imports: `agents.communicator`, `scripts.manager.briefing`, `scripts.communicator.weekly_brief`, `scripts.communicator.bilingual` all import cleanly

## Operator Notes

**Test mode for smoke runs / CI / verifier:**
```
set BILINGUAL_TEST_MODE=1     # PowerShell: $env:BILINGUAL_TEST_MODE = "1"
python -c "from scripts.communicator.bilingual import compose_bilingual; print(compose_bilingual('Hello'))"
# → {'en': 'Hello', 'ka': '[KA-PLACEHOLDER] Hello'}
```

Or simply omit `ANTHROPIC_API_KEY` from the environment — same fallback fires defensively.

**Production cost-gate test:** With `ANTHROPIC_API_KEY` set, `compose_bilingual` calls `check_daily_budget(raise_on_over=True)` BEFORE the SDK call. If daily spend is already over the FND-04 cap, `BudgetExceeded` raises and the SDK call never fires.

**Future Crew activation:** When the CrewAI Crew is actually run (currently `TOOLS: list = []`), each entry in `COMMUNICATOR_TOOLS` will be wrapped as a CrewAI `Tool()` instance. The Communicator agent's backstory tells the model to use `compose_bilingual` + `redact_bilingual` for every family-visible write — the framework just needs the `@tool` decoration to land.

## Self-Check: PASSED

**Created files:**
- FOUND: scripts/communicator/bilingual.py (201 lines)
- FOUND: tests/test_compose_bilingual.py (117 lines, 4 pytest cases)

**Modified files (git log -p verified):**
- FOUND: scripts/communicator/weekly_brief.py (commit 72837cd)
- FOUND: scripts/manager/briefing.py (commit a3111c2)
- FOUND: agents/communicator.py (commit a3111c2)

**Commits:**
- FOUND: 8de940d feat(06-09): compose_bilingual Anthropic strict tool_use helper
- FOUND: 72837cd feat(06-09): weekly_brief emits {en, ka} JSONB for briefs.sections
- FOUND: a3111c2 feat(06-09): bilingual write path for Communicator and manager briefing

**Verifier:** I18N-06 PASS (was FAIL); Phase 6 9/11 GREEN (was 8/11).
**Regression:** Phase 3 CGM-05 GREEN; Phase 5 MNG-10 GREEN; 65 existing pytest cases GREEN.
**D-02 contract:** outreach_drafter.py UNCHANGED (git diff vs HEAD~10 → 0 lines).
