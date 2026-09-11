"""The bot's exception types, each carrying the embed it displays."""

from dataclasses import dataclass

from discord import Embed
from discord.ext.commands import CheckFailure, CommandError

from command_info import CommandInfo
from config import BOT_PREFIX as prefix, EIKO
from utils.colors import PLUS, WARNING
from utils.flags import Flags, get_flag_title
from utils.urls import GG_PLUS_LINK


@dataclass
class BotError(CommandError):
    """An error that carries its own title and text."""
    title: str
    text: str
    flags: Flags | None = None

    @property
    def embed(self) -> Embed:
        """Return the embed, appending the flag title when flags are set."""
        title = self.title + (get_flag_title(self.flags) if self.flags is not None else "")
        return Embed(
            title=title,
            description=self.text,
        )


class MissingArguments(CommandError):
    """Raised when one or more parameters are missing from command arguments."""

    def usage_embed(self, info: CommandInfo, show_tip: bool = False) -> Embed:
        """Return the usage embed for a command, with an optional link tip."""
        embed = Embed(
            title="Missing Argument",
            description=(
                "One or more arguments is missing\n"
                f"Usage: `{info.usage}`"
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
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Invalid Argument",
            description="Argument can be: " + ", ".join([f"`{option}`" for option in self.options]),
        )


@dataclass
class ErrorWithUsername(CommandError):
    """General exception for errors with a username."""
    username: str


class ProfileNotFound(ErrorWithUsername):
    """Raised when a TypeGG profile is not found."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="User Not Found",
            description=f"User `{self.username.replace("`", "")}` not found",
        )


class NoRaces(ErrorWithUsername):
    """Raised when a TypeGG profile has no races."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="No Races",
            description=f"User `{self.username.replace("`", "")}` has no races",
        )


class NoRankedRaces(ErrorWithUsername):
    """Raised when a TypeGG profile has no ranked races."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="No Ranked Races",
            description=f"User `{self.username.replace("`", "")}` has no ranked races",
        )


class NoRacesFiltered(ErrorWithUsername):
    """Raised when a TypeGG profile has no races with the current filters."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="No Filtered Races",
            description=f"User `{self.username.replace("`", "")}` has no races with these filters",
        )


class NoQuoteRaces(ErrorWithUsername):
    """Raised when a user has no races on a specific quote."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="No Quote Races",
            description=f"User `{self.username.replace("`", "")}` has no races on this quote",
        )


class UserBanned(CheckFailure):
    """Raised when a banned user attempts to run a command."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="You Are Banned",
            description="You are banned from using commands",
        )


class UserNotAdmin(CheckFailure):
    """Raised when a non-admin user attempts to run an admin-only command."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Admin Command",
            description="You lack the permissions to use this command",
        )


class UserNotOwner(CheckFailure):
    """Raised when a non-owner attempts to run an owner-only command."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Owner Command",
            description="You lack the permissions to use this command",
        )


class SameUsername(CommandError):
    """Raised when two passed usernames are the same."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Same Username",
            description="You must provide two unique usernames to compare",
        )


class UnknownCommand(CommandError):
    """Raised when an unknown command is referenced."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Command Not Found",
            description=f"`{prefix}help` for a list of commands",
        )


@dataclass
class UnexpectedError(CommandError):
    """Global catch-all case for unexpected exceptions."""
    error_type: str

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Unexpected Error",
            description=(
                "An unexpected error occurred:\n"
                f"`{self.error_type}`"
            ),
        )


@dataclass
class BotUserNotFound(CommandError):
    """Raised when a discord ID is not found within the bot's database."""
    discord_id: str

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="User Not Found",
            description=f"<@{self.discord_id}> has never used the bot",
        )


class DiscordUserNotFound(CommandError):
    """Raised when a Discord user is not found."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="User Not Found",
        )


@dataclass
class UnknownQuote(CommandError):
    """Raised when a quote ID doesn't match any existing quote."""
    quote_id: str

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Unknown Quote",
            description=f"Quote `{self.quote_id.replace("`", "")}` not found",
        )


class InvalidDate(CommandError):
    """Raised when a date string is improperly formatted."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Invalid Date",
            description="Unrecognized date format",
        )


class DailyQuoteChannel(CommandError):
    """Raised when a non-daily command is sent in the daily quote channel."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Daily Channel",
            description="Only daily commands can be used in this channel\n"
                        f"Use <#{1337196592905846864}> for other commands",
        )


@dataclass
class APIError(CommandError):
    """Raised when the TypeGG API returns an error status."""
    status: int
    message: str

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="API Error",
            description=(
                f"API returned status {self.status}:\n"
                f"{self.message}"
            ),
        )


@dataclass
class APIUnavailable(CommandError):
    """Raised when the TypeGG API is briefly unavailable and says when to retry."""
    message: str
    retry_after: int

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Try Again Soon",
            description=(
                f"{self.message}\n"
                f"Try again in {self.retry_after} seconds"
            ),
            color=WARNING,
        )


@dataclass
class RaceNotFound(CommandError):
    """Raised when a specific race is not found."""
    username: str
    race_number: int

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Race Not Found",
            description=(
                f"Race `#{self.race_number:,}` for "
                f"`{self.username.replace("`", "")}` not found"
            ),
        )


class InvalidRange(CommandError):
    """Raised when a range string is improperly formatted."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Invalid Range",
            description=(
                "Range string should be formatted as:\n"
                "`<number1>-<number2>` (numbers must be unique)"
            ),
        )


@dataclass
class CommandOnCooldown(CommandError):
    """Raised when a user runs a command before its cooldown expires."""
    retry_after: float

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        from utils.dates import discord_date, now

        return Embed(
            title="Command On Cooldown",
            description=f"You may use the command again {discord_date(now().timestamp() + self.retry_after)}",
        )


@dataclass
class DailyLimitReached(CommandError):
    """Raised when a user has reached their daily usage limit."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Daily Limit Reached",
            description=(
                f"[Get GG+]({GG_PLUS_LINK}) to continue our conversation!"
            ),
            color=PLUS,
        )


class InvalidNumber(CommandError):
    """Raised when a number string is improperly formatted."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Invalid Number",
            description="Unrecognized number format",
        )


@dataclass
class NumberGreaterThan(CommandError):
    """Raised when a number is not above the required minimum."""
    n: int = 0

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Invalid Number",
            description=f"Number must be greater than {self.n}",
        )


class BotLocked(CheckFailure):
    """Raised when the bot is in lockdown mode."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title=":rotating_light: Bot Locked",
            description="The bot is currently in lockdown mode",
            color=WARNING,
        )


class MigrationActive(CommandError):
    """Raised when a migration is currently in progress."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Migration in Progress",
            description=(
                "The bot is currently undergoing a data migration\n"
                "Commands are temporarily disabled during this time"
            ),
            color=WARNING,
        )


@dataclass
class NotSubscribed(CommandError):
    """Raised when a command requires GG+ and the user lacks it."""
    feature: str = "this feature"

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Requires GG+",
            description=f"[Get GG+]({GG_PLUS_LINK}) to access " + self.feature + "!",
            color=PLUS,
        )


class NotEnoughRaces(CommandError):
    """Raised when a user has fewer races than the command needs."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Not Enough Races",
            description="User has not completed this many races",
        )


class AllQuits(CommandError):
    """Raised when every race in the requested range is a quit."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="All Quits",
            description="All races in this range are quits",
        )


class MessageTooLong(CommandError):
    """Raised when a message exceeds Discord's character limit."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Message Too Long",
            description="The maximum number of characters\nfor a message has been exceeded"
        )


class DiscordServerError(CommandError):
    """Raised when Discord's servers cannot be reached."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Discord Server Error",
            description=(
                "Failed to connect to Discord servers\n"
                "Please try again"
            ),
        )


class InvalidKeystrokeData(CommandError):
    """Raised when a race's keystroke data cannot be decoded."""

    @property
    def embed(self) -> Embed:
        """Return the embed shown for this error."""
        return Embed(
            title="Invalid Keystroke Data",
            description=(
                "The format of this keystroke data is corrupt.\n"
                f"If this replay happened very recently, contact <@{EIKO}>!"
            ),
        )
