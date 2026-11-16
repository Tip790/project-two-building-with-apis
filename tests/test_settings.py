"""Tests for how config/settings.py reads its environment."""

import importlib.util
from pathlib import Path

import dotenv
import pytest
from django.core.exceptions import ImproperlyConfigured

SETTINGS_FILE = Path(__file__).resolve().parent.parent / "config" / "settings.py"
SETTINGS_VARIABLES = ("DJANGO_SECRET_KEY", "DJANGO_DEBUG", "RAWG_API_KEY")


def load_settings(monkeypatch, **env):
    """Run config/settings.py from scratch with only the given variables set.

    The developer's real .env file is never read.
    """
    for name in SETTINGS_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)

    spec = importlib.util.spec_from_file_location("fresh_settings", SETTINGS_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_settings_refuse_to_load_without_a_secret_key(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
        load_settings(monkeypatch)


def test_debug_is_off_unless_turned_on(monkeypatch):
    assert load_settings(monkeypatch, DJANGO_SECRET_KEY="x").DEBUG is False
    assert (
        load_settings(monkeypatch, DJANGO_SECRET_KEY="x", DJANGO_DEBUG="no").DEBUG
        is False
    )
    assert (
        load_settings(monkeypatch, DJANGO_SECRET_KEY="x", DJANGO_DEBUG="True").DEBUG
        is True
    )


def test_rawg_key_is_optional(monkeypatch):
    settings = load_settings(monkeypatch, DJANGO_SECRET_KEY="x")
    assert settings.RAWG_API_KEY == ""

    settings = load_settings(monkeypatch, DJANGO_SECRET_KEY="x", RAWG_API_KEY="abc")
    assert settings.RAWG_API_KEY == "abc"


def test_test_suite_uses_a_dummy_rawg_key(settings):
    assert settings.RAWG_API_KEY == "test-dummy-rawg-key"
