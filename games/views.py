from django.shortcuts import render
from django.utils.cache import patch_vary_headers

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
    context = {"query": query, "search": None, "error": None}
    if query:
        try:
            context["search"] = rawg.search_games(
                query, page=_page_number(request.GET.get("page"))
            )
        except rawg.RawgError as error:
            context["error"] = str(error)

    if _wants_fragment(request):
        template = "games/partials/search_results.html"
    else:
        template = "games/home.html"
    response = render(request, template, context)
    # Browsers must not reuse a cached fragment for a full page load.
    patch_vary_headers(response, ["HX-Request"])
    return response
