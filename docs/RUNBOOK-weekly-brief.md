# Runbook — Weekly Brief PDF (Phase 3 CGM-05)

**Last updated:** 2026-05-16
**Delivery target:** Sunday 09:00 local (ET while in Boston/Durham, configurable when family relocates).

## Why ReportLab (not weasyprint)

The triage plan originally selected `weasyprint`. The Day 6 smoke test
on the Windows family workstation failed with:

```
OSError: cannot load library 'libgobject-2.0-0'
```

weasyprint depends on the GTK runtime (libgobject, libcairo, libpango)
which is not available on this Windows machine and requires a multi-step
MSYS2 install to add. ReportLab is pure Python and installs cleanly via
`uv pip install reportlab`. The trade-off:

- weasyprint: HTML/CSS template, richer typography, requires GTK
- ReportLab: imperative Python (Platypus flowables), works everywhere

For a 1-page summary + citation appendix the difference is invisible to
the family. If the brief ever grows complex typography (multi-column,
custom fonts, embedded SVG) we can revisit weasyprint with a GTK install.

The triage plan risk register flagged this exact path; no scope expansion.

## Manual render

```powershell
# Render this week's brief from live Supabase data
.\.venv\Scripts\python.exe -X utf8 -m scripts.communicator.weekly_brief

# Render a specific week
.\.venv\Scripts\python.exe -X utf8 -m scripts.communicator.weekly_brief `
    --week-start 2026-05-24 `
    --output briefs/2026-05-24.pdf

# Fixture render (used by CGM-05 verifier; no DB pulls)
.\.venv\Scripts\python.exe -X utf8 -m scripts.communicator.weekly_brief `
    --dry-run --output briefs/dry_run.pdf
```

Default output: `briefs/<week-start-iso>.pdf` relative to repo root.

## What goes in the brief

Eight sections, each rendered even when empty (per CGM-05 — "No new
items this week" is required to stay visible):

1. **Cover** — week range, generated timestamp, redaction-mode note.
2. **This week, in short** — bulleted summary (auto-counts).
3. **New evidence** — top 3 papers from `papers` joined with `evidence_ledger`,
   ordered by `relevance_score` DESC.
4. **Hypothesis updates** — `hypotheses` rows where `reviewed_at >= week_start`.
5. **Repurposing watch** — `therapies` where `aleksandra_status IN
   ('evaluating', 'applied', 'planned')`.
6. **Outreach queue** — `outreach_log` rows in the week; contact identity
   shown as role only (no name).
7. **Open family questions** — `scripts/communicator/questions_queue.yaml`
   entries with `status: open`.
8. **Citation appendix** — every PMID/DOI/NCT referenced anywhere in
   sections 3-6.

The renderer applies a final `phi_redactor` safety net pass over the
joined section text. If the safety net trips, the PDF is deleted and
the renderer raises — caller must fix upstream evidence first.

## Family questions queue

The YAML at `scripts/communicator/questions_queue.yaml` holds the open
questions for Shako. Flip `status:` to `answered` or `deferred` when the
family decides; the next render will drop that question from the brief.

Adding a new question: append a YAML block at the end of the file
following the existing schema. No code change required.

## Delivery flow

1. `workflows/weekly_brief.json` fires every Sunday 13:00 UTC (= 09:00 ET).
2. The workflow logs a `runs` row with `kind='weekly_brief_trigger'` and
   pings Telegram so Shako knows a brief is incoming.
3. A separate worker process (or a manual run from Shako) calls
   `python -m scripts.communicator.weekly_brief --week-start <next-sunday>`,
   uploads the PDF to R2 at `briefs/<week>.pdf`, and sends Shako a follow-up
   Telegram message with the link.
4. For months 1-6 the email backup is a **draft only** — Shako forwards
   manually when satisfied with the content.

## Persistence into Supabase

The `briefs` table (migration 008) is the queryable mirror. The renderer
itself does NOT insert — the upload worker (Day 7 wiring task) is
responsible for:

```sql
INSERT INTO briefs (
  brief_week, pdf_r2_path, sections, phi_redacted,
  delivered_telegram_at
) VALUES (
  '2026-05-24',
  'briefs/2026-05-24.pdf',
  $1::jsonb,           -- BriefSections.to_dict() as JSON
  TRUE,                -- CHECK constraint enforces
  NOW()
);
```

The `phi_redacted = TRUE` value reflects the renderer's safety-net pass
plus all upstream PHI redactor calls. Inserting `FALSE` is structurally
impossible — the table's CHECK constraint refuses the row.

## Empty-state behaviour

If a section has no rows, the renderer writes "No new items this week."
The PDF still renders. The citation appendix renders the same line if
no citations were referenced.

The verifier's fixture run asserts at least 1 citation and at least
4 filled section rows so the renderer's empty-state path doesn't mask
a real failure.

## Failure modes

- `psycopg2.OperationalError` on Supabase → renderer raises; the workflow
  retries on the next Sunday or after a manual fix.
- `RuntimeError("weekly_brief safety-net redactor blocked: ...")` → the
  PDF is removed; upstream evidence needs the offending PHI scrubbed
  before re-rendering.
- ReportLab page-overflow on very long citation lists → the appendix
  spills to additional pages; no truncation.
