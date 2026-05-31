"""Phase 7.4 Day 7 — telegram_flow tests."""

from __future__ import annotations

import pytest

from brain.active import telegram_flow
from brain.active.rate_limiter import reset_dry_run_state
from brain.active.telegram_flow import OutboundQuestion, send_question


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    reset_dry_run_state()
    telegram_flow.EMERGENCY_FREEZE = False
    yield
    telegram_flow.EMERGENCY_FREEZE = False
    reset_dry_run_state()


def _make_q(week: str = "2026-W45", dim: str = "head_control_seconds") -> OutboundQuestion:
    return OutboundQuestion(
        dim_name=dim,
        observation_type="tummy_time_timer",
        text_ka="ერთი წუთით მუცელზე დააწვინე და დაითვალე წამები.",
        text_en="One minute on tummy; count seconds.",
        eig_nats=0.3,
        wife_chat_id="0",
        week_iso=week,
        dry_run=True,
        expected_format="integer_seconds",
    )


def test_dry_run_returns_dry_run_status() -> None:
    res = send_question(_make_q())
    assert res["status"] == "dry_run"
    assert res["rendered_text"]
    assert res["dim_name"] == "head_control_seconds"


def test_fourth_send_is_rate_limited() -> None:
    """Verifier check 6 / 9: 4th send in same week returns rate_limited."""
    week = "2026-W45"
    for i in range(3):
        res = send_question(_make_q(week=week))
        assert res["status"] == "dry_run", f"send {i} got {res}"
    res4 = send_question(_make_q(week=week))
    assert res4["status"] == "rate_limited"
    assert res4["weekly_cap"] == 3
    assert res4["current_count"] == 3


def test_emergency_freeze_blocks_all_sends() -> None:
    telegram_flow.EMERGENCY_FREEZE = True
    res = send_question(_make_q())
    assert res["status"] == "frozen"


def test_outbound_question_pydantic_validated() -> None:
    with pytest.raises(Exception):
        OutboundQuestion(
            dim_name="",  # min_length=1 -> fail
            observation_type="x",
            text_ka="a",
            text_en="b",
            eig_nats=0.1,
            wife_chat_id="0",
            week_iso="2026-W45",
            expected_format="boolean",
        )


def test_live_mode_missing_dependency_handled(monkeypatch) -> None:
    # Force the import attempt to fail by shadowing the modules.
    import sys
    saved_communicator = sys.modules.pop("scripts.communicator.telegram_sender", None)
    saved_manager = sys.modules.pop("scripts.manager.telegram_sender", None)

    # Monkey-patch _try_import_live_sender to return None.
    monkeypatch.setattr(telegram_flow, "_try_import_live_sender", lambda: None)

    q = _make_q()
    q = q.model_copy(update={"dry_run": False})
    res = send_question(q)
    assert res["status"] == "missing_dependency"
    assert "telegram_sender" in res["error"]

    # Restore
    if saved_communicator is not None:
        sys.modules["scripts.communicator.telegram_sender"] = saved_communicator
    if saved_manager is not None:
        sys.modules["scripts.manager.telegram_sender"] = saved_manager


def test_dry_run_still_increments_rate_counter() -> None:
    from brain.active.rate_limiter import weekly_sent_count

    week = "2026-W47"
    assert weekly_sent_count(week) == 0
    send_question(_make_q(week=week))
    assert weekly_sent_count(week) == 1
