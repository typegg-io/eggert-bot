import asyncio

from discord.ext import commands

from api.users import get_race
from command_info import CommandInfo
from commands.base import Command, enforce_daily_quote
from config import DAILY_QUOTE_CHANNEL_ID
from context import BotContext
from database.typegg.races import get_race as get_race_db, get_races
from database.typegg.users import get_quote_bests
from graphs import match
from utils.dates import discord_date
from utils.errors import BotError, NoQuoteRaces
from utils.flags import Flags
from utils.keystrokes import get_keystroke_data
from utils.messages import Message, Page, usable_in
from utils.schemas import Profile, Theme
from utils.strings import quote_display, username_with_flag

max_users = 5

info = CommandInfo(
    name="racecompare",
    aliases=["rc"],
    description="Overlays multiple users' best races on the same quote on a single graph.\n"
                f"Supports up to {max_users} users.\n"
                "Race numbers compare your own races instead, and one number compares a race with your best.\n"
                "After a quote ID, the numbers are attempt numbers from the site's replay history.",
    parameters=f"[quote_id:latest] [username1] ... [username{max_users}] [race_number1] ... [race_number{max_users}]",
    examples=[
        "-rc me eiko",
        "-rc piykyai_3408 me eiko",
        "-rc 1500 1520",
        "-rc piykyai_3408 12 15",
    ],
)


class RaceCompare(Command):
    """Overlay several users' best races on one quote."""

    supported_flags = {"raw", "gamemode", "quote_id", "number"}

    @commands.command(aliases=info.aliases)
    @usable_in(DAILY_QUOTE_CHANNEL_ID)
    async def racecompare(self, ctx: BotContext, *args: str):
        """Compare the named users on a quote, one user against themselves, or races picked by number."""
        ctx.flags.status = None
        profiles = await self.get_profiles(ctx, args, max_users)

        if ctx.flags.numbers:
            await self.compare_picked(ctx, profiles)
            return

        if ctx.flags.quote_id:
            quote = await self.get_quote(ctx, ctx.flags.quote_id)
        else:
            quote = await self.get_quote(ctx, user_id=profiles[0]["userId"])

        enforce_daily_quote(ctx, quote["quoteId"])

        if len(profiles) > 1:
            await run(ctx, quote, profiles)
        else:
            await run_self(ctx, quote, profiles[0])

    async def compare_picked(self, ctx: BotContext, profiles: list[Profile]) -> None:
        """Compare one user's races picked by race number, or by attempt number after a quote ID."""
        if len(profiles) > 1:
            raise BotError("Too Many Users", "Race numbers pick races from one account at a time")

        profile = profiles[0]

        # The API shows a non-PB solo race only to its racer.
        if profile["userId"] != ctx.user["userId"] and not ctx.user["isAdmin"]:
            raise BotError("Privacy Error", "You may only compare specific races on your own account")

        numbers = list(dict.fromkeys(ctx.flags.numbers))[:max_users]

        if ctx.flags.quote_id:
            quote = await self.get_quote(ctx, ctx.flags.quote_id)
            picks = await pick_attempts(profile, quote["quoteId"], numbers)
        else:
            race_numbers = [number if number > 0 else await self.get_race_number(profile, number) for number in numbers]
            races = [get_race_db(profile["userId"], number) for number in race_numbers]
            if len({race["quoteId"] for race in races}) > 1:
                raise BotError(
                    "Different Quotes",
                    "Those races are on different quotes.\nPass a quote ID to pick by attempt number instead."
                )
            quote = await self.get_quote(ctx, races[0]["quoteId"])
            picks = [(f"Race #{race["raceNumber"]:,}", race) for race in races]

        enforce_daily_quote(ctx, quote["quoteId"])

        # Two numbers can name the same race, like 0 and the latest race number.
        picks = list({race["raceNumber"]: (label, race) for label, race in picks}.values())

        if len(picks) == 1:
            label, race = picks[0]
            quote_races = await get_races(profile["userId"], quote_id=quote["quoteId"], flags=ctx.flags)
            if not quote_races:
                raise NoQuoteRaces(profile["username"])
            best_race = max(quote_races, key=lambda quote_race: quote_race["wpm"])
            if best_race["raceNumber"] == race["raceNumber"]:
                raise BotError(
                    "Same Race",
                    f"{label} is the best race on this quote.\nPass a second number to compare it with."
                )
            picks.insert(0, ("Best", best_race))

        title = f"Race Comparison - {quote['quoteId']}"
        await compare_own_races(ctx, quote, profile, picks, title)


async def pick_attempts(profile: Profile, quote_id: str, numbers: list[int]) -> list[tuple[str, dict]]:
    """Return the races behind attempt numbers on a quote, counting back from the latest when not positive."""
    races = await get_races(profile["userId"], quote_id=quote_id, flags=Flags(status="any"))
    # A race with no number has no replay, so the site's history skips it.
    attempts = [race for race in races if race["raceNumber"] is not None]
    if not attempts:
        raise NoQuoteRaces(profile["username"])

    picks = []
    for number in numbers:
        attempt = number if number > 0 else len(attempts) + number
        if not 1 <= attempt <= len(attempts):
            raise BotError(
                "Attempt Not Found",
                f"{profile["username"]} has {len(attempts):,} attempts on this quote"
            )
        picks.append((f"Attempt #{attempt:,}", attempts[attempt - 1]))

    return picks


async def run(ctx: BotContext, quote: dict, profiles: list[Profile]) -> None:
    """Compare quote bests across multiple users."""
    description = quote_display(quote, 1000, display_status=True) + "\n"
    themed_line = 0

    # Fetch all best races in parallel
    async def fetch_user_best(profile: Profile) -> tuple[Profile, dict]:
        """Return the profile paired with its best race on the quote."""
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
        return profile, best_race

    bests = await asyncio.gather(*[fetch_user_best(p) for p in profiles])
    bests = sorted(bests, key=lambda best: -best[1]["wpm"])

    # Build description and find themed line
    for i, (profile, best_race) in enumerate(bests):
        if profile["userId"] == ctx.user["userId"]:
            themed_line = i
        description += format_race(profile, best_race)

    title = f"Quote Best Comparison - {quote['quoteId']}"
    page = create_comparison_page(
        title=title,
        description=description,
        race_data=[best_race for _, best_race in bests],
        theme=ctx.user["theme"],
        themed_line=themed_line,
    )

    message = Message(ctx, page=page)
    await message.send()


async def run_self(ctx: BotContext, quote: dict, profile: Profile) -> None:
    """Compare a user's best and recent races on the same quote."""
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

    recent_race = quote_races[-1]
    sorted_by_wpm = sorted(quote_races, key=lambda x: x["wpm"])
    best_race = sorted_by_wpm[-1]

    # New PB
    if recent_race["raceId"] == best_race["raceId"]:
        picks = [("New Best", recent_race), ("Previous Best", sorted_by_wpm[-2])]

    # Not a PB
    else:
        picks = [("Best", best_race), ("Recent", recent_race)]

    title = f"Quote Best Comparison - {quote['quoteId']}"
    await compare_own_races(ctx, quote, profile, picks, title)


async def compare_own_races(
    ctx: BotContext,
    quote: dict,
    profile: Profile,
    picks: list[tuple[str, dict]],
    title: str,
) -> None:
    """Overlay one user's labelled races on a quote and send the page."""
    description = quote_display(quote, 1000, display_status=True) + "\n"

    # Fetch keystroke data in parallel
    races = await asyncio.gather(*[
        get_race_keystrokes(profile["userId"], race["raceNumber"], ctx.flags.raw)
        for _, race in picks
    ])

    race_data = []
    for (label, _), race in zip(picks, races, strict=True):
        description += format_race(profile, race, label)
        race_data.append(race | {"username": label})

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


def format_race(profile: Profile, race: dict, label: str = None) -> str:
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
    theme: Theme,
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
