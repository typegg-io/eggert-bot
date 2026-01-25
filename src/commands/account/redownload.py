from typing import Optional

from discord.ext import commands

from commands.account.download import run as download
from commands.base import Command
from database.typegg.keystroke_data import delete_keystroke_data
from database.typegg.races import get_latest_race, delete_races
from utils.colors import ERROR, WARNING
from utils.logging import ADMIN_ALIASES
from utils.messages import Page, Message
from utils.strings import escape_formatting

info = {
    "name": "redownload",
    "aliases": ["reimport", "ri"],
    "description": (
        "Re-import your own complete race history.\n"
        "Has a cooldown of 10 minutes."
    ),
}


class ReDownload(Command):
    @commands.cooldown(1, 600, commands.BucketType.user)
    @commands.command(aliases=info["aliases"])
    async def redownload(self, ctx, username: Optional[str] = "me"):
        try:
            is_admin = ctx.author.id in ADMIN_ALIASES.keys()
            profile = await self.get_profile(ctx, username, races_required=True)
            user_id = profile["userId"]

            if not is_admin and user_id != ctx.user["userId"]:
                ctx.command.reset_cooldown(ctx)
                message = Message(ctx, Page(
                    title="User Limit",
                    description="You can only re-import your own races",
                    color=ERROR,
                ))
                return await message.send()

            latest_race = get_latest_race(user_id)
            if not latest_race:
                ctx.command.reset_cooldown(ctx)
                message = Message(ctx, Page(
                    title="Not Imported",
                    description="Your account is not yet imported",
                    color=ERROR,
                ))
                return await message.send()

            message = Message(ctx, Page(
                title="Are You Sure?",
                description=f"Please type \"confirm\" to proceed with the re-import",
                color=WARNING,
            ))
            await message.send()

            if not await self.await_confirmation(ctx):
                return

            delete_races(user_id)
            delete_keystroke_data(user_id)

            message = Message(ctx, Page(
                title="Races Deleted",
                description=f"Deleted all races for {escape_formatting(profile["username"])}"
            ))
            await message.send()

            ctx.invoked_with = "download"
            await download(ctx, profile)

            if is_admin:
                ctx.command.reset_cooldown(ctx)
        except Exception as e:
            ctx.command.reset_cooldown(ctx)
            raise e
