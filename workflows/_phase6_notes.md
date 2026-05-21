# Phase 6 I18N-07 — n8n zero-touch decision

## Conclusion

**No n8n workflow JSON file was modified by Phase 6.** Audience routing
(Telegram = `.ka`, Gmail = `.en`) lives entirely in the Python worker layer
(`scripts/communicator/*.py`, `scripts/manager/briefing.py`) — not in n8n
expression syntax.

This document is the audit trail that explains _why_ a Phase-6 git diff over
`workflows/` shows only this notes file. See `06-RESEARCH.md` Pattern 7 for
the 5-workflow survey that drove the decision, and `06-CONTEXT.md` §D-02 for
the per-audience locale policy.

## Per-workflow audit table

The 5 workflows that emit family-facing or operator-facing content were
audited; the body-composition source for each is the Python worker that n8n
invokes, not the n8n workflow itself:

| Workflow                       | Telegram-body source                              | Gmail-body source             | Phase 6 change |
| ------------------------------ | ------------------------------------------------- | ----------------------------- | -------------- |
| `telegram_daily_digest.json`   | Python worker `fire_daily_batch()`                | n/a                           | None — body in worker (`scripts/communicator/telegram_sender.py`); migration-012 reads route through `display_field_py(field, 'ka')` |
| `daily_digest.json`            | n8n `Compose digest` JS node reads `p.title`      | n/a                           | None — workflow stays `active: false` (per Phase 2.5 note in the file); if reactivated, update the JS expression — see backlog item below |
| `weekly_brief.json`            | Python worker `/render-weekly-brief`              | Same worker                   | None — `scripts/communicator/weekly_brief.py` reads `briefs.sections` per locale via `display_field_py` and `_bilingual_mirror` already wired in 06-09 |
| `manager_briefing.json`        | Python worker `/morning-briefing`                 | n/a                           | None — `scripts/manager/briefing.py` reads `aleksandra_timeline.title` + `therapies.name` JSONB via `display_field_py(field, 'ka')` (06-12 Task 4) |
| `outreach_review_queue.json`   | n8n `Compose digest` JS reads `outreach_log.subject` | n/a                       | None — `outreach_log.subject` stays TEXT per Plan 06-12 SPEC out-of-scope |

The single n8n surface that still touches a body-string column directly is
`outreach_review_queue.json` against `outreach_log.subject`. That column is
intentionally untouched by migration 012: outreach drafts are clinician-language
content authored once and shipped once — they do not need to be a bilingual
JSONB pair, and the queue review UI is operator-internal (English).

## Backlog item (filed 2026-05-21 at Plan 06-12 close)

If `workflows/daily_digest.json` is ever activated (currently
`"active": false` per its `_phase_2_5_note`), update its `Compose digest` JS
code node to extract the Telegram audience locale explicitly. The JS
equivalent of `display_field_py(field, 'ka')` is:

```js
// inside the n8n `Compose digest` Function/Code node
function displayField(field, locale) {
  if (field == null) return "";
  if (typeof field === "string") return field;
  if (typeof field === "object") return field[locale] || field.en || "";
  return String(field);
}
const titleKa = displayField(p.title, "ka");
```

No work was performed in this plan against `daily_digest.json`; the workflow
is dormant, and reactivation is out of scope for Phase 6.

## Reference

- `06-RESEARCH.md` Pattern 7 — 5-workflow survey + zero-touch finding.
- `06-RESEARCH.md` Open Question #1 — locale-policy ownership stays in the
  Python worker (not n8n) because workflow JSONs are not the canonical
  formatting layer for any audience.
- `06-CONTEXT.md` §D-02 — Telegram = `.ka`, Gmail = `.en` per audience policy.
- `scripts/communicator/_bilingual_read.py` — Python-side `display_field_py`
  helper that the worker layer routes every JSONB read through, symmetric
  with `viewer/lib/i18n.ts::displayField`.
