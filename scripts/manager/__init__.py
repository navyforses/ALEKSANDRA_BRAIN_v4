"""
scripts.manager — Phase 5 BRAIN AI Manager Assistant backend.

Public API surface (re-exported from submodules as Days 2–7 land):

  intake/    — multi-modal parsers (pdf, ocr, voice, email, text)
  routing/   — entity router + preview cards + apply orchestrator
  activity/  — manager_actions log writer + undo + audit query

The Phase 5 plan keeps every persistence touchpoint inside
``manager_actions`` so the BRAIN-applied CRUD trail stays auditable and
undoable. Every action ultimately writes a single ``manager_actions``
row via ``activity.log_action`` — that contract is the integration
seam every submodule honors.

Day 1 of the sprint ships only the package skeleton; submodule bodies
arrive on the day each capability is implemented.
"""

from __future__ import annotations

__all__: list[str] = []
