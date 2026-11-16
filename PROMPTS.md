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