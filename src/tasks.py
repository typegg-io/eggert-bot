from discord.ext import commands

from api.daily_quotes import get_daily_quote
from commands.quotes.dailyleaderboard import display_daily_quote
from config import DAILY_QUOTE_CHANNEL_ID
from utils.dates import parse_date


async def daily_quote_results(bot: commands.Bot):
    """Sends out the previous daily quote's results."""
    channel = bot.get_channel(DAILY_QUOTE_CHANNEL_ID)

    date = parse_date("yesterday")
    daily_quote = await get_daily_quote(date.strftime("%Y-%m-%d"))

    await display_daily_quote(
        channel,
        daily_quote,
        title=f"Daily Quote #{daily_quote["dayNumber"]:,} Results",
        show_leaderboard=True,
        show_champion=True,
        color=0xF1C40F,
    )


async def daily_quote_ping(bot: commands.Bot):
    """Sends out a ping with daily quote information."""
    channel = bot.get_channel(DAILY_QUOTE_CHANNEL_ID)

    date = parse_date("today")
    daily_quote = await get_daily_quote(date.strftime("%Y-%m-%d"))

    await display_daily_quote(
        channel,
        daily_quote,
        title=f"New Daily Quote #{daily_quote["dayNumber"]:,}",
        show_leaderboard=False,
        color=0xF1C40F,
        mention=True,
    )
