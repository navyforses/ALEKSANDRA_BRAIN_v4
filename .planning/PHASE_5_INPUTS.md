# Phase 5 Inputs — Gemini Scaffold Inventory

**Date logged:** 2026-05-17
**Status:** Input document for `gsd-plan-phase` when Phase 5 kicks off. **Not yet implemented.** Phase 4 must close first.
**Decision:** Treat the Gemini-authored VIS-* scaffold as the **foundation** for Phase 5, not throwaway. Integrate after the cleanup-and-audit pass below.

---

## What Gemini delivered (untracked at this point in git)

All files mtime 2026-05-16 19:47 – 23:32. Inventory:

### A. UI scaffold (root-level, parallel to `viewer/app/`)

| File | Purpose | Quality |
|---|---|---|
| `layout.tsx` | 65/35 split — TopNav (60px) + main (65%) + persistent BrainPanel aside (35%); Inter font; shadcn HSL vars | DESIGN.md-compliant |
| `page.tsx` | Brain Viewer page — Doctor/Parent/Researcher view tabs; WebGL canvas placeholder; medical-red/green legend; Layers + Maximize + Controls overlay toolbar | DESIGN.md-compliant; missing NiiVue/R3F mount |
| `TopNav.tsx` | 5 tabs: Today / Brain / Knowledge / Therapies / Timeline + "Doctor Mode" badge | DESIGN.md-compliant |
| `BrainPanel.tsx` | Persistent right-side AI panel — activity log + voice/file input zone + active-status dot | Shell only, no wiring |
| `globals.css` | HSL CSS vars (background/foreground/border/primary/secondary/panel/muted); `--radius: 0.5rem` | DESIGN.md-compliant |
| `tailwind.config.ts` | shadcn theme + `medical.{red,green,orange,purple}` palette + Inter var + `tailwindcss-animate` plugin | DESIGN.md-compliant; needs dep alignment with viewer/ Tailwind 4 |

### B. Real neuroimaging MCP (FastMCP + nibabel)

| File | Size | Purpose |
|---|---|---|
| `mcp/aleksandra_niivue_mcp.py` | 17 KB | FastMCP server with `load_nifti`, `segment`, `export_mesh`, `family_html`, `build_voxel_network`, `distribute_brain_processing`, `plan_brain_swarm_architecture` |
| `mcp/swarm_orchestrator.py` | 18 KB | MapReduce coordinator using `multiprocessing`; `ChunkResult`/`ChunkAssignment` dataclasses; designed to scale to Celery |
| `server.py` | 6 KB | FastMCP demo server with mock brain regions + voxel-cloud generator + agent-step simulation |

### C. Swarm agents (Celery + Redis Streams design)

[agents/swarm/](agents/swarm/):
- `team_registry.py` (12 KB) — 8-team competency registry: Alpha (ingestion), Beta (MapReduce coord), Gamma (chunk workers ×100–300), Delta (anomaly), Epsilon (mesh export), Zeta (HTML/PDF), Eta (audit), Theta (Celery worker pool)
- `chunk_worker.py` (7 KB) — `ChunkWorkerAgent` class
- `enhanced_detector.py` (10 KB) — lesion detector
- `celery_app.py` + `celery_tasks.py` — Celery wiring (idle until Redis exists)

### D. Neuroimaging pipeline (15 scripts)

[scripts/neuroimaging/](scripts/neuroimaging/): `create_healthy_brain.py`, `create_damaged_brain.py`, `create_realistic_brain.py`, `create_realistic_damaged.py`, `compare_brains.py`, `swarm_compare.py`, `nifti_to_pointcloud.py`, `export_voxel_data.py`, `export_surface_voxels.py`, `export_brain_meshes.py`, `extract_inline_demo.py`, plus 4 test scripts (`test_swarm.py`, `test_celery_swarm.py`, `test_enhanced_swarm.py`, `create_test_nifti.py`).

### E. Standalone HTML demos (NOT for integration — refs only)

- `viewer/brain_voxels.html` (17 KB) — Georgian-UI voxel viewer; uses `linear-gradient(135deg, #0f0f23 …)` background **— banned by DESIGN.md "no sci-fi gradients"**
- `viewer/neuron_3d.html` (20 KB) — neuron 3D structure
- `viewer/demo_points.js` (23 KB) — 3D point cloud data

### F. Test fixtures from Gemini swarm runs

[tests/fixtures/](tests/fixtures/): `brain_comparison_report.json`, `damaged_brain_points.json`, `healthy_brain_points.json`, `swarm_comparison_report.json`, `enhanced_detector_validation.json`, `test_brain_128_swarm_result.json` — these are real swarm outputs and can serve as regression baselines.

### G. Architecture document

[.planning/research/MCP_SWARM_ARCHITECTURE.md](.planning/research/MCP_SWARM_ARCHITECTURE.md) (21 KB) — full design doc for the swarm + MCP. Tagged `Scope: v2 Visualization Phase (VIS-* requirements)`.

---

## Required cleanup pass before integration (Phase 5 Day 1)

Concrete fixes to apply when Phase 5 begins. These are blockers, not nits.

1. **Resolve dual-layout collision.** `viewer/app/layout.tsx` (Geist font, single-column landing) and root `layout.tsx` (Inter font, 65/35 split with BrainPanel) describe different apps. **Action:** make root layout canonical by moving `layout.tsx` → `viewer/app/layout.tsx`, `page.tsx` → `viewer/app/brain/page.tsx` (the file IS a Brain Viewer page, not a landing page); migrate the current minimal `viewer/app/page.tsx` to a `Today` route or repurpose it.

2. **Move root-level UI files into `viewer/`.** `BrainPanel.tsx` and `TopNav.tsx` → `viewer/app/_components/` (or `viewer/components/layout/` per the layout.tsx import path `@/components/layout/TopNav`). Without this, the root layout.tsx's imports are broken.

3. **Reconcile Tailwind configs.** Root `tailwind.config.ts` is Tailwind 3 style (`darkMode: ["class"]`, `require("tailwindcss-animate")`, content globs); `viewer/` is on **Tailwind 4** (PostCSS plugin). **Action:** port the `medical.*` palette and Inter variable into the Tailwind 4 config; do not bring `tailwindcss-animate` (Tailwind 4 has built-in `@theme` directives).

4. **Strip "limited outcomes" framing from `server.py`.** The mock brain region database hardcodes `"damage_status": "destroyed"` and `"plasticity_potential": "minimal"` for `motor_cortex`. This violates the **CLAUDE.md principle:** "Unknown potential — not limited outcomes", "MRI structural damage ≠ functional limit". **Action:** replace `damage_status` with `imaging_appearance` (factual MRI observation), drop `plasticity_potential` entirely or rename to `intervention_targets` (a clinical question, not a prognosis).

5. **Drop the banned gradient demos from Phase 5 acceptance.** `viewer/brain_voxels.html` and `viewer/neuron_3d.html` use `linear-gradient(135deg, #0f0f23 …)` — explicitly banned by DESIGN.md "Anti-Patterns" (no `bg-gradient-to-r`, no sci-fi). **Action:** keep them only as `.planning/research/` references; do NOT serve from `viewer/`.

6. **Register `aleksandra-niivue-mcp` in [MCP-INVENTORY.csv](MCP-INVENTORY.csv).** FND-06 requires every MCP server to be allowlisted before any agent can call it. Row format: `aleksandra-niivue-mcp,FastMCP NIfTI + segmentation + mesh export,communicator,5,visualization,VIS-01..05 — local-only; never receives raw voxels over wire`.

7. **Verify the swarm's CrewAI / MCP allowlist boundaries.** `agents/swarm/` uses Celery, not CrewAI. Decide whether the swarm is (a) called *by* the existing CrewAI agents via the MCP, or (b) a parallel runtime. Option (a) is cleaner — keeps Phase 0's MCP allowlist as the single trust boundary.

8. **Decide on the Redis dependency.** Celery requires a broker. Options: (i) Redis on Railway (~$5/mo), (ii) Redis in Docker locally for one-shot batches, (iii) drop Celery and use `multiprocessing` only (already wired in `swarm_orchestrator.py`). **Recommend (iii) until VIS scale demands more** — keeps Phase 5 inside the $30 MVP delta.

9. **PHI/HIPAA posture for MRI loading.** The MCP `load_nifti(file_path)` reads from disk — fine, but the *transport* must stay local. **Action:** in Phase 5 plan, add a hard gate: any `niivue-mcp` deployment **must** be stdio-only, no SSE, no HTTP. Document in the MCP-INVENTORY row.

10. **Audit `enhanced_detector.py` for fabrication risk.** A "lesion detector" output flows into the Communicator's clinical PDF. The Phase 3 CGM-01 verifier round-trips PMIDs/DOIs — there is no equivalent yet for *AI-generated lesion claims*. **Action:** in Phase 5 plan, design a VIS-* analog of CGM-01: lesion overlays must cite the segmentation model + version + reference dataset (BONBID-HIE / BIBSnet) and be visibly labeled as model output, not radiologist read.

---

## Files to keep verbatim (good as written)

- `mcp/aleksandra_niivue_mcp.py` — real nibabel; FastMCP tools well-structured
- `mcp/swarm_orchestrator.py` — MapReduce code is clean, dataclasses sensible
- `scripts/neuroimaging/*` — useful test-data generators; pair with BONBID-HIE
- `tests/fixtures/*.json` — regression baselines for Phase 5 swarm
- `.planning/research/MCP_SWARM_ARCHITECTURE.md` — architecture doc

## Files to discard

- `viewer/brain_voxels.html`, `viewer/neuron_3d.html` — sci-fi style, violate DESIGN.md
- `server.py` once `aleksandra_niivue_mcp.py` is canonical (mock data is misleading)
- `viewer/demo_points.js` once real NIfTI loading works

---

## Phase 5 candidate scope (decided 2026-05-17, conditional)

Per [docs/PHASE_4_VERIFICATION_REPORT.md](docs/PHASE_4_VERIFICATION_REPORT.md) §11, the Phase 5 charter is conditional on the 14-day Phase 4 acceptance window outcome:

- **If Phase 4 acceptance succeeds** → Phase 5 = **VIS-*** (this scaffold becomes the foundation)
- **If Phase 4 acceptance fails** → Phase 5 = **CGF-*** (cognition full); VIS-* deferred

This document assumes the VIS-* path. If routed to CGF-*, this file is parked and revisited later.

---

## Open question for the operator

The Gemini scaffold also contains `mcp/swarm_orchestrator.py:plan_brain_swarm_architecture()` — an MCP tool that **calls back to an LLM to plan its own architecture**. Decision needed at Phase 5 plan time: keep as a one-shot bootstrap or remove (recursion + cost risk).
