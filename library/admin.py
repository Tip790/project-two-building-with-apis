from django.contrib import admin

from .models import LibraryEntry


@admin.register(LibraryEntry)
class LibraryEntryAdmin(admin.ModelAdmin):
    list_display = ("game", "user", "status", "rating", "hours_played", "created_at")
    list_filter = ("status", "rating")
    search_fields = ("game__name", "user__username")
    raw_id_fields = ("game",)
