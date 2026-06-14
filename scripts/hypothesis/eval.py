"""scripts/hypothesis/eval.py — COG-6 offline hypothesis-quality harness.

Scores a list of hypothesis dicts (the shape got_pipeline emits / inserts) against
deterministic quality gates, with NO live LLM and NO database. Use it to catch a
regression in generation output before it reaches the hypotheses table, or to audit
an exported batch.

Gates (per hypothesis):
  - hypothesis_type in the schema's CHECK set
  - confidence_level in the schema's CHECK set
  - novelty_score / feasibility_score are numeric and within [0, 1]
  - title + description carry no PHI (family-visible fields; flagged, see COG-4 —
    this is a quality signal, the generator itself never drops a lead)
  - when a PaperIndex is supplied, any cited supporting_source_ids resolve to a
    papers.id (an unresolved citation is a provenance gap)

evaluate() never raises; it returns a scorecard. A hypothesis with zero flags is ok.

Usage:
    python -m scripts.hypothesis.eval --dry-run            # built-in fixture (self-test)
    python -m scripts.hypothesis.eval --file hyps.json     # evaluate an exported batch
Exit code: 0 if every hypothesis passes, 1 if any is flagged (or the file is unusable).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from brain.common.phi_guard import PHIDetectedError, assert_no_phi
from scripts.hypothesis.backfill_supporting_papers import PaperIndex, _resolve_papers

# Mirror of the Phase 0 hypotheses CHECK-constraint sets (also in got_pipeline). Kept
# local so this offline harness never imports the neo4j-bearing generation module.
ALLOWED_HYPOTHESIS_TYPES = {
    "drug_repurposing",
    "pathway_target",
    "combination_therapy",
    "timing_optimization",
    "cross_disease_inference",
    "plasticity_mechanism",
    "biomarker_discovery",
    "technology_application",
    "rehabilitation_innovation",
    "other",
}
ALLOWED_CONFIDENCE = {"high", "moderate", "low", "very_low"}


def _score_numeric(h: dict, field: str, flags: list[str]) -> None:
    value = h.get(field)
    try:
        fv = float(value)
    except (TypeError, ValueError):
        flags.append(f"nonnumeric_{field}")
        return
    if not (0.0 <= fv <= 1.0):
        flags.append(f"out_of_range_{field}:{fv}")


def evaluate(hypotheses: list[dict], *, paper_index: PaperIndex | None = None) -> dict:
    """Return a scorecard {total, ok, flagged, results:[{index,title,flags,ok}]}."""
    results: list[dict[str, Any]] = []
    for i, h in enumerate(hypotheses):
        flags: list[str] = []

        if h.get("hypothesis_type") not in ALLOWED_HYPOTHESIS_TYPES:
            flags.append(f"bad_type:{h.get('hypothesis_type')!r}")
        if h.get("confidence_level") not in ALLOWED_CONFIDENCE:
            flags.append(f"bad_confidence:{h.get('confidence_level')!r}")

        _score_numeric(h, "novelty_score", flags)
        _score_numeric(h, "feasibility_score", flags)

        visible = f"{h.get('title') or ''}\n{h.get('description') or ''}"
        try:
            assert_no_phi(visible, source=f"hypothesis[{i}]")
        except PHIDetectedError:
            flags.append("phi_in_visible_fields")

        if paper_index is not None:
            sources = h.get("supporting_source_ids") or []
            if sources:
                resolved = _resolve_papers(
                    paper_index, {"supporting_source_ids": sources}
                )
                if not resolved:
                    flags.append("unresolved_supporting_papers")

        results.append(
            {
                "index": i,
                "title": (h.get("title") or "")[:80],
                "flags": flags,
                "ok": not flags,
            }
        )

    ok = sum(1 for r in results if r["ok"])
    return {
        "total": len(results),
        "ok": ok,
        "flagged": len(results) - ok,
        "results": results,
    }


# A deliberately mixed self-test batch: one clean row + one that trips three gates,
# so --dry-run demonstrates the harness catches problems (and exits 1).
_DRY_RUN_FIXTURE: list[dict] = [
    {
        "title": "Erythropoietin as an adjunct to therapeutic hypothermia in HIE",
        "description": "EPO may extend the neuroprotective window after perinatal asphyxia.",
        "hypothesis_type": "drug_repurposing",
        "confidence_level": "moderate",
        "novelty_score": 0.6,
        "feasibility_score": 0.7,
        "supporting_source_ids": [],
    },
    {
        "title": "Bad row with PHI: contact Dr. Kurtzberg",
        "description": "Unknown mechanism.",
        "hypothesis_type": "totally_made_up_type",
        "confidence_level": "certain",
        "novelty_score": 2.5,
        "feasibility_score": "n/a",
        "supporting_source_ids": [],
    },
]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Offline hypothesis-quality harness.")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="evaluate the built-in mixed fixture (self-test; exits 1 by design)",
    )
    ap.add_argument(
        "--file", default=None, help="path to a JSON list of hypothesis dicts"
    )
    args = ap.parse_args(argv)

    if args.file:
        try:
            data = json.loads(open(args.file, encoding="utf-8").read())
        except (OSError, json.JSONDecodeError) as e:
            sys.stderr.write(f"[eval] cannot read {args.file}: {e}\n")
            return 1
        if not isinstance(data, list):
            sys.stderr.write("[eval] file must contain a JSON list of hypotheses\n")
            return 1
        hypotheses = data
    elif args.dry_run:
        hypotheses = _DRY_RUN_FIXTURE
    else:
        ap.print_help()
        return 1

    card = evaluate(hypotheses)
    print(
        f"[eval] {card['ok']}/{card['total']} ok, {card['flagged']} flagged",
        flush=True,
    )
    for r in card["results"]:
        if not r["ok"]:
            print(f"  FLAG [{r['index']}] {r['title']!r}: {r['flags']}")
    return 0 if card["flagged"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
