"""The flags every command accepts, and their parsed form."""

from dataclasses import dataclass
from datetime import datetime

from config import DEFAULT_UNIVERSE, UNIVERSE_CODES

LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ru": "Russian",
    "ja": "Japanese",
    "zh": "Chinese (Simplified)",
    "ko": "Korean",
    "tr": "Turkish",
    "no": "Norwegian",
    "id": "Indonesian",
    "vi": "Vietnamese",
    "la": "Latin",
    "hi": "Hindi",
}

FLAG_VALUES = {
    # Metrics
    "pp", "wpm",

    # Raw
    "raw",

    # Gamemode
    "solo", "quickplay", "lobby", "multiplayer",

    # Status
    "ranked", "unranked", "any"
}

PERIOD_VALUES = {"day", "week", "month", "year", "alltime"}

for language in LANGUAGES.keys():
    FLAG_VALUES.add(language)


@dataclass
class Language:
    """A language flag, holding its code and display name."""

    code: str

    @property
    def name(self) -> str:
        """Return the language's display name."""
        return LANGUAGES[self.code]

    @property
    def is_universe(self) -> bool:
        """Return whether this language has its own ranked pool and pp leaderboard."""
        return self.code in UNIVERSE_CODES

    def __str__(self) -> str:
        """Return the language code."""
        return self.code


@dataclass
class Flags:
    """The flags one command invocation carries, after parsing."""

    metric: str | None = "pp"
    raw: bool | None = False
    gamemode: str | None = None
    status: str | None = "ranked"
    language: str | Language | None = None
    number: int | None = None
    number_range: tuple | None = None
    quote_id: str | None = None
    date: datetime | None = None
    dates: tuple[datetime, ...] = ()
    period: str | None = None
    date_range: tuple[datetime, datetime] | None = None

    def __post_init__(self) -> None:
        """Coerce a language code string into a Language."""
        if isinstance(self.language, str):
            self.language = Language(self.language)


# Gamemode

# "multiplayer" is the umbrella term, so it selects both modes without filtering to either.
MULTIPLAYER_GAMEMODES = ("quickplay", "lobby", "multiplayer")


def is_multiplayer(flags: Flags) -> bool:
    """Return whether the gamemode flag selects multiplayer races."""
    return flags.gamemode in MULTIPLAYER_GAMEMODES


def gamemode_filter(flags: Flags) -> str | None:
    """Return the one gamemode to match rows against, or None when the flag covers both."""
    return None if flags.gamemode == "multiplayer" else flags.gamemode


def multiplayer_race_count(flags: Flags, stats: dict) -> int:
    """Return how many races a profile has in the selected multiplayer mode."""
    multiplayer = stats["races"] - stats["soloRaces"]

    if flags.gamemode == "quickplay":
        return stats["quickplayRaces"]
    if flags.gamemode == "lobby":
        return multiplayer - stats["quickplayRaces"]

    return multiplayer


def get_flag_title(flags: Flags) -> str:
    """Build a parenthetical title string from command flags (e.g., '(Raw, Solo)')."""
    flag_titles = []
    if flags.language:
        flag_titles.append(flags.language.name)
    if flags.status:
        flag_titles.append(flags.status.title())
    if flags.raw:
        flag_titles.append("Raw")
    if flags.gamemode:
        flag_titles.append(flags.gamemode.title())

    if not flag_titles:
        return ""

    return " (" + ", ".join(flag_titles) + ")"


def resolve_universe(flags: Flags, stored: str | None) -> Language | None:
    """Return the universe a command runs in, preferring a typed flag over the stored one."""
    if flags.language:
        return flags.language
    if stored and stored != DEFAULT_UNIVERSE:
        return Language(stored)
    return None


def universe_code(flags: Flags) -> str | None:
    """Return the code the API takes for the active language, or None when it has no universe."""
    # The API 400s on a language code outside the registry rather than falling back to English.
    if flags.language and flags.language.is_universe:
        return str(flags.language)

    return None


def apply_universe_status(flags: Flags) -> None:
    """Force unranked for a language that has no ranked pool of its own."""
    if flags.language and not flags.language.is_universe:
        flags.status = "unranked"
    if flags.status != "ranked":
        flags.metric = "wpm"
