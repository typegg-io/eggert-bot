"""Loading rows appear only when the work behind them is slow."""

import asyncio
from types import SimpleNamespace

from utils.flags import Flags
from utils.messages import Message, Page

DELAY = 0.05


class RecordingMessage:
    """The message a send returns, recording every edit made to it."""

    def __init__(self, edits: list) -> None:
        """Share the edit log with the context that sent this message."""
        self.id = 1
        self.attachments = []
        self.edits = edits

    async def edit(self, **kwargs) -> "RecordingMessage":
        """Record one edit and return itself."""
        self.edits.append(kwargs)
        return self


class RecordingContext:
    """A context that records what a Message sends and edits."""

    def __init__(self) -> None:
        """Start with an empty log and the fields Message reads."""
        self.sent = []
        self.edits = []
        self.flags = Flags()
        self.user = {"theme": {"embed": 0}, "timezone": "UTC"}
        self.author = SimpleNamespace(id=1)

    async def send(self, **kwargs) -> RecordingMessage:
        """Record one send and return a stand-in for the message."""
        self.sent.append(kwargs)
        return RecordingMessage(self.edits)


def build() -> tuple[RecordingContext, Message, Page]:
    """Return a context, a message holding one loading page, and that page."""
    ctx = RecordingContext()
    page = Page(title="Leaderboard", description="loading")

    return ctx, Message(ctx, page=page), page


def descriptions(records: list) -> list[str]:
    """Return the description of the embed in each recorded send or edit."""
    return [record["embed"].description.strip() for record in records]


async def fast_work() -> RecordingContext:
    """Finish before the delay elapses and return what the context recorded."""
    ctx, message, page = build()
    task = message.start(delay=DELAY)

    page.description = "results"
    await message.finish(task)

    return ctx


async def slow_work() -> RecordingContext:
    """Outlast the delay and return what the context recorded."""
    ctx, message, page = build()
    task = message.start(delay=DELAY)

    await asyncio.sleep(DELAY * 4)
    page.description = "results"
    await message.finish(task)

    return ctx


def test_fast_work_never_shows_loading_rows():
    """The loading rows are the whole cost of the edit that Discord can reorder."""
    ctx = asyncio.run(fast_work())

    assert descriptions(ctx.sent) == ["results"]
    assert ctx.edits == []


def test_slow_work_shows_loading_rows_then_edits():
    """Work that outlasts the delay still earns its placeholder."""
    ctx = asyncio.run(slow_work())

    assert descriptions(ctx.sent) == ["loading"]
    assert descriptions(ctx.edits) == ["results"]
