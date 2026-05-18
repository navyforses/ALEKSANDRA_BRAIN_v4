"""
scripts.manager.routing — Phase 5 Day 4 entity routing + preview cards.

Submodules (filled in on Day 4):

  entity_router    — Qdrant therapy match + table-by-table action proposer
  preview_builder  — compose ActionCard payloads with before/after diff
  apply_action     — execute one approved ProposedAction (pre-image fetch
                     → write → manager_actions row)
  apply_batch      — apply N approved actions in transaction; rollback all
                     if any fails

Trust-boundary policy (Phase 5 plan §"Day 4"):

  - Auto-execute: OCR'd date+drug, conf ≥ 0.9, target = timeline-only
                  (NEVER medication dose)
  - Preview + 1-click confirm: field updates on therapies/contacts/hypotheses
  - Explicit approval: drafts that compose an outbound email
  - Never auto: medication dose or drug name change
"""

from __future__ import annotations

__all__: list[str] = []
