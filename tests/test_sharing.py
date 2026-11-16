"""Tests for sharing and privacy: shared library pages, Settings, and refusals.

These run from local data only; no test calls RAWG.
"""

import re
from decimal import Decimal
from html import unescape
from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from games import rawg
from games.models import Game, Platform
from library.models import LibraryEntry

pytestmark = pytest.mark.django_db


def make_user(username, **fields):
    return get_user_model().objects.create_user(
        username, password="pw-for-tests", **fields
    )


@pytest.fixture
def libraries():
    """One Private and one Public library, each with one entry."""
    private = make_user("private_owner")
    public = make_user("public_owner", library_is_public=True)
    hades = Game.objects.create(rawg_id=1, name="Hades", slug="hades")
    celeste = Game.objects.create(rawg_id=2, name="Celeste", slug="celeste")
    return {
        "private": LibraryEntry.objects.create(user=private, game=hades),
        "public": LibraryEntry.objects.create(user=public, game=celeste),
    }


@pytest.fixture
def rawg_unreachable(monkeypatch):
    """Any attempt to reach RAWG fails the test."""

    def _no_rawg(*args, **kwargs):
        raise AssertionError("Shared pages must not call RAWG")

    monkeypatch.setattr(rawg.requests, "get", _no_rawg)
    monkeypatch.setattr(rawg, "get_game", _no_rawg)
    monkeypatch.setattr(rawg, "search_games", _no_rawg)


def main_content(response):
    """The page's <main> element, without the navbar's log-out form."""
    html = unescape(response.content.decode())
    return html.split("<main", 1)[1].split("</main>", 1)[0]


def shared_url(page, username, entry):
    if page == "library":
        return reverse("shared:library", args=[username])
    return reverse("shared:entry_detail", args=[username, entry.pk])


@pytest.mark.parametrize("page", ["library", "entry"])
@pytest.mark.parametrize("viewer", ["signed-out", "stranger"])
def test_private_and_missing_libraries_get_an_identical_404(
    client, libraries, page, viewer
):
    if viewer == "stranger":
        client.force_login(make_user("stranger"))
    private, public = libraries["private"], libraries["public"]

    public_response = client.get(shared_url(page, "public_owner", public))
    private_response = client.get(shared_url(page, "private_owner", private))
    missing_response = client.get(shared_url(page, "no_such_user", private))

    assert public_response.status_code == 200
    assert "Celeste" in public_response.content.decode()
    assert private_response.status_code == 404
    assert missing_response.status_code == 404
    assert private_response.content == missing_response.content, (
        "a Private library must look exactly like a user who doesn't exist"
    )
    assert "Hades" not in private_response.content.decode()

    # The owner always sees their own library, even while it's Private.
    client.force_login(private.user)
    owner_response = client.get(shared_url(page, "private_owner", private))
    assert owner_response.status_code == 200
    assert "Hades" in owner_response.content.decode()


@pytest.mark.parametrize("page", ["library", "entry"])
def test_switching_to_private_makes_the_share_link_404_at_once(client, libraries, page):
    public = libraries["public"]
    url = shared_url(page, "public_owner", public)
    assert client.get(url).status_code == 200, "the share link works while Public"

    owner_client = client.__class__()
    owner_client.force_login(public.user)
    # An unchecked checkbox is simply absent from the form data.
    response = owner_client.post(reverse("accounts:settings"), {})

    assert response.status_code == 302
    settings_page = owner_client.get(response.url).content.decode()
    assert "Your library is now Private." in settings_page
    response = client.get(url)
    assert response.status_code == 404
    assert "Celeste" not in response.content.decode()


EDIT_ATTEMPTS = [
    ("get", "library:entry_detail", {}),
    ("post", "library:entry_detail", {"status": "dropped", "notes": "Hijacked"}),
    ("get", "library:entry_delete", {}),
    ("post", "library:entry_delete", {}),
]
EDIT_IDS = ["edit-page", "save", "delete-confirm", "delete"]


@pytest.mark.parametrize(
    ("library", "viewer", "expected"),
    [
        ("public", "stranger", 403),
        ("private", "stranger", 404),
        ("public", "signed-out", 302),
        ("private", "signed-out", 302),
    ],
    ids=["public-403", "private-404", "public-login", "private-login"],
)
@pytest.mark.parametrize(("method", "url_name", "data"), EDIT_ATTEMPTS, ids=EDIT_IDS)
def test_non_owner_edits_are_refused_and_change_nothing(
    client, libraries, library, viewer, expected, method, url_name, data
):
    entry = libraries[library]
    if viewer == "stranger":
        client.force_login(make_user("stranger"))
    url = reverse(url_name, args=[entry.pk])

    response = getattr(client, method)(url, data)

    assert response.status_code == expected
    if expected == 302:
        assert response.url == f"{reverse('accounts:login')}?next={url}"
    else:
        assert entry.game.name not in response.content.decode()
    entry.refresh_from_db()  # raises if the entry was deleted
    assert entry.status == LibraryEntry.Status.WANT_TO_PLAY
    assert entry.notes == ""


# --- Read-only shared pages ----------------------------------------------------


@pytest.fixture
def rated_public_entry(libraries):
    entry = libraries["public"]
    pc = Platform.objects.create(rawg_id=4, name="PC", slug="pc")
    entry.game.platforms.add(pc)
    entry.status = LibraryEntry.Status.COMPLETED
    entry.rating = 5
    entry.hours_played = Decimal("31.5")
    entry.platform = pc
    entry.notes = "Climbed every strawberry."
    entry.save()
    return entry


def assert_read_only(main, entry):
    assert 'method="post"' not in main
    assert "csrfmiddlewaretoken" not in main
    assert "Remove" not in main
    assert reverse("library:entry_detail", args=[entry.pk]) not in main


@pytest.mark.parametrize("viewer", ["signed-out", "stranger"])
def test_visitors_see_a_public_entry_read_only_with_the_owners_tracking(
    client, rated_public_entry, rawg_unreachable, viewer
):
    entry = rated_public_entry
    if viewer == "stranger":
        client.force_login(make_user("stranger"))

    response = client.get(shared_url("entry", "public_owner", entry))

    assert response.status_code == 200
    main = main_content(response)
    for text in [
        "Celeste",
        "public_owner's tracking",
        "Completed",
        "5/5 ★",
        "31.5 h",
        "PC",
        "Climbed every strawberry.",
        'href="https://rawg.io/games/celeste"',
        f'href="{reverse("shared:library", args=["public_owner"])}"',
    ]:
        assert text in main
    assert_read_only(main, entry)
    assert "Edit in My Library" not in main


@pytest.mark.parametrize("viewer", ["signed-out", "stranger"])
def test_visitors_see_a_public_library_read_only(client, libraries, viewer):
    entry = libraries["public"]
    if viewer == "stranger":
        client.force_login(make_user("stranger"))

    response = client.get(reverse("shared:library", args=["public_owner"]))

    assert response.status_code == 200
    main = main_content(response)
    assert "public_owner's library" in main
    assert "Hades" not in main, "only the owner's entries"
    assert f'href="{shared_url("entry", "public_owner", entry)}"' in main
    assert_read_only(main, entry)


def test_owners_preview_their_own_shared_pages_with_a_way_back_to_editing(
    client, libraries
):
    entry = libraries["private"]
    client.force_login(entry.user)

    library_main = main_content(
        client.get(reverse("shared:library", args=["private_owner"]))
    )
    detail_main = main_content(client.get(shared_url("entry", "private_owner", entry)))

    assert "This is how others see your library" in library_main
    assert "it's Private" in library_main
    assert "Edit in My Library" in detail_main
    assert reverse("library:entry_detail", args=[entry.pk]) in detail_main
    assert "Remove" not in detail_main


def test_an_entry_from_another_library_is_404_under_this_username(client, libraries):
    # The Public owner's URL with the Private owner's entry pk.
    url = reverse("shared:entry_detail", args=["public_owner", libraries["private"].pk])

    response = client.get(url)

    assert response.status_code == 404
    assert "Hades" not in response.content.decode()


def test_an_empty_shared_library_says_so(client):
    make_user("newbie", library_is_public=True)

    response = client.get(reverse("shared:library", args=["newbie"]))

    assert response.status_code == 200
    assert "newbie hasn't saved any games yet." in main_content(response)


# --- Browsing a shared library -------------------------------------------------


@pytest.fixture
def shared_collection():
    """A Public library of 14 games, 13 of them Playing, plus a Private one."""
    owner = make_user("sharer", library_is_public=True)
    for number in range(14):
        game = Game.objects.create(
            rawg_id=100 + number, name=f"Game {number:02}", slug=f"game-{number}"
        )
        status = "dropped" if number == 0 else "playing"
        LibraryEntry.objects.create(user=owner, game=game, status=status)
    hidden = Game.objects.create(rawg_id=999, name="Hidden Game", slug="hidden")
    LibraryEntry.objects.create(user=make_user("hidden"), game=hidden)
    return owner


def names_on_page(html):
    """The games' card links, in page order (each cover's alt text repeats them)."""
    return re.findall(r">(Game \d\d)</a>", html)


def test_shared_library_filters_sorts_and_pages_like_my_library(
    client, shared_collection, rawg_unreachable
):
    url = reverse("shared:library", args=["sharer"])

    response = client.get(url, {"status": "playing", "sort": "name"})

    html = unescape(response.content.decode())
    assert names_on_page(html) == [f"Game {n:02}" for n in range(1, 13)]
    assert "13 games" in html
    assert "Hidden Game" not in html
    next_link = re.search(r'rel="next" href="([^"]+)"', html).group(1)
    assert parse_qs(urlsplit(next_link).query) == {
        "status": ["playing"],
        "sort": ["name"],
        "page": ["2"],
    }
    page_two = unescape(client.get(url + next_link).content.decode())
    assert names_on_page(page_two) == ["Game 13"]


def test_shared_library_htmx_returns_only_the_results(client, shared_collection):
    url = reverse("shared:library", args=["sharer"])

    response = client.get(url, {"q": "game 07"}, headers={"HX-Request": "true"})

    html = unescape(response.content.decode())
    assert "<html" not in html
    assert names_on_page(html) == ["Game 07"]
    assert "HX-Request" in response["Vary"]


def test_shared_library_filter_bar_submits_to_the_shared_url(client, shared_collection):
    url = reverse("shared:library", args=["sharer"])

    main = main_content(client.get(url))

    assert f'hx-get="{url}"' in main
    assert 'hx-push-url="true"' in main


def test_no_matches_in_a_shared_library_says_this_library(client, shared_collection):
    response = client.get(reverse("shared:library", args=["sharer"]), {"q": "zzz"})

    assert "No games in this library match these filters." in main_content(response)


def test_private_library_htmx_requests_are_also_404(client, libraries):
    response = client.get(
        reverse("shared:library", args=["private_owner"]),
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 404


# --- Settings ------------------------------------------------------------------


def test_settings_requires_sign_in(client):
    url = reverse("accounts:settings")

    response = client.get(url)

    assert response.status_code == 302
    assert response.url == f"{reverse('accounts:login')}?next={url}"


def test_settings_shows_private_by_default_and_the_share_link(client):
    client.force_login(make_user("newcomer"))

    response = client.get(reverse("accounts:settings"))

    assert response.status_code == 200
    main = main_content(response)
    assert '<strong data-testid="library-visibility">Private</strong>' in main
    assert 'value="http://testserver/u/newcomer/"' in main
    toggle = re.search(r'<input[^>]*name="library_is_public"[^>]*>', main).group(0)
    assert "checked" not in toggle


def test_settings_can_make_a_library_public(client):
    user = make_user("sharer")
    client.force_login(user)

    response = client.post(
        reverse("accounts:settings"), {"library_is_public": "on"}, follow=True
    )

    user.refresh_from_db()
    assert user.library_is_public is True
    main = main_content(response)
    assert "Your library is now Public." in main
    assert '<strong data-testid="library-visibility">Public</strong>' in main
    client.logout()
    assert client.get(reverse("shared:library", args=["sharer"])).status_code == 200


def test_settings_changes_only_the_toggle_on_the_users_own_account(client, libraries):
    private_owner = libraries["private"].user
    client.force_login(private_owner)

    client.post(
        reverse("accounts:settings"),
        {"library_is_public": "on", "username": "public_owner", "is_staff": "on"},
    )

    private_owner.refresh_from_db()
    assert private_owner.library_is_public is True
    assert private_owner.username == "private_owner"
    assert private_owner.is_staff is False


def test_navbar_links_to_settings(client):
    client.force_login(make_user("player"))

    html = client.get(reverse("games:home")).content.decode()

    assert reverse("accounts:settings") == "/settings/"
    assert 'href="/settings/"' in html
