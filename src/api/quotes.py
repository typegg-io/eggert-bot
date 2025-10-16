from typing import Optional, Dict, Any
from urllib.parse import quote

import aiohttp

from api.core import API_URL, get_params, get_response
from utils.errors import UnknownQuote


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
            return await get_response(response, exceptions={
                404: UnknownQuote(quote_id),
            })


async def get_all_quotes():
    all_quotes = []
    page = 1
    first_page = await get_quotes(status="any", per_page=1000)
    total_pages = first_page["totalPages"]

    while True:
        data = first_page if page == 1 else await get_quotes(page=page, status="any", per_page=1000)
        for quote in data["quotes"]:
            all_quotes.append(quote)

        if page >= total_pages:
            break

        page += 1

    return all_quotes
