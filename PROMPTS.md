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