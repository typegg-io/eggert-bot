from discord.ext import commands

from api.daily_quotes import get_daily_quote
from config import DAILY_QUOTE_CHANNEL_ID, DAILY_QUOTE_ROLE_ID
from utils import urls
from utils.messages import Page, Message
from utils.strings import quote_display


async def daily_quote_ping(bot: commands.Bot):
    """Sends out a ping with daily quote information."""
    channel = bot.get_channel(DAILY_QUOTE_CHANNEL_ID)

    daily_quote = await get_daily_quote()
    quote = daily_quote["quote"]
    quote_id = quote["quoteId"]

    page = Page(
        title=f"New Daily Quote! #{daily_quote["dayNumber"]:,}\n{quote_id}",
        description=quote_display(quote),
        color=0xF1C40F,
    )

    message = Message(
        channel,
        page=page,
        url=urls.race(quote_id),
        thumbnail=quote["source"]["thumbnailUrl"],
        content=f"<@&{DAILY_QUOTE_ROLE_ID}>",
    )

    await message.send()
