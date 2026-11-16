Tech Requirements: Django, Django REST Framework (DRF), SQLite, uv, Ruff, Tailwind with DaisyUI, HTMX, pytest

Business Requirements:
The project must have one cohesive purpose. The purpose of the app must serve a clear user need, with features that work together.

Users can find items through an external API. Choose an API provider with free access sufficient to build and demonstrate the project. 

Users can save selected items to the application. Store enough information locally for saved items to remain accessible when the external API is unavailable.

Users can add and edit their own information. This might include notes, ratings, status, or progress. Choose information that serves the application's purpose.

Users can browse their saved items on a website. Include search, filtering, sorting, and pagination. These features must operate on locally saved data.

Users must sign in to manage their saved data. Decide who can view or modify it. You may choose private data, public viewing, or selective sharing. Enforce those rules through both the website and the API.

The application provides its own API. Support listing, creating, updating, and deleting saved entries.

The application handles unsuccessful external requests. Show a useful message when the provider is unavailable or a request fails. 

For example, a movie application might retrieve titles and descriptions from an external provider. Users could save movies and add their own ratings, notes, and viewing status. The database would store those choices, and the API would let another program access them.