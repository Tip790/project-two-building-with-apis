"""The RAWG API client used by the website and the API.

Every failure becomes a RawgError whose message is safe to show to users.
The API key comes from Django settings (RAWG_API_KEY).

Data from RAWG (https://rawg.io).
"""

import requests
import truststore
from django.conf import settings

# Use the operating system's trusted certificates (e.g. the Windows store)
# instead of Python's bundled list. This keeps HTTPS working on machines where
# antivirus or network security software inspects secure connections.
truststore.inject_into_ssl()

BASE_URL = "https://api.rawg.io/api"
TIMEOUT_SECONDS = 10
SEARCH_PAGE_SIZE = 12


class RawgError(Exception):
    """A RAWG request failed. The message is safe to show to the user."""


class RawgNotFound(RawgError):
    """RAWG answered, but has nothing at that address (a 404)."""


def _get(path: str, params: dict | None = None, not_found: str = "") -> dict:
    """Send a GET request to RAWG and return the JSON body."""
    api_key = settings.RAWG_API_KEY
    if not api_key:
        raise RawgError(
            "RAWG isn't configured on this site. The site operator needs to set "
            "RAWG_API_KEY in the .env file (see .env.example)."
        )
    query = {"key": api_key, **(params or {})}
    try:
        response = requests.get(
            f"{BASE_URL}{path}", params=query, timeout=TIMEOUT_SECONDS
        )
    except requests.Timeout as exc:
        raise RawgError(
            "RAWG took too long to respond. Try again in a moment."
        ) from exc
    except requests.exceptions.SSLError as exc:
        raise RawgError(
            "Could not make a secure connection to RAWG (certificate check failed)."
        ) from exc
    except requests.ConnectionError as exc:
        raise RawgError(
            "Could not reach RAWG. Check your internet connection and try again."
        ) from exc
    except requests.RequestException as exc:
        raise RawgError("The request to RAWG failed. Try again later.") from exc

    status = response.status_code
    if status in (401, 403):
        raise RawgError(
            "RAWG rejected the site's API key. The site operator needs to check "
            "RAWG_API_KEY in the .env file."
        )
    if status == 404:
        raise RawgNotFound(not_found or "RAWG could not find that.")
    if status == 429:
        raise RawgError("The site has reached RAWG's rate limit. Try again later.")
    if status >= 500:
        raise RawgError(
            f"RAWG is having problems right now (error {status}). Try again later."
        )
    if status >= 400:
        raise RawgError(f"RAWG could not handle the request (error {status}).")

    try:
        return response.json()
    except ValueError as exc:
        raise RawgError("RAWG sent an unexpected response.") from exc


def search_games(query: str, page: int = 1) -> dict:
    """Search RAWG by title and return one page of results.

    Returns a dict with "results" (a list of RAWG game dicts), "count",
    "page", "has_previous", and "has_next".
    """
    data = _get(
        "/games",
        {"search": query, "page": page, "page_size": SEARCH_PAGE_SIZE},
        not_found="There are no more results for that search.",
    )
    return {
        "results": data.get("results") or [],
        "count": data.get("count") or 0,
        "page": page,
        "has_previous": page > 1,
        "has_next": bool(data.get("next")),
    }


def get_game(rawg_id: int) -> dict:
    """Return the full details for one game, including its description."""
    return _get(f"/games/{rawg_id}", not_found="That game was not found on RAWG.")
