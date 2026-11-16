from django.urls import path

from . import views

app_name = "games"

urlpatterns = [
    path("", views.home, name="home"),
    path("games/add/", views.add_to_library, name="add"),
]
