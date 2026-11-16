# PRD: Game Backlog Tracker

## Problem Statement

Gamers own or want far more games than they can play, spread across many platforms and storefronts. They lose track of what they've started, what they've finished, what they thought of a game, and what they meant to play next. Existing game databases (like RAWG) are good at telling them *about* games, but don't remember *their* relationship to each game. They also want to be able to show a friend their backlog without exposing it to everyone, and some want to reach their data from their own scripts or tools rather than only through a website.

## Solution

A Django web application, the Game Backlog Tracker, that lets a signed-in user search the RAWG video game database, save games to a personal library with one click, and track their own information for each game: status (Want to Play, Playing, Completed, Dropped), a 1–5 star rating, hours played, the platform they play it on, and free-text notes.

Saved games are stored locally, so a user's library and game details keep working even when RAWG is unavailable. Users can search, filter, sort, and page through their library. Each user chooses whether their library is Private (the default) or Public; a Public library can be shared by link and viewed read-only by anyone. The application also provides its own REST API (Django REST Framework) so other programs can list, create, update, and delete a user's entries, with the same privacy rules as the website. When RAWG fails or isn't configured, users see a clear, friendly message instead of an error page.

## User Stories

### Finding games (external API)

1. As a visitor, I want the home page to be a game search box with a short tagline, so that I immediately understand what the app does and can start searching.
2. As a visitor, I want to search RAWG by game title, so that I can find the game I'm thinking of.
3. As a visitor, I want search results to update in place without a full page reload, so that searching feels quick.
4. As a visitor without JavaScript, I want search to still work as a normal form submission, so that the site is usable in any browser.
5. As a visitor, I want each search result to show the game's cover image, name, and release year, so that I can recognize the right game.
6. As a visitor, I want to page through search results, so that I can find games that aren't on the first page.
7. As a signed-out visitor, I want to see a "Sign in to add" prompt on search results, so that I know how to start saving games.
8. As a user, I want a clear message when RAWG is slow, down, rate-limited, or rejecting the key, so that I know the problem isn't my fault and can try again later.
9. As a user, I want a clear message when the site's RAWG key hasn't been configured, so that the operator knows exactly what to fix.
10. As a user, I want a credit and link to RAWG near search results, so that the data source is acknowledged.

### Saving games

11. As a signed-in user, I want to add a game to my library with one click from the search results, so that saving is effortless.
12. As a signed-in user, I want a newly added game to default to "Want to Play," so that I don't have to fill in a form just to save it.
13. As a signed-in user, I want the "Add" button to change to "In your library" after adding, without leaving the page, so that I can keep browsing results.
14. As a signed-in user, I want to be told "Already in your library" if I try to add a game twice, so that I don't get duplicates or an error.
15. As a signed-in user, I want a friendly message if a game can't be saved because RAWG is unavailable, so that I understand why and can retry.
16. As a signed-in user, I want to be able to save a game someone else has already saved even when RAWG is down, so that a RAWG outage doesn't block me unnecessarily.
17. As a user, I want my saved games' details (name, cover, release date, genres, platforms, Metacritic score, description) stored by the app, so that my library still works when RAWG is unavailable.

### Tracking my own information

18. As a signed-in user, I want to set a game's status to Want to Play, Playing, Completed, or Dropped, so that I can track where I am with it.
19. As a signed-in user, I want to give a game a 1–5 star rating, or leave it unrated, so that I can remember what I thought of it.
20. As a signed-in user, I want to record hours played, or leave it blank, so that I can track my progress.
21. As a signed-in user, I want to choose which platform I play a game on from that game's own platforms, so that I record it accurately.
22. As a signed-in user, I want to write notes about a game, so that I can capture thoughts, tips, or reasons I want to play it.
23. As a signed-in user, I want to be stopped with a clear message if I enter a rating outside 1–5, negative or absurd hours, or a platform the game isn't on, so that my data stays sensible.
24. As a signed-in user, I want an entry detail page showing the stored game information and my editable fields, so that each game has a home in my library.
25. As a signed-in user, I want my edits to save without a full page reload and show a "Saved" confirmation or inline errors, so that editing feels smooth.
26. As a signed-in user, I want to delete a game from my library after confirming, so that I can remove games I no longer care about without accidents.
27. As a user, I want a "View on RAWG" link on a game's detail page, so that I can see more about it at the source.
28. As a user, I want a placeholder image when a game's cover fails to load, so that pages still look intentional when RAWG's images are unreachable.

### Browsing my library (local data)

29. As a signed-in user, I want a "My Library" page listing my saved games, so that I can see my whole backlog.
30. As a signed-in user, I want to search my library by game name, so that I can find a game quickly.
31. As a signed-in user, I want to filter my library by status, so that I can see, for example, everything I'm currently playing.
32. As a signed-in user, I want to filter my library by genre, so that I can pick something in the mood I'm in.
33. As a signed-in user, I want to filter my library by the platform I play on, so that I can see what's available on the device in front of me.
34. As a signed-in user, I want to filter my library by minimum rating, so that I can find my favorites.
35. As a signed-in user, I want to sort my library by date added, name, rating, hours played, or release date, so that I can view it in the order that helps me.
36. As a signed-in user, I want my library paginated (12 per page), so that large libraries stay fast and readable.
37. As a signed-in user, I want filtering, sorting, and paging to update the results without a full reload while keeping a shareable URL, so that browsing is smooth and I can bookmark a view.
38. As a user, I want library browsing to work entirely from saved data, so that it works when RAWG is unavailable.

### Accounts and settings

39. As a visitor, I want to sign up for an account, so that I can start my own library.
40. As a user, I want to log in and log out, so that my library is protected.
41. As a user, I want to change my password, so that I can keep my account secure.
42. As a visitor who tries to open "My Library" while signed out, I want to be sent to log in and then returned to my library, so that I end up where I meant to go.
43. As a signed-in user, I want a Settings page, so that I have one place to manage sharing and API access.

### Sharing and privacy

44. As a new user, I want my library to be Private by default, so that nothing I write is exposed until I choose to share.
45. As a signed-in user, I want to switch my library between Private and Public on the Settings page, so that I control who can see it.
46. As a user with a Public library, I want a personal link to my library that I can share, so that friends can see my backlog.
47. As a visitor, I want to browse, search, filter, and sort a Public library, so that I can explore a friend's backlog.
48. As a visitor, I want to open a read-only detail page for a game in a Public library, including the owner's notes and rating, so that I can see what they thought.
49. As a library owner, I want visitors to see my library read-only with no edit controls, so that only I can change it.
50. As a library owner, I want my Private library to show "Not Found" to everyone else, so that nobody can see it.
51. As a library owner, I want a Private library to look exactly like a non-existent user to others, so that nobody can even tell my account exists.
52. As a library owner, I want an old share link to stop working as soon as I switch to Private, so that un-sharing takes effect immediately.
53. As a user, I want any attempt to change someone else's entries to be refused, so that my data can't be tampered with.

### API (Django REST Framework)

54. As an API client, I want to obtain a token by sending my username and password, so that my scripts can authenticate without sending my password on every request.
55. As a signed-in user, I want to see and regenerate my API token on the Settings page, so that I can use and rotate it.
56. As an API client, I want to list my own entries, so that another program can read my backlog.
57. As an API client, I want to create an entry by sending a RAWG game id plus my own fields, so that the server fetches trustworthy game data itself.
58. As an API client, I want a 503 response with a clear message when an entry can't be created because RAWG is unavailable, so that my program can handle it.
59. As an API client, I want to retrieve, update, and delete my own entries, so that I can fully manage my backlog programmatically.
60. As an API client, I want each entry to include the stored game details nested within it, so that I don't need a separate games endpoint.
61. As an API client, I want the same search, filter, sort, and pagination options as the website, so that results match what I see in the browser.
62. As an API client, I want the same validation rules and error messages as the website, so that bad data is rejected consistently.
63. As an API client, I want to read another user's entries only when their library is Public, so that sharing rules are respected.
64. As an API client, I want a 404 when I try to read a Private library or access an entry that isn't mine, so that private data is never revealed.
65. As an API client, I want unauthenticated requests to my own entries to be rejected, so that my data is protected.
66. As an API client, I want list responses to include a RAWG attribution, so that the data source is credited wherever the data appears.
67. As a signed-in user, I want to explore the API in the browser using my website session, so that I can try it without extra setup.

### Operating and demonstrating the app

68. As the developer, I want a single command that creates demo users (one Private, one Public) with varied saved games, so that the app is ready to demonstrate.
69. As the developer, I want to demonstrate that saved libraries and detail pages work when RAWG is unreachable, so that I can prove the offline requirement.
70. As the developer, I want the Django admin available with all models registered, so that I can inspect stored data during development.
71. As the developer, I want secrets (Django secret key, debug flag, RAWG key) loaded from an untracked environment file with a documented example, so that no secrets are committed.
72. As a user of any page, I want a site-wide footer crediting RAWG with a link, so that RAWG's attribution terms are met everywhere.

## Implementation Decisions

### Project structure
- A Django project configuration package plus three apps:
  - **accounts:** the custom user model, sign-up, and the Settings page (sharing toggle and API token).
  - **games:** the Genre, Platform, and Game models; the RAWG client; and the search page and add-to-library action.
  - **library:** the LibraryEntry model, shared validation, the shared filter set, the website library and detail views, and the API (serializers, viewset, and read-only shared-library view), kept in the same app as the model it serves.
- Shared templates: a base layout (navbar and RAWG attribution footer) and partial templates for HTMX fragments.

### Models and database
- **Custom user model** (subclassing Django's abstract user), configured before the first migration, with a `library_is_public` boolean that defaults to False.
- **Genre** and **Platform:** RAWG id (unique), name, slug.
- **Game:** RAWG id (unique), name, slug, background image URL (the URL only, never the image file), release date, Metacritic score, description, many-to-many to Genre and to Platform. One shared row per game, regardless of how many users save it.
- **LibraryEntry:** user, game, status (Want to Play / Playing / Completed / Dropped; required; default Want to Play), rating (optional, 1–5 integer), hours played (optional, decimal, 0 to a sensible cap such as 10,000), platform (optional foreign key to Platform), notes (optional text), created and updated timestamps.
- Database constraints: unique (user, game); check constraints for the rating range and non-negative hours.
- SQLite database.

### Validation
- Simple field rules (rating range, hours range) are expressed as field validators plus database check constraints, so Django forms and DRF model serializers both pick them up.
- The cross-field rule "the chosen platform must be one of this game's platforms" lives in one shared validation function, called from the model's clean method (website forms) and from the serializer's validate method (API).
- Duplicate saves are caught and reported as "Already in your library" rather than as an integrity error.
- Explicitly not enforced: "Want to Play can't be rated" and "Completed requires hours."

### RAWG integration
- The existing, tested console client is moved into the games app as a service module exposing a search function (title query plus page) and a get-game-by-id function, with the existing friendly error class and messages (timeouts, SSL, connection failures, 401/403, 404, 429, 5xx, bad JSON).
- The API key is read from Django settings. A missing key produces a friendly "RAWG isn't configured" message rather than a crash.
- No caching of RAWG responses. Locally saved games are the only persistence of RAWG data.
- **Save flow (shared by the website and the API):** given a RAWG id, reuse the local Game if one exists (no RAWG call). Otherwise fetch the game's full detail endpoint once (to get the description), then create the Game and any missing Genre and Platform rows and link them. If the fetch fails, the website shows the error message and the API returns 503 with it.
- **Attribution:** a site-wide footer credit and link on every page, a small credit under search results, a "View on RAWG" link (built from the stored slug) on detail pages, and an attribution field in API list responses via a custom pagination class.
- Cover images use RAWG-hosted URLs with a client-side fallback to a local placeholder image when they fail to load.

### Website URLs and behavior
- **Home** is the RAWG search page, with a tagline. Search uses HTMX on submit: the form has both a normal action and HTMX attributes, the view returns only the results fragment for HTMX requests and the full page otherwise, and paging links behave the same way. RAWG errors render as an alert where the results would appear. Signed-out visitors can search but see "Sign in to add."
- **Add to library** is a one-click HTMX action that saves with status Want to Play and swaps the button to "In your library."
- **My Library** requires sign-in and shows the current user's entries with edit capability. The login redirect returns the user to this page.
- **Shared library** (per-username URL): shown if the library is Public or belongs to the viewer; otherwise 404. A non-existent username returns the identical 404.
- **Owner entry detail page:** stored game details plus an edit form that saves via HTMX, returning a "Saved" alert or inline validation errors, with a plain form fallback. Delete requires confirmation and then redirects to My Library.
- **Read-only entry detail page** under the shared library URL, using the same template without edit controls and following the same 404 rule.
- **Website permission outcomes:** editing another user's Public library is 403; another user's Private library is 404; signed out redirects to login.
- **Settings page:** Public/Private toggle and API token display/regenerate.
- **Auth:** Django's built-in login, logout, and password-change views plus a small sign-up view using a user-creation form for the custom user.
- **Navbar:** signed in shows Search, My Library, Settings, Log out (with username); signed out shows Search, Log in, Sign up.
- **Django admin** enabled with all models registered.
- No public directory of libraries.

### Library browsing
- One `django-filter` filter set shared by My Library, the shared library page, and the API: name search; filters for status, genre, the entry's platform, and minimum rating; sorting by date added (default, newest first), name, rating, hours played, and release date.
- Pagination at 12 per page.
- Filter, sort, and page changes swap only the results grid via HTMX and push the URL so views stay shareable and bookmarkable.
- All browsing runs on local data only.

### API (Django REST Framework)
- **"My entries" endpoint:** a model viewset providing list, create, retrieve, update, partial update, and delete, scoped to the requesting user's entries. Authentication required.
- **Shared library endpoint** per username: read-only list, returned if the library is Public or belongs to the requester; otherwise 404.
- No standalone games endpoint. Game details (with genres and platforms) are nested read-only inside each entry.
- **Create** accepts a RAWG id plus the user's fields and uses the shared save flow. A RAWG failure for an unsaved game yields 503 with the friendly message.
- Because writes are only possible through the user-scoped endpoint, attempts to access or modify another user's entry return 404.
- Authentication: session plus DRF token authentication. A token-obtain endpoint accepts username and password, and tokens are managed per user on the Settings page.
- The same filter set, validation, and pagination apply as on the website. List responses include the RAWG attribution field.

### Front end
- Tailwind CSS built with the Tailwind standalone CLI (no Node.js), with DaisyUI loaded as a plugin file. The compiled stylesheet is served as a static file. The CLI executable is git-ignored, and its download and watch steps are documented in the README.
- HTMX vendored as a pinned, minified static file (no CDN), so pages work offline.
- DaisyUI components for alerts, modals (delete confirmation), the rating display, cards, and the navbar.

### Configuration
- `python-dotenv` loads an untracked environment file. Settings read the Django secret key (required; fails loudly if missing), the debug flag (defaults to off), and the RAWG API key (optional; missing triggers the friendly message).
- The example environment file documents all three with placeholders.
- Local-only operation: no deployment configuration.
- A current Django release that supports the project's required Python version, pinned at setup.

### Existing code
- The original console search script and its tests move into an archive folder titled "Initial API verification," with a short README noting they're superseded by the games app's RAWG client and kept as the original API-access proof. The archive is excluded from pytest and Ruff.

### Demo data
- A `seed_demo` management command creates a Private demo user and a Public demo user with a clearly marked local-demo-only password. It saves about eight well-known games by RAWG id through the real save flow, with varied statuses, ratings, hours, platforms, and notes. It requires RAWG access the first time it runs; afterward all demo data works offline. No RAWG data is committed to the repository as fixtures.

## Testing Decisions

- **What makes a good test here:** tests check externally visible behavior (HTTP status codes, rendered messages, which entries appear, what's stored in the database, whether RAWG was called) rather than internal implementation details, so refactoring doesn't break them.
- **Tooling:** pytest with `pytest-django` for the test client, database fixtures, and settings overrides. DRF's API client for API tests. A dummy RAWG key is set in test settings.
- **No live RAWG calls** in the test suite. RAWG is mocked at two levels:
  - **RAWG client module:** mock the HTTP library to verify each failure type becomes the right friendly error message, and that successful responses are parsed correctly. This continues the pattern of the archived console-client tests.
  - **Views and API:** replace the search and get-game functions to return hand-written sample RAWG data or raise the friendly error, then assert what the user or API client receives.
- **Modules and behaviors to test, in priority order:**
  1. **Privacy and permissions (website and API):** Private library and non-existent user both 404 for others; Public library is read-only for others; non-owner edits are 403 on the website and 404 in the API; signed-out requests redirect to login (website) or are rejected (API); switching to Private immediately hides a previously visible library.
  2. **Save flow:** a new RAWG id fetches and creates Game, Genre, and Platform rows and links them; an already-stored game triggers no RAWG call; a RAWG failure for an unsaved game yields a friendly website message and an API 503; a duplicate add yields "Already in your library."
  3. **Validation:** rating 1–5, hours within range, and platform belonging to the game, each enforced identically through the website form and the API serializer. The shared validation function is unit-tested directly.
  4. **Offline behavior:** library pages and detail pages render correctly while RAWG is mocked to fail.
  5. **Browsing:** status, genre, platform, and minimum-rating filters; name search; each sort order; and pagination on both the website and the API.
- **Prior art:** the existing console-client tests (moving to the archive) already demonstrate mocking HTTP calls and asserting friendly error messages. The new RAWG client tests follow the same approach.

## Out of Scope

- A public directory or discovery page listing Public libraries.
- Per-entry or per-field sharing (sharing is all-or-nothing per library), and sharing with specific users only.
- Email verification, password reset by email, social login, and `django-allauth`.
- JWT or OAuth authentication for the API.
- A standalone games API endpoint, or exposing stored RAWG data outside of entries.
- Caching RAWG search results or responses.
- Downloading or storing cover image files locally.
- Start and finish dates, priorities, tags, favorites, and custom lists or collections.
- Rules that block rating "Want to Play" games or require hours for "Completed" games.
- Live as-you-type search.
- Inline editing on the library grid.
- Price or deal data.
- Deployment to any hosting provider, production static-file hosting, and non-SQLite databases.
- Committing RAWG data as fixtures.
- Live RAWG calls in the automated test suite.

## Further Notes

- **RAWG terms:** the free plan allows 20,000 requests a month and requires crediting RAWG with an active hyperlink on every page where its data is used. The terms say "no data redistribution" and don't address caching. Storing only the fields the app needs, storing image URLs rather than images, and showing attribution everywhere (including the API) is the project's reasonable reading for a non-commercial student project.
- **Status codes:** the 403-versus-404 split is deliberate. Revealing that a Public library exists is fine, but a Private library must be indistinguishable from a non-existent account. The API's uniform 404 for other users' entries follows from scoping writes to the requester's own entries.
- **Local environment:** Node.js isn't installed on the development machine, which is why the Tailwind standalone CLI was chosen over npm-based setups.
- **Prototype:** a throwaway logic prototype of the sharing and URL rules lives in the prototypes folder. It was used to choose the per-user URL layout without a directory, and it isn't production code.
- **Tokens:** API tokens are real, app-generated DRF tokens stored locally. Documentation and tests use placeholder tokens only, and real tokens are never committed.
