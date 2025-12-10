from dataclasses import dataclass

from discord import Embed
from discord.ext.commands import CommandError, CheckFailure

from config import BOT_PREFIX as prefix
from utils.colors import WARNING, PLUS


class MissingArguments(CommandError):
    """Raised when one or more parameters are missing from command arguments."""

    def embed(self, info, show_tip=False):
        embed = Embed(
            title="Missing Argument",
            description=(
                "One or more arguments is missing\n"
                f"Usage: `{prefix}{info["name"]} {info["parameters"]}`"
            ),
        )
        if show_tip:
            embed.set_footer(text=f"Run {prefix}link to avoid typing your username!")

        return embed


class MissingUsername(CommandError):
    """Raised when a username is missing from required arguments."""


@dataclass
class InvalidArgument(CommandError):
    """Raised when a provided argument is invalid."""
    options: list[str]

    @property
    def embed(self):
        return Embed(
            title="Invalid Argument",
            description=f"Argument can be: " + ", ".join([f"`{option}`" for option in self.options]),
        )


@dataclass
class ErrorWithUsername(CommandError):
    """General exception for errors with a username."""
    username: str


class ProfileNotFound(ErrorWithUsername):
    """Raised when a TypeGG profile is not found."""

    @property
    def embed(self):
        return Embed(
            title="User Not Found",
            description=f"User `{self.username.replace("`", "")}` not found",
        )


class NoRaces(ErrorWithUsername):
    """Raised when a TypeGG profile has no races."""

    @property
    def embed(self):
        return Embed(
            title="No Races",
            description=f"User `{self.username.replace("`", "")}` has no races",
        )


class NoRankedRaces(ErrorWithUsername):
    """Raised when a TypeGG profile has no ranked races."""

    @property
    def embed(self):
        return Embed(
            title="No Ranked Races",
            description=f"User `{self.username.replace("`", "")}` has no ranked races",
        )


class NoRacesFiltered(ErrorWithUsername):
    """Raised when a TypeGG profile has no races with the current filters."""

    @property
    def embed(self):
        return Embed(
            title="No Filtered Races",
            description=f"User `{self.username.replace("`", "")}` has no races with these filters",
        )


class UserBanned(CheckFailure):
    """Raised when a banned user attempts to run a command."""
    embed = Embed(
        title="You Are Banned",
        description="You are banned from using commands",
    )


class UserNotAdmin(CheckFailure):
    """Raised when a non-admin user attempts to run an admin-only command."""
    embed = Embed(
        title="Admin Command",
        description="You lack the permissions to use this command",
    )


class UserNotOwner(CheckFailure):
    """Raised when a non-owner attempts to run an owner-only command."""
    embed = Embed(
        title="Owner Command",
        description="You lack the permissions to use this command",
    )


class SameUsername(CommandError):
    """Raised when two passed usernames are the same."""
    embed = Embed(
        title="Same Username",
        description="You must provide two unique usernames to compare",
    )


class UnknownCommand(CommandError):
    """Raised when an unknown command is referenced."""
    embed = Embed(
        title="Command Not Found",
        description=f"`{prefix}help` for a list of commands",
    )


@dataclass
class UnexpectedError(CommandError):
    """Global catch-all case for unexpected exceptions."""
    error_type: str

    @property
    def embed(self):
        return Embed(
            title="Unexpected Error",
            description=(
                "An unexpected error occurred:\n"
                f"`{self.error_type}`"
            ),
        )


class NoCommonTexts(CommandError):
    embed = Embed(
        title="No Common Texts",
        description="Users do not have any texts in common",
    )


@dataclass
class BotUserNotFound(CommandError):
    """Raised when a discord ID is not found within the bot's database."""
    discord_id: str

    @property
    def embed(self):
        return Embed(
            title="User Not Found",
            description=f"<@{self.discord_id}> has never used the bot",
        )


@dataclass
class UnknownQuote(CommandError):
    """Raised when a quote ID doesn't match any existing quote."""
    quote_id: str

    @property
    def embed(self):
        return Embed(
            title="Unknown Quote",
            description=f"Quote `{self.quote_id.replace("`", "")}` not found",
        )


class InvalidDate(CommandError):
    """Raised when a date string is improperly formatted."""
    embed = Embed(
        title="Invalid Date",
        description="Unrecognized date format",
    )


class DailyQuoteChannel(CommandError):
    """Raised when a non-daily command is sent in the daily quote channel."""
    embed = Embed(
        title="Daily Channel",
        description="Only daily commands can be used in this channel\n"
                    f"Use <#{1337196592905846864}> for other commands",
    )


@dataclass
class APIError(CommandError):
    status: int
    message: str

    @property
    def embed(self):
        return Embed(
            title="API Error",
            description=(
                f"API returned status {self.status}:\n"
                f"{self.message}"
            ),
        )


@dataclass
class RaceNotFound(CommandError):
    """Raised when a specific race is not found."""
    username: str
    race_number: int

    @property
    def embed(self):
        return Embed(
            title="Race Not Found",
            description=(
                f"Race `#{self.race_number:,}` for "
                f"`{self.username.replace("`", "")}` not found"
            ),
        )


class InvalidRange(CommandError):
    """Raised when a range string is improperly formatted."""
    embed = Embed(
        title="Invalid Range",
        description=(
            "Range string should be formatted as:\n"
            "`<number1>-<number2>` (numbers must be unique)"
        ),
    )


@dataclass
class CommandOnCooldown(CommandError):
    retry_after: float

    @property
    def embed(self):
        from utils.dates import now
        from utils.strings import discord_date

        return Embed(
            title="Command On Cooldown",
            description=f"You may use the command again {discord_date(now().timestamp() + self.retry_after)}",
        )


class InvalidNumber(CommandError):
    """Raised when a number string is improperly formatted."""
    embed = Embed(
        title="Invalid Number",
        description="Unrecognized number format",
    )


@dataclass
class NumberGreaterThan(CommandError):
    n: int = 0

    @property
    def embed(self):
        return Embed(
            title="Invalid Number",
            description=f"Number must be greater than {self.n}",
        )


class MigrationActive(CommandError):
    """Raised when a migration is currently in progress."""
    embed = Embed(
        title="Migration in Progress",
        description=(
            "The bot is currently undergoing a data migration\n"
            "Commands are temporarily disabled during this time"
        ),
        color=WARNING,
    )


@dataclass
class NotSubscribed(CommandError):
    feature: str = "this feature"

    @property
    def embed(self):
        from utils.strings import GG_PLUS_LINK
        return Embed(
            title="Requires GG+",
            description=f"[Get GG+]({GG_PLUS_LINK}) to access " + self.feature + "!",
            color=PLUS,
        )


class NotEnoughRaces(CommandError):
    embed = Embed(
        title="Not Enough Races",
        description="User has not completed this many races",
    )
