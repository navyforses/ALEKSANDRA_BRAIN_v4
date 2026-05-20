---
phase: 6
slug: bilingual-system-i18n
status: revised
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-20
revised: 2026-05-20  # plan-checker revision iteration 1 — see <revision_context>
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Updated 2026-05-20 post plan-checker iteration 1: 06-03 split into 06-03a + 06-03b; 06-05 split into 06-05a + 06-05b; Wave 3 split into 3a (06-10, 06-11) and 3b (06-09); test runner pinned to `npx tsx`; 06-13 check_i18n_02 build-only fallback removed.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend Python) + npm scripts + `npx tsx --test` (viewer unit tests) |
| **Config file** | `pyproject.toml` (pytest), `viewer/package.json` (npm) |
| **Quick run command** | `python -m scripts.verify_phase6 --mode code-complete --bucket A` |
| **Full suite command** | `python -m scripts.verify_phase6 --mode code-complete` |
| **Estimated runtime** | ~120 seconds (incl. npm build + `next start` smoke + bilingual fixture suite) |

---

## Sampling Rate

- **After every task commit:** Run `python -m scripts.verify_phase6 --mode code-complete --bucket <task-bucket>`
- **After every plan wave:** Run full suite `python -m scripts.verify_phase6 --mode code-complete`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds per bucket, 120 seconds full

---

## Per-Task Verification Map (15 plans)

(Wave assignments below are the planner's finalized output post-revision. Buckets follow CONTEXT.md D-06.)

| Bucket | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|--------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| A — Frontend | 06-01-i18n-scaffold | 0 | I18N-01 | next-intl@4 builds on Next.js 16 | build | `cd viewer && npm run build` | ❌ W0 | ⬜ pending |
| (infra) | 06-02-verifier-scaffold | 0 | I18N-01..11 (skeleton) | 11 check_i18n_NN functions scaffolded + fixtures | scaffold | `python -m scripts.verify_phase6 --help` | ❌ W0 | ⬜ pending |
| A — Frontend | 06-03a-locale-folder-move | 1 | I18N-02 | 8 git mv operations under app/[locale]/; build still exits 0 | build + grep | `python -m scripts.verify_phase6 --bucket A.routes --mode code-complete` | ❌ W0 | ⬜ pending |
| A — Frontend | 06-03b-locale-layout-and-params | 1 | I18N-02 | Locale layout + async params on 9 page.tsx; setRequestLocale + hasLocale | grep + tsc | `python -m scripts.verify_phase6 --bucket A.routes --mode code-complete` | ❌ W0 | ⬜ pending |
| A — Frontend | 06-04-displayfield-helper | 1 | I18N-04, I18N-08 | `displayField(field, locale)` returns correct slot with en fallback; LanguageSwitcher uses typed nav | unit (tsx) | `cd viewer && npx tsx --test viewer/lib/__tests__/i18n.test.ts` | ❌ W0 | ⬜ pending |
| A — Frontend | 06-05a-messages-authoring | 1 | I18N-03 | viewer/messages/{en,ka}.json have identical key-set; ≥60 leaves | python key-set diff | `python -m scripts.verify_phase6 --bucket A.dict --mode code-complete` | ❌ W0 | ⬜ pending |
| A — Frontend | 06-05b-pages-t-wiring | 1 | I18N-03 | Every t(...) reference resolves in both dictionaries; TopNav typed Link | grep + jq | `python -m scripts.verify_phase6 --bucket A.dict --mode code-complete` | ❌ W0 | ⬜ pending |
| B — Database | 06-06-migration-012-prep | 2 | I18N-05 | Pre-migration `pg_dump` written to scripts/migrations/012_rollback/ | file existence | `test -d scripts/migrations/012_rollback && ls scripts/migrations/012_rollback/*.dump` | ❌ W0 | ⬜ pending |
| B — Database | 06-07-migration-012-apply | 2 | I18N-05, I18N-09 | 6 columns converted to JSONB; RLS preserved; legacy values mirrored to en+ka | psql smoke (BLOCKING — Shako) | `python -m scripts.verify_phase6 --bucket B --mode production` | ❌ W0 | ⬜ pending |
| B — Database | 06-08-jsonb-write-read-paths | 2 | I18N-05, I18N-08 | Manager apply writes JSONB; viewer pages render via displayField | grep + build | `python -m scripts.verify_phase6 --bucket A.dict --mode code-complete && cd viewer && npm run build` | ❌ W0 | ⬜ pending |
| C — Agent | 06-09-communicator-bilingual-emission | 3b | I18N-06 | weekly_brief composer emits `{en, ka}` per section; depends_on includes 06-10+06-11 | dry-run + json shape | `python -m scripts.verify_phase6 --bucket C.compose --mode code-complete` | ❌ W0 | ⬜ pending |
| C — Agent | 06-10-phi-redactor-georgian | 3a | I18N-10 | 10 Georgian PHI fixtures pass redactor with zero raw PHI tokens; redact_bilingual helper exposed | fixture + pytest | `python -m pytest tests/test_phi_redactor_georgian.py -v` | ❌ W0 | ⬜ pending |
| C — Agent | 06-11-imperative-verb-lint-georgian | 3a | I18N-10 | Imperative-verb count = 0 across 30 sample bilingual digests; locales kwarg in `check()`; Shako-review checkpoint | regex sweep + pytest + checkpoint | `python -m pytest tests/test_imperative_verb_lint_georgian.py -v` | ❌ W0 | ⬜ pending |
| D — Delivery | 06-12-n8n-routing-telegram-ka | 4 | I18N-07 | Telegram body contains Georgian codepoints; Gmail body contains zero | dry-run | `python -m scripts.verify_phase6 --bucket D --mode code-complete` | ❌ W0 | ⬜ pending |
| E — Regression | 06-13-phase-closure | 4 | I18N-11 | verify_phase4 9/9 + verify_phase5 13/13 still PASS; check_i18n_02 production uses `next start` + curl (NO build-only fallback) | spawn | `python -m scripts.verify_phase4 --mode code-complete && python -m scripts.verify_phase5 --mode code-complete && python -m scripts.verify_phase6` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave Topology (post-revision)

| Wave | Plans | Notes |
|------|-------|-------|
| 0 | 06-01, 06-02 | Foundation: next-intl install + verifier scaffold |
| 1 | 06-03a, 06-03b, 06-04, 06-05a, 06-05b | Frontend i18n routing + dictionaries + helper. 06-03a → 06-03b (dependency). 06-05a → 06-05b (dependency). 06-04 independent of 06-03/06-05. |
| 2 | 06-06 → 06-07 → 06-08 | Sequential within wave: migration prep → BLOCKING apply (Shako) → JSONB write/read wiring |
| 3a | 06-10, 06-11 | Expose `redact_bilingual` + `check(text, locales=...)` kwarg APIs |
| 3b | 06-09 | Consumes 06-10 + 06-11 APIs; depends_on: [06-07, 06-10, 06-11] |
| 4 | 06-12, 06-13 | Audience routing + closure |

---

## Wave 0 Requirements

- [ ] `viewer/messages/en.json` + `viewer/messages/ka.json` exist (move from repo root and expand keys) — landed by 06-01 (relocate) + 06-05a (expand)
- [ ] `viewer/lib/i18n.ts` with `displayField(field, locale)` helper + unit test under `npx tsx --test` — landed by 06-04
- [ ] `scripts/migrations/012_i18n_jsonb.sql` + `scripts/migrations/012_rollback/` (pre-migration pg_dump) — landed by 06-06
- [ ] `scripts/verify_phase6.py` skeleton with 5 capability buckets (A/B/C/D/E) — landed by 06-02
- [ ] `tests/test_bilingual_composer.py` — JSON-shape assertions for Communicator bilingual emission — landed by 06-09 (as `tests/test_compose_bilingual.py`)
- [ ] `tests/test_phi_redactor_georgian.py` — 10-entry Georgian PHI fixture — landed by 06-10
- [ ] `tests/test_imperative_verb_lint_georgian.py` — 30-sample bilingual digest fixture — landed by 06-11

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LanguageSwitcher UX feels correct on real-device | I18N-04 | Cannot automate browser feel | After deploy, open Vercel preview on mobile + desktop; toggle EN/GE on 3 family-facing routes; observe URL change + content swap |
| Georgian imperative-verb lexicon completeness | I18N-10 (D-05) | Native speaker review needed | Shako reviews the 8-entry lexicon in `scripts/communicator/banned_phrases.py` before the lint goes live; adds missing forms or confirms list (06-11 Task 3 BLOCKING checkpoint) |
| SUMMARY_TEMPLATES_KA Georgian phrasing | I18N-06 | Native speaker review needed | TODO marker in 06-09 Task 2 — Shako sanity-checks the 5 weekly-brief template Georgian translations before the 06-09 commit merges (per checker WARNING 7 — TODO marker, not blocking checkpoint) |
| Production Supabase migration 012 application | I18N-05 | Manual SQL execution against prod | Follow scripts/migrations/012_runbook.md; apply in maintenance window; verify post-migration SELECT and RLS via psql (06-07 BLOCKING checkpoint) |
| First bilingual Sunday brief reaches Telegram in Georgian | I18N-07 (operator activation) | Real workflow trigger required | After Phase 5 activation completes, watch the first Sunday 09:00 ET Weekly Brief Telegram message; assert Georgian script renders correctly |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (mapped in 15-row table above)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every plan has a bucket check)
- [x] Wave 0 covers all MISSING references (en.json, ka.json seed, displayField, verifier skeleton, fixtures)
- [x] No watch-mode flags
- [x] Feedback latency < 120s (full suite estimate)
- [x] check_i18n_02 production mode pinned to single pattern (`next start` + curl 14 URLs); no build-only fallback per checker WARNING 6
- [x] check_i18n_08 verifier command pinned to `npx tsx --test` per checker WARNING 4
- [x] Wave 3 dependency chain corrected per checker BLOCKER 2: 06-09 depends_on includes 06-10 + 06-11
- [ ] `nyquist_compliant: true` will be set in frontmatter once plan-phase finalizes plan IDs and Wave 0 tasks land

**Approval:** revised 2026-05-20 (plan-checker iteration 1 resolved: 2 BLOCKERs + 6 WARNINGs addressed; plan count 15)
