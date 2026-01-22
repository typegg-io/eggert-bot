from discord.ext import commands

from commands.base import Command
from commands.checks import is_bot_owner
from tasks import daily_quote_results, daily_quote_ping, import_daily_quotes
from utils.messages import Page, Message

info = {
    "name": "rundaily",
    "aliases": [],
    "description": "Manually triggers the daily quote messages",
    "parameters": "",
}


class RunDaily(Command):
    @commands.command(aliases=info["aliases"])
    @is_bot_owner()
    async def rundaily(self, ctx: commands.Context):
        status = []

        try:
            await daily_quote_results(self.bot)
            status.append(":white_check_mark: Daily quote results sent")
        except Exception as e:
            status.append(f":x: Daily quote results failed: {e}")

        try:
            await daily_quote_ping(self.bot)
            status.append(":white_check_mark: Daily quote ping sent")
        except Exception as e:
            status.append(f":x: Daily quote ping failed: {e}")

        try:
            await import_daily_quotes()
            status.append(":white_check_mark: Daily quotes imported")
        except Exception as e:
            status.append(f":x: Daily quotes import failed: {e}")

        message = Message(
            ctx,
            Page(
                title="Daily Tasks",
                description="\n".join(status)
            )
        )

        await message.send()
