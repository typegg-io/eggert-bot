from datetime import timedelta
from typing import Dict, Any

import aiohttp

from api.core import API_URL, get_params, get_response
from utils import dates
from utils.dates import parse_date

START_DATE = parse_date("2025-09-21")


async def get_daily_quote(
    date: str = dates.now().strftime("%Y-%m-%d"),
    number: int = None,
    distinct: bool = True,
    results: int = 10,
    country: str = None,
) -> Dict[str, Any]:
    """
    Calls GET /daily with all available filters.
    Returns the JSON response as a dict.
    """
    if number is not None:
        number = max(0, number)
        date = (START_DATE + timedelta(days=number - 1)).strftime("%Y-%m-%d")

    url = f"{API_URL}/v1/daily"
    params = get_params({
        "date": date,
        "distinct": distinct,
        "results": results,
        "country": country,
    })

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            return await get_response(response)
