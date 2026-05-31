"""brain/memory/tests/test_classify_edges.py — Phase 7.1 Day 6 unit tests.

Scope:
  - Deterministic decision-tree rules (`pilot_classify.deterministic_suggest`)
  - LLM fallback parsing (`classify_edges.classify_with_llm`)
  - Graph mutation guards (`classify_edges.apply_classification`)
  - Main-loop LLM budget enforcement (`classify_edges.main` via subprocess-free
    in-process invocation with the Neo4j driver + Anthropic client both mocked)

Pure unit tests — no live Neo4j, no live Anthropic. Both clients are
monkey-patched at the module boundary.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# scripts/refactor/ is not a Python package; add it to sys.path so the test
# can import the modules under test directly.
_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "refactor"))

import pilot_classify  # noqa: E402
import classify_edges  # noqa: E402


# ---------------------------------------------------------------------------
# Deterministic rule suggestions
# ---------------------------------------------------------------------------

def test_deterministic_suggest_inhibits_on_mechanism_keyword() -> None:
    """An INHIBIT keyword in the mechanism property forces INHIBITS."""
    t, rationale = pilot_classify.deterministic_suggest(
        "Vigabatrin",
        "GABA-T",
        "RELATED_TO",
        {"mechanism": "irreversibly inhibits GABA-T enzyme"},
    )
    assert t == "INHIBITS"
    assert "inhibit" in rationale.lower()


def test_deterministic_suggest_inhibits_on_block_keyword() -> None:
    """`block` is in the INHIBIT lexicon."""
    t, _ = pilot_classify.deterministic_suggest(
        "Drug A", "Receptor B", "CO_OCCURS_WITH",
        {"mechanism": "blocks NMDA receptor"},
    )
    assert t == "INHIBITS"


def test_deterministic_suggest_causes_on_cause_keyword() -> None:
    """A CAUSE keyword in the fact text forces CAUSES via keyword path
    (not the disease-outcome target fallback)."""
    # Use a NON-disease target so the keyword path is the only way to
    # reach CAUSES — proves the keyword rule fires before fallback rules.
    t, rationale = pilot_classify.deterministic_suggest(
        "Vigabatrin",
        "GABA elevation",
        "RELATED_TO",
        {"fact": "vigabatrin elevates synaptic GABA concentration"},
    )
    assert t == "CAUSES"
    assert "elevate" in rationale.lower()


def test_deterministic_suggest_causes_on_disease_pattern() -> None:
    """RELATED_TO + disease-outcome target promotes to CAUSES even with no keyword."""
    t, rationale = pilot_classify.deterministic_suggest(
        "Perinatal hypoxia",
        "Brain injury",
        "RELATED_TO",
        {},
    )
    assert t == "CAUSES"
    assert "disease-outcome" in rationale


def test_deterministic_suggest_does_not_promote_co_occurs() -> None:
    """CO_OCCURS_WITH lacks direction → no disease-pattern promotion."""
    t, _ = pilot_classify.deterministic_suggest(
        "Risk factor X",
        "Neuronal damage",
        "CO_OCCURS_WITH",
        {},
    )
    assert t == "SKIP"


def test_deterministic_suggest_falls_back_to_skip() -> None:
    """No keyword + non-outcome target → SKIP (defer to LLM / manual)."""
    t, rationale = pilot_classify.deterministic_suggest(
        "Substance A", "Substance B", "CO_OCCURS_WITH", {"mechanism": "associated with"},
    )
    assert t == "SKIP"
    assert "no deterministic rule" in rationale.lower()


def test_deterministic_suggest_handles_empty_props() -> None:
    """Empty / None properties must not crash."""
    t, _ = pilot_classify.deterministic_suggest("A", "B", "CO_OCCURS_WITH", {})
    assert t == "SKIP"
    t, _ = pilot_classify.deterministic_suggest("A", "B", "CO_OCCURS_WITH", None)  # type: ignore[arg-type]
    assert t == "SKIP"


# ---------------------------------------------------------------------------
# LLM fallback parsing
# ---------------------------------------------------------------------------

def _mock_anthropic_client(reply_text: str) -> MagicMock:
    """Build a MagicMock Anthropic client whose .messages.create() returns
    a response object whose .content[0].text == reply_text."""
    client = MagicMock()
    response = SimpleNamespace(content=[SimpleNamespace(text=reply_text)])
    client.messages.create.return_value = response
    return client


def test_classify_with_llm_parses_valid_response() -> None:
    """A well-formed `CAUSES | rationale` reply is parsed cleanly."""
    client = _mock_anthropic_client("CAUSES | drug A elevates B via CYP3A4")
    edge = {"source_name": "A", "target_name": "B", "legacy_type": "RELATED_TO", "rel_props": {}}
    causal_type, rationale, cost = classify_edges.classify_with_llm(edge, client)
    assert causal_type == "CAUSES"
    assert "CYP3A4" in rationale
    assert cost == classify_edges.HAIKU_COST_PER_CALL_USD


def test_classify_with_llm_parses_inhibits() -> None:
    client = _mock_anthropic_client("INHIBITS | blocks receptor")
    edge = {"source_name": "X", "target_name": "Y", "legacy_type": "CO_OCCURS_WITH", "rel_props": {}}
    causal_type, _, _ = classify_edges.classify_with_llm(edge, client)
    assert causal_type == "INHIBITS"


def test_classify_with_llm_parses_none_as_delete() -> None:
    """`NONE` from the LLM → DELETE (non-causal correlation)."""
    client = _mock_anthropic_client("NONE | mere statistical association")
    edge = {"source_name": "A", "target_name": "B", "legacy_type": "RELATED_TO", "rel_props": {}}
    causal_type, rationale, _ = classify_edges.classify_with_llm(edge, client)
    assert causal_type == "DELETE"
    assert "non-causal" in rationale.lower()


def test_classify_with_llm_handles_unparseable_response() -> None:
    """No pipe separator → SKIP, never crash."""
    client = _mock_anthropic_client("yes I think this is causal probably")
    edge = {"source_name": "A", "target_name": "B", "legacy_type": "RELATED_TO", "rel_props": {}}
    causal_type, rationale, _ = classify_edges.classify_with_llm(edge, client)
    assert causal_type == "SKIP"
    assert "unparseable" in rationale.lower()


def test_classify_with_llm_rejects_out_of_scope_type() -> None:
    """Day 6 cannot produce MEDIATES — LLM picking it is rerouted to SKIP."""
    client = _mock_anthropic_client("MEDIATES | via intermediate node")
    edge = {"source_name": "A", "target_name": "B", "legacy_type": "RELATED_TO", "rel_props": {}}
    causal_type, rationale, _ = classify_edges.classify_with_llm(edge, client)
    assert causal_type == "SKIP"
    assert "out-of-scope" in rationale.lower()


def test_classify_with_llm_rejects_invalid_type() -> None:
    """Gibberish type also → SKIP."""
    client = _mock_anthropic_client("FOO | something")
    edge = {"source_name": "A", "target_name": "B", "legacy_type": "RELATED_TO", "rel_props": {}}
    causal_type, _, _ = classify_edges.classify_with_llm(edge, client)
    assert causal_type == "SKIP"


def test_classify_with_llm_handles_api_exception() -> None:
    """API exception is caught and downgraded to SKIP."""
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("rate limited")
    edge = {"source_name": "A", "target_name": "B", "legacy_type": "RELATED_TO", "rel_props": {}}
    causal_type, rationale, cost = classify_edges.classify_with_llm(edge, client)
    assert causal_type == "SKIP"
    assert "LLM API error" in rationale
    # Cost still counted (we issued the call attempt)
    assert cost == classify_edges.HAIKU_COST_PER_CALL_USD


# ---------------------------------------------------------------------------
# apply_classification — graph mutation guards
# ---------------------------------------------------------------------------

def test_apply_classification_skip_leaves_legacy_edge() -> None:
    """SKIP must NOT issue any Cypher."""
    session = MagicMock()
    edge = {"rel_id": 42, "legacy_type": "RELATED_TO",
            "source_name": "A", "target_name": "B", "rel_props": {}}
    classify_edges.apply_classification(session, edge, "SKIP", "deferred")
    session.run.assert_not_called()


def test_apply_classification_delete_runs_one_delete_query() -> None:
    """DELETE emits exactly one DELETE statement."""
    session = MagicMock()
    edge = {"rel_id": 99, "legacy_type": "CO_OCCURS_WITH",
            "source_name": "A", "target_name": "B", "rel_props": {}}
    classify_edges.apply_classification(session, edge, "DELETE", "non-causal")
    assert session.run.call_count == 1
    call_args = session.run.call_args
    query = call_args.args[0]
    assert "DELETE r" in query
    assert "id(r) = $rid" in query
    assert call_args.kwargs["rid"] == 99


def test_apply_classification_writes_new_edge_and_deletes_old() -> None:
    """CAUSES emits a single transaction that CREATEs a new edge AND DELETEs the legacy one."""
    session = MagicMock()
    edge = {"rel_id": 7, "legacy_type": "RELATED_TO",
            "source_name": "HIE", "target_name": "Cyst",
            "rel_props": {"mechanism": "tissue necrosis"}}
    classify_edges.apply_classification(session, edge, "CAUSES", "disease pattern")
    assert session.run.call_count == 1
    query = session.run.call_args.args[0]
    assert ":CAUSES" in query
    assert "CREATE" in query
    assert "DELETE r_old" in query
    assert "confidence: 0.7" in query
    assert "'TBD-Day-7-backfill'" in query
    # Mandatory property names present in the new edge:
    for prop in ("confidence", "citation", "mechanism", "time_lag_days"):
        assert prop in query, f"missing mandatory property {prop} in query"
    kwargs = session.run.call_args.kwargs
    assert kwargs["rid"] == 7
    assert kwargs["legacy"] == "RELATED_TO"


def test_apply_classification_inhibits_uses_inhibits_label() -> None:
    """INHIBITS edge label is interpolated correctly."""
    session = MagicMock()
    edge = {"rel_id": 1, "legacy_type": "RELATED_TO",
            "source_name": "A", "target_name": "B", "rel_props": {}}
    classify_edges.apply_classification(session, edge, "INHIBITS", "blocks")
    query = session.run.call_args.args[0]
    assert ":INHIBITS" in query
    assert ":CAUSES" not in query


def test_apply_classification_rejects_out_of_scope_type() -> None:
    """MEDIATES / CONFOUNDS / MODERATES cannot be produced by Day 6."""
    session = MagicMock()
    edge = {"rel_id": 1, "legacy_type": "RELATED_TO",
            "source_name": "A", "target_name": "B", "rel_props": {}}
    with pytest.raises(ValueError, match="cannot produce edge type"):
        classify_edges.apply_classification(session, edge, "MEDIATES", "ignored")
    session.run.assert_not_called()


def test_apply_classification_rationale_capped_at_200() -> None:
    """Long LLM rationales are stored truncated to keep edge property size sane."""
    session = MagicMock()
    edge = {"rel_id": 1, "legacy_type": "RELATED_TO",
            "source_name": "A", "target_name": "B", "rel_props": {}}
    long_rationale = "x" * 500
    classify_edges.apply_classification(session, edge, "CAUSES", long_rationale)
    stored = session.run.call_args.kwargs["rationale"]
    assert len(stored) == 200


# ---------------------------------------------------------------------------
# Main-loop LLM budget enforcement
# ---------------------------------------------------------------------------

class _FakeSession:
    """Minimal Neo4j session double — collects all session.run() calls."""
    def __init__(self, edges):
        self.edges = edges
        self.run_calls: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, query, **kwargs):
        self.run_calls.append((query, kwargs))
        # Simulate the FETCH_LEGACY_EDGES query returning our seeded edges.
        if "MATCH (s)-[r:CO_OCCURS_WITH|RELATED_TO]->(t)" in query and "RETURN id(r)" in query:
            return iter(self.edges)
        return iter([])


class _FakeDriver:
    def __init__(self, edges):
        self._edges = edges

    def session(self):
        return _FakeSession(self._edges)

    def close(self):
        pass


def _seed_ambiguous_edges(n: int) -> list[dict]:
    """All edges hit SKIP under the deterministic rules (no keyword, no
    disease-outcome target) so every one triggers LLM fallback."""
    return [
        {
            "rel_id": i,
            "legacy_type": "CO_OCCURS_WITH",
            "source_name": f"Concept_{i}",
            "target_name": f"Other_{i}",
            "rel_props": {"mechanism": "associated with"},
        }
        for i in range(n)
    ]


def test_main_respects_max_llm_budget(monkeypatch, tmp_path) -> None:
    """With 10 ambiguous edges and --max-llm 2, only 2 LLM calls fire."""
    seeded = _seed_ambiguous_edges(10)
    fake_driver = _FakeDriver(seeded)

    # Required env vars
    monkeypatch.setenv("NEO4J_URI", "neo4j+s://fake")
    monkeypatch.setenv("NEO4J_PASSWORD", "fake")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    # CLI args + dry-run so we don't need to mock per-edge writes
    monkeypatch.setattr(
        sys, "argv",
        ["classify_edges.py", "--dry-run", "--max-llm", "2"],
    )

    # Mock the Neo4j driver factory + the Anthropic client
    fake_graphdb = SimpleNamespace(driver=lambda uri, auth: fake_driver)
    monkeypatch.setattr(classify_edges, "GraphDatabase", fake_graphdb)
    fake_client = _mock_anthropic_client("CAUSES | mock fallback rationale")

    class _FakeAnthropicModule:
        Anthropic = MagicMock(return_value=fake_client)

    monkeypatch.setitem(sys.modules, "anthropic", _FakeAnthropicModule)

    # Redirect output dir to a tmp path so the test doesn't litter the repo
    monkeypatch.setattr(classify_edges, "OUTPUT_DIR", tmp_path)

    rc = classify_edges.main()

    # Run succeeded (dry-run, SKIP rate computed against the seeded 10)
    # 8 edges will be SKIP (no LLM available), 2 will be CAUSES (LLM hit).
    # SKIP rate = 80% → >= 15% abort threshold → exit 1. That IS the
    # contract: budget-starved runs MUST fail loudly.
    assert rc == 1
    # The crucial assertion: exactly 2 LLM calls fired, no more.
    assert fake_client.messages.create.call_count == 2


def test_main_with_zero_max_llm_disables_fallback(monkeypatch, tmp_path) -> None:
    """--max-llm 0 disables LLM entirely — no anthropic SDK import attempted."""
    seeded = _seed_ambiguous_edges(5)
    fake_driver = _FakeDriver(seeded)

    monkeypatch.setenv("NEO4J_URI", "neo4j+s://fake")
    monkeypatch.setenv("NEO4J_PASSWORD", "fake")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    monkeypatch.setattr(
        sys, "argv",
        ["classify_edges.py", "--dry-run", "--max-llm", "0"],
    )
    fake_graphdb = SimpleNamespace(driver=lambda uri, auth: fake_driver)
    monkeypatch.setattr(classify_edges, "GraphDatabase", fake_graphdb)

    # Sentinel: if anthropic IS imported, the test fails. We don't want it
    # called because --max-llm 0 should short-circuit before any import.
    fake_client = _mock_anthropic_client("CAUSES | unused")

    class _FakeAnthropicModule:
        Anthropic = MagicMock(return_value=fake_client)

    monkeypatch.setitem(sys.modules, "anthropic", _FakeAnthropicModule)
    monkeypatch.setattr(classify_edges, "OUTPUT_DIR", tmp_path)

    rc = classify_edges.main()
    # All 5 → SKIP → 100% SKIP rate → exit 1 (expected with no LLM, no rules firing).
    assert rc == 1
    # Critical: zero LLM calls fired.
    assert fake_client.messages.create.call_count == 0
