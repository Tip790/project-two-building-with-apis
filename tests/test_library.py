"""Tests for the My Library page. It runs from local data only."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from games import rawg
from games.models import Game
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
