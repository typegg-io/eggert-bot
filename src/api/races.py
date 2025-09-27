from typing import Dict, Any

import aiohttp

from config import API_URL


async def get_race(race_id: str) -> Dict[str, Any]:
    """
    Calls GET /races/{raceId}.
    Returns the JSON response as a dict.
    """

    url = f"{API_URL}/races/{race_id}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"API returned status {response.status}: {text}")
