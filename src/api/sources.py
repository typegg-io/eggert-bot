from typing import Any
from urllib.parse import quote

from api.core import API_URL, request
from utils.logging import log


async def get_sources(
    search: str | None = None,
    min_publication_year: int | None = None,
    max_publication_year: int | None = None,
    sort: str = "timestamp",
    reverse: bool = True,
    page: int = 1,
    per_page: int = 10,
) -> dict[str, Any]:
    """
    Calls GET /sources with all available filters.
    Returns the JSON response as a dict.
    """
    return await request(
        url=f"{API_URL}/v1/sources",
        params={
            "search": search,
            "minPublicationYear": min_publication_year,
            "maxPublicationYear": max_publication_year,
            "sort": sort,
            "reverse": str(reverse).lower(),
            "page": page,
            "perPage": per_page,
        },
    )


async def get_source(source_id: str) -> dict[str, Any]:
    """
    Calls GET /sources/{sourceId}.
    Returns the JSON response as a dict.
    """
    return await request(f"{API_URL}/v1/sources/{quote(source_id, safe="")}")


async def get_all_sources():
    """Async generator that yields one page of sources at a time."""
    page = 1
    first_page = await get_sources(per_page=1000)
    total_pages = first_page["totalPages"]

    while True:
        data = first_page if page == 1 else await get_sources(page=page, per_page=1000)
        log(f"Fetched page {page}/{total_pages}")
        yield data["sources"]

        if page >= total_pages:
            break

        page += 1
