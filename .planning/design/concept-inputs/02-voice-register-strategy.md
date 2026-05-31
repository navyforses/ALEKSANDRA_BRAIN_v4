# Concept Input 02 — Voice + Register Strategy

**Author**: design-content-bilingual
**Date**: 2026-05-25
**Wave**: 1 (parallel with ux-researcher, systems-lead, a11y)
**Status**: input for design-director synthesis

---

## 2.1 Voice audit across current surfaces

The 143-key dictionary samples cleanly into three register zones, and one of them is leaking into the others.

**On-register surfaces** (audience matches voice):

- `Home.*` and `Home.subtitle` (`viewer/messages/en.json:71`) reads as warm-narrative: "Continuous research ingestion, memory, and hypothesis validation for Aleksandra Jincharadze. This surface is for family workflow visibility; clinical action stays with physicians." Plain language. Clinical-authority sentence is unambiguous. This is the voice the rest of the family surfaces should match.
- `Therapies.subtitle` (`en.json:237`) holds the line: "Read-only status view of treatments, programs, and research candidates. This page is operational context, not clinical advice." Notice the explicit not-clinical-advice disclaimer. Reuse this pattern.
- `Manager.input.askPlaceholder` (`en.json:166`) "Ask BRAIN or drop file..." is correct for Shako-register: direct, verb-first, no decoration.

**Drifted surfaces** (developer voice bleeding into family-facing namespaces):

- `Dashboard.rlsSmoke` (`en.json:51`): "RLS smoke: covered by Phase 2.5 verifier C.2." This is a developer log line rendered as user copy. The wife persona has no model for "RLS", "smoke", or "verifier C.2". Cut entirely from the family view, or move behind a Shako-only audit panel.
- `Hypotheses.emptySupportingPapers` (`en.json:85`): "No supporting papers linked yet. The pipeline cites these in ai_reasoning; `backfill_supporting_papers.py` populates the UUID array." Three register violations in one string: file path, internal table name, UUID. This is empty-state copy seen by the wife.
- `Twin.mockNotice` and `Drift.mockNotice` and `Causal.mockNotice` and `Simulate.mockNotice`: all four open with "Structural build:" followed by "Backend wiring lands in a follow-up sprint." This is sprint-planning vocabulary rendered to the family. v8 should replace with a single neutral phrase like "Preview view. Live data lands next."
- `Home.phaseLabel` / `Dashboard.phaseLabel` / 8 other `phaseLabel` keys: internal phase numbers ("Phase II.5C", "Phase 7.6 Digital Twin") are exposed as navigational chrome. Phase numbers carry meaning for Shako and zero meaning for the wife. v8 candidate: render `phaseLabel` only in Shako-mode shells.
- `Audit.title` "Audit log" plus `Audit.subtitle` "Every BRAIN-applied action, newest first. Undo works for the last {undoLimit} actions within {undoWindow}." This is correct for Shako. The problem is it shares chrome with family surfaces; the answer is route segmentation, not a copy rewrite.

**Net finding**: the drift is not random. It clusters on surfaces written during engineering sprints without a copy pass. The fix is a register tag per namespace in `en.json` (family / shako / clinician) and a verifier that fails CI when a family-tagged key contains a banned-token list (file extensions, table names, UUIDs, phase numbers, the words "verifier" / "pipeline" / "backfill" / "wiring" / "sprint").

## 2.2 "Unknown potential" at month 9 — re-read

At month 0 the phrase did real work. It named a stance against a default prognosis. At month 9 it risks reading as evasive because the system now has data: 5 confirmed hypotheses, 12 therapy candidates, a posterior over 13 dimensions. The wife who reads weekly is no longer asking "is there hope at all"; she is asking "what changed this week, and on what evidence".

The phrase still belongs in 3 places: the landing hero, the Family Handover preamble, and any empty state where the system genuinely has no evidence to show yet. The phrase does not belong on dashboards that have real numbers to render. Replacing it with concrete evidence is more hopeful than restating the stance.

Proposed v8 voice rule: "Unknown potential" is reserved for moments where the alternative is "limited outcomes". Where the alternative is "no update", say what changed.

KA direction note for v7-i18n: the existing rendering as `უცნობი პოტენციალი` is on-register and not loop-prone. Keep.

## 2.3 Telegram weekly digest preview — the load-bearing string

This is the most-seen surface in the product. It appears in a notification banner before the wife opens the app. Phone lockscreens truncate around 140 chars EN and ~120 chars KA. Three constraints stack: warmth, length, no clinical content.

Proposed shape (3 lines, all optional after line 1):

```
Line 1 (always): "Weekly brief ready. {n} new findings this week."
Line 2 (if any): "Highlight: {one-sentence headline, no jargon}"
Line 3 (always, short): "Open to read together."
```

Voice rules for this surface specifically:
- Never lead with a number that is zero. If `n = 0`, lead with "This week was quiet. {one observation we did make}."
- Never include "BRAIN", "agent", "hypothesis", "Sonnet", or any model name. The system stays invisible; the finding is the subject.
- Never include a clinician name, MRN, or trial code in the preview. Those live behind the open.
- Closing line is invitational not transactional. "Open to read together" not "Tap to open" not "View report".

KA direction for v7-i18n: target ≤ 120 chars per line in Mkhedruli. The phrase "ერთად წავიკითხოთ" carries the invitational register without imperative tone (D-05 safe — not an order, it is a suggestion in first-person plural). Anti-loop hint: avoid `ცამეტი` if the number lands on 13; render as `13`.

## 2.4 Provenance in family copy — how to cite without citation-heavy

The clinician needs PubMed IDs visible. The wife needs to trust the finding without reading the citation. Both are true at once. The pattern that works:

**Single-line provenance tag**, never inline citation. Three forms:

1. `Based on 5 papers` (wife — count + verb, no IDs visible)
2. `5 papers · 3 trials · last updated {date}` (wife — slightly denser, still no IDs)
3. `[PMID 38274510](link), [PMID 38911223](link), and 3 others` (clinician — IDs primary)

The wife sees forms 1 and 2 by default. A single "show sources" affordance reveals form 3 inline. The provenance lives in the chrome around the finding, not woven through the sentence.

Two anti-patterns to forbid:

- Mid-sentence citations in family-facing copy ("Vigabatrin (Smith et al., 2023; Jones et al., 2024) reduces seizure frequency..."). The wife reads through the citations as noise; trust drops.
- "AI-generated" disclaimers in copy. The wife already knows. Repeating it implies the system is apologizing. Provenance reads as confidence; disclaimer reads as hedging.

The Hypotheses surface already has `curatorActionBody` (`en.json:80`) doing this well: "Confirmation marks the evidence link curated for research follow-up. It is not a clinical treatment recommendation." Reuse this scaffolding verbatim where the audience is mixed.

## 2.5 v8 voice strategy in 3 sentences

Tag every namespace with one of three registers — family / shako / clinician — and have CI fail when family-tagged copy contains developer tokens. Replace internal phase labels and sprint vocabulary with neutral status phrases on every family-facing surface, while keeping Shako's audit-mode shells dense and jargon-rich on purpose. Reserve "Unknown potential" for the landing hero and genuinely empty states; everywhere the system has data, render the data, because concrete evidence is the most hopeful voice the product has.
