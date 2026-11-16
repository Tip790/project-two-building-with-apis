"""Tests for the owner's entry detail page: viewing, editing, and deleting.

These run from local data only; no test calls RAWG.
"""

import datetime
from decimal import Decimal
from html import unescape

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from games import rawg
from games.models import Game, Genre, Platform
from library.models import LibraryEntry

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}


def make_user(username):
    return get_user_model().objects.create_user(username, password="pw-for-tests")


@pytest.fixture
def entry():
    game = Game.objects.create(rawg_id=1, name="Hades", slug="hades")
    game.platforms.add(Platform.objects.create(rawg_id=4, name="PC", slug="pc"))
    return LibraryEntry.objects.create(user=make_user("owner"), game=game)


@pytest.mark.parametrize(
    ("method", "url_name", "data"),
    [
        ("get", "library:entry_detail", {}),
        ("post", "library:entry_detail", {"status": "dropped", "notes": "Hijacked"}),
        ("get", "library:entry_delete", {}),
        ("post", "library:entry_delete", {}),
    ],
    ids=["view", "save", "delete-confirm", "delete"],
)
def test_another_users_entry_is_404_and_left_unchanged(
    client, entry, method, url_name, data
):
    client.force_login(make_user("intruder"))

    response = getattr(client, method)(reverse(url_name, args=[entry.pk]), data)

    assert response.status_code == 404
    assert "Hades" not in response.content.decode()
    entry.refresh_from_db()  # raises if the entry was deleted
    assert entry.status == LibraryEntry.Status.WANT_TO_PLAY
    assert entry.notes == ""


@pytest.mark.parametrize(
    ("rating", "saved"), [("4", True), ("7", False)], ids=["valid", "invalid-rating"]
)
def test_htmx_save_returns_saved_alert_or_inline_errors(client, entry, rating, saved):
    client.force_login(entry.user)
    pc = Platform.objects.get(slug="pc")

    response = client.post(
        reverse("library:entry_detail", args=[entry.pk]),
        {
            "status": "playing",
            "rating": rating,
            "hours_played": "12.5",
            "platform": pc.pk,
            "notes": "Just one more run.",
        },
        headers=HTMX,
    )

    assert response.status_code == 200
    html = response.content.decode()
    assert "<html" not in html, "HTMX saves return only the form fragment"
    entry.refresh_from_db()
    if saved:
        assert "Saved." in html
        assert entry.status == LibraryEntry.Status.PLAYING
        assert entry.rating == 4
        assert entry.hours_played == Decimal("12.5")
        assert entry.platform == pc
        assert entry.notes == "Just one more run."
    else:
        assert "Saved." not in html
        assert "Rating must be between 1 and 5 stars." in html
        assert entry.status == LibraryEntry.Status.WANT_TO_PLAY
        assert entry.rating is None
        assert entry.notes == ""


def save(client, entry, headers=None, **fields):
    data = {"status": "want_to_play", "rating": "", "hours_played": "", "notes": ""}
    data.update(fields)
    return client.post(
        reverse("library:entry_detail", args=[entry.pk]), data, headers=headers or {}
    )


@pytest.fixture
def rawg_unreachable(monkeypatch):
    """Any attempt to reach RAWG fails the test."""

    def _no_rawg(*args, **kwargs):
        raise AssertionError("Entry pages must not call RAWG")

    monkeypatch.setattr(rawg.requests, "get", _no_rawg)
    monkeypatch.setattr(rawg, "get_game", _no_rawg)
    monkeypatch.setattr(rawg, "search_games", _no_rawg)


def test_detail_page_shows_stored_game_details_while_rawg_is_down(
    client, rawg_unreachable
):
    game = Game.objects.create(
        rawg_id=3328,
        name="The Witcher 3: Wild Hunt",
        slug="the-witcher-3-wild-hunt",
        background_image="https://media.rawg.io/media/games/witcher3.jpg",
        released=datetime.date(2015, 5, 18),
        metacritic=92,
        description="The third game in a series.",
    )
    game.genres.add(Genre.objects.create(rawg_id=5, name="RPG", slug="rpg"))
    game.platforms.add(
        Platform.objects.create(rawg_id=4, name="PC", slug="pc"),
        Platform.objects.create(rawg_id=187, name="PlayStation 5", slug="ps5"),
    )
    entry = LibraryEntry.objects.create(user=make_user("owner"), game=game)
    client.force_login(entry.user)

    response = client.get(reverse("library:entry_detail", args=[entry.pk]))

    assert response.status_code == 200
    html = unescape(response.content.decode())
    for text in [
        "The Witcher 3: Wild Hunt",
        "https://media.rawg.io/media/games/witcher3.jpg",
        "May 18, 2015",
        "92",
        "RPG",
        "PC, PlayStation 5",
        "The third game in a series.",
    ]:
        assert text in html
    assert 'href="https://rawg.io/games/the-witcher-3-wild-hunt"' in html
    assert "View on RAWG" in html
    assert "cover-placeholder.svg" in html, "broken covers fall back"


def test_detail_page_requires_sign_in(client, entry):
    url = reverse("library:entry_detail", args=[entry.pk])

    response = client.get(url)

    assert response.status_code == 302
    assert response.url == f"/accounts/login/?next={url}"


def test_platform_choices_are_only_the_games_platforms(client, entry):
    Platform.objects.create(rawg_id=1, name="Xbox One", slug="xbox-one")
    client.force_login(entry.user)

    html = client.get(reverse("library:entry_detail", args=[entry.pk])).content
    html = html.decode()

    assert ">PC</option>" in html
    assert "Xbox One" not in html
    assert ">Not set</option>" in html


def test_unrated_and_blank_hours_can_be_saved(client, entry):
    entry.rating, entry.hours_played = 3, Decimal("5")
    entry.save()
    client.force_login(entry.user)

    response = save(client, entry, headers=HTMX, status="completed")

    assert "Saved." in response.content.decode()
    entry.refresh_from_db()
    assert entry.status == LibraryEntry.Status.COMPLETED
    assert entry.rating is None
    assert entry.hours_played is None
    assert entry.platform is None


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"rating": "0"}, "Rating must be between 1 and 5 stars."),
        ({"hours_played": "-1"}, "Hours played can't be negative."),
        ({"hours_played": "10000.5"}, "Hours played can't be more than 10,000."),
        ({"status": "abandoned"}, "Select a valid choice."),
    ],
    ids=["rating-0", "negative-hours", "hours-over-cap", "unknown-status"],
)
def test_out_of_range_values_are_rejected_with_clear_messages(
    client, entry, fields, message
):
    client.force_login(entry.user)

    response = save(client, entry, headers=HTMX, notes="should not stick", **fields)

    html = unescape(response.content.decode())
    assert message in html
    assert "Saved." not in html
    entry.refresh_from_db()
    assert entry.notes == ""


def test_a_platform_the_game_is_not_on_gets_the_shared_message(client, entry):
    xbox = Platform.objects.create(rawg_id=1, name="Xbox One", slug="xbox-one")
    client.force_login(entry.user)

    response = save(client, entry, headers=HTMX, platform=xbox.pk)

    assert "Hades isn't available on Xbox One." in unescape(response.content.decode())
    entry.refresh_from_db()
    assert entry.platform is None


def test_plain_post_saves_and_redirects_back_with_a_message(client, entry):
    client.force_login(entry.user)

    response = save(client, entry, status="playing", rating="5")

    url = reverse("library:entry_detail", args=[entry.pk])
    assert response.status_code == 302
    assert response.url == url
    entry.refresh_from_db()
    assert entry.status == LibraryEntry.Status.PLAYING
    assert entry.rating == 5
    page = client.get(url).content.decode()
    assert "Saved." in page


def test_plain_post_with_errors_rerenders_the_full_page(client, entry):
    client.force_login(entry.user)

    response = save(client, entry, rating="9")

    assert response.status_code == 200
    html = response.content.decode()
    assert "<html" in html
    assert "Rating must be between 1 and 5 stars." in html
    assert "Hades" in html, "the game details still show beside the errors"


def test_detail_page_offers_a_confirming_delete(client, entry):
    client.force_login(entry.user)
    delete_url = reverse("library:entry_delete", args=[entry.pk])

    html = client.get(reverse("library:entry_detail", args=[entry.pk])).content
    html = html.decode()

    assert '<dialog id="delete-modal"' in html
    assert f'href="{delete_url}"' in html, "no-JavaScript confirmation fallback"
    assert f'action="{delete_url}"' in html


def test_delete_confirmation_page_does_not_delete(client, entry):
    client.force_login(entry.user)

    response = client.get(reverse("library:entry_delete", args=[entry.pk]))

    assert response.status_code == 200
    assert "Remove Hades?" in response.content.decode()
    assert LibraryEntry.objects.filter(pk=entry.pk).exists()


def test_confirmed_delete_removes_the_entry_and_returns_to_my_library(client, entry):
    client.force_login(entry.user)

    response = client.post(
        reverse("library:entry_delete", args=[entry.pk]), follow=True
    )

    assert response.redirect_chain == [(reverse("library:my_library"), 302)]
    assert not LibraryEntry.objects.filter(pk=entry.pk).exists()
    assert Game.objects.filter(slug="hades").exists(), "the shared game stays"
    assert "Removed Hades from your library." in response.content.decode()


def test_my_library_links_each_entry_to_its_detail_page(client, entry):
    client.force_login(entry.user)

    html = client.get(reverse("library:my_library")).content.decode()

    assert f'href="{reverse("library:entry_detail", args=[entry.pk])}"' in html
