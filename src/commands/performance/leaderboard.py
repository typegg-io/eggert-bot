from discord.ext import commands

from api.leaders import get_leaders, get_multiplayer_leaders
from commands.base import Command
from database.typegg.daily_quotes import get_daily_rank_leaderboard
from database.typegg.quotes import get_top_submitters, get_ranked_quote_count
from database.typegg.users import get_quotes_over_leaderboard, get_user_lookup
from utils import strings
from utils.errors import GeneralException
from utils.messages import Message, Page, paginate_data
from utils.strings import get_argument, username_with_flag, rank, get_flag_title, LOADING, parse_number

categories = {
    # API leaderboards
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
    "wins": {
        "sort": "wins",
        "title": "Wins",
        "formatter": lambda user: f"{user["stats"]["wins"]:,} ({user["stats"]["wins"] / user["stats"]["quickplayRaces"]:.2%} win rate)"
    },
    "quotes": {
        "sort": "quotesTyped",
        "title": "Ranked Quotes Typed",
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

    # Multiplayer leaderboards
    "quickplay": {
        "title": "Quickplay",
        "multiplayer": True,
        "formatter": lambda user: f"{user["average"]:,.2f} WPM ({user["difficulty"]:.2f}★)",
    },

    # Custom leaderboards
    "submissions": {
        "title": "Quote Submissions",
    },
    "quotesover": {
        "title": "Quotes Over",
    },
    "dailywins": {
        "title": "Daily Quote Wins",
        "max_rank": 1,
    },
    "dailyseconds": {
        "title": "Daily Quote Seconds",
        "max_rank": 2,
        "exact": True,
    },
    "dailytoptens": {
        "title": "Daily Quote Top 10s",
        "max_rank": 10,
    },
}
info = {
    "name": "leaderboard",
    "aliases": ["lb"],
    "description": "Displays the top 100 users for a given category.\n"
                   f"Categories: {', '.join('`' + c + '`' for c in categories)}.",
    "parameters": "<category> [args]",
    "examples": [
        "-lb pp",
        "-lb wpm",
        "-lb quickplay",
    ],
}


class Leaderboard(Command):
    @commands.command(aliases=info["aliases"])
    async def leaderboard(self, ctx, category: str = "pp", *args):
        category = get_argument(categories.keys(), category)
        category_info = categories[category]

        if category_info.get("multiplayer"):
            return await run_multiplayer(ctx, category_info)

        if not category_info.get("formatter"):
            return await run_custom(ctx, category_info, args)

        await run(ctx, category_info)


def entry_formatter(data):
    bold = "**" if data["highlight"] else ""
    return f"{rank(data["rank"])} {bold}{username_with_flag(data)} - {data["category"]["formatter"](data)}{bold}\n"


async def run(ctx: commands.Context, category: dict):
    gamemode = ctx.flags.gamemode or "any"
    title = f"{category["title"]} Leaderboard"

    if category["sort"] not in ["wins", "level", "nWpm", "profileViews"]:
        title += get_flag_title(ctx.flags)

    skeleton_page = Page(
        title=title,
        description="\n".join(f"{rank(i + 1)} {LOADING}" for i in range(20)),
    )
    message = Message(ctx, page=skeleton_page)
    message.timeout = 60
    initial_send = message.start()

    results = await get_leaders(
        sort=category["sort"],
        per_page=100,
        gamemode=gamemode,
    )

    if gamemode == "quickplay" and category["sort"] == "races":
        category = {
            "sort": "races",
            "title": "Races",
            "formatter": lambda user: f"{user["stats"]["quickplayRaces"]:,}",
        }

    leaderboard = results["users"]
    for i in range(len(leaderboard)):
        leaderboard[i] |= {
            "rank": i + 1,
            "category": category,
            "highlight": leaderboard[i]["userId"] == ctx.user["userId"],
        }
    pages = paginate_data(leaderboard, entry_formatter, page_count=5, per_page=20)

    footer = None
    if category["sort"] == "quotesTyped":
        quote_count = get_ranked_quote_count()
        footer = f"{quote_count:,} Total Quotes"

    message.title = title
    message.pages = pages
    message.page_count = len(pages)
    message.paginated = True
    message.footer = footer

    await initial_send
    await message.edit()


async def run_custom(ctx: commands.Context, category: dict, args: tuple = ()):
    """Displays a custom leaderboard generated from the database."""
    title = f"{category["title"]} Leaderboard"

    if category["title"] == "Quotes Over":
        if not args:
            raise GeneralException("Missing threshold", "Usage: `-lb qo <threshold> [metric]`")

        threshold = parse_number(args[0])
        metric = get_argument(["pp", "wpm"], args[1] if len(args) > 1 else "wpm")
        title = f"Quotes Over {threshold:,} {"WPM" if metric == "wpm" else "pp"} Leaderboard" + get_flag_title(ctx.flags)

    skeleton_page = Page(
        title=title,
        description="\n".join(f"{rank(i + 1)} {LOADING}" for i in range(20)),
    )
    message = Message(ctx, page=skeleton_page)
    message.timeout = 60
    initial_send = message.start()

    pages = []

    if category["title"] == "Quote Submissions":
        leaderboard = get_top_submitters()
        for i in range(len(leaderboard)):
            leaderboard[i] = dict(leaderboard[i]) | {"rank": i + 1}
        formatter = lambda quote: f"{rank(quote["rank"])} {quote["submittedByUsername"]} - {quote["submissions"]:,}\n"
        pages = paginate_data(leaderboard, formatter, page_count=5, per_page=20)

    elif category["title"] == "Quotes Over":
        ctx.flags.status = ctx.flags.status or "ranked"

        leaderboard_data = get_quotes_over_leaderboard(
            threshold=threshold,
            metric=metric,
            limit=100,
            flags=ctx.flags
        )

        if not leaderboard_data:
            await initial_send

            message.title = title
            message.pages = [Page(description="No users above this threshold.", )]

            return await message.edit()

        user_lookup = get_user_lookup()

        leaderboard = []
        for i, entry in enumerate(leaderboard_data):
            user = user_lookup.get(entry["userId"], {
                "username": entry["userId"],
                "country": None,
            })
            leaderboard.append({
                "rank": i + 1,
                "username": user["username"],
                "country": user["country"],
                "count": entry["count"],
                "highlight": entry["userId"] == ctx.user["userId"],
            })

        def qo_formatter(entry):
            bold = "**" if entry["highlight"] else ""
            return f"{rank(entry["rank"])} {bold}{username_with_flag(entry)} - {entry["count"]:,}{bold}\n"

        pages = paginate_data(leaderboard, qo_formatter, page_count=5, per_page=20)

    elif "max_rank" in category:
        leaderboard_data = get_daily_rank_leaderboard(category["max_rank"], exact=category.get("exact", False))

        leaderboard = [
            {
                "rank": i + 1,
                "username": entry["username"],
                "country": entry["country"],
                "count": entry["count"],
                "highlight": entry["userId"] == ctx.user["userId"],
            }
            for i, entry in enumerate(leaderboard_data)
        ]

        def daily_formatter(entry):
            bold = "**" if entry["highlight"] else ""
            return f"{rank(entry["rank"])} {bold}{username_with_flag(entry)} - {entry["count"]:,}{bold}\n"

        pages = paginate_data(leaderboard, daily_formatter, page_count=5, per_page=20)

    await initial_send

    message.title = title
    message.pages = pages
    message.page_count = len(pages)

    await message.edit()


async def run_multiplayer(ctx: commands.Context, category: dict):
    title = f"{category["title"]} Leaderboard"
    skeleton_page = Page(
        title=title,
        description="\n".join(f"{rank(i + 1)} {LOADING}" for i in range(20)),
    )
    message = Message(ctx, page=skeleton_page)
    message.timeout = 60
    initial_send = message.start()

    results = await get_multiplayer_leaders()
    leaderboard = [
        {
            "rank": item["rank"],
            "username": item["username"],
            "country": item.get("country_code"),
            "userId": item["user_id"],
            "average": item["best_wpm_avg"],
            "difficulty": item["best_difficulty_avg"],
            "highlight": item["user_id"] == ctx.user["userId"],
        }
        for item in results["items"]
    ]

    def mp_formatter(user):
        bold = "**" if user["highlight"] else ""
        return f"{rank(user["rank"])} {bold}{username_with_flag(user)} - {category["formatter"](user)}{bold}\n"

    pages = paginate_data(leaderboard, mp_formatter, page_count=5, per_page=20)

    await initial_send

    message.title = title
    message.pages = pages
    message.page_count = len(pages)
    message.paginated = True

    await message.edit()
