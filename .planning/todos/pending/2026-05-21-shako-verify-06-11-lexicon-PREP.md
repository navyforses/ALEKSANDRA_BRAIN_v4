---
status: pending
created: 2026-05-24
prepared_by: v7-i18n
for: Shako (native-Georgian-speaker review)
estimated_window: 10-15 minutes
default_if_no_response: ALL 8 APPROVED (per auto-mode contract in 06-11-SUMMARY.md)
companion: 2026-05-21-shako-verify-06-11-lexicon.md
---

# 06-11 KA Lexicon Review — Pre-filled Decision Document

> 8 D-05 imperative-verb patterns appended to `scripts/communicator/banned_phrases.py`
> awaiting native-speaker confirmation. Lint is already live (65/65 pytest GREEN,
> verify_phase6 I18N-10 PASS); this review absorbs the ~10% literal-string gap
> RESEARCH.md A6 accepts. No family-facing artifact has emitted Georgian content yet,
> so wrong-entry false positives cannot have harmed anything to date.

## Quick decision (recommended path)

If you agree with all 8 defaults in the table below, reply with one word: `approved`

If you disagree on any entry, reply with the lines you want to change. Format:
- `remove: <pattern>` (one per line) → executor comments it out with audit trail
- `add: <pattern> for <English mapping>` (one per line) → executor appends
- Anything not mentioned stays KEEP.

## 8 entries with v7-i18n recommendation

All 8 defaults are **KEEP** (v7-i18n confirms each maps to a polite-plural
imperative form the Communicator could plausibly emit when drafting advice).
The table flags the two entries with the highest false-positive risk so you
can scrutinize them first.

| # | EN target | KA pattern (regex) | Default | v7-i18n rationale | Pytest fixture | FP risk |
|---|---|---|---|---|---|---|
| 1 | should (you-ought) | `\bმართებთ\b` | KEEP | Direct-instruction "you ought" form. Rare in everyday register; when it does appear, it is almost always prescriptive. | `ka-should` (line 90) | low |
| 2 | must (bare) | `\bაუცილებლად\b` | KEEP | Bare adverb "necessarily". Complements the existing compound `აუცილებლად გაუმჯობესდება` at line 91. **Risk:** common in benign clauses (e.g., "this is necessarily a draft"); the existing _PATTERNS_EN allows `must` only after subject (Aleksandra/the patient), so the KA bare form is broader by design. Acceptable per RESEARCH.md A6 (false positives preferred over false negatives). | `ka-must-bare` (line 91) | **medium** |
| 3 | must (predicative) | `\bაუცილებელია\b` | KEEP | Predicative "it is necessary". Same FP shape as #2 but slightly tighter (predicative copula form). | `ka-must-pred` (line 92) | low-medium |
| 4 | consider (polite 2pl) | `განიხილეთ` | KEEP | Canonical polite imperative. Standard advice register. No common benign sense. | `ka-consider` (line 93) | low |
| 5 | consider (alt) | `გაითვალისწინეთ` | KEEP | "Take into account" polite imperative. Slightly more formal than #4; same advice register. | `ka-consider2` (line 94) | low |
| 6 | try | `სცადეთ` | KEEP | Polite imperative 2pl. **Caveat verified:** the only repo string that matches is `viewer/messages/ka.json` line 188 `Shared.errorRetry = "სცადეთ ხელახლა"`, which is a static UI label and **outside lint scope** (lint runs on Communicator output, not on UI dictionaries). Confirmed by grep — no other matches in repo. | `ka-try` (line 95) | low (UI label out of scope) |
| 7 | ask for | `მოითხოვეთ` | KEEP | Polite imperative 2pl "demand / ask for". Strong advice register. | `ka-askfor` (line 96) | low |
| 8 | request | `ითხოვეთ` | KEEP | Polite imperative 2pl. Slightly softer than #7 but same family. | `ka-request` (line 97) | low |

## Critical anti-loop reminder

None of the 8 patterns share a root with a common Communicator vocabulary word
that could trigger the Phase 6.1 generation-loop bug. The 4 forbidden roots
(`ცარიელი`, `ცამეტი`, `ფარული`, `ცდილია`) do not appear in any of the 8
patterns. Safe to land verbatim.

## False-positive likelihood against viewer/messages/ka.json

Repo-wide grep over the 8 patterns against `viewer/messages/ka.json`:
- 1 match: `errorRetry = "სცადეთ ხელახლა"` (entry #6, line 188).
- Match is in `viewer/messages/`, which is OUT OF LINT SCOPE (lint runs against
  Communicator digests via `scripts/communicator/banned_phrases.check()`).
- 0 matches for the other 7 patterns.

Conclusion: no false-positive surface in the static UI dictionary. Risk is
isolated to Communicator-emitted text, where the false positives are accepted
by design.

## Verification after Shako responds

After Shako replies (or after the auto-mode default fires), the executor runs
this 2-command sequence to confirm no regression:

```
python -m pytest tests/test_imperative_verb_lint_georgian.py -v
python -m scripts.verify_phase6 --bucket C --mode code-complete
```

Expected: 65/65 PASS (or new count if entries added/removed) + I18N-10 PASS.

## Highest- and lowest-risk summary

- **Highest risk:** Entry #2 `\bაუცილებლად\b` (bare "necessarily"). Adverb is
  common in benign clauses; the lint will fire on legitimate non-imperative
  uses. Acceptable per the A6 false-positive trade-off, but Shako may choose to
  REMOVE it and rely on entry #3 `\bაუცილებელია\b` (the predicative form, which
  is tighter).
- **Lowest risk:** Entry #4 `განიხილეთ` (polite imperative "consider"). Used by
  fixture `ka-consider`; no plausible benign sense in the medical-advice
  register; already a recognized Communicator phrase pattern.

## References

- `scripts/communicator/banned_phrases.py` (lines 93-118, D-05 block)
- `tests/test_imperative_verb_lint_georgian.py` (lines 89-107, POSITIVE_KA_CASES)
- `.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-CONTEXT.md` Decisions §D-05 (lines 127-144)
- `.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-11-SUMMARY.md` Self-Approved Lexicon section
- `.planning/todos/pending/2026-05-21-shako-verify-06-11-lexicon.md` (companion full-context todo)
- `viewer/messages/ka.json` line 188 (only in-repo match; out of lint scope)
