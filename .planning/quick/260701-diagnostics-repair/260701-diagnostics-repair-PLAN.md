---
phase: quick-260701-diagnostics-repair
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/backup_neo4j.py
  - scripts/refactor/pilot_classify.py
  - scripts/verify_phase2.py
  - scripts/verify_phase2_5.py
  - scripts/verify_phase4.py
  - scripts/verify_phase5.py
  - scripts/verify_phase6.py
  - scripts/communicator/summarize.py
  - scripts/chunking/repair_qdrant_missing_points.py
  - viewer/components/ActionPreview/PreviewCardList.tsx
  - viewer/components/ActionPreview/ActionCard.tsx
  - viewer/components/ActionPreview/FieldDiff.tsx
  - viewer/components/ActionPreview/BatchApplyButton.tsx
  - viewer/lib/brain/apply.ts
  - docker-compose.yml
autonomous: true
requirements: [DIAG-REPAIR]
---

<objective>
Turn the July 1 diagnostics findings into small, low-risk repairs:
1. Clear the current ruff lint failures.
2. Update stale verifier path checks that still expect pre-locale viewer routes/components.
3. Add a safe Qdrant repair utility for the case where `paper_chunks.embedding_id`
   is populated but the corresponding local Qdrant point is missing.
4. Fix the Qdrant Docker healthcheck false negative caused by `wget` not being
   present in the current upstream image.
5. Request JSON mode for Communicator summaries so CGM-01 does not fail on
   model prose or malformed non-JSON wrappers.
6. Separate engineering-code gates from operator/live-fire gates where current
   diagnostics were failing because old data or no recent alert/digest existed.
7. Complete the Phase 5 ActionPreview UI surface expected by the manager flow.
</objective>

<scope>
No `.env` edits, no secret changes, no schema migrations, no git merge/rebase.
Qdrant repair may write only to the local Qdrant collection selected by
`QDRANT_URL`; Supabase rows are read-only for the missing-point repair.
</scope>

<verification>
- `ruff check` on touched Python files passes.
- Focused Phase 2.5 / Phase 5 / Phase 6 verifier gates reflect the current
  viewer structure instead of stale root-route/component paths.
- Local Qdrant `papers` point count reaches the DB `paper_chunks` embedding
  count, or the repair reports a concrete blocker without mutating Supabase.
- `viewer` lint/typecheck/build passes.
- Phase 2.5, Phase 5 code-complete, and Phase 6 code-complete are green.
</verification>

<result>
Completed 2026-07-01. Local Qdrant was repaired to cover all DB embedded
chunks; Docker healthchecks are green; viewer build passed; Phase 2.5 is 16/16,
Phase 5 code-complete is 13/13, and Phase 6 code-complete is 11/11.
</result>
