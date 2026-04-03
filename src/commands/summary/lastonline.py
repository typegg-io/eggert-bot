from typing import Optional

from discord.ext import commands

from commands.base import Command
from utils.dates import parse_date, now
from utils.messages import Page, Message
from utils.strings import discord_date, format_duration

info = {
    "name": "lastonline",
    "aliases": ["lo"],
    "description": "Displays when a user last completed a race.",
    "parameters": "[username]",
    "examples": [
        "-lo",
        "-lo eiko",
    ],
}


class LastOnline(Command):
    @commands.command(aliases=info["aliases"])
    async def lastonline(self, ctx, username: Optional[str] = "me"):
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
