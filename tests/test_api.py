"""Tests for the REST API: tokens, the requester's entries, and pagination.

Tokens here are placeholders made for the test database only. No test
calls RAWG.
"""

import re
from datetime import date
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from games import rawg
from games.models import Game, Genre, Platform
from library.models import LibraryEntry

pytestmark = pytest.mark.django_db

PLACEHOLDER_TOKENS = {
    "alice": "placeholder-token-alice-000000000000000",
    "bob": "placeholder-token-bob-00000000000000000",
}


def make_user(username, **fields):
    return get_user_model().objects.create_user(
        username, password="pw-for-tests", **fields
    )


def make_game(rawg_id, name):
    return Game.objects.create(rawg_id=rawg_id, name=name, slug=name.lower())


def token_client(user):
    token = Token.objects.create(user=user, key=PLACEHOLDER_TOKENS[user.username])
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


def session_client(user):
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture
def two_libraries():
    """Alice and Bob each have entries; Bob's library is Public."""
    alice = make_user("alice")
    bob = make_user("bob", library_is_public=True)
    hades, celeste, tunic = (
        make_game(1, "Hades"),
        make_game(2, "Celeste"),
        make_game(3, "Tunic"),
    )
    return {
        "alice": alice,
        "bob": bob,
        "alice_entries": [
            LibraryEntry.objects.create(user=alice, game=hades),
            LibraryEntry.objects.create(user=alice, game=celeste),
        ],
        "bob_entry": LibraryEntry.objects.create(user=bob, game=tunic),
    }


def entries_url(pk=None):
    if pk is None:
        return reverse("api:entry-list")
    return reverse("api:entry-detail", args=[pk])


@pytest.mark.parametrize("make_client", [token_client, session_client])
def test_api_returns_only_the_requesters_own_entries(two_libraries, make_client):
    alice = two_libraries["alice"]
    own_ids = {entry.pk for entry in two_libraries["alice_entries"]}
    bobs_pk = two_libraries["bob_entry"].pk
    client = make_client(alice)

    # The list holds Alice's entries and nothing of Bob's.
    response = client.get(entries_url())
    assert response.status_code == 200
    assert {entry["id"] for entry in response.json()["results"]} == own_ids

    # Each of her own entries can be retrieved.
    for pk in own_ids:
        assert client.get(entries_url(pk)).status_code == 200

    # Bob's entry is a 404 to her, even though his library is Public.
    assert client.get(entries_url(bobs_pk)).status_code == 404


def test_regenerating_the_token_on_settings_retires_the_old_one(two_libraries):
    alice = two_libraries["alice"]
    old_client = token_client(alice)
    assert old_client.get(entries_url()).status_code == 200

    browser = session_client(alice)
    response = browser.post(reverse("accounts:regenerate_token"))
    assert response.status_code == 302

    # The old token is refused from the very next request.
    assert old_client.get(entries_url()).status_code == 401

    # A different token replaced it, and it works.
    new_key = Token.objects.get(user=alice).key
    assert new_key != PLACEHOLDER_TOKENS["alice"]
    new_client = APIClient()
    new_client.credentials(HTTP_AUTHORIZATION=f"Token {new_key}")
    assert new_client.get(entries_url()).status_code == 200


def test_api_lists_12_per_page_with_a_rawg_attribution():
    alice = make_user("alice")
    all_ids = {
        LibraryEntry.objects.create(user=alice, game=make_game(n, f"Game {n:02}")).pk
        for n in range(13)
    }
    client = token_client(alice)

    first = client.get(entries_url()).json()
    second = client.get(entries_url(), {"page": 2}).json()

    assert first["count"] == second["count"] == 13
    assert len(first["results"]) == 12
    assert len(second["results"]) == 1
    assert first["previous"] is None and first["next"].endswith("?page=2")
    assert second["next"] is None and second["previous"] is not None
    ids = [entry["id"] for entry in first["results"] + second["results"]]
    assert set(ids) == all_ids and len(ids) == 13

    # Every page credits RAWG with a link, like the website's footer.
    for page in (first, second):
        assert page.get("attribution") == {
            "text": "Game data from RAWG.",
            "name": "RAWG",
            "url": "https://rawg.io",
        }


@pytest.mark.parametrize("url_pk", ["list", "own", "other"])
def test_api_rejects_requests_without_credentials(two_libraries, url_pk):
    pk = {
        "list": None,
        "own": two_libraries["alice_entries"][0].pk,
        "other": two_libraries["bob_entry"].pk,
    }[url_pk]

    response = APIClient().get(entries_url(pk))

    # Only DRF's error message comes back, never entry data.
    assert response.status_code == 401
    assert set(response.json()) == {"detail"}


# --- Token endpoint ---------------------------------------------------------


def test_token_endpoint_returns_the_users_token_for_valid_credentials():
    alice = make_user("alice")

    response = APIClient().post(
        reverse("api:token"), {"username": "alice", "password": "pw-for-tests"}
    )

    assert response.status_code == 200
    key = response.json()["token"]
    assert key == Token.objects.get(user=alice).key
    # The token it hands out works on the API.
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {key}")
    assert client.get(entries_url()).status_code == 200


@pytest.mark.parametrize(
    "credentials",
    [
        {"username": "alice", "password": "wrong-password"},
        {"username": "nobody", "password": "pw-for-tests"},
        {"username": "alice"},
    ],
    ids=["wrong-password", "unknown-user", "no-password"],
)
def test_token_endpoint_rejects_invalid_credentials(credentials):
    make_user("alice")

    response = APIClient().post(reverse("api:token"), credentials)

    assert response.status_code == 400
    assert "token" not in response.json()
    assert not Token.objects.exists()


def test_a_made_up_token_is_rejected():
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token placeholder-token-not-a-real-one")
    assert client.get(entries_url()).status_code == 401


# --- Settings page ----------------------------------------------------------


def test_settings_shows_the_users_token_and_a_regenerate_button(client):
    alice = make_user("alice")
    client.force_login(alice)

    html = client.get(reverse("accounts:settings")).content.decode()

    key = Token.objects.get(user=alice).key
    assert f'value="{key}"' in html
    assert reverse("accounts:regenerate_token") in html
    assert "Regenerate token" in html
    # Visiting again shows the same token, not a new one.
    client.get(reverse("accounts:settings"))
    assert Token.objects.get(user=alice).key == key


def test_settings_shows_the_new_token_after_regenerating(client):
    alice = make_user("alice")
    client.force_login(alice)
    client.get(reverse("accounts:settings"))
    old_key = Token.objects.get(user=alice).key

    response = client.post(reverse("accounts:regenerate_token"), follow=True)

    new_key = Token.objects.get(user=alice).key
    html = response.content.decode()
    assert new_key != old_key
    assert f'value="{new_key}"' in html
    assert old_key not in html
    assert "The old token no longer works." in html


def test_regenerating_needs_sign_in_and_a_post(client):
    url = reverse("accounts:regenerate_token")
    response = client.post(url)
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))
    assert not Token.objects.exists()

    client.force_login(make_user("alice"))
    assert client.get(url).status_code == 405
    assert not Token.objects.exists()


# --- Entry data -------------------------------------------------------------


def test_each_entry_nests_its_game_details_with_genres_and_platforms():
    alice = make_user("alice")
    game = Game.objects.create(
        rawg_id=3328,
        name="The Witcher 3: Wild Hunt",
        slug="the-witcher-3-wild-hunt",
        background_image="https://media.rawg.io/media/games/witcher3.jpg",
        released=date(2015, 5, 18),
        metacritic=92,
        description="An open-world RPG.",
    )
    rpg = Genre.objects.create(rawg_id=5, name="RPG", slug="role-playing-games-rpg")
    pc = Platform.objects.create(rawg_id=4, name="PC", slug="pc")
    ps4 = Platform.objects.create(rawg_id=18, name="PlayStation 4", slug="ps4")
    game.genres.add(rpg)
    game.platforms.add(pc, ps4)
    entry = LibraryEntry.objects.create(
        user=alice,
        game=game,
        status=LibraryEntry.Status.COMPLETED,
        rating=5,
        hours_played=Decimal("120.5"),
        platform=pc,
        notes="Best side quests.",
    )
    pc_data = {"id": pc.pk, "rawg_id": 4, "name": "PC", "slug": "pc"}
    ps4_data = {"id": ps4.pk, "rawg_id": 18, "name": "PlayStation 4", "slug": "ps4"}

    data = token_client(alice).get(entries_url(entry.pk)).json()

    assert data["status"] == "completed"
    assert data["rating"] == 5
    assert data["hours_played"] == "120.5"
    assert data["notes"] == "Best side quests."
    assert data["platform"] == pc_data
    assert data["game"] == {
        "rawg_id": 3328,
        "name": "The Witcher 3: Wild Hunt",
        "slug": "the-witcher-3-wild-hunt",
        "background_image": "https://media.rawg.io/media/games/witcher3.jpg",
        "released": "2015-05-18",
        "metacritic": 92,
        "description": "An open-world RPG.",
        "genres": [{"rawg_id": 5, "name": "RPG", "slug": "role-playing-games-rpg"}],
        "platforms": [pc_data, ps4_data],
    }


def test_the_api_is_read_only_until_phase_8():
    alice = make_user("alice")
    entry = LibraryEntry.objects.create(user=alice, game=make_game(1, "Hades"))
    client = token_client(alice)

    assert client.post(entries_url(), {"rawg_id": 2}).status_code == 405
    assert client.patch(entries_url(entry.pk), {"rating": 5}).status_code == 405
    assert client.delete(entries_url(entry.pk)).status_code == 405
    assert LibraryEntry.objects.filter(pk=entry.pk, rating=None).exists()


def test_api_reads_work_while_rawg_is_down(monkeypatch):
    def _no_rawg(*args, **kwargs):
        raise AssertionError("The API must not call RAWG to read entries")

    monkeypatch.setattr(rawg.requests, "get", _no_rawg)
    monkeypatch.setattr(rawg, "get_game", _no_rawg)
    monkeypatch.setattr(rawg, "search_games", _no_rawg)
    alice = make_user("alice")
    entry = LibraryEntry.objects.create(user=alice, game=make_game(1, "Hades"))
    client = token_client(alice)

    assert client.get(entries_url()).status_code == 200
    assert client.get(entries_url(entry.pk)).json()["game"]["name"] == "Hades"


def test_signed_in_users_can_browse_the_api_in_the_browser(client):
    alice = make_user("alice")
    LibraryEntry.objects.create(user=alice, game=make_game(1, "Hades"))
    client.force_login(alice)

    response = client.get(entries_url(), headers={"accept": "text/html"})

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    assert "Hades" in response.content.decode()


# --- Same browsing as the website -------------------------------------------


@pytest.fixture
def browsable_library():
    """A library varied enough for every filter and sort to matter."""
    alice = make_user("alice")
    action = Genre.objects.create(rawg_id=4, name="Action", slug="action")
    puzzle = Genre.objects.create(rawg_id=7, name="Puzzle", slug="puzzle")
    pc = Platform.objects.create(rawg_id=4, name="PC", slug="pc")
    switch = Platform.objects.create(rawg_id=7, name="Nintendo Switch", slug="switch")
    rows = [
        ("Hades", action, pc, "completed", 5, "80", date(2020, 9, 17)),
        ("Hollow Knight", action, switch, "playing", 4, "30", date(2017, 2, 24)),
        ("Portal 2", puzzle, pc, "completed", 5, "12", date(2011, 4, 18)),
        ("Baba Is You", puzzle, switch, "dropped", 3, None, date(2019, 3, 13)),
        ("Celeste", action, pc, "want_to_play", None, None, None),
    ]
    for n, (name, genre, platform, status, rating, hours, released) in enumerate(rows):
        game = Game.objects.create(
            rawg_id=100 + n, name=name, slug=f"game-{n}", released=released
        )
        game.genres.add(genre)
        game.platforms.add(platform)
        LibraryEntry.objects.create(
            user=alice,
            game=game,
            status=status,
            rating=rating,
            hours_played=Decimal(hours) if hours else None,
            platform=platform,
        )
    return {"user": alice, "action": action, "pc": pc, "switch": switch}


def website_entry_ids(html):
    """Entry pks in the order My Library's cards show them."""
    return [int(pk) for pk in re.findall(r'href="/library/(\d+)/"', html)]


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"q": "hol"},
        {"status": "completed"},
        {"genre": "action"},
        {"platform": "switch"},
        {"min_rating": "4"},
        {"sort": "name"},
        {"sort": "rating"},
        {"sort": "hours"},
        {"sort": "released"},
        {"genre": "action", "platform": "pc", "sort": "name"},
    ],
    ids=lambda params: "&".join(f"{k}={v}" for k, v in params.items()) or "default",
)
def test_api_and_website_give_the_same_results(client, browsable_library, params):
    # Genre and platform go by primary key, as on the website.
    params = {
        key: str(browsable_library[value].pk) if key in {"genre", "platform"} else value
        for key, value in params.items()
    }
    alice = browsable_library["user"]
    client.force_login(alice)

    html = client.get(reverse("library:my_library"), params).content.decode()
    api = token_client(alice).get(entries_url(), params).json()

    expected = website_entry_ids(html)
    assert expected, "the website shows something to compare against"
    assert [entry["id"] for entry in api["results"]] == expected
    assert api["count"] == len(expected)


def test_api_page_links_keep_the_active_filters_and_sort():
    alice = make_user("alice")
    for n in range(15):
        LibraryEntry.objects.create(
            user=alice, game=make_game(n, f"Game {n:02}"), rating=5 if n % 4 else 2
        )
    client = token_client(alice)

    first = client.get(entries_url(), {"min_rating": 5, "sort": "name"}).json()

    assert first["count"] == 11
    assert [entry["game"]["name"] for entry in first["results"]] == [
        f"Game {n:02}" for n in range(15) if n % 4
    ]
    # Only 11 match, so there's one page.
    assert first["next"] is None

    for n in range(15, 30):
        LibraryEntry.objects.create(
            user=alice, game=make_game(n, f"Game {n:02}"), rating=5
        )
    first = client.get(entries_url(), {"min_rating": 5, "sort": "name"}).json()
    query = parse_qs(urlsplit(first["next"]).query)
    assert query == {"min_rating": ["5"], "sort": ["name"], "page": ["2"]}
    second = client.get(first["next"]).json()
    assert second["previous"] is not None
    assert {e["id"] for e in first["results"]}.isdisjoint(
        e["id"] for e in second["results"]
    )


@pytest.mark.parametrize(
    "params",
    [{"status": "palying"}, {"sort": "price"}, {"min_rating": "lots"}],
    ids=["status", "sort", "min_rating"],
)
def test_api_reports_invalid_browsing_values(browsable_library, params):
    response = token_client(browsable_library["user"]).get(entries_url(), params)

    assert response.status_code == 400
    assert set(response.json()) == set(params)


def test_api_page_past_the_end_is_a_404():
    alice = make_user("alice")
    LibraryEntry.objects.create(user=alice, game=make_game(1, "Hades"))

    response = token_client(alice).get(entries_url(), {"page": 9})

    assert response.status_code == 404
