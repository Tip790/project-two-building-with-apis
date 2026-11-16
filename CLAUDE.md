# Game Backlog Tracker

A Django web app and REST API for saving games from the RAWG database to a personal library and tracking them.

## Stack

- Python 3.14, managed with uv
- Django 6.1, Django REST Framework, SQLite
- Tailwind CSS (standalone CLI, no Node.js) with DaisyUI; HTMX served locally (no CDN)
- pytest with pytest-django; Ruff

## Commands

- Run: `uv run python manage.py runserver` (needs `DJANGO_SECRET_KEY` in `.env`)
- Test: `uv run pytest` · Lint/format: `uv run ruff check .` and `uv run ruff format .`
- Add a package: `uv add --system-certs <pkg>` (this machine's network inspects HTTPS)
- Rebuild CSS after changing template classes: `tailwind/tailwindcss -i tailwind/input.css -o static/css/app.css --minify` (the compiled CSS is committed)

## Architecture decisions

- A custom user model, `accounts.User`.
- Saved RAWG game data is stored locally. Library features work without RAWG.
- The website and the API share the same save, validation, and filtering logic.
- Every HTMX interaction has a plain-HTTP fallback.
- Secrets are loaded from an untracked `.env` with `python-dotenv`. They are never committed.
- Tests use `config.test_settings` (dummy RAWG key, never reads `.env`) and never call RAWG for real.
- URL names are app-namespaced (e.g. `accounts:login`, `games:home`).
- `archive/` is a read-only record, excluded from pytest and Ruff.
- Local use only; no deployment.

## References

- PRD: `prd/game-backlog-tracker.md`
- Plan: `plans/game-backlog-tracker.md`
- Prototype: `prototypes/library-sharing-urls.html`
