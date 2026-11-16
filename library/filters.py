"""The library filter set, shared by My Library, shared libraries, and the API."""

import django_filters
from django import forms
from django.db.models import F
from django.db.models.functions import Lower

from games.models import Genre, Platform

from .models import LibraryEntry


class EntryFilter(django_filters.FilterSet):
    SORTS = {
        "added": [F("created_at").desc()],
        "name": [Lower("game__name")],
        "rating": [F("rating").desc(nulls_last=True)],
        "hours": [F("hours_played").desc(nulls_last=True)],
        "released": [F("game__released").desc(nulls_last=True)],
    }

    q = django_filters.CharFilter(
        field_name="game__name", lookup_expr="icontains", label="Name"
    )
    status = django_filters.ChoiceFilter(
        choices=LibraryEntry.Status.choices, empty_label="Any status"
    )
    genre = django_filters.ModelChoiceFilter(
        field_name="game__genres", queryset=Genre.objects.all(), empty_label="Any genre"
    )
    # The platform the user plays the game on, not every platform it's out on.
    platform = django_filters.ModelChoiceFilter(
        queryset=Platform.objects.all(), empty_label="Any platform"
    )
    min_rating = django_filters.NumberFilter(
        field_name="rating",
        lookup_expr="gte",
        label="Minimum rating",
        widget=forms.NumberInput(attrs={"min": 1, "max": 5}),
    )
    sort = django_filters.ChoiceFilter(
        choices=[
            ("added", "Date added (newest)"),
            ("name", "Name (A–Z)"),
            ("rating", "Rating (highest)"),
            ("hours", "Hours played (most)"),
            ("released", "Release date (newest)"),
        ],
        method="sort_entries",
        empty_label=None,
        label="Sort by",
    )

    def __init__(self, data=None, queryset=None, **kwargs):
        super().__init__(data, queryset=queryset, **kwargs)
        # Offer only the genres and platforms in the library being browsed.
        entries = self.queryset.values("pk")
        self.filters["genre"].queryset = Genre.objects.filter(
            games__entries__in=entries
        ).distinct()
        self.filters["platform"].queryset = Platform.objects.filter(
            entries__in=entries
        ).distinct()

    def sort_entries(self, queryset, name, value):
        # Most useful first; blank values always sort last. pk breaks ties so
        # pages never overlap or skip entries.
        return queryset.order_by(*self.SORTS.get(value, self.SORTS["added"]), "-pk")

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if not self.form.cleaned_data.get("sort"):
            queryset = self.sort_entries(queryset, "sort", "added")
        return queryset

    class Meta:
        model = LibraryEntry
        fields = []
