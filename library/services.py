"""Adding games to a library, shared by the website and the API."""

from django.db import IntegrityError, transaction

from games.services import get_or_fetch_game

from .models import LibraryEntry

ALREADY_IN_LIBRARY = "Already in your library."


class AlreadyInLibrary(Exception):
    """The user tried to add a game that is already in their library."""

    def __init__(self, entry: LibraryEntry):
        super().__init__(ALREADY_IN_LIBRARY)
        self.entry = entry


def add_to_library(user, rawg_id: int, **fields) -> LibraryEntry:
    """Save a RAWG game to the user's library.

    `fields` are the entry's own fields (status, rating, ...). Anything left
    out takes the model default, so the website's one-click add is status
    Want to Play. Callers validate `fields` first.

    Raises AlreadyInLibrary for a duplicate, and games.rawg.RawgError if the
    game isn't stored and RAWG fails.
    """
    game = get_or_fetch_game(rawg_id)
    existing = LibraryEntry.objects.filter(user=user, game=game).first()
    if existing is not None:
        raise AlreadyInLibrary(existing)
    try:
        with transaction.atomic():
            return LibraryEntry.objects.create(user=user, game=game, **fields)
    except IntegrityError:
        # Another request added it between the check and the insert.
        raise AlreadyInLibrary(LibraryEntry.objects.get(user=user, game=game)) from None
