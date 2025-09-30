from dataclasses import dataclass

from discord import Embed
from discord.ext.commands import CommandError, CheckFailure

from config import BOT_PREFIX as prefix
from utils.colors import ERROR


def missing_arguments(info, show_tip=False):
    embed = Embed(
        title="Missing Parameter",
        description="One or more parameters is missing\n"
                    f"Usage: `{prefix}{info["name"]} {info["parameters"]}`",
        color=ERROR,
    )
    if show_tip:
        embed.set_footer(text=f"Run {prefix}link to avoid typing your username!")

    return embed


def invalid_argument(options):
    return Embed(
        title="Invalid Parameter",
        description=f"Parameter can be: " + ",".join([f"`{option}`" for option in options]),
        color=ERROR,
    )


def same_username():
    return Embed(
        title="Same Username",
        description="You must provide two unique usernames to compare",
        color=ERROR,
    )


def unknown_command():
    return Embed(
        title="Command Not Found",
        description=f"`{prefix}help` for a list of commands",
        color=ERROR,
    )


def invalid_number():
    return Embed(
        title="Invalid Number",
        description="Number provided is invalid",
        color=ERROR,
    )


def unexpected_error():
    return Embed(
        title="Unexpected Error",
        description="An unexpected error occurred",
        color=ERROR,
    )


def invalid_category(categories):
    return Embed(
        title="Invalid Category",
        description=f"Category can be: {", ".join("`" + c + "`" for c in categories)}",
        color=ERROR,
    )


def invalid_metric(metric):
    return Embed(
        title="Invalid Metric",
        description=f"'{metric}' is not a valid metric. Please use 'pp' or 'wpm'.",
        color=ERROR,
    )


def invalid_user(user_arg):
    return Embed(
        title="Invalid User",
        description=f"User `{user_arg.replace("`", "")}` not found",
        color=ERROR,
    )


def api_error(message):
    return Embed(
        title="API Error",
        description=f"Error from API: {message}",
        color=ERROR,
    )


def no_races(username):
    return Embed(
        title="No Races",
        description=f"User `{username}` has no races",
        color=ERROR,
    )


def banned_user():
    return Embed(
        title="You Are Banned",
        description="You are banned from using commands",
        color=ERROR,
    )


def admin_command():
    return Embed(
        title="Admin Command",
        description="You lack the permissions to use this command",
        color=ERROR,
    )


def owner_command():
    return Embed(
        title="Owner Command",
        description="You lack the permissions to use this command",
        color=ERROR,
    )


def import_required(username):
    return Embed(
        title="Import Required",
        description=f"Must `{prefix}import {username.replace("`", "")}`"
    )


def no_common_texts():
    return Embed(
        title="No Common Texts",
        description="Users do not have any texts in common",
        color=ERROR,
    )


def user_not_found(discord_id):
    return Embed(
        title="User Not Found",
        description=f"<@{discord_id}> has never used the bot",
        color=ERROR,
    )


def unknown_quote(quote_id: str):
    return Embed(
        title="Unknown Quote",
        description=f"Quote `{quote_id.replace("`", "")}` not found",
        color=ERROR,
    )


def invalid_date():
    return Embed(
        title="Invalid Date",
        description="Unrecognized date format",
        color=ERROR,
    )


@dataclass
class ErrorWithUsername(CommandError):
    """General exception for errors with a username."""
    username: str


class ProfileNotFound(ErrorWithUsername):
    """Raised when a TypeGG profile is not found."""

    @property
    def embed(self):
        return invalid_user(self.username)


class NoRaces(ErrorWithUsername):
    """Raised when a TypeGG profile has no races."""

    @property
    def embed(self):
        return no_races(self.username)


class MissingUsername(CommandError):
    """Raised when a username is missing from required arguments."""


class UserBanned(CheckFailure):
    """Raised when a banned user attempts to run a command."""
    embed = banned_user()


class UserNotAdmin(CheckFailure):
    """Raised when a non-admin user attempts to run an admin-only command."""
    embed = admin_command()


class UserNotOwner(CheckFailure):
    """Raised when a non-owner attempts to run an owner-only command."""
    embed = owner_command()


class InvalidDate(CommandError):
    """Raised when a date string is improperly formatted."""
    embed = invalid_date()
