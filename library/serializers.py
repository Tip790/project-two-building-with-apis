"""API serializers. Game details are nested read-only inside each entry."""

from rest_framework import serializers

from games.models import Game, Genre, Platform

from .models import LibraryEntry


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["rawg_id", "name", "slug"]


class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = ["id", "rawg_id", "name", "slug"]


class GameSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    platforms = PlatformSerializer(many=True, read_only=True)

    class Meta:
        model = Game
        fields = [
            "rawg_id",
            "name",
            "slug",
            "background_image",
            "released",
            "metacritic",
            "description",
            "genres",
            "platforms",
        ]
        read_only_fields = fields


class EntrySerializer(serializers.ModelSerializer):
    game = GameSerializer(read_only=True)
    platform = PlatformSerializer(read_only=True)

    class Meta:
        model = LibraryEntry
        fields = [
            "id",
            "game",
            "status",
            "rating",
            "hours_played",
            "platform",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
