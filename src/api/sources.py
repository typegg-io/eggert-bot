from typing import Optional, Dict, Any
from urllib.parse import quote

import aiohttp

from api.core import get_params
from config import API_URL


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
    url = f"{API_URL}/sources"
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
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"API returned status {response.status}: {text}")


async def get_source(source_id: str) -> Dict[str, Any]:
    """
    Calls GET /sources/{sourceId}.
    Returns the JSON response as a dict.
    """
    url = f"{API_URL}/sources/{quote(source_id, safe="")}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"API returned status {response.status}: {text}")
