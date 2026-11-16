"""The library REST API (Django REST Framework)."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets

from .filters import EntryFilter
from .models import LibraryEntry
from .pagination import EntryPagination
from .serializers import EntrySerializer


class EntryViewSet(viewsets.ReadOnlyModelViewSet):
    """The requester's own library entries.

    Every lookup goes through the requester's entries, so anyone else's entry
    is a 404, whether their library is Public or Private. Search, filters and
    sort are the website's own `EntryFilter`, with the same parameter names.
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
