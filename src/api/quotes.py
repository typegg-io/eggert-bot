import aiohttp
from typing import Optional, Dict, Any

from config import API_URL


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
    url = f"{API_URL}/quotes"

    params: Dict[str, Any] = {
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
        "distinct": str(distinct).lower(),
        "reverse": str(reverse).lower(),
        "page": page,
        "perPage": per_page,
    }

    params = {k: v for k, v in params.items() if v is not None}

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
    url = f"{API_URL}/quotes/{quote_id}"
    params = {"distinct": str(distinct).lower()}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                return {}
            else:
                text = await response.text()
                raise Exception(f"API returned status {response.status}: {text}")