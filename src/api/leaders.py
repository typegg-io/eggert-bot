"""The leaderboard endpoints."""

from typing import Any

from api.core import request
from config import API_URL


async def get_leaders(
    sort: str = "totalPp",
    gamemode: str = "any",
    country: str | None = None,
    page: int = 1,
    per_page: int = 10,
    universe: str | None = None,
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
            "universe": universe,
        },
    )
