from typing import Dict, Any
from urllib.parse import quote

import aiohttp

from core import API_URL


async def get_race(race_id: str) -> Dict[str, Any]:
    """
    Calls GET /races/{raceId}.
    Returns the JSON response as a dict.
    """
    url = f"{API_URL}/v1/races/{quote(race_id, safe="")}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"API returned status {response.status}: {text}")
