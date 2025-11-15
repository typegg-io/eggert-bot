from typing import Dict, Any
from urllib.parse import quote

from api.core import API_URL, request


async def get_race(race_id: str) -> Dict[str, Any]:
    """
    Calls GET /races/{raceId}.
    Returns the JSON response as a dict.
    """
    return await request(f"{API_URL}/v1/races/{quote(race_id, safe="")}")
