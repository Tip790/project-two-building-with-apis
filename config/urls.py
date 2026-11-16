from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("games.urls")),
    path("accounts/", include("accounts.urls")),
    path("library/", include("library.urls")),
    path("admin/", admin.site.urls),
]
