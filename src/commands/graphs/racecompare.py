import asyncio
from typing import Optional

from discord.ext import commands

from api.users import get_race
from commands.base import Command
from database.typegg.races import get_races
from database.typegg.users import get_quote_bests
from graphs import match
from utils.errors import NoQuoteRaces, GeneralException
from utils.keystrokes import get_keystroke_data
from utils.messages import Page, Message
from utils.strings import quote_display, username_with_flag, discord_date

max_users = 5

info = {
    "name": "racecompare",
    "aliases": ["rc"],
    "description": "Displays separate races of the same quote on a single graph",
    "parameters": f"[quote_id] [username1] ... [username{max_users}]",
}


class RaceCompare(Command):
    @commands.command(aliases=info["aliases"])
    async def racecompare(self, ctx, quote_id: Optional[str] = None, *user_args: Optional[str]):
        if quote_id and not user_args:
            user_args = [quote_id]
            quote_id = None

        user_args = list(user_args) if user_args else [ctx.user["userId"]]
        user_args = user_args[:max_users]
        usernames = set(user_args)
        profiles = []

        for i, username in enumerate(usernames):
            profile = await self.get_profile(ctx, username, races_required=True)
            profiles.append(profile)
            await self.import_user(ctx, profile)

            if i == 0:
                quote = await self.get_quote(ctx, quote_id, profile["userId"])

        if len(profiles) > 1:
            await run(ctx, quote, profiles)
        else:
            await run_self(ctx, quote, profiles[0])


async def run(ctx: commands.Context, quote: dict, profiles: list[dict]):
    """Compare quote bests across multiple users."""
    description = quote_display(quote, 1000, display_status=True) + "\n"
    themed_line = 0

    # Fetch all best races in parallel
    async def fetch_user_best(profile: dict) -> dict:
        quote_best = get_quote_bests(profile["userId"], quote_id=quote["quoteId"])
        if not quote_best:
            raise NoQuoteRaces(profile["username"])

        best_race = await get_race_keystrokes(
            profile["userId"],
            quote_best[0]["raceNumber"]
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
        themed_line=themed_line
    )

    message = Message(ctx, page=page)
    await message.send()


async def run_self(ctx: commands.Context, quote: dict, profile: dict):
    """Compare a user's best and recent races on the same quote."""
    description = quote_display(quote, 1000, display_status=True) + "\n"

    quote_races = await get_races(profile["userId"], quote_id=quote["quoteId"], order_by="timestamp")
    if len(quote_races) < 2:
        raise GeneralException(
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
        description += format_race(profile, old_best, "Old Best")
        race_numbers = [recent_race["raceNumber"], old_best["raceNumber"]]
        race_data = [recent_race, old_best]

    # Not a PB
    else:
        description += format_race(profile, best_race, "Best")
        description += format_race(profile, recent_race, "Recent")
        race_numbers = [best_race["raceNumber"], recent_race["raceNumber"]]
        race_data = [best_race, recent_race]

    # Fetch keystroke data in parallel
    races_with_keystrokes = await asyncio.gather(*[
        get_race_keystrokes(profile["userId"], rn)
        for rn in race_numbers
    ])

    for i, race in enumerate(races_with_keystrokes):
        race_data[i].update(race)
        race_data[i]["username"] = profile["username"]

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


async def get_race_keystrokes(user_id: str, race_number: int) -> dict:
    """Fetch race with keystroke data and add keystroke_wpm."""
    race = await get_race(user_id, race_number, get_keystrokes=True)
    keystroke_data = get_keystroke_data(race["keystrokeData"])
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
        )
    )
