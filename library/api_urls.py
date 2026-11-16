"""API URLs, under /api/."""

from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import api

app_name = "api"

router = DefaultRouter()
router.register("entries", api.EntryViewSet, basename="entry")

urlpatterns = [
    path("token/", obtain_auth_token, name="token"),
    path("", include(router.urls)),
]
