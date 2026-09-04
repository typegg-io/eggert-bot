from dataclasses import dataclass
from datetime import datetime

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
    "la": "Latin",
}

FLAG_VALUES = {
    # Metrics
    "pp", "wpm",

    # Raw
    "raw",

    # Gamemode
    "solo", "quickplay", "lobby",

    # Status
    "ranked", "unranked", "any"
}

for language in LANGUAGES.keys():
    FLAG_VALUES.add(language)


@dataclass
class Language:
    code: str

    @property
    def name(self) -> str:
        return LANGUAGES[self.code]

    def __str__(self) -> str:
        return self.code


@dataclass
class Flags:
    metric: str | None = "pp"
    raw: bool | None = False
    gamemode: str | None = None
    status: str | None = "ranked"
    language: str | Language | None = None
    number: int | None = None
    number_range: tuple | None = None
    quote_id: str | None = None
    date: datetime | None = None

    def __post_init__(self):
        if isinstance(self.language, str):
            self.language = Language(self.language)


def get_flag_title(flags: Flags):
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
