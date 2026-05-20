---
phase: 06-bilingual-system-i18n
plan: 05a
type: execute
wave: 1
depends_on:
  - 06-01
files_modified:
  - viewer/messages/en.json
  - viewer/messages/ka.json
requirements:
  - I18N-03
autonomous: true
must_haves:
  truths:
    - "viewer/messages/en.json contains a parallel namespace tree (Common, Navigation, Shared, Dashboard, Timeline, Papers, Therapies, Hypotheses, Today, Knowledge) with ≥60 leaf keys"
    - "viewer/messages/ka.json contains the SAME structural shape (recursive key-set equality with en.json) with Georgian Mkhedruli translations"
    - "Every ka.json leaf value is non-empty AND ≥95% of values contain at least one Mkhedruli codepoint (U+10A0..U+10FF) — remaining ~5% allowed for proper nouns like ALEKSANDRA_BRAIN"
    - "JSON files are UTF-8 (no BOM), valid JSON, 2-space indent"
    - "No new remote fetch/axios.post/XMLHttpRequest from viewer/ to non-self origins introduced by this plan (FND-02 trust boundary lint must continue to pass)"
  artifacts:
    - path: viewer/messages/en.json
      provides: "English dictionary covering Common, Navigation, Shared, Dashboard, Timeline, Papers, Therapies, Hypotheses, Today, Knowledge"
    - path: viewer/messages/ka.json
      provides: "Georgian dictionary with the SAME key tree as en.json — verified by recursive key-set equality"
  key_links:
    - from: viewer/messages/ka.json
      to: viewer/messages/en.json
      via: "recursive key-set equality contract (RESEARCH.md T-06-05 — missing keys render [object Object])"
      pattern: "ka\\.json"
---

<objective>
Pure dictionary authoring step (split from former 06-05): expand viewer/messages/en.json and viewer/messages/ka.json from their 2-namespace seed (Common, Navigation; 7 keys each) to full coverage of every visible string in the 7 family-facing routes — RESEARCH.md estimate 60–80 keys covering Dashboard, Timeline, Papers, Therapies, Hypotheses, Today, Knowledge, plus Navigation and Shared (loading/empty/error). The 9-page `t(...)` rewrite + TopNav update lands in 06-05b — by splitting authoring from rewriting, this plan delivers reviewable JSON diffs without the noise of 11 TSX file edits.

Critical Nyquist gate: the parallel key trees MUST be IDENTICAL (recursive key-set equality) — missing keys in ka.json render `[object Object]` per RESEARCH.md T-06-05.

Purpose: Begin I18N-03 — author the dictionaries that 06-05b's page rewrites will consume.
Output: 60–80 key dictionaries × 2 locales with structurally identical key trees.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-SPEC.md
@.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-CONTEXT.md
@.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-RESEARCH.md
@viewer/messages/en.json
@viewer/messages/ka.json
@viewer/app/[locale]/dashboard/page.tsx
@viewer/app/[locale]/timeline/page.tsx
@viewer/app/[locale]/papers/page.tsx
@viewer/app/[locale]/therapies/page.tsx
@viewer/app/[locale]/hypotheses/page.tsx
@viewer/app/[locale]/today/page.tsx
@viewer/app/[locale]/knowledge/page.tsx
@viewer/components/layout/TopNav.tsx
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Grep-extract every hardcoded English string from viewer/app/[locale]/** + TopNav, draft the expanded en.json key tree</name>
  <files>viewer/messages/en.json</files>
  <read_first>
    - viewer/app/[locale]/page.tsx
    - viewer/app/[locale]/dashboard/page.tsx
    - viewer/app/[locale]/timeline/page.tsx
    - viewer/app/[locale]/papers/page.tsx
    - viewer/app/[locale]/therapies/page.tsx
    - viewer/app/[locale]/hypotheses/page.tsx
    - viewer/app/[locale]/hypotheses/[id]/page.tsx
    - viewer/app/[locale]/today/page.tsx
    - viewer/app/[locale]/knowledge/page.tsx
    - viewer/components/layout/TopNav.tsx
    - viewer/messages/en.json (current seed — Common + Navigation, 7 keys)
    - .planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-RESEARCH.md (Pattern 3 — strategy: group by page; add Shared.empty/loading/error)
  </read_first>
  <action>
    (a) Grep all 9 [locale]/ page.tsx files + TopNav.tsx for hardcoded user-visible strings. A user-visible string is:
        - JSX text content: `<h1>Dashboard</h1>` → "Dashboard"
        - JSX attribute values that surface to the user: `placeholder="Search..."`, `title="..."`, `aria-label="..."`, `alt="..."`
        - Inline ternary/conditional strings: `{count > 0 ? "No papers" : "..."}`
        - NOT visible: API endpoints, table names, column names, CSS class names, route paths, enum literals used in switch statements.

    (b) Group extracted strings by namespace:
        - `Common.save`, `Common.cancel`, `Common.loading`, `Common.refresh`, `Common.search`
        - `Navigation.dashboard`, `Navigation.timeline`, `Navigation.papers`, `Navigation.therapies`, `Navigation.hypotheses`, `Navigation.today`, `Navigation.knowledge`, `Navigation.brain`, `Navigation.audit`
        - `Shared.empty`, `Shared.loading`, `Shared.error`, `Shared.errorRetry`, `Shared.count.zero`, `Shared.count.one`, `Shared.count.other`
        - `Dashboard.title`, `Dashboard.subtitle`, plus chart titles + section headers extracted from viewer/app/[locale]/dashboard/page.tsx and any DashboardCharts component string content
        - `Timeline.title`, `Timeline.subtitle`, `Timeline.empty`, `Timeline.column.date`, `Timeline.column.event`, `Timeline.column.institution`, plus row-action labels
        - `Papers.title`, `Papers.subtitle`, `Papers.empty`, `Papers.column.*`, `Papers.filter.*`
        - `Therapies.title`, `Therapies.subtitle`, `Therapies.empty`, `Therapies.status.*`, `Therapies.column.*`
        - `Hypotheses.title`, `Hypotheses.empty`, `Hypotheses.status.*` (`new`, `validating`, `confirmed`, `refuted`), `Hypotheses.detail.*`
        - `Today.title`, `Today.subtitle`, `Today.summary.*`
        - `Knowledge.title`, `Knowledge.subtitle`, `Knowledge.section.*`

    (c) Write viewer/messages/en.json with the full key tree. Preserve existing `Common.{save,cancel,loading}` and `Navigation.{dashboard,timeline,papers,therapies}` keys but ADD all the new keys. Target count: 60–80 keys total. JSON must be valid; use 2-space indentation; UTF-8 no BOM.
  </action>
  <acceptance_criteria>
    - `python -c "import json; d = json.load(open('viewer/messages/en.json', encoding='utf-8')); leaves = []; stack = [d]; \nwhile stack: x = stack.pop(); [stack.append(v) if isinstance(v, dict) else leaves.append(v) for v in x.values()]; print(len(leaves))"` prints a number ≥ 60.
    - viewer/messages/en.json contains namespaces: `Common`, `Navigation`, `Shared`, `Dashboard`, `Timeline`, `Papers`, `Therapies`, `Hypotheses`, `Today`, `Knowledge` (top-level keys).
    - `python -c "import json; json.load(open('viewer/messages/en.json', encoding='utf-8'))"` exits 0 (valid JSON).
    - File contains `"Shared":` with sub-keys `"empty"`, `"loading"`, `"error"`.
  </acceptance_criteria>
  <verify>
    <automated>python -c "import json; d = json.load(open('viewer/messages/en.json', encoding='utf-8')); ns = set(d.keys()); req = {'Common','Navigation','Shared','Dashboard','Timeline','Papers','Therapies','Hypotheses','Today','Knowledge'}; missing = req - ns; assert not missing, f'missing {missing}'; print('OK')"</automated>
  </verify>
  <done>en.json expanded with full key coverage across 10 namespaces; ≥60 leaf keys.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Mirror the en.json key tree into ka.json with Georgian translations</name>
  <files>viewer/messages/ka.json</files>
  <read_first>
    - viewer/messages/en.json (just expanded — Task 1 output is the source of truth for key structure)
    - viewer/messages/ka.json (current seed — Common + Navigation, 7 keys)
    - .planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-RESEARCH.md (T-06-05 — missing keys at runtime render `[object Object]`)
    - CLAUDE.md (language convention: docs and family-facing prose in Georgian; codez stays English)
  </read_first>
  <action>
    Build viewer/messages/ka.json with the SAME structural shape as en.json (same namespace names, same key paths) and Georgian translations for every leaf value. Preserve the existing `Common.{save,cancel,loading}` and `Navigation.{dashboard,timeline,papers,therapies}` Georgian translations from the current ka.json.

    Translation guidance:
    - Use Mkhedruli (no Latin transliteration except for established proper nouns like "ALEKSANDRA_BRAIN" — keep these as-is).
    - Polite formal register matching the family-facing tone established in Phase 4 (Sunday brief Telegram language).
    - Medical terminology: prefer Georgian-medical equivalents already in scripts/communicator/weekly_brief.py if present; otherwise transliterate (e.g., "HIE" stays "HIE" / "ჰიპოქსიურ-იშემიური ენცეფალოპათია").
    - Avoid imperative-verb forms banned by D-05 — translations describe state, not direct instructions to the family.

    The structural key-set of ka.json MUST recursively equal that of en.json. Use this Python check after writing:

        import json
        def flatten(d, prefix=''):
            for k, v in d.items():
                p = f'{prefix}.{k}' if prefix else k
                if isinstance(v, dict): yield from flatten(v, p)
                else: yield p
        en = set(flatten(json.load(open('viewer/messages/en.json', encoding='utf-8'))))
        ka = set(flatten(json.load(open('viewer/messages/ka.json', encoding='utf-8'))))
        assert en == ka, f'en-only: {en-ka}; ka-only: {ka-en}'

    Every ka.json value must be non-empty AND contain at least one Mkhedruli codepoint (U+10A0..U+10FF) — except for proper nouns where Latin is intentional (`ALEKSANDRA_BRAIN`).
  </action>
  <acceptance_criteria>
    - viewer/messages/ka.json is valid JSON.
    - Recursive key-set equality with en.json (see Python snippet above — must succeed).
    - Every leaf value is a non-empty string.
    - Across all leaf values, the count of values containing at least one Mkhedruli codepoint is ≥ 95% of the total leaves (allows ~5% for proper nouns/acronyms).
  </acceptance_criteria>
  <verify>
    <automated>python -c "import json; \ndef flatten(d, p=''):\n  for k,v in d.items():\n    pp = f'{p}.{k}' if p else k\n    if isinstance(v, dict): yield from flatten(v, pp)\n    else: yield pp\nen = set(flatten(json.load(open('viewer/messages/en.json', encoding='utf-8'))))\nka = set(flatten(json.load(open('viewer/messages/ka.json', encoding='utf-8'))))\nassert en == ka, f'en-only={en-ka} ka-only={ka-en}'\nprint('OK')"</automated>
  </verify>
  <done>ka.json mirrors en.json structure exactly; Georgian translations populated; verifier check_i18n_03 has a passable dictionary target (page-side wiring lands in 06-05b).</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Final key-set equality verification + commit-readiness check</name>
  <files>(no source files modified — verification only)</files>
  <read_first>
    - viewer/messages/en.json (Task 1 output)
    - viewer/messages/ka.json (Task 2 output)
  </read_first>
  <action>
    Run the key-set equality check from Task 2 one more time post-write and capture both leaf-count numbers:

        python -c "
        import json
        def flatten(d, p=''):
          for k, v in d.items():
            pp = f'{p}.{k}' if p else k
            if isinstance(v, dict): yield from flatten(v, pp)
            else: yield pp
        en = list(flatten(json.load(open('viewer/messages/en.json', encoding='utf-8'))))
        ka = list(flatten(json.load(open('viewer/messages/ka.json', encoding='utf-8'))))
        en_set, ka_set = set(en), set(ka)
        assert en_set == ka_set, f'DRIFT en-only={en_set-ka_set} ka-only={ka_set-en_set}'
        print(f'en leaves: {len(en)}; ka leaves: {len(ka)}; equal: True')
        "

    If drift exists, fix it in en.json or ka.json before proceeding — DO NOT commit dictionaries with structural drift. The verifier check_i18n_03 (06-13 finalization) does this check too; landing dictionary drift now creates downstream brittleness.

    Plan handoff to 06-05b: confirm both files are valid UTF-8 (no BOM); confirm 2-space indent is consistent; confirm the namespaces match the 10 listed in Task 1 acceptance.
  </action>
  <acceptance_criteria>
    - en.json and ka.json have identical recursive key-sets.
    - Leaf count ≥ 60 in both.
    - Both files parse as valid JSON.
    - Both files are UTF-8 without BOM.
  </acceptance_criteria>
  <verify>
    <automated>python -c "import json; flatten=lambda d,p='': (lambda f: f(f, d, p))(lambda f, d, p: [item for k, v in d.items() for item in (f(f, v, f'{p}.{k}' if p else k) if isinstance(v, dict) else [f'{p}.{k}' if p else k])]); en=set(flatten(json.load(open('viewer/messages/en.json', encoding='utf-8')))); ka=set(flatten(json.load(open('viewer/messages/ka.json', encoding='utf-8')))); assert en == ka, f'DRIFT: en-only={en-ka} ka-only={ka-en}'; assert len(en) >= 60, f'only {len(en)} leaves'; print(f'OK: {len(en)} keys equal')"</automated>
  </verify>
  <done>Dictionary authoring complete; 06-05b can consume both files knowing every key path resolves in both locales.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| viewer build → messages/{locale}.json | Static assets bundled at build time (V12 — no user-provided paths) |
| viewer/ → external origins | FND-02 trust boundary lint — this plan touches only static JSON; no fetch sites |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-06-05 | Information Disclosure (low) | viewer/messages/ka.json | mitigate | Task 2 + Task 3 recursive key-set equality check forces ka.json to mirror en.json's structure; downstream 06-05b verifier check_i18n_03 re-confirms every used `t('...')` key resolves in both dictionaries. Missing-key fixture in scripts/verify_phase6.py would flip RED at any future regression. |
| T-06-MISSING-LOCALE-FILE | Denial of Service | viewer/i18n/request.ts | mitigate | `(await import(\`../messages/${locale}.json\`)).default` — Next.js bundles both JSON files at build time; a missing file is a build error, not a runtime error. |
| T-06-FND-02 (carry-over) | Information Disclosure | viewer/ remote-origin fetches | mitigate | This plan touches only viewer/messages/*.json; no fetch call sites added; FND-02 lint regression continues to pass (covered by 06-13 sweep). |
</threat_model>

<verification>
- `python -c "import json; json.load(open('viewer/messages/en.json', encoding='utf-8')); json.load(open('viewer/messages/ka.json', encoding='utf-8'))"` exits 0
- Recursive key-set equality between en.json and ka.json (Task 3 final check)
- Leaf count ≥ 60 in both files
- ≥95% Mkhedruli coverage on ka.json values
</verification>

<success_criteria>
- 60–80 keys × 2 locales with identical structural shape
- All 10 namespaces present in both files
- Verifier check_i18n_03 (dictionary half) has a passable target; full page-side check_i18n_03 GREEN after 06-05b wires the `t(...)` calls
</success_criteria>

<output>
Create `.planning/phases/06-bilingual-system-i18n-full-site-dynamic-data-bilingual-suppo/06-05a-SUMMARY.md` when done. Record:
- Final leaf-key count in en.json (must equal ka.json count)
- Namespace breakdown (10 namespaces × per-namespace key count)
- Any Georgian translation decisions worth surfacing (e.g., HIE acronym handling, medical-term Mkhedruli-vs-Latin choices)
- Confirmation of UTF-8-no-BOM encoding on both files
</output>
