---
phase: 06-bilingual-system-i18n
plan: 11
subsystem: communicator-lint
tags: [i18n, georgian, lint, banned-phrases, cgm-04-regression, auto-mode]
dependency-graph:
  requires: [06-02]
  provides: [I18N-10 imperative-verb half]
  affects: [scripts/communicator/banned_phrases.py, tests/test_imperative_verb_lint_georgian.py]
tech-stack:
  added: []
  patterns:
    - RESEARCH.md Pattern 8 (literal-string Mkhedruli match with selective \b word-boundary)
    - Per-locale scoping kwarg `locales=(...)` on check() (RESEARCH.md Open Question #3 — already present in code, no signature change required)
key-files:
  created:
    - tests/test_imperative_verb_lint_georgian.py
    - .planning/todos/pending/2026-05-21-shako-verify-06-11-lexicon.md
  modified:
    - scripts/communicator/banned_phrases.py
decisions:
  - "Auto-mode-approved the 8 D-05 lexicon entries against the locked CONTEXT.md D-05 reference (Task 3 checkpoint:human-verify deferred to post-hoc Shako review via maintenance todo)"
  - "Removed English positive-catch assertions from Group A — fixture's bare-verb paraphrases fall outside Phase-3 _PATTERNS_EN by design (subject+modal scope); plan Task 1 (c) freezes _PATTERNS_EN"
metrics:
  duration: 13min
  completed: 2026-05-21
---

# Phase 6 Plan 06-11: Imperative-Verb Lint Georgian Extension Summary

**One-liner:** Appended 8 Georgian polite-imperative regex patterns (D-05 lexicon) to `_PATTERNS_KA` in `banned_phrases.py` and wired a 65-case pytest regression suite; Phase 6 verifier check_i18n_10 flips PASS; Phase 3 CGM-04 unregressed.

## What changed

### `scripts/communicator/banned_phrases.py` (+26 lines)

- New Phase 6 D-05 block appended to `_PATTERNS_KA` (after the existing 11 Phase-3 entries).
- 8 new regex patterns mapping the 6 English banned imperatives to Georgian polite-plural forms.
- Each entry preceded by a `TODO(shako-review)` inline comment naming the English mapping.
- A block-header comment explains RESEARCH.md Pattern 8 word-boundary policy: the first three additions (`\bმართებთ\b`, `\bაუცილებლად\b`, `\bაუცილებელია\b`) carry `\b` because they typically appear at Mkhedruli ↔ ASCII script boundaries; the remaining five (`განიხილეთ`, `გაითვალისწინეთ`, `სცადეთ`, `მოითხოვეთ`, `ითხოვეთ`) match without `\b` per the existing _PATTERNS_KA convention.
- `check(text, locales=(...))` signature was already present (existing Phase-3 code, lines 120–135); no kwarg change required. Backward-compat preserved — callers that don't pass `locales` get the default `('en', 'ka', 'fr')` tuple.

### `tests/test_imperative_verb_lint_georgian.py` (new, 130 lines)

65 pytest cases across 5 groups (parametrized — 5 pytest functions, 65 invocations):

| Group | Function | Count | Purpose |
|---|---|---:|---|
| A.en | `test_clean_sample_lint_clean_en` | 25 | No false positives on 25 clean English samples under `locales=('en',)` |
| A.ka | `test_clean_sample_lint_clean_ka` | 25 | No false positives on 25 clean Georgian samples under `locales=('ka',)` |
| A.pos.ka | `test_positive_sample_caught_ka` | 5 | Each of 5 fixture `banned=true` samples (S26–S30) is caught on its Georgian half |
| B | `test_d05_lexicon_catches_planted_violation` | 8 | Each of the 8 new D-05 entries catches a planted Georgian violation |
| C | `test_english_regression_phase3_cgm04` | 1 | "you should consider trying that approach" still trips the English lexicon |
| D | `test_locale_scoping_excludes_unrequested_locales` | 1 | Georgian banned text under `locales=('en',)` returns passed=True (no leak) |

`python -m pytest tests/test_imperative_verb_lint_georgian.py -v` → **65 passed in 0.07s**.

### `.planning/todos/pending/2026-05-21-shako-verify-06-11-lexicon.md` (new)

Maintenance todo (P2) tracking the post-hoc Shako native-Georgian-speaker review of the 8 lexicon entries. Records the auto-mode-approval audit trail and provides Shako a one-page decision form (approve / remove / add) for when next at console.

## Self-Approved Lexicon

**Auto-Mode authorization.** Plan 06-11 Task 3 was authored as `checkpoint:human-verify gate="blocking-human"` requiring Shako to sanity-check the 8 entries before activation. The execute-plan prompt for this session overrode the gate with `AUTO MODE ACTIVE` instructions: *"Auto mode overrides this — proceed using the D-05 locked 8-entry lexicon from CONTEXT.md verbatim. Do NOT pause for confirmation. Document the auto-mode-approved lexicon in SUMMARY.md 'Self-Approved Lexicon' section."*

The 8 entries below are taken verbatim from CONTEXT.md §Decisions D-05 (the locked reference) cross-checked against RESEARCH.md Pattern 8 (`<read_first>` block in the plan's Task 1). Native-speaker re-verification by Shako is tracked separately at `.planning/todos/pending/2026-05-21-shako-verify-06-11-lexicon.md`.

| # | Regex pattern | English target | Notes |
|---|---|---|---|
| 1 | `\bმართებთ\b` | "should" (you-ought, direct-instruction) | `\b` carried for Mkhedruli ↔ ASCII script boundary |
| 2 | `\bაუცილებლად\b` | "must" (bare 'necessarily') | Adds standalone catch on top of the existing compound `აუცილებლად გაუმჯობესდება` |
| 3 | `\bაუცილებელია\b` | "must" (predicative 'it is necessary') | `\b` carried |
| 4 | `განიხილეთ` | "consider" (polite imperative 2pl) | Triggered by fixture S27 ka |
| 5 | `გაითვალისწინეთ` | "consider" (alt form: 'take into account') | |
| 6 | `სცადეთ` | "try" (polite imperative 2pl) | Triggered by fixture S28 ka |
| 7 | `მოითხოვეთ` | "ask for" (polite imperative 2pl) | Triggered by fixture S29 ka |
| 8 | `ითხოვეთ` | "request" (polite imperative 2pl) | Triggered by fixture S30 ka |

**Final approval state:** auto-mode-approved (Shako re-verify pending — maintenance todo open).

> Plan 06-11 Task 3 (`checkpoint:human-verify`) was auto-mode-approved against the locked D-05 reference. Maintenance todo filed at `.planning/todos/pending/2026-05-21-shako-verify-06-11-lexicon.md` for Shako to re-verify when next at console.

## Verification

| Check | Command | Result |
|---|---|---|
| pytest suite | `python -X utf8 -m pytest tests/test_imperative_verb_lint_georgian.py -v` | **65 passed** |
| Phase 3 CGM-04 regression | `python -X utf8 -m scripts.verify_phase3 --gate cgm-04` | **1/1 PASS — ALL GREEN** |
| Phase 6 bucket C (I18N-10) | `python -X utf8 -m scripts.verify_phase6 --bucket C --mode code-complete` | **I18N-10 PASS** (I18N-06 correctly PENDING — Wave-3b 06-09 owns it) |
| TODO marker count | `grep -c "TODO(shako-review)" scripts/communicator/banned_phrases.py` | **8** (matches plan acceptance floor) |
| Acceptance cmd 1 | `check('მართებთ რომ მიიღოს თერაპია', locales=('ka',)).passed` | **False** (caught) |
| Acceptance cmd 2 | `check('ეს არის კვლევის შედეგი.', locales=('ka',)).passed` | **True** (clean) |
| Acceptance cmd 3 | `check('you should consider trying', locales=('en',)).passed` | **False** (caught) |
| Per-locale scoping | `check('მართებთ რომ მიიღოს თერაპია', locales=('en',)).passed` | **True** (no leak) |

## Deviations from Plan

### Rule 3 — Scope correction in Task 2 test design

**Found during:** Task 2 first pytest run.

**Issue:** Plan Task 2 Group A specified "for each sample, assert `check(sample['en'], locales=('en',)).passed is True` AND `check(sample['ka'], locales=('ka',)).passed is True`" across all 30 fixtures. But the fixture (authored in Plan 06-02) has `banned=true` flagged on 5 of 30 entries (S26–S30) whose Georgian half contains D-05 banned forms, and asserting the **English** half of those same banned samples must also trip violates Plan Task 1 (c): "DO NOT modify `_PATTERNS_EN` or `_PATTERNS_FR`. Phase 6 only extends the Georgian lexicon."

Three of the five fixture English paraphrases use bare verbs (`Please consider …`, `The family must try …`, `Please request …`) that the existing `_PATTERNS_EN` does NOT catch by design (Phase-3 CGM-04 scopes to subject+modal phrasings like "you should", "we recommend"). A strict positive-catch assertion on those English halves would require extending `_PATTERNS_EN` — out of Plan 06-11 scope.

**Fix:** Restructured Group A into three parametrized functions partitioned on the fixture's `banned` flag:
- 25 clean-en lint-clean (no false positives)
- 25 clean-ka lint-clean (no false positives)
- 5 positive-ka catch (Georgian half — the Plan 06-11 contract)

Did **not** add an English positive-catch parametrization. Documented the omission inline at lines 74–83 of the test file with a paragraph citing Plan Task 1 (c).

**Files modified:** `tests/test_imperative_verb_lint_georgian.py`
**Commit:** `94698c6`

### Rule 4 — None

No architectural decisions required. No new dependencies, services, or schema changes.

### Auto-Mode override (not a deviation)

Plan Task 3 was a `checkpoint:human-verify gate="blocking-human"` checkpoint. The execute-plan prompt explicitly overrode the blocking-human gate via auto-mode directive (the prompt names this an explicit auto-mode authorization for this one checkpoint). This is **not** a Rule-based deviation — it is the documented session-level operating mode. Captured as a "Self-Approved Lexicon" section above with the maintenance todo as the post-hoc audit trail.

## Acceptance Criteria

- [x] `scripts/communicator/banned_phrases.py` `_PATTERNS_KA` contains the 8 D-05 entries (literal Mkhedruli substring search confirms)
- [x] File contains `TODO(shako-review)` ≥ 8 times (exact count: 8)
- [x] File contains comment header `Phase 6 D-05 additions`
- [x] `check('მართებთ რომ მიიღოს თერაპია', locales=('ka',)).passed == False`
- [x] `check('ეს არის კვლევის შედეგი.', locales=('ka',)).passed == True`
- [x] `check('you should consider trying', locales=('en',)).passed == False`
- [x] `python -m scripts.verify_phase3 --gate cgm-04` exits 0
- [x] `tests/test_imperative_verb_lint_georgian.py` exists and 65 cases pass (above the 39-floor target)
- [x] No tests marked xfail or skip
- [x] Per-locale scoping works (Georgian text under `locales=('en',)` returns passed=True)
- [x] Maintenance todo for Shako lexicon re-verify filed at `.planning/todos/pending/`

## Commits

- `6cd2cfb` — `feat(06-11): append D-05 Georgian imperative-verb lexicon to banned_phrases`
- `94698c6` — `test(06-11): bilingual imperative-verb lint regression suite`
- (final docs commit pending)

## Self-Check: PASSED

- `scripts/communicator/banned_phrases.py` exists and contains the 8 new patterns (verified)
- `tests/test_imperative_verb_lint_georgian.py` exists (verified — 130 lines)
- `.planning/todos/pending/2026-05-21-shako-verify-06-11-lexicon.md` exists (verified)
- Commit `6cd2cfb` present in `git log` (verified)
- Commit `94698c6` present in `git log` (verified)
- `python -m pytest tests/test_imperative_verb_lint_georgian.py -q` returns 65 passed (verified)
- `python -m scripts.verify_phase3 --gate cgm-04` returns 1/1 PASS (verified)
- `python -m scripts.verify_phase6 --bucket C --mode code-complete` returns I18N-10 PASS (verified)

## Threat Flags

No new threat surface introduced. The D-05 lexicon extension is an additive deny-list against patterns the Communicator should never emit — it narrows the trust boundary at `scripts/communicator/banned_phrases.py::check()`, it does not widen any surface. T-06-03 (Repudiation MEDIUM, planned threat) is mitigated by the 8-entry catalog + 65 pytest assertions + the Shako-review maintenance todo (provides the native-speaker review the original plan required, just post-hoc).

## What this unlocks

- **I18N-10 verifier check (Phase 6 bucket C):** flipped from PENDING (Wave 0 baseline) to PASS in code-complete mode. Combined with Plan 06-10's PHI-half deliverable, the I18N-10 requirement is now fully GREEN.
- **Wave 3a closure:** Plans 06-10 (PHI bilingual redactor) and 06-11 (imperative-verb lint Georgian) are both complete. Wave 3b (06-09 — Communicator `compose_bilingual` via Anthropic strict tool_use) is the next blocker for I18N-06.
- **Phase 6 verifier status after this plan:** expected to move from 8/11 PASS (06-10 baseline) to 9/11 PASS. Remaining PENDING: I18N-06 (06-09) and I18N-11 (06-13 regression sweep at Wave 4).

## Notes for future

- Outreach drafter callers (`scripts/communicator/outreach_drafter.py`) that scan English-only or French-only content may benefit from passing explicit `locales=('en',)` or `locales=('fr',)` to avoid the (currently-cheap) Georgian-pattern iteration. This is a micro-optimization, not a correctness requirement, and is **out of scope** for Plan 06-11 (Task 1 action (c) freezes English/French behavior).
- The 5 fixture English paraphrases (S27, S28, S30) that don't trip existing `_PATTERNS_EN` suggest a future Phase-3-side maintenance plan could broaden `_PATTERNS_EN` to bare-verb forms. Filed mentally — not landed as a separate todo because Plan 06-11 must not author Phase-3-scope work.
