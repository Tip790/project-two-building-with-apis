"""Tests for the one-click add-to-library action on search results.

games.rawg is replaced with fakes, so no test calls RAWG.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from games import rawg
from games.models import Game
from library.models import LibraryEntry

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}


@pytest.fixture
def stored_game():
    return Game.objects.create(
        rawg_id=3328, name="The Witcher 3: Wild Hunt", slug="the-witcher-3-wild-hunt"
    )


@pytest.fixture
def rawg_down(monkeypatch):
    """Make every RAWG detail request fail, recording the ids asked for."""
    calls = []

    def _failing_get_game(rawg_id):
        calls.append(rawg_id)
        raise rawg.RawgError("Could not reach RAWG. Check your internet connection.")

    monkeypatch.setattr(rawg, "get_game", _failing_get_game)
    return calls


def make_user(username):
    return get_user_model().objects.create_user(username, password="pw-for-tests")


def test_adding_a_game_someone_already_saved_works_while_rawg_is_down(
    client, stored_game, rawg_down
):
    LibraryEntry.objects.create(user=make_user("first_saver"), game=stored_game)
    second = make_user("second_saver")
    client.force_login(second)

    response = client.post(reverse("games:add"), {"rawg_id": 3328}, headers=HTMX)

    assert rawg_down == [], "RAWG must not be asked for a game that is stored"
    assert response.status_code == 200
    assert "In your library" in response.content.decode()
    entry = LibraryEntry.objects.get(user=second)
    assert entry.game == stored_game
    assert entry.status == LibraryEntry.Status.WANT_TO_PLAY
    assert Game.objects.count() == 1


@pytest.mark.parametrize("htmx", [True, False], ids=["htmx", "plain-post"])
def test_adding_a_game_twice_says_already_in_your_library(stored_game, htmx):
    user = make_user("collector")
    LibraryEntry.objects.create(user=user, game=stored_game)
    # Report a crash as the 500 page a browser would get, not a test exception.
    browser = Client(raise_request_exception=False)
    browser.force_login(user)

    response = browser.post(
        reverse("games:add"),
        {"rawg_id": 3328, "next": "/"},
        headers=HTMX if htmx else {},
        follow=not htmx,
    )

    assert response.status_code == 200
    assert "Already in your library" in response.content.decode()
    assert LibraryEntry.objects.filter(user=user).count() == 1


def detail_for(rawg_id):
    return {
        "id": rawg_id,
        "slug": "hades",
        "name": "Hades",
        "released": "2020-09-17",
        "background_image": None,
        "metacritic": 93,
        "description_raw": "Defy the god of the dead.",
        "genres": [{"id": 4, "name": "Action", "slug": "action"}],
        "platforms": [{"platform": {"id": 4, "name": "PC", "slug": "pc"}}],
    }


@pytest.fixture
def rawg_up(monkeypatch):
    calls = []

    def _fake_get_game(rawg_id):
        calls.append(rawg_id)
        return detail_for(rawg_id)

    monkeypatch.setattr(rawg, "get_game", _fake_get_game)
    return calls


def test_htmx_add_of_a_new_game_saves_it_and_swaps_the_button(client, rawg_up):
    user = make_user("player")
    client.force_login(user)

    response = client.post(reverse("games:add"), {"rawg_id": 274755}, headers=HTMX)

    assert rawg_up == [274755]
    html = response.content.decode()
    assert response.status_code == 200
    assert "In your library" in html
    assert "<html" not in html
    assert "Add to library" not in html
    entry = LibraryEntry.objects.get(user=user)
    assert entry.game.name == "Hades"
    assert entry.status == LibraryEntry.Status.WANT_TO_PLAY


def test_plain_post_add_redirects_back_with_a_success_message(client, rawg_up):
    client.force_login(make_user("player"))

    response = client.post(
        reverse("games:add"), {"rawg_id": 274755, "next": "/?q=hades"}
    )

    assert response.status_code == 302
    assert response.url == "/?q=hades"
    follow = client.get(reverse("library:my_library"))
    assert "Added Hades to your library." in follow.content.decode()


def test_plain_post_add_ignores_an_off_site_next_url(client, rawg_up):
    client.force_login(make_user("player"))

    response = client.post(
        reverse("games:add"),
        {"rawg_id": 274755, "next": "https://evil.example/"},
    )

    assert response.status_code == 302
    assert response.url == reverse("games:home")


@pytest.mark.parametrize("htmx", [True, False], ids=["htmx", "plain-post"])
def test_rawg_failure_for_an_unsaved_game_is_friendly_and_saves_nothing(
    client, rawg_down, htmx
):
    client.force_login(make_user("player"))

    response = client.post(
        reverse("games:add"),
        {"rawg_id": 274755, "next": "/"},
        headers=HTMX if htmx else {},
        follow=not htmx,
    )

    assert rawg_down == [274755]
    assert response.status_code == 200
    html = response.content.decode()
    assert "Couldn&#x27;t add this game: Could not reach RAWG." in html
    assert 'class="alert alert-error' in html
    assert Game.objects.count() == 0
    assert LibraryEntry.objects.count() == 0
    if htmx:
        # The button stays so the user can retry.
        assert "Try again" in html


def test_signed_out_visitors_cannot_post_an_add(client, rawg_up):
    response = client.post(reverse("games:add"), {"rawg_id": 274755})

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))
    assert rawg_up == []
    assert LibraryEntry.objects.count() == 0


def test_add_requires_post(client):
    client.force_login(make_user("player"))

    assert client.get(reverse("games:add")).status_code == 405


@pytest.mark.parametrize("bad_id", ["", "abc"])
def test_add_without_a_valid_rawg_id_is_a_bad_request(client, rawg_up, bad_id):
    client.force_login(make_user("player"))

    response = client.post(reverse("games:add"), {"rawg_id": bad_id})

    assert response.status_code == 400
    assert rawg_up == []


@pytest.fixture
def fake_search(monkeypatch):
    results = [
        {"id": 3328, "name": "The Witcher 3: Wild Hunt", "released": "2015-05-18"},
        {"id": 274755, "name": "Hades", "released": "2020-09-17"},
    ]
    monkeypatch.setattr(
        rawg,
        "search_games",
        lambda query, page=1: {
            "results": results,
            "count": 2,
            "page": 1,
            "has_previous": False,
            "has_next": False,
        },
    )


def test_signed_out_search_results_say_sign_in_to_add(client, fake_search):
    html = client.get(reverse("games:home") + "?q=game").content.decode()

    assert html.count("Sign in to add") == 2
    assert 'href="/accounts/login/?next=/%3Fq%3Dgame"' in html
    assert "Add to library" not in html


def test_signed_in_results_mark_saved_games_and_offer_add_for_the_rest(
    client, fake_search, stored_game
):
    user = make_user("player")
    LibraryEntry.objects.create(user=user, game=stored_game)
    # Someone else's entry must not count as being in this user's library.
    LibraryEntry.objects.create(
        user=make_user("other"),
        game=Game.objects.create(rawg_id=274755, name="Hades", slug="hades"),
    )
    client.force_login(user)

    html = client.get(reverse("games:home") + "?q=game", headers=HTMX).content.decode()

    assert html.count("In your library") == 1
    assert html.count("Add to library") == 1
    assert 'name="rawg_id" value="274755"' in html
    assert 'name="rawg_id" value="3328"' not in html
    assert 'hx-post="/games/add/"' in html
    assert 'action="/games/add/"' in html
    assert "Sign in to add" not in html
