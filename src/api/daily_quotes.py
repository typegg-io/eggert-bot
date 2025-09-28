from typing import Dict, Any

import aiohttp

from config import API_URL
from utils import dates


async def get_daily_quote(
    date: str = dates.now().strftime("%Y-%m-%d"),
    country: str = None,
) -> Dict[str, Any]:
    """
    Calls GET /daily with all available filters.
    Returns the JSON response as a dict.
    """
    url = f"{API_URL}/daily"

    params: Dict[str, Any] = {
        "date": date,
        "country": country,
    }

    params = {k: v for k, v in params.items() if v is not None}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"API returned status {response.status}: {text}")
