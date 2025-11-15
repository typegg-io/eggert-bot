from typing import Optional, Dict, Any

from api.core import API_URL, request


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
    return await request(
        url=f"{API_URL}/v1/leaders",
        params={
            "sort": sort,
            "gamemode": gamemode,
            "country": country,
            "page": page,
            "perPage": per_page,
        },
    )
