import numpy as np
from discord.ext import commands

from api.users import get_quote as get_quote_stats
from command_info import CommandInfo
from commands.base import Command, enforce_daily_quote
from config import DAILY_QUOTE_CHANNEL_ID
from context import BotContext
from database.typegg.races import get_race, get_races
from database.typegg.users import get_quote_bests
from graphs import improvement
from utils.colors import SUCCESS
from utils.dates import discord_date, parse_date
from utils.errors import APIError, BotError
from utils.messages import Field, Message, Page, usable_in
from utils.schemas import Profile, Theme
from utils.stats import calculate_total_pp
from utils.strings import INCREASE, format_duration, quote_display

info = CommandInfo(
    name="quote",
    aliases=["q", "pb", "qh", "qg", "qp", "qa"],
    description="Displays a user's stats on a specific quote.",
    parameters="[username] [quote_id:latest]",
    privacy=True,
    examples=[
        "-q",
        "-q eiko",
        "-q eiko piykyai_3408",
    ],
)
PROGRESSION_LIMIT = 50


class Quote(Command):
    """Display a user's stats on one quote."""

    supported_flags = {"number", "quote_id"}

    @commands.command(aliases=info.aliases)
    @usable_in(DAILY_QUOTE_CHANNEL_ID)
    async def quote(self, ctx: BotContext, *args: str):
        """Resolve the quote from a flag, a race number, or the caller's latest race."""
        ctx.flags.status = None
        profile = await self.get_profile(ctx, args[0] if args else None)

        if ctx.flags.number is not None or ctx.flags.quote_id is None:
            race_number = await self.get_race_number(profile, ctx.flags.number)
            race = get_race(profile["userId"], race_number)
            quote = await self.get_quote(ctx, race["quoteId"])
        else:
            quote = await self.get_quote(ctx, ctx.flags.quote_id, profile["userId"])

        enforce_daily_quote(ctx, quote["quoteId"])
        await run(ctx, profile, quote)


def get_quote_best_rank(quote_bests: list[dict], race_id: str) -> int | None:
    """Returns the rank of a score given a list of quote bests."""
    for i, race in enumerate(quote_bests):
        if race["raceId"] == race_id:
            return i + 1


def score_display(score, show_pp=True) -> str:
    """Format one score as a single line, with or without its pp."""
    if show_pp:
        return (
            f"{score["pp"]:,.2f} pp ({score["wpm"]:,.2f} WPM) - "
            f"{discord_date(score["timestamp"])}"
        )

    return f"{score["wpm"]:,.2f} WPM - {discord_date(score["timestamp"])}"


def build_personal_best_page(quote: dict, quote_races: list[dict], user_id: str) -> Page:
    """Build the personal best page for a ranked quote, showing how the latest race moved it."""
    description = quote_display(quote, max_text_chars=1000, display_status=True) + "\n"
    page = Page(description=description, button_name="Personal Best")

    if not quote_races:
        page.description += "No races on this quote."
        return page

    recent_race = quote_races[-1]
    quote_bests = get_quote_bests(user_id)
    quote_bests_without = [
        score for score in quote_bests
        if score["raceId"] != recent_race["raceId"]
    ]

    best_race = max(quote_races, key=lambda x: x["pp"])
    best_rank = get_quote_best_rank(quote_bests, best_race["raceId"])

    if len(quote_races) == 1:
        pp_gain = calculate_total_pp(quote_bests) - calculate_total_pp(quote_bests_without)
        quote_best_rank = get_quote_best_rank(quote_bests, recent_race["raceId"])
        page.description += (
            f"**New Quote!**\n"
            f"**Quote Rank:** #{quote_best_rank:,} (+{pp_gain:,.2f} epp)\n\n"
            f"**Quote Score:** {score_display(recent_race)}\n"
        )
        page.color = SUCCESS
        return page

    elif recent_race == best_race:
        previous_best = max(quote_races[:-1], key=lambda x: x["pp"])
        quote_bests_without.append(previous_best)
        quote_bests_without.sort(key=lambda x: -x["pp"])
        pp_gain = calculate_total_pp(quote_bests) - calculate_total_pp(quote_bests_without)

        pp_difference = best_race["pp"] - previous_best["pp"]
        wpm_difference = best_race["wpm"] - previous_best["wpm"]
        rank_difference = get_quote_best_rank(quote_bests_without, previous_best["raceId"]) - best_rank

        page.description += (
            f"**New Quote Best!** +{pp_difference:,.2f} pp (+{wpm_difference:,.2f} WPM)\n"
            f"**Quote Rank:** #{best_rank:,} {INCREASE}{rank_difference:,} (+{pp_gain:,.2f} epp)\n\n"
            f"**New Best:** {score_display(best_race)}\n"
            f"**Previous Best:** {score_display(previous_best)}\n"
        )
        page.color = SUCCESS
        return page

    else:
        recent_rank = None
        for i, race in enumerate(quote_bests):
            if race["pp"] >= recent_race["pp"]:
                recent_rank = i + 1

        page.description += (
            f"**Best:** {score_display(best_race)} (Rank #{best_rank:,})\n"
            f"**Recent:** {score_display(recent_race)} (→Rank #{recent_rank:,})"
        )
        return page


def build_unranked_personal_best_page(quote: dict, quote_races: list[dict]) -> Page:
    """Build the personal best page for an unranked quote, which has no pp to report."""
    description = quote_display(quote, max_text_chars=1000, display_status=True) + "\n"
    page = Page(description=description, button_name="Personal Best")

    if not quote_races:
        page.description += "No races on this quote."
        return page

    recent_race = quote_races[-1]

    if len(quote_races) == 1:
        page.description += (
            f"**New Quote!**\n"
            f"**Quote Score:** {score_display(recent_race, show_pp=False)}\n"
        )
        page.color = SUCCESS
        return page

    best_race = max(quote_races, key=lambda x: x["wpm"])

    if recent_race == best_race:
        previous_best = max(quote_races[:-1], key=lambda x: x["wpm"])
        wpm_difference = best_race["wpm"] - previous_best["wpm"]

        page.description += (
            f"**New Quote Best!** +{wpm_difference:,.2f} WPM\n"
            f"**New Best:** {score_display(best_race, show_pp=False)}\n"
            f"**Previous Best:** {score_display(previous_best, show_pp=False)}\n"
        )
        page.color = SUCCESS
        return page

    else:
        page.description += (
            f"**Best:** {score_display(best_race, show_pp=False)}\n"
            f"**Recent:** {score_display(recent_race, show_pp=False)}"
        )
        return page


async def get_attempt_stats(user_id: str, quote_id: str) -> dict | None:
    """Return a user's attempt and play time counters for one quote, or None when the API has none."""
    try:
        return await get_quote_stats(user_id, quote_id)
    except APIError:
        return None


def build_attempts_page(stats: dict | None, quote: dict, quote_races: list[dict]) -> Page:
    """Build the page showing how much typing a quote took, including the runs never finished."""
    page = Page(button_name="Attempts")

    if not stats or not stats["attempts"]:
        page.description = "No attempt data for this quote."
        return page

    # The attempt counter postdates some races, so it can sit below the completion count.
    races, attempts = stats["races"], max(stats["attempts"], stats["races"])
    unfinished = attempts - races
    completed = stats["completionPlayTime"] / 1000
    abandoned = stats["attemptPlayTime"] / 1000

    page.description = (
        f"**Attempts:** {attempts:,}\n"
        f"**Finishes:** {races:,} ({races / attempts:.2%})\n"
        f"**Quits:** {unfinished:,} ({unfinished / attempts:.2%})\n\n"
        f"**Time Typed:** {format_duration(stats["playTime"] / 1000)}\n"
        f"**Completed:** {format_duration(completed)}\n"
        f"**Abandoned:** {format_duration(abandoned)}\n"
    )

    if unfinished and races:
        page.description += "\n"
        length = len(quote["text"])
        speeds = [race["wpm"] for race in quote_races if race["wpm"] > 0]

        if length and speeds:
            # The API sends no per-quote character counts, so estimate from the user's own speed.
            characters = (abandoned / unfinished) * (sum(speeds) / len(speeds)) * 5 / 60
            page.description += (
                f"**Average Quit:** ~{characters:,.0f}/{length:,} characters ({characters / length:.2%})\n"
            )

        page.description += (
            f"**Average Quit Time:** {format_duration(abandoned / unfinished, round_seconds=False)}\n"
            f"**Average Finish Time:** {format_duration(completed / races, round_seconds=False)}\n"
        )

    return page


def build_history_page(quote_races: list[dict], ranked: bool) -> Page:
    """Build the page listing a user's 10 best and 10 most recent races on a quote."""

    def quote_history(scores) -> str:
        """Format up to 10 scores as a numbered list."""
        history = ""
        for i in range(min(len(scores), 10)):
            score = scores[i]
            if ranked:
                display = (
                    f"{i + 1}. {score["pp"]:,.2f} pp - {score["wpm"]:,.2f} WPM ({score["accuracy"]:.2%})"
                    f" - {discord_date(score["timestamp"])}\n"
                )
            else:
                display = (
                    f"{i + 1}. {score["wpm"]:,.2f} WPM ({score["accuracy"]:.2%}) - "
                    f"{discord_date(score["timestamp"])}\n"
                )
            history += display

        return history

    quote_races.sort(key=lambda x: -parse_date(x["timestamp"]).timestamp())
    recent_races = quote_history(quote_races)

    quote_races.sort(key=lambda x: -x["wpm"])
    best_races = quote_history(quote_races)

    page = Page(
        fields=[
            Field(
                title="Recent",
                content=recent_races,
            ),
            Field(
                title="Best",
                content=best_races,
            ),
        ],
        button_name="Score History",
    )

    return page


def build_graph_page(quote_races: list, ranked: bool, theme: Theme) -> Page:
    """Build the page graphing every race a user has run on a quote."""
    metric = "pp" if ranked else "wpm"
    pp, wpm = zip(*[(race["pp"], race["wpm"]) for race in quote_races])

    description = f"**Times Typed:** {len(quote_races):,}\n"

    if ranked:
        description += (
            f"**Average:** {np.average(pp):,.2f} pp ({np.average(wpm):,.2f} WPM)\n"
            f"**Best:** {max(pp):,.2f} pp ({max(wpm):,.2f} WPM)"
        )
    else:
        description += (
            f"**Average:** {np.average(wpm):,.2f} WPM\n"
            f"**Best:** {max(wpm):,.2f} WPM"
        )

    quote_races.sort(key=lambda x: parse_date(x["timestamp"]).timestamp())
    page = Page(
        description=description,
        render=lambda: improvement.render_text(
            values=np.array([race[metric] for race in quote_races]),
            metric=metric,
            quote_id=quote_races[0]["quoteId"],
            theme=theme,
        ),
        button_name="Improvement",
    )

    return page


def build_progression_page(quote_races: list[dict], ranked: bool) -> Page:
    """Build the page listing every race that raised a user's best on a quote, oldest first."""
    metric = "pp" if ranked else "wpm"
    races = sorted(quote_races, key=lambda x: parse_date(x["timestamp"]).timestamp())

    progression = []
    for attempt, race in enumerate(races, 1):
        if not progression or race[metric] > progression[-1][1][metric]:
            progression.append((attempt, race))

    lines = []
    for i, (attempt, race) in enumerate(progression):
        gain = f" (+{race[metric] - progression[i - 1][1][metric]:,.2f})" if i else ""
        if ranked:
            score = f"{race["pp"]:,.2f} pp{gain} - {race["wpm"]:,.2f} WPM"
        else:
            score = f"{race["wpm"]:,.2f} WPM{gain}"
        lines.append(f"{i + 1}. {score} - #{attempt:,} - {discord_date(race["timestamp"], "D")}")

    # Discord caps an embed description at 4,096 characters.
    if len(lines) > PROGRESSION_LIMIT:
        hidden = len(lines) - PROGRESSION_LIMIT
        lines = lines[:1] + [f"*{hidden:,} more improvements*"] + lines[-(PROGRESSION_LIMIT - 1):]

    first, best = progression[0][1], progression[-1][1]
    if ranked:
        total_gain = f"+{best["pp"] - first["pp"]:,.2f} pp ({best["wpm"] - first["wpm"]:+,.2f} WPM)"
    else:
        total_gain = f"+{best["wpm"] - first["wpm"]:,.2f} WPM"

    description = (
        f"**Races:** {len(races):,}\n"
        f"**Improvements:** {len(progression) - 1:,}\n"
        f"**Total Gain:** {total_gain}\n\n"
    ) + "\n".join(lines)

    return Page(description=description, button_name="PB Progression")


async def run(ctx: BotContext, profile: Profile, quote: dict) -> None:
    """Send a user's personal best, history and graph for one quote."""
    user_id = profile["userId"]
    quote_id = quote["quoteId"]
    is_ranked = quote["ranked"]

    quote_races = await get_races(user_id, quote_id=quote_id, flags=ctx.flags)
    show_buttons = quote_races and (ctx.user["userId"] == profile["userId"] or ctx.user["isAdmin"])

    if is_ranked:
        pb_page = build_personal_best_page(quote, quote_races, user_id)
    else:
        pb_page = build_unranked_personal_best_page(quote, quote_races)

    pages = [pb_page]

    if show_buttons:
        stats = await get_attempt_stats(user_id, quote_id)
        pages += [
            build_history_page(quote_races, is_ranked),
            build_graph_page(quote_races, is_ranked, ctx.user["theme"]),
            build_progression_page(quote_races, is_ranked),
            build_attempts_page(stats, quote, quote_races),
        ]

    try:
        default_page = {"qh": 1, "qg": 2, "qp": 3, "qa": 4}.get(ctx.invoked_with, 0)
        pages[default_page].default = True
    except IndexError:
        raise BotError(
            "Privacy Error",
            "You may only view this embed for your own account",
        )

    message = Message(
        ctx,
        title=f"Quote History - {quote_id}",
        pages=pages,
        profile=profile,
    )

    await message.send()
