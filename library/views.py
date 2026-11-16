from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EntryForm
from .models import LibraryEntry


def _is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _own_entry_or_404(request, pk) -> LibraryEntry:
    """The signed-in user's entry with this pk; anyone else's is a 404."""
    return get_object_or_404(
        LibraryEntry.objects.select_related("game", "platform"),
        pk=pk,
        user=request.user,
    )


@login_required
def my_library(request):
    """The signed-in user's saved games, newest first, from local data only."""
    entries = (
        LibraryEntry.objects.filter(user=request.user)
        .select_related("game", "platform")
        .order_by("-created_at")
    )
    return render(request, "library/my_library.html", {"entries": entries})


@login_required
def entry_detail(request, pk):
    """The owner's page for one entry: stored game details plus the edit form."""
    entry = _own_entry_or_404(request, pk)
    saved = False
    if request.method == "POST":
        form = EntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            saved = True
            if not _is_htmx(request):
                messages.success(request, "Saved.")
                return redirect("library:entry_detail", pk=entry.pk)
        else:
            # A failed save must not leave half-applied values on the
            # instance the page is rendered from.
            entry.refresh_from_db()
    else:
        form = EntryForm(instance=entry)

    context = {"entry": entry, "form": form, "saved": saved}
    if _is_htmx(request):
        return render(request, "library/partials/entry_form.html", context)
    return render(request, "library/entry_detail.html", context)


@login_required
def entry_delete(request, pk):
    """Remove an entry after confirmation, then return to My Library.

    The detail page confirms in a modal; a GET here is the no-JavaScript
    confirmation page.
    """
    entry = _own_entry_or_404(request, pk)
    if request.method == "POST":
        name = entry.game.name
        entry.delete()
        messages.success(request, f"Removed {name} from your library.")
        return redirect("library:my_library")
    return render(request, "library/entry_confirm_delete.html", {"entry": entry})
