from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("games.urls")),
    path("", include("accounts.urls")),
    path("library/", include("library.urls")),
    path("u/", include("library.shared_urls")),
    path("api/", include("library.api_urls")),
    path("admin/", admin.site.urls),
]
