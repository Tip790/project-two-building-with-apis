# External API Research: Video Games and Music

**Project:** CIDM 3312 Project Two, Building with APIs (Django + DRF + SQLite + HTMX)
**Date checked:** 2026-11-15
**Scope:** Free APIs where users can search for items, save them to their own collection, and add their own notes, ratings, status, or progress.

## How to read the citations

Every claim links to an official page from the provider. Some official sites (IGDB docs, Giant Bomb, MobyGames, CheapShark, Discogs docs and terms) returned **HTTP 403 to the automated fetcher**. For those, the facts come from the search engine's indexed copy of the official page, not from a live read. They are marked **[indexed copy]**. Before you rely on one of those facts, open the link in a browser and confirm it.

### Assignment constraints that shaped this evaluation (from `project-idea.md`)

- "Choose an API provider with free access sufficient to build and demonstrate the project." So the API must have a free tier with no credit card, and approval must be quick.
- "Store enough information locally for saved items to remain accessible when the external API is unavailable." This makes the provider's **storage and caching terms** a deciding factor.
- "The application handles unsuccessful external requests." Clear error codes and documented rate-limit responses help here.
- The external calls will be made server-side from Django, so a server-to-server key or token is fine. Browser CORS support does not matter much.

---

## 1. Summary and recommendation

### Games

1. **RAWG (top pick).** You get a free API key and put it in a single `?key=` query parameter. The search endpoint is easy to use, every game comes with a `background_image`, and the free plan allows 20,000 requests a month ([RAWG API docs](https://rawg.io/apidocs), [RAWG API ToS §8.2.1](https://rawg.io/tos_api)). The cost is attribution: you must credit RAWG and put an active link on **every page that uses RAWG data** ([ToS §8.2.1](https://rawg.io/tos_api)). The ToS never mentions caching. They do contain broad "no copying / no further distribution" language (§6.2, §4.3(5)), so store only the fields your app needs and keep the attribution on your saved-item pages.
2. **IGDB (runner-up).** The data is richer and better structured, and it is free for non-commercial use ([IGDB docs, Account Creation, indexed copy](https://api-docs.igdb.com/)). Setup takes more work. You need a Twitch account with 2FA turned on ([Twitch: Register Your App](https://dev.twitch.tv/docs/authentication/register-app/)). Your app has to request an OAuth client-credentials token and refresh it when it expires ([Twitch: Getting OAuth tokens](https://dev.twitch.tv/docs/authentication/getting-tokens-oauth/)). Queries are POST requests with an Apicalypse text body. Pick IGDB if you are comfortable with token handling and want more accurate metadata.

### Music

1. **MusicBrainz + Cover Art Archive (top pick).** No key, no signup, and the JSON comes back with `fmt=json` ([MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API)). The core data is **CC0** (public domain) ([Data License](https://musicbrainz.org/doc/About/Data_License)), so it has the cleanest terms for saving items to your own database. Cover art comes from `coverartarchive.org/release-group/{mbid}/front` ([CAA API](https://musicbrainz.org/doc/Cover_Art_Archive/API)). Two constraints: **1 request per second per IP**, and a **required descriptive User-Agent** ([Rate Limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)). The cover images themselves are "copyrighted by their respective copyright owners" ([coverartarchive.org](https://coverartarchive.org/)). Saving the image URL is safer than saving the image file.
2. **Discogs (runner-up, with a caveat).** Signup is quick: you generate a personal access token and send it as `Authorization: Discogs token=...`. The data covers releases and pressings well, and the rate limit is 60 requests a minute ([Discogs developers, indexed copy](https://www.discogs.com/developers)). The **API Terms forbid displaying content that is more than 6 hours older than Discogs' own data, and forbid storing it "longer than is necessary"** ([Discogs API Terms of Use, indexed copy](https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use)). That clashes with the assignment's rule that saved items must stay viewable while the API is down.

**Avoid for this project:**
- **Spotify.** Since February and March 2026, Development Mode requires the app owner to have **Spotify Premium**, each app is capped at **5 users**, and search returns at most **10 results** per request ([Feb 2026 migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)). The terms also say "Do not store Spotify Content indefinitely" ([Developer Terms IV.3.1.a](https://developer.spotify.com/terms)).
- **Last.fm.** The terms forbid using "any ... images and/or artwork" (§5.1.8) and cap the data you may store at 100 MB ([Last.fm API ToS](https://www.last.fm/api/tos)).
- **MobyGames.** There is no free general tier. The Hobbyist tier costs $9.99 a month ([MobyGames API subscribe, indexed copy](https://www.mobygames.com/api/subscribe/)).

### Overall pick for this project

**A game backlog and progress tracker built on RAWG.** A game collection fits the assignment's "notes, ratings, status, or progress" requirement naturally (Backlog / Playing / Completed, hours played, rating, notes). Integration is the simplest of all the candidates: one GET request with one query parameter. Every result has an image, and 20,000 requests a month is plenty for a class demo.

If you would rather do music, **MusicBrainz + Cover Art Archive** is just as good. Its licensing is actually cleaner (CC0), but you have to throttle requests to 1 per second and send a custom User-Agent.

---

## 2. Comparison tables

### Games

| Provider | Auth | Signup friction | Rate / quota (free) | Key data | Images | Storage / attribution terms |
|---|---|---|---|---|---|---|
| **RAWG** | API key in `?key=` query param ([docs](https://rawg.io/apidocs)) | Low: account, then "Get API Key" | 20,000 req/month ([ToS §8.2.1](https://rawg.io/tos_api)) | Search, games, platforms, genres, ratings, Metacritic score | Yes: `background_image`, screenshots | Must credit RAWG and link from every page that uses its data. Free plan limited to ≤100k MAU / 500k page views. No redistribution. Caching not addressed ([ToS](https://rawg.io/tos_api)) |
| **IGDB** | Twitch Client-ID + Bearer token (client credentials) ([IGDB, indexed copy](https://api-docs.igdb.com/)) | Medium: Twitch account, 2FA, app registration ([Twitch](https://dev.twitch.tv/docs/authentication/register-app/)) | 4 req/s, up to 8 open requests; 429 on excess ([IGDB, indexed copy](https://api-docs.igdb.com/)) | Very rich: games, covers, genres, platforms, companies, release dates | Yes: build from `image_id`, e.g. `t_cover_big` ([IGDB, indexed copy](https://api-docs.igdb.com/)) | Free for non-commercial use under the Twitch Developer Service Agreement. Commercial use requires a partnership plus attribution ([IGDB, indexed copy](https://api-docs.igdb.com/)) |
| **Giant Bomb** | API key ([forum/announcement, indexed copy](https://www.giantbomb.com/articles/giant-bomb-api-now-available/1100-793/)) | Low to medium, current status unverified | Unconfirmed: staff forum posts conflict (1 req/s; 450 per 15 min; ~200/hr per resource) ([forum, indexed copy](https://www.giantbomb.com/forums/api-developers-3017/api-rate-limiting-1786442/)) | Games, franchises, characters, reviews | Yes | Non-commercial only; commercial use leads to key revocation (per forum quotes of the terms). Official API page returned 403, **unverified** |
| **MobyGames** | `api_key` query param ([docs, indexed copy](https://www.mobygames.com/info/api/)) | **Paid**: Hobbyist $9.99/mo; free access only via a research application ([subscribe, indexed copy](https://www.mobygames.com/api/subscribe/)) | Hobbyist 0.2 req/s (pages conflict) | Deep historical data | Yes (covers, screenshots) | Must credit MobyGames. No repackaging or reselling ([indexed copy](https://www.mobygames.com/info/api/)) |
| **CheapShark** | None ([docs, indexed copy](https://apidocs.cheapshark.com/)) | None | Unspecified; 429 + `Retry-After` on excess | Game deals and prices across stores | Thumbnails | Discourages building a cached catalog through automated calls ([indexed copy](https://apidocs.cheapshark.com/)). Attribution not found |
| **FreeToGame** | None ([docs](https://www.freetogame.com/api-doc)) | None | "avoid doing more than 10 requests per second" | Free-to-play games only: title, genre, description, developer, publisher, release date | Thumbnail (not documented on the page) | Attribution with an active hyperlink required. Personal and commercial use allowed ([docs](https://www.freetogame.com/api-doc)) |
| **Steam Web API / Store** | Web API key ([terms](https://steamcommunity.com/dev/apiterms)) | Low | 100,000 calls/day ([terms](https://steamcommunity.com/dev/apiterms)) | App lists, user libraries. **Store search/appdetails is undocumented** | Store-only | No implied endorsement. Keep the key confidential. `ISteamApps/GetAppList` is deprecated ([Steamworks](https://partner.steamgames.com/doc/webapi/isteamapps)) |

### Music

| Provider | Auth | Signup friction | Rate / quota (free) | Key data | Images | Storage / attribution terms |
|---|---|---|---|---|---|---|
| **MusicBrainz + CAA** | None for reads. User-Agent required ([API](https://musicbrainz.org/doc/MusicBrainz_API), [Rate Limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)) | None | ~1 req/s per IP; 503 on excess | Artists, releases, release groups, recordings, labels, tags, genres | CAA front/back covers at 250/500/1200 px ([CAA](https://musicbrainz.org/doc/Cover_Art_Archive/API)) | Core data CC0; supplementary data CC BY-NC-SA 3.0 ([license](https://musicbrainz.org/doc/About/Data_License)). Images copyrighted by their owners ([CAA](https://coverartarchive.org/)) |
| **Discogs** | Personal access token, or consumer key/secret, or OAuth ([indexed copy](https://www.discogs.com/developers)) | Low: account, then generate a token | 60/min authenticated, 25/min unauthenticated, by IP | Releases, masters, artists, labels, formats, tracklists | Yes, but image URLs require authentication | "Data provided by Discogs" notice + link required. **6-hour freshness rule**; no storing "longer than is necessary" ([API ToU, indexed copy](https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use)) |
| **iTunes Search API** | None ([docs](https://performance-partners.apple.com/search-api)) | None | ~20 calls/min | Albums, tracks, artists, podcasts, prices | `artworkUrl100`, `artworkUrl60` | Album art only to promote store content, near a "Download on iTunes" badge. Previews may not be cached ([docs](https://performance-partners.apple.com/search-api)) |
| **TheAudioDB** | Free test key `123` in the URL path ([docs](https://www.theaudiodb.com/free_music_api)) | None for the test key | 30 req/min free | Artist bios, albums, tracks, music videos | Yes: fanart, thumbnails, logos (`/small`, `/medium`) | Free use is for development projects. Publishing to an app store requires payment. Credit TheAudioDB for artwork ([terms, indexed copy](https://www.theaudiodb.com/docs_terms_of_use.php)). Free search endpoints appear limited ("Free Limit 1") |
| **Last.fm** | `api_key` query param ([album.search](https://www.last.fm/api/show/album.search)) | Low: Last.fm account, then create an API account ([create](https://www.last.fm/api/account/create)) | At Last.fm's discretion (§4.4) | Albums, artists, tracks, tags, listening data | Returned by the API, but **use of images/artwork is prohibited** (§5.1.8) | Non-commercial only. Credit and link to Last.fm. 100 MB storage cap ([ToS](https://www.last.fm/api/tos)) |
| **Deezer** | None for public data (not confirmed on a docs page, which needs JS/login) | Unclear: the docs page says "You have to login to accept the terms" ([developers](https://developers.deezer.com/api)) | "query quota" exists; number not confirmed ([FAQ](https://support.deezer.com/hc/en-gb/articles/360011538897-Deezer-FAQs-For-Developers)) | Albums, tracks, artists | Yes (cover fields; names not confirmed from docs) | Strictly non-commercial. Images belong to Deezer or rights holders; reproduction requires authorization ([ToU §IV, §VII](https://developers.deezer.com/termsofuse)) |
| **Spotify** | OAuth client credentials ([docs](https://developer.spotify.com/documentation/web-api/tutorials/client-credentials-flow)) | **High**: owner must have Premium; 5 users per app ([migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)) | Quota per developer account ([Jul 2026](https://developer.spotify.com/blog/2026-07-23-web-api-quota-updates)) | Albums, tracks, artists (`popularity` removed) | Yes | "Do not store Spotify Content indefinitely"; cover-art caching temporary only ([Terms IV.3](https://developer.spotify.com/terms)) |

---

## 3. Provider details

### Games

#### RAWG Video Games Database API
- **Data:** Base URL `https://api.rawg.io/api`. Example requests use `?key=YOUR_API_KEY` ([RAWG API docs](https://rawg.io/apidocs)). The docs cover games, platforms, genres and related resources. (The interactive reference at [api.rawg.io/docs](https://api.rawg.io/docs/) is rendered with JavaScript and could not be read automatically, so the exact `/games` parameter list is not confirmed here. The `search`, `page`, `page_size` and `ordering` parameters are widely used, but verify them in the interactive docs.)
- **Auth/signup:** API key from the "Get API Key" link. The older User-Agent request signing is being phased out in favor of the key ([apidocs](https://rawg.io/apidocs)). No credit card is mentioned for the free plan.
- **Limits:** Free plan is 20,000 requests a month. Business is 50,000 a month and Enterprise is 1,000,000 a month. RAWG may change these limits unilaterally ([ToS §8.2, §8.5](https://rawg.io/tos_api)).
- **Terms:** "API is free for personal use as long as you attribute RAWG as the source of the data and/or images and add an active hyperlink from every page where the data of RAWG is used" ([ToS §8.2.1](https://rawg.io/tos_api)). Free commercial use stops at 100,000 MAU or 500,000 page views a month. "No data redistribution" ([apidocs](https://rawg.io/apidocs)). §6.2 says "no parts of the Services or the Content may be copied, reproduced, published, posted online," and §6.5 says RAWG does "not claim ownership of any of the images or data provided by the API" ([ToS](https://rawg.io/tos_api)). **Caching and storage are not addressed explicitly.** Storing a minimal saved-item record and showing attribution on those pages is a reasonable reading for a non-commercial student project, but the ToS do not state it.
- **Ease from Django:** Very easy. One GET request with a query-string key, and the response is JSON.

#### IGDB (Twitch)
- **Data:** Endpoints include `games`, `covers`, `genres` and `platforms`. Each request sends a body listing the fields to return plus filters and sorting ([IGDB docs, indexed copy](https://api-docs.igdb.com/)). Covers come back with an `image_id`. You build image URLs as `https://images.igdb.com/igdb/image/upload/t_{size}/{image_id}.png`, where `cover_big` is 264×374 ([indexed copy](https://api-docs.igdb.com/)).
- **Auth/signup:** Register an app in the Twitch developer console. This requires a verified email and **2FA**, a unique app name, and an OAuth redirect URL (`http://localhost` works) ([Register Your App](https://dev.twitch.tv/docs/authentication/register-app/)). Get an app access token with `POST https://id.twitch.tv/oauth2/token` and `client_id`, `client_secret`, `grant_type=client_credentials`. The response includes `access_token` and `expires_in` but no refresh token ([Getting OAuth tokens](https://dev.twitch.tv/docs/authentication/getting-tokens-oauth/)). Every request sends `Client-ID` and `Authorization: Bearer <token>` headers ([indexed copy](https://api-docs.igdb.com/)).
- **Limits:** 4 requests per second, with 429 above that, and up to 8 open requests ([indexed copy](https://api-docs.igdb.com/)).
- **Terms:** "The IGDB.com API is free for non-commercial usage under the terms of the Twitch Developer Service Agreement." Commercial partnerships ask for user-facing attribution to IGDB.com ([indexed copy](https://api-docs.igdb.com/)). Specific caching rules were not found.
- **Ease from Django:** Moderate. You need to store the token, refresh it when it expires, and send POST requests with a text body.

#### Giant Bomb
- The official API page ([giantbomb.com/api](https://www.giantbomb.com/api/)) returned 403. No official, current rate-limit or terms page could be read. Staff posts on the forum give conflicting limits: 1 request per second, "450 requests within a 15 minute window," and roughly 200 per hour per resource ([API Rate Limiting thread, indexed copy](https://www.giantbomb.com/forums/api-developers-3017/api-rate-limiting-1786442/)). A 2014 announcement says commercial users must get in touch first ([announcement, indexed copy](https://www.giantbomb.com/articles/giant-bomb-api-now-available/1100-793/)). **Current status and terms are unverified, so this is not recommended.**

#### MobyGames
- The key goes in the `api_key` query parameter ([API docs, indexed copy](https://www.mobygames.com/info/api/)). **No free general tier.** Hobbyist costs $9.99 a month and is non-commercial. Free access is offered only to research projects and not-for-profits that apply ([subscribe, indexed copy](https://www.mobygames.com/api/subscribe/), [March 2025 forum notice, indexed copy](https://www.mobygames.com/forum/3/thread/270120/important-changes-to-mobypro-subscription-service/)). Terms require crediting MobyGames and forbid repackaging or reselling the data. **This fails the "free access" requirement unless a research application is approved.**

#### CheapShark
- No key is needed. The API is "designed to be called directly in response to user input," and building a cached catalog through automated calls "can lead to a permanent block." Exceeding the limit returns 429 with `Retry-After` ([docs, indexed copy](https://apidocs.cheapshark.com/)). The data is deals and prices, not a game catalog, so it suits a deal tracker better than a collection app. No attribution clause was found.

#### FreeToGame
- No auth. Base URL `https://www.freetogame.com/api`, with endpoints `/games`, `/games?platform=`, `/games?category=`, `/games?sort-by=`, `/filter?tag=` and `/game?id=`. "Attribution to FreeToGame required with an active hyperlink." Free for personal and commercial use ([API docs](https://www.freetogame.com/api-doc)). **Limitation:** there is no text-search parameter, and coverage is limited to free-to-play games.

#### Steam Web API / Store endpoints
- The Web API terms set 100,000 calls a day, require you to keep the key confidential, and bar any implied endorsement by Valve ([Steam Web API Terms](https://steamcommunity.com/dev/apiterms)). `ISteamApps/GetAppList` is deprecated in favor of `IStoreService/GetAppList` ([Steamworks ISteamApps](https://partner.steamgames.com/doc/webapi/isteamapps)). The store endpoints people use for search and game details (`store.steampowered.com/api/appdetails`) have **no official documentation** that could be found. **Not recommended as the primary search API.**

### Music

#### MusicBrainz API
- **Data:** Base URL `https://musicbrainz.org/ws/2/`. Search with `/<entity>?query=<q>&limit=&offset=` and look up with `/<entity>/<MBID>?inc=`. Entity types include artist, release, release-group, recording, label, genre and others. Add `fmt=json` or `Accept: application/json` to get JSON ([MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API)).
- **Auth:** Not required for lookups, browses or searches ([API](https://musicbrainz.org/doc/MusicBrainz_API)).
- **Limits:** About 1 request per second per IP, with a 503 above that. A User-Agent such as `MyApp/1.0 ( me@example.com )` is required, and generic UAs like `Python-urllib` are throttled as anonymous ([Rate Limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)).
- **Terms:** Core data is CC0. Supplementary data (for example annotations and some user-contributed content) is CC BY-NC-SA 3.0 ([Data License](https://musicbrainz.org/doc/About/Data_License)). The API page says non-commercial use is free and commercial use needs a plan or contact with MetaBrainz ([API](https://musicbrainz.org/doc/MusicBrainz_API)). These are the friendliest terms here for storing saved items locally.
- **Ease from Django:** Easy, as long as you set a custom User-Agent and throttle requests.

#### Cover Art Archive
- `GET https://coverartarchive.org/release-group/{mbid}/front` redirects (307) to the image. `/release/{mbid}/` returns a JSON listing. Thumbnails come in 250, 500 and 1200 px. The page says no rate limiting is in place, although several endpoints list a 503 response ([CAA API](https://musicbrainz.org/doc/Cover_Art_Archive/API)). "All images are copyrighted by their respective copyright owners" ([coverartarchive.org](https://coverartarchive.org/)). No license for reusing the images is stated.

#### Discogs
- **Auth:** Personal access token, sent as `Authorization: Discogs token=...` or `&token=`. A User-Agent that identifies the app is required. Database search requires authentication, and image URLs are only returned to authenticated requests ([developers, indexed copy](https://www.discogs.com/developers)).
- **Limits:** 60 requests a minute authenticated and 25 a minute unauthenticated, by IP, measured over a moving 60-second window. Usage is reported in the `X-Discogs-Ratelimit-*` headers ([indexed copy](https://www.discogs.com/developers)).
- **Terms (updated May 27, 2025, indexed copy):** Some data is CC0 and some is "restricted data." You must show a "Data provided by Discogs" notice with a dofollow link next to the data, plus a non-affiliation notice. You may not display content that is more than 6 hours older than Discogs' own, and you may not cache or store it "longer than is necessary to provide a service to Your application's users" ([API Terms of Use](https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use)). The freshness rule is the main conflict with the assignment's offline requirement.

#### iTunes Search API
- `https://itunes.apple.com/search?term=&media=music&entity=album&limit=` and `/lookup?id=`. No auth. About 20 calls a minute. Artwork is in `artworkUrl100` and `artworkUrl60`. Promotional content such as album art may only promote store content and must sit near a "Download on iTunes" badge. Previews cannot be saved or cached ([iTunes Search API](https://performance-partners.apple.com/search-api)). The API is easy to use, but the terms are built for affiliate promotion, not personal collections.

#### TheAudioDB
- Free key `123`, for example `/api/v1/json/123/searchalbum.php?s=daft_punk`. 30 requests a minute on the free key. Premium costs $8 a month and adds the V2 API ([free_music_api](https://www.theaudiodb.com/free_music_api)). The docs list a "Free Limit" of 1 on several search and lookup endpoints without explaining what it means. It appears to restrict free results heavily, but **this is unconfirmed**. Per the indexed copy of the terms, free use covers development projects and artwork must be credited ([terms, indexed copy](https://www.theaudiodb.com/docs_terms_of_use.php)).

#### Last.fm
- `http://ws.audioscrobbler.com/2.0/?method=album.search&album=...&api_key=...&format=json`. Results include an `image` array ([album.search](https://www.last.fm/api/show/album.search)). Use an identifiable User-Agent ([intro](https://www.last.fm/api/intro)). Terms: "solely for non-commercial purposes" (§3.1). Storage is capped at "a maximum of 100 MB" (§4.3.4). "You will not use any audio, audiovisual, images and/or artwork" (§5.1.8). Credit and link to Last.fm ([ToS](https://www.last.fm/api/tos)). **The image ban rules out a visual collection app.**

#### Deezer
- The docs pages ([api](https://developers.deezer.com/api), [api/search](https://developers.deezer.com/api/search)) need JavaScript or a login, and only show "You have to login to accept the terms and conditions of the simple API." The endpoint shape, quota number and app-registration status **could not be confirmed from official pages**. The FAQ confirms there is "a query quota" ([FAQ](https://support.deezer.com/hc/en-gb/articles/360011538897-Deezer-FAQs-For-Developers)). Terms: "strictly limited for a non-commercial purpose" (§IV), and reproducing images without authorization is forbidden (§VII) ([ToU](https://developers.deezer.com/termsofuse)).

#### Spotify Web API (restrictions, 2024–2026)
- **Nov 27, 2024:** New apps lost access to Related Artists, Recommendations, Audio Features and Analysis, Featured and Category Playlists, 30-second previews in multi-get responses, and algorithmic or editorial playlists ([blog](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)).
- **Apr 15, 2025:** Extended access is limited to "established, scalable, and impactful" use cases, from May 15, 2025 ([blog](https://developer.spotify.com/blog/2025-04-15-updating-the-criteria-for-web-api-extended-access)).
- **Feb 11 / Mar 9, 2026:** "All Development Mode apps require the app owner to have an active Spotify Premium subscription." Apps are capped at 5 users. Batch endpoints (`GET /albums`, `/tracks`, ...) were removed. Search `limit` maximum dropped to 10 (default 5). `popularity` and `followers` fields were removed ([migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)).
- **Jul 23, 2026:** Up to 25 Client IDs per developer. Quota is now counted per developer account, and quota 429s carry `"QUOTA_EXCEEDED"` ([blog](https://developer.spotify.com/blog/2026-07-23-web-api-quota-updates)).
- **Storage terms:** "Do not store Spotify Content indefinitely" (IV.3.1.a). Cover art may only be cached temporarily (IV.3.2) ([Developer Terms](https://developer.spotify.com/terms)).
- **Verdict:** The Premium requirement plus the no-indefinite-storage rule make it a poor fit.

---

## 4. How a Django app would call the top picks

All of these are server-side calls with `requests` or `httpx`. Keep keys in environment variables (for example loaded in `settings.py`), set a timeout, and catch `requests.RequestException` and non-2xx responses so the app can show a "provider unavailable" message, as the assignment requires.

### RAWG (games, top pick)
```python
import os, requests

resp = requests.get(
    "https://api.rawg.io/api/games",
    params={
        "key": os.environ["RAWG_API_KEY"],
        "search": "hollow knight",
        "page_size": 10,
    },
    timeout=5,
)
resp.raise_for_status()
results = resp.json()[
    "results"
]  # each item: id, name, released, background_image, rating, ...
```
- The base URL and the `key` query parameter come from [RAWG API docs](https://rawg.io/apidocs). The `search` and `page_size` parameter names and the `results` response shape come from the interactive docs ([api.rawg.io/docs](https://api.rawg.io/docs/)), which could not be read automatically, so verify them there.
- Show "Data and images from RAWG" with a link on every page that uses RAWG data ([ToS §8.2.1](https://rawg.io/tos_api)).

### IGDB (games, runner-up)
```python
# 1) Token (cache it until expires_in elapses; no refresh token is issued)
tok = requests.post(
    "https://id.twitch.tv/oauth2/token",
    data={
        "client_id": CID,
        "client_secret": SECRET,
        "grant_type": "client_credentials",
    },
    timeout=5,
).json()

# 2) Query
resp = requests.post(
    "https://api.igdb.com/v4/games",
    headers={"Client-ID": CID, "Authorization": f"Bearer {tok['access_token']}"},
    data='search "hollow knight"; fields name,summary,first_release_date,cover.image_id; limit 10;',
    timeout=5,
)
# cover URL: https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg
```
- The token flow comes from [Twitch docs](https://dev.twitch.tv/docs/authentication/getting-tokens-oauth/). The headers and image URL template come from the [IGDB docs, indexed copy](https://api-docs.igdb.com/). The `v4/games` path and the Apicalypse `search` and `fields` syntax match the IGDB docs, but the live page could not be fetched, so verify them there.

### MusicBrainz + Cover Art Archive (music, top pick)
```python
HEADERS = {"User-Agent": "MyMusicShelf/0.1 ( you@example.com )"}

resp = requests.get(
    "https://musicbrainz.org/ws/2/release-group",
    params={"query": 'releasegroup:"OK Computer"', "fmt": "json", "limit": 10},
    headers=HEADERS,
    timeout=5,
)
groups = resp.json()[
    "release-groups"
]  # each: id (MBID), title, first-release-date, artist-credit, ...
cover_url = f"https://coverartarchive.org/release-group/{groups[0]['id']}/front-500"
```
- The search pattern, `fmt=json` and the User-Agent format come from the [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API) and [Rate Limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting) pages. The CAA path and the 250/500/1200 sizes come from the [CAA API](https://musicbrainz.org/doc/Cover_Art_Archive/API). The `front-500` suffix form and the exact `release-groups` JSON key were not verified on the pages read, so check them against a live response.
- Throttle to at most 1 request per second, and treat 503 as rate-limited.

### Discogs (music, runner-up)
```python
resp = requests.get(
    "https://api.discogs.com/database/search",
    params={"q": "Nirvana", "type": "release"},
    headers={
        "Authorization": f"Discogs token={os.environ['DISCOGS_TOKEN']}",
        "User-Agent": "MyMusicShelf/0.1 +https://example.com",
    },
    timeout=5,
)
```
- The header and User-Agent format come from the [Discogs developers page, indexed copy](https://www.discogs.com/developers). The `type` parameter was not confirmed.

---

## 5. Sources (all checked 2026-11-15)

**Games**
- RAWG API docs: https://rawg.io/apidocs
- RAWG API Terms of Service: https://rawg.io/tos_api
- RAWG interactive API reference: https://api.rawg.io/docs/ (JS-rendered, not readable automatically)
- IGDB API docs: https://api-docs.igdb.com/ [indexed copy; 403 to the fetcher]
- IGDB API landing: https://www.igdb.com/api [indexed copy]
- Twitch, Register Your App: https://dev.twitch.tv/docs/authentication/register-app/
- Twitch, Getting OAuth Access Tokens: https://dev.twitch.tv/docs/authentication/getting-tokens-oauth/
- Giant Bomb API: https://www.giantbomb.com/api/ [403]; announcement: https://www.giantbomb.com/articles/giant-bomb-api-now-available/1100-793/ [indexed copy]; rate-limit thread: https://www.giantbomb.com/forums/api-developers-3017/api-rate-limiting-1786442/ [indexed copy]
- MobyGames API docs: https://www.mobygames.com/info/api/ [indexed copy]; subscribe: https://www.mobygames.com/api/subscribe/ [indexed copy]; MobyPro changes: https://www.mobygames.com/forum/3/thread/270120/important-changes-to-mobypro-subscription-service/ [indexed copy]
- CheapShark API docs: https://apidocs.cheapshark.com/ [indexed copy]
- FreeToGame API docs: https://www.freetogame.com/api-doc
- Steam Web API Terms: https://steamcommunity.com/dev/apiterms
- Steamworks ISteamApps: https://partner.steamgames.com/doc/webapi/isteamapps

**Music**
- MusicBrainz API: https://musicbrainz.org/doc/MusicBrainz_API
- MusicBrainz Rate Limiting: https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting
- MusicBrainz Data License: https://musicbrainz.org/doc/About/Data_License
- Cover Art Archive API: https://musicbrainz.org/doc/Cover_Art_Archive/API
- Cover Art Archive home: https://coverartarchive.org/
- Discogs developers: https://www.discogs.com/developers [indexed copy]
- Discogs API Terms of Use: https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use [indexed copy]
- iTunes Search API: https://performance-partners.apple.com/search-api
- TheAudioDB API docs: https://www.theaudiodb.com/free_music_api
- TheAudioDB terms: https://www.theaudiodb.com/docs_terms_of_use.php [indexed copy]
- Last.fm API ToS: https://www.last.fm/api/tos
- Last.fm album.search: https://www.last.fm/api/show/album.search
- Last.fm API intro: https://www.last.fm/api/intro
- Last.fm API account creation: https://www.last.fm/api/account/create
- Deezer developers: https://developers.deezer.com/api ; terms: https://developers.deezer.com/termsofuse ; FAQ: https://support.deezer.com/hc/en-gb/articles/360011538897-Deezer-FAQs-For-Developers
- Spotify, Nov 2024 changes: https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api
- Spotify, Apr 2025 extended access: https://developer.spotify.com/blog/2025-04-15-updating-the-criteria-for-web-api-extended-access
- Spotify, Feb 2026 migration guide: https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide
- Spotify, Jul 2026 quota update: https://developer.spotify.com/blog/2026-07-23-web-api-quota-updates
- Spotify, Client Credentials flow: https://developer.spotify.com/documentation/web-api/tutorials/client-credentials-flow
- Spotify Developer Terms: https://developer.spotify.com/terms

### Open items to verify by hand in a browser
- IGDB: current docs text, especially the Apicalypse examples and the non-commercial terms (the page returned 403 to the fetcher).
- RAWG: exact `/games` parameter list in the interactive docs, and whether the ToS's "no copying" clause is meant to cover local storage of saved items. You could email api@rawg.io to ask.
- Discogs: confirm whether the 6-hour display rule applies to CC0 fields.
- TheAudioDB: what "Free Limit 1" means.
- Deezer: whether new app registration and keyless public endpoints are still available.
- Giant Bomb: whether the API is currently live and what its current terms are.
