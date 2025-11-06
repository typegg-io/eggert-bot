import bisect
from typing import Optional

from discord import File
from discord.ext import commands

from commands.base import Command
from database.typegg.races import get_races
from graphs import line
from utils.strings import get_argument

metrics = {
    "pp": {
        "columns": "pp quoteId",
        "title": "Total pp",
        "alias": "ppl",
    },
    "best": {
        "columns": "pp",
        "title": "Best pp",
        "alias": "bl",
    },
    "wpm": {
        "columns": "wpm",
        "title": "Best WPM",
        "alias": "wl",
    },
    "races": {
        "columns": "raceNumber",
        "title": "Races",
        "alias": "rl",
    },
    "quotes": {
        "columns": "quoteId",
        "title": "Quotes Typed",
        "alias": "ql",
    },
    "characters": {
        "columns": "wpm duration",
        "title": "Characters Typed",
        "alias": "cl",
    }
}

max_users = 5
metric_aliases = [metric["alias"] for metric in metrics.values()]

info = {
    "name": "linegraph",
    "aliases": ["lg", "l"] + metric_aliases,
    "description": f"Displays a line graph of up to {max_users} users for a given metric",
    "parameters": f"<metric> [username1] [username2] ... [username{max_users}]",
}


class LineGraph(Command):
    @commands.command(aliases=info["aliases"])
    async def linegraph(self, ctx, metric: str = "pp", username1: Optional[str] = "me", *other_users: Optional[str]):
        invoke = ctx.invoked_with.lower()

        if invoke in metric_aliases:
            other_users = list(other_users) + [metric]
            metric = [*metrics.keys()][metric_aliases.index(invoke)]
        else:
            metric = get_argument(metrics.keys(), metric)

        other_users = other_users[:max_users - 1]
        usernames = set(other_users)
        usernames.add(username1)
        profiles = []

        for username in usernames:
            profile = await self.get_profile(ctx, username, races_required=True)
            profiles.append(profile)
            await self.import_user(ctx, profile)

        await run(ctx, metric, profiles)


def get_total_pp_over_time(race_list: list[dict]):
    quote_bests = {}
    best_pps = []
    total_pp = []
    current_total = 0.0
    max_entries = 250

    for race in race_list:
        quote_id = race["quoteId"]
        pp = race["pp"]
        old_best = quote_bests.get(quote_id)

        if old_best is None or pp > old_best["pp"]:
            if old_best is not None:
                old_pp = old_best["pp"]
                idx = bisect.bisect_left([-x for x in best_pps], -old_pp)
                if idx < len(best_pps) and best_pps[idx] == old_pp:
                    best_pps.pop(idx)

            bisect.insort_left(best_pps, pp)
            best_pps.sort(reverse=True)

            quote_bests[quote_id] = race

            if len(best_pps) <= max_entries or best_pps.index(pp) < max_entries:
                current_total = 0.0
                for i, p in enumerate(best_pps[:max_entries]):
                    current_total += p * 0.97 ** i

        total_pp.append(current_total)

    return total_pp


def get_best_over_time(race_list: list[dict], key: str):
    values = []
    best = race_list[0][key]

    for race in race_list:
        value = race[key]
        if value > best:
            best = value
        values.append(best)

    return values


def get_quotes_over_time(race_list: list[dict]):
    quotes_typed = []
    unique_quotes = set()

    for race in race_list:
        unique_quotes.add(race["quoteId"])
        quotes_typed.append(len(unique_quotes))

    return quotes_typed


def get_characters_over_time(race_list: list[dict]):
    characters_typed = []
    total = 0

    for race in race_list:
        quote_length = int(round(race["wpm"] * race["duration"] / 12000) + 1)
        total += quote_length
        characters_typed.append(total)

    return characters_typed


async def run(ctx: commands.Context, metric: str, profiles: list[dict]):
    profiles.sort(key=lambda x: -x["stats"]["races"])
    username = profiles[0]["username"]

    lines = []
    for profile in profiles:
        columns = metrics[metric]["columns"].split(" ")
        columns.append("timestamp")
        min_pp = 0.01 if metric in ["wpm", "quotes"] else 0

        race_list = await get_races(
            profile["userId"],
            columns,
            min_pp=min_pp,
            order_by="timestamp",
        )

        x_values = [race["timestamp"] for race in race_list]
        y_values = []

        if metric == "pp":
            y_values = get_total_pp_over_time(race_list)
        elif metric in ["best", "wpm"]:
            y_values = get_best_over_time(race_list, key=columns[0])
        elif metric == "races":
            y_values = [race["raceNumber"] for race in race_list]
        elif metric == "quotes":
            y_values = get_quotes_over_time(race_list)
        elif metric == "characters":
            y_values = get_characters_over_time(race_list)

        lines.append({
            "username": profile["username"],
            "x_values": x_values,
            "y_values": y_values,
        })

        if profile["userId"] == ctx.user["userId"]:
            username = profile["username"]

    lines.sort(key=lambda x: -x["y_values"][-1])

    title = metrics[metric]["title"]
    file_name = line.render(
        username,
        lines,
        f"{title} Over Time",
        title,
        ctx.user["theme"],
    )
    file = File(file_name, filename=file_name)
    await ctx.send(file=file)
