"""Tests for the shared save flow: turning a RAWG id into a stored Game.

games.rawg.get_game is replaced with a fake, so no test calls RAWG.
"""

import datetime

import pytest

from games import rawg, services
from games.models import Game, Genre, Platform

pytestmark = pytest.mark.django_db


def sample_game_detail(rawg_id=3328):
    """A hand-written RAWG /games/<id> response, trimmed to the fields we use."""
    return {
        "id": rawg_id,
        "slug": "the-witcher-3-wild-hunt",
        "name": "The Witcher 3: Wild Hunt",
        "released": "2015-05-18",
        "background_image": "https://media.rawg.io/media/games/witcher3.jpg",
        "metacritic": 92,
        "description": "<p>The third game in a series.</p>",
        "description_raw": "The third game in a series.",
        "genres": [
            {"id": 4, "name": "Action", "slug": "action"},
            {"id": 5, "name": "RPG", "slug": "role-playing-games-rpg"},
        ],
        "platforms": [
            {"platform": {"id": 4, "name": "PC", "slug": "pc"}},
            {"platform": {"id": 187, "name": "PlayStation 5", "slug": "playstation5"}},
        ],
    }


def test_new_rawg_id_is_fetched_once_and_stored_with_genres_and_platforms(
    monkeypatch,
):
    calls = []

    def _fake_get_game(rawg_id):
        calls.append(rawg_id)
        return sample_game_detail(rawg_id)

    monkeypatch.setattr(rawg, "get_game", _fake_get_game)

    game = services.get_or_fetch_game(3328)

    assert calls == [3328]
    assert Game.objects.count() == 1
    stored = Game.objects.get(rawg_id=3328)
    assert game == stored
    assert stored.name == "The Witcher 3: Wild Hunt"
    assert stored.slug == "the-witcher-3-wild-hunt"
    assert stored.background_image == "https://media.rawg.io/media/games/witcher3.jpg"
    assert stored.released == datetime.date(2015, 5, 18)
    assert stored.metacritic == 92
    assert stored.description == "The third game in a series."
    assert sorted(stored.genres.values_list("rawg_id", "name")) == [
        (4, "Action"),
        (5, "RPG"),
    ]
    assert sorted(stored.platforms.values_list("rawg_id", "name")) == [
        (4, "PC"),
        (187, "PlayStation 5"),
    ]
    assert Genre.objects.count() == 2
    assert Platform.objects.count() == 2
