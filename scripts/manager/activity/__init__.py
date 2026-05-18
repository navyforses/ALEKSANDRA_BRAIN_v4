"""
scripts.manager.activity — Phase 5 Day 5 activity log + undo + audit.

Submodules (filled in on Day 5):

  log_action    — single entry point: write one manager_actions row
  undo          — reverse one manager_actions by id; writes pre-image back
                  to target_table and marks the original row
                  reversed_at + reversed_by
  audit_query   — paginate manager_actions with friendly labels

Undo contract (Phase 5 plan §"Day 5"):

  - Only rows with ``reversed_at IS NULL AND created_at > now() - '24h'``
    are undoable.
  - Undo writes a NEW manager_actions row with ``action_type='reverse'``
    and ``target_record_id`` = the original action's id.
  - The original row's ``reversed_at`` is set on the same transaction
    (single-shot, no double-undo).
  - Reversed actions stay queryable forever (immutable trail).
"""

from __future__ import annotations

__all__: list[str] = []
