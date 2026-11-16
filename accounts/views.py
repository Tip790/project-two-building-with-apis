from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from rest_framework.authtoken.models import Token

from .forms import SharingForm, SignUpForm


def signup(request):
    """Create an account, sign the new user in, and send them on."""
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def settings_page(request):
    """Sharing (the Public/Private switch and share link) and the API token."""
    if request.method == "POST":
        form = SharingForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            visibility = "Public" if user.library_is_public else "Private"
            messages.success(request, f"Your library is now {visibility}.")
            return redirect("accounts:settings")
    else:
        form = SharingForm(instance=request.user)
    share_url = request.build_absolute_uri(
        reverse("shared:library", args=[request.user.username])
    )
    # Every user has a token to copy; the first visit creates it.
    token, _ = Token.objects.get_or_create(user=request.user)
    context = {
        "form": form,
        "share_url": share_url,
        "api_token": token.key,
        "api_entries_url": request.build_absolute_uri(reverse("api:entry-list")),
    }
    return render(request, "accounts/settings.html", context)


@login_required
@require_POST
def regenerate_token(request):
    """Replace the user's API token; the old one stops working at once."""
    with transaction.atomic():
        Token.objects.filter(user=request.user).delete()
        Token.objects.create(user=request.user)
    messages.success(
        request, "Your API token was regenerated. The old token no longer works."
    )
    return redirect("accounts:settings")
