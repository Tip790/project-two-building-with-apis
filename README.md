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
