import asyncio

from discord import Embed, Forbidden, File
from discord.ext import commands, tasks

from api.daily_quotes import get_daily_quote
from api.users import get_profile, get_race
from commands.daily.dailyleaderboard import display_daily_quote
from config import DAILY_QUOTE_CHANNEL_ID, SITE_URL, TYPEGG_GUILD_ID, DAILY_QUOTE_ROLE_ID
from database.bot.users import get_user
from database.typegg.daily_quotes import add_daily_quote, add_daily_results, get_missing_days, update_daily_quote_id
from graphs import daily as daily_graph
from utils import dates
from utils.colors import DEFAULT_THEME
from utils.dates import parse_date, format_date
from utils.files import remove_file
from utils.keystrokes import get_keystroke_data
from utils.logging import log, log_error
from utils.strings import discord_date


class BackgroundTasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tasks_loop.start()

    def cog_unload(self):
        self.tasks_loop.cancel()

    @tasks.loop(minutes=1)
    async def tasks_loop(self):
        now = dates.now()

        if now.hour == 20 and now.minute == 0:
            await daily_quote_reminder(self.bot)

        elif now.hour == 0 and now.minute == 5:
            await daily_quote_results(self.bot)
            await daily_quote_ping(self.bot)
            await import_daily_quotes()

    @tasks_loop.error
    async def tasks_loop_error(self, error):
        log_error("Tasks Loop", error)


async def setup(bot):
    await bot.add_cog(BackgroundTasks(bot))


async def daily_quote_results(bot: commands.Bot):
    """Sends out the previous daily quote's results."""
    channel = bot.get_channel(DAILY_QUOTE_CHANNEL_ID)

    date = parse_date("yesterday")
    daily_quote = await get_daily_quote(date.strftime("%Y-%m-%d"))
    score_list = []

    for score in daily_quote["leaderboard"][:10]:
        race = await get_race(score["userId"], score["raceNumber"], get_keystrokes=True)
        keystroke_data = get_keystroke_data(race["keystrokeData"])
        score["keystroke_wpm"] = keystroke_data.keystrokeWpm
        score_list.append(score)

    file_name = daily_graph.render(
        score_list,
        f"Daily Quote #{daily_quote["dayNumber"]} - "
        f"{format_date(parse_date(daily_quote["startDate"]))}",
        DEFAULT_THEME,
    )
    file = File(file_name, filename=file_name)

    await display_daily_quote(
        channel,
        daily_quote,
        title=f"Daily Quote #{daily_quote["dayNumber"]:,} Results",
        show_leaderboard=True,
        show_champion=True,
        color=0xF1C40F,
    )

    await channel.send(file=file)
    remove_file(file_name)


async def daily_quote_ping(bot: commands.Bot):
    """Sends out a ping with daily quote information."""
    channel = bot.get_channel(DAILY_QUOTE_CHANNEL_ID)

    date = parse_date("today")
    daily_quote = await get_daily_quote(date.strftime("%Y-%m-%d"))
    update_daily_quote_id(daily_quote["quote"]["quoteId"])

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
    daily_quote = await get_daily_quote(date.strftime("%Y-%m-%d"), results=100)
    daily_users = {score["userId"] for score in daily_quote["leaderboard"]}

    for member in role.members:
        if member.bot:
            continue

        bot_user = get_user(member.id, auto_insert=False)
        if not bot_user or not bot_user["userId"]:
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


async def import_daily_quotes():
    """Imports all the recent daily quotes."""
    missing_days = get_missing_days()
    for number in missing_days:
        log(f"Importing daily quote #{number:,}")
        daily_quote = await get_daily_quote(number=number, results=100)
        add_daily_quote(daily_quote)
        add_daily_results(number, daily_quote["leaderboard"])
