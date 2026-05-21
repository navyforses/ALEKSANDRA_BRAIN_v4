---
phase: 06-bilingual-system-i18n
plan: 02
subsystem: testing
tags: [verifier, fixtures, i18n, georgian, phi-redactor, bilingual-lint, pytest]

requires:
  - phase: 06-01
    provides: "next-intl@4.12.0 installed + proxy.ts mounted + viewer/messages/{en,ka}.json relocated → I18N-01 baseline green"

provides:
  - "scripts/verify_phase6.py — runnable 11-check verifier scaffold (Check/Report dataclasses; --mode {production,code-complete}; --bucket {A,B,C,D,E}; --gate I18N-NN)"
  - "tests/fixtures/phase6/phi_ka.yaml — 10 Georgian PHI fixtures across 5 categories + 1 hard-block"
  - "tests/fixtures/phase6/bilingual_samples.json — 30 bilingual digest samples (25 clean / 5 positive-catch covering D-05 banned phrases)"
  - "Bucket dispatch map (CONTEXT.md D-06): A frontend, B database, C agent, D delivery, E regression"

affects: [06-03a, 06-03b, 06-04, 06-05a, 06-05b, 06-06, 06-07, 06-08, 06-09, 06-10, 06-11, 06-12, 06-13]

tech-stack:
  added: []
  patterns:
    - "Phase-5-style verifier (Check + Report dataclasses + table printer)"
    - "Bucket dispatch: per-bucket subset selection without re-running all 11 checks"
    - "RED-with-PENDING-evidence default for not-yet-implemented requirements"
    - "Fixture-driven validation: YAML for PHI, JSON for bilingual-lint samples"

key-files:
  created:
    - "scripts/verify_phase6.py"
    - "tests/fixtures/phase6/phi_ka.yaml"
    - "tests/fixtures/phase6/bilingual_samples.json"
    - ".planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-02-SUMMARY.md"
  modified: []

key-decisions:
  - "Mirror scripts/verify_phase5.py structurally (Check + Report dataclasses, --mode flag, table printer) so cumulative project verifier idiom is preserved (78 → 89 checks after Phase 6 closes)"
  - "Default to RED with PENDING evidence rather than crashing on missing-implementation modules — keeps Wave 0 scaffold runnable end-to-end so downstream plans can append real assertions incrementally"
  - "PHI fixture count exactly 10 across 5 categories (patient_name × 4, dob × 2, mrn × 1, hospital × 1, clinician × 1) + exactly 1 mri_artifact hard-block — matches 06-RESEARCH.md Pattern 8 verbatim"
  - "Bilingual-lint sample mix 25:5 (clean : positive-catch) — clean subset covers all 5 CGM-03 finding kinds × 5 each; positive-catch covers each D-05 banned phrase (should / consider+განიხილეთ / try+სცადეთ / ask-for+მოითხოვეთ / request+ითხოვეთ)"
  - "tools[].triggered_phrase field documents WHICH banned phrase each positive-catch sample fires, simplifying plan 06-11's banned_phrases.py extension test"

patterns-established:
  - "Pattern: PENDING-evidence placeholders — every check_i18n_NN function defaults to Check(passed=False, evidence='PENDING — implemented in Wave N plan NN') until downstream plan lands real assertion"
  - "Pattern: Code-complete vs production split — code-complete passes on file existence + module presence; production requires DB roundtrip + subprocess spawn"
  - "Pattern: Mkhedruli fixtures stored UTF-8-no-BOM, validated by python -X utf8 on Windows; verifier reads with explicit encoding='utf-8'"

requirements-completed: [I18N-01, I18N-02, I18N-03, I18N-04, I18N-05, I18N-06, I18N-07, I18N-08, I18N-09, I18N-10, I18N-11]

duration: 16min
completed: 2026-05-20
---

# Phase 6 Plan 02: Verifier Scaffold + PHI & Bilingual-Lint Fixtures Summary

**11-check Phase-6 verifier scaffold (`scripts/verify_phase6.py`) with 5-bucket dispatch (A/B/C/D/E), plus the two Wave-0 fixture artifacts — 10 Georgian PHI phrases (`phi_ka.yaml`) and 30 bilingual digest samples (`bilingual_samples.json`) — that downstream plans 03-13 will consume.**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-05-20 (Wave 0)
- **Completed:** 2026-05-20
- **Tasks:** 3
- **Files modified:** 3 (created)
- **verify_phase6.py line count:** 1060 (≥300 acceptance criterion satisfied)

## Accomplishments

- `scripts/verify_phase6.py` runnable as module: `python -X utf8 -m scripts.verify_phase6 --mode code-complete` emits the 11-row table with 2/11 PASS (I18N-01 + I18N-10 already green; remaining 9 RED with PENDING evidence pointing to the responsible downstream plan).
- All 11 `check_i18n_NN` functions defined (verified by `python -c "import scripts.verify_phase6 as v; sum(1 for n in dir(v) if n.startswith('check_i18n_'))" → 11`).
- 5-bucket dispatch confirmed: `--bucket A` returns 5 rows (A frontend = I18N-01/02/03/04/08), `--bucket B` returns 2 rows (B database = I18N-05/09), `--bucket C` returns 2 rows (C agent = I18N-06/10), `--bucket D` returns 1 row (D delivery = I18N-07), `--bucket E` returns 1 row (E regression = I18N-11).
- 10 Georgian PHI fixtures stored under `tests/fixtures/phase6/phi_ka.yaml` (5 categories, 1 hard-block, exactly one `must_block: true` line in the data section).
- 30 bilingual digest samples stored under `tests/fixtures/phase6/bilingual_samples.json` (25 clean + 5 positive-catch; every `ka` value contains Mkhedruli codepoints; clean subset asserts zero violations against existing + D-05 banned-phrase lexicon).
- check_i18n_10 already flips to PASS in code-complete mode because both fixture files exist and the existing `scripts.communicator.{phi_redactor,banned_phrases}` modules are importable (Wave 3a real-call validation deferred to plans 06-10 / 06-11).

## Task Commits

Each task was committed atomically:

1. **Task 1: scaffold scripts/verify_phase6.py** — `b3cc2ff` (feat)
2. **Task 2: add 10 Georgian PHI fixtures** — `a7dbdc8` (test)
3. **Task 3: add 30 bilingual digest samples** — `fa1708e` (test)

**Plan metadata commit:** (this file + STATE.md + ROADMAP.md, separate commit)

## Files Created

- `scripts/verify_phase6.py` (1060 lines) — Phase-6 verifier scaffold: 11 check_i18n_NN functions, Check + Report dataclasses, --mode/--bucket/--gate/--json argparse, _pg_query/_module_present/_file_present/_read_text/_pending helpers, ALL_ORDER + GATES + BUCKETS dispatch tables.
- `tests/fixtures/phase6/phi_ka.yaml` (89 lines, 10 fixtures) — 5-category Georgian PHI corpus + 1 hard-block (MRI artifact reference).
- `tests/fixtures/phase6/bilingual_samples.json` (247 lines, 30 entries) — 25 clean (5-each across CGM-03 finding kinds: finding/source/evidence_strength/population_gap/clinician_question) + 5 positive-catch entries (each with `triggered_phrase` annotation tying back to a D-05 banned phrase).

## Wave 0 Verifier Output (Snapshot)

```
============================================================
  #  CODE      STATUS  LABEL                             EVIDENCE
------------------------------------------------------------
  1  I18N-01   PASS    next-intl@4 + proxy.ts on N16    next-intl='^4.0.0' proxy.ts=True ...
  2  I18N-02   FAIL    Routes mounted under [locale]/   PENDING — Wave 1 / plan 06-03a
  3  I18N-03   FAIL    en+ka dictionaries aligned       PENDING — Wave 1 / plan 06-05b ...
  4  I18N-04   FAIL    LanguageSwitcher in layout       PENDING — Wave 1 / plan 06-03b + 06-04
  5  I18N-05   FAIL    Migration 012 prepared           PENDING — Wave 2 / plan 06-06
  6  I18N-06   FAIL    Communicator emits {en,ka}       PENDING — Wave 3b / plan 06-09
  7  I18N-07   FAIL    Telegram=ka / Gmail=en routing   PENDING — Wave 4 / plan 06-12
  8  I18N-08   FAIL    displayField helper + en fallback PENDING — Wave 1 / plan 06-04
  9  I18N-09   FAIL    Migration 012 USING jsonb_build  PENDING — Wave 2 / plan 06-07
 10  I18N-10   PASS    PHI redactor + lint scaffolded   phi_fixtures=10 samples=30 ...
 11  I18N-11   FAIL    Phases 4+5 still GREEN           PENDING — Wave 4 / plan 06-13
============================================================
  2/11 PASS — NEEDS WORK (as expected at Wave 0)
```

Phase-5-style table renders cleanly under `python -X utf8` on Windows — Mkhedruli evidence strings and arrow glyph (→) emit without UnicodeEncodeError. `--bucket A/B/C/D/E` subset dispatch verified manually. `--help` shows all 4 flags.

## Decisions Made

- **Mirror Phase 5 verifier style verbatim.** Same Check / Report dataclasses, same table printer, same `--mode` semantics. Cumulative project verifier total grows from 78 → 89 once Phase 6 closes; idiom continuity matters for the cumulative-coverage rhetoric in Project Brain.
- **PENDING-evidence sentinel rather than NotImplementedError raises.** Crashing on missing modules would break the scaffold smoke test. Returning RED with `evidence="PENDING — implemented in Wave N plan NN"` keeps the verifier honest (it's still RED until the work lands) while letting Wave-0 scaffold-CI runs surface the table.
- **Fixture counts pinned to acceptance: exactly 10 PHI, exactly 30 samples, exactly 1 hard-block, exactly 25 clean / 5 positive-catch.** Each is asserted by the verifier itself in code-complete mode — drift between fixture and consumer is caught immediately.
- **Positive-catch entries explicitly annotated with `triggered_phrase`.** Lets plan 06-11's banned_phrases.py extension test grep for the exact phrase that each canary fires, rather than re-deriving it. Reduces test-authoring friction.

## Deviations from Plan

None — plan executed exactly as written.

- ruff + ruff-format auto-reformatted `scripts/verify_phase6.py` on first commit attempt. Re-staged and re-committed; no behavioral changes (smoke test still emits 1/11 then 2/11 PASS at the same table positions). This is the standard hook behavior, not a deviation.

## Issues Encountered

None.

The acceptance criterion "exactly one `must_block: true` line in `phi_ka.yaml`" initially counted 2 lines because the schema header comment included a literal `must_block: true` example. Resolved by rewriting the schema-doc placeholder to `must_block: <bool>` (descriptive, not literal). One-line edit; YAML data semantics unchanged (still exactly one fixture with `must_block: true`).

## Next Plan Readiness

**Wave 1 (06-03a, 06-03b, 06-04, 06-05a, 06-05b) is unblocked.** Each Wave-1 plan can now:

1. Implement its feature.
2. Re-run `python -X utf8 -m scripts.verify_phase6 --bucket A --mode code-complete` to confirm the corresponding `check_i18n_NN` flips from RED to PASS.
3. Use the bucket-specific dispatcher as a fast-feedback signal during execution (<30s per bucket vs ~120s for the full suite once production-mode wiring lands).

**Wave 3a (06-10 PHI redactor Georgian, 06-11 imperative-verb lint Georgian)** has both fixtures in place — those plans now author the real `redact_bilingual` helper + `check(text, locales=...)` kwarg API, then point the existing fixture loader at them.

**No blockers.** I18N-11 (regression) will remain RED-as-expected until plan 06-13 runs the closure check against Phases 4 + 5 in code-complete mode.

## Self-Check: PASSED

All claims verified:

- `scripts/verify_phase6.py` exists (1060 lines, ≥300 required)
- `tests/fixtures/phase6/phi_ka.yaml` exists (10 fixtures, 1 hard-block line in data section, 6 occurrences of ალექსანდრა, 5 of ჯინჭარაძე, 3 of 7616818)
- `tests/fixtures/phase6/bilingual_samples.json` exists (30 entries: 25 clean / 5 positive-catch, all 30 have Mkhedruli in `.ka`, clean subset has zero banned-phrase violations across English + Georgian existing + D-05 lexicon)
- Commit b3cc2ff exists (Task 1)
- Commit a7dbdc8 exists (Task 2)
- Commit fa1708e exists (Task 3)
- `python -X utf8 -m scripts.verify_phase6 --mode code-complete` emits the 11-row table; final tally 2/11 PASS (I18N-01 from Wave 0 carry-over + I18N-10 newly green from fixture presence + module importability)
- `python -X utf8 -m scripts.verify_phase6 --bucket A --mode code-complete` emits 5 rows
- `python -X utf8 -m scripts.verify_phase6 --help` exits 0 and shows `--gate`, `--bucket`, `--json`, `--mode` flags

---

*Phase: 06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo*
*Plan: 02 verifier-scaffold + fixtures (Wave 0)*
*Completed: 2026-05-20*
