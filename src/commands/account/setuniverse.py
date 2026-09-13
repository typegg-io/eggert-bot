from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from config import DEFAULT_UNIVERSE, UNIVERSE_CODES
from context import BotContext
from database.bot.users import update_universe
from utils.errors import BotError
from utils.flags import LANGUAGES, Language
from utils.messages import Message, Page

info = CommandInfo(
    name="setuniverse",
    aliases=["universe", "su"],
    description="Applies a universe to every command that can show stats for one.\n"
                "Run it with no language to return to English.",
    parameters="[language]",
    examples=[
        "-setuniverse fr",
        "-setuniverse French",
        "-setuniverse",
    ],
)


class SetUniverse(Command):
    """Set or clear the universe applied across a user's commands."""

    supported_flags = {"language"}
    quiet_settings = True

    @commands.command(aliases=info.aliases)
    async def setuniverse(self, ctx: BotContext, language: str = None):
        """Store the universe the flag or name resolved to, or return the user to English."""
        # set_user has already merged the stored universe in, so only a typed flag counts here.
        code = ctx.flags.language.code if "language" in ctx.explicit_flags else resolve_name(language)

        if code is None or code == DEFAULT_UNIVERSE:
            update_universe(ctx.author.id, DEFAULT_UNIVERSE)
            ctx.flags.language = None
            title = "Back to English"
            description = "Commands run in the English universe again."
        else:
            if code not in UNIVERSE_CODES:
                raise universe_error(Language(code).name)
            update_universe(ctx.author.id, code)
            ctx.flags.language = Language(code)
            title = f"{Language(code).name} Universe"
            description = "Commands now cover this universe only."

        await Message(ctx, page=Page(title=title, description=description)).send()


def resolve_name(language: str | None) -> str | None:
    """Return the code for a language name, or None when nothing was given."""
    if not language:
        return None

    for code, name in LANGUAGES.items():
        if name.lower() == language.lower():
            return code

    raise universe_error(language)


def universe_error(language: str) -> BotError:
    """Return the error naming every universe a user can choose."""
    universes = ", ".join(f"`{code}` {LANGUAGES[code]}" for code in UNIVERSE_CODES)
    return BotError(
        "Invalid Universe",
        f"{language} has no universe of its own.\nChoose one of: {universes}",
    )
