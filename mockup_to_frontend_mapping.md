# Mockup-to-Frontend Mapping

## Primary correction from user

The current prototype should be treated as insufficient because it mostly reuses the existing application frame. The next implementation must visibly reproduce the generated image concepts as actual frontend screens.

## Layout targets

| Route | Mockup Source | Required visual architecture |
| --- | --- | --- |
| `/[locale]` | Concept B | Family-safe light portal with left sidebar feel, soft hero, journey stepper, family cards, right assistant style sections, and explicit safety banner. |
| `/[locale]/dashboard` | Concept A | Dark clinical command center with navy shell, glowing brain/network hero, KPI strip, evidence-to-therapy pipeline, chart panels, clinical timeline, and assistant-like contextual card. |
| `/[locale]/hypotheses` | Concept A | Dark validation workflow with status cards, confidence/progress markers, evidence review cards, and validation queue. |
| `/[locale]/therapies` | Concept A | Dark therapy candidate board with evidence strength, candidate phases, clinical impact, safety gates, and pipeline cards. |
| `/[locale]/brain` | Concept C | Immersive digital twin lab with left MRI layer controls, large central brain visualization, right evidence links, hypothesis inspector, and bottom timeline scrubber. |
| `/[locale]/timeline` | Concept B + C | Calm longitudinal journey plus clinical scan/event timeline, not a plain list. |

## Component gaps to implement

The current `PrototypeKit` is mostly light-card based. It needs additional mockup-faithful components: `CommandCenterShell`, `DarkGlassPanel`, `MockupSidebar`, `AssistantPanel`, `NeuralHeroVisual`, `CommandMetricCard`, `ResearchPipelineStage`, `FamilyJourneyStepper`, `FamilyPortalShell`, `DigitalTwinLab`, `MriLayerControl`, `EvidenceLinkCard`, and `ScanTimelineScrubber`.

## Global shell issue

The locale layout currently forces a generic top header and a fixed 65/35 content-plus-old-BrainPanel layout. This conflicts with all three mockups. The implementation should let pages own the full-screen mockup layout and convert the persistent right panel into a mockup-style assistant or hide it from prototype pages.
