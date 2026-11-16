from django.db import models


class Genre(models.Model):
    """A RAWG genre, shared by every game that has it."""

    rawg_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Platform(models.Model):
    """A RAWG platform (e.g. PC, PlayStation 5), shared by every game on it."""

    rawg_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Game(models.Model):
    """A game saved from RAWG. One shared row no matter how many users save it."""

    rawg_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    # Only the RAWG-hosted URL is stored, never the image file.
    background_image = models.URLField(max_length=500, blank=True)
    released = models.DateField(null=True, blank=True)
    metacritic = models.PositiveSmallIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    genres = models.ManyToManyField(Genre, related_name="games", blank=True)
    platforms = models.ManyToManyField(Platform, related_name="games", blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
