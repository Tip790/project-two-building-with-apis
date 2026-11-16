"""API pagination: the website's page size, plus the RAWG credit."""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .views import ENTRIES_PER_PAGE

# RAWG's terms require crediting it, with a link, wherever its data is shown.
RAWG_ATTRIBUTION = {
    "text": "Game data from RAWG.",
    "name": "RAWG",
    "url": "https://rawg.io",
}


class EntryPagination(PageNumberPagination):
    page_size = ENTRIES_PER_PAGE

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        return Response({**response.data, "attribution": RAWG_ATTRIBUTION})

    def get_paginated_response_schema(self, schema):
        schema = super().get_paginated_response_schema(schema)
        schema["properties"]["attribution"] = {
            "type": "object",
            "example": RAWG_ATTRIBUTION,
        }
        return schema
