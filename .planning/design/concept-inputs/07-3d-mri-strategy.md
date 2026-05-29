# Concept Input 07 — 3D / MRI Viewer Strategy

**Author**: design-webgl-3d
**Date**: 2026-05-25
**Wave**: 3 of 3 — specialty positioning
**Status**: input for design-director synthesis
**Files read**: `viewer/app/[locale]/brain/page.tsx` · `viewer/package.json` · CLAUDE.md § Visualization + § Privacy posture · Concept Inputs 01–06, 08

---

## 7.1 Current state of `/brain` — what is actually there

`viewer/app/[locale]/brain/page.tsx` is **86 lines of placeholder chrome with zero 3D**. It renders a card-shaped frame, three pseudo-tabs (`doctorView` / `parentView` / `researcherView`) as plain `<button>` elements without `role="tab"` (a11y B2), an icon-only Layers toggle, a red/green legend (a11y B3), and centered "in development / drop MRI hint" copy. Nothing loads, nothing parses, nothing renders volumetric. The comment at line 4 — "All MRI data is client-side only (FND-01/FND-02)" — is forward-looking promise, not implementation.

`viewer/package.json` confirms what we feared and need: **NiiVue is not installed. `@niivue/nvreact` is not installed. `@react-three/fiber` is not installed. `drei` is not installed. `postprocessing` is not installed.** The only related dep is `react-dropzone@15.0.0` — the file picker the agent canon names as the privacy-correct ingest UX. The brain route is genuinely a greenfield surface: no rip-and-replace cost, no in-flight viewer state to migrate.

This is good news for v8 planning. There is no debt, no half-built viewer, no upstream NiiVue version we are pinned to. Whatever we ship will be the first thing.

## 7.2 The MRI viewer in the new IA — where does it live?

Concept Input 04 lands `/brain` under the **Belief** section alongside Twin · Causal · Simulate · Drift. That is correct, and I would not move it. Rationale:

- **Belief is the model-vs-anatomy section.** Twin holds the 13-dimensional posterior, Drift holds its evolution, Causal holds the DAG. `/brain` is the only Belief surface where the anatomy is *literal*. Co-locating it with Twin/Drift teaches the operator: "this is what we believe about Aleksandra, expressed five ways."
- **Brain is NOT a Research section route.** Research (Hypotheses · Papers · Therapies · Timeline) is paper-and-finding pipeline territory. The MRI viewer never produces a citation; it is reference imagery, not evidence-output.
- **Brain is NOT a channel-namespace route.** No wife-facing `/family/brain` route in v8 or v9. The clinician deep-link variant (7.6 below) is a separate consideration, but it routes off the operator surface, not off a parallel family surface.

The BrainPanel docking rule from IA §4.4 ("collapse to 56px on dense routes") applies here: **`/brain` gets the collapsed-rail panel** because the viewer itself owns the visual real estate. The MRI volume + slice navigation must claim the same ~65% column that hypotheses cards claim on `/hypotheses`; the BrainPanel cannot eat 35% of a 3D surface.

## 7.3 Minimum viable MRI viewer surface for v8

**IN** for v8 (the floor that earns the route):

1. **NiiVue volume render** of a single client-loaded NIfTI file (`.nii.gz` / `.nii`) via `@niivue/nvreact`'s declarative component, mounted inside a `<Suspense>` boundary with our shimmer fallback.
2. **`react-dropzone` ingest** with explicit privacy reassurance copy: "Files stay in your browser. Nothing is uploaded." This copy is non-negotiable per FND-01/FND-02 and the agent canon rule 13.
3. **Three orthogonal slice views** (axial / coronal / sagittal) with a single linked-crosshair, keyboard slice nav (↑/↓ steps slice, ←/→ jumps 10 slices, `Home`/`End` go to extremes — per a11y principle 4 and agent canon rule 14).
4. **One overlay type**: a binary lesion mask, loaded as a second NIfTI, rendered with `viridis` colormap at 0.6 opacity (never `jet`, per agent canon rule 8). Toggle on/off via `L` key or the Layers icon-button (now properly `aria-label`ed per a11y B2).
5. **Reduced-motion mode**: zero auto-rotate, zero shader-heavy effects, static camera, the `prefers-reduced-motion` global rule from motion §6.2 just works.
6. **ARIA description + text-summary fallback**: a visually-hidden live region announces "axial slice 45 of 90, lesion overlay on" on every change (a11y principle for 3D).

**OUT** for v8 (deferred to v9 explicitly):

- R3F anatomical shells around the viewer (postprocessing depth-of-field, ambient brain mesh context).
- Multiple simultaneous overlays (just one toggle is enough to learn the pattern).
- nii2mesh-derived 3D-print STL pipeline (off-app Docker, not in-viewer; agent canon names it as off-app).
- TVB simulation visualization (depends on v7-neurosim Docker output, not yet a contract).
- Doctor / parent / researcher view-mode tabs as **functionally distinct** — v8 keeps the tab visual but all three render the same viewer; modes ship in v9 when we know what they actually toggle.

## 7.4 v8 commit or v9 defer? — recommendation

**Recommendation: v8 commits to the minimum viable surface above. Do not defer to v9.**

The case for committing in v8:

- The brain route is already in nav, already in i18n, already named in the brief as a "hero surface." Shipping it with 0 of the promised functionality for another version cycle reads as broken to anyone who clicks the tab. A placeholder that has been a placeholder for 9 months is debt that compounds.
- **NiiVue is small and self-contained**: ~600KB gzipped, lazy-loaded via dynamic import on the brain route only — zero impact on the home / dashboard / research bundles. `@niivue/nvreact` is a thin React wrapper; the integration surface is small.
- **No R3F yet.** v8 does NOT install `@react-three/fiber@9.6.x` or `drei` or `postprocessing`. Those land in v9 when we have an anatomical-shell justification. The MV surface above is pure NiiVue + dropzone + keyboard nav — and that is the entire bundle delta.
- The neuroplasticity-window time pressure (CLAUDE.md, Aleksandra ~9 months) argues for *making the surface real* now, even at a floor. A real viewer that loads a real T1 from Shako's laptop is a different artifact than a card that says "in development."

Cost estimate: **~3-4 engineer-days** for the v8 floor — 1d NiiVue + nvreact integration spike, 1d slice nav + keyboard + ARIA, 0.5d lesion-overlay toggle, 0.5d empty / loading / error states, 0.5d the privacy-copy + i18n keys + ChartLegend-style legend primitive coordination with design-dataviz §5.5. Risk: low. There is no upstream uncertainty — `@niivue/nvreact` is maintained by the NiiVue org, niivue v0.49 is current, the dropzone + Blob → ArrayBuffer flow is documented.

Dependencies that must land first: motion §6.2 reduced-motion global rule (otherwise we re-accrue debt instantly), a11y F9 focus-visible rule (the slice-nav buttons need a visible focus ring), and the IA §4.4 BrainPanel collapsed-rail behavior (otherwise the viewer ships with a 35% panel eating into it).

**What stays v9-deferred**: R3F shells (need a designed visual reason, not "because it's cool"), nii2mesh export pipeline, TVB simulation viz, the three view-mode functional differentiation, and the segmentation-overlay UX (7.5 below explains why segmentation specifically defers).

## 7.5 FastSurfer-LIT / BIBSnet segmentation pipeline UX

The CLAUDE.md pipeline is **FastSurfer+LIT → BIBSnet → BONBID-HIE → nii2mesh** — and per the agent canon rule on PHI, all four containers run on a **family-controlled machine, never in the cloud**. This shapes the UX in a specific way:

1. **Family does not see segmentations in v8.** The pipeline does not exist as a running service. Until v7-devops stands up a one-shot Docker workflow that produces a `segmentation.nii.gz` artifact on Shako's machine, there is nothing to visualize. In v8 the viewer accepts a *lesion mask* (whatever NIfTI Shako has on hand — Duke's MRI radiologist deliverable, a manually drawn ITK-SNAP mask, or a BIBSnet output if/when one exists) — but does not assume any specific pipeline produced it.
2. **The off-device → in-viewer flow that respects client-side-only**:
   - FastSurfer-LIT / BIBSnet run as one-shot Docker containers on Shako's MacBook (or a family workstation). Input: T1 NIfTI from the radiology dump. Output: segmentation masks (`aparc+aseg.nii.gz`, lesion mask), all written to `~/aleksandra-imaging/` locally.
   - Shako (or the wife, with a one-line instruction) drags the segmentation file into the viewer dropzone. The mask becomes the overlay layer.
   - The viewer never knows the file's provenance — it could be a Duke neuroradiologist's hand-segmentation or a FastSurfer-LIT auto-output. It just renders whatever NIfTI mask is dropped.
3. **When does the family see segmentations?** When Shako runs the pipeline and shares the output file. v9 may add a "saved files" affordance — but that affordance is *also* client-side-only (IndexedDB or File System Access API), not a server cache. v8 keeps the file picker honest: every session starts from a drag-drop. This is the privacy posture, not a missing feature.
4. **A future v9 nice-to-have**: a one-screen "Pipeline cheatsheet" link from the empty-state ("How do I generate a lesion mask?") routing to a `/system/imaging-pipeline` doc page that explains the FastSurfer-LIT command. **Doc page, not API.** Coordinated with v7-devops for the Docker recipe.

## 7.6 Channel-destination MRI viewer (deep-link from doctor session prep)

The clinician deep-link variant from the Family Handover PDF is a real future surface. Two design positions:

- **v8 does NOT ship `/clinician/brain`.** The clinician's first read is the Handover PDF + the citation-forward `/clinician/handover` route (IA §4.6). They do not need a viewer to evaluate the system; they need provenance.
- **v9 may ship a `/clinician/brain/[hash]` route as a hashed deep-link target** — but only if a real Duke / BMC clinician asks for it. The route would be the same NiiVue surface stripped of operator chrome: no BrainPanel, no operator top-nav, no view-mode tabs (the clinician picks colormap themselves), citation footer with PMID-style imaging citations ("BIBSnet 2024, T1 acquired DD-MMM-YYYY at BMC MRN 7616818"), and a single "Print to PDF" action. The deep-link hash carries no PHI — it's a session token. The MRI file itself is **still client-side only**: the clinician's browser loads from their local dump, not from our server. The hash gates the *route*, not the *data*.

The difference from the operator read is honest: clinicians do not get keyboard hotkeys (they are not living in this app), do not get the constitutional rules surface, and do not see the family-mode soft tone. They get the imaging, the labels, and the source. Same NiiVue volume, different chrome.

This is a v9 conversation. v8 does not pre-build the channel surface.

## 7.7 A11y for the 3D surface (responding to a11y principles)

The five principles from Concept Input 08 translate to the viewer as follows:

1. **Keyboard slice navigation** (responds to principle 4 — focus ring + keyboard-first). `↑` / `↓` step ±1 slice. `←` / `→` jump ±10. `Home` / `End` jump to slice 0 / max. `Tab` cycles between axial / coronal / sagittal panels. `L` toggles lesion overlay. `?` opens the per-route shortcuts cheatsheet (IA §4.5 pattern). Every slice-nav button has `:focus-visible` per a11y F9.
2. **ARIA live region** describes the current view. `<div role="status" aria-live="polite" className="sr-only">` reads "axial slice 45 of 90, lesion overlay on, viewing T1 acquired 2026-03-12". Updates on every slice change, throttled to 500ms to avoid screen-reader spam.
3. **Text-summary fallback** for users who cannot see the 3D at all. A visually-presented "view summary" sidebar (collapsed by default; `S` to expand) renders: "T1 NIfTI, 256×256×176 voxels, 1mm isotropic. Lesion mask: 3.2% of brain volume, distributed across periventricular white matter and bilateral parietal cortex." This summary is generated client-side from the loaded NIfTI header + mask voxel counts. No PHI, no cloud call.
4. **Reduced-motion compliance** (responds to principle 3 and agent canon rule 5). No auto-orbit camera (agent canon rule 10 already forbids this on first open; reduced-motion enforces it permanently). No shader animations. Smooth crosshair drag becomes instant snap. Loading shimmer becomes static "Loading volume..." text per motion §6.2 utility pattern.
5. **Color signal pairing** (responds to principle 2). The medical-red / medical-green legend at the bottom of the current placeholder is exactly the deuteranopia failure a11y B3 named. v8 viewer legend uses the `<ChartLegend />` primitive from dataviz §5.5: dot + lucide icon (`AlertCircle` for damaged, `Check` for preserved) + text label. Colormap for lesion mask is **viridis** (perceptually uniform across deuteranopia) — never `jet`, never rainbow.
6. **`lang` correctness on legend labels** (responds to principle 1). KA labels for "damaged" / "preserved" wrap in `<Lang code="ka">` so the screen reader pronounces them correctly.

## 7.8 Three 3D decisions Shako must make

1. **Install NiiVue + `@niivue/nvreact` in v8 and ship the MV viewer surface from §7.3?** *Recommendation: **YES.*** ~3-4 engineer-days, ~600KB lazy-loaded delta on the `/brain` route only, no R3F yet, no FreeBrowse fork yet, no upstream uncertainty. Risk: low. Refusal cost: the brain tab stays a placeholder for another version cycle, breaking the "hero surface" contract from the brief.

2. **Defer R3F + drei + postprocessing + FreeBrowse fork to v9?** *Recommendation: **YES.*** R3F earns its bundle when we have a designed anatomical-shell visual reason ("postprocessing depth-of-field on a frosted brain mesh that contextualizes the volume render") — and we do not yet. v8 ships NiiVue alone. v9 revisits with a sketch in hand. Refusal cost: v8 scope balloons from 4 days to ~3 weeks; risk of shipping it broken (R3F 9.6.x stable is fine but the postprocessing + shader work is the time sink).

3. **Treat segmentation overlays as an off-device → drag-drop UX in v8 (no in-app pipeline integration), with the pipeline-cheatsheet doc deferred to v9?** *Recommendation: **YES.*** v7-devops owns the FastSurfer-LIT + BIBSnet Docker recipe; the viewer just accepts whatever NIfTI mask is dropped. This honors the client-side-only rule absolutely and lets v8 ship without waiting on a Docker pipeline contract. Refusal cost: viewer ships with a "lesion overlay" affordance that has no input source, reading as broken to the operator who tries to use it.

---

**Hand-off note to design-director**: the load-bearing call is §7.4 — **commit NiiVue MV in v8, defer R3F to v9**. This unlocks the hero surface without exposing us to a 3-week R3F design sprint we are not staffed for. The three §7.8 decisions ladder cleanly: yes-yes-yes ships a real client-side viewer with one overlay type, full keyboard nav, viridis colormap, and zero cloud round-trips. The Family Handover clinician deep-link variant (§7.6) is a v9 conversation; do not pre-build. Coordinate with motion §6.2 (reduced-motion global must land first), a11y F9 (focus-visible global must land first), and IA §4.4 (BrainPanel collapsed-rail on `/brain`) — all three are prerequisites, not parallel work.
