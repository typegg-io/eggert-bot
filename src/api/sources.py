from typing import Optional, Dict, Any
from urllib.parse import quote

import aiohttp

from api.core import API_URL, get_params, get_response


async def get_sources(
    search: Optional[str] = None,
    min_publication_year: Optional[int] = None,
    max_publication_year: Optional[int] = None,
    sort: str = "created",
    reverse: bool = True,
    page: int = 1,
    per_page: int = 10,
) -> Dict[str, Any]:
    """
    Calls GET /sources with all available filters.
    Returns the JSON response as a dict.
    """
    url = f"{API_URL}/v1/sources"
    params = get_params({
        "search": search,
        "minPublicationYear": min_publication_year,
        "maxPublicationYear": max_publication_year,
        "sort": sort,
        "reverse": str(reverse).lower(),
        "page": page,
        "perPage": per_page,
    })

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            return await get_response(response)


async def get_source(source_id: str) -> Dict[str, Any]:
    """
    Calls GET /sources/{sourceId}.
    Returns the JSON response as a dict.
    """
    url = f"{API_URL}/v1/sources/{quote(source_id, safe="")}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await get_response(response)


async def get_all_sources():
    all_sources = []
    page = 1
    first_page = await get_sources(per_page=1000)
    total_pages = first_page["totalPages"]

    while True:
        data = first_page if page == 1 else await get_sources(page=page, per_page=1000)
        for source in data["sources"]:
            all_sources.append(source)

        if page >= total_pages:
            break

        page += 1

    return all_sources
