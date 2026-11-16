# Game Backlog Tracker

A Django web app and REST API for saving games from the RAWG database to a personal library and tracking them.

## Stack

- Python, managed with uv
- Django, Django REST Framework, SQLite
- Tailwind CSS (standalone CLI, no Node.js) with DaisyUI; HTMX served locally (no CDN)
- pytest with pytest-django; Ruff

## Architecture decisions

- A custom user model, set up before the first migration.
- Saved RAWG game data is stored locally. Library features work without RAWG.
- The website and the API share the same save, validation, and filtering logic.
- Every HTMX interaction has a plain-HTTP fallback.
- Secrets are loaded from an untracked environment file with `python-dotenv`. They are never committed.
- Tests never call RAWG for real.
- Local use only; no deployment.

## References

- PRD: `prd/game-backlog-tracker.md`
- Plan: `plans/game-backlog-tracker.md`
- Prototype: `prototypes/library-sharing-urls.html`
