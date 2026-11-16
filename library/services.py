"""Adding games to a library, shared by the website and the API."""

from django.db import IntegrityError, transaction

from games.services import get_or_fetch_game

from .models import LibraryEntry


class AlreadyInLibrary(Exception):
    """The user tried to add a game that is already in their library."""

    def __init__(self, entry: LibraryEntry):
        super().__init__("Already in your library.")
        self.entry = entry


def add_to_library(user, rawg_id: int) -> LibraryEntry:
    """Save a RAWG game to the user's library with status Want to Play.

    Raises AlreadyInLibrary for a duplicate, and games.rawg.RawgError if the
    game isn't stored and RAWG fails.
    """
    game = get_or_fetch_game(rawg_id)
    existing = LibraryEntry.objects.filter(user=user, game=game).first()
    if existing is not None:
        raise AlreadyInLibrary(existing)
    try:
        with transaction.atomic():
            return LibraryEntry.objects.create(user=user, game=game)
    except IntegrityError:
        # Another request added it between the check and the insert.
        raise AlreadyInLibrary(LibraryEntry.objects.get(user=user, game=game)) from None
