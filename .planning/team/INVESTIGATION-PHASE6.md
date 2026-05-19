# Investigation: Phase 6 Scaffold Classification
**Agent:** R3 (Wave 1)
**Audit reference:** `.planning/AUDIT_2026-05-18.md` §3 (referenced in mandate; not opened — banned)
**Cleanup checklist:** `.planning/PHASE_5_INPUTS.md` (10-item cleanup list, lines 60-82)
**Date:** 2026-05-18

## Method
- Got file list verbatim from `git status --short`
- Confirmed every classified file shows `??` (untracked) — not `M` (modified)
- Cross-checked directory contents with `ls -la` on each mentioned directory
- Read first 30-50 lines of each Python/HTML file
- Grepped HTML files for `linear-gradient` and `radial-gradient` to get **actual** line numbers of DESIGN.md violations (no suspicion-based flagging)
- Verified `viewer/app/brain/page.tsx`, `viewer/app/layout.tsx`, `viewer/components/layout/{BrainPanel,TopNav}.tsx` exist on-disk before treating them as integration targets
- Did NOT read `.handoffs/*` or any `PHASE_*_EXIT_REPORT.md` (banned per mandate)
- Did NOT assume the existence of `server.py` — explicit `Glob "server.py"` confirms it is NOT present in the repo (only inside `.venv/Lib/site-packages/...`)

## Untracked files actually present (verbatim from `git status --short`)
```
?? mcp/__init__.py
?? mcp/aleksandra_niivue_mcp.py
?? mcp/swarm_orchestrator.py
?? agents/swarm/                          (expanded below)
?? scripts/brain_builder_swarm.py
?? scripts/neuroimaging/                  (expanded below)
?? tests/fixtures/brain_comparison_report.json
?? tests/fixtures/damaged_brain_points.json
?? tests/fixtures/enhanced_detector_validation.json
?? tests/fixtures/healthy_brain_points.json
?? tests/fixtures/swarm_comparison_report.json
?? tests/fixtures/test_brain_128_swarm_result.json
?? viewer/brain_3d.html
?? viewer/brain_comparison.html
?? viewer/brain_data.js
?? viewer/brain_procedural.html
?? viewer/brain_procedural.js
?? viewer/brain_surface.html
?? viewer/brain_surface.js
?? viewer/brain_surface_damaged.js
?? viewer/brain_voxels.html
?? viewer/demo_points.js
?? viewer/neuron_3d.html
?? viewer/neuron_data.js
?? viewer/neuron_surface.html
```

`agents/swarm/` expanded (via `ls`):
```
agents/swarm/__init__.py
agents/swarm/celery_app.py
agents/swarm/celery_tasks.py
agents/swarm/chunk_worker.py
agents/swarm/enhanced_detector.py
agents/swarm/team_registry.py
```

`scripts/neuroimaging/` expanded (via `ls`):
```
scripts/neuroimaging/compare_brains.py
scripts/neuroimaging/create_damaged_brain.py
scripts/neuroimaging/create_healthy_brain.py
scripts/neuroimaging/create_realistic_brain.py
scripts/neuroimaging/create_realistic_damaged.py
scripts/neuroimaging/create_test_nifti.py
scripts/neuroimaging/export_brain_meshes.py
scripts/neuroimaging/export_surface_voxels.py
scripts/neuroimaging/export_voxel_data.py
scripts/neuroimaging/extract_inline_demo.py
scripts/neuroimaging/generate_brain_procedural.py
scripts/neuroimaging/generate_neuron.py
scripts/neuroimaging/nifti_to_pointcloud.py
scripts/neuroimaging/swarm_compare.py
scripts/neuroimaging/test_celery_swarm.py
scripts/neuroimaging/test_enhanced_swarm.py
scripts/neuroimaging/test_swarm.py
```

**Total: 31 untracked code/data files** in scope for Phase 6.

## File-by-file classification

### A. MCP servers (`mcp/`)

| File | Bytes | Class | Rationale | Cleanup min | Target |
|---|---|---|---|---|---|
| `mcp/__init__.py` | 40 | KEEP | Trivial package marker (`"""MCP servers for ALEKSANDRA_BRAIN."""`) | none | `mcp/__init__.py` |
| `mcp/aleksandra_niivue_mcp.py` | 16,753 | REFACTOR | Real FastMCP + nibabel; useful tools (`load_nifti`, `segment`, `export_mesh`, `family_html`, `build_voxel_network`, `distribute_brain_processing`); BUT (i) line 31 uses `header.get_affine()` which is removed in nibabel 3.x — must become `img.affine`; (ii) `segment`/`export_mesh`/`family_html` return stub strings ("ჩონჩხი" = "skeleton"); (iii) PHASE_5_INPUTS item 9 requires stdio-only enforcement docs/code | nibabel API fix + stub completion + stdio gate docstring + register in MCP-INVENTORY.csv | `mcp/aleksandra_niivue_mcp.py` |
| `mcp/swarm_orchestrator.py` | 18,239 | KEEP | Clean MapReduce w/ dataclasses, multiprocessing pool, `EnhancedDetector` integration via `healthy_path`; PHASE_5_INPUTS open question flags `plan_brain_swarm_architecture` (LLM-callback-to-plan-self) — DECISION NEEDED at Wave 2 (recursion + cost risk) | none if `CeleryOrchestrator` class also kept; otherwise strip Celery branch | `mcp/swarm_orchestrator.py` |

### B. Swarm agents (`agents/swarm/`)

| File | Bytes | Class | Rationale | Cleanup min | Target |
|---|---|---|---|---|---|
| `agents/swarm/__init__.py` | 469 | REFACTOR | Imports `celery_app`, `celery_tasks` in `__all__` — breaks at import time if Celery branch removed per PHASE_5_INPUTS item 8 recommendation (drop Celery, multiprocessing-only) | wrap Celery imports in try/except OR remove them from `__all__` | `agents/swarm/__init__.py` |
| `agents/swarm/team_registry.py` | 12,185 | KEEP | 8-team competency registry (alpha-theta) with dataclasses — sensible scaffold for future scale-up; pure data/types, no runtime risk | none (or trim Theta if Celery dropped) | `agents/swarm/team_registry.py` |
| `agents/swarm/chunk_worker.py` | 7,158 | KEEP | `ChunkWorkerAgent` class for one chunk processing; clean dataclass `ChunkWorkerResult`; used by both multiprocessing AND Celery paths | none | `agents/swarm/chunk_worker.py` |
| `agents/swarm/enhanced_detector.py` | 9,949 | REFACTOR | Real cyst/lesion detector (intensity Z-score vs baseline + GLCM texture); but PHASE_5_INPUTS item 10 says output flows into clinical PDFs without provenance — needs VIS-* analog of CGM-01 (cite model+version+dataset; label as model output, not radiologist read) | add `model_version`, `reference_dataset` fields to output schema; never emit lesions without a `source: "model"` tag | `agents/swarm/enhanced_detector.py` |
| `agents/swarm/celery_app.py` | 1,313 | DISCARD (recommended) **or** REFACTOR | PHASE_5_INPUTS item 8 recommends dropping Celery for MVP (use `multiprocessing` only); Redis adds ~$5/mo to Railway with no scale need yet | If discarding: delete + remove from `__init__.py`. If keeping: defer to ENV-gated activation only | (delete) |
| `agents/swarm/celery_tasks.py` | 2,007 | DISCARD (recommended) **or** REFACTOR | Same as `celery_app.py` — Celery wrapper around `ChunkWorkerAgent`. The underlying agent stays; the Celery binding is what's optional | same | (delete) |

**Note on Celery decision:** PHASE_5_INPUTS recommends option (iii) "drop Celery and use multiprocessing only — keeps Phase 5 inside the $30 MVP delta". `swarm_orchestrator.py` already implements pure-multiprocessing as the primary path, so this is a safe deletion. If kept, it stays idle until `REDIS_URL` actually resolves.

### C. Neuroimaging scripts (`scripts/neuroimaging/`)

| File | Bytes | Class | Rationale | Target |
|---|---|---|---|---|
| `compare_brains.py` | 10,162 | KEEP | Differential analysis healthy↔damaged → `tests/fixtures/brain_comparison_report.json`; pure utility script | `scripts/neuroimaging/` |
| `create_damaged_brain.py` | 5,652 | KEEP | Generates synthetic HIE+cystic encephalomalacia fixture (Aleksandra's profile); regenerable test data | `scripts/neuroimaging/` |
| `create_healthy_brain.py` | 4,302 | KEEP | Generates synthetic healthy neonatal baseline fixture | `scripts/neuroimaging/` |
| `create_realistic_brain.py` | 12,582 | KEEP | Anatomically-informed brain with gyri/sulci/ventricles/cerebellum/brainstem — Phase 6 stretch fixture | `scripts/neuroimaging/` |
| `create_realistic_damaged.py` | 4,931 | REFACTOR | Imports `from create_realistic_brain import ...` (sibling-script style, no package prefix) — breaks if cwd ≠ scripts/neuroimaging/. Change to `from scripts.neuroimaging.create_realistic_brain import ...` | `scripts/neuroimaging/` |
| `create_test_nifti.py` | 3,207 | KEEP | Older simpler synthetic brain w/ cysts — used by `test_swarm.py`, `test_celery_swarm.py`. Useful as a smoke-test fixture | `scripts/neuroimaging/` |
| `export_brain_meshes.py` | 2,549 | KEEP | Marching cubes → JSON meshes for Three.js; supersedes the inline `.js` data dumps once R3F integration lands | `scripts/neuroimaging/` |
| `export_surface_voxels.py` | 3,252 | KEEP | Surface-voxel extraction w/ outward-pointing normals for better point cloud rendering | `scripts/neuroimaging/` |
| `export_voxel_data.py` | 3,039 | KEEP | Older voxel exporter w/ Sobel-gradient normals — superseded by `export_surface_voxels.py` but still referenced | `scripts/neuroimaging/` |
| `extract_inline_demo.py` | 949 | REFERENCE-ONLY | One-shot generator for `viewer/demo_points.js` (the 800-point inline demo). Once real NIfTI loading via NiiVue works, both the generator and its output become obsolete | move to `.planning/research/scripts/` or delete with `demo_points.js` |
| `generate_brain_procedural.py` | 20,872 | REFERENCE-ONLY | Procedural brain as branching tubes — generates `viewer/brain_procedural.js` (832KB inline data). Conceptually clever, but PRODUCES one of the standalone demos that PHASE_5_INPUTS classifies as not-for-integration | keep in `.planning/research/scripts/` for reference |
| `generate_neuron.py` | 14,242 | REFERENCE-ONLY | Same shape — generates `viewer/neuron_data.js`; not an integration artifact | `.planning/research/scripts/` |
| `nifti_to_pointcloud.py` | 3,241 | KEEP | NIfTI → JSON point cloud w/ intensity colors — useful for regression baselines and Three.js demos | `scripts/neuroimaging/` |
| `swarm_compare.py` | 4,436 | KEEP | Runs `SwarmOrchestrator` on healthy vs damaged + writes `tests/fixtures/swarm_comparison_report.json` — regression harness | `scripts/neuroimaging/` |
| `test_celery_swarm.py` | 2,486 | DISCARD (if Celery dropped) | E2E test for the Celery path; obsolete if PHASE_5_INPUTS item 8 takes option (iii). References `CeleryOrchestrator` from `mcp.swarm_orchestrator` | delete with `celery_app.py`/`celery_tasks.py` |
| `test_enhanced_swarm.py` | 5,411 | KEEP | FP+TP test for `EnhancedDetector` (healthy-vs-healthy = ~0 lesions; damaged-vs-healthy = real lesions). This is the **closest thing to a Phase 6 verifier** in the scaffold | promote to `tests/integration/` later |
| `test_swarm.py` | 1,768 | KEEP | Smoke test for `SwarmOrchestrator` (multiprocessing path); fast, no Redis | promote to `tests/integration/` later |

### D. Other untracked Python (`scripts/`)

| File | Bytes | Class | Rationale |
|---|---|---|---|
| `scripts/brain_builder_swarm.py` | (mtime May 16 20:23) | REFERENCE-ONLY | 3-tier mock pipeline (MasterArchitect / ForemanAgent / WorkerDrone) using `ThreadPoolExecutor`; lines 14-20 contain hard-coded **mock LLM response** with `"vulnerability_to_hie": 0.85` — a fabricated number that violates the "ფაქტი არ გამოიგონო" principle. **Cannot ship.** Also overlaps conceptually with `swarm_orchestrator.py` (real MapReduce) | move to `.planning/research/` or delete |

### E. Standalone HTML demos (`viewer/`)

All 6 HTML files in `viewer/` have Georgian-language UI, "Segoe UI" font, dark backgrounds, neon button styles (rgba blues/teals). They violate **DESIGN.md §1 "Never Sci-Fi"** ("NO dark mode as default", "Use Inter exclusively for UI") even where they don't hit a `linear-gradient`.

| File | Bytes | Class | Rationale | DESIGN.md hits |
|---|---|---|---|---|
| `viewer/brain_voxels.html` | 17,166 | DISCARD | `linear-gradient` body (banned) + secondary `linear-gradient(90deg, ...)` accent | **L11**, **L79** — see DESIGN.md violations table |
| `viewer/neuron_3d.html` | 19,798 | DISCARD | `linear-gradient` body (banned) | **L11** — see DESIGN.md violations table |
| `viewer/brain_3d.html` | 12,988 | REFERENCE-ONLY | Solid dark background `#0a0a1a` (no gradient → no L11-equivalent hit), but Segoe UI font + dark-by-default + neon button styles still violate "Inter exclusively" and "NO dark mode as default" | font + dark-default violations (no gradient line) |
| `viewer/brain_procedural.html` | 10,870 | REFERENCE-ONLY | Solid `#080814` background, same font/dark issues | font + dark-default violations |
| `viewer/brain_surface.html` | 10,942 | REFERENCE-ONLY | Solid `#050510`, same | font + dark-default violations |
| `viewer/brain_comparison.html` | 12,933 | REFERENCE-ONLY | Solid `#050510`, same | font + dark-default violations |
| `viewer/neuron_surface.html` | 13,693 | REFERENCE-ONLY | Solid `#080814`, red neon palette `#e8a0a0` | font + dark-default violations |

**PHASE_5_INPUTS item 5 says:** "keep them only as `.planning/research/` references; do NOT serve from `viewer/`." → DISCARD the two banned-gradient files outright; the other five (no gradient hit, but other violations) move to `.planning/research/standalone_demos/` for archival reference.

### F. Standalone JS data dumps (`viewer/`)

| File | Bytes | Class | Rationale |
|---|---|---|---|
| `viewer/brain_data.js` | 457,496 | REFERENCE-ONLY | Pre-computed `BRAIN_VOXELS` array (~30K voxels w/ normals) — paired with `brain_voxels.html` |
| `viewer/brain_procedural.js` | 832,776 | REFERENCE-ONLY | Pre-computed `BRAIN_PROCEDURAL` array — paired with `brain_procedural.html` |
| `viewer/brain_surface.js` | 618,051 | REFERENCE-ONLY | Pre-computed `BRAIN_SURFACE` array (healthy) — paired with `brain_surface.html` |
| `viewer/brain_surface_damaged.js` | 614,419 | REFERENCE-ONLY | Pre-computed `BRAIN_SURFACE` array (damaged) — paired with `brain_surface.html` toggle |
| `viewer/neuron_data.js` | 199,279 | REFERENCE-ONLY | Pre-computed `NEURON_POINTS` array — paired with `neuron_3d.html` / `neuron_surface.html` |
| `viewer/demo_points.js` | 23,141 | DISCARD | 800-point inline demo (PHASE_5_INPUTS line 98: "discard once real NIfTI loading works"); generated by `extract_inline_demo.py` |

All these JS files are large precomputed data dumps (no logic). Move to `.planning/research/standalone_demos/` alongside their HTML peers (or delete `demo_points.js` outright).

### G. Test fixtures (`tests/fixtures/`)

| File | Bytes | Class | Rationale |
|---|---|---|---|
| `tests/fixtures/brain_comparison_report.json` | 9,666 | KEEP | Output of `compare_brains.py`; regression baseline for differential analysis |
| `tests/fixtures/swarm_comparison_report.json` | 2,642 | KEEP | Output of `swarm_compare.py`; regression baseline for swarm MapReduce |
| `tests/fixtures/enhanced_detector_validation.json` | 265,873 | KEEP | FP+TP test results — directly relevant to PHASE_5_INPUTS item 10 (clinical-claim provenance) |
| `tests/fixtures/test_brain_128_swarm_result.json` | 1,404,205 | KEEP | Swarm output on `test_brain_128.nii.gz`; smoke-test regression baseline |
| `tests/fixtures/healthy_brain_points.json` | 14,889,938 (~15 MB) | KEEP-but-LFS-or-gitignore | Point cloud dump used by Three.js demos; **too large for plain git** — either Git LFS or move to `.gitignore` + regenerate from `nifti_to_pointcloud.py` |
| `tests/fixtures/damaged_brain_points.json` | 24,736,839 (~25 MB) | KEEP-but-LFS-or-gitignore | Same — even larger |

Note: the existing `tests/fixtures/*.nii.gz` files are already committed and ranged 1.4-10.5 MB; the two `*_points.json` files are dramatically bigger and need a decision (LFS vs ignore-and-regenerate).

## DESIGN.md violations (verified via grep, not assumed)

| File | Line | Pattern (verbatim) | DESIGN.md rule violated |
|---|---|---|---|
| `viewer/brain_voxels.html` | **11** | `background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);` | §2 Anti-Patterns: BANNED `bg-gradient-to-r` family + §1 "NO purple/pink gradients, NO neon glows, NO dark mode as default" |
| `viewer/brain_voxels.html` | **79** | `background: linear-gradient(90deg, #4ECDC4, #FFE66D);` | §2 Anti-Patterns: same |
| `viewer/neuron_3d.html` | **11** | `background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);` | §2 Anti-Patterns: same |

`Grep "radial-gradient"` across `viewer/*.html` returned **No matches found** — no radial-gradient violations.

**The other 5 HTML files** (`brain_3d.html`, `brain_procedural.html`, `brain_surface.html`, `brain_comparison.html`, `neuron_surface.html`) do NOT use `linear-gradient` or `radial-gradient` — they use solid dark backgrounds (`#0a0a1a`, `#080814`, `#050510`). They still violate DESIGN.md §1 ("NO dark mode as default") and §2 ("BANNED: standard AI fonts (Roboto, Arial). Use Inter exclusively" — they use `'Segoe UI', Tahoma, Geneva, Verdana, sans-serif`), but **NOT** the gradient ban. Flagging as REFERENCE-ONLY (not DISCARD) reflects that distinction.

## PHASE_5_INPUTS.md 10-item checklist mapping

| # | Checklist item | Affected files (verified to exist) | Recommended action |
|---|---|---|---|
| 1 | Resolve dual-layout collision | `viewer/app/layout.tsx`, `viewer/app/page.tsx`, `viewer/app/brain/page.tsx` — already exist on-disk | **Already done in tree**: root `layout.tsx`/`page.tsx` referenced by checklist do NOT exist at repo root anymore; the Gemini scaffold appears to have been **moved into `viewer/app/`** before this audit. See "Untracked-sibling collision check" below. |
| 2 | Move root-level UI files into `viewer/` | `viewer/components/layout/TopNav.tsx`, `viewer/components/layout/BrainPanel.tsx` — already exist | **Already done in tree** — both files are at the path the checklist asks for. |
| 3 | Reconcile Tailwind configs | `viewer/package.json` + (former) root `tailwind.config.ts` (not in untracked list) | **Action needed at Phase 6 plan time**: port `medical.{red,green,orange,purple}` palette + `--font-inter` into Tailwind 4 `@theme` directives. Confirm `viewer/app/globals.css` already has the HSL CSS vars (read shows it's 1985 bytes — needs verification by Wave 2). |
| 4 | Strip "limited outcomes" framing from `server.py` | `server.py` — **NOT present anywhere in the repo** (Glob confirms only `.venv/.../server.py` matches) | **Item is moot** — likely already deleted in an earlier cleanup pass. Mark closed. |
| 5 | Drop banned gradient demos | `viewer/brain_voxels.html`, `viewer/neuron_3d.html` | DISCARD both. Other 5 HTML demos → REFERENCE-ONLY in `.planning/research/standalone_demos/`. |
| 6 | Register `aleksandra-niivue-mcp` in `MCP-INVENTORY.csv` | `MCP-INVENTORY.csv` (exists at repo root, confirmed via Glob) | Add row at Phase 6 Day 1; format given in PHASE_5_INPUTS line 75. |
| 7 | CrewAI / MCP allowlist boundary for swarm | `agents/swarm/*`, `mcp/swarm_orchestrator.py` | Pick option (a): CrewAI agents call the swarm via `aleksandra-niivue-mcp` tools, NOT directly. Single trust boundary preserved. |
| 8 | Redis dependency decision | `agents/swarm/celery_app.py`, `agents/swarm/celery_tasks.py`, `scripts/neuroimaging/test_celery_swarm.py` | Take option (iii): DISCARD Celery, multiprocessing-only. Save ~$5/mo Railway. |
| 9 | PHI/HIPAA stdio-only gate | `mcp/aleksandra_niivue_mcp.py` | Add hard assert + docstring: server must run stdio only, no SSE, no HTTP. Document in MCP-INVENTORY row. |
| 10 | Audit `enhanced_detector.py` for fabrication risk | `agents/swarm/enhanced_detector.py`, downstream Communicator PDF path | Design VIS-* CGM-01 analog: lesion overlays must carry `model_id`, `model_version`, `reference_dataset` (BONBID-HIE/BIBSnet) + visible "model output, not radiologist read" label. **Block any Communicator PDF that lacks these.** |

## Integration entry-point

**NiiVue/R3F mounts at:** `viewer/app/brain/page.tsx` — specifically inside the `<div className="flex-1 relative bg-slate-50 border border-slate-200 rounded-lg overflow-hidden shadow-inner flex flex-col min-h-[500px]">` container at **lines 41-76**. The placeholder at **lines 51-62** (`"WebGL Canvas Ready"` / `"React Three Fiber & NiiVue mount here in VIS-*"`) is the literal replacement target.

The file is already DESIGN.md-compliant (Inter font inherited from root layout, slate palette, no gradients) and already has correct Doctor/Parent/Researcher view tabs, Layers/Maximize/Controls toolbar overlay, and medical-red/medical-green legend. **Phase 6 work = replace the `<div className="text-center">` placeholder with a client component that wraps `@niivue/nvreact` + an R3F `<Canvas>` overlay.**

Trust-boundary note from `viewer/app/brain/page.tsx` lines 4-7:
> "All MRI data is client-side only (FND-01/FND-02) — no remote fetch from this route or any sibling route under viewer/app."

Phase 6 must preserve this. Any niivue volume URL must be a `URL.createObjectURL(file)` from a local file picker, never a server URL.

Companion files for the activity panel are already wired:
- `viewer/components/layout/BrainPanel.tsx` (right-side 35% aside)
- `viewer/components/BrainPanel/ActivityFeed.tsx`, `EmailIntent.tsx`, `InputBar.tsx`, `VoiceRecorder.tsx`
- `viewer/components/layout/TopNav.tsx` (5 tabs: Today/Brain/Knowledge/Therapies/Timeline)

## Untracked-sibling collision check

PHASE_5_INPUTS.md (lines 13-23, section A) lists six files supposedly at the repo root: `layout.tsx`, `page.tsx`, `TopNav.tsx`, `BrainPanel.tsx`, `globals.css`, `tailwind.config.ts`.

`git status --short` does NOT list ANY of these at the repo root. Verified by inspection of the full git status output above — no `?? layout.tsx`, no `?? page.tsx`, no `?? TopNav.tsx`, no `?? BrainPanel.tsx`, no `?? globals.css`, no `?? tailwind.config.ts` entries.

**Conclusion:** The Gemini scaffold UI files were already migrated into `viewer/app/` and `viewer/components/layout/` (those files are visible in `ls`, confirmed to exist on-disk, but they are NOT untracked — they presumably were committed in a prior commit, since they also don't appear with `M`). **PHASE_5_INPUTS items 1 + 2 are already resolved in the working tree.**

`server.py` (PHASE_5_INPUTS section B, line 30, item 4) is also NOT present anywhere outside `.venv/`. **Item 4 is moot.**

These three items can be closed at Phase 6 plan time — no work needed. **5 items remain actionable** (3, 5, 6, 7, 8, 9, 10 — counting 1, 2, 4 as already-done leaves 7 active items).

## Summary classification counts

| Class | Count | Files |
|---|---|---|
| **KEEP** | **15** | `mcp/__init__.py`, `mcp/swarm_orchestrator.py`, `agents/swarm/team_registry.py`, `agents/swarm/chunk_worker.py`, `compare_brains.py`, `create_damaged_brain.py`, `create_healthy_brain.py`, `create_realistic_brain.py`, `create_test_nifti.py`, `export_brain_meshes.py`, `export_surface_voxels.py`, `export_voxel_data.py`, `nifti_to_pointcloud.py`, `swarm_compare.py`, `test_enhanced_swarm.py`, `test_swarm.py`, plus all 4 small JSON fixtures (counted as 1 group) |
| **REFACTOR** | **5** | `mcp/aleksandra_niivue_mcp.py` (nibabel API + stubs + stdio gate), `agents/swarm/__init__.py` (Celery import guard), `agents/swarm/enhanced_detector.py` (provenance fields), `scripts/neuroimaging/create_realistic_damaged.py` (sibling-import fix), `tests/fixtures/{healthy,damaged}_brain_points.json` (LFS-or-regenerate decision) |
| **DISCARD** | **6** | `viewer/brain_voxels.html` (gradient), `viewer/neuron_3d.html` (gradient), `viewer/demo_points.js`, `agents/swarm/celery_app.py`, `agents/swarm/celery_tasks.py`, `scripts/neuroimaging/test_celery_swarm.py` |
| **REFERENCE-ONLY** | **10** | 5 non-gradient HTML demos (`brain_3d`, `brain_procedural`, `brain_surface`, `brain_comparison`, `neuron_surface`), 5 large JS data dumps (`brain_data`, `brain_procedural`, `brain_surface`, `brain_surface_damaged`, `neuron_data`), `extract_inline_demo.py`, `generate_brain_procedural.py`, `generate_neuron.py`, `scripts/brain_builder_swarm.py` |

(Tallies include all 31 untracked code/data files plus the 6 fixture JSONs — total ~37 items classified.)

## Open questions for Wave 2

- **Celery vs multiprocessing-only**: PHASE_5_INPUTS recommends drop Celery. R3 concurs. Confirm at Phase 6 plan time before deleting `celery_app.py` / `celery_tasks.py` / `test_celery_swarm.py`.
- **`plan_brain_swarm_architecture` MCP tool** (PHASE_5_INPUTS open question): keep as one-shot bootstrap or remove? R3 leans REMOVE — recursive LLM self-planning has unbounded cost and adds no MVP value when a working `SwarmOrchestrator` exists.
- **Point-cloud JSON fixtures (~40 MB combined)**: Git LFS or regenerate-on-demand via `nifti_to_pointcloud.py`? R3 leans regenerate-on-demand to keep the repo light; the source `.nii.gz` files are already in the repo.
- **`@niivue/nvreact` vs raw `@niivue/niivue` mount?** R3 recommends `nvreact` per CLAUDE.md stack notes; verify versions exist in `viewer/node_modules/` before committing.
- **`brain_builder_swarm.py` fabricated `vulnerability_to_hie: 0.85`**: do we have a "no-fabricated-numbers" linter for Phase 6 source files? If not, this script should be deleted, not moved to research/.
- **`viewer/AGENTS.md` warning** ("This is NOT the Next.js you know — APIs may differ; read `node_modules/next/dist/docs/` before writing"): Wave 2 must consult that path before authoring any niivue mount component.
- **MCP-INVENTORY.csv row format**: confirm the exact comma-separated schema by reading the current file before adding the `aleksandra-niivue-mcp` row.
- **Tailwind 4 vs 3 reconciliation**: verify whether `viewer/app/globals.css` already defines the medical palette via `@theme` directives, or if the migration from a root Tailwind-3 config is still pending.
