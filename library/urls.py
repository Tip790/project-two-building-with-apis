from django.urls import path

from . import views

app_name = "library"

urlpatterns = [
    path("", views.my_library, name="my_library"),
    path("<int:pk>/", views.entry_detail, name="entry_detail"),
    path("<int:pk>/delete/", views.entry_delete, name="entry_delete"),
]
