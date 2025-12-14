from datetime import timedelta
from typing import Dict, Any

from api.core import API_URL, request
from utils import dates
from utils.dates import parse_date

START_DATE = parse_date("2025-09-21")


async def get_daily_quote(
    date: str = dates.now().strftime("%Y-%m-%d"),
    number: int = None,
    distinct: bool = True,
    results: int = 10,
    country: str = None,
    get_keystrokes: bool = False,
) -> Dict[str, Any]:
    """
    Calls GET /daily with all available filters.
    Returns the JSON response as a dict.
    """
    if number is not None:
        number = max(0, number)
        date = (START_DATE + timedelta(days=number - 1)).strftime("%Y-%m-%d")

    return await request(
        url=f"{API_URL}/v1/daily",
        params={
            "date": date,
            "distinct": distinct,
            "results": results,
            "country": country,
            "showKeystrokeData": get_keystrokes,
        }
    )
