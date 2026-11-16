"""Tests for the RAWG client in games/rawg.py.

requests.get is replaced with a fake, so these tests never contact RAWG
and never use up the API quota.
"""

import pytest
import requests

from games import rawg
from games.rawg import RawgError


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

    monkeypatch.setattr(rawg.requests, "get", _fake)
    return calls


@pytest.mark.parametrize("missing_key", ["", None])
def test_missing_key_says_rawg_is_not_configured_without_calling_rawg(
    monkeypatch, settings, missing_key
):
    settings.RAWG_API_KEY = missing_key
    calls = fake_get(monkeypatch, FakeResponse(json_data={"results": []}))

    with pytest.raises(RawgError, match="RAWG isn't configured"):
        rawg.search_games("hades")

    assert calls == []


def test_search_sends_key_title_and_page_and_parses_the_results(monkeypatch):
    calls = fake_get(
        monkeypatch,
        FakeResponse(
            json_data={
                "count": 30,
                "next": "https://api.rawg.io/api/games?page=3",
                "previous": "https://api.rawg.io/api/games?page=1",
                "results": [{"id": 1, "name": "Hades"}],
            }
        ),
    )

    search = rawg.search_games("hades", page=2)

    assert search == {
        "results": [{"id": 1, "name": "Hades"}],
        "count": 30,
        "page": 2,
        "has_previous": True,
        "has_next": True,
    }
    assert calls[0]["url"] == "https://api.rawg.io/api/games"
    assert calls[0]["params"] == {
        "key": "test-dummy-rawg-key",
        "search": "hades",
        "page": 2,
        "page_size": rawg.SEARCH_PAGE_SIZE,
    }
    assert calls[0]["timeout"] == rawg.TIMEOUT_SECONDS


def test_search_with_no_matches_has_no_results_and_no_more_pages(monkeypatch):
    fake_get(
        monkeypatch, FakeResponse(json_data={"count": 0, "next": None, "results": []})
    )

    search = rawg.search_games("xyzzy")

    assert search["results"] == []
    assert search["count"] == 0
    assert search["has_previous"] is False
    assert search["has_next"] is False


def test_get_game_fetches_the_detail_endpoint(monkeypatch):
    game = {"id": 3328, "name": "The Witcher 3: Wild Hunt", "description_raw": "..."}
    calls = fake_get(monkeypatch, FakeResponse(json_data=game))

    assert rawg.get_game(3328) == game
    assert calls[0]["url"] == "https://api.rawg.io/api/games/3328"
    assert calls[0]["params"] == {"key": "test-dummy-rawg-key"}


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, "rejected the site's API key"),
        (403, "rejected the site's API key"),
        (429, "rate limit"),
        (500, "error 500"),
        (503, "error 503"),
        (400, "error 400"),
    ],
)
def test_http_errors_become_friendly_messages(monkeypatch, status, expected):
    fake_get(monkeypatch, FakeResponse(status_code=status))
    with pytest.raises(RawgError, match=expected):
        rawg.search_games("hades")


def test_404_messages_fit_the_request(monkeypatch):
    fake_get(monkeypatch, FakeResponse(status_code=404))

    with pytest.raises(rawg.RawgNotFound, match="That game was not found on RAWG"):
        rawg.get_game(999999999)
    with pytest.raises(RawgError, match="no more results"):
        rawg.search_games("hades", page=50)


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        (requests.Timeout(), "took too long"),
        (requests.exceptions.SSLError(), "secure connection"),
        (requests.ConnectionError(), "Could not reach RAWG"),
        (requests.RequestException(), "request to RAWG failed"),
    ],
)
def test_network_failures_become_friendly_messages(monkeypatch, exception, expected):
    fake_get(monkeypatch, raises=exception)
    with pytest.raises(RawgError, match=expected):
        rawg.get_game(3328)


def test_invalid_json_becomes_friendly_message(monkeypatch):
    fake_get(monkeypatch, FakeResponse(bad_json=True))
    with pytest.raises(RawgError, match="unexpected response"):
        rawg.search_games("hades")
