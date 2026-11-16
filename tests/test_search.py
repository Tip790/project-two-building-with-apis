"""Tests for the RAWG search on the home page.

games.rawg.search_games is replaced with a fake, so no test calls RAWG.
"""

import re
from html import unescape

import pytest
from django.test import Client
from django.urls import reverse

from games import rawg

pytestmark = pytest.mark.django_db


def sample_search(results=None, page=1, has_next=False):
    """A hand-written page of RAWG search results, shaped like search_games()."""
    if results is None:
        results = [
            {
                "id": 3328,
                "name": "The Witcher 3: Wild Hunt",
                "released": "2015-05-18",
                "background_image": "https://media.rawg.io/media/games/witcher3.jpg",
            },
            {
                "id": 274755,
                "name": "Hades",
                "released": "2020-09-17",
                "background_image": None,
            },
        ]
    return {
        "results": results,
        "count": len(results),
        "page": page,
        "has_previous": page > 1,
        "has_next": has_next,
    }


@pytest.fixture
def fake_search(monkeypatch):
    """Replace search_games with a fake that records its calls."""
    calls = []

    def _fake(query, page=1):
        calls.append({"query": query, "page": page})
        return sample_search(page=page)

    monkeypatch.setattr(rawg, "search_games", _fake)
    return calls


def test_htmx_search_returns_only_the_results_fragment(client, fake_search):
    url = reverse("games:home") + "?q=witcher"

    full = client.get(url).content.decode()
    fragment = client.get(url, headers={"HX-Request": "true"}).content.decode()

    # The full page has the layout and the results.
    assert "<html" in full
    assert "Find a game. Track your backlog." in full
    assert "The Witcher 3: Wild Hunt" in full

    # The HTMX response has the same results and nothing else from the page.
    assert "The Witcher 3: Wild Hunt" in fragment
    assert "Hades" in fragment
    for page_part in ("<html", "<footer", "Find a game. Track your backlog."):
        assert page_part not in fragment


@pytest.mark.parametrize("htmx", [False, True], ids=["full-page", "htmx"])
def test_rawg_failure_shows_an_alert_where_results_go_not_an_error_page(
    monkeypatch, htmx
):
    def _failing_search(query, page=1):
        raise rawg.RawgError("RAWG took too long to respond. Try again in a moment.")

    monkeypatch.setattr(rawg, "search_games", _failing_search)
    # Report a crash as the 500 page a browser would get, not a test exception.
    browser = Client(raise_request_exception=False)
    headers = {"HX-Request": "true"} if htmx else {}

    response = browser.get(reverse("games:home") + "?q=witcher", headers=headers)

    assert response.status_code == 200
    html = response.content.decode()
    alert = re.search(
        r'<div role="alert" class="alert alert-error">.*?</div>', html, re.DOTALL
    )
    assert alert, "no error alert on the page"
    assert "RAWG took too long to respond. Try again in a moment." in alert.group(0)
    if not htmx:
        # On the full page the alert sits inside the results area.
        results_area = html.split('<div id="search-results">', 1)[1]
        assert alert.group(0) in results_area


def test_home_without_a_query_does_not_search(client, fake_search):
    response = client.get(reverse("games:home"))

    assert response.status_code == 200
    assert fake_search == []
    assert 'data-testid="search-result"' not in response.content.decode()


def test_full_page_search_shows_cover_name_and_release_year(client, fake_search):
    html = client.get(reverse("games:home") + "?q=witcher").content.decode()

    assert fake_search == [{"query": "witcher", "page": 1}]
    assert html.count('data-testid="search-result"') == 2
    assert "The Witcher 3: Wild Hunt" in html
    assert "2015" in html
    assert 'src="https://media.rawg.io/media/games/witcher3.jpg"' in html
    assert 'alt="Cover of The Witcher 3: Wild Hunt"' in html


def test_covers_fall_back_to_the_local_placeholder(client, fake_search):
    html = client.get(reverse("games:home") + "?q=witcher").content.decode()

    # Hades has no cover URL, so the placeholder is used directly.
    assert 'src="/static/img/cover-placeholder.svg"' in html
    # A cover URL that fails to load swaps to the placeholder in the browser.
    assert html.count("this.src='/static/img/cover-placeholder.svg'") == 2


@pytest.mark.parametrize("htmx", [False, True], ids=["full-page", "htmx"])
def test_paging_requests_the_page_and_links_both_ways(monkeypatch, client, htmx):
    calls = []

    def _fake(query, page=1):
        calls.append(page)
        return sample_search(page=page, has_next=True)

    monkeypatch.setattr(rawg, "search_games", _fake)
    headers = {"HX-Request": "true"} if htmx else {}

    html = client.get(
        reverse("games:home") + "?q=dark+souls&page=2", headers=headers
    ).content.decode()

    assert calls == [2]
    assert "Page 2" in html
    for page in (1, 3):
        link = f"?q=dark%20souls&amp;page={page}"
        assert f'href="{link}"' in html
        assert f'hx-get="{link}"' in html
    assert html.count('hx-target="#search-results"') >= 2


@pytest.mark.parametrize("bad_page", ["0", "-3", "abc", ""])
def test_a_bad_page_number_falls_back_to_page_one(client, fake_search, bad_page):
    client.get(reverse("games:home") + f"?q=witcher&page={bad_page}")

    assert fake_search == [{"query": "witcher", "page": 1}]


def test_search_results_credit_rawg_with_a_link(client, fake_search):
    fragment = client.get(
        reverse("games:home") + "?q=witcher", headers={"HX-Request": "true"}
    ).content.decode()

    assert "Search results from" in fragment
    assert 'href="https://rawg.io"' in fragment


def test_no_matches_shows_a_helpful_message(monkeypatch, client):
    monkeypatch.setattr(rawg, "search_games", lambda q, page=1: sample_search([]))

    html = client.get(reverse("games:home") + "?q=xyzzy").content.decode()

    assert "No games found for “xyzzy”" in html


def test_missing_rawg_key_shows_not_configured_alert(monkeypatch, settings, client):
    settings.RAWG_API_KEY = ""

    def _no_http(*args, **kwargs):
        raise AssertionError("RAWG must not be called without a key")

    monkeypatch.setattr(rawg.requests, "get", _no_http)

    response = client.get(reverse("games:home") + "?q=witcher")

    assert response.status_code == 200
    html = unescape(response.content.decode())
    assert 'class="alert alert-error"' in html
    assert "RAWG isn't configured" in html


def test_htmx_history_restore_gets_the_full_page(client, fake_search):
    html = client.get(
        reverse("games:home") + "?q=witcher",
        headers={"HX-Request": "true", "HX-History-Restore-Request": "true"},
    ).content.decode()

    assert "<html" in html
    assert "The Witcher 3: Wild Hunt" in html


def test_responses_vary_on_the_htmx_header(client, fake_search):
    response = client.get(reverse("games:home") + "?q=witcher")

    assert "HX-Request" in response.headers["Vary"]


def test_search_form_submits_normally_and_via_htmx(client):
    html = client.get(reverse("games:home")).content.decode()

    assert '<form action="/" method="get" role="search"' in html
    assert 'hx-get="/"' in html
    assert 'hx-target="#search-results"' in html
    assert 'hx-push-url="true"' in html
