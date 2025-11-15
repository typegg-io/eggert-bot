from typing import Optional, Dict, Any
from urllib.parse import quote

from api.core import API_URL, request
from utils.errors import ProfileNotFound, RaceNotFound


async def get_profile(user_id: str):
    """
    Calls GET /users/{userId}.
    Returns the JSON response as a dict.
    """
    return await request(
        url=f"{API_URL}/v1/users/{quote(user_id, safe="")}",
        exceptions={404: ProfileNotFound(user_id)},
    )


async def get_races(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    start_number: Optional[int] = None,
    end_number: Optional[int] = None,
    quote_id: Optional[str] = None,
    min_pp: Optional[float] = None,
    max_pp: Optional[float] = None,
    min_wpm: Optional[float] = None,
    max_wpm: Optional[float] = None,
    gamemode: str = "any",
    sort: str = "timestamp",
    reverse: bool = True,
    get_keystrokes: bool = False,
    page: int = 1,
    per_page: int = 10,
) -> Dict[str, Any]:
    """
    Calls GET /users/{userId}/races with all available filters.
    Returns the JSON response as a dict.
    """
    return await request(
        url=f"{API_URL}/v1/users/{quote(user_id, safe="")}/races",
        params=dict(
            startDate=start_date,
            endDate=end_date,
            startNumber=start_number,
            endNumber=end_number,
            quoteId=quote_id,
            minPp=min_pp,
            maxPp=max_pp,
            minWpm=min_wpm,
            maxWpm=max_wpm,
            gamemode=gamemode,
            sort=sort,
            reverse=str(reverse).lower(),
            showKeystrokeData=str(get_keystrokes).lower(),
            page=page,
            perPage=per_page,
        )
    )


async def get_race(user_id: str, race_number: int, get_keystrokes=False) -> Dict[str, Any]:
    """
    Calls GET /users/{userId}/races/{raceNumber}.
    Returns the JSON response as a dict.
    """
    return await request(
        url=f"{API_URL}/v1/users/{quote(user_id, safe="")}/races/{race_number}",
        params={"showKeystrokeData": get_keystrokes},
        exceptions={404: RaceNotFound(user_id, race_number)}
    )


async def get_latest_race(user_id: str) -> Dict[str, Any]:
    """
    Gets a user's latest race.
    Returns the JSON response as a dict.
    """
    race_list = await get_races(user_id, per_page=1)

    return race_list["races"][0]


async def get_quotes(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    start_number: Optional[int] = None,
    end_number: Optional[int] = None,
    min_pp: Optional[float] = None,
    max_pp: Optional[float] = None,
    min_wpm: Optional[float] = None,
    max_wpm: Optional[float] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    gamemode: str = "any",
    status: str = "any",
    sort: str = "timestamp",
    reverse: bool = True,
    page: int = 1,
    per_page: int = 10,
) -> Dict[str, Any]:
    """
    Calls GET /users/{userId}/quotes with all available filters.
    Returns the JSON response as a dict.
    """
    return await request(
        url=f"{API_URL}/v1/users/{quote(user_id, safe="")}/quotes",
        params=dict(
            startDate=start_date,
            endDate=end_date,
            startNumber=start_number,
            endNumber=end_number,
            minPp=min_pp,
            maxPp=max_pp,
            minWpm=min_wpm,
            maxWpm=max_wpm,
            minLength=min_length,
            maxLength=max_length,
            gamemode=gamemode,
            status=status,
            sort=sort,
            reverse=str(reverse).lower(),
            page=page,
            perPage=per_page,
        )
    )


async def get_quote(user_id: str, quote_id: str) -> Dict[str, Any]:
    """
    Calls GET /users/{userId}/quotes/{quoteId} with all available filters.
    Returns the JSON response as a dict.
    """
    return await request(f"{API_URL}/v1/users/{quote(user_id, safe="")}/quotes/{quote_id}")
