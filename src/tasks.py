from discord import Embed
from discord.ext import commands

from api.daily_quotes import get_daily_quote
from config import DAILY_QUOTE_CHANNEL_ID, DAILY_QUOTE_ROLE_ID
from utils import urls
from utils.strings import quote_display


async def daily_quote_ping(bot: commands.Bot):
    """Sends out a ping with daily quote information."""
    channel = bot.get_channel(DAILY_QUOTE_CHANNEL_ID)

    daily_quote = await get_daily_quote()
    quote = daily_quote["quote"]
    quote_id = quote["quoteId"]

    embed = Embed(
        title=f"New Daily Quote! #{daily_quote["dayNumber"]:,}\n{quote_id}",
        description=quote_display(quote),
        url=urls.race(quote_id),
        color=0xF1C40F,
    )

    embed.set_thumbnail(url=quote["source"]["thumbnailUrl"])

    await channel.send(embed=embed, content=f"<@&{DAILY_QUOTE_ROLE_ID}>")
