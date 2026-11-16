"""API serializers. Game details are nested read-only inside each entry."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from rest_framework import exceptions, serializers

from games import rawg
from games.models import Game, Genre, Platform
from games.services import get_or_fetch_game

from .models import LibraryEntry
from .services import ALREADY_IN_LIBRARY, AlreadyInLibrary, add_to_library
from .validation import validate_platform_for_game


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


class PlatformField(serializers.PrimaryKeyRelatedField):
    """Written as a platform's primary key, shown as the full platform.

    The key is the same `id` the API shows and the website's `platform`
    filter uses.
    """

    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        return PlatformSerializer(value).data

    def get_choices(self, cutoff=None):
        # The browsable API's dropdown needs hashable keys, not platform dicts.
        queryset = self.get_queryset()
        if cutoff is not None:
            queryset = queryset[:cutoff]
        return {item.pk: self.display_value(item) for item in queryset}


class RawgUnavailable(exceptions.APIException):
    """RAWG failed while saving a game that isn't stored yet."""

    status_code = 503
    default_code = "rawg_unavailable"


class EntrySerializer(serializers.ModelSerializer):
    """One library entry, created from a RAWG id through the shared save flow."""

    rawg_id = serializers.IntegerField(write_only=True)
    game = GameSerializer(read_only=True)
    platform = PlatformField(
        queryset=Platform.objects.all(), allow_null=True, required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            # An entry's game is fixed once it's created.
            self.fields["rawg_id"].read_only = True

    def build_standard_field(self, field_name, model_field):
        """Keep the model's own range validators, and so its messages.

        DRF swaps a model's MinValueValidator/MaxValueValidator for its own
        min_value/max_value checks, which say "Ensure this value is ...". The
        website form reports the model's messages, so the API must too.
        """
        field_class, kwargs = super().build_standard_field(field_name, model_field)
        kwargs.pop("min_value", None)
        kwargs.pop("max_value", None)
        range_validators = [
            validator
            for validator in model_field.validators
            if isinstance(validator, (MinValueValidator, MaxValueValidator))
        ]
        kwargs["validators"] = [*kwargs.get("validators", []), *range_validators]
        return field_class, kwargs

    def validate(self, attrs):
        if self.instance is not None:
            game = self.instance.game
        else:
            try:
                # Reuses a stored game with no RAWG call; otherwise fetches it.
                game = get_or_fetch_game(attrs["rawg_id"])
            except rawg.RawgNotFound as error:
                # The client sent a bad id; RAWG itself is fine.
                raise serializers.ValidationError({"rawg_id": [str(error)]}) from error
            except rawg.RawgError as error:
                raise RawgUnavailable(str(error)) from error
            user = self.context["request"].user
            if LibraryEntry.objects.filter(user=user, game=game).exists():
                raise serializers.ValidationError({"rawg_id": [ALREADY_IN_LIBRARY]})
        if "platform" in attrs:
            try:
                validate_platform_for_game(game, attrs["platform"])
            except DjangoValidationError as error:
                raise serializers.ValidationError(error.message_dict) from error
        return attrs

    def create(self, validated_data):
        rawg_id = validated_data.pop("rawg_id")
        try:
            return add_to_library(
                self.context["request"].user, rawg_id, **validated_data
            )
        except AlreadyInLibrary as error:
            # Another request added it after validate() checked.
            raise serializers.ValidationError(
                {"rawg_id": [ALREADY_IN_LIBRARY]}
            ) from error

    class Meta:
        model = LibraryEntry
        fields = [
            "id",
            "rawg_id",
            "game",
            "status",
            "rating",
            "hours_played",
            "platform",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
