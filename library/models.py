from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

MAX_HOURS = Decimal("10000")


class LibraryEntry(models.Model):
    """One game in one user's library, with that user's own tracking fields."""

    class Status(models.TextChoices):
        WANT_TO_PLAY = "want_to_play", "Want to Play"
        PLAYING = "playing", "Playing"
        COMPLETED = "completed", "Completed"
        DROPPED = "dropped", "Dropped"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="entries"
    )
    game = models.ForeignKey(
        "games.Game", on_delete=models.CASCADE, related_name="entries"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.WANT_TO_PLAY
    )
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1, "Rating must be between 1 and 5 stars."),
            MaxValueValidator(5, "Rating must be between 1 and 5 stars."),
        ],
    )
    hours_played = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0, "Hours played can't be negative."),
            MaxValueValidator(MAX_HOURS, "Hours played can't be more than 10,000."),
        ],
    )
    platform = models.ForeignKey(
        "games.Platform",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entries",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "library entries"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "game"], name="unique_entry_per_user_and_game"
            ),
            models.CheckConstraint(
                condition=models.Q(rating__isnull=True)
                | models.Q(rating__gte=1, rating__lte=5),
                name="rating_between_1_and_5",
            ),
            models.CheckConstraint(
                condition=models.Q(hours_played__isnull=True)
                | models.Q(hours_played__gte=0, hours_played__lte=MAX_HOURS),
                name="hours_played_in_range",
            ),
        ]

    def __str__(self):
        return f"{self.user} – {self.game}"
