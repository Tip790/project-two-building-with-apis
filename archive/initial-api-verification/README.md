# Initial API verification

The original console script (`rawg_search.py`) and its tests (`test_rawg_search.py`). They were the first proof that the project could reach the RAWG API with a real key and handle its failures.

The RAWG client is being moved into the Django `games` app, which supersedes this script. These files are kept here as a record only. This folder is excluded from pytest and Ruff, and the tests here are not part of the project's test suite.
