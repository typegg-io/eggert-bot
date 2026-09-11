import numpy as np
from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from config import DEFAULT_UNIVERSE
from context import BotContext
from database.typegg.quotes import get_quotes
from database.typegg.races import get_raced_quote_ids
from database.typegg.sources import get_sources
from database.typegg.users import get_quote_bests
from utils.errors import BotError, NoRankedRaces
from utils.flags import Flags, Language
from utils.messages import Message, Page, paginate_data
from utils.schemas import Profile
from utils.stats import MAX_SCORING_QUOTES, PP_DECAY_FACTOR, PP_WEIGHT_DECAY_SHARE, PP_WEIGHT_FLOOR
from utils.strings import quote_display

# How far a quote reaches its neighbours, in percentiles of the ranked pool.
BANDWIDTH = 0.1

info = CommandInfo(
    name="unraced",
    aliases=["ur"],
    description="Recommends ranked quotes a user has never raced, most like the quotes their pp comes from.\n"
                "Quotes are matched on length, complexity and difficulty against the top 250 ranked quotes.",
    parameters="[username]",
    examples=[
        "-unraced",
        "-unraced eiko",
        "-unraced fr",
    ],
    plus=True,
)


class Unraced(Command):
    """Recommend ranked quotes a user has never raced."""

    supported_flags = {"language"}

    @commands.command(aliases=info.aliases)
    async def unraced(self, ctx: BotContext, *args: str):
        """Resolve the profile from the arguments, then list their recommendations."""
        self.check_gg_plus(ctx, "unraced quote recommendations")
        profile = await self.get_profile(ctx, args[0] if args else None)
        await run(ctx, profile)


def percentiles(values: list[float]) -> np.ndarray:
    """Return each value's percentile among the values, from 0 to 1."""
    values = np.array(values, dtype=float)
    return np.searchsorted(np.sort(values), values, side="right") / len(values)


def recommend(pool: list[dict], quote_bests: list, raced: set[str]) -> list[dict]:
    """Return the pool's unraced quotes, most like the quotes a user's pp comes from first."""
    features = np.column_stack([
        percentiles([len(quote["text"]) for quote in pool]),
        percentiles([quote["complexity"] for quote in pool]),
        percentiles([quote["difficulty"] for quote in pool]),
    ])

    index = {quote["quoteId"]: i for i, quote in enumerate(pool)}
    scoring = [index[best["quoteId"]] for best in quote_bests if best["quoteId"] in index]
    weights = PP_WEIGHT_DECAY_SHARE * PP_DECAY_FACTOR ** np.arange(len(scoring)) + PP_WEIGHT_FLOOR

    distances = sum((features[:, [axis]] - features[scoring, axis]) ** 2 for axis in range(features.shape[1]))
    scores = np.exp(-distances / (2 * BANDWIDTH ** 2)) @ weights

    return [pool[i] for i in np.argsort(-scores, kind="stable") if pool[i]["quoteId"] not in raced]


async def run(ctx: BotContext, profile: Profile) -> None:
    """Send the 100 unraced ranked quotes that best suit a user, paginated."""
    language = ctx.flags.language or Language(DEFAULT_UNIVERSE)
    if not language.is_universe:
        raise BotError("No Ranked Quotes", f"{language.name} has no ranked quotes of its own")

    quote_bests = get_quote_bests(
        profile["userId"],
        columns=["quoteId", "pp"],
        order_by="pp",
        limit=MAX_SCORING_QUOTES,
        flags=Flags(language=language),
    )
    if not quote_bests:
        raise NoRankedRaces(profile["username"])

    pool = [quote for quote in get_quotes().values() if quote["ranked"] and quote["language"] == language.name]
    recommendations = recommend(pool, quote_bests, get_raced_quote_ids(profile["userId"]))
    sources = get_sources()

    def entry_formatter(quote: dict) -> str:
        """Format one quote as a quote display."""
        quote = dict(quote)
        quote["source"] = sources[quote["sourceId"]]
        return quote_display(quote) + "\n"

    if recommendations:
        pages = paginate_data(recommendations, entry_formatter, 20, 5)
    else:
        pages = [Page(description="Every ranked quote has been raced.", flag_title=True)]

    message = Message(
        ctx,
        title="Unraced Quote Recommendations",
        header=f"**Unraced:** {len(recommendations):,} of {len(pool):,}\n",
        pages=pages,
        profile=profile,
    )

    await message.send()
