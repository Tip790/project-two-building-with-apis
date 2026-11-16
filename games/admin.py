from django.contrib import admin

from .models import Game, Genre, Platform


@admin.register(Genre, Platform)
class RawgNamedAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "rawg_id")
    search_fields = ("name", "slug")


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("name", "released", "metacritic", "rawg_id")
    search_fields = ("name", "slug")
    list_filter = ("genres", "platforms")
    filter_horizontal = ("genres", "platforms")
