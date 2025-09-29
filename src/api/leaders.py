from typing import Optional, Dict, Any

import aiohttp

from api.core import get_params
from config import API_URL


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
    url = f"{API_URL}/leaders"
    params = get_params({
        "sort": sort,
        "gamemode": gamemode,
        "country": country,
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
