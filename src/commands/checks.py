"""Command checks that gate a command on the invoking user's role."""

from collections.abc import Callable

from discord.ext import commands

from config import EIKO, KEEGAN, STAGING
from context import BotContext
from utils.errors import UserNotAdmin, UserNotOwner


def is_bot_admin() -> Callable:
    """Return a check that passes only for bot admins."""

    async def predicate(ctx: BotContext) -> bool:
        """Raise unless the invoking user is a bot admin."""
        if ctx.user["isAdmin"] or STAGING:
            return True
        raise UserNotAdmin

    return commands.check(predicate)


def is_bot_owner() -> Callable:
    """Return a check that passes only for the bot owners."""

    async def predicate(ctx: BotContext) -> bool:
        """Raise unless the invoking user is a bot owner."""
        if ctx.author.id in [EIKO, KEEGAN] or STAGING:
            return True
        raise UserNotOwner

    return commands.check(predicate)
