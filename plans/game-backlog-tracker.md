# Plan: Game Backlog Tracker

> Source PRD: `prd/game-backlog-tracker.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning apps**: a Django project configuration package plus three apps, as fixed by the PRD:
  - `accounts` — custom user model, sign-up, Settings page (sharing toggle, API token).
  - `games` — `Genre`, `Platform`, `Game` models; the RAWG client service; search page and add-to-library action.
  - `library` — `LibraryEntry` model, shared validation, shared `django-filter` filter set, website library/detail views, and the API (serializers, viewset, shared-library view).
- **Website URLs** (all named and app-namespaced):
  - `/` — RAWG search (home)
  - `/games/add/` — one-click add to library (POST, HTMX)
  - `/accounts/signup/`, `/accounts/login/`, `/accounts/logout/`, `/accounts/password_change/`
  - `/library/` — My Library (sign-in required)
  - `/library/<pk>/` — owner entry detail, edit, and delete
  - `/u/<username>/` — shared library (visible if Public or owned by the viewer; otherwise 404)
  - `/u/<username>/<pk>/` — read-only entry detail (same 404 rule)
  - `/settings/` — sharing toggle and API token
  - `/admin/`
- **API URLs**:
  - `/api/entries/`, `/api/entries/<pk>/` — the requester's own entries (model viewset)
  - `/api/users/<username>/entries/` — read-only shared library
  - `/api/token/` — token obtain (username + password)
- **Identifiers**: entries addressed by pk; libraries addressed by username; games identified externally by RAWG id. "View on RAWG" links built from the stored game slug.
- **Models**:
  - `accounts.User` — subclasses Django's abstract user; `library_is_public` boolean, default False. Must exist before the first migration.
  - `games.Genre`, `games.Platform` — RAWG id (unique), name, slug.
  - `games.Game` — RAWG id (unique), name, slug, background image URL, release date, Metacritic score, description; M2M to `Genre` and `Platform`. One shared row per game.
  - `library.LibraryEntry` — FK user, FK game, status (Want to Play / Playing / Completed / Dropped; default Want to Play), rating (optional 1–5), hours played (optional decimal, 0–10,000), FK platform (optional), notes, created/updated timestamps. Unique (user, game); check constraints on rating range and non-negative hours.
- **Authentication / authorization**:
  - Website: Django session auth with built-in login/logout/password-change views plus a small sign-up view.
  - API: DRF session + token authentication.
  - Permission outcomes: website edit of another user's Public library → 403; another user's Private library (or non-existent user) → identical 404; signed-out → redirect to login. API: other users' entries → 404 (writes scoped to the requester); unauthenticated → rejected.
- **Save flow** (shared by website and API): reuse a local `Game` by RAWG id with no RAWG call; otherwise fetch the RAWG detail endpoint once, create the `Game` plus missing `Genre`/`Platform` rows. A fetch failure becomes a friendly website message or an API 503.
- **Validation**: field validators + DB check constraints for rating and hours; one shared function for "platform must belong to the game", called from the model's clean and the serializer's validate.
- **Front end**: Tailwind (standalone CLI, git-ignored executable) with DaisyUI plugin; HTMX vendored as a pinned static file. Every HTMX interaction has a plain-HTTP fallback.
- **Configuration**: `python-dotenv`; Django secret key required, debug defaults off, RAWG key optional (missing → friendly message). SQLite. Local only.
- **Testing**: pytest + `pytest-django`, DRF API client; dummy RAWG key in test settings; no live RAWG calls (mock HTTP in client tests, mock search/get-game in view and API tests).
- **Prototype note**: the sharing prototype showed 403 for API edits to another user's Public entry; the PRD's uniform API 404 takes precedence.

---

## Phase 1: Walking skeleton + accounts

**User stories**: 1, 39, 40, 41, 70, 71, 72

### What to build

Stand up the Django project with the three apps, the custom user model (before any migration), environment-driven settings, and the admin. Build the base layout with a DaisyUI navbar and a site-wide RAWG attribution footer, with compiled Tailwind/DaisyUI and vendored HTMX served as static files. The home page renders a search box and tagline (search itself comes in Phase 2). Wire up sign-up, login, logout, and password change, with a navbar that shows Search / My Library / Settings / Log out (with username) when signed in and Search / Log in / Sign up when signed out. Move the console script and its tests into the "Initial API verification" archive folder with a short README, excluded from pytest and Ruff.

### Acceptance criteria

- [ ] Server starts with settings loaded from an untracked `.env`; a missing secret key fails loudly; debug defaults off; `.env.example` documents all three settings with placeholders
- [ ] Custom user model with `library_is_public` (default False) is the configured auth user model and is in the initial migration
- [ ] Home page renders the search box, tagline, navbar, and RAWG footer credit with a link
- [ ] A visitor can sign up, log in, log out, and change their password; navbar reflects signed-in state
- [ ] Admin is reachable and the user model is registered
- [ ] Old console script and tests live in the archive folder with a README and are excluded from pytest and Ruff
- [ ] README documents downloading and running the Tailwind standalone CLI
- [ ] pytest runs with `pytest-django` and a dummy RAWG key; tests cover home page rendering, footer attribution, and the sign-up/login/logout flow

---

## Phase 2: RAWG search

**User stories**: 2, 3, 4, 5, 6, 8, 9, 10, 28

### What to build

Move the RAWG client into the `games` app as a service exposing title search (with page) and get-game-by-id, keeping the friendly error class and messages, and reading the key from settings. The home page searches RAWG and shows result cards (cover, name, release year) with paging and a small RAWG credit under the results. The form works as a normal GET submission and also via HTMX, which swaps in only the results fragment; paging links behave the same way. RAWG failures and a missing key render as an alert where results would appear. Broken cover images fall back to a local placeholder.

### Acceptance criteria

- [ ] RAWG client tests (mocked HTTP) cover success parsing and each failure: timeout, SSL, connection error, 401/403, 404, 429, 5xx, bad JSON, and missing key
- [ ] Full-page search returns results with cover, name, and release year; HTMX requests return only the results fragment
- [ ] Paging works for both full-page and HTMX requests
- [ ] RAWG errors and the "RAWG isn't configured" message appear as an alert, never an error page
- [ ] RAWG credit with link appears under search results
- [ ] Cover images fall back to a placeholder when they fail to load
- [ ] View tests mock the search function; no live RAWG calls

---

## Phase 3: Add to library + minimal My Library

**User stories**: 7, 11, 12, 13, 14, 15, 16, 17, 29, 38 (partial), 42

### What to build

Add the `Genre`, `Platform`, `Game`, and `LibraryEntry` models with their constraints, and register them in the admin. Implement the shared save flow: reuse a local game by RAWG id, otherwise fetch RAWG detail once and create the game with its genres and platforms. Signed-in users see an "Add" button on each search result that saves with status Want to Play via HTMX and swaps to "In your library"; games already saved show "In your library" initially. Duplicates report "Already in your library"; RAWG failures for unsaved games show a friendly message. Signed-out visitors see "Sign in to add." A plain `/library/` page lists the current user's entries from local data, requires sign-in, and returns the user there after login.

### Acceptance criteria

- [ ] Migrations create all four models with unique (user, game) and check constraints for rating and hours
- [ ] Adding a new RAWG id calls get-game once and creates `Game`, `Genre`, and `Platform` rows linked correctly
- [ ] Adding an already-stored game makes no RAWG call, even when RAWG is mocked to fail
- [ ] A duplicate add returns "Already in your library" with no integrity error
- [ ] A RAWG failure for an unsaved game shows a friendly message and creates nothing
- [ ] The HTMX add swaps the button to "In your library" without leaving the page; a non-HTMX POST also works
- [ ] Signed-out visitors see "Sign in to add" and cannot POST an add
- [ ] `/library/` redirects signed-out visitors to login and back; signed-in users see only their own entries; it renders while RAWG is mocked to fail
- [ ] All models are registered in the admin

---

## Phase 4: Entry detail, edit, and delete

**User stories**: 18, 19, 20, 21, 22, 23, 24, 25, 26, 27

### What to build

An owner entry detail page at `/library/<pk>/` showing stored game details (cover, name, release date, genres, platforms, Metacritic score, description, "View on RAWG" link) alongside an edit form for status, rating, hours played, platform (limited to the game's platforms), and notes. The shared platform validator is called from the model's clean. The form saves via HTMX, returning a "Saved" alert or inline errors, and falls back to a normal POST. Delete uses a DaisyUI confirmation modal (with a non-JS confirmation fallback) and redirects to My Library. Library entries link to their detail page.

### Acceptance criteria

- [ ] Detail page shows all stored game fields and a "View on RAWG" link built from the slug, and renders while RAWG is mocked to fail
- [ ] Status, rating (or unrated), hours (or blank), platform, and notes can be saved
- [ ] Rating outside 1–5, negative hours, hours over the cap, and a platform not on the game are rejected with clear messages
- [ ] The shared platform validation function has direct unit tests
- [ ] HTMX save returns a "Saved" alert or inline errors; plain POST works too
- [ ] Delete requires confirmation, removes the entry, and redirects to My Library
- [ ] Another user's entry pk at `/library/<pk>/` is not editable or viewable through this URL

---

## Phase 5: Library browsing

**User stories**: 30, 31, 32, 33, 34, 35, 36, 37, 38

### What to build

A single `django-filter` filter set for library entries: name search; filters for status, genre, the entry's platform, and minimum rating; sorting by date added (default, newest first), name, rating, hours played, and release date. My Library uses it with 12-per-page pagination. Filter, sort, and page changes swap only the results grid via HTMX and push the URL, so any view is bookmarkable; a full page load of that URL shows the same results. All browsing uses local data only.

### Acceptance criteria

- [ ] Name search, and each of the status, genre, platform, and minimum-rating filters, narrows results correctly
- [ ] Each sort order works, with date added (newest first) as the default
- [ ] Results are paginated at 12 per page, and paging keeps the active filters
- [ ] HTMX requests return only the grid fragment and push the URL; loading that URL directly gives the same results
- [ ] Browsing works while RAWG is mocked to fail

---

## Phase 6: Sharing and privacy

**User stories**: 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53

### What to build

A Settings page at `/settings/` with a Public/Private toggle (Private by default) and the user's personal share link. `/u/<username>/` shows a library with the same browsing, filtering, sorting, and paging as My Library, read-only, when the library is Public or belongs to the viewer; otherwise it returns a 404 identical to a non-existent username. `/u/<username>/<pk>/` reuses the detail template without edit controls, including the owner's notes and rating, under the same rule. Edit attempts by non-owners are refused: 403 for a Public library, 404 for a Private one, login redirect when signed out.

### Acceptance criteria

- [ ] New users are Private; Settings toggles Public/Private and shows the share link
- [ ] A Public library and its entry detail pages are viewable by anyone, read-only, with no edit controls
- [ ] A Private library and a non-existent username both return an identical 404 to non-owners
- [ ] Switching to Private immediately makes a previously working share link 404
- [ ] Non-owner edit/delete attempts are 403 (Public), 404 (Private), or a login redirect (signed out)
- [ ] The shared library supports the same filters, sorting, and pagination as My Library

---

## Phase 7: API reads + tokens

**User stories**: 54, 55, 56, 59 (retrieve), 60, 61, 65, 66, 67

### What to build

Add Django REST Framework with session and token authentication. `/api/token/` returns a token for a username and password. The Settings page displays the user's token and can regenerate it. `/api/entries/` lists and retrieves only the requester's entries, with game details (including genres and platforms) nested read-only, using the shared filter set and a custom pagination class (12 per page) that adds a RAWG attribution field to list responses. Signed-in users can explore it in the browsable API with their session.

### Acceptance criteria

- [ ] `/api/token/` returns a token for valid credentials and rejects invalid ones
- [ ] Settings shows the token and regenerating it invalidates the old one
- [ ] Token-authenticated and session-authenticated requests can list and retrieve their own entries
- [ ] Unauthenticated requests are rejected; another user's entry pk returns 404
- [ ] Each entry nests game details with genres and platforms
- [ ] List responses are paginated at 12 and include a RAWG attribution field
- [ ] The same search, filter, and sort parameters as the website produce the same results
- [ ] Tests use placeholder tokens only

---

## Phase 8: API writes + shared library endpoint

**User stories**: 57, 58, 59, 62, 63, 64

### What to build

Enable create, update, partial update, and delete on `/api/entries/`. Create accepts a RAWG id plus the user's fields and uses the shared save flow; if RAWG is unavailable for an unsaved game, it returns 503 with the friendly message. The serializer uses the same field validators and calls the same shared platform validation function, so errors match the website. Duplicates return a clear "Already in your library" error. Add `/api/users/<username>/entries/`, a read-only list (with filters, pagination, and attribution) returned when the library is Public or belongs to the requester, and otherwise 404.

### Acceptance criteria

- [ ] Creating with a new RAWG id fetches and stores the game; an already-stored game makes no RAWG call
- [ ] A RAWG failure for an unsaved game returns 503 with the friendly message and creates nothing
- [ ] A duplicate create returns a clear "Already in your library" error, not a 500
- [ ] Update, partial update, and delete work on own entries; another user's entry returns 404
- [ ] Invalid rating, hours, and platform are rejected with the same rules and messages as the website form
- [ ] `/api/users/<username>/entries/` returns entries for a Public library or the requester's own, and an identical 404 for Private or non-existent users
- [ ] Switching to Private immediately makes the shared endpoint return 404

---

## Phase 9: Demo seed, offline demo, and README

**User stories**: 68, 69

### What to build

A `seed_demo` management command that creates a Private demo user and a Public demo user with a clearly marked local-demo-only password, and saves about eight well-known games by RAWG id through the real save flow with varied statuses, ratings, hours, platforms, and notes. It is safe to re-run. The README documents setup, the Tailwind CLI steps, running the seed, the API (token usage with placeholder tokens), and how to demonstrate that libraries and detail pages work with RAWG unreachable.

### Acceptance criteria

- [ ] `seed_demo` creates one Private and one Public demo user with varied entries via the real save flow
- [ ] Re-running `seed_demo` doesn't create duplicates or crash
- [ ] Seed tests mock get-game; no RAWG data is committed as fixtures
- [ ] After seeding, My Library, shared library, and detail pages work with RAWG unreachable (documented demo steps)
- [ ] README covers setup, environment file, Tailwind CLI, seeding, API usage with placeholder tokens, and the offline demo
