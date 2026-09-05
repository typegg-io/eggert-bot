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
