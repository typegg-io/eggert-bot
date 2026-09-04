from discord.ext import commands

from commands.base import Command
from context import BotContext
from utils.dates import discord_date, now, parse_date
from utils.messages import Message, Page
from utils.strings import format_duration

info = {
    "name": "lastonline",
    "aliases": ["lo"],
    "description": "Displays when a user was last active on their account.",
    "parameters": "[username]",
    "examples": [
        "-lo",
        "-lo eiko",
    ],
}


class LastOnline(Command):
    @commands.command(aliases=info["aliases"])
    async def lastonline(self, ctx: BotContext, username: str = None):
        profile = await self.get_profile(ctx, username)
        last_online = parse_date(profile["lastSeen"]).timestamp()
        duration = now().timestamp() - last_online

        page = Page(
            title="Last Online",
            description=(
                f"{format_duration(duration)} ago\n"
                f"{discord_date(last_online, "f")}"
            ),
        )

        message = Message(
            ctx,
            page=page,
            profile=profile,
        )

        await message.send()
