"""The command context type, kept in a leaf module so importing it costs nothing."""

from discord.ext import commands

from utils.flags import Flags


class BotContext(commands.Context):
    """A command context carrying the extra fields `Eggert.get_context` populates."""

    flags: Flags
    explicit_flags: dict[str, str]
    user: dict
    raw_args: tuple
