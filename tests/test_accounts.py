"""Tests for sign-up, login, logout, and password change."""

import pytest
from django.contrib import auth
from django.urls import reverse

from accounts.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-test-password-123"


def test_sign_up_creates_a_private_account_and_signs_the_user_in(client):
    response = client.post(
        reverse("accounts:signup"),
        {"username": "newplayer", "password1": PASSWORD, "password2": PASSWORD},
    )

    assert response.status_code == 302
    user = User.objects.get(username="newplayer")
    assert user.library_is_public is False
    assert auth.get_user(client) == user


def test_sign_up_with_mismatched_passwords_shows_an_error(client):
    response = client.post(
        reverse("accounts:signup"),
        {"username": "newplayer", "password1": PASSWORD, "password2": "different"},
    )

    assert response.status_code == 200
    assert "didn’t match" in response.content.decode()
    assert not User.objects.filter(username="newplayer").exists()


@pytest.fixture
def player():
    return User.objects.create_user(username="player", password=PASSWORD)


def test_log_in_then_log_out(client, player):
    response = client.post(
        reverse("accounts:login"), {"username": "player", "password": PASSWORD}
    )
    assert response.status_code == 302
    assert auth.get_user(client) == player

    response = client.post(reverse("accounts:logout"))
    assert response.status_code == 302
    assert not auth.get_user(client).is_authenticated


def test_log_in_with_a_wrong_password_is_refused(client, player):
    response = client.post(
        reverse("accounts:login"), {"username": "player", "password": "wrong"}
    )

    assert response.status_code == 200
    assert not auth.get_user(client).is_authenticated


def test_change_password(client, player):
    client.force_login(player)
    new_password = "another-long-password-456"

    response = client.post(
        reverse("accounts:password_change"),
        {
            "old_password": PASSWORD,
            "new_password1": new_password,
            "new_password2": new_password,
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("accounts:password_change_done")
    player.refresh_from_db()
    assert player.check_password(new_password)


def test_password_change_requires_sign_in(client):
    response = client.get(reverse("accounts:password_change"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_admin_lists_users_with_their_sharing_setting(admin_client, player):
    response = admin_client.get(reverse("admin:accounts_user_changelist"))

    assert response.status_code == 200
    assert "player" in response.content.decode()

    response = admin_client.get(reverse("admin:accounts_user_change", args=[player.pk]))
    assert 'name="library_is_public"' in response.content.decode()
