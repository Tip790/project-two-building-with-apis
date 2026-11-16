"""Tests for the My Library page. It runs from local data only."""

from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from games import rawg
from games.models import Game, Genre, Platform
from library.models import LibraryEntry

pytestmark = pytest.mark.django_db


def make_user(username):
    return get_user_model().objects.create_user(username, password="pw-for-tests")


@pytest.fixture
def rawg_unreachable(monkeypatch):
    """Any attempt to reach RAWG fails the test."""

    def _no_rawg(*args, **kwargs):
        raise AssertionError("My Library must not call RAWG")

    monkeypatch.setattr(rawg.requests, "get", _no_rawg)
    monkeypatch.setattr(rawg, "get_game", _no_rawg)
    monkeypatch.setattr(rawg, "search_games", _no_rawg)


def test_signed_out_visitors_are_sent_to_login_and_back(client):
    make_user("player")

    response = client.get(reverse("library:my_library"))

    assert response.status_code == 302
    assert response.url == "/accounts/login/?next=/library/"

    login = client.post(
        response.url, {"username": "player", "password": "pw-for-tests"}
    )
    assert login.status_code == 302
    assert login.url == "/library/"


def test_logging_in_without_a_destination_opens_my_library(client):
    make_user("player")

    response = client.post(
        reverse("accounts:login"), {"username": "player", "password": "pw-for-tests"}
    )

    assert response.status_code == 302
    assert response.url == "/library/"


def test_signing_up_opens_my_library(client):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "newcomer",
            "password1": "a-long-test-passphrase-42",
            "password2": "a-long-test-passphrase-42",
        },
    )

    assert response.status_code == 302
    assert response.url == "/library/"


def test_shows_only_the_signed_in_users_entries_while_rawg_is_down(
    client, rawg_unreachable
):
    me, other = make_user("me"), make_user("other")
    hades = Game.objects.create(rawg_id=1, name="Hades", slug="hades")
    celeste = Game.objects.create(rawg_id=2, name="Celeste", slug="celeste")
    LibraryEntry.objects.create(user=me, game=hades)
    LibraryEntry.objects.create(user=other, game=celeste)
    client.force_login(me)

    response = client.get(reverse("library:my_library"))

    assert response.status_code == 200
    html = response.content.decode()
    assert html.count('data-testid="library-entry"') == 1
    assert "Hades" in html
    assert "Want to Play" in html
    assert "Celeste" not in html


def test_newest_entries_come_first(client):
    me = make_user("me")
    for rawg_id, name in [(1, "First Saved"), (2, "Second Saved")]:
        LibraryEntry.objects.create(
            user=me, game=Game.objects.create(rawg_id=rawg_id, name=name, slug=name)
        )
    client.force_login(me)

    html = client.get(reverse("library:my_library")).content.decode()

    assert html.index("Second Saved") < html.index("First Saved")


def test_empty_library_points_to_search(client):
    client.force_login(make_user("me"))

    html = client.get(reverse("library:my_library")).content.decode()

    assert "Your library is empty." in html
    assert 'href="/"' in html


def test_navbar_links_to_my_library(client):
    client.force_login(make_user("me"))

    html = client.get(reverse("games:home")).content.decode()

    assert 'href="/library/">My Library</a>' in html


class _PageLinks(HTMLParser):
    """Collects the href of each <a rel="prev"> and <a rel="next">."""

    def __init__(self):
        super().__init__()
        self.links = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("rel") in ("prev", "next"):
            self.links[attrs["rel"]] = attrs["href"]


def page_links(html):
    parser = _PageLinks()
    parser.feed(html)
    return parser.links


def test_pages_hold_12_entries_and_page_links_keep_filters_and_sort(client):
    me = make_user("me")
    for n in range(1, 14):  # 13 Playing entries: Game 01 … Game 13
        game = Game.objects.create(rawg_id=n, name=f"Game {n:02}", slug=f"game-{n}")
        LibraryEntry.objects.create(user=me, game=game, status="playing")
    dropped = Game.objects.create(rawg_id=99, name="Game 00 Dropped", slug="dropped")
    LibraryEntry.objects.create(user=me, game=dropped, status="dropped")
    client.force_login(me)

    first = client.get(
        reverse("library:my_library"), {"status": "playing", "sort": "name"}
    )
    html = first.content.decode()
    assert html.count('data-testid="library-entry"') == 12
    assert "Game 01" in html and "Game 12" in html
    assert "Game 13" not in html and "Game 00 Dropped" not in html

    links = page_links(html)
    assert "prev" not in links
    next_url = urlsplit(links["next"])
    assert parse_qs(next_url.query) == {
        "status": ["playing"],
        "sort": ["name"],
        "page": ["2"],
    }

    second = client.get(reverse("library:my_library") + "?" + next_url.query)
    html = second.content.decode()
    assert html.count('data-testid="library-entry"') == 1
    assert "Game 13" in html
    links = page_links(html)
    assert "next" not in links
    assert parse_qs(urlsplit(links["prev"]).query) == {
        "status": ["playing"],
        "sort": ["name"],
        "page": ["1"],
    }


@pytest.fixture
def browsable(client):
    """A signed-in user with a few varied entries, plus another user's entry."""
    me, other = make_user("me"), make_user("other")
    rpg = Genre.objects.create(rawg_id=5, name="RPG", slug="rpg")
    puzzle = Genre.objects.create(rawg_id=7, name="Puzzle", slug="puzzle")
    pc = Platform.objects.create(rawg_id=4, name="PC", slug="pc")
    for rawg_id, name, status, rating in [
        (1, "The Witcher 3", "completed", 5),
        (2, "Skyrim", "dropped", 2),
        (3, "Mass Effect", "playing", 4),
    ]:
        game = Game.objects.create(rawg_id=rawg_id, name=name, slug=name.lower())
        game.genres.add(rpg)
        game.platforms.add(pc)
        LibraryEntry.objects.create(
            user=me, game=game, status=status, rating=rating, platform=pc
        )
    portal = Game.objects.create(rawg_id=9, name="Portal", slug="portal")
    portal.genres.add(puzzle)
    LibraryEntry.objects.create(user=other, game=portal)
    client.force_login(me)
    return {"rpg": rpg, "pc": pc}


def entry_names(html):
    """The test games on the page, in the order they appear."""
    names = ("The Witcher 3", "Skyrim", "Mass Effect", "Portal")
    return sorted((name for name in names if name in html), key=html.index)


def test_htmx_returns_only_the_results_and_a_full_load_matches(client, browsable):
    params = {"genre": browsable["rpg"].pk, "min_rating": "3", "sort": "name"}
    url = reverse("library:my_library")

    fragment = client.get(url, params, headers={"HX-Request": "true"})
    full = client.get(url, params)

    assert fragment.status_code == full.status_code == 200
    fragment_html, full_html = fragment.content.decode(), full.content.decode()
    assert "<html" not in fragment_html
    assert "<form" not in fragment_html, "the filter bar is not swapped"
    assert 'id="library-results"' in full_html
    assert "<form" in full_html
    # Same entries, same order, whether swapped in or loaded directly.
    assert entry_names(fragment_html) == ["Mass Effect", "The Witcher 3"]
    assert entry_names(full_html) == ["Mass Effect", "The Witcher 3"]
    assert "HX-Request" in fragment["Vary"]
    assert "HX-Request" in full["Vary"]


def test_filter_bar_pushes_the_url_and_keeps_the_chosen_values(client, browsable):
    html = client.get(
        reverse("library:my_library"), {"q": "witch", "sort": "rating"}
    ).content.decode()

    assert 'hx-push-url="true"' in html
    assert 'hx-target="#library-results"' in html
    assert 'name="q" value="witch"' in html
    assert '<option value="rating" selected>' in html


def test_history_restore_gets_the_full_page(client, browsable):
    response = client.get(
        reverse("library:my_library"),
        headers={"HX-Request": "true", "HX-History-Restore-Request": "true"},
    )

    assert "<html" in response.content.decode()


def test_browsing_works_while_rawg_is_down(client, browsable, rawg_unreachable):
    response = client.get(
        reverse("library:my_library"),
        {"q": "e", "status": "completed", "platform": browsable["pc"].pk, "page": "1"},
    )

    assert response.status_code == 200
    assert entry_names(response.content.decode()) == ["The Witcher 3"]


@pytest.mark.parametrize(
    "params",
    [
        {"min_rating": "lots"},
        {"sort": "bogus"},
        {"genre": "99999"},
        {"status": "finished"},
        {"page": "999"},
        {"page": "first"},
    ],
    ids=["min-rating", "sort", "genre", "status", "page-too-high", "page-not-number"],
)
def test_bad_browsing_values_still_show_the_library(client, browsable, params):
    response = client.get(reverse("library:my_library"), params)

    assert response.status_code == 200
    assert response.content.decode().count('data-testid="library-entry"') >= 1


def test_no_matches_says_so_and_offers_to_clear(client, browsable):
    html = client.get(reverse("library:my_library"), {"q": "zelda"}).content.decode()

    assert "No games in your library match these filters." in html
    assert 'data-testid="library-entry"' not in html


def test_genre_choices_come_from_the_users_own_library(client, browsable):
    html = client.get(reverse("library:my_library")).content.decode()

    assert ">RPG</option>" in html
    assert ">Puzzle</option>" not in html, "another user's genre is not offered"
