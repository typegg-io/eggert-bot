import time

import aiohttp
from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.checks import is_bot_admin
from context import BotContext
from services.uptime import Alert, format_duration
from uptime import MONITOR, post
from utils.messages import Message, Page
from utils.strings import parse_duration

info = CommandInfo(
    name="uptime",
    aliases=[],
    description="Shows the uptime watcher, or mutes it for planned downtime",
    parameters="[mute <duration> | unmute]",
)


class Uptime(Command):
    """Show the uptime watcher's state, or mute and unmute its alerts."""

    ignore_flags = True

    @commands.command(aliases=info.aliases)
    @is_bot_admin()
    async def uptime(self, ctx: BotContext, action: str = None, duration: str = None):
        """Report the watcher's state, or mute or unmute it."""
        now = time.time()

        if action == "mute":
            seconds = parse_duration(duration or "")
            if not seconds:
                return await Message(ctx, Page(
                    title="Uptime",
                    description="Give a duration, such as `-uptime mute 30m`.",
                )).send()
            MONITOR.mute(now + seconds, by=ctx.author.display_name)
            until = f"<t:{int(now + seconds)}:t>"
            await self._announce(f"🔇 Uptime alerts muted by {ctx.author.display_name} until {until}.")
            page = Page(title="Uptime Muted", description=f"Alerts are muted until {until}.")
            return await Message(ctx, page).send()

        if action == "unmute":
            MONITOR.unmute()
            page = Page(title="Uptime Unmuted", description="Alerts resume on the next check.")
            return await Message(ctx, page).send()

        lines = []
        for name, state in MONITOR.states.items():
            if state.down_since is not None:
                lines.append(f"🔴 **{name}** down for {format_duration(now - state.down_since)}")
            else:
                lines.append(f"🟢 **{name}** up")
        if MONITOR.maintenance:
            lines.append("🛠️ Maintenance mode is on")
        if MONITOR.is_muted(now):
            lines.append(f"🔇 Muted by {MONITOR.muted_by} until <t:{int(MONITOR.muted_until)}:t>")

        await Message(ctx, Page(title="Uptime", description="\n".join(lines))).send()

    @staticmethod
    async def _announce(text: str) -> None:
        """Post a mute to the uptime channel, so everyone watching sees it."""
        async with aiohttp.ClientSession() as session:
            await post(session, Alert(text))
