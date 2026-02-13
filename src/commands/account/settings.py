import re
import zoneinfo
from datetime import timedelta, timezone

from discord.ext import commands

from commands.base import Command
from database.bot.users import update_timezone
# from database.bot.users import update_timezone
from utils.errors import GeneralException
from utils.messages import Page, Message
from utils.strings import get_argument

settings = {"timezone"}
info = {
    "name": "settings",
    "aliases": ["set"],
    "description": "Change your personal bot settings\n\n"
                   "Available settings:\n"
                   "\\- `timezone` (IANA format, default UTC)",
    "parameters": "<setting> <value>",
}


class Settings(Command):
    @commands.command(aliases=info["aliases"])
    async def settings(self, ctx, setting: str, value: str):
        setting = get_argument(settings, setting)

        if setting == "timezone":
            try:
                timezone = resolve_timezone(value)
            except zoneinfo.ZoneInfoNotFoundError:
                raise GeneralException(
                    "Invalid Timezone",
                    "Use [IANA format](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List) (`America/New_York`)"
                )

            display_value = str(timezone)
            update_timezone(ctx.author.id, display_value)

        message = Message(ctx=ctx, page=Page(
            title="Settings Updated",
            description=f"`{setting}` has been set to `{display_value}`"
        ))

        await message.send()


def resolve_timezone(value: str):
    value = value.strip()

    # IANA
    value_lower = value.lower()
    for tz in zoneinfo.available_timezones():
        if tz.lower() == value_lower:
            return zoneinfo.ZoneInfo(tz)

    raise zoneinfo.ZoneInfoNotFoundError(value)
