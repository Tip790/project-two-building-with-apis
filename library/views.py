from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.cache import patch_vary_headers

from .filters import EntryFilter
from .forms import EntryForm
from .models import LibraryEntry

ENTRIES_PER_PAGE = 12


def _is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _wants_fragment(request) -> bool:
    """True for HTMX swaps. History restores need the full page."""
    return (
        _is_htmx(request)
        and request.headers.get("HX-History-Restore-Request") != "true"
    )


def _own_entry_or_404(request, pk) -> LibraryEntry:
    """The signed-in user's entry with this pk, for editing.

    Anyone else is refused: a 403 if the entry is in a Public library (its
    existence is no secret), and a 404 if it's Private, so a Private library
    stays indistinguishable from one that doesn't exist.
    """
    entry = get_object_or_404(
        LibraryEntry.objects.select_related("game", "platform", "user"), pk=pk
    )
    if entry.user == request.user:
        return entry
    if entry.user.library_is_public:
        raise PermissionDenied
    raise Http404


def _browse(request, owner, template, extra_context=None):
    """Search, filter, sort and page one user's library, from local data only.

    HTMX requests get only the results grid; everything else gets the full
    page. Shared by My Library and the shared library page.
    """
    own_entries = LibraryEntry.objects.filter(user=owner)
    filterset = EntryFilter(
        request.GET, queryset=own_entries.select_related("game", "platform")
    )
    page = Paginator(filterset.qs, ENTRIES_PER_PAGE).get_page(request.GET.get("page"))
    context = {
        "filterset": filterset,
        "page": page,
        "entries": page.object_list,
        "library_is_empty": not own_entries.exists(),
        "library_owner": owner,
        **(extra_context or {}),
    }
    if _wants_fragment(request):
        template = "library/partials/library_results.html"
    response = render(request, template, context)
    # Browsers must not reuse a cached fragment for a full page load.
    patch_vary_headers(response, ["HX-Request"])
    return response


@login_required
def my_library(request):
    """The signed-in user's saved games, with edit links."""
    return _browse(request, request.user, "library/my_library.html")


def _visible_library_owner_or_404(request, username):
    """The owner of the library at /u/<username>/, if the viewer may see it.

    A Private library is visible only to its owner. To everyone else it
    raises the same 404 as a username that doesn't exist, so nobody can tell
    the account is there.
    """
    owner = get_user_model().objects.filter(username=username).first()
    if owner is None or not (owner.library_is_public or owner == request.user):
        raise Http404
    return owner


def shared_library(request, username):
    """A read-only view of someone's library, with the same browsing."""
    owner = _visible_library_owner_or_404(request, username)
    return _browse(request, owner, "library/shared_library.html", {"read_only": True})


def shared_entry_detail(request, username, pk):
    """A read-only detail page for one entry in a shared library."""
    owner = _visible_library_owner_or_404(request, username)
    entry = get_object_or_404(
        LibraryEntry.objects.select_related("game", "platform"), pk=pk, user=owner
    )
    return render(
        request, "library/entry_detail.html", {"entry": entry, "read_only": True}
    )


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
