import io
import json

from discord import File
from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command, enforce_daily_quote, take_race_universe
from config import DAILY_QUOTE_CHANNEL_ID
from context import BotContext
from database.bot.recent_quotes import set_recent_quote
from database.typegg.races import get_race
from database.typegg.users import get_quote_bests
from utils.dates import discord_date
from utils.errors import BotError, NoQuoteRaces
from utils.messages import usable_in
from utils.schemas import Profile
from utils.strings import format_duration
from utils.urls import race_url

# Discord rejects a message longer than this.
MESSAGE_LIMIT = 2000

info = CommandInfo(
    name="keystrokelog",
    aliases=["kl"],
    description="Displays the raw keystroke log for one of your races, ready to copy.\n"
                "Pass a quote ID to show your best race on that quote.\n"
                "A log too long for one message is attached as a file.",
    parameters="[race_number/quote_id:latest]",
    examples=[
        "-kl",
        "-kl 1500",
        "-kl piykyai_3408",
    ],
)


class KeystrokeLog(Command):
    """Show the raw keystroke log for one of the caller's races."""

    supported_flags = {"number", "quote_id", "language"}

    @commands.command(aliases=info.aliases)
    @usable_in(DAILY_QUOTE_CHANNEL_ID)
    async def keystrokelog(self, ctx: BotContext, *args: str):
        """Show the log for the race number given, or the caller's best race on a quote."""
        ctx.flags.status = None
        profile = await self.get_profile(ctx, args[0] if args else None)
        universe = take_race_universe(ctx)

        # The API returns raw keystrokes only to the racer.
        if profile["userId"] != ctx.user["userId"] and not ctx.user["isAdmin"]:
            raise BotError("Privacy Error", "You may only view keystroke logs for your own account")

        if ctx.flags.number is not None or ctx.flags.quote_id is None:
            race_number = await self.get_race_number(profile, ctx.flags.number, universe)
        else:
            quote = await self.get_quote(ctx, ctx.flags.quote_id, profile["userId"])
            quote_bests = get_quote_bests(profile["userId"], quote_id=quote["quoteId"], flags=ctx.flags)
            if not quote_bests:
                raise NoQuoteRaces(profile["username"])
            race_number = quote_bests[0]["raceNumber"]

        await run(ctx, profile, race_number)


def log_block(header: str, log: str) -> str | None:
    """Return the header with the log in a code block, or None if one message cannot hold it."""
    if "```" in log:
        return None

    content = f"{header}\n```json\n{log}\n```"
    if len(content) > MESSAGE_LIMIT:
        return None

    return content


async def run(ctx: BotContext, profile: Profile, race_number: int) -> None:
    """Send one race's stats and its keystroke log, as a code block or an attached file."""
    race = get_race(profile["userId"], race_number, get_keystrokes=True)
    set_recent_quote(ctx.channel.id, race["quoteId"])

    enforce_daily_quote(ctx, race["quoteId"])

    if race["keystrokeData"] is None:
        raise BotError("No Keystroke Data", f"Race `#{race_number:,}` has no keystroke log")

    header = (
        f"**Keystroke Log - Race #{race_number:,}**\n"
        # The angle brackets stop Discord from unfurling a link preview under the log.
        f"Completed {discord_date(race["timestamp"])} on [{race["quoteId"]}](<{race_url(race["quoteId"])}>)\n"
        f"**Score:** {race["pp"]:,.2f} pp | **Speed:** {race["wpm"]:,.2f} WPM | "
        f"**Accuracy:** {race["accuracy"]:.2%} | "
        f"**Time:** {format_duration(race["duration"] / 1000, round_seconds=False)}"
    )
    log = json.dumps(race["keystrokeData"], ensure_ascii=False, separators=(",", ":"))
    content = log_block(header, log)

    if content is not None:
        await ctx.send(content)
        return

    file_name = f"{profile["username"]}_{race_number}.json"
    await ctx.send(header, file=File(io.BytesIO(log.encode("utf-8")), filename=file_name))
