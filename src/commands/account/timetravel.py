from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from database.bot.users import update_date_range
from utils.messages import Message, Page

info = CommandInfo(
    name="timetravel",
    aliases=["tt"],
    description="Applies a date range to every command that shows stats over time.\n"
                "Run it with no dates to return to the present.",
    parameters="[dates]",
    examples=[
        "-timetravel 9/1/2025 9/1/2026",
        "-timetravel year",
        "-timetravel",
    ],
)


class TimeTravel(Command):
    """Set or clear the date range applied across a user's commands."""

    supported_flags = {"date_range"}
    quiet_settings = True

    @commands.command(aliases=info.aliases)
    async def timetravel(self, ctx: BotContext):
        """Store the range the flags resolved to, or return the user to the present."""
        date_range = ctx.flags.date_range if "date_range" in ctx.explicit_flags else None

        if not date_range:
            update_date_range(ctx.author.id, None, None)
            ctx.flags.date_range = None
            title, description = "Back to the Present", "Commands show all-time stats again."
        else:
            start, end = date_range
            update_date_range(ctx.author.id, start.timestamp(), end.timestamp())
            title, description = "Time Travel On", "Commands now cover this range only."

        await Message(ctx, page=Page(title=title, description=description)).send()
