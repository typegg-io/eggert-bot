from discord.ext import commands

from api.leaders import get_leaders
from commands.base import Command
from utils import strings
from utils.messages import Message, paginate_data
from utils.strings import get_argument, username_with_flag, rank, get_flag_title

categories = {
    "pp": {
        "sort": "totalPp",
        "title": "Total pp",
        "formatter": lambda user: f"{user["stats"]["totalPp"]:,.0f} pp ({user["stats"]["accuracy"]:.2%} Accuracy)"
    },
    "best": {
        "sort": "bestPp",
        "title": "Best pp",
        "formatter": lambda user: f"{user["stats"]["bestPp"]["value"]:,.2f} pp"
    },
    "wpm": {
        "sort": "bestWpm",
        "title": "Best WPM",
        "formatter": lambda user: f"{user["stats"]["bestWpm"]["value"]:,.2f} WPM"
    },
    "nwpm": {
        "sort": "nWpm",
        "title": "nWPM",
        "formatter": lambda user: f"{user["stats"]["nWpm"]:,.2f} WPM"
    },
    "level": {
        "sort": "level",
        "title": "Level",
        "formatter": lambda user: f"{user["stats"]["level"]:,.2f} ({user["stats"]["experience"]:,.0f} XP)"
    },
    "playtime": {
        "sort": "playTime",
        "title": "Play Time",
        "formatter": lambda user: f"{strings.format_duration(user["stats"]["playTime"] / 1000)}"
    },
    "races": {
        "sort": "races",
        "title": "Races",
        "formatter": lambda user: f"{user["stats"]["races"]:,}"
    },
    "races.multiplayer": {
        "sort": "races",
        "title": "Races",
        "formatter": lambda user: f"{user["stats"]["multiplayerRaces"]:,}",
    },
    "wins": {
        "sort": "wins",
        "title": "Wins",
        "formatter": lambda user: f"{user["stats"]["wins"]:,} ({user["stats"]["wins"] / user["stats"]["multiplayerRaces"]:.2%} win rate)"
    },
    "quotes": {
        "sort": "quotesTyped",
        "title": "Quotes Typed",
        "formatter": lambda user: f"{user["stats"]["quotesTyped"]:,}"
    },
    "views": {
        "sort": "profileViews",
        "title": "Profile Views",
        "formatter": lambda user: f"{user["profileViews"]:,}"
    },
    "daily": {
        "sort": "dailyQuotes.streak",
        "title": "Current Daily Quote Streak",
        "formatter": lambda user: f"{user["stats"]["dailyQuotes"]["streak"]} :fire:"
    },
    "streak": {
        "sort": "dailyQuotes.bestStreak",
        "title": "Best Daily Quote Streak",
        "formatter": lambda user: f"{user["stats"]["dailyQuotes"]["bestStreak"]} :fire:"
    },
    "dailyquotes": {
        "sort": "dailyQuotes.completed",
        "title": "Total Daily Quotes Completed",
        "formatter": lambda user: f"{user["stats"]["dailyQuotes"]["completed"]:,}"
    },
    "characters": {
        "sort": "charactersTyped",
        "title": "Characters Typed",
        "formatter": lambda user: f"{user["stats"]["charactersTyped"]:,}"
    },
}
info = {
    "name": "leaderboard",
    "aliases": ["lb"],
    "description": "Displays the top 100 users for a given category\n"
                   f"Category can be: {", ".join("`" + c + "`" for c in categories)}",
    "parameters": "<category> [multiplayer]",
}


class Leaderboard(Command):
    @commands.command(aliases=info["aliases"])
    async def leaderboard(self, ctx, category: str):
        category = get_argument(categories.keys(), category)
        await run(ctx, categories[category])


def entry_formatter(data):
    return f"{rank(data["rank"])} {username_with_flag(data)} - {data["category"]["formatter"](data)}\n"


async def run(ctx: commands.Context, category: dict):
    gamemode = ctx.flags.get("gamemode", "any")
    results = await get_leaders(
        sort=category["sort"],
        per_page=100,
        gamemode=gamemode,
    )

    if gamemode == "multiplayer" and category["sort"] == "races":
        category = categories["races.multiplayer"]

    leaderboard = results["users"]
    for i in range(len(leaderboard)):
        leaderboard[i] |= {"rank": i + 1, "category": category}
    pages = paginate_data(leaderboard, entry_formatter, page_count=5, per_page=20)

    title = f"{category["title"]} Leaderboard"

    if category["sort"] not in ["wins", "level", "nWpm", "profileViews"]:
        title += get_flag_title(ctx.flags)

    message = Message(
        ctx,
        title=title,
        pages=pages,
    )

    await message.send()
