from typing import Optional

import numpy as np
from discord.ext import commands

from commands.base import Command
from database.typegg.match_results import get_encounter_stats, get_match_stats, get_opponent_encounters
from database.typegg.quotes import get_quote, get_quotes
from database.typegg.races import get_races
from graphs import match as match_graph, encounters as encounters_graph
from utils.errors import GeneralException
from utils.keystrokes import get_keystroke_data
from utils.messages import Page, Message, Field
from utils.strings import get_flag_title, discord_date, username_with_flag, quote_display, rank

sorts = ["wins", "losses", "winrate", "wpm", "-winrate", "-wpm"]
info = {
    "name": "encounters",
    "aliases": ["en"],
    "description": "Displays a list of opponents faced in multiplayer matches\n"
                   "Enter a second username for head-to-head analysis\n"
                   "Sort options: `wins`, `losses`, `winrate`, `wpm`,\n`-winrate` (lowest), `-wpm` (biggest diff)",
    "parameters": "[username] [username2/sort]",
}


class Encounters(Command):
    @commands.command(aliases=info["aliases"])
    async def encounters(self, ctx, username: Optional[str] = "me", username2: Optional[str] = None):
        sort = None
        profile = await self.get_profile(ctx, username)
        await self.import_user(ctx, profile)

        if username2:
            if username2 not in sorts:
                profile2 = await self.get_profile(ctx, username2)
                await self.import_user(ctx, profile2)
                return await run_head_to_head(ctx, profile, profile2)
            else:
                sort = username2

        if ctx.flags.metric == "wpm":
            sort = "-wpm"

        await run(ctx, profile, sort)


async def run(ctx: commands.Context, profile: dict, sort: str):
    gamemode = ctx.flags.gamemode
    encounters = get_encounter_stats(profile["userId"], gamemode=gamemode)

    total_encounters = sum(en["totalEncounters"] for en in encounters)
    min_threshold = 2 if total_encounters < 500 else 10

    match sort:
        case "wins" | "losses":
            encounters.sort(key=lambda x: -x[sort])
        case "winrate":
            encounters = [en for en in encounters if en["totalEncounters"] >= min_threshold]
            encounters.sort(key=lambda x: -(x["wins"] / (x["wins"] + x["losses"])))
        case "-winrate":
            encounters = [en for en in encounters if en["totalEncounters"] >= min_threshold]
            encounters.sort(key=lambda x: x["wins"] / (x["wins"] + x["losses"]))
        case "wpm":
            encounters = [
                en for en in encounters
                if en["userWpm"] and en["opponentWpm"] and
                   en["totalEncounters"] >= min_threshold
            ]
            encounters.sort(key=lambda x: abs(x["userWpm"] - x["opponentWpm"]))
        case "-wpm":
            encounters = [
                en for en in encounters
                if en["userWpm"] and en["opponentWpm"] and
                   en["totalEncounters"] >= min_threshold
            ]
            encounters.sort(key=lambda x: -abs(x["userWpm"] - x["opponentWpm"]))

    if not encounters:
        raise GeneralException(
            "No Encounters",
            f"User `{profile["username"]}` has no {gamemode or "multiplayer"} encounters"
        )

    match_stats = get_match_stats(profile["userId"], gamemode=gamemode)
    bot_encounters = [e for e in encounters if e["isBot"]]
    total_bot_encounters = sum([e["totalEncounters"] for e in bot_encounters])
    user_encounters = [e for e in encounters if not e["isBot"]]
    total_user_encounters = sum([e["totalEncounters"] for e in user_encounters])
    bot_wins = sum([e["wins"] for e in bot_encounters])
    user_wins = sum([e["wins"] for e in user_encounters])

    description = (
        f"**Total Matches:** {match_stats["totalMatches"]:,} | "
        f"**Wins:** {match_stats["matchWins"]:,} "
        f"({match_stats["matchWins"] / match_stats["totalMatches"]:.2%})\n"
        f"**User Encounters:** {total_user_encounters:,} | "
        f"**Wins:** {user_wins:,} "
        f"({user_wins / total_user_encounters:.2%})\n"
        f"**Bot Encounters:** {total_bot_encounters:,} | "
        f"**Wins:** {bot_wins:,}    "
        f"({bot_wins / total_bot_encounters:.2%})\n"
        f"**Unique Opponents:** {len(user_encounters):,} users | {len(bot_encounters):,} bots\n\n"
        f"**Most Faced Users**\n"
    )

    sort_labels = {
        "wins": "Most Wins Against",
        "losses": "Most Losses Against",
        "winrate": "Highest Win Rate",
        "-winrate": "Lowest Win Rate",
        "wpm": "Closest Average WPM",
        "-wpm": "Farthest Average WPM",
    }

    description = description.replace(
        "**Most Faced Users**\n",
        f"**{sort_labels.get(sort)}**\n"
    )

    for i, en in enumerate(user_encounters[:10]):
        opponent = en["opponentUsername"]
        count = en["totalEncounters"]
        wins = en["wins"]
        losses = en["losses"]
        win_rate = wins / (wins + losses)
        if not en["userWpm"] or not en["opponentWpm"]:
            average = "n/a"
        else:
            wpm_diff = en["userWpm"] - en["opponentWpm"]
            plus = "+" if wpm_diff >= 0 else ""
            average = f"{plus}{wpm_diff:,.2f} WPM"

        description += (
            f"{i + 1}. **{opponent}** - {count:,}x | "
            f"{wins:,}W—{losses:,}L, {win_rate:.2%} | "
            f"{average}\n"
        )

    footer = None
    if sort in ["winrate", "-winrate", "wpm", "-wpm"] and min_threshold == 10:
        footer = f"Minimum {min_threshold} encounters required"

    page = Page(
        title="Multiplayer Encounters" + get_flag_title(ctx.flags),
        description=description,
        footer=footer,
    )

    message = Message(
        ctx,
        page=page,
        profile=profile,
    )

    return await message.send()


async def run_head_to_head(ctx: commands.Context, profile1: dict, profile2: dict):
    gamemode = ctx.flags.gamemode
    encounters = get_opponent_encounters(profile1["userId"], profile2["userId"], gamemode=gamemode)
    quote_list = get_quotes()
    difficulties = [quote_list[en["quoteId"]]["difficulty"] for en in encounters]
    p1_finish_count = len([en for en in encounters if not en["userDnf"]])
    p2_finish_count = len([en for en in encounters if not en["opponentDnf"]])

    if not encounters:
        raise GeneralException(
            "No Encounters", (
                f"No {gamemode or "multiplayer"} encounters found \n"
                f"between `{profile1["username"]}` and `{profile2["username"]}`"
            )
        )

    total_encounters = len(encounters)

    description = (
        f"**Total Encounters:** {total_encounters}\n"
        f"**First Encounter:** {discord_date(encounters[0]["timestamp"], "R")}\n"
        f"**Latest Encounter:** {discord_date(encounters[-1]["timestamp"], "R")}\n"
        f"**Average Difficulty:** {np.mean(difficulties):,.2f}★\n"
    )

    # Building stats
    stat_keys = ["wpm", "rawWpm", "accuracy", "placement"]
    default_stats = {
        "wpm": 0, "rawWpm": 0, "accuracy": 0, "placement": 0, "wins": 0,
        "bestStreak": 0, "currentStreak": 0, "biggestWin": None,
    }

    profile1["enStats"] = default_stats | {}
    profile2["enStats"] = default_stats | {}
    closest_race = None

    for match in encounters:
        p1 = profile1["enStats"]
        p2 = profile2["enStats"]

        p1["wpm"] += match["userWpm"]
        p1["rawWpm"] += match["userRawWpm"]
        p1["accuracy"] += match["userAccuracy"]
        p1["placement"] += match["userPlacement"]

        p2["wpm"] += match["opponentWpm"]
        p2["rawWpm"] += match["opponentRawWpm"]
        p2["accuracy"] += match["opponentAccuracy"]
        p2["placement"] += match["opponentPlacement"]

        winner, loser = profile1, profile2
        if match["opponentPlacement"] < match["userPlacement"]:
            winner, loser = loser, winner

        winner["enStats"]["wins"] += 1
        winner["enStats"]["currentStreak"] += 1
        winner["enStats"]["bestStreak"] = max(
            winner["enStats"]["currentStreak"],
            winner["enStats"]["bestStreak"]
        )
        loser["enStats"]["currentStreak"] = 0

        wpm_delta = match["userWpm"] - match["opponentWpm"]

        if match["userDnf"] or match["opponentDnf"]:
            continue

        if p1["biggestWin"] is None or wpm_delta > (p1["biggestWin"]["userWpm"] - p1["biggestWin"]["opponentWpm"]):
            p1["biggestWin"] = match

        if p2["biggestWin"] is None or -wpm_delta > (p2["biggestWin"]["opponentWpm"] - p2["biggestWin"]["userWpm"]):
            p2["biggestWin"] = match

        if closest_race is None or abs(wpm_delta) < abs(closest_race["userWpm"] - closest_race["opponentWpm"]):
            closest_race = match

    profile1["enStats"]["completion"] = p1_finish_count / total_encounters
    profile2["enStats"]["completion"] = p2_finish_count / total_encounters

    profiles = (
        (profile1, p1_finish_count),
        (profile2, p2_finish_count),
    )

    for profile, finish_count in profiles:
        for key in stat_keys:
            divisor = total_encounters if key == "placement" else finish_count
            profile["enStats"][key] = (
                0 if divisor == 0 else profile["enStats"][key] / divisor
            )

    def build_field(profile: dict):
        stats = profile["enStats"]
        biggest = stats["biggestWin"]

        content = (
            f"**Average Speed:** {stats["wpm"]:,.2f} WPM\n"
            f"**Raw Speed:** {stats["rawWpm"]:,.2f} WPM\n"
            f"**Accuracy:** {stats["accuracy"]:.2%}\n"
            f"**Completion:** {stats["completion"]:.0%}\n"
            f"**Average Placement:** {stats["placement"]:,.2f}\n"
            f"**Wins:** {stats["wins"]:,} "
            f"({stats["wins"] / total_encounters:.2%} Win Rate)\n"
            f"**Best Win Streak:** {stats["bestStreak"]}\n"
        )

        if biggest is not None:
            is_p1 = profile["userId"] == profile1["userId"]
            user_wpm = biggest["userWpm"] if is_p1 else biggest["opponentWpm"]
            opp_wpm = biggest["opponentWpm"] if is_p1 else biggest["userWpm"]
            delta = user_wpm - opp_wpm

            label = "Biggest Win" if delta > 0 else "Closest Loss"
            sign = "+" if delta > 0 else ""
            content += f"**{label}:** {sign}{delta:,.2f} WPM\n"

        return Field(
            title=username_with_flag(profile, link_user=False),
            content=content,
            inline=True,
        )

    async def load_race_data(match: dict):
        races = await get_races(match_id=match["matchId"], get_keystrokes=True)

        race_data = []
        for profile, prefix in [
            (profile1, "user"),
            (profile2, "opponent"),
        ]:
            race = next(r for r in races if r["userId"] == profile["userId"])
            start_time = match[prefix + "StartTime"]
            ks = get_keystroke_data(race["keystrokeData"], True, start_time)

            race |= {
                "keystroke_wpm": ks.keystrokeWpm,
                "username": profile["username"],
                "displayName": username_with_flag(profile, link_user=False),
                "startTime": start_time,
                "wpm": match[prefix + "Wpm"],
            }
            race_data.append(race)

        return race_data

    def build_race_description(race_data: list, quote: dict):
        race_data.sort(key=lambda r: -r["wpm"])
        rankings = "".join(
            f"{rank(i + 1)} {r["displayName"]} - {r["wpm"]:,.2f} WPM "
            f"({r["accuracy"]:.2%} Acc, {r["startTime"]:,.0f}ms Start)\n"
            for i, r in enumerate(race_data)
        )

        return (
            f"Completed {discord_date(race_data[0]["timestamp"], "R")}\n\n"
            f"{quote_display(quote, 1000, display_status=True)}\n"
            f"**Rankings:**\n"
            f"{rankings}"
        )

    # Pages
    pages = [
        Page(
            title="Multiplayer Encounters",
            description=description,
            fields=[
                build_field(profile1),
                build_field(profile2),
            ],
            render=lambda: encounters_graph.render(
                encounters,
                difficulties,
                title=(
                    "Multiplayer Encounters\n"
                    f"{profile1["username"]} vs. {profile2["username"]}"
                ),
                theme=ctx.user["theme"],
            ),
            button_name="Stats",
            footer=f"🔵 {profile1["username"]} | 🟣 {profile2["username"]} | ⚫ Difficulty | 🔴 DNF"
        )
    ]

    # Biggest Wins
    for i, profile in enumerate((profile1, profile2)):
        biggest = profile["enStats"]["biggestWin"]

        if biggest is None:
            continue

        delta = (
            biggest["userWpm"] - biggest["opponentWpm"]
            if i == 0
            else biggest["opponentWpm"] - biggest["userWpm"]
        )

        if delta <= 0:
            continue

        race_data = await load_race_data(biggest)
        quote = get_quote(biggest["quoteId"])

        pages.append(Page(
            title=f"Biggest Win - {profile["username"]} (+{delta:,.2f} WPM)",
            description=build_race_description(race_data, quote),
            button_name=f"Biggest Win (p{i + 1})",
            render=lambda id=i, rd=race_data: match_graph.render(
                race_data=rd,
                title=(
                    f"Match Graph - {profile1["username"]} - "
                    f"Race #{rd[id]["raceNumber"]:,}"
                ),
                theme=ctx.user["theme"],
                themed_line=id,
            ),
        ))

    # Closest race
    if closest_race is not None:
        close_delta = abs(closest_race["userWpm"] - closest_race["opponentWpm"])
        close_race_data = await load_race_data(closest_race)
        close_quote = get_quote(closest_race["quoteId"])
        themed_line = 0 if close_race_data[0]["userId"] == profile1["userId"] else 1

        pages.append(Page(
            title=f"Closest Race (+{close_delta:,.2f} WPM)",
            description=build_race_description(close_race_data, close_quote),
            button_name="Closest Race",
            render=lambda: match_graph.render(
                race_data=close_race_data,
                title=(
                    f"Match Graph - {profile1["username"]} - "
                    f"Race #{close_race_data[0]["raceNumber"]:,}"
                ),
                theme=ctx.user['theme'],
                themed_line=themed_line,
            ),
        ))

    message = Message(ctx, pages=pages)
    await message.send()
