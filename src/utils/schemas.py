"""The shapes of the dicts commands pass around."""

from typing import NotRequired, TypedDict


class Theme(TypedDict):
    """A user's graph and embed theme."""
    embed: int
    axis: str
    background: str
    graph_background: str
    grid: str
    grid_opacity: float
    line: str
    raw_speed: str
    title: str
    text: str
    crosses: str
    isGgPlus: NotRequired[bool]


class BestRecord(TypedDict):
    """A user's best race by one metric."""
    value: float


class DailyQuoteStats(TypedDict):
    """A user's daily quote streaks and completion count."""
    streak: int
    bestStreak: int
    completed: int


class Hardware(TypedDict):
    """The keyboard setup a user lists on their profile."""
    layout: str | None
    keyboard: str | None
    switches: str | None


class ProfileStats(TypedDict):
    """The stats block of a profile."""
    races: int
    soloRaces: int
    quickplayRaces: int
    quotesTyped: int
    charactersTyped: float
    wins: int
    playTime: float
    level: float
    experience: float
    accuracy: float
    nWpm: float
    totalPp: float
    bestPp: BestRecord
    bestWpm: BestRecord
    dailyQuotes: DailyQuoteStats
    firsts: int
    podiums: int
    topTens: int


class Profile(TypedDict):
    """A TypeGG user profile, holding the fields the bot reads."""
    userId: str
    username: str
    displayName: NotRequired[str | None]
    avatarUrl: str | None
    country: str | None
    globalRank: int
    countryRank: int
    joinDate: str
    lastSeen: str
    profileViews: int
    hardware: Hardware
    stats: ProfileStats
    isGgPlus: NotRequired[bool]
    subscribeDate: NotRequired[str | None]
