from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import LibraryEntry


@login_required
def my_library(request):
    """The signed-in user's saved games, newest first, from local data only."""
    entries = (
        LibraryEntry.objects.filter(user=request.user)
        .select_related("game", "platform")
        .order_by("-created_at")
    )
    return render(request, "library/my_library.html", {"entries": entries})
