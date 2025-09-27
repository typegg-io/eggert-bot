from discord.ext import commands

from config import EIKO, KEEGAN
from utils.errors import UserNotAdmin, UserNotOwner


def is_bot_admin():
    async def predicate(ctx: commands.Context):
        if ctx.user["isAdmin"]:
            return True
        raise UserNotAdmin("Non admin user attempted to use an admin command")

    return commands.check(predicate)


def is_bot_owner():
    async def predicate(ctx: commands.Context):
        if ctx.author.id in [EIKO, KEEGAN]:
            return True
        raise UserNotOwner("Non owner attempted to use an owner command")

    return commands.check(predicate)
