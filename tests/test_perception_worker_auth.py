"""tests/test_perception_worker_auth.py — OPS-7 opt-in worker auth.

Offline: builds a _Handler via __new__ (no socket / no server), fakes .headers
as a dict, and monkeypatches the module-level _json_response so nothing touches
the wire. Pins the load-bearing backward-compat contract: when NO token env is
set the gate stays open (today's behavior), and enforcement turns on the moment
any of the historical token names is set.
"""

from __future__ import annotations

import scripts.perception_worker as pw

_TOKEN_ENVS = (
    "PERCEPTION_WORKER_AUTH_TOKEN",
    "PHASE5_WORKER_AUTH_TOKEN",
    "PHASE4_WORKER_AUTH_TOKEN",
)


def _handler(headers: dict[str, str]):
    h = pw._Handler.__new__(pw._Handler)  # bypass BaseHTTPRequestHandler socket init
    h.headers = headers
    return h


def _clear(monkeypatch):
    for name in _TOKEN_ENVS:
        monkeypatch.delenv(name, raising=False)


def _capture_json(monkeypatch):
    seen: list[tuple] = []
    monkeypatch.setattr(
        pw, "_json_response", lambda handler, code, body: seen.append((code, body))
    )
    return seen


def test_open_relay_when_no_token(monkeypatch):
    # Load-bearing: with no secret configured the gate allows + never 401s.
    _clear(monkeypatch)
    seen = _capture_json(monkeypatch)
    assert _handler({})._require_auth() is True
    assert seen == []


def test_phase5_match_allows(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("PHASE5_WORKER_AUTH_TOKEN", "secret123")
    _capture_json(monkeypatch)
    assert _handler({"X-Auth-Token": "secret123"})._require_auth() is True


def test_wrong_token_401(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("PHASE5_WORKER_AUTH_TOKEN", "secret123")
    seen = _capture_json(monkeypatch)
    assert _handler({"X-Auth-Token": "nope"})._require_auth() is False
    assert seen and seen[0][0] == 401


def test_missing_header_401(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("PHASE5_WORKER_AUTH_TOKEN", "secret123")
    seen = _capture_json(monkeypatch)
    assert _handler({})._require_auth() is False
    assert seen and seen[0][0] == 401


def test_perception_name_precedence(monkeypatch):
    # The new canonical name is honored on its own.
    _clear(monkeypatch)
    monkeypatch.setenv("PERCEPTION_WORKER_AUTH_TOKEN", "p-secret")
    _capture_json(monkeypatch)
    assert _handler({"X-Auth-Token": "p-secret"})._require_auth() is True


def test_phase4_legacy_honored(monkeypatch):
    # The oldest name still works so the PHASE4 digest workflow never breaks.
    _clear(monkeypatch)
    monkeypatch.setenv("PHASE4_WORKER_AUTH_TOKEN", "legacy")
    _capture_json(monkeypatch)
    assert _handler({"X-Auth-Token": "legacy"})._require_auth() is True
