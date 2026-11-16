"""Search RAWG for video games from the console.

Run with:  uv run scripts/rawg_search.py

Search for a game, pick a result by number to see its details, and repeat.
Type q (or press Enter on an empty search) to quit.

Data from RAWG (https://rawg.io).
"""

import os
import sys

import requests
import truststore
from dotenv import load_dotenv

# Use the operating system's trusted certificates (e.g. the Windows store)
# instead of Python's bundled list. This keeps HTTPS working on machines where
# antivirus or network security software inspects secure connections.
truststore.inject_into_ssl()

BASE_URL = "https://api.rawg.io/api"
TIMEOUT_SECONDS = 10
PAGE_SIZE = 10
DESCRIPTION_LIMIT = 300
ATTRIBUTION = "Data from RAWG (https://rawg.io)"


class RawgError(Exception):
    """A RAWG request failed. The message is safe to show to the user."""


def _get(path: str, api_key: str, params: dict | None = None) -> dict:
    """Send a GET request to RAWG and return the JSON body.

    Every kind of failure is turned into a RawgError with a friendly message.
    """
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
        raise RawgError(f"The request to RAWG failed: {exc}") from exc

    status = response.status_code
    if status in (401, 403):
        raise RawgError(
            "RAWG rejected the API key. Check RAWG_API_KEY in your .env file."
        )
    if status == 404:
        raise RawgError("That game was not found on RAWG.")
    if status == 429:
        raise RawgError(
            "Rate limit reached (free plan: 20,000 requests a month). Try again later."
        )
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


def search_games(query: str, api_key: str) -> list[dict]:
    """Return up to PAGE_SIZE games matching the search phrase."""
    data = _get("/games", api_key, {"search": query, "page_size": PAGE_SIZE})
    return data.get("results") or []


def get_game(game_id: int, api_key: str) -> dict:
    """Return the full details for one game."""
    return _get(f"/games/{game_id}", api_key)


# ---------- formatting ----------


def _names(items: list | None, key: str | None = None) -> str:
    """Join the 'name' fields of a RAWG list, e.g. genres or platforms."""
    names = []
    for item in items or []:
        if key:  # platforms are nested: {"platform": {"name": ...}}
            item = item.get(key) or {}
        if item.get("name"):
            names.append(item["name"])
    return ", ".join(names) or "n/a"


def _shorten(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def format_result_line(number: int, game: dict) -> str:
    year = (game.get("released") or "")[:4] or "n/a"
    rating = game.get("rating")
    rating_text = f"★ {rating:.1f}" if rating else "★ n/a"
    platforms = _shorten(_names(game.get("platforms"), key="platform"), 60)
    name = game.get("name", "Untitled")
    return f"{number:>2}. {name} ({year})  {rating_text}  — {platforms}"


def format_details(game: dict) -> str:
    description = (game.get("description_raw") or "").strip()
    slug = game.get("slug")
    lines = [
        "",
        "=" * 60,
        game.get("name", "Untitled"),
        "=" * 60,
        f"Released:    {game.get('released') or 'n/a'}",
        f"Rating:      {game.get('rating') or 'n/a'} / 5",
        f"Metacritic:  {game.get('metacritic') or 'n/a'}",
        f"Genres:      {_names(game.get('genres'))}",
        f"Platforms:   {_names(game.get('platforms'), key='platform')}",
        f"Developers:  {_names(game.get('developers'))}",
        f"Playtime:    {game.get('playtime') or 'n/a'} hours (average)",
        "",
        _shorten(description, DESCRIPTION_LIMIT) if description else "No description.",
        "",
        f"Image:       {game.get('background_image') or 'n/a'}",
        f"RAWG page:   {f'https://rawg.io/games/{slug}' if slug else 'n/a'}",
        "-" * 60,
        ATTRIBUTION,
    ]
    return "\n".join(lines)


# ---------- console loop ----------


def pick_game(games: list[dict]) -> dict | None:
    """Ask the user to choose a result. Returns None to go back to searching."""
    while True:
        choice = input("\nPick a number for details (Enter to search again): ").strip()
        if not choice:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(games):
            return games[int(choice) - 1]
        print(f"Please type a number from 1 to {len(games)}, or press Enter.")


def run(api_key: str) -> None:
    print("RAWG game search. Type q to quit.")
    print(ATTRIBUTION)
    while True:
        query = input("\nSearch for a game (or 'q' to quit): ").strip()
        if query.lower() in ("", "q", "quit"):
            print("Goodbye!")
            return

        try:
            games = search_games(query, api_key)
        except RawgError as error:
            print(f"Error: {error}")
            continue

        if not games:
            print(f"No games found for '{query}'.")
            print("Try a different spelling or fewer words.")
            continue

        print()
        for number, game in enumerate(games, start=1):
            print(format_result_line(number, game))

        chosen = pick_game(games)
        if chosen is None:
            continue

        try:
            print(format_details(get_game(chosen["id"], api_key)))
        except RawgError as error:
            print(f"Error: {error}")


def main() -> int:
    # Windows may default to an encoding without characters like ★ and —.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()
    api_key = os.environ.get("RAWG_API_KEY", "").strip()
    if not api_key:
        print(
            "RAWG_API_KEY is not set. Copy .env.example to .env and add your key "
            "from https://rawg.io/apidocs"
        )
        return 1
    try:
        run(api_key)
    except KeyboardInterrupt, EOFError:
        print("\nGoodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
