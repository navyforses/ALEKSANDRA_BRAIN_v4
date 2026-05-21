"""
tests/test_compose_bilingual.py — Phase 6 plan 06-09 Task 1.

Verifies scripts.communicator.bilingual.compose_bilingual:
  Test 1 — mocked Anthropic returning tool_use yields {'en', 'ka'}
  Test 2 — mocked Anthropic with no tool_use raises RuntimeError
  Test 3 — BILINGUAL_TOOL schema integrity (strict=True, additionalProperties=False)
  Test 4 — default model is claude-sonnet-4-5

Run:
    .venv/Scripts/python.exe -X utf8 -m pytest tests/test_compose_bilingual.py -v
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# Ensure we don't accidentally hit the test-mode fallback during the mocked-client
# tests (we want to assert the real code path through the Anthropic call).
os.environ["ANTHROPIC_API_KEY"] = "test-key-for-pytest"
os.environ.pop("BILINGUAL_TEST_MODE", None)

from scripts.communicator.bilingual import (  # noqa: E402
    BILINGUAL_TOOL,
    DEFAULT_MODEL,
    compose_bilingual,
)


def _tool_use_block(inputs: dict) -> SimpleNamespace:
    """Build a fake Anthropic tool_use content block."""
    return SimpleNamespace(
        type="tool_use",
        name="compose_bilingual",
        input=inputs,
    )


def _text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _mock_response(content_blocks: list) -> SimpleNamespace:
    return SimpleNamespace(content=content_blocks)


@pytest.fixture(autouse=True)
def _stub_budget(monkeypatch):
    """Patch check_daily_budget to a no-op so the unit tests don't need
    Supabase credentials.
    """
    monkeypatch.setattr(
        "scripts.communicator.bilingual.check_daily_budget",
        lambda *args, **kwargs: (0.0, False),
    )


def test_1_tool_use_block_returns_en_ka_pair():
    """A mocked Anthropic client returning a tool_use block yields the pair."""
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        [_tool_use_block({"en": "Hello", "ka": "გამარჯობა"})]
    )

    result = compose_bilingual("draft a greeting", client=client)

    assert result == {"en": "Hello", "ka": "გამარჯობა"}
    # Verify the call shape — strict tool_use + tool_choice forcing this tool
    call_kwargs = client.messages.create.call_args.kwargs
    assert call_kwargs["tools"] == [BILINGUAL_TOOL]
    assert call_kwargs["tool_choice"] == {
        "type": "tool",
        "name": "compose_bilingual",
    }
    assert call_kwargs["messages"] == [{"role": "user", "content": "draft a greeting"}]


def test_2_no_tool_use_block_raises_runtime_error():
    """If the model returns only text blocks, raise RuntimeError."""
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        [_text_block("the model forgot to use the tool")]
    )

    with pytest.raises(RuntimeError, match="no tool_use"):
        compose_bilingual("draft something", client=client)


def test_3_bilingual_tool_schema_integrity():
    """The exported BILINGUAL_TOOL constant honors the strict-tool-use contract."""
    assert BILINGUAL_TOOL["strict"] is True
    assert BILINGUAL_TOOL["input_schema"]["additionalProperties"] is False
    assert BILINGUAL_TOOL["input_schema"]["required"] == ["en", "ka"]
    assert BILINGUAL_TOOL["name"] == "compose_bilingual"
    # Both keys must be string type
    props = BILINGUAL_TOOL["input_schema"]["properties"]
    assert props["en"]["type"] == "string"
    assert props["ka"]["type"] == "string"


def test_4_default_model_is_sonnet_4_5():
    """Calling without explicit model uses claude-sonnet-4-5 per CLAUDE.md."""
    assert DEFAULT_MODEL == "claude-sonnet-4-5"

    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        [_tool_use_block({"en": "x", "ka": "ხ"})]
    )

    compose_bilingual("anything", client=client)

    call_kwargs = client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-5"
