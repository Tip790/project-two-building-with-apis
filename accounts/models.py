from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A site account. Each user owns one library, Private unless they share it."""

    library_is_public = models.BooleanField(
        default=False,
        help_text="Public libraries can be viewed read-only by anyone with the link.",
    )
