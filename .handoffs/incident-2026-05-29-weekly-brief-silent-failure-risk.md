# Incident note — Phase 4 weekly-brief silent-failure risk

**Date:** 2026-05-29
**Severity:** P1 (Phase 4 acceptance window v1 release gate at risk; closes ~2026-06-07)
**Author:** Claude (preflight check during v7.0 closure resume)
**Trigger:** carry-forward `verify_phase2_5 B.1 RED` flagged in `handoff.md` §0 — "n8n perception_tick worker on Railway (cron not firing 7d)"

---

## What we know (code-side, verified)

### Workflow JSON files are healthy

| Workflow | `active` | Cron | What it does |
|---|---|---|---|
| `workflows/weekly_brief.json` | `true` | `0 13 * * 0` (Sun 13:00 UTC = 09:00 ET) | Phase 3 CGM-05 + Phase 4 ACD-03 — renders PDF + R2 upload + Gmail draft |
| `workflows/manager_briefing.json` | `true` | `0 13 * * 0` (same trigger) | Phase 5 manager summary |
| `workflows/perception_6h.json` | `false` (by file design) | every 6h | Comment: "Inactive template. Activates after a Railway Python worker exposing `/perception-tick` is deployed. For the Phase 1 exit drill we trigger `scripts/perception_tick.py` manually from the dev venv." |
| `workflows/daily_digest.json` | `false` | — | inactive by design |
| `workflows/daily-budget-gate.json` | (separate) | per-trigger | Code-side JSON-body expression fix landed in v6.1; deployed workflow restart still pending |

### Code path verified

```bash
PYTHONUTF8=1 .venv/Scripts/python.exe -m scripts.communicator.weekly_brief --dry-run --bilingual-test
# week_start = 2026-05-24 (correct — most recent past Sunday from today 2026-05-29 UTC+)
# summary_lines, papers, hypotheses, citations all render with en+ka fields populated
# exit 0
```

Conclusion: the Python code path is healthy. Any failure of the actual Sunday brief is operational, not code.

---

## What we don't know (operator-only)

1. **Did `weekly_brief.json` actually fire on 2026-05-24 13:00 UTC?**
   The cron expression resolved correctly. The active flag is true. But n8n on Railway may have:
   - Been asleep / cold-started after the cron deadline
   - Errored and silently logged the failure
   - Returned non-zero exit and dropped the PDF / Gmail draft

2. **Has `perception_tick` actually fired any time since the v6.1 handoff (~2026-05-15)?**
   The B.1 verifier check says no — but B.1 reads from the `runs` table, and the runs table is only populated when the worker successfully starts. A worker that never starts produces zero rows by design — indistinguishable from "ran and failed before writing the row."

3. **Are the Gmail digest drafts staged for Shako to review?**
   Even if the worker ran and the PDF rendered, the digest goes through `stage_weekly_digest` which writes a draft to Shako's Gmail. If Shako hasn't seen a 2026-05-24-dated draft, the chain broke somewhere between cron-trigger and Gmail-draft-create.

---

## Why this matters for the Phase 4 acceptance window

Per `handoff.md` §0:
> Phase 4 14-day acceptance window in progress (opens at first real Weekly Brief Sunday 2026-05-24 09:00 ET, closes ~2026-06-07).

The window's **opening event** is the first real Weekly Brief delivered to wife on 2026-05-24. If that brief either (a) didn't render, (b) rendered nothing-new-this-week, or (c) didn't land in wife's hands, the acceptance window cannot legitimately close — there's nothing to accept.

Combined risk if both `weekly_brief` and `perception_tick` are down:
- No new papers ingested for 14+ days
- Sunday brief renders "0 new papers, 0 new hypotheses, 0 new therapy candidates"
- Wife reads two consecutive empty briefs → loss of confidence → "Never miss a credible treatment lead for Aleksandra" core value (CLAUDE.md) **compromised**

---

## Shako-only diagnostic — what to check on Railway

In Railway dashboard for the n8n service:

### Step 1 — Confirm n8n container is reachable
```
# In Railway → n8n service → "Logs" tab
# Look at the last 7 days for any successful startup log line.
# If the container restarted at all in the window, that's a flag.
```

### Step 2 — Check n8n executions list for the Sunday-13:00-UTC slot
```
# n8n UI → Executions
# Filter: workflow="Weekly Brief — Sunday 09:00 ET" + date 2026-05-24
# If 0 executions → cron didn't fire. Restart n8n.
# If 1 execution with status="success" → brief rendered. Find R2 upload + Gmail draft.
# If 1 execution with status="error" → click into it, surface the failing node.
```

### Step 3 — Verify weekly_brief PDF artifact in R2
```
# R2 bucket → look for `briefs/2026-05-24.pdf`
# If absent → render step failed; manual rescue:
#   .venv/Scripts/python.exe -m scripts.communicator.weekly_brief \
#     --week-start 2026-05-24 --output briefs/2026-05-24.pdf
# Then upload via scripts.ledger.upload_artifact
```

### Step 4 — Verify Gmail draft was staged
```
# jincharadzeshako@gmail.com → Drafts folder
# Search for "weekly brief 2026-05-24" or similar subject
# If absent and PDF exists → re-run scripts.communicator.gmail_digest.stage_weekly_digest --week-start 2026-05-24
```

### Step 5 — If cron didn't fire, restart and re-trigger
```
# Railway → n8n service → Restart
# After healthy: n8n UI → Workflows → Weekly Brief → "Execute Workflow" button (manual trigger for the missed slot)
# Same for Manager Briefing
```

### Step 6 — perception_tick (separate question)
The file comment says perception_6h is **inactive by design** until a Railway Python worker exposing `/perception-tick` is deployed. Two paths:

a. **Quick rescue:** manually run `python scripts/perception_tick.py` once. Confirms B.1 check flips to GREEN. Repeat weekly until path b lands.

b. **Permanent fix:** deploy the Phase-2.5-Step-B Python worker on Railway, flip `workflows/perception_6h.json` to `"active": true`, restart n8n. Cron fires every 6h.

---

## Recommended priority order

1. **TODAY** — Step 2 + 3 + 4: was the 2026-05-24 brief actually delivered? If no, manual rescue NOW so wife gets it before 2026-06-07 window closure.
2. **THIS WEEK** — Step 5: restart n8n, verify Sunday 2026-05-31 13:00 UTC fires cleanly.
3. **POST-PR** — Step 6a (quick) or 6b (proper). Quick is fine until v7 ships; proper is required before the Phase 7.4 active-question flow goes live (it depends on fresh ingestion).

---

## Why this isn't in handoff.md §0

The carry-forward listed in handoff.md §0 only said "n8n perception_tick worker restart pending" without separating:
- perception_6h (file-inactive by design)
- weekly_brief (file-active, but n8n-side-state unknown)
- manager_briefing (same as weekly_brief)
- daily-budget-gate (separate JSON-body bug, separate restart-pending)

This note unpacks those four into the actual diagnostic + rescue paths so Shako doesn't conflate them under a single "restart n8n" task.

---

## Status after this note

- `handoff.md` updated with cross-reference to this incident
- Code path verified clean — no PR-blocker
- Operator action required before Phase 4 acceptance window closes ~2026-06-07
