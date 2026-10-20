from discord import Embed
from discord.ext import commands

from bot_setup import Eggert
from command_info import CommandInfo
from commands.base import Command
from config import BOT_PREFIX, TYPEGG_GUILD_ID
from context import BotContext
from database.bot.users import unlink_user, update_gg_plus_status, update_theme
from utils.colors import DEFAULT_THEME, ERROR, WARNING
from utils.logging import log
from web_server.utils import remove_user_roles

info = CommandInfo(
    name="unlink",
    aliases=["unverify"],
    description="Removes the link between your Discord and TypeGG accounts.",
    examples=["-unlink"],
)


class Unlink(Command):
    """Remove the link between a Discord account and a TypeGG account."""

    ignore_flags = True

    @commands.command(aliases=info.aliases)
    async def unlink(self, ctx: BotContext):
        """Confirm with the caller, then drop the link and its Discord roles."""
        if not ctx.user["userId"]:
            return await ctx.send(embed=not_verified())

        sent = await ctx.send(embed=Embed(
            title="Are You Sure?",
            description=(
                "You are about to remove the verification link\n"
                "between your Discord and TypeGG account.\n"
                "Please type \"confirm\" to proceed."
            ),
            color=WARNING,
        ))

        if not await self.await_confirmation(ctx, prompt_message=sent):
            return

        await unverify_user(self.bot, ctx.author.id)

        # Reset GG+ status and theme in database
        if ctx.user["userId"]:
            update_gg_plus_status(ctx.user["userId"], False)
            update_theme(ctx.author.id, DEFAULT_THEME)
            log(f"Reset GG+ status and theme for user {ctx.user['userId']}")

        unlink_user(ctx.author.id)

        return await ctx.send(embed=Embed(
            title="Verification Removed",
            description=f"To re-verify your account, run `{BOT_PREFIX}link`.\n",
            color=ctx.user["theme"]["embed"]
        ))


async def unverify_user(bot_instance: Eggert, discord_id: str) -> None:
    """Strip the verification roles a linked account earned in the TypeGG guild."""
    guild = bot_instance.get_guild(TYPEGG_GUILD_ID)
    if not guild:
        log(f"Guild with ID {TYPEGG_GUILD_ID} not found")
        return

    await remove_user_roles(guild, int(discord_id))


def not_verified() -> Embed:
    """Return the embed shown when the caller has no link to remove."""
    return Embed(
        title="Not Verified",
        description="Your account has not yet been verified.",
        color=ERROR
    )
