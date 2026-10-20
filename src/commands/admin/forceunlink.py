from discord.ext import commands

from command_info import CommandInfo
from commands.account.unlink import unverify_user
from commands.base import Command
from commands.checks import is_bot_admin
from context import BotContext
from database.bot.users import get_user_by_user_id, unlink_user, update_gg_plus_status, update_theme
from utils.colors import DEFAULT_THEME, ERROR, SUCCESS
from utils.errors import ProfileNotFound
from utils.logging import log
from utils.messages import Message, Page

info = CommandInfo(
    name="forceunlink",
    aliases=[],
    description="Force unlink a TypeGG account from its Discord user",
    parameters="<typegg_username>",
)


class ForceUnlink(Command):
    """Remove a TypeGG account's link without access to the linked Discord account."""

    ignore_flags = True

    @commands.command(aliases=info.aliases)
    @is_bot_admin()
    async def forceunlink(self, ctx: BotContext, username: str):
        """Find the Discord user linked to the account, then drop the link and its roles."""
        try:
            profile = await self.get_profile(ctx, username, races_required=False, auto_import=False)
            user_id = profile["userId"]
        except ProfileNotFound:
            user_id = username

        linked = get_user_by_user_id(user_id)
        if not linked:
            return await Message(ctx, Page(
                title="Not Linked",
                description=f"TypeGG user `{user_id}` is not linked to a Discord account",
                color=ERROR,
            )).send()

        discord_id = linked["discordId"]
        log(f"Admin {ctx.author.name} force-unlinking TypeGG user {user_id} from Discord user {discord_id}")

        await unverify_user(self.bot, discord_id)
        update_gg_plus_status(user_id, False)
        update_theme(discord_id, DEFAULT_THEME)
        unlink_user(discord_id)

        await Message(ctx, Page(
            title="Force Unlink Successful",
            description=f"Unlinked TypeGG user `{user_id}` from <@{discord_id}> (`{discord_id}`)",
            color=SUCCESS,
        )).send()
