from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

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
    """Sharing for the user's library: the Public/Private switch and share link."""
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
    return render(
        request, "accounts/settings.html", {"form": form, "share_url": share_url}
    )
