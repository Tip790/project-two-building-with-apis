"""The library REST API (Django REST Framework)."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, viewsets

from .filters import EntryFilter
from .models import LibraryEntry
from .pagination import EntryPagination
from .serializers import EntrySerializer
from .views import _visible_library_owner_or_404


class EntryViewSet(viewsets.ModelViewSet):
    """The requester's own library entries: list, create, read, update, delete.

    Every lookup goes through the requester's entries, so anyone else's entry
    is a 404, whether their library is Public or Private, and can't be
    changed. Search, filters and sort are the website's own `EntryFilter`,
    with the same parameter names. Create goes through the shared save flow.
    """

    serializer_class = EntrySerializer
    pagination_class = EntryPagination
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EntryFilter

    def get_queryset(self):
        return (
            LibraryEntry.objects.filter(user=self.request.user)
            .select_related("game", "platform")
            .prefetch_related("game__genres", "game__platforms")
        )


class SharedLibraryEntries(generics.ListAPIView):
    """A user's library, read-only, at /api/users/<username>/entries/."""

    serializer_class = EntrySerializer
    pagination_class = EntryPagination
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EntryFilter

    def get_queryset(self):
        # The website's rule: Private libraries are a 404 to everyone but
        # their owner, identical to a username that doesn't exist.
        owner = _visible_library_owner_or_404(self.request, self.kwargs["username"])
        return (
            LibraryEntry.objects.filter(user=owner)
            .select_related("game", "platform")
            .prefetch_related("game__genres", "game__platforms")
        )
