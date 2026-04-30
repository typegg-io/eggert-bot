from discord.ext import commands

from bot_setup import BotContext
from config import EIKO, KEEGAN, STAGING
from utils.errors import UserNotAdmin, UserNotOwner


def is_bot_admin():
    async def predicate(ctx: BotContext):
        if ctx.user["isAdmin"] or STAGING:
            return True
        raise UserNotAdmin

    return commands.check(predicate)


def is_bot_owner():
    async def predicate(ctx: BotContext):
        if ctx.author.id in [EIKO, KEEGAN] or STAGING:
            return True
        raise UserNotOwner

    return commands.check(predicate)
