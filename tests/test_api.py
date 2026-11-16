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
from library.forms import EntryForm
from library.models import LibraryEntry

pytestmark = pytest.mark.django_db

PLACEHOLDER_TOKENS = {
    "alice": "placeholder-token-alice-000000000000000",
    "bob": "placeholder-token-bob-00000000000000000",
    "carol": "placeholder-token-carol-000000000000000",
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


# --- Writes (Phase 8) -------------------------------------------------------


def sample_rawg_detail(rawg_id=3328):
    """A hand-written RAWG /games/<id> response, trimmed to the fields we use."""
    return {
        "id": rawg_id,
        "slug": "the-witcher-3-wild-hunt",
        "name": "The Witcher 3: Wild Hunt",
        "released": "2015-05-18",
        "background_image": "https://media.rawg.io/media/games/witcher3.jpg",
        "metacritic": 92,
        "description_raw": "An open-world RPG.",
        "genres": [{"id": 5, "name": "RPG", "slug": "role-playing-games-rpg"}],
        "platforms": [{"platform": {"id": 4, "name": "PC", "slug": "pc"}}],
    }


def test_api_create_uses_the_shared_save_flow(monkeypatch):
    rawg_is_up = False
    calls = []

    def _fake_get_game(rawg_id):
        calls.append(rawg_id)
        if not rawg_is_up:
            raise rawg.RawgError("RAWG is having problems right now. Try again later.")
        return sample_rawg_detail(rawg_id)

    monkeypatch.setattr(rawg, "get_game", _fake_get_game)
    client = token_client(make_user("alice"))
    payload = {
        "rawg_id": 3328,
        "status": "playing",
        "rating": 4,
        "hours_played": "12.5",
        "notes": "Started in Velen.",
    }

    # RAWG is down and the game isn't stored: a 503 with the friendly
    # message, and nothing is saved.
    response = client.post(entries_url(), payload, format="json")
    assert response.status_code == 503
    assert response.json() == {
        "detail": "RAWG is having problems right now. Try again later."
    }
    assert not Game.objects.exists()
    assert not LibraryEntry.objects.exists()

    # Once RAWG is back, the same request fetches the game once and saves
    # the entry with the client's own fields.
    rawg_is_up = True
    calls.clear()
    response = client.post(entries_url(), payload, format="json")
    assert response.status_code == 201
    assert calls == [3328]
    entry = LibraryEntry.objects.get()
    assert entry.game.name == "The Witcher 3: Wild Hunt"
    assert list(entry.game.platforms.values_list("name", flat=True)) == ["PC"]
    assert (entry.status, entry.rating, entry.hours_played, entry.notes) == (
        "playing",
        4,
        Decimal("12.5"),
        "Started in Velen.",
    )
    data = response.json()
    assert data["id"] == entry.pk
    assert data["game"]["rawg_id"] == 3328
    assert data["status"] == "playing"


@pytest.mark.parametrize("action", ["create", "update"])
@pytest.mark.parametrize(
    "field, bad_value",
    [
        ("rating", 0),
        ("rating", 6),
        ("hours_played", "-1"),
        ("hours_played", "10001"),
        ("platform", "xbox"),
    ],
    ids=["rating-0", "rating-6", "hours-negative", "hours-over-cap", "platform"],
)
def test_api_rejects_bad_values_with_the_website_forms_messages(
    action, field, bad_value
):
    alice = make_user("alice")
    pc = Platform.objects.create(rawg_id=4, name="PC", slug="pc")
    xbox = Platform.objects.create(rawg_id=1, name="Xbox One", slug="xbox-one")
    hades, celeste = make_game(1, "Hades"), make_game(2, "Celeste")
    hades.platforms.add(pc)
    celeste.platforms.add(pc)
    existing = LibraryEntry.objects.create(user=alice, game=hades)
    if bad_value == "xbox":
        bad_value = xbox.pk  # a real platform, but neither game is on it
    client = token_client(alice)

    # What the website's edit form says about this value.
    target = existing if action == "update" else LibraryEntry(user=alice, game=celeste)
    form = EntryForm({"status": "want_to_play", field: bad_value}, instance=target)
    assert not form.is_valid()
    website_messages = form.errors[field]

    if action == "create":
        payload = {"rawg_id": celeste.rawg_id, field: bad_value}
        response = client.post(entries_url(), payload, format="json")
    else:
        payload = {field: bad_value}
        response = client.patch(entries_url(existing.pk), payload, format="json")

    assert response.status_code == 400
    assert response.json() == {field: website_messages}
    # Nothing was saved.
    assert LibraryEntry.objects.count() == 1
    existing.refresh_from_db()
    assert (existing.rating, existing.hours_played, existing.platform) == (
        None,
        None,
        None,
    )


# --- Shared library endpoint ------------------------------------------------


def user_entries_url(username):
    return reverse("api:user-entries", args=[username])


def test_shared_library_endpoint_follows_the_websites_visibility_rule():
    alice = make_user("alice")  # Private, the default
    bob = make_user("bob", library_is_public=True)
    carol = make_user("carol")
    alices_ids = {
        LibraryEntry.objects.create(user=alice, game=make_game(n, f"A{n}")).pk
        for n in (1, 2)
    }
    bobs_ids = {LibraryEntry.objects.create(user=bob, game=make_game(3, "B3")).pk}
    anonymous, as_carol = APIClient(), token_client(carol)

    def ids(response):
        return {entry["id"] for entry in response.json()["results"]}

    # A Public library is visible to anyone, signed in or not.
    for client in (anonymous, as_carol):
        response = client.get(user_entries_url("bob"))
        assert response.status_code == 200
        assert ids(response) == bobs_ids

    # Owners always see their own library, Private or not.
    response = token_client(alice).get(user_entries_url("alice"))
    assert response.status_code == 200
    assert ids(response) == alices_ids

    # To everyone else, a Private library and a username that doesn't exist
    # get the very same 404.
    for client in (anonymous, as_carol):
        private = client.get(user_entries_url("alice"))
        missing = client.get(user_entries_url("nobody"))
        assert private.status_code == missing.status_code == 404
        assert private.content == missing.content

    # Switching to Private on Settings hides the library from the next request.
    browser = session_client(bob)
    assert browser.post(reverse("accounts:settings"), {}).status_code == 302
    for client in (anonymous, as_carol):
        response = client.get(user_entries_url("bob"))
        assert response.status_code == 404
        assert response.content == client.get(user_entries_url("nobody")).content


# --- Writes: the rest -------------------------------------------------------


def _rawg_must_not_be_called(*args, **kwargs):
    raise AssertionError("RAWG must not be called for a stored game")


def test_api_create_reuses_a_stored_game_without_calling_rawg(monkeypatch):
    monkeypatch.setattr(rawg, "get_game", _rawg_must_not_be_called)
    pc = Platform.objects.create(rawg_id=4, name="PC", slug="pc")
    hades = make_game(1, "Hades")
    hades.platforms.add(pc)
    bob = make_user("bob")
    LibraryEntry.objects.create(user=bob, game=hades)
    client = token_client(make_user("alice"))

    response = client.post(
        entries_url(), {"rawg_id": 1, "platform": pc.pk}, format="json"
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "want_to_play"  # the default
    assert data["platform"] == {"id": pc.pk, "rawg_id": 4, "name": "PC", "slug": "pc"}
    assert Game.objects.count() == 1
    assert LibraryEntry.objects.filter(user__username="alice", game=hades).exists()


def test_api_create_needs_a_rawg_id():
    response = token_client(make_user("alice")).post(
        entries_url(), {"status": "playing"}, format="json"
    )

    assert response.status_code == 400
    assert response.json() == {"rawg_id": ["This field is required."]}
    assert not LibraryEntry.objects.exists()


def test_api_create_of_a_game_rawg_does_not_have_is_a_400(monkeypatch):
    def _not_on_rawg(rawg_id):
        raise rawg.RawgNotFound("That game was not found on RAWG.")

    monkeypatch.setattr(rawg, "get_game", _not_on_rawg)

    response = token_client(make_user("alice")).post(
        entries_url(), {"rawg_id": 999999999}, format="json"
    )

    assert response.status_code == 400
    assert response.json() == {"rawg_id": ["That game was not found on RAWG."]}
    assert not Game.objects.exists()


def test_api_duplicate_create_says_already_in_your_library(monkeypatch):
    monkeypatch.setattr(rawg, "get_game", _rawg_must_not_be_called)
    alice = make_user("alice")
    entry = LibraryEntry.objects.create(
        user=alice, game=make_game(1, "Hades"), rating=5
    )

    response = token_client(alice).post(
        entries_url(), {"rawg_id": 1, "rating": 2}, format="json"
    )

    assert response.status_code == 400
    assert response.json() == {"rawg_id": ["Already in your library."]}
    assert LibraryEntry.objects.count() == 1
    entry.refresh_from_db()
    assert entry.rating == 5


def test_api_duplicate_create_that_loses_a_race_is_still_a_400(monkeypatch):
    # Another request adds the game between validation and the insert.
    from library import serializers as entry_serializers
    from library.services import AlreadyInLibrary

    alice = make_user("alice")
    hades = make_game(1, "Hades")

    def _lose_the_race(user, rawg_id, **fields):
        raise AlreadyInLibrary(LibraryEntry.objects.create(user=user, game=hades))

    monkeypatch.setattr(entry_serializers, "add_to_library", _lose_the_race)

    response = token_client(alice).post(entries_url(), {"rawg_id": 1}, format="json")

    assert response.status_code == 400
    assert response.json() == {"rawg_id": ["Already in your library."]}


def test_api_full_and_partial_updates_save_the_owners_fields():
    alice = make_user("alice")
    pc = Platform.objects.create(rawg_id=4, name="PC", slug="pc")
    hades = make_game(1, "Hades")
    hades.platforms.add(pc)
    entry = LibraryEntry.objects.create(user=alice, game=hades, notes="Old")
    client = token_client(alice)

    response = client.put(
        entries_url(entry.pk),
        {
            "status": "completed",
            "rating": 5,
            "hours_played": "80",
            "platform": pc.pk,
            "notes": "Escaped!",
        },
        format="json",
    )
    assert response.status_code == 200
    entry.refresh_from_db()
    assert (entry.status, entry.rating, entry.hours_played, entry.platform) == (
        "completed",
        5,
        Decimal("80"),
        pc,
    )
    assert entry.notes == "Escaped!"

    # PATCH changes only what it sends; null clears rating and platform.
    response = client.patch(
        entries_url(entry.pk), {"rating": None, "platform": None}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["platform"] is None
    entry.refresh_from_db()
    assert (entry.status, entry.rating, entry.platform, entry.notes) == (
        "completed",
        None,
        None,
        "Escaped!",
    )


def test_api_update_cannot_move_an_entry_to_another_game():
    alice = make_user("alice")
    entry = LibraryEntry.objects.create(user=alice, game=make_game(1, "Hades"))
    make_game(2, "Celeste")

    response = token_client(alice).patch(
        entries_url(entry.pk), {"rawg_id": 2, "notes": "Hi"}, format="json"
    )

    assert response.status_code == 200
    entry.refresh_from_db()
    assert entry.game.name == "Hades"
    assert entry.notes == "Hi"


def test_api_delete_removes_only_the_entry():
    alice = make_user("alice")
    hades = make_game(1, "Hades")
    entry = LibraryEntry.objects.create(user=alice, game=hades)
    bobs = LibraryEntry.objects.create(user=make_user("bob"), game=hades)

    response = token_client(alice).delete(entries_url(entry.pk))

    assert response.status_code == 204
    assert not LibraryEntry.objects.filter(pk=entry.pk).exists()
    # The shared game and other users' entries stay.
    assert Game.objects.filter(pk=hades.pk).exists()
    assert LibraryEntry.objects.filter(pk=bobs.pk).exists()


@pytest.mark.parametrize("bob_is_public", [True, False], ids=["public", "private"])
@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_api_cannot_change_another_users_entry(two_libraries, method, bob_is_public):
    bob = two_libraries["bob"]
    bob.library_is_public = bob_is_public
    bob.save()
    bobs_entry = two_libraries["bob_entry"]
    client = token_client(two_libraries["alice"])

    response = getattr(client, method)(
        entries_url(bobs_entry.pk), {"status": "dropped", "rating": 1}, format="json"
    )

    # Always a 404, never a 403, whatever Bob's sharing setting.
    assert response.status_code == 404
    bobs_entry.refresh_from_db()
    assert (bobs_entry.status, bobs_entry.rating) == ("want_to_play", None)


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_api_writes_need_credentials(two_libraries, method):
    pk = None if method == "post" else two_libraries["alice_entries"][0].pk

    response = getattr(APIClient(), method)(
        entries_url(pk), {"rawg_id": 1, "status": "dropped"}, format="json"
    )

    assert response.status_code == 401
    assert LibraryEntry.objects.count() == 3
    assert not LibraryEntry.objects.filter(status="dropped").exists()


def test_signed_in_users_can_open_an_entry_in_the_browsable_api(client):
    alice = make_user("alice")
    pc = Platform.objects.create(rawg_id=4, name="PC", slug="pc")
    entry = LibraryEntry.objects.create(
        user=alice, game=make_game(1, "Hades"), platform=pc
    )
    client.force_login(alice)

    response = client.get(entries_url(entry.pk), headers={"accept": "text/html"})

    assert response.status_code == 200
    assert "Hades" in response.content.decode()


# --- Shared library endpoint: browsing and read-only ------------------------


def test_shared_library_endpoint_pages_filters_and_credits_rawg():
    bob = make_user("bob", library_is_public=True)
    for n in range(14):
        LibraryEntry.objects.create(
            user=bob,
            game=make_game(n, f"Game {n:02}"),
            status="completed" if n % 2 else "playing",
        )
    LibraryEntry.objects.create(user=make_user("alice"), game=make_game(99, "Other"))
    client = APIClient()

    first = client.get(user_entries_url("bob")).json()
    assert first["count"] == 14
    assert len(first["results"]) == 12
    assert first["next"] is not None
    assert first["attribution"] == {
        "text": "Game data from RAWG.",
        "name": "RAWG",
        "url": "https://rawg.io",
    }

    completed = client.get(
        user_entries_url("bob"), {"status": "completed", "sort": "name"}
    ).json()
    assert [entry["game"]["name"] for entry in completed["results"]] == [
        f"Game {n:02}" for n in range(14) if n % 2
    ]

    bad = client.get(user_entries_url("bob"), {"status": "palying"})
    assert bad.status_code == 400


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_shared_library_endpoint_is_read_only_even_for_the_owner(method):
    bob = make_user("bob", library_is_public=True)
    LibraryEntry.objects.create(user=bob, game=make_game(1, "Hades"))

    response = getattr(token_client(bob), method)(
        user_entries_url("bob"), {"rawg_id": 1}, format="json"
    )

    assert response.status_code == 405
    assert LibraryEntry.objects.count() == 1
