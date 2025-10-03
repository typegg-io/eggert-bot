from typing import Optional, Dict, Any

import aiohttp

from api.core import API_URL, get_params, get_response


async def get_leaders(
    sort: str = "totalPp",
    gamemode: str = "any",
    country: Optional[str] = None,
    page: int = 1,
    per_page: int = 10,
) -> Dict[str, Any]:
    """
    Calls GET /leaders with all available filters.
    Returns the JSON response as a dict.
    """
    url = f"{API_URL}/v1/leaders"
    params = get_params({
        "sort": sort,
        "gamemode": gamemode,
        "country": country,
        "page": page,
        "perPage": per_page,
    })

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            return await get_response(response)
