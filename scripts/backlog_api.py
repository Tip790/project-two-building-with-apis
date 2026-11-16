"""A small client for the Game Backlog Tracker's own REST API.

Run the site first (`uv run python manage.py runserver`), then:

    uv run python scripts/backlog_api.py list --status playing --sort rating
    uv run python scripts/backlog_api.py update 3 rating 4

Authentication uses a DRF token, from the BACKLOG_API_TOKEN environment
variable (or .env), or from --token. Get one from the Settings page, or let the
script ask for it with --username (it prompts for the password).
Never commit a real token.
"""

import argparse
import getpass
import os
import sys

import requests
from dotenv import load_dotenv

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 10

# The entry fields a client may change, and how to read them from the command line.
UPDATABLE_FIELDS = ("status", "rating", "hours_played", "platform", "notes")
STATUSES = ("want_to_play", "playing", "completed", "dropped")
SORTS = ("added", "name", "rating", "hours", "released")


class ApiError(Exception):
    """An API request failed. The message is safe to print."""


class BacklogApi:
    """Calls /api/entries/ with token authentication."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Token {token}",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(
                method, url, headers=self.headers, timeout=TIMEOUT_SECONDS, **kwargs
            )
        except requests.ConnectionError as exc:
            raise ApiError(
                f"Could not reach {self.base_url}. Is `manage.py runserver` running?"
            ) from exc
        except requests.Timeout as exc:
            raise ApiError("The API took too long to respond.") from exc
        return _json_or_error(response)

    def list_entries(self, params: dict) -> dict:
        return self._request("GET", "/api/entries/", params=params)

    def get_entry(self, entry_id: int) -> dict:
        return self._request("GET", f"/api/entries/{entry_id}/")

    def update_entry(self, entry_id: int, field: str, value) -> dict:
        # PATCH changes only the field sent; everything else stays as it is.
        return self._request("PATCH", f"/api/entries/{entry_id}/", json={field: value})


def obtain_token(base_url: str, username: str, password: str) -> str:
    """Swap a username and password for the user's API token."""
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/api/token/",
            data={"username": username, "password": password},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise ApiError(f"Could not reach {base_url} to get a token.") from exc
    return _json_or_error(response)["token"]


def _json_or_error(response: requests.Response) -> dict:
    """Return the JSON body, or raise ApiError with the API's own message."""
    try:
        body = response.json()
    except ValueError:
        body = None
    if response.ok and isinstance(body, dict):
        return body
    if response.status_code == 401:
        raise ApiError("401: the token is missing or wrong. Check BACKLOG_API_TOKEN.")
    if response.status_code == 404:
        raise ApiError("404: no such entry in your library.")
    if isinstance(body, dict):
        # DRF errors: {"detail": "..."} or {"field": ["message", ...]}
        details = "; ".join(
            f"{key}: {' '.join(value) if isinstance(value, list) else value}"
            for key, value in body.items()
        )
        raise ApiError(f"{response.status_code}: {details}")
    raise ApiError(f"{response.status_code}: the API returned an unexpected response.")


def parse_value(field: str, raw: str):
    """Turn a command-line value into what the API expects for that field."""
    if raw.lower() in ("null", "none", "") and field != "notes":
        return None
    if field in ("rating", "platform"):
        try:
            return int(raw)
        except ValueError:
            raise ApiError(f"{field} must be a whole number or null.") from None
    return raw


def format_entry(entry: dict) -> str:
    """One entry as a few readable lines."""
    game = entry.get("game") or {}
    platform = entry.get("platform") or {}
    rating = entry.get("rating")
    year = (game.get("released") or "")[:4] or "year unknown"
    lines = [
        f"#{entry['id']}  {game.get('name', '?')} ({year})",
        f"    status: {entry.get('status')}   "
        f"rating: {'★' * rating if rating else 'unrated'}   "
        f"hours: {entry.get('hours_played') or '-'}   "
        f"platform: {platform.get('name', '-')}",
    ]
    if entry.get("notes"):
        lines.append(f"    notes: {entry['notes']}")
    return "\n".join(lines)


def show_entry_fields(entry: dict, field: str) -> str:
    value = entry.get(field)
    if field == "platform" and isinstance(value, dict):
        value = f"{value['name']} (id {value['id']})"
    return f"{field} = {value!r}   (updated_at {entry.get('updated_at')})"


def run_list(api: BacklogApi, args) -> None:
    params = {
        key: value
        for key, value in {
            "q": args.q,
            "status": args.status,
            "min_rating": args.min_rating,
            "sort": args.sort,
            "page": args.page,
        }.items()
        if value is not None
    }
    data = api.list_entries(params)
    shown = ", ".join(f"{k}={v}" for k, v in params.items()) or "none"
    print(f"GET /api/entries/  (query: {shown})")
    print(f"{data['count']} matching entries, showing {len(data['results'])}:\n")
    for entry in data["results"]:
        print(format_entry(entry))
    if data.get("next"):
        print(f"\nMore results: --page {(args.page or 1) + 1}")
    attribution = data.get("attribution") or {}
    if attribution:
        print(f"\n{attribution.get('text')} {attribution.get('url')}")


def run_update(api: BacklogApi, args) -> None:
    value = parse_value(args.field, args.value)
    before = api.get_entry(args.entry_id)
    after = api.update_entry(args.entry_id, args.field, value)
    print(f"PATCH /api/entries/{args.entry_id}/  {{{args.field!r}: {value!r}}}\n")
    print("Before:")
    print(format_entry(before))
    print(f"    {show_entry_fields(before, args.field)}\n")
    print("After:")
    print(format_entry(after))
    print(f"    {show_entry_fields(after, args.field)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--token", help="API token (default: BACKLOG_API_TOKEN)")
    parser.add_argument("--username", help="get a token by logging in as this user")
    commands = parser.add_subparsers(dest="command", required=True)

    list_cmd = commands.add_parser("list", help="list your entries, with filters")
    list_cmd.add_argument("--q", help="name search")
    list_cmd.add_argument("--status", choices=STATUSES)
    list_cmd.add_argument("--min-rating", type=int, choices=range(1, 6))
    list_cmd.add_argument("--sort", choices=SORTS)
    list_cmd.add_argument("--page", type=int)

    update_cmd = commands.add_parser("update", help="change one field of one entry")
    update_cmd.add_argument("entry_id", type=int)
    update_cmd.add_argument("field", choices=UPDATABLE_FIELDS)
    update_cmd.add_argument("value", help="the new value; 'null' clears it")
    return parser


def main(argv=None) -> int:
    # Windows consoles default to cp1252, which can't print ★.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        token = args.token or os.environ.get("BACKLOG_API_TOKEN")
        if args.username:
            password = getpass.getpass(f"Password for {args.username}: ")
            token = obtain_token(args.base_url, args.username, password)
        if not token:
            raise ApiError(
                "No API token. Set BACKLOG_API_TOKEN (copy it from the Settings "
                "page), or pass --token or --username."
            )
        api = BacklogApi(args.base_url, token)
        if args.command == "list":
            run_list(api, args)
        else:
            run_update(api, args)
    except ApiError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    # Only a real run reads .env (for BACKLOG_API_TOKEN); tests never do.
    load_dotenv()
    sys.exit(main())
