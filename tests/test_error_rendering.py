"""Tests for error embeds that the global handler builds from a command's CommandInfo."""

from command_info import CommandInfo
from utils.errors import MissingArguments


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


def test_usage_line_includes_parameters_when_present():
    """The parameter string is appended when the command declares one."""
    embed = MissingArguments().usage_embed(
        CommandInfo(name="stats", aliases=[], description="", parameters="[username]")
    )
    assert "`-stats [username]`" in embed.description
