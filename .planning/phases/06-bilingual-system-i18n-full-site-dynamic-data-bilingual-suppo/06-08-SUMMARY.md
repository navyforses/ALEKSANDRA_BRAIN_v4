---
phase: 06-bilingual-system-i18n
plan: 08
subsystem: bilingual-i18n

tags: [i18n, jsonb, displayField, toBilingual, manager-apply, wave-2-read-side, next-intl-4]

requires:
  - phase: 06
    plan: 04
    provides: displayField helper + BilingualField type in viewer/lib/i18n.ts
  - phase: 06
    plan: 03b
    provides: async params + setRequestLocale(locale) on every [locale]/ page
  - phase: 06
    plan: 07
    provides: production Supabase migration 012 applied (Shako, 2026-05-20) — 6 columns now JSONB

provides:
  - viewer/lib/i18n.ts:toBilingual — write-side {en, ka} shape helper for any future TypeScript caller
  - 4 viewer pages reading the 6 migration-012-converted JSONB columns via displayField(field, locale)
  - Task 1 audit confirming viewer/ has zero INSERT/UPDATE call sites against the 4 target tables (Python writers correctly deferred to 06-09)

affects:
  - I18N-05 (migration 012 consumer surface — read path)
  - I18N-08 (displayField wiring across all 4 plan-target pages)
  - 06-09 Wave-3b — the Python write paths in scripts/manager/routing/apply_action.py + scripts/communicator/weekly_brief.py + agents/communicator.py are the planned next step

tech-stack:
  added: []
  patterns:
    - "BilingualField row-type widening: title/description/name/evidence_summary go from `string` / `string | null` to BilingualField on row interfaces"
    - "displayField(field, locale) at every render point for the 6 converted columns; columns NOT in 012 (event_type, institution, location, status, therapy_type, evidence_in_hie, aleksandra_status, ai_assessment, mechanism_of_action, etc.) stay as direct row reads"
    - "Hidden form input audit-trail invariance: server-action FormData inputs pass displayField(field, 'en') so the audit label stays locale-invariant even when the user submits from /ka/"
    - "Truthiness gate over BilingualField requires displayField → string first, because `{en: '', ka: ''}` is always truthy as an object"
    - "Shape-contract helper colocation: toBilingual sits next to displayField in viewer/lib/i18n.ts — write-side and read-side helpers live together, not in a proxy route"

key-files:
  created: []
  modified:
    - viewer/lib/i18n.ts (+21 lines — toBilingual helper)
    - viewer/app/[locale]/timeline/page.tsx (2 displayField sites; row type widened)
    - viewer/app/[locale]/therapies/page.tsx (2 displayField sites + truthiness-gate refactor)
    - viewer/app/[locale]/hypotheses/page.tsx (3 displayField sites; row type widened; hidden form input uses English canonical)
    - viewer/app/[locale]/hypotheses/[id]/page.tsx (4 displayField sites incl. related therapy.name; row types widened)

key-decisions:
  - "viewer/app/api/manager/apply/route.ts NOT modified — pure HTTP proxy to Python worker; never shapes payloads server-side. The plan's literal Task 2 acceptance criterion (grep '{en:' in route.ts) cannot be satisfied without inventing dead code."
  - "toBilingual write-side helper added to viewer/lib/i18n.ts — colocated with displayField; the shape contract architecturally belongs in the i18n library, not in a proxy route. Future TypeScript callers get the helper for free."
  - "Hidden form inputs for reviewHypothesis (`<input name=\"title\">`) use displayField(hypothesis.title, 'en') — server-action audit trail stays locale-invariant. The action writes to `outcome` (TEXT, not JSONB), so no downstream shape transformation is needed."
  - "RelatedTherapy.name widened to BilingualField even though it's a denormalized read on the hypothesis detail page — the underlying table column is JSONB, so the row interface must reflect that or TypeScript surfaces a mismatch."
  - "All 9 displayField sites use the locale obtained from `const {locale} = await params;` — already added by 06-03b; no new locale propagation needed."

patterns-established:
  - "Audit-first execution for shape-migration plans: Task 1's grep audit IS the deliverable when downstream Python write paths are scheduled in a later plan (06-09 Wave 3)."
  - "Read-side wiring per-column rule: only the 6 columns named in migration 012 become BilingualField on row interfaces — neighbouring TEXT columns (institution, location, status, therapy_type, evidence_in_hie, aleksandra_status, mechanism_of_action, ai_assessment, etc.) stay typed as `string | null` and rendered directly."

requirements-completed: [I18N-05, I18N-08]

duration: 28min
completed: 2026-05-21
---

# Phase 06 Plan 06-08: Wave-2 read-side displayField wiring + toBilingual write-side helper Summary

**9 displayField call sites wired across 4 family-facing `[locale]/` pages so the 6 migration-012-converted JSONB columns render locale-correctly; toBilingual shape helper added to viewer/lib/i18n.ts; Task 1 audit confirmed viewer/ has zero TypeScript INSERT sites against the 4 target tables (Python writers correctly scheduled in 06-09).**

## Performance

- **Duration:** ~28 min (audit + helper + 4 page edits + build + verifier)
- **Started:** 2026-05-21T04:35:00Z
- **Completed:** 2026-05-21T05:03:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Read-side wiring complete: timeline, therapies, hypotheses (list + detail) render JSONB columns via `displayField(field, locale)` from `@/lib/i18n`. A row written by 06-09's future Communicator pipeline with `{en: 'X', ka: 'X-ka'}` will render `X` on `/en/timeline` and `X-ka` on `/ka/timeline` automatically.
- Mixed-locale rendering proven by `displayField` contract: a row with only `{en: 'X'}` (no `ka` key) renders `X` on `/ka/*` via English fallback (06-04 unit-test case 4 covers this).
- Row TypeScript types reflect the JSONB shape: `title`, `description`, `name`, `evidence_summary` are `BilingualField` (= `string | {en?, ka?} | null | undefined`) on the 4 plan-target page row interfaces. This tolerates legacy TEXT rows, `{en, ka}` objects, and `null` in one type — no migration-day-zero crash window.
- Write-side shape contract made explicit in TypeScript: `toBilingual()` helper added to `viewer/lib/i18n.ts` colocated with `displayField`. Mirrors single-language manager input into the `{en, ka}` JSONB shape that migration 012 expects. Available to any future TypeScript caller.
- Task 1 audit codified the disposition: viewer/ has **zero** INSERT/UPDATE call sites against `aleksandra_timeline`, `hypotheses`, `therapies`, or `briefs`. All actual writes live in Python (`scripts/manager/routing/apply_action.py` lines 58 + 102; `scripts/communicator/weekly_brief.py`), which the plan's own Task 1 classification table DEFERS to 06-09 (Wave 3 — Bilingual emission via `compose_bilingual`).
- Build green, verifier no-regression: `cd viewer && npm run build` exits 0 (21 static pages, 8 `/[locale]/*` dynamic routes preserved). `python -X utf8 -m scripts.verify_phase6 --mode code-complete` reports **8/11 PASS** — identical to the 06-05b baseline. I18N-08 stays GREEN.

## Task Commits

Each task was committed atomically:

1. **Task 1+2 (folded): Audit INSERT call sites + add toBilingual helper** — `a018fd4` (feat)
   - Audit confirmed viewer/ has no TypeScript INSERT sites against the 4 target tables. `viewer/app/api/manager/apply/route.ts` is a pure HTTP proxy.
   - `viewer/lib/i18n.ts` extended with `toBilingual()` helper (+21 lines): mirrors string → `{en, ka}`, normalizes partial objects, returns null for null input. Documented as the canonical TypeScript-side shape contract for any future caller.

2. **Task 3: Wire displayField on 4 viewer pages for JSONB read path** — `26c79c6` (feat)
   - 4 files changed, 42 insertions, 22 deletions.
   - 9 displayField sites: timeline (2), therapies (2), hypotheses list (3), hypotheses detail (4).
   - All 4 page row types widened to `BilingualField` for the 6 converted columns; neighbouring TEXT columns left untouched.
   - Therapies' truthiness gate over `evidence_summary` refactored to resolve to a string first (BilingualField objects are always truthy as objects, even when both en+ka are empty strings).
   - Hidden form inputs (`<input name="title">`) for the `reviewHypothesis` server action use `displayField(_, 'en')` — locale-invariant audit trail.

**Plan metadata commit:** _(this commit — `docs(06-08): complete Wave-2 read-side wiring + write-side shape helper`)_

## Files Created/Modified

- `viewer/lib/i18n.ts` — Added `toBilingual()` write-side shape helper (+21 lines). Sits next to `displayField` so the i18n module owns both read-side and write-side primitives.
- `viewer/app/[locale]/timeline/page.tsx` — `TimelineEvent.title` + `TimelineEvent.description` widened to `BilingualField`; 2 displayField render sites.
- `viewer/app/[locale]/therapies/page.tsx` — `Therapy.name` + `Therapy.evidence_summary` widened to `BilingualField`; 2 displayField render sites; truthiness gate over `evidence_summary` refactored.
- `viewer/app/[locale]/hypotheses/page.tsx` — `Hypothesis.title` + `Hypothesis.description` widened; 3 displayField sites (h2 link, description p, hidden form input using English canonical).
- `viewer/app/[locale]/hypotheses/[id]/page.tsx` — `HypothesisDetail.title` + `HypothesisDetail.description` + `RelatedTherapy.name` widened; 4 displayField sites (h1, description p, hidden form input English canonical, related therapy name).

## Audit Results (Task 1 — call-site enumeration with disposition)

Grep ran across `viewer/`, `scripts/`, `agents/` for `INSERT INTO (aleksandra_timeline|hypotheses|therapies|briefs)` and `.from('<table>').insert/update`. Classification:

| Call site | Disposition | Reason |
| --- | --- | --- |
| `viewer/app/api/manager/apply/route.ts` | **NO-OP (proxy)** + `toBilingual()` added to `viewer/lib/i18n.ts` | Pure HTTP proxy that forwards approved ActionCards to the Python worker's `/apply-actions` endpoint. Body shape passes through unchanged via `JSON.stringify({ cards })`. No TypeScript-side shape transformation; nowhere to wrap with `{en, ka}`. |
| `scripts/manager/routing/apply_action.py` — `_write_aleksandra_timeline` (INSERT, line 58) | **DEFER to 06-09** | Wave 3 — Bilingual emission via `compose_bilingual()` (Anthropic strict tool_use). Plan 06-09 explicitly owns this write path. |
| `scripts/manager/routing/apply_action.py` — `_write_therapies` (INSERT, line 102) | **DEFER to 06-09** | Same. |
| `scripts/manager/routing/apply_action.py` — UPDATE branches (timeline + therapies) | **DEFER to 06-09** | Same. |
| `scripts/communicator/weekly_brief.py` — briefs INSERT | **DEFER to 06-09** | Wave 3 — `briefs.sections.*` body fields wrapped via Pattern 6 Option A (deterministic-prose mirror) per 06-09 plan. |
| `scripts/communicator/outreach_drafter.py` | **NO CHANGE (out of scope by D-02)** | Single-recipient single-language stays per CONTEXT.md D-02 Per-tier policy. |
| `agents/communicator.py` (CrewAI wrapper) | **DEFER to 06-09** | Hypothesis/therapy/timeline row writes via compose_bilingual. |
| `scripts/migrations/012_i18n_jsonb.sql` | **NO CHANGE** | Migration is static; already correct. |
| `scripts/migrations/012_rollback/*.pre012.dump` | **NO CHANGE** | Rollback artifacts, not active code paths. |
| `docs/RUNBOOK-weekly-brief.md` (line 98 — example INSERT) | **NO CHANGE** | Documentation example, not executed code. |

**Surface count:** 6+ active Python write call sites enumerated; 0 active TypeScript write call sites. All Python sites are correctly scheduled in 06-09 per the planner's own Task 1 classification table.

## Decisions Made

- **Task 2 scope correction (Rule 3 deviation, see below):** The plan's literal Task 2 acceptance criterion (`grep -c "{en:" viewer/app/api/manager/apply/route.ts ≥ 2`) presumed a `.from('aleksandra_timeline').insert({...})` call site that does not exist in the proxy route. Rather than fabricate dead code, the shape contract was made explicit in `viewer/lib/i18n.ts` via `toBilingual()`, colocated with `displayField`. Pitfall 3 defense is satisfied; the architectural decision is documented in code and commit.
- **Hidden form inputs use English canonical:** `<input name="title">` for `reviewHypothesis` server action passes `displayField(hypothesis.title, 'en')` instead of the locale-current value. Rationale: the action writes to `outcome` (TEXT, not JSONB) and constructs an audit string; making that label locale-dependent would produce ka-locale audit rows that read confusingly in the English-default operator console.
- **Truthiness gate refactor on therapies:** `therapy.evidence_summary || assessment || therapy.aleksandra_notes` previously worked because `evidence_summary` was `string | null`. Post-typing it's `BilingualField`, and `{en: '', ka: ''}` is truthy as an object. Resolved by computing `const evidence = displayField(therapy.evidence_summary, locale)` first so the gate operates on a string.
- **`RelatedTherapy.name` widened to BilingualField on detail page:** Even though it's a denormalized read, the underlying `therapies.name` column is JSONB; the row interface must reflect that or TypeScript surfaces a mismatch when JSONB data lands.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Scope correction / architectural premise wrong] Task 2 target file is a proxy, not a writer**

- **Found during:** Task 1 (audit phase)
- **Issue:** The plan's literal Task 2 ("Update viewer/app/api/manager/apply/route.ts to write JSONB shape for the 6 converted columns") presumed the route owns INSERT/UPDATE SQL. Reading the actual file revealed it's a pure HTTP proxy (server-side fetch to the Python worker's `/apply-actions` endpoint, runtime='nodejs', body forwarded unchanged via `JSON.stringify({ cards })`). There is no `.from('aleksandra_timeline').insert(...)` in the viewer/ TypeScript codebase at all. Confirmed by `grep -rEn ".from\((aleksandra_timeline|hypotheses|therapies|briefs)).(insert|update)" viewer/` → 0 matches.
- **Fix:** Three alternatives considered:
  - **A.** Fabricate dead `.from('table').insert({title: {en:x, ka:x}, ...})` code in route.ts purely to satisfy the grep acceptance criterion. Rejected — dead code, false-positive marker, architectural drift.
  - **B.** Add `toBilingual()` shape helper to `viewer/lib/i18n.ts` where the shape contract architecturally belongs (companion to `displayField`). Future TS callers get the helper for free; Pitfall 3 defense from the viewer side is satisfied. **Chosen.**
  - **C.** Mark Task 2 BLOCKED and emit a checkpoint. Rejected — the plan's own Task 1 classification table explicitly says "DEFER to 06-09 — Bilingual emission is Wave 3's job" for the Python write paths. The planner already anticipated the disposition; the literal Task 2 wording was vestigial.
- **Files modified:** `viewer/lib/i18n.ts` (+21 lines, `toBilingual()` exported with doc-comment explaining the rationale and pointing forward to 06-09).
- **Verification:** `cd viewer && npx tsc --noEmit` exits 0; `cd viewer && npm run build` exits 0; helper is type-safe and documented.
- **Committed in:** `a018fd4` (Task 1+2 folded commit)

**2. [Rule 1 - Bug, anticipatory] Therapies truthiness gate became always-truthy post-widening**

- **Found during:** Task 3 (therapies page edit)
- **Issue:** Pre-existing code `const hasAny = therapy.evidence_summary || assessment || therapy.aleksandra_notes;` worked when `evidence_summary` was `string | null` (empty string falsy). After widening to `BilingualField`, the value is typically `{en, ka}` — an object — which is unconditionally truthy. The gate would always pass and render an empty `<p></p>` even for rows with no evidence_summary content.
- **Fix:** Resolve `evidence_summary` to a string via `displayField(therapy.evidence_summary, locale)` BEFORE the truthiness check, then gate on the string. Single computed `evidence` variable used both in the gate and in the render.
- **Files modified:** `viewer/app/[locale]/therapies/page.tsx`
- **Verification:** `npm run build` exits 0; the IIFE returns `null` when all three fields are empty, exactly as it did pre-widening.
- **Committed in:** `26c79c6` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule-3 scope correction, 1 Rule-1 anticipatory bug fix tied to the row-type widening).

**Impact on plan:** Both deviations preserve the plan's spirit. Deviation 1 routes the Pitfall 3 mitigation surface to where the shape contract architecturally belongs (`viewer/lib/i18n.ts`) instead of inventing dead code in a proxy. Deviation 2 is a correctness fix forced by the row-type widening that Task 3 itself introduces. No scope creep.

## Issues Encountered

- None during planned work. The Task 2 scope correction surfaced during Task 1 audit and was handled via Rule 3 deviation rather than a checkpoint, because the planner's own Task 1 classification table already encoded the disposition.

## Self-Check

- [x] `a018fd4` commit exists (`git log --oneline -5` confirms): `a018fd4 feat(06-08): add toBilingual write-side shape helper in viewer/lib/i18n.ts`
- [x] `26c79c6` commit exists: `26c79c6 feat(06-08): wire displayField on 4 viewer pages for JSONB read path`
- [x] `viewer/lib/i18n.ts` contains `toBilingual` symbol
- [x] All 4 page files contain `displayField(` call (grep confirms 9 total sites across the 4 files)
- [x] All 4 page files import `displayField, type BilingualField` from `@/lib/i18n`
- [x] `cd viewer && npm run build` exits 0 (21 static pages, 8 `/[locale]/*` dynamic routes preserved)
- [x] `python -X utf8 -m scripts.verify_phase6 --mode code-complete` → 8/11 PASS (identical to 06-05b baseline; I18N-08 stays GREEN; the 3 PENDING items — I18N-06, I18N-07, I18N-11 — are Wave 3b/4 by design)
- [x] No new untracked generated files

**Self-Check: PASSED**

## Known Stubs

None. The Rule-3 scope correction (Task 2 → no-op for proxy route, helper added to lib/i18n.ts instead) is a documented architectural decision, not a stub. The actual write paths for the 6 JSONB columns are scheduled in 06-09 (Wave 3b) per the planner's explicit classification.

## Threat Flags

None new. The plan's STRIDE register stays intact:

- **T-06-INSERT-SHAPE-MISMATCH** — Disposition stands as `mitigate`. The mitigation surface moved from `viewer/app/api/manager/apply/route.ts` (which can't shape because it's a proxy) to `scripts/manager/routing/apply_action.py` + `scripts/communicator/weekly_brief.py` + `agents/communicator.py` (06-09). Until 06-09 lands, the manager apply path would error with `invalid input syntax for type json` if a manager-initiated batch reached the Python worker AND that worker still passed the raw string through. This is an **inherited Wave-3 dependency**, not a new risk introduced by this plan.
- **T-06-05** (display layer) — `mitigate` via `displayField` (06-04); now exercised at 9 call sites across 4 pages.
- **T-06-FND-02** — No new fetch/axios.post/XMLHttpRequest call sites introduced. FND-02 lint passed in the pre-commit hooks (visible in the commit transcript: "no remote fetch in viewer/ (FND-02) Passed").

## Next Phase Readiness

- Wave 2 is now fully closed at the consumer surface: migration 012 applied (06-07) and consumed (06-08).
- Wave 3a (06-10 + 06-11) is next per the dependency graph: `redact_bilingual` exposure in `scripts/communicator/phi_redactor.py` (06-10) and the per-locale `check(text, locales=...)` kwarg in `scripts/communicator/banned_phrases.py` (06-11). Both must land before 06-09 (Wave 3b) can wire the Python write paths.
- After 06-09 lands, the verifier should flip I18N-06 from PENDING-FAIL to GREEN (compose_bilingual integration in the Communicator write paths).
- Production-mode validation (Shako-run `verify_phase6 --mode production --bucket B` against live Supabase) remains queued under the existing `.planning/todos/pending/2026-05-21-capture-migration-012-rollback-artifacts.md` maintenance todo — not blocked by or blocking 06-08.

---
*Phase: 06-bilingual-system-i18n*
*Completed: 2026-05-21*
