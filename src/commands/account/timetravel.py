from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from config import BOT_PREFIX
from context import BotContext
from database.bot.users import update_date_range
from utils.errors import BotError
from utils.messages import Message, Page

info = CommandInfo(
    name="timetravel",
    aliases=["tt"],
    description="Applies a date range to every command that shows stats over time.\n"
                "Run it with no arguments to see the current range, or `off` to clear it.",
    parameters="[start date] [end date]",
    examples=[
        "-timetravel",
        "-timetravel 9/1/2025 9/1/2026",
        "-timetravel year",
        "-timetravel off",
    ],
)


class TimeTravel(Command):
    """Set, report or clear the date range applied across a user's commands."""

    supported_flags = {"date_range"}

    @commands.command(aliases=info.aliases)
    async def timetravel(self, ctx: BotContext, *args: str):
        """Store the range the flags resolved to, or report and clear it."""
        typed = "date_range" in ctx.explicit_flags
        # A typed range resolving to nothing is the alltime keyword, which clears rather than sets.
        if (args and args[0].lower() in ["off", "clear", "reset"]) or (typed and not ctx.flags.date_range):
            update_date_range(ctx.author.id, None, None)
            ctx.flags.date_range = None
            await send(ctx, "Time Travel Off", "Commands show all-time stats again.")
            return

        if not typed:
            await report(ctx)
            return

        start, end = ctx.flags.date_range
        update_date_range(ctx.author.id, start.timestamp(), end.timestamp())
        await send(ctx, "Time Travel On", "Commands now cover this range only.")


async def report(ctx: BotContext) -> None:
    """Send the range currently stored on the account."""
    if not ctx.flags.date_range:
        raise BotError(
            "No Range Set",
            f"Run `{BOT_PREFIX}timetravel 9/1/2025 9/1/2026` to set one.",
        )

    await send(ctx, "Time Travel On", "Commands cover this range only.")


async def send(ctx: BotContext, title: str, description: str) -> None:
    """Send the command's confirmation page."""
    await Message(ctx, page=Page(title=title, description=description)).send()
