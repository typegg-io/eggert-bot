from discord.ext import commands

from api.users import get_quotes
from command_info import CommandInfo
from commands.base import Command, take_universe
from context import BotContext
from utils.dates import discord_date
from utils.errors import BotError
from utils.messages import Message, paginate_data
from utils.schemas import Profile, ProfileStats
from utils.strings import pp_display, quote_display, rank

# The API rejects a maxRank outside 1 to 100.
MAX_RANK = 100
QUOTE_LIMIT = 100
PLACEMENTS = {"firsts": "Firsts", "podiums": "Podiums", "topTens": "Top 10s"}

info = CommandInfo(
    name="quoteranks",
    aliases=["qr", "ranks"],
    description="Displays a user's top 100 quote leaderboard positions.\n"
                "Ordered by position, then by how far ahead of the next racer they sit.\n"
                "Add a position to keep only ranks that high, like `1` for firsts.",
    parameters="[username] [position]",
    examples=[
        "-qr",
        "-qr eiko",
        "-qr eiko 1",
        "-qr eiko 10 -fr",
    ],
)


class QuoteRanks(Command):
    """Display the quote leaderboard positions a user holds, best first."""

    supported_flags = {"language", "number"}

    @commands.command(aliases=info.aliases)
    async def quoteranks(self, ctx: BotContext, *args: str):
        """Resolve the position cutoff and the profile, then render the list."""
        max_rank = None
        if ctx.flags.number is not None:
            max_rank = int(abs(ctx.flags.number))
            if not 1 <= max_rank <= MAX_RANK:
                raise BotError("Invalid Position", f"Position must be between 1 and {MAX_RANK}")

        profile = await self.get_profile(ctx, args[0] if args else None)
        await run(ctx, profile, max_rank)


def lead_display(margin: float | None) -> str:
    """Return how far a position sits ahead of the next racer below it."""
    if margin is None:
        return "No one below"
    if margin == 0:
        return "Tied"
    return f"+{margin:,.2f} pp ahead"


def placement_line(stats: ProfileStats) -> str:
    """Return the user's firsts, podiums and top 10s on one line, leaving out any that are zero."""
    return " | ".join(f"**{label}:** {stats[key]:,}" for key, label in PLACEMENTS.items() if stats[key])


async def run(ctx: BotContext, profile: Profile, max_rank: int | None) -> None:
    """Send a user's best quote leaderboard positions, paginated."""
    universe = await take_universe(ctx)
    response = await get_quotes(
        profile["userId"],
        gamemode=None,
        status="ranked",
        sort="globalRank",
        max_rank=max_rank,
        universe=universe,
        per_page=QUOTE_LIMIT,
    )

    quote_ranks = response["quotes"]
    if not quote_ranks:
        username = profile["username"].replace("`", "")
        text = f"User `{username}` has no ranked quotes"
        if max_rank is not None:
            text = f"User `{username}` holds no position of #{max_rank} or better"
        raise BotError("No Quote Ranks", text, ctx.flags)

    def entry_formatter(data) -> str:
        """Format one quote as a quote display, then its position and the race holding it."""
        best_race = data["bestRace"]
        return quote_display(data["quote"]) + (
            f"{rank(data["globalRank"])} {lead_display(data["margin"])} - "
            f"{pp_display(best_race["pp"])} - {best_race["wpm"]:,.2f} WPM - "
            f"{discord_date(best_race["timestamp"])}\n\n"
        )

    pages = paginate_data(quote_ranks, entry_formatter, 20, 5)
    header = placement_line(profile["stats"])

    message = Message(
        ctx,
        title="Quote Ranks",
        header=header + "\n" if header else "",
        pages=pages,
        profile=profile,
    )

    await message.send()
