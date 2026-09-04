from typing import Any

from api.core import request
from config import API_URL


async def get_leaders(
    sort: str = "totalPp",
    gamemode: str = "any",
    country: str | None = None,
    page: int = 1,
    per_page: int = 10,
) -> dict[str, Any]:
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


async def get_multiplayer_leaders(
    metric: str = "wpm",
    page: int = 1,
    per_page: int = 100,
) -> dict[str, Any]:
    """Temporary internal API."""
    return await request(
        url=f"{API_URL}/leaderboard/multiplayer/{metric}",
        params={"page": page, "perPage": per_page},
    )
