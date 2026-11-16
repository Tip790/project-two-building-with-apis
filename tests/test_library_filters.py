"""Tests for the shared library filter set (My Library, shared library, API)."""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from games.models import Game, Genre, Platform
from library.filters import EntryFilter
from library.models import LibraryEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def library():
    """Four entries for one user, varied across every filterable field."""
    user = get_user_model().objects.create_user("player", password="pw-for-tests")
    rpg = Genre.objects.create(rawg_id=5, name="RPG", slug="role-playing-games-rpg")
    indie = Genre.objects.create(rawg_id=51, name="Indie", slug="indie")
    pc = Platform.objects.create(rawg_id=4, name="PC", slug="pc")
    switch = Platform.objects.create(rawg_id=7, name="Nintendo Switch", slug="switch")

    def add(rawg_id, name, genres, status, rating, platform):
        game = Game.objects.create(rawg_id=rawg_id, name=name, slug=name.lower())
        game.genres.set(genres)
        game.platforms.set([pc, switch])
        return LibraryEntry.objects.create(
            user=user, game=game, status=status, rating=rating, platform=platform
        )

    S = LibraryEntry.Status
    entries = {
        "witcher": add(1, "The Witcher 3", [rpg], S.COMPLETED, 5, pc),
        "hades": add(2, "Hades", [indie], S.PLAYING, 4, switch),
        "hollow": add(3, "Hollow Knight", [indie], S.WANT_TO_PLAY, None, None),
        "skyrim": add(4, "Skyrim", [rpg], S.DROPPED, 2, pc),
    }
    return user, {"rpg": rpg, "indie": indie, "pc": pc, "switch": switch}, entries


def filtered_names(user, params):
    filterset = EntryFilter(params, queryset=LibraryEntry.objects.filter(user=user))
    assert filterset.is_valid(), filterset.errors
    return {entry.game.name for entry in filterset.qs}


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({}, {"The Witcher 3", "Hades", "Hollow Knight", "Skyrim"}),
        ({"q": "hol"}, {"Hollow Knight"}),
        ({"q": "THE witcher"}, {"The Witcher 3"}),
        ({"status": "playing"}, {"Hades"}),
        ({"genre": "rpg"}, {"The Witcher 3", "Skyrim"}),
        ({"platform": "pc"}, {"The Witcher 3", "Skyrim"}),
        ({"min_rating": "4"}, {"The Witcher 3", "Hades"}),
        ({"genre": "indie", "min_rating": "1"}, {"Hades"}),
        (
            {"q": "", "status": "", "genre": "", "platform": "", "min_rating": ""},
            {"The Witcher 3", "Hades", "Hollow Knight", "Skyrim"},
        ),
    ],
    ids=[
        "no-filters",
        "name-search",
        "name-search-ignores-case",
        "status",
        "genre",
        "entry-platform",
        "min-rating",
        "combined",
        "blank-values",
    ],
)
def test_filters_narrow_entries(library, params, expected):
    user, objects, _ = library
    # Genre and platform are chosen by primary key, like a dropdown sends them.
    params = dict(params)
    for key in ("genre", "platform"):
        if params.get(key) in objects:
            params[key] = str(objects[params[key]].pk)

    assert filtered_names(user, params) == expected


@pytest.fixture
def sortable():
    """Four entries whose sort keys disagree, including blank values."""
    user = get_user_model().objects.create_user("sorter", password="pw-for-tests")
    rows = [
        # name, released, rating, hours, days since added
        ("Celeste", datetime.date(2018, 1, 25), 3, Decimal("40"), 3),
        ("Animal Crossing", datetime.date(2020, 3, 20), None, Decimal("300"), 1),
        ("Doom", None, 5, None, 2),
        ("Braid", datetime.date(2008, 8, 6), 4, Decimal("6.5"), 0),
    ]
    now = timezone.now()
    for rawg_id, (name, released, rating, hours, days_ago) in enumerate(rows, 1):
        game = Game.objects.create(
            rawg_id=rawg_id, name=name, slug=name.lower(), released=released
        )
        entry = LibraryEntry.objects.create(
            user=user, game=game, rating=rating, hours_played=hours
        )
        # created_at is auto_now_add, so backdate it with a direct update.
        LibraryEntry.objects.filter(pk=entry.pk).update(
            created_at=now - datetime.timedelta(days=days_ago)
        )
    return user


def sorted_names(user, params):
    filterset = EntryFilter(params, queryset=LibraryEntry.objects.filter(user=user))
    assert filterset.is_valid(), filterset.errors
    return [entry.game.name for entry in filterset.qs]


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({}, ["Braid", "Animal Crossing", "Doom", "Celeste"]),
        ({"sort": "added"}, ["Braid", "Animal Crossing", "Doom", "Celeste"]),
        ({"sort": "name"}, ["Animal Crossing", "Braid", "Celeste", "Doom"]),
        ({"sort": "rating"}, ["Doom", "Braid", "Celeste", "Animal Crossing"]),
        ({"sort": "hours"}, ["Animal Crossing", "Celeste", "Braid", "Doom"]),
        ({"sort": "released"}, ["Animal Crossing", "Celeste", "Braid", "Doom"]),
    ],
    ids=["default", "date-added", "name", "rating", "hours", "release-date"],
)
def test_sort_orders(sortable, params, expected):
    assert sorted_names(sortable, params) == expected
