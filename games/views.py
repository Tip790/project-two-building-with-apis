from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils.cache import patch_vary_headers
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from library.models import LibraryEntry
from library.services import AlreadyInLibrary
from library.services import add_to_library as save_to_library

from . import rawg


def _page_number(raw: str | None) -> int:
    """Turn the ?page= value into a page number, falling back to 1."""
    try:
        return max(int(raw), 1)
    except TypeError, ValueError:
        return 1


def _wants_fragment(request) -> bool:
    """True for HTMX swaps. History restores need the full page."""
    return (
        request.headers.get("HX-Request") == "true"
        and request.headers.get("HX-History-Restore-Request") != "true"
    )


def home(request):
    """The home page: a RAWG game search box, a tagline, and search results.

    HTMX requests get only the results fragment; everything else gets the
    full page, so the search also works as a plain form submission.
    """
    query = request.GET.get("q", "").strip()
    context = {"query": query, "search": None, "error": None, "saved_ids": set()}
    if query:
        try:
            context["search"] = rawg.search_games(
                query, page=_page_number(request.GET.get("page"))
            )
        except rawg.RawgError as error:
            context["error"] = str(error)
    if context["search"] and request.user.is_authenticated:
        result_ids = [game["id"] for game in context["search"]["results"]]
        context["saved_ids"] = set(
            LibraryEntry.objects.filter(
                user=request.user, game__rawg_id__in=result_ids
            ).values_list("game__rawg_id", flat=True)
        )

    if _wants_fragment(request):
        template = "games/partials/search_results.html"
    else:
        template = "games/home.html"
    response = render(request, template, context)
    # Browsers must not reuse a cached fragment for a full page load.
    patch_vary_headers(response, ["HX-Request"])
    return response


@login_required
@require_POST
def add_to_library(request):
    """Save a search result to the user's library with one click.

    HTMX requests get the swapped add control back; a plain POST gets a
    flash message and a redirect to the page it came from.
    """
    try:
        rawg_id = int(request.POST.get("rawg_id", ""))
    except ValueError:
        return HttpResponseBadRequest("A RAWG game id is required.")
    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}
    ):
        next_url = ""

    state, message = "in_library", ""
    try:
        entry = save_to_library(request.user, rawg_id)
    except AlreadyInLibrary as duplicate:
        entry, state = duplicate.entry, "already"
    except rawg.RawgError as error:
        state, message = "", f"Couldn't add this game: {error}"

    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "games/partials/add_button.html",
            {"rawg_id": rawg_id, "state": state, "message": message, "next": next_url},
        )
    if message:
        messages.error(request, message)
    elif state == "already":
        messages.info(request, f"Already in your library: {entry.game.name}.")
    else:
        messages.success(request, f"Added {entry.game.name} to your library.")
    return redirect(next_url or "games:home")
