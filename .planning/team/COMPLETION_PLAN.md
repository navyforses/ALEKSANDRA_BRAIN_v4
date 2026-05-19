# ALEKSANDRA_BRAIN — Site Completion Plan

**Agent:** D2 (Wave 2, Site Completion Architect)
**Date:** 2026-05-18
**Inputs consumed:** `.planning/AUDIT_2026-05-18.md` §1/§3/§7, `.planning/team/INVESTIGATION-PHASE6.md` (R3), `.planning/PHASE_5_INPUTS.md`, `.planning/research/MCP_SWARM_ARCHITECTURE.md` §1-3, `viewer/app/brain/page.tsx`, `DESIGN.md`, `viewer/AGENTS.md`.
**Banned reads honored:** No `.handoffs/*` or `PHASE_*_EXIT_REPORT.md` opened.
**User decision applied:** Phase 6 = integrate the existing 5,073 LOC scaffold after cleanup. No rewrite.

---

## §1. Context — definition of "site complete"

"Site complete" is the state at which **ALEKSANDRA_BRAIN delivers continuous, family-visible value without operator intervention** — i.e., literature mining runs on the 6-hour cron, weekly briefs land in Gmail every Sunday, clinician PDFs auto-generate, voice intake works in the BRAIN panel, and the 3D viewer at `viewer/app/brain/page.tsx` actually renders Aleksandra's MRI from a local file picker. The audit (§1) shows we are NOT there: Vercel is in ERROR state across 5 deploys (§4.6), the Railway service named `n8n` is not running n8n (§4.5), `manager_actions=0` / `intake_drops=0` / `briefs=0` (§4.1), CGM-01 is genuinely broken (§Phase 3), and 5,073 LOC of Phase 6 scaffold is sitting untracked (§3).

This plan defines six completion phases (C1..C6) that bridge from "repair plan R0 done" — meaning Tier-0 audit items unblock production traffic — to "Phase 6 acceptance + drift watch passes a 90+/90+ master verifier." The plan deliberately makes the **Phase 5 production smoke** (C1) the first gate, because every later phase depends on at least one real `manager_actions` row proving the cockpit works end-to-end. Phase 6 cleanup (C3) blocks Phase 6 integration (C4); the 10 backend gaps (C5) deliberately interleave with C2's 14-day acceptance soak so wall-clock time isn't lost. Total wall-clock budget from R0-done → C6-done: **~25 days** (14 of which are Phase 4 soak running in parallel with engineering work).

**Exit criteria (concrete, all must hold simultaneously):**

- **Family-visible:** Voice intake button in BrainPanel records → Whisper → `intake_drops` row → entity router → preview card; Sunday weekly digest fires unattended; clinician PDF auto-generates without manual `--mode code-complete` workaround; `/brain` route renders Aleksandra's MRI volume via NiiVue from a local file picker (no server upload); layout works at iPad-mini width (768px).
- **Operator-visible:** All 11 n8n workflow JSONs are `active=True` AND fire on schedule against a real n8n process (not `perception_worker.py` masquerading as n8n per audit §4.5); all 6 verifiers GREEN at `--mode production` (not just `code-complete`); `cumulative coverage = 90+/90+`.
- **Backend closed:** All 10 backend gaps from `.planning/phase-5/` resolved (Google Calendar, Supabase realtime, pattern recognition, TVB simulation stub, mobile, Auth, Whisper audit, voice-ambient PHI redactor, `aleksandra_timeline.event_type` ENUM, Python worker observability); 6 missing Supabase tables (audit §4.1: `llm_call`, `citations`, `digest_to_run_link`, `telegram_history`, `email_log`, `firecrawl_calls`) either created via migration or removed from code paths; CGM-01 propagation finished (CGM-01 itself was the `QDRANT_API_KEY` propagation bug — repair plan R0 fixes the verifier; C5 confirms no other Qdrant client in code is missing the key).
- **Phase 6 specific:** `aleksandra-niivue-mcp` registered in `MCP-INVENTORY.csv` row 6 (FND-06 allowlist); swarm orchestrator callable from Communicator agent via the MCP tool boundary (not direct Python import — per PHASE_5_INPUTS item 7 option a); banned-gradient HTML demos (`viewer/brain_voxels.html`, `viewer/neuron_3d.html`) deleted or archived to `.planning/research/visualization-demos/`; nibabel 3.x bug at `mcp/aleksandra_niivue_mcp.py:31` patched; `scripts/brain_builder_swarm.py` fabricated value removed.

---

## §2. Completion roadmap (C1..C6)

| Phase | Headline | Goal | Success criteria | Dependency | ETA |
|---|---|---|---|---|---|
| **C1** | Phase 5 production smoke | First real `intake_drops` row + `manager_actions` row from a live Shako voice clip + PDF drop + email intent | `select count(*) from manager_actions > 0` AND `select count(*) from intake_drops > 0` AND `select count(*) from runs where kind='whisper_call' > 0` AND a Telegram audit message visible in the family chat | R0 (repair plan) done — Vercel root dir fixed, n8n actually running, env vars distributed, `QDRANT_API_KEY` propagated | **1 hour Shako** (after R0) |
| **C2** | Phase 4 acceptance soak | 14 days of Sunday brief + daily digest firing without manual intervention | `briefs` count ≥ 2 (two Sundays in window); `prod_t1_delivered ≥ 3`; `prod_weekly_drafts ≥ 2`; `prod_clinician_drafts ≥ 1`; zero panic-stop events; daily-spend never exceeded $0.50 | C1 (proves the worker is reachable) | **14 days wall-clock soak** (engineering work proceeds in parallel) |
| **C3** | Phase 6 cleanup | 9 PHASE_5_INPUTS checklist items closed; banned-gradient demos archived; nibabel 3.x bug fixed; fabricated values removed; Tailwind 4 palette reconciliation done; MCP-INVENTORY row added; Celery branch deleted | All 9 task verify-probes return expected output; `git status` shows REFACTOR-class files modified/staged, DISCARD-class files deleted, REFERENCE-ONLY files moved to `.planning/research/visualization-demos/`; `git ls-files mcp/aleksandra_niivue_mcp.py` returns a path | C1 (no need to wait for C2 — cleanup is pure-edit work) | **2-3 hours engineering** |
| **C4** | Phase 6 integration — NiiVue MCP + swarm | `aleksandra-niivue-mcp` registered + stdio-only gate enforced; mount point at `viewer/app/brain/page.tsx:41-76` actually renders a NiiVue volume from a local file picker; swarm callable via `mcp.tool()` from Communicator agent; PHI/HIPAA transport gate enforced | Family member can drag-drop a NIfTI into `/brain` and see a 3D rendering within 10 seconds; `agents/communicator.py` invokes `aleksandra-niivue-mcp.segment(...)` and receives a structured response; new `verify_phase6.py` GREEN | C3 (cleanup must precede integration) | **3-5 days engineering** |
| **C5** | 10 backend gaps closure | All 10 items from `.planning/phase-5/` closed: Google Calendar API, Supabase realtime client, pattern recognition, TVB simulation stub, mobile responsive, Supabase Auth, Whisper transport audit, voice-ambient PHI redactor expansion, `aleksandra_timeline.event_type` ENUM, Python worker observability + the 6 missing Supabase tables resolved | Each gap has a verifier check or feature flag; `select pg_get_constraintdef(oid) from pg_constraint where conname='aleksandra_timeline_event_type_check'` returns a row; mobile viewport test at 768px passes manual review; OpenTelemetry traces visible in worker logs | C2 (acceptance lessons inform Whisper/PHI tuning); engineering can run in parallel with the C2 soak | **5-7 days engineering** |
| **C6** | Phase 6 acceptance + drift watch | Family-visible 3D brain viewer; clinician dossier export with VIS-* provenance (model_id + dataset cite analogous to CGM-01); new `verify_phase6.py` GREEN; cumulative master verifier shows `90+/90+` across all 6 phases | `python -m scripts.verify_phase{1..6} --mode production` all PASS; family signs off on the brain viewer (subjective UAT); 7-day drift watch confirms no new ERROR states on Vercel and no inactive workflow regressions | C4 + C5 | **3-day acceptance window** + 7-day drift watch |

**Total wall-clock from R0-done → C6-done:** ≈ 25 days (14-day C2 soak overlaps with 10-12 days of C3+C4+C5 engineering).

**Critical-path constraint:** C2 (the 14-day soak) is the single longest item and the only one that cannot be compressed — it is calendar-bound (two Sunday weekly briefs). Engineering work (C3, C4, partial C5) executes on the soak's calendar while the soak watches itself.

---

## §3. C3 executable plan — Phase 6 cleanup (9 tasks)

Based on R3's classification, items 1, 2, 4 from `PHASE_5_INPUTS.md` are **already done in the working tree** (no root `layout.tsx`/`page.tsx`/`TopNav.tsx`/`BrainPanel.tsx`/`server.py` — Glob confirmed). The remaining 7 active items plus 2 R3-discovered fixes (nibabel bug, fabricated value) yield 9 tasks. Each task ID maps `C3.N`.

### C3.1 — Verify already-done items (items 1, 2, 4)

- **Action:** Confirm no orphan files exist at repo root and viewer migration is complete.
- **Files touched:** none (read-only verification).
- **Verify probe:** `git ls-files | grep -E "^(layout|page|TopNav|BrainPanel)\.tsx$|^server\.py$"` returns empty AND `git ls-files viewer/app/layout.tsx viewer/components/layout/TopNav.tsx viewer/components/layout/BrainPanel.tsx viewer/app/brain/page.tsx` returns all 4.
- **Time:** 1 min.
- **Commit:** none (noop verify).

### C3.2 — Reconcile Tailwind 4 palette (item 3)

- **Action:** Port `medical.{red,green,orange,purple}` palette + Inter font variable into `viewer/app/globals.css` via Tailwind 4 `@theme` directives (NOT a root `tailwind.config.ts` — Tailwind 4 is config-less). Confirm by inspection that the four palette tokens are referenced in `viewer/app/brain/page.tsx:67-71` (`bg-medical-red`, `bg-medical-green`) and `viewer/app/brain/page.tsx:44` (`text-medical-purple`).
- **Files touched:** `viewer/app/globals.css` (palette injection if missing); confirm against `viewer/AGENTS.md` warning to read `node_modules/next/dist/docs/` first.
- **Verify probe:** Build viewer locally `cd viewer && npm run build` returns exit 0; grep `viewer/app/globals.css` for `--color-medical-red` (or whatever Tailwind 4 token form is used).
- **Time:** 20 min.
- **Commit:** `chore(viewer): port medical palette to Tailwind 4 @theme directives`.

### C3.3 — Move 5 REFERENCE-ONLY HTML demos to research archive (item 5, partial)

- **Action:** R3 confirmed only `viewer/brain_voxels.html` (lines 11, 79) and `viewer/neuron_3d.html` (line 11) violate the gradient ban. The other 5 (`brain_3d.html`, `brain_procedural.html`, `brain_surface.html`, `brain_comparison.html`, `neuron_surface.html`) use solid dark backgrounds — still off-spec (Segoe UI font, dark-by-default) but not the gradient ban. Move all 7 HTML files + their paired JS data dumps (`brain_data.js`, `brain_procedural.js`, `brain_surface.js`, `brain_surface_damaged.js`, `neuron_data.js`) to `.planning/research/visualization-demos/`. Delete `viewer/demo_points.js` outright (R3 DISCARD class).
- **Files touched:** `viewer/{brain_3d,brain_voxels,brain_procedural,brain_surface,brain_comparison,brain_surface_damaged,neuron_3d,neuron_surface}.html` (7 — note `brain_surface_damaged` is JS not HTML), `viewer/{brain_data,brain_procedural,brain_surface,brain_surface_damaged,neuron_data}.js` (5), `viewer/demo_points.js` (delete).
- **Verify probe:** `ls .planning/research/visualization-demos/ | wc -l` ≥ 12; `ls viewer/*.html viewer/*.js 2>/dev/null | wc -l` returns 0 (no orphan demos in viewer/ root).
- **Time:** 10 min.
- **Commit:** `chore(viewer): archive 7 standalone HTML demos + 5 data dumps to .planning/research/`.

### C3.4 — Fix nibabel 3.x bug in MCP (R3-discovered)

- **Action:** R3 flagged `mcp/aleksandra_niivue_mcp.py:31` uses `header.get_affine()` which was removed in nibabel 3.x. Replace with `img.affine` (the canonical nibabel 3+ API).
- **Files touched:** `mcp/aleksandra_niivue_mcp.py` line 31 only.
- **Verify probe:** `python -c "import nibabel as nib; img=nib.load('tests/fixtures/test_brain_128.nii.gz'); print(img.affine.shape)"` returns `(4, 4)` AND `grep -n "header.get_affine" mcp/aleksandra_niivue_mcp.py` returns empty.
- **Time:** 2 min.
- **Commit:** `fix(mcp/niivue): replace removed nibabel header.get_affine() with img.affine`.

### C3.5 — Delete fabricated `vulnerability_to_hie: 0.85` (R3-discovered)

- **Action:** R3 flagged `scripts/brain_builder_swarm.py` contains hard-coded mock LLM response with fabricated number `"vulnerability_to_hie": 0.85`. This violates CLAUDE.md "ფაქტი არ გამოიგონო" principle. The script is **already classified REFERENCE-ONLY** by R3 (3-tier mock pipeline overlapping with the real `swarm_orchestrator.py`). **Recommend deletion** rather than archival — the script has no integration path and the fabricated number leaks if anyone runs it.
- **Files touched:** `scripts/brain_builder_swarm.py` (delete).
- **Verify probe:** `git ls-files scripts/brain_builder_swarm.py` returns empty; grep `0.85` across `scripts/` for vulnerability strings returns no fabrication matches.
- **Time:** 1 min.
- **Commit:** `chore(scripts): delete brain_builder_swarm.py — fabricated mock value violated source-integrity rule`.

### C3.6 — Register `aleksandra-niivue-mcp` in MCP-INVENTORY.csv (item 6)

- **Action:** Add row per `PHASE_5_INPUTS.md` line 74 format: `aleksandra-niivue-mcp,FastMCP NIfTI + segmentation + mesh export,communicator,5,visualization,VIS-01..05 — local-only; stdio-only transport; never receives raw voxels over wire`. Confirm exact column schema by reading current `MCP-INVENTORY.csv` first.
- **Files touched:** `MCP-INVENTORY.csv`.
- **Verify probe:** `grep "aleksandra-niivue-mcp" MCP-INVENTORY.csv` returns 1 line; CSV still parses with `python -c "import csv; list(csv.reader(open('MCP-INVENTORY.csv')))"`.
- **Time:** 5 min.
- **Commit:** `chore(mcp): register aleksandra-niivue-mcp in FND-06 allowlist inventory`.

### C3.7 — Decide CrewAI / MCP allowlist boundary for swarm (item 7)

- **Action:** Per PHASE_5_INPUTS item 7 option (a), confirmed by R3: swarm called BY existing CrewAI agents via `aleksandra-niivue-mcp`, NOT directly. This is a **design decision document**, not code yet — the actual wiring happens in C4. Write a short ADR-style note in `.planning/decisions/PHASE6_SWARM_BOUNDARY.md` declaring "Communicator agent invokes swarm via `aleksandra-niivue-mcp.distribute_brain_processing()` tool, never via direct Python import of `mcp.swarm_orchestrator`." Also flag for removal: `mcp/swarm_orchestrator.py:plan_brain_swarm_architecture` (R3 + PHASE_5_INPUTS open question recommend REMOVE — recursive LLM self-planning has unbounded cost).
- **Files touched:** new file `.planning/decisions/PHASE6_SWARM_BOUNDARY.md`; `mcp/swarm_orchestrator.py` (remove the recursive `plan_brain_swarm_architecture` function only).
- **Verify probe:** ADR file exists; `grep "plan_brain_swarm_architecture" mcp/` returns empty.
- **Time:** 15 min.
- **Commit:** `chore(phase-6): adopt MCP-only swarm boundary; remove recursive plan_brain_swarm_architecture`.

### C3.8 — Drop Celery branch (item 8, R3 recommendation)

- **Action:** R3 concurs with PHASE_5_INPUTS option (iii): drop Celery, use `multiprocessing` only (already wired in `swarm_orchestrator.py`). Saves ~$5/mo Railway Redis cost. Delete `agents/swarm/celery_app.py`, `agents/swarm/celery_tasks.py`, `scripts/neuroimaging/test_celery_swarm.py`. Update `agents/swarm/__init__.py` to remove Celery imports from `__all__` (R3 REFACTOR class).
- **Files touched:** delete 3 files; edit `agents/swarm/__init__.py`.
- **Verify probe:** `python -c "import agents.swarm"` returns exit 0 (no ImportError); `ls agents/swarm/celery*` returns no matches; `grep -r "from agents.swarm.celery" .` returns no matches.
- **Time:** 10 min.
- **Commit:** `chore(swarm): drop Celery branch — multiprocessing-only per MVP budget`.

### C3.9 — Add PHI/HIPAA stdio-only gate to niivue MCP (item 9)

- **Action:** Add hard assert + docstring at top of `mcp/aleksandra_niivue_mcp.py`: server must run stdio only, no SSE, no HTTP. Implementation: at startup, raise `RuntimeError` if any HTTP/SSE transport flag is passed to FastMCP; document in module docstring and in the MCP-INVENTORY row (already done in C3.6). Also flag `enhanced_detector.py` (R3 REFACTOR class) to gain `model_version`, `reference_dataset`, `source: "model"` provenance fields per PHASE_5_INPUTS item 10. The provenance schema lands in C4; this task only adds the stdio gate.
- **Files touched:** `mcp/aleksandra_niivue_mcp.py` (top of file: docstring + transport assertion).
- **Verify probe:** `grep -n "stdio-only\|no HTTP\|no SSE" mcp/aleksandra_niivue_mcp.py` returns matches; attempting to instantiate the MCP with `transport="sse"` raises RuntimeError.
- **Time:** 10 min.
- **Commit:** `feat(mcp/niivue): enforce stdio-only transport — PHI/HIPAA local-only gate`.

**C3 total:** 9 tasks, **~75 min engineering** (well under the 2-3 hour estimate; buffer absorbed by Tailwind 4 reconciliation risk).

---

## §4. C4 outline — NiiVue MCP integration (phase plan sketch)

Not a deep-executable spec yet; C4's own `gsd-spec-phase` will produce that. The major workstreams:

1. **Register in MCP-INVENTORY** — already done in C3.6.
2. **Mount NiiVue React component** — replace the placeholder `<div className="text-center">` at `viewer/app/brain/page.tsx:51-62` with a client component (`'use client'`) that wraps `@niivue/nvreact` and renders into the already-allocated WebGL container at lines 41-76. **Critical constraint per `viewer/app/brain/page.tsx:4-7`:** the volume URL must be a `URL.createObjectURL(file)` from a local file picker (`<input type="file" accept=".nii,.nii.gz">`), never a server URL. R3 recommends `@niivue/nvreact` over raw `@niivue/niivue` (matches CLAUDE.md stack note).
3. **Wire `load_nifti` MCP tool to React component via Communicator agent path** — when the family drops a file, the React component calls a CrewAI Communicator agent endpoint; Communicator calls `aleksandra-niivue-mcp.load_nifti(...)` via the MCP boundary defined in C3.7 ADR. The MCP returns metadata (dimensions, affine, intensity range) which the React component uses to set up the NiiVue scene. The raw volume bytes never traverse the network — only metadata.
4. **Wire swarm via multiprocessing** — C3.8 dropped Celery. The swarm orchestrator (`mcp/swarm_orchestrator.py`) is invoked via `aleksandra-niivue-mcp.distribute_brain_processing(...)` for any lesion-detection batch. Per R3's note on `agents/swarm/enhanced_detector.py`, the detector output schema must include `model_version`, `reference_dataset` (BONBID-HIE/BIBSnet), and `source: "model"` — analog of CGM-01 for VIS-* claims.
5. **Enforce PHI/stdio gate** — already done in C3.9 at MCP startup; verify end-to-end in C4 by attempting to run the MCP under `mcp.client.http_client` (should fail) versus `mcp.client.stdio_client` (should succeed).
6. **Reading `viewer/AGENTS.md` first** — `viewer/AGENTS.md` warns "This is NOT the Next.js you know — APIs may differ; read `node_modules/next/dist/docs/` before writing." C4 must consult that path before authoring any niivue-mount component. Failure to consult is a known historical bug source.
7. **New verifier:** `scripts/verify_phase6.py` — see §6 for sketch.

**Phase 6 spec deliverable:** `gsd-spec-phase` for C4 produces VIS-01..05 requirements:
- VIS-01: family can load a NIfTI via local file picker; volume renders in <10s
- VIS-02: lesion-detection output carries model+version+dataset provenance (CGM-01 analog)
- VIS-03: MCP enforces stdio-only transport; HTTP/SSE attempts raise RuntimeError
- VIS-04: swarm orchestrator processes a 128^3 fixture (`tests/fixtures/test_brain_128.nii.gz`) in <60s on multiprocessing path
- VIS-05: clinician PDF export includes the rendered brain view + VIS-02 provenance

---

## §5. C5 backend gaps — high level

The 10 backend gaps documented in `.planning/phase-5/` (referenced in audit §Phase 5 final paragraph). For each: what closing means, owner, ETA.

| Gap | Closing means | Owner | ETA |
|---|---|---|---|
| **G1. Google Calendar API** | Treatment-timeline events (vigabatrin washout, Duke EAP target, BMC appointments) write to Google Calendar via OAuth-installed creds. Verifier check: `select count(*) from runs where kind='calendar_event_write' > 0`. | Shako (OAuth) + Claude (n8n node) | 4 hrs |
| **G2. Supabase realtime client** | `viewer/components/BrainPanel/ActivityFeed.tsx` subscribes to `manager_actions` realtime channel; new rows appear without poll. Verifier: open `/brain`, insert a row, see it appear within 2s. | Claude | 3 hrs |
| **G3. Pattern recognition** | Hypothesis agent learns recurring entity patterns across `episodic_facts` (e.g., recurring drug-disease pairs in literature). Verifier: `select count(*) from hypotheses where confidence > 0.6 and discovered_by='pattern_recognition' > 0`. | Claude | 1 day |
| **G4. TVB simulation stub** | One-shot Docker run of TVB 2.9 against the patient's connectome (when available); writes output to R2; NOT in-app per stack notes. Verifier: TVB Docker image pulled, smoke run on `bnm-config-sample` completes. **Deferred to Phase 7+ per §7 — stub only in C5.** | Claude (stub) | 2 hrs (stub) |
| **G5. Mobile responsive** | `viewer/app/brain/page.tsx` and `viewer/app/today/page.tsx` work at 768px (iPad-mini) and 390px (iPhone-mini); BrainPanel collapses to a bottom-sheet on <768px. Verifier: Chrome DevTools device-emulation pass. | Claude | 6 hrs |
| **G6. Supabase Auth** | Magic-link auth gates `/brain`, `/today`, `/audit-log`; service-role keys never leave server. **Single-operator scope locked per §7 deferral — defer multi-tenant.** Verifier: anon visitor gets 401 on `/api/manager-actions`. | Claude | 4 hrs |
| **G7. Whisper transport audit** | Verify Whisper voice transport never persists raw audio to Supabase; transcription happens, raw blob is dropped. Verifier: `select count(*) from intake_drops where raw_audio_bytes is not null` = 0 across 30 test clips. | Claude | 3 hrs |
| **G8. Voice-ambient PHI redactor expansion** | PHI redactor (CGM-02) currently handles 12 fixture types; expand to voice-ambient cases (background chatter mentioning MRN, DOB drift). Verifier: 30 new voice fixtures, 30/30 redaction match. | Claude | 6 hrs |
| **G9. `aleksandra_timeline.event_type` ENUM** | Currently `event_type` is a free-text column on `aleksandra_timeline` (9 rows per audit §4.1). Migrate to ENUM `('clinical', 'imaging', 'milestone', 'travel', 'medication')`. Verifier: `select pg_get_constraintdef(oid) from pg_constraint where conname='aleksandra_timeline_event_type_check'` returns a row. | Claude | 1 hr |
| **G10. Python worker observability** | Add OpenTelemetry traces to `perception_worker.py` for `/perception-tick`, `/chunking-tick`, `/extraction-tick`, `/morning-briefing`, `/fire-daily-batch`, `/render-weekly-brief` endpoints. Verifier: Railway service logs include `traceparent` headers. | Claude | 4 hrs |

**Plus: 6 missing Supabase tables** (audit §4.1: `llm_call`, `citations`, `digest_to_run_link`, `telegram_history`, `email_log`, `firecrawl_calls`). Per Tier-2 audit item T2-4: decide create-via-migration vs remove-from-code. **Recommendation: write migration 012 to create them** because each name suggests legitimate observability/audit value already referenced in code. Time: 2 hrs.

**C5 total wall-clock:** ~5 days engineering. Many gaps can run in parallel.

---

## §6. Verification per phase

| Phase | Verifier | Production-mode criterion |
|---|---|---|
| **C1** | `python -m scripts.verify_phase5 --mode production` (NEW mode flag — currently only `--mode code-complete`) | `manager_actions count > 0` AND `intake_drops count > 0` AND `runs.kind='whisper_call' count > 0` |
| **C2** | `python -m scripts.verify_phase4 --mode production` (NEW mode flag) | `prod_t1_delivered ≥ 3` AND `prod_weekly_drafts ≥ 2` AND `prod_clinician_drafts ≥ 1` AND `briefs count ≥ 2` |
| **C3** | New ad-hoc check (no full verifier script): `ls .planning/research/visualization-demos/ \| wc -l` ≥ 12; `grep "img.affine" mcp/aleksandra_niivue_mcp.py` matches; `grep -L "vulnerability_to_hie" scripts/` returns; `grep "aleksandra-niivue-mcp" MCP-INVENTORY.csv` returns 1 line; no `celery*` files in `agents/swarm/` | per task probes in §3 |
| **C4** | New `scripts/verify_phase6.py` with checks VIS-01..05 (see §4) | VIS-04 swarm-on-fixture < 60s; VIS-03 stdio-only assertion holds |
| **C5** | Per-gap verifier checks: enumerated in §5 table column "Verifier" | each gap probe returns expected value |
| **C6** | Master verifier rolling up all 6: `python -m scripts.verify_phase1 && verify_phase2 && verify_phase2_5 && verify_phase3 && verify_phase4 --mode production && verify_phase5 --mode production && verify_phase6` | Total checks: 10 + 19 + 16 + 11 + 9 + 13 + ~13 (VIS-01..05 + REGR + observability) ≈ **91/91** PASS |

**New verifier introductions required:**
1. `--mode production` flag added to `verify_phase4` and `verify_phase5` (currently only `--mode code-complete`).
2. New `scripts/verify_phase6.py` with VIS-01..05 + REGR cascade.
3. Optional: master script `scripts/verify_all_phases.py` orchestrating the 6 verifiers + writing a single PASS/FAIL roll-up.

---

## §7. Out of scope (explicit deferrals to Phase 7+)

The following are intentionally excluded from "site complete." They were considered and explicitly deferred:

- **TVB whole-brain simulation** — only the stub lands in C5/G4; the actual Docker-driven simulation runs are Phase 7. Reason: requires per-patient connectome derivation (FastSurfer-LIT output) which is itself a Phase 7 add-on; not on critical path for family value.
- **brain2print STL export pipeline** — nii2mesh → meshlab/pymeshfix watertight pass; defer to Phase 7 once C4 brain viewer is GREEN. R3 noted `nii2mesh` outputs aren't watertight for printing; the post-processing is non-trivial and not blocking family value.
- **Multi-tenant Supabase Auth** — C5/G6 locks single-operator scope (Shako = MANAGER_USER_ID). Multi-tenant (Diana, clinicians) is Phase 7+ when the security review can be funded.
- **Hindsight self-improving memory** — defer to Phase 3+ (already noted in CLAUDE.md stack notes). Not on the path to "site complete."
- **Prism MCP HIPAA-hardened on-device memory** — defer until a clinician needs read access. Until then, MRI stays client-side and PHI never enters server memory.
- **Anything that breaks the $20-30/mo MVP budget cap** — implies Firecrawl Pro tier, Anthropic over $40/mo, Railway over $25/mo, or new SaaS subscriptions. Out of scope by constraint.
- **`viewer/app/brain/page.tsx` deep-clinical features** (radiologist tracing tools, ROI measurement, DICOM windowing presets) — out of scope. The brain viewer's MVP role is "family can see Aleksandra's structural MRI in 3D"; clinician-grade tooling is Phase 7+.
- **R3F v10 migration** — stick with R3F 9.6.x stable per CLAUDE.md stack notes; v10 is alpha as of May 2026. Revisit at v10 GA.
- **`PHASE_5_INPUTS.md` open-question item `plan_brain_swarm_architecture` MCP tool** — R3 recommends REMOVE; C3.7 removes it. Not deferred — explicitly killed.

---

## §8. Open questions (escalated to S1)

The following decisions exceed D2's authority and need a synthesizing or operator decision:

1. **Can C5 backend gaps run in parallel with C3+C4, or must they be serialized?** D2's recommendation: C5/G1 (Calendar), G2 (realtime), G7 (Whisper audit), G9 (timeline ENUM), G10 (observability) are **independent** of C3/C4 — they can start the moment R0 ends. C5/G2 (realtime) depends on C5/G6 (Auth gate) only loosely; G3 (pattern recognition), G4 (TVB stub) are pure-backend. G5 (mobile) and G8 (voice-PHI) interact with C4 viewer changes — recommend serialize after C4 for those two. **Open for S1 confirmation.**

2. **Vercel SSO gate (audit §4.6: `viewer-git-main-…` returns 401):** Family members cannot access the deployed viewer without Vercel SSO seats. Is the plan to **(a)** disable SSO for the production alias (set as public), **(b)** add Shako + Diana as Vercel team members, or **(c)** deploy `/brain` to a non-Vercel public URL (e.g., Cloudflare Pages)? Option (a) is cheapest; (b) is most secure. **Open — D2 cannot decide.**

3. **Vercel alias `aleksandra-brain-v4.vercel.app` does NOT exist (audit §4.6: `DEPLOYMENT_NOT_FOUND`).** The Phase 5 operator runbook references this URL. Decision: **(a)** create the alias (CLI: `vercel alias <prod-dpl> aleksandra-brain-v4.vercel.app`) — but Vercel requires this name be unique globally and it may be taken, OR **(b)** update all docs to use `viewer-sigma-two.vercel.app` (the actual stable alias). Recommend (a) if available, (b) otherwise. **Open — needs Vercel CLI probe.**

4. **6 missing Supabase tables (audit §4.1):** Create migration 012 (D2 recommendation in §5), or remove the code references that target these table names? Trade-off: creating tables that have no producers is dead weight; removing code references risks breaking call sites that may activate later. **Open — needs S1 audit of code references.**

5. **CGM-01 in repair plan R0 vs C3:** Audit Tier 0 T0-6 fixes CGM-01 (`QDRANT_API_KEY` propagation to `summarize()`). Is this part of **R0 (repair plan)** or **C3 (Phase 6 cleanup)**? D2 assumes R0 — this plan starts after R0-done. **Open — confirm with S1.**

6. **`tests/fixtures/healthy_brain_points.json` (~15MB) and `damaged_brain_points.json` (~25MB):** R3 flagged as KEEP-but-LFS-or-gitignore. Decision: **(a)** Git LFS (operational overhead), **(b)** add to `.gitignore` + regenerate on demand via `nifti_to_pointcloud.py` (R3's lean recommendation), **(c)** move to R2 with checksum manifest. D2 leans (b). **Open.**

7. **`enhanced_detector.py` VIS-* provenance schema (R3 item 10):** Should the lesion-output schema use the exact CGM-01 column names (`source`, `cite_ids`, `confidence`) or VIS-prefixed parallels (`vis_source`, `vis_model_id`, `vis_dataset`)? D2 leans parallel namespace to avoid coupling literature-cite logic with model-output logic. **Open.**

---

## End-state map

| Item | Audit value (2026-05-18) | Target value (C6-done) |
|---|---|---|
| `manager_actions` count | 0 | ≥ 5 |
| `intake_drops` count | 0 | ≥ 5 |
| `briefs` count | 0 | ≥ 2 |
| `prod_t1_delivered` | 0 | ≥ 3 |
| `prod_weekly_drafts` | 0 | ≥ 2 |
| `prod_clinician_drafts` | 0 | ≥ 1 |
| Vercel deploy state | ERROR (5/5) | READY |
| n8n service actually n8n | NO | YES |
| Active workflows firing | 0 (n8n dead) | 11/11 |
| Verifier coverage | 73/78 (CGM-01 + 4 REGR cascades) | 91/91 |
| Untracked Phase 6 LOC | 5,073 | 0 (all KEEP-class committed, DISCARD deleted, REFERENCE-ONLY archived) |
| Banned-gradient files | 2 | 0 |
| nibabel 3.x bug | active | fixed |
| Fabricated `vulnerability_to_hie` | present | deleted |
| MCP-INVENTORY rows | N (without niivue) | N+1 (niivue registered) |
| Brain viewer | placeholder | renders Aleksandra's MRI |
| Backend gaps closed | 0/10 | 10/10 |

---

*End of plan. Owner: Shako Jincharadze. Next action: synthesis agent S1 consumes this + R3 + repair plan R0 into a master execution sequence.*
