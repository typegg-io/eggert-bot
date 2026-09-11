"""The user endpoints."""

from typing import Any
from urllib.parse import quote

from api.core import request
from config import API_URL
from utils.errors import ProfileNotFound, RaceNotFound


async def get_profile(user_id: str, universe: str | None = None) -> dict[str, Any]:
    """
    Calls GET /users/{userId}, optionally scoped to a universe.
    Returns the JSON response as a dict.
    """
    return await request(
        url=f"{API_URL}/v1/users/{quote(user_id, safe="")}",
        params={"universe": universe},
        exceptions={404: ProfileNotFound(user_id)},
    )


async def get_races(
    user_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    start_number: int | None = None,
    end_number: int | None = None,
    quote_id: str | None = None,
    min_pp: float | None = None,
    max_pp: float | None = None,
    min_wpm: float | None = None,
    max_wpm: float | None = None,
    gamemode: str = "any",
    sort: str = "timestamp",
    reverse: bool = True,
    get_keystrokes: bool = False,
    page: int = 1,
    per_page: int = 10,
) -> dict[str, Any]:
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


async def get_race(user_id: str, race_number: int, get_keystrokes: bool = False) -> dict[str, Any]:
    """
    Calls GET /users/{userId}/races/{raceNumber}.
    Returns the JSON response as a dict.
    """
    return await request(
        url=f"{API_URL}/v1/users/{quote(user_id, safe="")}/races/{race_number}",
        params={"showKeystrokeData": get_keystrokes},
        exceptions={404: RaceNotFound(user_id, race_number)}
    )


async def get_latest_race(user_id: str) -> dict[str, Any]:
    """
    Gets a user's latest race.
    Returns the JSON response as a dict.
    """
    race_list = await get_races(user_id, per_page=1)

    return race_list["races"][0]


async def get_quotes(
    user_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    start_number: int | None = None,
    end_number: int | None = None,
    min_pp: float | None = None,
    max_pp: float | None = None,
    min_wpm: float | None = None,
    max_wpm: float | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    gamemode: str | None = "any",
    status: str = "any",
    sort: str = "timestamp",
    max_rank: int | None = None,
    universe: str | None = None,
    reverse: bool = True,
    page: int = 1,
    per_page: int = 10,
) -> dict[str, Any]:
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
            maxRank=max_rank,
            universe=universe,
            reverse=str(reverse).lower(),
            page=page,
            perPage=per_page,
        )
    )


async def get_quote(user_id: str, quote_id: str) -> dict[str, Any]:
    """
    Calls GET /users/{userId}/quotes/{quoteId} with all available filters.
    Returns the JSON response as a dict.
    """
    return await request(f"{API_URL}/v1/users/{quote(user_id, safe="")}/quotes/{quote_id}")


async def get_quote_rankings(
    user_id: str,
    max_rank: int = 10,
    status: str = "ranked",
    universe: str | None = None,
) -> dict[str, Any]:
    """
    Calls GET /users/{userId}/quote-rankings, optionally scoped to a universe.
    Returns the user's quote leaderboard placement counts (rank -> count).
    """
    return await request(
        url=f"{API_URL}/v1/users/{quote(user_id, safe="")}/quote-rankings",
        params=dict(
            maxRank=max_rank,
            status=status,
            universe=universe,
        ),
        exceptions={404: ProfileNotFound(user_id)},
    )
