"""Settings for the test suite.

Tests never depend on the developer's .env file: a test-only secret key is
supplied here, and RAWG gets a dummy key so no test can reach the real API
with real credentials.
"""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-for-real-use")

from .settings import *  # noqa: E402, F403

RAWG_API_KEY = "test-dummy-rawg-key"

# Fast password hashing keeps account tests quick.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
