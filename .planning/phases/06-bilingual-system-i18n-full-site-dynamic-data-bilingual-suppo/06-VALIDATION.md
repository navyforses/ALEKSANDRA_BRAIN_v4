---
phase: 6
slug: bilingual-system-i18n
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-20
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend Python) + npm scripts (frontend) |
| **Config file** | `pyproject.toml` (pytest), `viewer/package.json` (npm) |
| **Quick run command** | `python -m scripts.verify_phase6 --mode code-complete --bucket A` |
| **Full suite command** | `python -m scripts.verify_phase6 --mode code-complete` |
| **Estimated runtime** | ~120 seconds (incl. npm build + 5 n8n dry-runs + bilingual fixture suite) |

---

## Sampling Rate

- **After every task commit:** Run `python -m scripts.verify_phase6 --mode code-complete --bucket <task-bucket>`
- **After every plan wave:** Run full suite `python -m scripts.verify_phase6 --mode code-complete`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds per bucket, 120 seconds full

---

## Per-Task Verification Map

(Wave assignments below are the planner's expected output; finalize during plan-phase. Buckets follow CONTEXT.md D-06.)

| Bucket | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|--------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| A — Frontend | 01-i18n-scaffold | 1 | I18N-01 | next-intl@4 builds on Next.js 16 | build | `cd viewer && npm run build` | ❌ W0 | ⬜ pending |
| A — Frontend | 02-locale-routes | 1 | I18N-02 | All 7 family routes reachable under `/en/*` and `/ka/*` | curl smoke | `python -m scripts.verify_phase6 --bucket A.routes` | ❌ W0 | ⬜ pending |
| A — Frontend | 03-messages-dictionaries | 1 | I18N-03 | Every `useTranslations` key exists in both en.json + ka.json | grep + json schema | `python -m scripts.verify_phase6 --bucket A.dict` | ❌ W0 | ⬜ pending |
| A — Frontend | 04-language-switcher | 1 | I18N-04 | LanguageSwitcher swaps URL prefix correctly | unit (playwright not in stack — use viewer build smoke) | `python -m scripts.verify_phase6 --bucket A.switcher` | ❌ W0 | ⬜ pending |
| A — Frontend | 05-displayfield-helper | 2 | I18N-08 | `displayField(field, locale)` returns correct slot with en fallback | unit (vitest or basic node) | `cd viewer && node --test viewer/lib/__tests__/i18n.test.ts` | ❌ W0 | ⬜ pending |
| B — Database | 06-migration-012-prep | 2 | I18N-05 | Pre-migration `pg_dump` written to scripts/migrations/012_rollback/ | file existence | `test -d scripts/migrations/012_rollback && ls scripts/migrations/012_rollback/*.dump` | ❌ W0 | ⬜ pending |
| B — Database | 07-migration-012-apply | 2 | I18N-05 | 6 columns converted to JSONB; RLS preserved; legacy values mirrored to en+ka | psql smoke | `python -m scripts.verify_phase6 --bucket B.schema` | ❌ W0 | ⬜ pending |
| B — Database | 08-historical-rows-mirrored | 2 | I18N-09 | Every existing row has identical `.en` and `.ka` content | psql diff | `python -m scripts.verify_phase6 --bucket B.history` | ❌ W0 | ⬜ pending |
| C — Agent | 09-communicator-bilingual-emission | 3 | I18N-06 | weekly_brief composer emits `{en, ka}` per section | dry-run + json shape | `python -m scripts.verify_phase6 --bucket C.compose` | ❌ W0 | ⬜ pending |
| C — Agent | 10-phi-redactor-georgian | 3 | I18N-10 | 10 Georgian PHI fixtures pass redactor with zero raw PHI tokens | fixture | `python -m scripts.verify_phase6 --bucket C.phi` | ❌ W0 | ⬜ pending |
| C — Agent | 11-imperative-verb-lint-georgian | 3 | I18N-10 | Imperative-verb count = 0 across 30 sample bilingual digests | regex sweep | `python -m scripts.verify_phase6 --bucket C.lint` | ❌ W0 | ⬜ pending |
| D — Delivery | 12-n8n-routing-telegram-ka | 4 | I18N-07 | Telegram body contains Georgian codepoints; Gmail body contains zero | dry-run | `python -m scripts.verify_phase6 --bucket D.routing` | ❌ W0 | ⬜ pending |
| E — Regression | 13-phase-4-5-no-regress | 4 | I18N-11 | verify_phase4 9/9 + verify_phase5 13/13 still PASS | spawn | `python -m scripts.verify_phase4 --mode code-complete && python -m scripts.verify_phase5 --mode code-complete` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `viewer/messages/en.json` + `viewer/messages/ka.json` exist (move from repo root and expand keys)
- [ ] `viewer/lib/i18n.ts` with `displayField(field, locale)` helper + unit test
- [ ] `scripts/migrations/012_i18n_jsonb.sql` + `scripts/migrations/012_rollback/` (pre-migration pg_dump)
- [ ] `scripts/verify_phase6.py` skeleton with 5 capability buckets (A/B/C/D/E)
- [ ] `tests/test_bilingual_composer.py` — JSON-shape assertions for Communicator bilingual emission
- [ ] `tests/test_phi_redactor_georgian.py` — 10-entry Georgian PHI fixture
- [ ] `tests/test_imperative_verb_lint_georgian.py` — 30-sample bilingual digest fixture

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LanguageSwitcher UX feels correct on real-device | I18N-04 | Cannot automate browser feel | After deploy, open Vercel preview on mobile + desktop; toggle EN/GE on 3 family-facing routes; observe URL change + content swap |
| Georgian imperative-verb lexicon completeness | I18N-10 (D-05) | Native speaker review needed | Shako reviews the 6-entry lexicon in `scripts/communicator/banned_phrases.py` before the lint goes live; adds missing forms or confirms list |
| Production Supabase migration 012 application | I18N-05 | Manual SQL execution against prod | Follow scripts/migrations/012_runbook.md (planner produces); apply in maintenance window; verify post-migration SELECT and RLS via psql |
| First bilingual Sunday brief reaches Telegram in Georgian | I18N-07 (operator activation) | Real workflow trigger required | After Phase 5 activation completes, watch the first Sunday 09:00 ET Weekly Brief Telegram message; assert Georgian script renders correctly |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (mapped in table above)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every plan has a bucket check)
- [x] Wave 0 covers all MISSING references (en.json, ka.json, displayField, verifier skeleton, fixtures)
- [x] No watch-mode flags
- [x] Feedback latency < 120s (full suite estimate)
- [ ] `nyquist_compliant: true` will be set in frontmatter once plan-phase finalizes plan IDs and Wave 0 tasks land

**Approval:** pending (plan-phase will finalize the task→plan ID mapping and flip nyquist_compliant to true)
