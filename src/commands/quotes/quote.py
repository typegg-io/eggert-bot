from typing import Optional

import numpy as np
from discord.ext import commands

from commands.base import Command
from database.typegg.races import get_quote_races
from database.typegg.users import get_quote_bests
from graphs import improvement
from utils.colors import SUCCESS
from utils.dates import parse_date
from utils.messages import Page, Message, Field
from utils.stats import calculate_total_pp
from utils.strings import discord_date, INCREASE, quote_display

info = {
    "name": "quote",
    "aliases": ["q", "pb"],
    "description": "Displays a user's stats about a specific text",
    "parameters": "[username] [quote_id]",
}


class Quote(Command):
    @commands.command(aliases=info["aliases"])
    async def quote(self, ctx, username: Optional[str] = "me", *, quote_id: Optional[str] = None):
        if not ctx.user["isPrivacyWarned"]:
            await self.send_privacy_warning(ctx)

        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)
        quote = await self.get_quote(ctx, quote_id, profile["userId"])

        await run(ctx, profile, quote)


def get_quote_best_rank(quote_bests: list[dict], race_id: str):
    """Returns the rank of a score given a list of quote bests."""
    for i, race in enumerate(quote_bests):
        if race["raceId"] == race_id:
            return i + 1


def score_display(score, show_pp=True):
    if show_pp:
        return (
            f"{score["pp"]:,.2f} pp ({score["wpm"]:,.2f} WPM) - "
            f"{discord_date(score["timestamp"])}"
        )

    return f"{score["wpm"]:,.2f} WPM - {discord_date(score["timestamp"])}"


def build_personal_best_page(quote: dict, quote_races: list[dict], user_id: str):
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
            if race["pp"] > recent_race["pp"]:
                recent_rank = i + 1

        page.description += (
            f"**Best:** {score_display(best_race)} (Rank #{best_rank:,})\n"
            f"**Recent:** {score_display(recent_race)} (→Rank #{recent_rank:,})"
        )
        return page


def build_unranked_personal_best_page(quote: dict, quote_races: list[dict]):
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


def build_history_page(quote_races: list[dict], ranked: bool):
    def quote_history(scores):
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


def build_graph_page(quote_races: list, ranked: bool, theme: dict):
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


async def run(ctx: commands.Context, profile: dict, quote: dict):
    user_id = profile["userId"]
    quote_id = quote["quoteId"]
    is_ranked = quote["ranked"]

    quote_races = get_quote_races(user_id, quote_id)
    show_buttons = ctx.user["userId"] == profile["userId"] and quote_races

    if is_ranked:
        pb_page = build_personal_best_page(quote, quote_races, user_id)
    else:
        pb_page = build_unranked_personal_best_page(quote, quote_races)

    pages = [pb_page]

    if show_buttons:
        pages += [
            build_history_page(quote_races, is_ranked),
            build_graph_page(quote_races, is_ranked, ctx.user["theme"])
        ]

    message = Message(
        ctx,
        title=f"Quote History - {quote_id}",
        pages=pages,
        profile=profile,
    )

    await message.send()
