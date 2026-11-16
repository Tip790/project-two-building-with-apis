"""Tests for the database rules on games and library entries."""

from decimal import Decimal

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse

from games.models import Game, Genre, Platform
from library.models import LibraryEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return get_user_model().objects.create_user("player", password="pw-for-tests")


@pytest.fixture
def game():
    return Game.objects.create(rawg_id=1, name="Hades", slug="hades")


def test_new_entries_default_to_want_to_play(user, game):
    entry = LibraryEntry.objects.create(user=user, game=game)

    assert entry.status == LibraryEntry.Status.WANT_TO_PLAY
    assert entry.rating is None
    assert entry.hours_played is None


def test_a_user_can_save_a_game_only_once(user, game):
    LibraryEntry.objects.create(user=user, game=game)

    with pytest.raises(IntegrityError), transaction.atomic():
        LibraryEntry.objects.create(user=user, game=game)


@pytest.mark.parametrize(
    "fields",
    [
        {"rating": 0},
        {"rating": 6},
        {"hours_played": Decimal("-1")},
        {"hours_played": Decimal("10000.1")},
    ],
    ids=["rating-0", "rating-6", "negative-hours", "hours-over-cap"],
)
def test_the_database_rejects_out_of_range_values(user, game, fields):
    with pytest.raises(IntegrityError), transaction.atomic():
        LibraryEntry.objects.create(user=user, game=game, **fields)


@pytest.mark.parametrize(
    "fields",
    [
        {"rating": 1},
        {"rating": 5},
        {"hours_played": Decimal("0")},
        {"hours_played": Decimal("10000")},
    ],
    ids=["rating-1", "rating-5", "zero-hours", "hours-at-cap"],
)
def test_the_database_accepts_values_at_the_limits(user, game, fields):
    LibraryEntry.objects.create(user=user, game=game, **fields)


def test_rawg_ids_are_unique(game):
    with pytest.raises(IntegrityError), transaction.atomic():
        Game.objects.create(rawg_id=1, name="Another", slug="another")


@pytest.mark.parametrize("model", [Genre, Platform, Game, LibraryEntry])
def test_every_model_is_in_the_admin(admin_client, model):
    assert admin.site.is_registered(model)
    opts = model._meta
    url = reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")

    assert admin_client.get(url).status_code == 200
