from django.urls import path

from . import views

app_name = "library"

urlpatterns = [
    path("", views.my_library, name="my_library"),
]
