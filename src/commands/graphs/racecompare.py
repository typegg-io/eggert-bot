import asyncio

from discord.ext import commands

from api.users import get_race
from bot_setup import BotContext
from commands.base import Command
from database.typegg.races import get_races
from database.typegg.users import get_quote_bests
from graphs import match
from utils.errors import NoQuoteRaces, BotError
from utils.keystrokes import get_keystroke_data
from utils.messages import Page, Message
from utils.strings import quote_display, username_with_flag, discord_date

max_users = 5

info = {
    "name": "racecompare",
    "aliases": ["rc"],
    "description": "Overlays multiple users' best races on the same quote on a single graph.\n"
                   "Defaults to the most recently viewed quote.\n"
                   f"Supports up to {max_users} users.",
    "parameters": f"[quote_id] [username1] ... [username{max_users}]",
    "examples": [
        "-rc me eiko",
        "-rc piykyai_3408 me eiko",
    ],
}


class RaceCompare(Command):
    supported_flags = {"raw", "gamemode", "quote_id"}

    @commands.command(aliases=info["aliases"])
    async def racecompare(self, ctx: BotContext, *args: str):
        ctx.flags.status = None
        profiles = await self.get_profiles(ctx, args, max_users)

        if ctx.flags.quote_id:
            quote = await self.get_quote(ctx, ctx.flags.quote_id)
        else:
            quote = await self.get_quote(ctx, user_id=profiles[0]["userId"])

        if len(profiles) > 1:
            await run(ctx, quote, profiles)
        else:
            await run_self(ctx, quote, profiles[0])


async def run(ctx: BotContext, quote: dict, profiles: list[dict]):
    """Compare quote bests across multiple users."""
    description = quote_display(quote, 1000, display_status=True) + "\n"
    themed_line = 0

    # Fetch all best races in parallel
    async def fetch_user_best(profile: dict) -> dict:
        quote_best = get_quote_bests(
            profile["userId"], quote_id=quote["quoteId"],
            order_by="wpm", flags=ctx.flags,
        )
        if not quote_best:
            raise NoQuoteRaces(profile["username"])

        best_race = await get_race_keystrokes(
            profile["userId"],
            quote_best[0]["raceNumber"],
            ctx.flags.raw,
        )
        profile["bestRace"] = best_race
        return profile

    profiles = await asyncio.gather(*[fetch_user_best(p) for p in profiles])
    profiles = sorted(profiles, key=lambda x: -x["bestRace"]["wpm"])

    # Build description and find themed line
    for i, profile in enumerate(profiles):
        if profile["userId"] == ctx.user["userId"]:
            themed_line = i
        description += format_race(profile, profile["bestRace"])

    title = f"Quote Best Comparison - {quote['quoteId']}"
    page = create_comparison_page(
        title=title,
        description=description,
        race_data=[p["bestRace"] for p in profiles],
        theme=ctx.user["theme"],
        themed_line=themed_line,
    )

    message = Message(ctx, page=page)
    await message.send()


async def run_self(ctx: BotContext, quote: dict, profile: dict):
    """Compare a user's best and recent races on the same quote."""
    description = quote_display(quote, 1000, display_status=True) + "\n"

    quote_races = await get_races(
        profile["userId"],
        quote_id=quote["quoteId"],
        order_by="timestamp",
        flags=ctx.flags,
    )
    if len(quote_races) < 2:
        raise BotError(
            "Not Enough Races",
            "User must have at least 2 races\non this quote to compare."
        )

    recent_race = dict(quote_races[-1])
    sorted_by_wpm = sorted(quote_races, key=lambda x: x["wpm"])
    best_race = dict(sorted_by_wpm[-1])

    # New PB
    if recent_race["raceId"] == best_race["raceId"]:
        old_best = dict(sorted_by_wpm[-2])
        description += format_race(profile, best_race, "New Best")
        description += format_race(profile, old_best, "Previous Best")
        race_numbers = [recent_race["raceNumber"], old_best["raceNumber"]]
        race_data = [
            recent_race | {"username": "New Best"},
            old_best | {"username": "Previous Best"},
        ]

    # Not a PB
    else:
        description += format_race(profile, best_race, "Best")
        description += format_race(profile, recent_race, "Recent")
        race_numbers = [best_race["raceNumber"], recent_race["raceNumber"]]
        race_data = [
            best_race | {"username": "Best"},
            recent_race | {"username": "Recent"},
        ]

    # Fetch keystroke data in parallel
    races_with_keystrokes = await asyncio.gather(*[
        get_race_keystrokes(profile["userId"], rn, raw=ctx.flags.raw)
        for rn in race_numbers
    ])

    for i, race in enumerate(races_with_keystrokes):
        del race["username"]
        race_data[i].update(race)

    title = f"Quote Best Comparison - {quote['quoteId']}"
    page = create_comparison_page(
        title=title,
        description=description,
        race_data=race_data,
        theme=ctx.user["theme"],
        themed_line=0
    )

    message = Message(ctx, page=page)
    await message.send()


async def get_race_keystrokes(user_id: str, race_number: int, raw: bool) -> dict:
    """Fetch race with keystroke data and add keystroke_wpm."""
    race = await get_race(user_id, race_number, get_keystrokes=True)
    keystroke_data = get_keystroke_data(race["keystrokeData"])
    if raw:
        race["keystroke_wpm"] = keystroke_data.keystrokeRawWpm
        race["wpm"] = race["rawWpm"]
    else:
        race["keystroke_wpm"] = keystroke_data.keystrokeWpm
    return race


def format_race(profile: dict, race: dict, label: str = None) -> str:
    """Format race information with username, WPM, accuracy, and timestamp."""
    prefix = f"**{label}:** " if label else ""
    return (
        f"{prefix}{username_with_flag(profile)} - {race['wpm']:,.2f} "
        f"({race['accuracy']:.2%}) - {discord_date(race['timestamp'])}\n"
    )


def create_comparison_page(
    title: str,
    description: str,
    race_data: list[dict],
    theme: dict,
    themed_line: int = 0
) -> Page:
    """Create a comparison page with race data."""
    return Page(
        title=title,
        description=description,
        render=lambda: match.render(
            race_data=race_data,
            title=title,
            theme=theme,
            themed_line=themed_line,
        ),
        flag_title=True,
    )
