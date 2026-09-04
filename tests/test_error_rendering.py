"""Tests for error embeds that the global handler builds from a command's info dict."""

from utils.errors import MissingArguments


def test_missing_arguments_renders_for_every_command(command_modules):
    """on_command_error builds this for any command, including those with no parameters key.

    A KeyError here is raised inside the handler itself, so the user gets no reply at all.
    """
    failed = []
    for group, file, module in command_modules:
        try:
            MissingArguments().embed(module.info, show_tip=True)
        except Exception as error:
            failed.append(f"{group}/{file}: {type(error).__name__}: {error}")
    assert failed == []


def test_usage_line_has_no_trailing_space_without_parameters():
    """A command with no parameters still renders a clean usage line."""
    embed = MissingArguments().embed({"name": "ping"})
    assert "`-ping`" in embed.description


def test_usage_line_includes_parameters_when_present():
    """The parameter string is appended when the command declares one."""
    embed = MissingArguments().embed({"name": "stats", "parameters": "[username]"})
    assert "`-stats [username]`" in embed.description
