"""Validation rules for library entries, shared by the website and the API."""

from django.core.exceptions import ValidationError


def validate_platform_for_game(game, platform) -> None:
    """Raise a ValidationError if `platform` isn't one of `game`'s platforms.

    No platform is always allowed. The error is attached to the `platform`
    field so forms show it inline and the API can report it the same way.
    """
    if platform is None:
        return
    if not game.platforms.filter(pk=platform.pk).exists():
        raise ValidationError(
            {"platform": f"{game.name} isn't available on {platform.name}."}
        )
