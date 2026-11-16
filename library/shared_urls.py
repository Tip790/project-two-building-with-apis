"""Read-only shared library pages, under /u/<username>/."""

from django.urls import path

from . import views

app_name = "shared"

urlpatterns = [
    path("<str:username>/", views.shared_library, name="library"),
    path("<str:username>/<int:pk>/", views.shared_entry_detail, name="entry_detail"),
]
