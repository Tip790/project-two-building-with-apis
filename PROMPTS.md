# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-11-16 — Implemented Phase 6 (sharing and privacy) with three TDD behaviors

### Prompts
1. `/implement` @prd/game-backlog-tracker.md @plans/game-backlog-tracker.md Implement phase 6
2. go ahead with those three
3. the test is right, make it pass
4. move to behavior 2
5. the test is right, make it pass
6. move on to the new behavior
7. make it pass
8. finish phase 6
9. verification passes, write entry and commit

### Summary
- **Outcome:** Phase 6 of the plan is built:
  - **Settings:** `/settings/` (`accounts:settings`, sign-in only) shows whether the library is Public or Private, has a `SharingForm` toggle that flashes "Your library is now Public." or "…Private.", and shows a copyable share link. The navbar links to it by URL name.
  - **Shared library:** `/u/<username>/` (`shared:library`, in `library/shared_urls.py`) uses the same browsing as My Library through a new `_browse` helper: search, filters, sort, 12 per page and HTMX swaps. The filter bar moved to `templates/library/partials/filter_bar.html` so both pages share it.
  - **Read-only detail:** `/u/<username>/<pk>/` (`shared:entry_detail`) reuses `entry_detail.html` with `read_only`. It shows the owner's status, rating, hours, platform and notes, with no form or delete button.
  - **Visibility rule:** `_visible_library_owner_or_404` raises the same bare `Http404` for a missing username and for a Private library viewed by anyone but its owner.
  - **Edit refusals:** `_own_entry_or_404` now gives non-owners a 403 for a Public entry and a 404 for a Private one. `@login_required` still sends signed-out visitors to log in.
  - **Owner preview:** owners viewing their own shared pages see "This is how others see your library" and an "Edit in My Library" link.
  - **CSS:** `static/css/app.css` was rebuilt for the toggle and input classes.

  TDD covered three behaviors, each RED → approved → GREEN:
  1. a Private library and a username that doesn't exist get byte-identical 404s on both shared pages, Public libraries are visible to anyone, and owners see their own
  2. switching to Private on Settings makes a working share link 404 on the next request
  3. non-owner edit, save, delete-confirm and delete attempts are 403 (Public), 404 (Private) or a login redirect (signed out), and leave the entry unchanged

  All 180 tests pass, and Ruff lint and format are clean. The user confirmed manual browser verification passed.
- **Deviations:** The user approved each TDD test unchanged, and no recommendations were overridden. When showing the behavior 3 test, the agent pointed out it treats opening `/library/<pk>/` as an edit attempt (403 for a stranger on a Public entry, not a redirect to the read-only page). The user kept it. Decisions made during the phase that the PRD doesn't specify:
  - To put Settings at `/settings/` in the `accounts` namespace, `accounts.urls` is now included at the root with full `accounts/...` paths. Every existing URL is unchanged.
  - Shared pages are read-only for everyone, owners included. Owners edit through My Library.
  - An entry addressed under the wrong username (`/u/alice/<bob's pk>/`) is a 404.
  - The Settings form edits only `library_is_public` on the signed-in user. A test checks that extra fields such as `username` and `is_staff` are ignored.
- **Sideways:**
  - Behavior 1's shared views were built at first with no visibility check, so the test failed on `200 == 404`. Behavior 2's Settings view didn't handle POST at first, so it failed on `200 == 302`.
  - In behavior 3, only the 4 Public cases were RED (`404 == 403`). The other 12 already passed from Phases 3 and 4 and were kept as regression checks, which the agent said when presenting the test.
  - One Bash heredoc that appended the regular tests was rejected for a quoting error before it ran. Nothing was written, and the tests were added with the Edit tool.
  - The `names_on_page` test helper first counted each game twice, because each cover's alt text repeats the name. It was fixed to match only the card links, without changing what the tests check.
  - Ruff's formatter rewrapped 2 files. Every edited file was checked for valid UTF-8, and the en dash, «, … and ★ were intact.
  - The first `PROMPTS.md` edit failed (wrong indentation in the matched text), and the agent ran it in the same step as the commit and push — the same mistake as in Phase 3. So the Phase 6 commit `ab639e4` went to GitHub without this log, and the log was added in a follow-up commit.
  - Known gaps:
    - With DEBUG on, Django's debug 404 pages differ by path. The identical-404 guarantee is tested with DEBUG off.
    - Nothing exercises the Settings toggle or the shared filter bar's HTMX in a real browser (only markup and responses are checked).
    - The API token section of Settings waits for Phase 7.

## 2026-11-16 — Implemented Phase 5 (library browsing) with three TDD behaviors

### Prompts
1. `/implement` @prd/game-backlog-tracker.md @plans/game-backlog-tracker.md Implement phase 5
2. go ahead with those three
3. the test is right, make it pass
4. move to the next behavior
5. continue!
6. move on to behavior 3
7. make it green!
8. continue with the rest of phase 5
9. verification passed, add PROMPTS.md, commit to git and push

### Summary
- **Outcome:** Phase 5 of the plan is built:
  - **Filter set:** `library/filters.py` has `EntryFilter`, shared with the shared library page (Phase 6) and the API (Phase 7). Parameters:
    - `q`: name search that ignores case
    - `status`
    - `genre` and `platform`: by primary key; `platform` is the entry's own platform
    - `min_rating`: unrated entries drop out
    - `sort`: `added` (the default, newest first), `name` (A–Z), `rating`, `hours` and `released` (highest or newest first, blank values last)

    Every order ends with `-pk`, so pages never overlap. The genre and platform dropdowns list only what's in the library being browsed.
  - **My Library:** `/library/` shows 12 entries per page with Django's `Paginator`. Page links use `{% querystring %}`, so they keep the active filters and sort, and they're marked `rel="prev"`/`rel="next"`.
  - **Filter bar:** a plain GET form that also submits through HTMX on submit or change. It swaps only `#library-results`, pushes the URL, and uses `hx-sync` so a newer request replaces an older one.
  - **Results partial:** the grid moved to `templates/library/partials/library_results.html`. It adds a count, rating and hours badges, and a "No games in your library match these filters" message. History restores get the full page, and responses send `Vary: HX-Request`.
  - **Dependencies and CSS:** `django-filter` 26.2 was added and registered. `tailwind/input.css` has `.filter-bar` styles, and `static/css/app.css` was rebuilt.

  TDD covered three behaviors, each RED → approved → GREEN:
  1. the filter set narrows entries by name search, status, genre, entry platform and minimum rating
  2. each sort order works, and with no sort the newest entries come first
  3. My Library shows 12 entries per page, and page links keep the active filters and sort

  All 141 tests pass, and Ruff lint and format are clean. The user confirmed manual browser verification passed.
- **Deviations:** The user approved each TDD test unchanged, and no recommendations were overridden. Decisions made during the phase that the PRD doesn't specify:
  - Parameter names are `q`, `status`, `genre`, `platform`, `min_rating`, `sort` and `page`. Genre and platform go by primary key, not slug.
  - Each sort has one fixed direction (no `-rating`-style reverse sorts), with blank values last.
  - Invalid filter, sort or page values are ignored, or the nearest real page is shown, instead of returning an error.
  - Changing a filter goes back to page 1.
- **Sideways:**
  - The sort test's two date-added cases passed before any sort code existed, because the model's default ordering is newest first. The other four failed on assertions, and the default no longer relies on `Meta.ordering`.
  - The behavior 3 test first failed after GREEN code on `"Dropped" not in html`, which matched the new status dropdown's option. It was fixed mechanically to check for the game's full name, "Game 00 Dropped".
  - A Python `read_text`/`write_text` edit used the Windows code page and garbled the en dash in "Name (A–Z)". It was caught, fixed, and every file edited that way was checked for valid UTF-8.
  - The `entry_names` test helper first returned names in a fixed order, not page order. It was fixed before the first full run.
  - A grep check reported the `col-span` classes missing from the compiled CSS. The rules were there; the grep pattern was wrong (third time this has happened).
  - `PROMPTS.md` showed a stray blank line with trailing spaces that this session didn't add. It was gone by the time this entry was written.
  - Known gaps:
    - Nothing exercises the HTMX filter bar in a real browser (only its markup and the fragment responses are checked).
    - Name sort compares lowercased names, which no test checks.

## 2026-11-16 — Implemented Phase 4 (entry detail, edit, and delete) with three TDD behaviors

### Prompts
1. `/implement` @prd/game-backlog-tracker.md @plans/game-backlog-tracker.md Implement phase 4
2. go ahead
3. the test is right, make it pass
4. move to behavior 2
5. the test is right, make it pass
6. move to behavior 3
7. make it green
8. continue with the rest of phase 4
9. manual verification passed, log it and commit

### Summary
- **Outcome:** Phase 4 of the plan is built:
  - **Shared validation:** `library/validation.py` has `validate_platform_for_game(game, platform)`. It raises a `ValidationError` on the `platform` field ("Hades isn't available on Xbox One.") and allows no platform. `LibraryEntry.clean()` calls it, so the website form and the admin use it, and Phase 8's serializer can too.
  - **Edit form:** `library/forms.py` has `EntryForm` for status, rating, hours played, platform and notes. The dropdown lists only the game's platforms, but the field accepts any platform, so a foreign one reaches the shared validator and gets the same message the API will give.
  - **Detail page:** `/library/<pk>/` shows the stored cover (with the placeholder fallback), name, release date, Metacritic score, genres, platforms and description, plus a "View on RAWG" link built from the slug. It renders from local data only.
  - **Save:** HTMX saves return the form partial (`templates/library/partials/entry_form.html`) with a "Saved." alert or inline errors. A plain POST flashes "Saved." and redirects back, and on errors re-renders the full page.
  - **Delete:** a DaisyUI modal on the detail page. Without JavaScript, the link opens a confirmation page at `/library/<pk>/delete/`. Confirming removes only the entry (the shared game stays) and redirects to My Library.
  - **Owner-only access:** both views look entries up through `_own_entry_or_404`, so another user's entry is a 404.
  - **My Library:** cards link to their detail pages.
  - **CSS:** `tailwind/input.css` styles selects and textareas in `.form-stack`, and `static/css/app.css` was rebuilt.

  TDD covered three behaviors, each RED → approved → GREEN:
  1. the shared validator rejects a platform the game isn't on
  2. an HTMX save returns "Saved." and stores the changes, or inline errors and stores nothing
  3. another user's entry is 404 for view, save, delete-confirm and delete, and stays unchanged

  All 113 tests pass, and Ruff lint and format are clean. The user confirmed manual browser verification passed.
- **Deviations:** The user approved each TDD test unchanged, and no recommendations were overridden. Decisions made during the phase that the PRD doesn't specify:
  - Delete lives at `/library/<pk>/delete/`, a sub-path of the plan's detail URL. A GET there is the no-JavaScript confirmation page.
  - Until Phase 6, every non-owner gets a 404 on `/library/<pk>/`. Phase 6 changes Public-library entries to a 403, in `_own_entry_or_404`.
  - HTMX saves with errors return status 200, because HTMX doesn't swap 4xx responses by default.
  - After a failed save, the entry is reloaded from the database, so half-applied values never show on the page.
  - Rating is a number field (1–5), not a dropdown, so out-of-range values get the model's own message, matching the API.
- **Sideways:**
  - Behaviors 2 and 3 were built with the views on purpose unfinished (POST not handled, lookup by `pk` alone), so each test failed on an assertion first.
  - The new non-TDD tests were appended in one shell step, which left their imports missing at first. They were added before the first run.
  - A grep check reported 0 matches for `.textarea` in the compiled CSS. The styles were there under `.form-stack textarea`, because `@apply` inlines them. The grep pattern was wrong.
  - The first `PROMPTS.md` edit failed again on the wrong indentation in the matched text. This time it was caught and fixed before committing.
  - Known gaps:
    - Nothing exercises the delete modal's JavaScript in a real browser (only its markup is checked).
    - The browser's own min/max checks stop most out-of-range values before the server sees them, so the server messages show mainly without those checks.
    - The 403 for Public-library edits waits for Phase 6.

## 2026-11-16 — Implemented Phase 3 (add to library + minimal My Library) with three TDD behaviors

### Prompts
1. `/implement` @prd/game-backlog-tracker.md @plans/game-backlog-tracker.md Implement phase 3
2. continue with these three
3. continue, make it green
4. go ahead with behavior 2
5. the test is right, make it pass
6. continue to behavior 3
7. the test is right, make it pass
8. continue with the rest of phase 3
9. the login redirect does not open /library/ on login
10. it's neither, logging in in general does not redirect to the /library/ remaining at the home page
11. manual verification passed, log it and commit

### Summary
- **Outcome:** Phase 3 of the plan is built:
  - **Models:** `games.Genre`, `games.Platform` and `games.Game`, and `library.LibraryEntry`, in new migrations. Entries have a unique (user, game) constraint and check constraints for a 1–5 rating and 0–10,000 hours. All four models are registered in the admin.
  - **Save flow:** `games/services.py` has `get_or_fetch_game(rawg_id)`. It reuses a stored game with no RAWG call. Otherwise it fetches RAWG's detail endpoint once and creates the game with its genres and platforms. `library/services.py` has `add_to_library(user, rawg_id)`, which raises `AlreadyInLibrary` for duplicates, including a race on the unique constraint.
  - **Add button:** `/games/add/` is a sign-in-only POST. HTMX requests get the swapped control (`templates/games/partials/add_button.html`). A plain POST gets a flash message and a redirect to a same-site `next`. Search results show Add, "In your library" or "Sign in to add", and a RAWG failure shows "Couldn't add this game: …" with a Try again button and saves nothing.
  - **My Library:** `/library/` lists the user's own entries from local data, newest first, with an empty state. The navbar links to it by URL name, and the base layout now shows flash messages.
  - **Login:** logging in or signing up without a `next` now lands on My Library.
  - **CSS:** `static/css/app.css` was rebuilt for the new classes.

  TDD covered three behaviors, each RED → approved → GREEN:
  1. a new RAWG id is fetched once and stored with its genres and platforms
  2. adding a game someone else already saved works with RAWG down and makes no RAWG call
  3. adding a game twice says "Already in your library" with no integrity error (HTMX and plain POST)

  All 89 tests pass, and Ruff lint and format are clean. One live save of RAWG game 3328, rolled back afterwards, stored the name, date, Metacritic score, description, 2 genres and 7 platforms. The user confirmed manual browser verification passed.
- **Deviations:** The user approved each TDD test unchanged. Follow-up: the user reported that logging in didn't open `/library/`. The agent first suspected a dropped `next` and asked two diagnostic questions. The user clarified they wanted every login to land on My Library, so `LOGIN_REDIRECT_URL` changed from the home page to `library:my_library`, which sign-up uses too. Decisions made during the phase that the PRD doesn't specify:
  - The stored description is RAWG's plain-text `description_raw`, not its HTML, so no RAWG HTML reaches our pages.
  - The save flow is `games.services.get_or_fetch_game`, and the add logic is `library.services.add_to_library` with an `AlreadyInLibrary` exception the API can reuse in Phase 8.
  - A RAWG failure on add keeps the button as "Try again" under the error message.
  - A plain-POST add only redirects to a same-site `next`, and falls back to the home page otherwise.
- **Sideways:**
  - The first behavior 1 run failed on an import error and then on `NotImplementedError`, neither of which counts as RED. A stub returning `None` gave an assertion failure.
  - Before approval, the behavior 3 test's plain-POST case followed a redirect to `/?q=witcher`, which would have called RAWG for real. It was changed to `next=/`.
  - The `/library/` login-redirect test posted straight to the login URL, so it couldn't have caught a form that dropped `next`. A probe of the real login form showed the hidden `next` field was there, which ruled that out.
  - Piping a probe script into `manage.py shell` from PowerShell failed on a byte-order mark, and the Bash heredoc version didn't run its indented block. Running the script with `shell -c "exec(...)"` worked.
  - Ruff's formatter rewrapped 3 files.
  - The first `PROMPTS.md` edit failed (wrong indentation in the matched text), and the agent ran it in the same step as the commit and push. So the Phase 3 commit `8984cff` went to GitHub without this log, and the log was added in a follow-up commit.
  - Known gaps: nothing tests the race-condition fallback in `add_to_library`. Two simultaneous first saves of the same new game could still hit the unique `rawg_id` in `get_or_fetch_game`. The "Sign up" link on the login page doesn't carry `next`.

## 2026-11-16 — Implemented Phase 2 (RAWG search, plain form and HTMX) with three TDD behaviors

### Prompts
1. `/implement` @prd/game-backlog-tracker.md @plans/game-backlog-tracker.md Implement phase 2
2. go ahead with those three
3. the test is right, make it pass
4. go ahead with behavior 2
5. the test is right, make it pass
6. continue to behavior 3
7. the test is right, make it pass
8. continue with the rest of phase 2
9. manual verification passed, log it and commit

### Summary
- **Outcome:** Phase 2 of the plan is built:
  - **RAWG client:** `games/rawg.py`, moved from the archived console script. It reads `RAWG_API_KEY` from Django settings, keeps the `RawgError` friendly messages, and exposes `search_games(query, page)` and `get_game(rawg_id)`. A missing key raises "RAWG isn't configured" without any HTTP call.
  - **Search page:** the home view searches RAWG and shows cards with the cover, name and release year, plus Previous/Next paging and a "Search results from RAWG" credit. The form and paging links work as plain GETs and through HTMX. HTMX requests get only the results partial (`templates/games/partials/search_results.html`), and history restores get the full page. Responses send `Vary: HX-Request`.
  - **Errors:** any `RawgError` renders as an alert where the results go, with status 200. Empty searches show a "No games found" message.
  - **Covers:** a missing or broken cover falls back to `static/img/cover-placeholder.svg`.
  - **CSS:** `static/css/app.css` was rebuilt for the new classes.

  TDD covered three behaviors, each RED → approved → GREEN:
  1. a missing RAWG key says "RAWG isn't configured" and makes no HTTP call
  2. HTMX searches return only the results fragment, and normal requests return the full page
  3. a RAWG failure shows an alert in the results area, never an error page

  All 52 tests pass, and Ruff lint and format are clean. One live search ("hollow knight") through the new client returned 12 results with names, years and covers. The user confirmed manual browser verification passed.
- **Deviations:** No recommendations were overridden, and the user approved each TDD test unchanged. Decisions made during the phase that the PRD doesn't specify:
  - Search shows 12 results per page so the 3-column grid fills evenly. The old console script showed 10.
  - A 404 gives a message that fits what was asked for: "That game was not found on RAWG" for a game, "There are no more results" for a search page past the end.
  - Key and rate-limit messages now speak to a website visitor ("the site's API key", "the site operator needs to check…"), not a console user.
  - HTMX history-restore requests get the full page, and responses send `Vary: HX-Request`, so Back and caching can't show a bare fragment.
  - The behavior 3 test uses a client that doesn't re-raise server exceptions, so a crash shows up as the 500 a browser would get.
- **Sideways:**
  - Two of the first view tests failed because of how they were written, not the code. Django escapes the apostrophe in "isn't", so the test now unescapes the HTML. The paging links used a bare `&` in attributes, so the template now writes `&amp;`.
  - A test edit through `python` in the shell failed because this machine has no bare `python` command. The edit was redone with the Edit tool.
  - Ruff's formatter rewrapped one line in `games/rawg.py`.
  - A grep check reported the `lg:grid-cols-3` class missing from the compiled CSS. The rule was there; the grep pattern was wrong.
  - Known gaps: nothing tests the `onerror` fallback in a real browser (only its markup is checked), and "Sign in to add" and the Add button arrive in Phase 3.

## 2026-11-16 — Implemented Phase 1 (walking skeleton + accounts) with three TDD behaviors

### Prompts
1. `/implement` @prd/game-backlog-tracker.md @plans/game-backlog-tracker.md Implement phase 1
2. go ahead with those three
3. the test is right, make it pass
4. go ahead with behavior 2
5. the test is right, make it pass
6. continue to behavior 3
7. continue with making it green
8. continue with the rest of phase 1
9. manual verification passed, log it and commit

### Summary
- **Outcome:** Phase 1 of the plan is built:
  - **Project setup:** a Django 6.1.3 project (`config`) with the `accounts`, `games` and `library` apps. Django is pinned to `~=6.1.3`, and pytest-django was added.
  - **Users:** a custom `accounts.User` with `library_is_public` (default False), created in the first migration and registered in the admin with that field.
  - **Settings:** read from `.env`. A missing `DJANGO_SECRET_KEY` stops the app, `DJANGO_DEBUG` defaults to off, and `RAWG_API_KEY` is optional. `.env.example` documents all three.
  - **Accounts:** sign-up plus Django's built-in login, logout and password-change pages, all under the `accounts` namespace.
  - **Layout:** a base layout with a navbar that changes when you sign in, and a RAWG footer credit. The home page has the tagline and a search box that does a plain GET for now.
  - **Front end:** Tailwind CLI v4.3.3 (git-ignored) with the DaisyUI 5.7.50 plugin file, the compiled `static/css/app.css`, and HTMX 2.0.11 as a local file.
  - **Archive:** the console script and its tests moved to `archive/initial-api-verification/` with a README. The folder is excluded from pytest and Ruff.
  - **README:** setup steps, the Tailwind CLI download and build commands, and the test commands.

  TDD covered three behaviors, each RED → approved → GREEN:
  1. settings refuse to load without a secret key
  2. sign-up creates a Private account and signs the user in
  3. the navbar matches the signed-in state

  All 17 tests pass, and Ruff lint and format are clean. The user confirmed manual browser verification passed.
- **Deviations:** No recommendations were overridden, and the user approved each TDD test unchanged. Decisions made during the phase that the PRD doesn't specify:
  - The archive folder is `archive/initial-api-verification/`, with "Initial API verification" as its README title. This settles the folder-name question left open in the design interview.
  - The compiled stylesheet and the DaisyUI plugin file are committed. Only the CLI executable is git-ignored.
  - Tailwind and DaisyUI are pinned to the newest releases at least two weeks old (4.3.3 and 5.7.50), not the very latest (4.3.5 and 5.8.1).
  - `.env.example` sets `DJANGO_DEBUG=true` for local development, because with debug off Django's development server doesn't serve static files.
  - `ALLOWED_HOSTS` is `localhost` and `127.0.0.1`, because the app runs locally only.
  - Django-generated migrations are excluded from Ruff, and long lines are allowed in `config/settings.py`.
  - The navbar's My Library and Settings links point at `/library/` and `/settings/` until those pages exist in Phases 3 and 6.
- **Sideways:**
  - The agent ran a stray `git checkout --` with no file paths while running checks. It changed nothing (it only listed modified files), and the agent said so.
  - Ruff's first run flagged long lines in the Django-generated migration and in a settings validator path. Excluding migrations and allowing long lines in settings fixed this.
  - The user's real `.env` had only `RAWG_API_KEY`, so the agent added a generated `DJANGO_SECRET_KEY` and `DJANGO_DEBUG=true` to the end without printing the secret.
  - Known gaps the user was told about:
    - My Library and Settings show "Page not found" until later phases.
    - There's no link to the password-change page yet.
    - The navbar test checks link text but not where the links go.

## 2026-11-16 — Wrote the initial CLAUDE.md and trimmed it to stack, decisions, and document pointers

### Prompts
1. Create the initial CLAUDE.md for this project. Keep it to about 20-30 lines. Include only: 1. A one-line project description. 2. The approved technology stack and package manager. 3. Durable, project-wide architecture decisions already established in the PRD. 4. Short pointers to the PRD, plan, and prototypes instead of repeating their details. Do not add commands yet because the project tooling has not been installed or verified. Do not predict project structure, paths, template conventions, URL conventions, or testing commands that do not exist yet. Do not copy business requirements, user stories, implementation phases, rejected alternatives, or detailed feature rules into CLAUDE.md. Do not invent new architectural conventions.
2. This CLAUDE.md is too detailed. Reduce it to about 20-30 lines. Remove feature-specific business rules and anything that predicts commands or project structure. Keep only the project description, technology stack, document pointers, and durable architecture decisions from the PRD.
3. commit and push
4. log this session in PROMPTS.md

### Summary
- **Outcome:** Added a 26-line `CLAUDE.md` with a one-line description and three sections:
  - the stack (uv, Django, DRF, SQLite, Tailwind standalone CLI with DaisyUI, local HTMX, pytest with pytest-django, Ruff)
  - seven architecture decisions from the PRD
  - pointers to the PRD, the plan, and the sharing prototype

  Committed it as `9b5986b` and pushed it to `origin/main`.
- **Deviations:** None on recommendations. The user corrected the first draft as too detailed (prompt 2).
- **Sideways:** The first draft broke the user's own constraints:
  - It named the three apps, which predicts project structure.
  - It included feature rules: the API 503, the Private-library 404, and where RAWG attribution goes.
  - It included a command-style instruction ("use `uv`, not pip").
  - It reworded the PRD's caching rule loosely.

  The user caught this, and the second draft removed all of it. Git also warned that it will convert the file's LF line endings to CRLF. This is harmless.

## 2026-11-16 — Broke the game backlog tracker PRD into a 9-phase tracer-bullet plan and committed the design documents

### Prompts
1. `/prd-to-plan` @prd/game-backlog-tracker.md
2. merge the suggested merges then display the phases again
3. are there any more merges possible that you would recommend?
4. write the 9 phases
5. commit the PRD, Plan, Grill-me, and the prototype
6. Append a session log to PROMPTS.md at the repo root, under today's date, newest entry at the top. Record every prompt I gave you this session, in order, including any corrections. End the entry with a short summary: the outcome, any places where I deviated from a recommended answer or asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** Wrote `plans/game-backlog-tracker.md`, a 9-phase plan. Its header records the decisions every phase relies on:
  - URL layout A from the prototype: `/library/`, `/u/<username>/`, `/api/entries/`, `/api/users/<username>/entries/`
  - the models and the owning apps
  - the auth and 403/404 rules
  - the shared save flow

  The phases:
  1. walking skeleton + accounts
  2. RAWG search (plain form and HTMX)
  3. add to library + minimal My Library
  4. entry detail, edit, and delete
  5. library browsing
  6. sharing and privacy
  7. API reads + tokens
  8. API writes + shared library endpoint
  9. demo seed, offline demo, and README

  Committed the PRD, the plan, the sharing prototype, and the grill-me session log in `PROMPTS.md` as `b4bc4a1` on `main`. No app code has been written.
- **Deviations:**
  - The first breakdown had 13 phases. I asked for the three suggested merges, which made 10 phases:
    - both search phases combined
    - detail/edit combined with HTMX edit/delete
    - API writes combined with the shared library endpoint
  - Follow-up question: asked whether any more merges were worth doing. The recommendation was to fold accounts into the walking skeleton and keep the rest separate. I took it, which made 9 phases.
  - Details the plan adds that the PRD doesn't specify:
    - the add-to-library action is at `/games/add/`
    - running `seed_demo` again must not create duplicates or crash
    - regenerating an API token makes the old one stop working
    - story 7 ("Sign in to add") moved to the add-to-library phase
- **Sideways:**
  - The prototype showed a 403 for API edits to another user's Public entry, but the PRD says 404. The plan follows the PRD and records the conflict in its header.
  - "Grill-me" in the commit request was ambiguous. The agent read it as the interview session log in `PROMPTS.md` and said so before committing.
  - Git warned about line-ending conversion when committing (harmless).
  - The agent's first attempt to edit `PROMPTS.md` failed because the text it searched for had the wrong indentation. The second attempt worked.

## 2026-11-16 — Designed the Django RAWG game backlog tracker in a 22-question interview, prototyped the sharing URLs, and wrote the PRD

### Prompts
1. `/grill-me` @project-idea.md Create a Django application that consumes an external API and provides it's own API focued on the RAWG video game API follow the tech and business requirements.  Users will find items through the external API, save selected items, and add their own information. Your application will store that information locally and make it available through a website and an API built with Django REST Framework.
2. A, the Game backlog and progress tracker
3. B (A's core tracker with hours played and platform) with 1–5 star rating, remove the start and finish dates from B
4. A, two tables with Game and LibraryEntry (how data is stored locally)
5. A, real Genre and Platform models (how to store genres and platforms)
6. Instead of the reccommendation B: Public viewing of all librarys, do C. Selective Sharing where you selected if the library is private or public.
7. A, custom User model with private by default
8. `/prototype` this question
9. back to the question, use option A, the personal URL per user with no directory
10. A, mirror the website, with entries only (DRF API endpoints)
11. A, send rawg_id and fetch full details from /games/<id> (how game data gets to the database)
12. C, the HTMX on submit and i the one click add to library (How "find games on RAWG" search works)
13. A, django-filter with HTMX results swap (library browsing)
14. A plus (ii), built-in auth with token API (sign in) but the API tokens will be fake ones, not real ones is that okay??
15. Meaning 1, real tokens with placeholders in docs, one Settings page (DRF tokens not API keys, my bad)
16. C, detail page with HTMX save, and yes to read-only (how to edit or delete entries)
17. A, keep rules 1–4 and skip 5 and 6 (Validation Rules for entries)
18. A, move existing client with no caching, and yes to placeholder (how client code is organized, and if it is cached)
19. A, three apps, and delete the tests and ecisting scripts, unless it would remove it from the repository, then keep but disable the code.
20. A, move them to archive and exclude from pytest and Ruff, name archive "Initial API verification" (What happens to the earlier API tests)
21. B, Tailwind's CLI and i, Save htmx.min.js into static/js (vendored HTMX) (In regards to how Tailwind, DaisyUI, and HTMX are added to the pages)
22. A, pytest-django with two-level mocking (how things are tested)
23. C, footer plus View on RAWG link, and i (attribution to list responses) (RAWG attribution/crediting)
24. A, python-dotenv with os.environ, local-only not deployed (settings and secrets, keeping the things not commited to git in Django)
25. A, search as home page with tagline, and yes to admin
26. B, seed_demo management command (demo data)
27. `/to-prd`
28. Append a session log to PROMPTS.md at the repo root, under today's date, newest entry at the top. Record every prompt I gave you this session, in order, including any corrections. End the entry with a short summary: the outcome, any places where I deviated from a recommended answer or asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** A 22-question design interview settled the whole design of a Django + DRF game backlog tracker built on RAWG:
  - **Data:** custom `User` with a Private/Public library setting (Private by default); shared `Game`/`Genre`/`Platform` tables; `LibraryEntry` with status, 1–5 rating, hours played, platform and notes.
  - **Website:** HTMX search home page with one-click add; `/library/` and `/u/<username>/` with `django-filter` browsing; detail pages with an HTMX edit form.
  - **API:** a DRF API that mirrors the website, with token auth.
  - **Supporting decisions:** a RAWG client moved from the old script, RAWG attribution everywhere, Tailwind standalone CLI with DaisyUI, vendored HTMX, `pytest-django` with mocked RAWG, and a `seed_demo` command.

  Files written:
  - `prototypes/library-sharing-urls.html`, a throwaway logic prototype comparing three URL layouts for sharing
  - `prd/game-backlog-tracker.md`, with 72 user stories, implementation and testing decisions, and the out-of-scope list

  No app code has been written. Nothing from this session is committed yet.
- **Deviations:**
  - Q2 (personal fields): chose the recommended core tracker but removed start and finish dates.
  - Q5 (who can see a library): overrode the recommended public read-only viewing and chose selective sharing (each user picks Private or Public).
  - Q16 (old console script): made deleting the script and tests conditional on it not removing them from the repo. Once told that deleting removes them from the current files (history keeps them), chose to move them to an archive excluded from pytest and Ruff, named "Initial API verification".
  - Follow-up question: asked whether API tokens could be "fake." This turned out to be a mix-up between DRF tokens and external API keys, and was settled as real DRF tokens with placeholder tokens in docs and tests.
  - Detour: used `/prototype` on the URL-layout question before answering it.
  - Every other answer matched the recommendation.
- **Sideways:**
  - Node.js isn't installed, so the prototype's model couldn't be run automatically. The walkthroughs were traced by hand instead, and the prototype hasn't been confirmed by clicking through it in a browser.
  - Dropping start and finish dates also removed the planned "finished can't be before started" check, leaving "platform must belong to the game" as the only cross-field rule.
  - The archive folder name is unresolved. I suggested `archive/initial-api-verification/` (no spaces) with "Initial API verification" as the README title, but the choice wasn't confirmed. The PRD says only that the folder is "titled" that.
  - The PRD assumes a Django version that supports Python 3.14, which hasn't been checked yet. It gets pinned at setup.

## 2026-11-16 — Researched game/music APIs, then designed and built a RAWG console search script with uv

### Prompts
1. `/research` Find free external APIs for a Django application where users search for items, save them, and add their own notes, ratings, or progress. Explore the topics games and  music Compare promising providers using official documentation, including available data, free limits, signup requirements, etc...
2. `/grill-me` write a short console script that makes a real request to RAWG, it should Accept user input, such as a search phrase or item identifier. Make a meaningful request to the external API. Use your own credentials if the provider requires them. Display selected results clearly in the console. Handle unsuccessful requests and empty results with useful messages. setup the script with uv.
3. A, make it a uv project at the root
4. stick with A requests over httpx (library)
5. A, use a .env file with python-dotenv
6. C, search then pick a result (user typing and script request)
7. B, keep going until the user quits (when does conversation with user end)
8. B, standard details with plain print() (what should show, and how it should look, Standard over Breif or raw JSON)
9. A, full table with custom RawgError (error handling)
10. B. Script, Ruff and pytest with fake RAWG responses, (tests/code-quality checks now or later)
11. Yes, build it, I have a key
12. how do I make a .env that doesn't get commited to github
13. I made the .env, run a real search
14. walk through the code. Identify how the API requests get made, retrieved, and displayed back to you in the console.
15. how would I run this myself?
16. Append a session log to PROMPTS.md at the repo root, under today's date, newest entry at the top. Record every prompt I gave you this session, in order, including any corrections. End the entry with a short summary: the outcome, any places where I deviated from a recommended answer or asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** A background research agent wrote `research/games-and-music-apis.md`, comparing 14 game and music APIs against their official docs. It recommended RAWG (games) and MusicBrainz + Cover Art Archive (music), and a RAWG game backlog tracker as the overall pick. An 8-question design interview then led to building:
  - a uv project at the repo root (`pyproject.toml`, `uv.lock`) with `requests`, `python-dotenv` and `truststore`, plus Ruff and pytest as dev tools
  - `.env.example`
  - `scripts/rawg_search.py`, a looping search → pick → details console script with a custom `RawgError` error table
  - `tests/test_rawg_search.py`, 11 tests that fake RAWG's responses

  Verified against the real API: a "hollow knight" search, the details view, no results, bad number input, and a rejected (fake) key. Ruff passes and all 11 tests pass. Nothing is committed yet.
- **Deviations:** Q2 (HTTP library): chose `requests` over the recommended `httpx`. `timeout=10` was added to every call to make up for `httpx`'s default timeout. All other answers matched the recommendation. Follow-up questions:
  - how to make a `.env` that isn't committed (`.gitignore` already covered it, confirmed with `git check-ignore`)
  - a walkthrough of how requests are made, checked and displayed
  - how to run the script, tests and checks yourself
- **Sideways:**
  - The research agent couldn't read the official pages for IGDB, Giant Bomb, MobyGames, CheapShark or Discogs directly. Their facts come from search-engine copies, marked "[indexed copy]", and need checking by hand.
  - `uv add` failed with `invalid peer certificate: UnknownIssuer`, probably from antivirus or network software inspecting secure connections. Retrying with `--system-certs` worked.
  - The first real run printed "Could not reach RAWG" for every search. The real cause was an `SSLError` (the same certificate problem), which was being reported as a connection error. Fixed by adding `truststore` and a separate certificate-error message.
  - Printing the results then crashed with `UnicodeEncodeError` on `★`, because Windows output used cp1252. Fixed by switching output to UTF-8 in `main()`.
  - Ruff flagged two lines over 88 characters, which were split. Ruff's formatter also rewrote `except (KeyboardInterrupt, EOFError):` without the parentheses, which is valid Python 3.14 syntax.
  - Not covered by tests: the new SSL-error message and the UTF-8 output fix. The real API has been checked only for the success, empty, bad-input and bad-key cases. Timeout, 429 and 5xx are checked only with fake responses in the tests.