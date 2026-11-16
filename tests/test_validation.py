"""Tests for the shared entry validation used by the website and the API."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from games.models import Game, Platform
from library.models import LibraryEntry
from library.validation import validate_platform_for_game

pytestmark = pytest.mark.django_db


@pytest.fixture
def hades():
    game = Game.objects.create(rawg_id=1, name="Hades", slug="hades")
    game.platforms.add(Platform.objects.create(rawg_id=4, name="PC", slug="pc"))
    return game


def test_rejects_a_platform_the_game_is_not_on(hades):
    xbox = Platform.objects.create(rawg_id=1, name="Xbox One", slug="xbox-one")

    with pytest.raises(ValidationError) as caught:
        validate_platform_for_game(hades, xbox)

    assert caught.value.message_dict == {
        "platform": ["Hades isn't available on Xbox One."]
    }


def test_accepts_one_of_the_games_platforms_or_no_platform(hades):
    pc = Platform.objects.get(slug="pc")

    validate_platform_for_game(hades, pc)
    validate_platform_for_game(hades, None)


def test_model_clean_applies_the_platform_rule(hades):
    user = get_user_model().objects.create_user("player", password="pw-for-tests")
    xbox = Platform.objects.create(rawg_id=1, name="Xbox One", slug="xbox-one")
    entry = LibraryEntry(user=user, game=hades, platform=xbox)

    with pytest.raises(ValidationError) as caught:
        entry.full_clean()

    assert caught.value.message_dict["platform"] == [
        "Hades isn't available on Xbox One."
    ]
