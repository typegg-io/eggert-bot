from discord.ext import commands
from typing import Optional

from commands.base import Command
from utils.dates import parse_date, now
from utils.messages import Page, Message, Field
from utils.strings import discord_date, format_duration

info = {
    "name": "lastonline",
    "aliases": ["lo"],
    "description": "Displays when a user last completed a race",
    "parameters": "[username]",
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
                f"{format_duration(duration)}\n"
                f"{discord_date(last_online, "f")}"
            ),
        )

        message = Message(
            ctx,
            page=page,
            profile=profile,
        )

        await message.send()