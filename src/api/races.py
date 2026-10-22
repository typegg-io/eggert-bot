"""The race endpoint."""

from typing import Any
from urllib.parse import quote

from api.core import request
from config import API_URL


async def get_race(race_id: str, get_keystrokes: bool = False) -> dict[str, Any]:
    """
    Calls GET /races/{raceId}.
    Returns the JSON response as a dict.
    """
    return await request(
        f"{API_URL}/v1/races/{quote(race_id, safe="")}",
        params={"showKeystrokeData": get_keystrokes},
    )
