"""Create demo users with saved games, for demonstrating the app."""

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from games.rawg import RawgError
from games.services import get_or_fetch_game
from library.models import LibraryEntry
from library.services import AlreadyInLibrary, add_to_library

# For local demos only. Never use this password for a real account.
DEMO_PASSWORD = "demo-password-local-only"

Status = LibraryEntry.Status

# username -> (library_is_public, entries). Each entry is
# (RAWG id, status, rating, hours played, platform slug, notes).
DEMO_LIBRARIES = {
    "demo_public": (
        True,
        [
            (
                3328,
                Status.COMPLETED,
                5,
                "140.5",
                "playstation4",
                "Best side quests I've played. The Bloody Baron stays with you.",
            ),
            (
                9767,
                Status.PLAYING,
                4,
                "22",
                "nintendo-switch",
                "Stuck on the Mantis Lords. Getting closer every try.",
            ),
            (4200, Status.COMPLETED, 5, "12", "pc", "Co-op with a friend is a must."),
            (
                22511,
                Status.DROPPED,
                3,
                "30",
                "nintendo-switch",
                "Loved exploring, but weapon durability wore me down.",
            ),
            (
                28,
                Status.WANT_TO_PLAY,
                None,
                None,
                "playstation4",
                "Saving this for a long holiday.",
            ),
            (5679, Status.PLAYING, None, "85", "pc", ""),
        ],
    ),
    "demo_private": (
        False,
        [
            (
                3498,
                Status.COMPLETED,
                4,
                "60",
                "pc",
                "Finished the story. Heists were the highlight.",
            ),
            (
                3328,
                Status.WANT_TO_PLAY,
                None,
                None,
                None,
                "Everyone keeps recommending it.",
            ),
            (
                9767,
                Status.DROPPED,
                2,
                "5.5",
                "pc",
                "Too hard for me right now. Maybe later.",
            ),
            (13537, Status.COMPLETED, 5, "14", "pc", "A classic for a reason."),
        ],
    ),
}


class Command(BaseCommand):
    help = "Create a Private and a Public demo user with saved games."

    def handle(self, *args, **options):
        for username, (is_public, entries) in DEMO_LIBRARIES.items():
            # Re-running resets the demo user's visibility and password.
            user, _ = User.objects.get_or_create(username=username)
            user.library_is_public = is_public
            user.set_password(DEMO_PASSWORD)
            user.save()
            for rawg_id, status, rating, hours, platform_slug, notes in entries:
                try:
                    game = get_or_fetch_game(rawg_id)
                except RawgError as exc:
                    # Work saved so far is kept; running again picks up from here.
                    raise CommandError(
                        f"{exc} Run seed_demo again once RAWG is reachable."
                    ) from exc
                fields = {
                    "status": status,
                    "rating": rating,
                    "hours_played": Decimal(hours) if hours is not None else None,
                    "platform": game.platforms.filter(slug=platform_slug).first(),
                    "notes": notes,
                }
                try:
                    add_to_library(user, rawg_id, **fields)
                except AlreadyInLibrary as exc:
                    # Restore a seeded entry. Entries added by hand are kept.
                    for name, value in fields.items():
                        setattr(exc.entry, name, value)
                    exc.entry.save()
            visibility = "Public" if is_public else "Private"
            self.stdout.write(
                f"{username} ({visibility} library): {len(entries)} games"
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready. Log in with password {DEMO_PASSWORD!r} "
                "(local demo only)."
            )
        )
