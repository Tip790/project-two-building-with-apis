"""Tests for scripts/backlog_api.py, run against a live test server.

The script makes real HTTP requests to pytest-django's live_server, so these
exercise the real API. Games are created directly, so RAWG is never involved.
"""

import pytest
from rest_framework.authtoken.models import Token

from accounts.models import User
from games.models import Game, Platform
from library.models import LibraryEntry
from scripts import backlog_api

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def library():
    """alice's library: two Playing games and one Completed one."""
    alice = User.objects.create_user("alice", password="pw")
    pc = Platform.objects.create(rawg_id=4, name="PC", slug="pc")
    games = {}
    for rawg_id, name in [(1, "Hades"), (2, "Celeste"), (3, "Portal 2")]:
        games[name] = Game.objects.create(
            rawg_id=rawg_id, name=name, slug=name.lower(), released="2018-01-01"
        )
        games[name].platforms.add(pc)
    playing = LibraryEntry.Status.PLAYING
    LibraryEntry.objects.create(
        user=alice, game=games["Hades"], status=playing, rating=5
    )
    LibraryEntry.objects.create(
        user=alice, game=games["Celeste"], status=playing, rating=3
    )
    LibraryEntry.objects.create(
        user=alice, game=games["Portal 2"], status=LibraryEntry.Status.COMPLETED
    )
    # Someone else's entry, which alice's token must never reach.
    bob = User.objects.create_user("bob", password="pw")
    bobs = LibraryEntry.objects.create(user=bob, game=games["Hades"], rating=1)
    return {
        "token": Token.objects.create(user=alice).key,
        "pc": pc,
        "bobs_entry": bobs,
    }


def run(live_server, token, *args):
    # 127.0.0.1, not localhost: on Windows, localhost tries IPv6 first and
    # waits about 2 seconds per request before falling back.
    base_url = live_server.url.replace("localhost", "127.0.0.1")
    return backlog_api.main(["--base-url", base_url, "--token", token, *args])


def test_list_sends_the_query_parameters_and_prints_the_matching_entries(
    live_server, library, capsys
):
    code = run(
        live_server, library["token"], "list", "--status", "playing", "--sort", "rating"
    )

    out = capsys.readouterr().out
    assert code == 0
    assert "query: status=playing, sort=rating" in out
    assert "2 matching entries, showing 2" in out
    assert out.index("Hades") < out.index("Celeste")  # sorted by rating
    assert "Portal 2" not in out  # filtered out: Completed
    assert "Game data from RAWG." in out


def test_update_changes_one_field_and_prints_before_and_after(
    live_server, library, capsys
):
    entry = LibraryEntry.objects.get(user__username="alice", game__name="Celeste")

    code = run(live_server, library["token"], "update", str(entry.pk), "rating", "4")

    out = capsys.readouterr().out
    assert code == 0
    before, after = out.split("After:")
    assert "rating = 3" in before
    assert "rating = 4" in after
    entry.refresh_from_db()
    assert entry.rating == 4
    assert entry.status == LibraryEntry.Status.PLAYING  # other fields untouched


def test_update_can_set_a_platform_and_clear_a_field(live_server, library, capsys):
    entry = LibraryEntry.objects.get(user__username="alice", game__name="Hades")

    assert (
        run(
            live_server,
            library["token"],
            "update",
            str(entry.pk),
            "platform",
            str(library["pc"].pk),
        )
        == 0
    )
    assert (
        run(live_server, library["token"], "update", str(entry.pk), "rating", "null")
        == 0
    )

    entry.refresh_from_db()
    assert entry.platform == library["pc"]
    assert entry.rating is None
    assert "platform = 'PC (id" in capsys.readouterr().out


def test_invalid_values_print_the_apis_message_and_change_nothing(
    live_server, library, capsys
):
    entry = LibraryEntry.objects.get(user__username="alice", game__name="Celeste")

    code = run(live_server, library["token"], "update", str(entry.pk), "rating", "9")

    assert code == 1
    assert "Rating must be between 1 and 5 stars." in capsys.readouterr().err
    entry.refresh_from_db()
    assert entry.rating == 3


def test_another_users_entry_is_not_found(live_server, library, capsys):
    bobs = library["bobs_entry"]

    code = run(live_server, library["token"], "update", str(bobs.pk), "rating", "5")

    assert code == 1
    assert "404" in capsys.readouterr().err
    bobs.refresh_from_db()
    assert bobs.rating == 1


def test_a_bad_token_says_so(live_server, library, capsys):
    code = run(live_server, "not-a-real-token", "list")

    assert code == 1
    assert "401" in capsys.readouterr().err


def test_no_token_explains_where_to_get_one(monkeypatch, capsys):
    monkeypatch.delenv("BACKLOG_API_TOKEN", raising=False)

    code = backlog_api.main(["list"])

    assert code == 1
    assert "Settings page" in capsys.readouterr().err


def test_server_not_running_says_so(capsys):
    # Nothing listens on port 9; the request fails at once.
    code = backlog_api.main(
        ["--base-url", "http://127.0.0.1:9", "--token", "x", "list"]
    )

    assert code == 1
    assert "Is `manage.py runserver` running?" in capsys.readouterr().err
