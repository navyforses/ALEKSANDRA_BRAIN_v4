# Activity Diagnostic Plan

> Local-first checklist for auditing Claude Code activity in `ALEKSANDRA_BRAIN`.
> Current snapshot: 2026-05-15.

## Executive status

**YELLOW: Phase 1 and Phase 2 verifier claims are reproducible, and README now
reflects Phase 2 closure. Remaining risk is mostly historical/stale diagnostic
surface area, especially `scripts/test_all.py`.**

The strongest evidence is green: `verify_phase1` returns **10/10 PASS** and
`verify_phase2 --gate all` returns **19/19 PASS** when run through the project
virtualenv with UTF-8 output. The main risk is not core Phase 2 functionality;
it is keeping older smoke tests and historical docs from misleading future
Claude Code sessions.

## Evidence table

| Claim | Source | Verification command | Result | Verdict |
|---|---|---|---|---|
| README reflects current phase status | `README.md`, `CLAUDE.md`, phase reports | `Get-Content README.md`; `Get-Content CLAUDE.md` | README now says Phase 2 closed and Phase 2.5/3 entry active; CLAUDE says Phase 1 and Phase 2 closed on 2026-05-15 | **PASS** |
| Phase 1 exit gate is reproducible | `docs/PHASE_1_EXIT_REPORT.md`, `CLAUDE.md` | `.venv\Scripts\python.exe -m scripts.verify_phase1` | `RESULT: 10/10 PASS` | **PASS** |
| Phase 2 exit gate is reproducible | `docs/PHASE_2_EXIT_REPORT.md`, `docs/PHASE_2_LIVE_AUDIT.md` | `.venv\Scripts\python.exe -X utf8 -m scripts.verify_phase2 --gate all` | `19/19 PASS - ALL GREEN` | **PASS** |
| System `python` is enough to run verifiers | Test plan default commands | `python -m scripts.verify_phase1`; `python -m scripts.verify_phase2 --gate all` | Both fail before checks because system Python lacks `boto3` | **FAIL** |
| Project virtualenv is the correct diagnostic runtime | `.venv`, verifier runs | `.venv\Scripts\python.exe ...` | Verifiers run; UTF-8 flag needed for unicode table/checkmark output | **PASS** |
| CrewAI agent constructors initialize | `scripts/test_crew.py`, `agents/` | `.venv\Scripts\python.exe -X utf8 scripts/test_crew.py` | All 5 agents initialized | **PASS** |
| Legacy Phase 0 all-test script reflects current state | `scripts/test_all.py`, README Phase 0 TODOs | `.venv\Scripts\python.exe -X utf8 scripts/test_all.py` | `1/10 checks passed`; many checks are static TODO placeholders despite newer verifiers passing | **PARTIAL** |
| Recent Claude Code activity is committed | `git log --oneline -15` | `git log --oneline -15` | HEAD is `e94a2f2 feat(phase-2.5A): token_cost precision NUMERIC(14,8) + daily-budget gate`; prior commits record spend instrumentation and external live audit | **PASS** |
| Working tree cleanup has an explicit decision | Git status | `git status --short` | Diagnostic report and handoff are intended to be committed with README cleanup | **PARTIAL** |
| Phase 2 audit artifact is committed | `docs/PHASE_2_LIVE_AUDIT.md`, git log | `git log --oneline -15`; `git status --short` | `15524fe docs(phase-2): external live audit...`; file no longer appears untracked | **PASS** |
| Spend instrumentation gap has started closing | `scripts/cognition/llm.py`, `scripts/cognition/budget.py`, git log | `Get-Content scripts/cognition/llm.py`; `git log --oneline -15` | Wrapper and daily-budget gate are committed; still needs a low-cost or mocked row-level assertion | **PARTIAL** |
| Spend precision migration is integrated | `scripts/migrations/007_runs_token_cost_precision.sql` | `git ls-files scripts/migrations/007_runs_token_cost_precision.sql`; `git log --oneline -- scripts/migrations/007_runs_token_cost_precision.sql` | Migration is tracked and committed in `e94a2f2` | **PASS** |
| Qdrant local endpoint is reachable | Docker/Qdrant | `docker ps`; `Invoke-WebRequest http://127.0.0.1:6333/healthz` | Container health flag is `unhealthy`, but `/healthz` returns HTTP 200 OK | **PARTIAL** |
| Neo4j local Bolt endpoint is reachable | Docker/Neo4j | `docker ps`; `Test-NetConnection 127.0.0.1 -Port 7687` | Container healthy; Bolt TCP test succeeds | **PASS** |
| Viewer privacy guard exists | Pre-commit config and script | `rg --files`; `.pre-commit-config.yaml` inspection | `scripts/check-no-remote-fetch.sh` exists and is wired as local hook for `viewer/` | **PASS** |
| Append-only `runs` contract is documented and verifier-adjacent | `docs/PHASE_2_LIVE_AUDIT.md`, migration 001 | Phase audit review | Audit records PATCH/DELETE rejection evidence; current `verify_phase2` does not directly re-run that check | **PARTIAL** |
| Medical safety principle remains active | `README.md`, `CLAUDE.md` | Targeted doc inspection | README and CLAUDE both retain "doctor decides / system informs" principle | **PASS** |

## Claude Code notes

- Claude Code has produced a coherent Phase 2 implementation trail: chunking,
  Qdrant embedding, Graphiti extraction, retrieve facade, hypotheses,
  repurposing, CrewAI tool wiring, and Phase 2 reports.
- The current repo has advanced beyond the original plan snapshot: Phase 2 live
  audit is committed, spend instrumentation is committed, and token-cost
  precision/daily-budget gate work is now HEAD.
- Claude Code overclaims or leaves ambiguity where older diagnostics remain
  stale: `scripts/test_all.py` still reports Phase 0 TODO failures even though
  later phase verifiers pass.
- Claude Code operational constraints should stay explicit in future handoffs:
  manual push may be required, `.env` edits may be blocked, PowerShell/Windows
  needs UTF-8 for verifier output, and OneDrive can interfere with cache files.
- The diagnostic runtime should always be `.venv\Scripts\python.exe -X utf8`,
  not bare `python`, on this machine.

## Blocking issues

No confirmed implementation blocker prevents Phase 3 planning. Remaining cleanup
items before treating the diagnostic surface as polished:

- Keep `handoff.md` as a session handoff artifact if it is useful for Claude
  Code continuity.
- Decide whether to modernize or retire `scripts/test_all.py`; it is now the
  main stale signal.

## Non-blocking gaps for Phase 2.5

- `scripts/test_all.py` is stale relative to Phase 1/2 verifiers and should be
  retired, renamed as legacy Phase 0 smoke, or rewritten to delegate to current
  verifiers.
- Qdrant Docker healthcheck still reports unhealthy despite HTTP health success.
- `runs` append-only evidence is documented, but not re-exercised by the main
  Phase 2 verifier.
- Known Phase 2 audit gaps remain candidates for Phase 2.5: DSPy training data,
  explicit `supporting_papers` hydration, repurposing run logs, full 6-MCP
  dossiers, MEM-02/MEM-03/MEM-07/MEM-08 completion.
- Spend instrumentation now exists, but should be verified with a low-cost or
  mocked Anthropic call plus a `runs` row assertion before calling the gap fully
  closed.

## Next recommended Claude Code prompt

```text
Continue from docs/ACTIVITY_DIAGNOSTIC_PLAN.md. README now reflects Phase 1/2
closure and Phase 2.5/3 entry. Next, modernize or retire scripts/test_all.py so
the legacy Phase 0 smoke test no longer contradicts current verifiers. Run
.venv\Scripts\python.exe -X utf8 -m scripts.verify_phase1,
.venv\Scripts\python.exe -X utf8 -m scripts.verify_phase2 --gate all, and
.venv\Scripts\python.exe -X utf8 scripts/test_crew.py before committing.
Do not use bare python on Windows for these diagnostics.
```

## Command transcript summary

Commands run for this diagnostic snapshot:

```powershell
git status --short
git log --oneline -15
rg --files
Get-Content README.md -TotalCount 80
Get-Content CLAUDE.md -TotalCount 130
Get-Content scripts/migrations/007_runs_token_cost_precision.sql -TotalCount 160
python -m scripts.verify_phase1
python -m scripts.verify_phase2 --gate all
python scripts/test_crew.py
.venv\Scripts\python.exe -m scripts.verify_phase1
.venv\Scripts\python.exe -X utf8 -m scripts.verify_phase2 --gate all
.venv\Scripts\python.exe -X utf8 scripts/test_crew.py
.venv\Scripts\python.exe -X utf8 scripts/test_all.py
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
Invoke-WebRequest -Uri http://127.0.0.1:6333/healthz -UseBasicParsing
Test-NetConnection -ComputerName 127.0.0.1 -Port 7687
```

Acceptance classification:

- **PASS** means the claim was verified locally in this session.
- **PARTIAL** means the claim is broadly true but has stale docs, caveats, or
  incomplete automation.
- **FAIL** means the command or repo state contradicts the claim.
- **BLOCKED** means the environment prevented a fair check. No current row is
  marked BLOCKED.
- **DEFERRED** means the item is intentionally Phase 2.5 or later scope.
