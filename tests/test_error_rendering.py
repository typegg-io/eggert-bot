"""Tests for error embeds that the global handler builds from a command's CommandInfo."""

import asyncio
from types import SimpleNamespace

import pytest
from discord.ext import commands
from discord.ext.commands.view import StringView

from bot_setup import normalize_apostrophes
from command_info import CommandInfo
from utils.errors import BotError, MissingArguments, UnmatchedQuote
from utils.flags import Flags
from utils.messages import Message


def test_missing_arguments_renders_for_every_command(command_modules):
    """on_command_error builds this for any command, including those declaring no parameters.

    An error here is raised inside the handler itself, so the user gets no reply at all.
    """
    failed = []
    for group, file, module in command_modules:
        try:
            MissingArguments().usage_embed(module.info, show_tip=True)
        except Exception as error:
            failed.append(f"{group}/{file}: {type(error).__name__}: {error}")
    assert failed == []


def test_usage_line_has_no_trailing_space_without_parameters():
    """A command with no parameters still renders a clean usage line."""
    embed = MissingArguments().usage_embed(CommandInfo(name="ping", aliases=[], description=""))
    assert "`-ping`" in embed.description


def test_empty_pages_raise_a_bot_error():
    """A command whose filters match nothing gets an embed, not an IndexError."""

    async def build_with_no_pages() -> None:
        """Build a message holding no pages, inside a running loop."""
        ctx = SimpleNamespace(
            flags=Flags(),
            user={"theme": {"embed": 0}, "timezone": "UTC"},
            author=SimpleNamespace(id=1),
        )
        message = Message(ctx, pages=[])

        with pytest.raises(BotError):
            message.build_embeds()

    asyncio.run(build_with_no_pages())


def test_usage_line_includes_parameters_when_present():
    """The parameter string is appended when the command declares one."""
    embed = MissingArguments().usage_embed(
        CommandInfo(name="stats", aliases=[], description="", parameters="[username]")
    )
    assert "`-stats [username]`" in embed.description


@pytest.mark.parametrize("error_type", [
    commands.ExpectedClosingQuoteError,
    commands.UnexpectedQuoteError,
    commands.InvalidEndOfQuotedStringError,
])
def test_a_quote_error_reaches_the_unmatched_quote_branch(error_type):
    """Every quote failure discord.py raises renders one embed, not an Unexpected Error."""
    assert issubclass(error_type, commands.ArgumentParsingError)
    assert UnmatchedQuote().embed.title == "Unmatched Quote"


def test_an_apostrophe_parses_as_plain_text():
    """A word carrying an apostrophe is an argument, not an unclosed quote."""
    view = StringView(normalize_apostrophes("-su I’d"))
    view.get_word()
    view.skip_ws()
    assert view.get_quoted_word() == "I'd"
