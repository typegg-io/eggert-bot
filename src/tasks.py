import asyncio

from discord import Embed, Forbidden
from discord.ext import commands

from api.daily_quotes import get_daily_quote
from api.users import get_profile
from commands.quotes.dailyleaderboard import display_daily_quote
from config import DAILY_QUOTE_CHANNEL_ID, SITE_URL, TYPEGG_GUILD_ID, DAILY_QUOTE_ROLE_ID
from database.bot.users import get_user
from utils.dates import parse_date
from utils.strings import discord_date


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


async def daily_quote_reminder(bot: commands.Bot):
    """Sends out a DM reminder to anyone on a daily streak who hasn't completed the daily quote."""
    guild = bot.get_guild(TYPEGG_GUILD_ID)
    role = guild.get_role(DAILY_QUOTE_ROLE_ID)

    date = parse_date("today")
    daily_quote = await get_daily_quote(date.strftime("%Y-%m-%d"))
    daily_users = {score["userId"] for score in daily_quote["leaderboard"]}

    for member in role.members:
        if member.bot:
            continue

        bot_user = get_user(member.id, auto_insert=False)
        if not bot_user:
            continue

        user_id = bot_user["userId"]
        profile = await get_profile(user_id)
        current_streak = profile["stats"]["dailyQuotes"]["streak"]

        if current_streak > 0 and user_id not in daily_users:
            embed = Embed(
                title=":warning: Your daily streak expires soon! :warning:",
                description=(
                    f"Your :fire: {current_streak} day streak will end "
                    f"{discord_date(daily_quote['endDate'])}\n"
                    "Keep it alive by playing today's quote!\n"
                    f"{SITE_URL}/daily"
                ),
                color=0xF1C40F,
            )
            try:
                await member.send(embed=embed)
                await asyncio.sleep(0.5)
            except Forbidden:
                pass
