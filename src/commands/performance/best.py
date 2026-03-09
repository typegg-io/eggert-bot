import re
from typing import Optional

from discord.ext import commands

from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.sources import get_sources
from database.typegg.users import get_quote_bests
from utils import strings
from utils.errors import NoRacesFiltered, NotSubscribed
from utils.messages import Message, paginate_data, Page
from utils.strings import get_argument, quote_display, get_flag_title

metrics = ["pp", "wpm"]
info = {
    "name": "best",
    "aliases": ["b"],
    "description": "Displays a user's top 100 quotes\n"
                   "\\- `metric` defaults to pp\n"
                   "\\- `wpm range`: `>150`, `<120`, or `100-150`",
    "parameters": "[username] [pp|wpm] [wpm range]",
}


class Best(Command):
    @commands.command(aliases=info["aliases"])
    async def best(
        self, ctx,
        username: Optional[str] = "me",
        metric: Optional[str] = "pp",
        wpm_range: Optional[str] = None
    ):
        min_wpm, max_wpm = None, None

        remaining = []
        for arg in filter(None, [username, metric, wpm_range]):
            if parsed := parse_wpm_range(arg):
                min_wpm, max_wpm = parsed
            else:
                remaining.append(arg)

        metric_val = next((a for a in remaining if get_argument(metrics, a, _raise=False)), "pp")
        username = next((a for a in remaining if a != metric_val), "me")
        metric = get_argument(metrics, metric_val)

        # GG+ exclusive
        if metric == "pp" and ctx.flags.raw and not ctx.user["isGgPlus"]:
            raise NotSubscribed("raw pp stats")

        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)
        await run(ctx, profile, metric, min_wpm=min_wpm, max_wpm=max_wpm)


def parse_wpm_range(s: str):
    pattern = r"(\d+(?:\.\d+)?)"
    if m := re.fullmatch(f">{pattern}", s):
        return float(m.group(1)), None
    if m := re.fullmatch(f"<{pattern}", s):
        return None, float(m.group(1))
    if m := re.fullmatch(f"{pattern}-{pattern}", s):
        return float(m.group(1)), float(m.group(2))
    return None


async def run(
    ctx: commands.Context,
    profile: dict,
    metric: str,
    reverse: bool = True,
    min_wpm: float = None,
    max_wpm: float = None
):
    flags = ctx.flags
    flags.status = flags.status or "ranked"
    metric = flags.metric or metric
    quotes = get_quotes()
    sources = get_sources()
    quote_bests = get_quote_bests(
        profile["userId"],
        columns=["quoteId", "pp", "wpm", "accuracy", "timestamp"],
        order_by=metric,
        reverse=reverse,
        limit=100,
        flags=flags,
        min_wpm=min_wpm,
        max_wpm=max_wpm,
    )
    if not quote_bests:
        raise NoRacesFiltered(profile["username"])

    def entry_formatter(data):
        quote = dict(quotes[data["quoteId"]])
        quote["source"] = sources[quote["sourceId"]]
        pp_display = f"{data["pp"]:,.2f} pp - "
        if flags.raw and not ctx.user["isGgPlus"]:
            pp_display = ""
        return quote_display(quote) + (
            f"{pp_display}{data["wpm"]:,.2f} WPM ({data["accuracy"]:.2%} Accuracy) - "
            f"{strings.discord_date(data["timestamp"])}\n\n"
        )

    per_page = 5
    page_count = 20
    page_count = min(page_count, ((len(quote_bests) - 1) // per_page) + 1)
    pages = []
    for i in range(page_count):
        description = ""
        for quote in quote_bests[i * per_page:(i + 1) * per_page]:
            description += entry_formatter(quote)
        pages.append(Page(description=description))

    pages = paginate_data(quote_bests, entry_formatter, 20, 5)
    title = f"{["Worst", "Best"][reverse]}{[" WPM", ""][metric == "pp"]} Quotes"

    if min_wpm is not None or max_wpm is not None:
        if min_wpm is not None and max_wpm is not None:
            title += f" {min_wpm:g}-{max_wpm:g} WPM"
        elif min_wpm is not None:
            title += f" ≥{min_wpm:g} WPM"
        else:
            title += f" <{max_wpm:g} WPM"

    title += get_flag_title(flags)

    message = Message(
        ctx,
        title=title,
        pages=pages,
        profile=profile,
    )

    await message.send()
