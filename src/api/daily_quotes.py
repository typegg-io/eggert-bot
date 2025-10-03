from typing import Dict, Any

import aiohttp

from api.core import API_URL, get_params, get_response
from utils import dates


async def get_daily_quote(
    date: str = dates.now().strftime("%Y-%m-%d"),
    country: str = None,
) -> Dict[str, Any]:
    """
    Calls GET /daily with all available filters.
    Returns the JSON response as a dict.
    """
    url = f"{API_URL}/v1/daily"
    params = get_params({
        "date": date,
        "country": country,
    })

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            return await get_response(response)
