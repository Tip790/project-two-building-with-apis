# project-two-building-with-apis
CIDM 3312 Project #2 Building With APIs

**Game Backlog Tracker:** a Django app for finding games in the [RAWG](https://rawg.io) database and tracking your own backlog. Game data comes from RAWG.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14.

```sh
uv sync
cp .env.example .env    # then fill in DJANGO_SECRET_KEY and RAWG_API_KEY
uv run python manage.py migrate
uv run python manage.py createsuperuser   # optional, for /admin/
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/.

The `.env` file is git-ignored. `.env.example` documents its three settings:

| Setting | Required? | What it does |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Yes | The app won't start without it. `.env.example` shows a command to generate one. |
| `DJANGO_DEBUG` | No | Off unless `true`. Turn it on locally, so the development server serves the static files. |
| `RAWG_API_KEY` | No | Without it, search shows "RAWG isn't configured". Get a free key at https://rawg.io/apidocs. |

## Demo data

```sh
uv run python manage.py seed_demo
```

This creates two demo users. Their password is `demo-password-local-only`, **for local demos only**:

| User | Library | Games |
| --- | --- | --- |
| `demo_public` | Public, at http://127.0.0.1:8000/u/demo_public/ | 6 |
| `demo_private` | Private (a 404 for everyone else) | 4 |

The 8 games are saved through the same save flow as the Add button, with varied statuses, ratings, hours, platforms and notes. Two games are in both libraries.

- **The first run needs RAWG** (a `RAWG_API_KEY` and an internet connection), because it fetches each game once. After that, the demo data works offline.
- If RAWG fails partway, the command stops with RAWG's message. Run it again once RAWG is reachable, and it picks up where it left off.
- **Running it again resets the demo**: both users' Public/Private setting, their password and their seeded entries go back to the values above. Games you added to a demo library yourself are kept. It never creates duplicates.

No RAWG data is committed to the repository. It is fetched by this command.

## Offline demo (RAWG unreachable)

Saved libraries and detail pages are read from the local database, so they keep working without RAWG.

1. Run `seed_demo` once while online (see above).
2. Make RAWG unreachable in one of two ways:
   - Turn off your network connection.
   - Or set `RAWG_API_KEY=` (blank) in `.env` and restart `runserver`.
3. Check that these still work:
   - http://127.0.0.1:8000/u/demo_public/: search, filter, sort and open a game's detail page.
   - Log in as `demo_private`. My Library, its detail pages, and editing and saving an entry all work.
   - http://127.0.0.1:8000/api/entries/ works in the browser while you're logged in.
4. Only the parts that need RAWG are affected:
   - The home page search shows a friendly alert where results would go, not an error page.
   - Adding a game that nobody has saved yet shows "Couldn't add this game". A game someone else already saved can still be added.
   - With the network off, cover images fall back to a placeholder.

## API

The API is built with Django REST Framework, under `/api/`. Every request needs authentication: a token, or your website session (so you can explore the API in the browser while logged in). The examples use `curl` (on Windows PowerShell, type `curl.exe`), with `YOUR_TOKEN` as a placeholder. Never commit a real token.

**Get a token** by sending your username and password, or copy it from the **Settings** page. Settings can also regenerate the token, and the old one stops working at once.

```sh
curl -X POST http://127.0.0.1:8000/api/token/ -d "username=demo_public" -d "password=demo-password-local-only"
# {"token": "YOUR_TOKEN"}
```

**Your entries**: `/api/entries/` and `/api/entries/<id>/`

```sh
# List, with the same filters as My Library
curl -H "Authorization: Token YOUR_TOKEN" "http://127.0.0.1:8000/api/entries/?status=playing&sort=rating"

# Create: send a RAWG game id plus your own fields
curl -X POST -H "Authorization: Token YOUR_TOKEN" -H "Content-Type: application/json" \
     -d '{"rawg_id": 3328, "status": "playing", "rating": 5}' http://127.0.0.1:8000/api/entries/

# Update some fields, or delete
curl -X PATCH -H "Authorization: Token YOUR_TOKEN" -H "Content-Type: application/json" \
     -d '{"hours_played": "12.5"}' http://127.0.0.1:8000/api/entries/1/
curl -X DELETE -H "Authorization: Token YOUR_TOKEN" http://127.0.0.1:8000/api/entries/1/
```

**Someone's shared library** (read-only): `/api/users/<username>/entries/`. It returns a Public library, or your own. A Private library and a username that doesn't exist both get the same 404.

**Fields:**
- `status` is one of `want_to_play`, `playing`, `completed` or `dropped`.
- `rating` is 1–5 or `null`.
- `hours_played` is 0–10,000 or `null`.
- `platform` is the `id` of one of the game's platforms.
- `notes` is free text.
- Each entry includes the stored `game` (name, cover, release date, Metacritic score, description, genres and platforms). The game can't be changed after create.

**Filters and sort** (the same as the website):
- `q`: name search
- `status`
- `genre` and `platform`: by `id`
- `min_rating`
- `sort`: `added` (the default, newest first), `name`, `rating`, `hours` or `released`
- `page`

Lists hold 12 entries per page, with `count`, `next`, `previous`, `results` and a RAWG `attribution`.

**Errors:**
- 401: no credentials or a bad token
- 404: an entry that isn't yours
- 400: invalid fields, with the same messages as the website. A game already in your library gets `{"rawg_id": ["Already in your library."]}`.
- 503: RAWG is unavailable while creating an entry for a game that isn't stored yet. Nothing is saved.

### Example client script

`scripts/backlog_api.py` calls the API from Python. Start `runserver` first. The script needs your token, which it can get in three ways:
- `BACKLOG_API_TOKEN` in `.env` or your environment
- `--token YOUR_TOKEN`
- `--username demo_public`, which prompts for the password

```sh
# List entries with query parameters (--q, --status, --min-rating, --sort, --page)
uv run python scripts/backlog_api.py list --status playing --sort rating

# Change one field of one entry (status, rating, hours_played, platform or notes) and print it before and after
uv run python scripts/backlog_api.py update 3 rating 4
uv run python scripts/backlog_api.py update 3 rating null    # clear it
```

## Styles (Tailwind CSS + DaisyUI)

The compiled stylesheet, `static/css/app.css`, is committed, so you only need these steps when you change templates or styles. The build uses the Tailwind **standalone CLI**, so Node.js isn't needed.

1. Download the Tailwind CLI v4.3.3 for your system from the [release page](https://github.com/tailwindlabs/tailwindcss/releases/tag/v4.3.3) and save it in the `tailwind/` folder as `tailwindcss.exe` (Windows) or `tailwindcss` (macOS/Linux; run `chmod +x tailwind/tailwindcss`). The executable is git-ignored. On Windows (PowerShell):

   ```powershell
   Invoke-WebRequest https://github.com/tailwindlabs/tailwindcss/releases/download/v4.3.3/tailwindcss-windows-x64.exe -OutFile tailwind\tailwindcss.exe
   ```

2. Rebuild the stylesheet once, or keep it rebuilding while you edit:

   ```sh
   tailwind/tailwindcss -i tailwind/input.css -o static/css/app.css --minify
   tailwind/tailwindcss -i tailwind/input.css -o static/css/app.css --watch
   ```

DaisyUI 5.7.50 is loaded by `tailwind/input.css` from the committed plugin file `tailwind/daisyui.mjs`. HTMX 2.0.11 is a local file, `static/js/htmx.min.js`, so pages don't depend on a CDN.

## Tests and checks

```sh
uv run pytest
uv run ruff check .
uv run ruff format .
```

The tests never call RAWG and don't read your `.env` file.
