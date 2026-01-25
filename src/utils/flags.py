from dataclasses import dataclass
from typing import Optional, Union

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
class Flags: # IF status == unranked, metric = wpm
    metric: Optional[str] = "pp"
    raw: Optional[bool] = False
    gamemode: Optional[str] = None
    status: Optional[str] = None
    language: Optional[Union[str, Language]] = None

    def __post_init__(self):
        if isinstance(self.language, str):
            self.language = Language(self.language)
