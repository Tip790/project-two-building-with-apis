"""Tests for the seed_demo management command.

games.rawg.get_game is replaced with a fake, so no test calls RAWG.
"""

import html
from collections import Counter

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse

from accounts.models import User
from games import rawg
from games.models import Game
from library.management.commands.seed_demo import DEMO_LIBRARIES
from library.models import LibraryEntry
from library.services import add_to_library

pytestmark = pytest.mark.django_db

PRIVATE_USER = "demo_private"
PUBLIC_USER = "demo_public"
DEMO_PASSWORD = "demo-password-local-only"

PLATFORMS = [
    (4, "PC", "pc"),
    (18, "PlayStation 4", "playstation4"),
    (187, "PlayStation 5", "playstation5"),
    (7, "Nintendo Switch", "nintendo-switch"),
    (1, "Xbox One", "xbox-one"),
]


def fake_game_detail(rawg_id):
    """A hand-written RAWG /games/<id> response for any id."""
    return {
        "id": rawg_id,
        "slug": f"game-{rawg_id}",
        "name": f"Game {rawg_id}",
        "released": "2020-01-01",
        "background_image": f"https://media.rawg.io/media/games/{rawg_id}.jpg",
        "metacritic": 80,
        "description_raw": f"Description of game {rawg_id}.",
        "genres": [{"id": 4, "name": "Action", "slug": "action"}],
        "platforms": [
            {"platform": {"id": pid, "name": name, "slug": slug}}
            for pid, name, slug in PLATFORMS
        ],
    }


@pytest.fixture
def rawg_calls(monkeypatch):
    """Record every get_game call and answer it with a fake game."""
    calls = []

    def _fake_get_game(rawg_id):
        calls.append(rawg_id)
        return fake_game_detail(rawg_id)

    monkeypatch.setattr(rawg, "get_game", _fake_get_game)
    return calls


def test_first_run_seeds_a_private_and_a_public_user_through_the_save_flow(
    rawg_calls,
):
    call_command("seed_demo")

    private = User.objects.filter(username=PRIVATE_USER).first()
    public = User.objects.filter(username=PUBLIC_USER).first()
    assert private is not None and public is not None
    assert private.library_is_public is False
    assert public.library_is_public is True
    assert private.check_password(DEMO_PASSWORD)
    assert public.check_password(DEMO_PASSWORD)

    # About eight games, each fetched from RAWG exactly once and stored.
    assert 6 <= Game.objects.count() <= 10
    assert Counter(rawg_calls) == Counter(
        Game.objects.values_list("rawg_id", flat=True)
    )
    assert len(rawg_calls) == len(set(rawg_calls))

    # Both users have entries, and at least one game is in both libraries.
    private_games = set(private.entries.values_list("game_id", flat=True))
    public_games = set(public.entries.values_list("game_id", flat=True))
    assert private_games and public_games
    assert private_games & public_games

    # The entries vary in every tracked field.
    entries = list(LibraryEntry.objects.all())
    assert len({e.status for e in entries}) == len(LibraryEntry.Status)
    assert any(e.rating is not None for e in entries)
    assert any(e.rating is None for e in entries)
    assert len({e.rating for e in entries if e.rating is not None}) >= 3
    assert any(e.hours_played is not None for e in entries)
    assert any(e.hours_played is None for e in entries)
    assert any(e.platform is not None for e in entries)
    assert any(e.notes for e in entries)

    # Each entry's platform is one of its game's own platforms.
    for entry in entries:
        if entry.platform is not None:
            assert entry.game.platforms.filter(pk=entry.platform.pk).exists()


def test_rerunning_creates_no_duplicates_makes_no_rawg_calls_and_restores_demo_state(
    rawg_calls,
):
    call_command("seed_demo")
    counts = (User.objects.count(), Game.objects.count(), LibraryEntry.objects.count())
    seeded = {
        (e.user.username, e.game.rawg_id): (
            e.status,
            e.rating,
            e.hours_played,
            e.platform_id,
            e.notes,
        )
        for e in LibraryEntry.objects.select_related("user", "game")
    }

    # Someone plays with the demo accounts between runs.
    private = User.objects.get(username=PRIVATE_USER)
    private.library_is_public = True
    private.set_password("changed-during-demo")
    private.save()
    changed = private.entries.first()
    changed.status = LibraryEntry.Status.PLAYING
    changed.rating = 1
    changed.notes = "edited during the demo"
    changed.save()
    rawg_calls.clear()

    call_command("seed_demo")

    assert rawg_calls == []
    assert (
        User.objects.count(),
        Game.objects.count(),
        LibraryEntry.objects.count(),
    ) == counts
    private.refresh_from_db()
    assert private.library_is_public is False
    assert private.check_password(DEMO_PASSWORD)
    assert {
        (e.user.username, e.game.rawg_id): (
            e.status,
            e.rating,
            e.hours_played,
            e.platform_id,
            e.notes,
        )
        for e in LibraryEntry.objects.select_related("user", "game")
    } == seeded


def test_rawg_failure_stops_with_the_friendly_message_and_a_rerun_finishes(
    monkeypatch,
):
    message = "Could not reach RAWG. Check your internet connection and try again."
    calls = []

    def _get_game_failing_on_third(rawg_id):
        calls.append(rawg_id)
        if len(calls) == 3:
            raise rawg.RawgError(message)
        return fake_game_detail(rawg_id)

    monkeypatch.setattr(rawg, "get_game", _get_game_failing_on_third)

    error = None
    try:
        call_command("seed_demo")
    except Exception as exc:  # noqa: BLE001 - the test checks which kind
        error = exc

    assert isinstance(error, CommandError)
    assert message in str(error)
    stored_before_rerun = set(Game.objects.values_list("rawg_id", flat=True))
    assert len(stored_before_rerun) == 2

    # RAWG is back: the re-run fetches only what's missing and finishes.
    rerun_calls = []

    def _get_game_working(rawg_id):
        rerun_calls.append(rawg_id)
        return fake_game_detail(rawg_id)

    monkeypatch.setattr(rawg, "get_game", _get_game_working)
    call_command("seed_demo")

    expected = {
        (username, entry[0])
        for username, (_, entries) in DEMO_LIBRARIES.items()
        for entry in entries
    }
    all_ids = {rawg_id for _, rawg_id in expected}
    assert sorted(rerun_calls) == sorted(all_ids - stored_before_rerun)
    assert {
        (e.user.username, e.game.rawg_id)
        for e in LibraryEntry.objects.select_related("user", "game")
    } == expected


def test_rerunning_keeps_games_added_to_a_demo_library_by_hand(rawg_calls):
    call_command("seed_demo")
    public = User.objects.get(username=PUBLIC_USER)
    hand_added = add_to_library(public, 99999, notes="added by hand")

    call_command("seed_demo")

    hand_added.refresh_from_db()
    assert hand_added.notes == "added by hand"
    assert public.entries.filter(game__rawg_id=99999).count() == 1


def test_rawg_down_on_a_first_run_saves_no_games(monkeypatch):
    def _rawg_down(rawg_id):
        raise rawg.RawgError("Could not reach RAWG.")

    monkeypatch.setattr(rawg, "get_game", _rawg_down)

    with pytest.raises(CommandError, match="Run seed_demo again"):
        call_command("seed_demo")
    assert Game.objects.count() == 0
    assert LibraryEntry.objects.count() == 0


def test_seeded_pages_and_api_work_while_rawg_is_unreachable(
    client, rawg_calls, monkeypatch
):
    call_command("seed_demo")

    def _no_rawg(*args, **kwargs):
        raise AssertionError("RAWG must not be called")

    monkeypatch.setattr(rawg, "get_game", _no_rawg)
    monkeypatch.setattr(rawg, "search_games", _no_rawg)
    monkeypatch.setattr(rawg.requests, "get", _no_rawg)

    public = User.objects.get(username=PUBLIC_USER)
    private = User.objects.get(username=PRIVATE_USER)
    public_entry = public.entries.select_related("game").exclude(notes="").first()
    private_entry = private.entries.select_related("game").first()

    # Anyone can browse the Public demo library and its detail pages.
    response = client.get(reverse("shared:library", args=[PUBLIC_USER]))
    assert response.status_code == 200
    assert public_entry.game.name in response.content.decode()
    response = client.get(
        reverse("shared:entry_detail", args=[PUBLIC_USER, public_entry.pk])
    )
    assert response.status_code == 200
    assert public_entry.notes in html.unescape(response.content.decode())

    # The Private demo library is hidden from others.
    response = client.get(reverse("shared:library", args=[PRIVATE_USER]))
    assert response.status_code == 404

    # The Private demo user can sign in with the demo password and use it all.
    assert client.login(username=PRIVATE_USER, password=DEMO_PASSWORD)
    response = client.get(reverse("library:my_library"))
    assert response.status_code == 200
    assert private_entry.game.name in response.content.decode()
    response = client.get(reverse("library:entry_detail", args=[private_entry.pk]))
    assert response.status_code == 200
    response = client.get(reverse("api:entry-list"))
    assert response.status_code == 200
    assert response.json()["count"] == private.entries.count()
