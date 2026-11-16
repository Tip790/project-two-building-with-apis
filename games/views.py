from django.shortcuts import render


def home(request):
    """The home page: a game search box and a short tagline."""
    return render(request, "games/home.html", {"query": request.GET.get("q", "")})
