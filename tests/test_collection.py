from datetime import datetime

from src.matches.collect_matches import build_rows
from src.youtube.search_videos import period_for
from src.youtube.youtube_client import YouTubeClient
from src.youtube.youtube_client import _safe_error
from src.common import sanitize_metadata


def test_match_snapshot_is_exactly_ten_and_ordered():
    rows = build_rows()
    assert len(rows) == 10
    assert [r["match_date"] for r in rows] == sorted((r["match_date"] for r in rows), reverse=True)
    assert all(r["result_atletico"] in {"win", "draw", "loss"} for r in rows)


def test_period_uses_kickoff_time():
    kickoff = datetime.fromisoformat("2026-01-25T18:00:00-03:00")
    assert period_for(datetime.fromisoformat("2026-01-25T12:00:00-03:00"), kickoff) == "pre_game"
    assert period_for(datetime.fromisoformat("2026-01-25T20:00:00-03:00"), kickoff) == "post_game"


def test_credentials_are_redacted_from_errors_and_metadata():
    message = "https://example.test/api?part=x&key=secret-value; failure"
    assert "secret-value" not in _safe_error(message)
    assert "secret-value" not in str(sanitize_metadata({"errors": [message]}))


def test_page_iterator_follows_tokens_without_mutating_params():
    client = object.__new__(YouTubeClient)
    calls = []

    def fake_get(endpoint, **params):
        calls.append((endpoint, params))
        return {"nextPageToken": "next"} if len(calls) == 1 else {"items": []}

    client.get = fake_get
    assert len(list(client.pages("comments", parentId="p", maxResults=100))) == 2
    assert "pageToken" not in calls[0][1]
    assert calls[1][1]["pageToken"] == "next"
