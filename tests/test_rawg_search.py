"""Tests for scripts/rawg_search.py.

requests.get is replaced with a fake, so these tests never contact RAWG
and never use up the API quota.
"""

import pytest
import rawg_search
import requests
from rawg_search import (
    RawgError,
    format_details,
    format_result_line,
    get_game,
    search_games,
)


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, bad_json=False):
        self.status_code = status_code
        self._json_data = json_data
        self._bad_json = bad_json

    def json(self):
        if self._bad_json:
            raise ValueError("not JSON")
        return self._json_data


def fake_get(monkeypatch, response=None, raises=None):
    """Make requests.get return `response` (or raise `raises`). Returns the call log."""
    calls = []

    def _fake(url, params=None, timeout=None):
        calls.append({"url": url, "params": params, "timeout": timeout})
        if raises:
            raise raises
        return response

    monkeypatch.setattr(rawg_search.requests, "get", _fake)
    return calls


def test_search_sends_key_and_query_and_returns_results(monkeypatch):
    calls = fake_get(
        monkeypatch, FakeResponse(json_data={"results": [{"id": 1, "name": "Hades"}]})
    )

    games = search_games("hades", "test-key")

    assert games == [{"id": 1, "name": "Hades"}]
    assert calls[0]["url"].endswith("/games")
    assert calls[0]["params"]["key"] == "test-key"
    assert calls[0]["params"]["search"] == "hades"
    assert calls[0]["timeout"] == rawg_search.TIMEOUT_SECONDS


def test_search_with_no_matches_returns_empty_list(monkeypatch):
    fake_get(monkeypatch, FakeResponse(json_data={"count": 0, "results": []}))
    assert search_games("xyzzy", "test-key") == []


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, "rejected the API key"),
        (403, "rejected the API key"),
        (404, "not found"),
        (429, "Rate limit"),
        (503, "error 503"),
    ],
)
def test_http_errors_become_friendly_messages(monkeypatch, status, expected):
    fake_get(monkeypatch, FakeResponse(status_code=status))
    with pytest.raises(RawgError, match=expected):
        get_game(123, "test-key")


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        (requests.Timeout(), "too long"),
        (requests.ConnectionError(), "internet connection"),
    ],
)
def test_network_failures_become_friendly_messages(monkeypatch, exception, expected):
    fake_get(monkeypatch, raises=exception)
    with pytest.raises(RawgError, match=expected):
        search_games("hades", "test-key")


def test_invalid_json_becomes_friendly_message(monkeypatch):
    fake_get(monkeypatch, FakeResponse(bad_json=True))
    with pytest.raises(RawgError, match="unexpected response"):
        search_games("hades", "test-key")


def test_formatting_handles_full_and_missing_fields():
    game = {
        "name": "Hades",
        "released": "2020-09-17",
        "rating": 4.4,
        "platforms": [
            {"platform": {"name": "PC"}},
            {"platform": {"name": "Nintendo Switch"}},
        ],
        "slug": "hades-2",
    }
    line = format_result_line(1, game)
    assert "Hades (2020)" in line
    assert "★ 4.4" in line
    assert "PC, Nintendo Switch" in line

    details = format_details(game)
    assert "Metacritic:  n/a" in details  # missing field
    assert "https://rawg.io/games/hades-2" in details
    assert rawg_search.ATTRIBUTION in details
