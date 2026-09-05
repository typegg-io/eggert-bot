from discord import Embed, Forbidden
from discord.ext import commands

from api.verification import DASHBOARD_MINUTES, generate_dashboard_link
from command_info import CommandInfo
from commands.base import Command
from commands.checks import is_bot_admin
from context import BotContext
from utils.colors import ERROR
from utils.logging import log

info = CommandInfo(
    name="dashboard",
    aliases=["dash"],
    description="DMs a one-time link to the usage dashboard.",
    examples=["-dashboard"],
)


class Dashboard(Command):
    """Send a bot admin a single-use link to the usage dashboard."""

    ignore_flags = True

    @commands.command(aliases=info.aliases)
    @is_bot_admin()
    async def dashboard(self, ctx: BotContext):
        """DM the caller a single-use dashboard link."""
        log(f"Admin {ctx.author.name} requested a dashboard link")

        embed = Embed(
            title="Usage Dashboard",
            description=f"Open the dashboard [**here**]({generate_dashboard_link(str(ctx.author.id))}).\n"
                        f"The link works once and expires in {DASHBOARD_MINUTES} minutes.\n"
                        f"Your browser stays signed in for 30 days.",
            color=ctx.user["theme"]["embed"],
        )

        try:
            await ctx.author.send(embed=embed)
        except Forbidden:
            await ctx.send(embed=dms_disabled())


def dms_disabled() -> Embed:
    """Return the embed shown when the dashboard DM cannot be delivered."""
    return Embed(
        title="Message Failed",
        description="Failed to send a direct message. Please enable\n"
                    "direct messages to receive the dashboard link.",
        color=ERROR,
    )
