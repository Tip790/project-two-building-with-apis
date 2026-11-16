"""The shared save flow used by the website and the API."""

from django.db import transaction
from django.utils.dateparse import parse_date

from . import rawg
from .models import Game, Genre, Platform


def get_or_fetch_game(rawg_id: int) -> Game:
    """Return the stored Game for a RAWG id, fetching it from RAWG if needed.

    A game that is already stored is reused with no RAWG call, so saving it
    still works while RAWG is down. Raises rawg.RawgError if RAWG has to be
    asked and the request fails.
    """
    stored = Game.objects.filter(rawg_id=rawg_id).first()
    if stored is not None:
        return stored
    data = rawg.get_game(rawg_id)
    with transaction.atomic():
        game = Game.objects.create(
            rawg_id=data["id"],
            name=data.get("name") or "",
            slug=data.get("slug") or "",
            background_image=data.get("background_image") or "",
            released=parse_date(data["released"]) if data.get("released") else None,
            metacritic=data.get("metacritic"),
            # The plain-text description, so no RAWG HTML reaches our pages.
            description=data.get("description_raw") or "",
        )
        game.genres.set(
            Genre.objects.get_or_create(
                rawg_id=genre["id"],
                defaults={"name": genre["name"], "slug": genre["slug"]},
            )[0]
            for genre in data.get("genres") or []
        )
        game.platforms.set(
            Platform.objects.get_or_create(
                rawg_id=item["platform"]["id"],
                defaults={
                    "name": item["platform"]["name"],
                    "slug": item["platform"]["slug"],
                },
            )[0]
            for item in data.get("platforms") or []
        )
    return game
