from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class LibraryUserAdmin(UserAdmin):
    fieldsets = (*UserAdmin.fieldsets, ("Library", {"fields": ("library_is_public",)}))
    list_display = (*UserAdmin.list_display, "library_is_public")
    list_filter = (*UserAdmin.list_filter, "library_is_public")
