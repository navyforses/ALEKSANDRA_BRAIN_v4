---
status: pending
created: 2026-05-21
resolves_phase: maintenance
source: .planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-11-SUMMARY.md
owner: Shako (native-Georgian-speaker review)
priority: P2 (lint already live in code; review confirms the literal-string catalog is correct for the polite-plural medical-advice register)
estimated_window: 10-15 minutes (read the 8 entries; type "approved" or list removals/additions)
related_plan: 06-11-banned-phrases-georgian-extension
---

# Shako Native-Speaker Re-Verify: 06-11 D-05 Imperative-Verb Lexicon

## Context

Plan 06-11 was executed in **Auto Mode** on 2026-05-21. The plan's Task 3 was a `checkpoint:human-verify` gate requiring Shako (native Georgian speaker) to sanity-check the 8 D-05 imperative-verb patterns appended to `scripts/communicator/banned_phrases.py` **before activation**. Per the auto-mode directive in the plan-execution prompt, the checkpoint was auto-approved against the locked D-05 reference in `06-CONTEXT.md` (Decisions section) — the executor landed the lexicon verbatim from D-05 + RESEARCH.md Pattern 8, with each entry preceded by a `TODO(shako-review)` comment marking it as pending native-speaker confirmation.

The lint is functional today (65 pytest cases GREEN, Phase 6 verifier check_i18n_10 PASS, Phase 3 CGM-04 unregressed). This maintenance todo tracks the post-hoc Shako review that the original plan placed BEFORE activation.

**Why this is P2 (not P0/P1).** The 8 entries are direct mappings of the 6 English banned imperatives Phase 3 CGM-04 already enforces; the D-05 decision was locked in CONTEXT.md after planner research (linguist-style mapping of subject+modal English forms to polite-plural Georgian imperatives). RESEARCH.md A6 expressly accepts ~90% catch rate from literal-string match — Shako's review absorbs the 10% gap by adding/removing entries based on what the Communicator actually emits. The lint is not currently used in a production path that has emitted Georgian content (Wave-3b 06-09 lands the bilingual emission); so a wrong-entry false positive cannot harm any family-facing artifact yet.

## What to do

Open `scripts/communicator/banned_phrases.py` and locate the `# ===== Phase 6 D-05 additions — REVIEW BEFORE ACTIVATION =====` block (currently ~lines 95–113).

For each of the 8 new patterns, evaluate whether the Georgian form genuinely appears in the polite-plural medical-advice register the Communicator might emit:

| # | English target | Georgian form | Verification question |
|---|----|---|---|
| 1 | "should" (you-ought) | `\bმართებთ\b` | Does an advice-giving sentence use this form? Or is it dominantly past-tense lookalike? |
| 2 | "must" (bare) | `\bაუცილებლად\b` | Existing compound `აუცილებლად გაუმჯობესდება` already in lexicon (line ~91); this adds bare-form catch. False-positive tolerated? |
| 3 | "must" (predicative) | `\bაუცილებელია\b` | "It is necessary" — confirm imperative-advice use vs benign predicative use. |
| 4 | "consider" (polite 2pl) | `განიხილეთ` | Standard Georgian polite imperative — already used by fixture S27 ka. |
| 5 | "consider" (alt) | `გაითვალისწინეთ` | "Take into account" — polite imperative. |
| 6 | "try" | `სცადეთ` | Polite imperative 2pl of "try" — already used by fixture S28 ka. **Note:** `viewer/messages/ka.json` Shared.errorRetry = "სცადეთ ხელახლა" is a static UI label and is OUTSIDE the lint scope (which targets Communicator digests, not dictionaries). |
| 7 | "ask for" | `მოითხოვეთ` | Polite imperative 2pl. |
| 8 | "request" | `ითხოვეთ` | Polite imperative 2pl. |

**Decision options:**

1. **All 8 approved as-is** → reply `approved`. Executor strips `TODO(shako-review):` markers and replaces with `# APPROVED BY SHAKO 2026-MM-DD: <English mapping>`.
2. **Remove one or more** (entry too benign in subordinate clauses → too many false positives) → reply `remove: <pattern>` per line. Executor comments out with `# REMOVED PER SHAKO REVIEW <date>:` (audit preserved); pytest `POSITIVE_KA_CASES` updated; verifier rerun.
3. **Add new patterns Shako has heard the Communicator emit** → reply `add: <pattern> for <English mapping>` per line. Executor appends with same TODO(shako-review) header (treated as approved by being volunteered).

After resolution: update `06-11-SUMMARY.md` "Self-Approved Lexicon" section's "Final approval state" subsection with the outcome (approved-verbatim / approved-with-changes), and remove this maintenance todo from `.planning/todos/pending/`.

## Acceptance

- `scripts/communicator/banned_phrases.py` contains zero `TODO(shako-review)` markers in `_PATTERNS_KA` (each replaced with `APPROVED BY SHAKO YYYY-MM-DD`).
- `python -m pytest tests/test_imperative_verb_lint_georgian.py -v` still exits 0 (65/65 PASS, or new count if entries added/removed).
- `python -m scripts.verify_phase6 --bucket C --mode code-complete` still shows I18N-10 PASS.

## Reference

- D-05 decision: `.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-CONTEXT.md` Decisions §D-05
- RESEARCH.md Pattern 8 (literal-string approach + Mkhedruli word-boundary note)
- 06-VALIDATION.md "Manual-Only Verifications" section
- Auto-mode-approval SUMMARY: `.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-11-SUMMARY.md`
