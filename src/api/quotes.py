from typing import Optional, Dict, Any
from urllib.parse import quote

import aiohttp

from api.core import API_URL, get_params


async def get_quotes(
    search: Optional[str] = None,
    min_difficulty: Optional[float] = None,
    max_difficulty: Optional[float] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    min_publication_year: Optional[int] = None,
    max_publication_year: Optional[int] = None,
    source_id: str = None,
    status: str = "ranked",
    sort: str = "created",
    distinct: bool = True,
    reverse: bool = True,
    page: int = 1,
    per_page: int = 10,
) -> Dict[str, Any]:
    """
    Calls GET /quotes with all available filters.
    Returns the JSON response as a dict.
    """
    url = f"{API_URL}/v1/quotes"
    params = get_params({
        "search": search,
        "minDifficulty": min_difficulty,
        "maxDifficulty": max_difficulty,
        "minLength": min_length,
        "maxLength": max_length,
        "minPublicationYear": min_publication_year,
        "maxPublicationYear": max_publication_year,
        "sourceId": source_id,
        "status": status,
        "sort": sort,
        "distinct": distinct,
        "reverse": reverse,
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


async def get_quote(quote_id: str, distinct: bool = True) -> Dict[str, Any]:
    """
    Calls GET /quotes/{quoteId}.
    Returns the JSON response as a dict.
    """
    url = f"{API_URL}/v1/quotes/{quote(quote_id, safe="")}"
    params = get_params({"distinct": distinct})

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                return {}
            else:
                text = await response.text()
                raise Exception(f"API returned status {response.status}: {text}")
