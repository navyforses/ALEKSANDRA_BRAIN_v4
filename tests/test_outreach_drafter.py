from scripts.communicator import outreach_drafter as O


def test_count_drafts_today_fails_closed_when_db_unavailable(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(O.psycopg2, "connect", boom)

    assert O.count_drafts_today() == O.MAX_DAILY_DRAFTS


def test_gmail_scope_is_compose_only() -> None:
    assert O.GMAIL_SCOPES == ("https://www.googleapis.com/auth/gmail.compose",)
