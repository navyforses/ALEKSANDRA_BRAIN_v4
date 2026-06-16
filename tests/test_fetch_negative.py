from __future__ import annotations

import scripts.fetch_negative as fn


class _Resp:
    def __init__(self, rows):
        self.status_code = 200
        self._rows = rows
        self.text = ""

    def json(self):
        return self._rows


def test_list_active_therapies_accepts_bilingual_name_json(monkeypatch):
    monkeypatch.setattr(fn, "_supabase_creds", lambda: ("https://example.supabase.co", "k"))
    monkeypatch.setattr(fn, "_supabase_headers", lambda *a, **k: {})
    monkeypatch.setattr(
        fn.httpx,
        "get",
        lambda *a, **k: _Resp(
            [
                {"name": {"en": "Keppra", "ka": "კეპრა"}},
                {"name": "Vigabatrin"},
                {"name": {"ka": "კორდის სისხლი"}},
                {"name": {"en": ""}},
            ]
        ),
    )

    names = fn._list_active_therapies()
    assert names == ["Keppra", "Vigabatrin", "კორდის სისხლი"]
