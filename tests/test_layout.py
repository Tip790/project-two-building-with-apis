"""Tests for the shared page layout: navbar and footer."""

import re

import pytest
from django.urls import reverse

from accounts.models import User

pytestmark = pytest.mark.django_db


def navbar_html(response):
    """Return only the <nav> part of a rendered page."""
    match = re.search(r"<nav\b.*?</nav>", response.content.decode(), re.DOTALL)
    assert match, "page has no <nav> element"
    return match.group(0)


def test_home_page_has_a_search_box_and_tagline(client):
    response = client.get(reverse("games:home"))

    assert response.status_code == 200
    html = response.content.decode()
    assert "Find a game. Track your backlog." in html
    assert '<form action="/" method="get" role="search"' in html
    assert 'name="q"' in html


@pytest.mark.parametrize(
    "url_name", ["games:home", "accounts:login", "accounts:signup"]
)
def test_every_page_credits_rawg_with_a_link_in_the_footer(client, url_name):
    html = client.get(reverse(url_name)).content.decode()

    footer = re.search(r"<footer\b.*?</footer>", html, re.DOTALL)
    assert footer, "page has no <footer> element"
    assert "RAWG" in footer.group(0)
    assert 'href="https://rawg.io"' in footer.group(0)


def test_pages_load_the_local_stylesheet_and_htmx(client):
    html = client.get(reverse("games:home")).content.decode()

    assert 'href="/static/css/app.css"' in html
    assert 'src="/static/js/htmx.min.js"' in html


def test_navbar_shows_account_links_that_match_the_signed_in_state(client):
    signed_out = navbar_html(client.get(reverse("games:home")))

    assert "Search" in signed_out
    assert "Log in" in signed_out
    assert "Sign up" in signed_out
    for label in ("My Library", "Settings", "Log out"):
        assert label not in signed_out

    user = User.objects.create_user(username="navplayer", password="unused-pw-123")
    client.force_login(user)
    signed_in = navbar_html(client.get(reverse("games:home")))

    for label in ("Search", "My Library", "Settings", "Log out", "navplayer"):
        assert label in signed_in
    assert "Log in" not in signed_in
    assert "Sign up" not in signed_in
