from discord.ext import commands

from config import EIKO, KEEGAN, DISCORD_UUID
from utils.errors import UserNotAdmin, UserNotOwner


def is_bot_admin():
    async def predicate(ctx: commands.Context):
        if ctx.user["isAdmin"]:
            return True
        raise UserNotAdmin

    return commands.check(predicate)


def is_bot_owner():
    async def predicate(ctx: commands.Context):
        if ctx.author.id in [EIKO, KEEGAN, DISCORD_UUID]:
            return True
        raise UserNotOwner

    return commands.check(predicate)
