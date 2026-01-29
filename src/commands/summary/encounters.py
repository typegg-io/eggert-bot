from typing import Optional

from discord.ext import commands

from commands.base import Command
from database.typegg.match_results import get_encounter_stats, get_match_stats, get_opponent_encounters
from database.typegg.quotes import get_quote
from database.typegg.races import get_races
from graphs import match as match_graph
from utils.errors import GeneralException
from utils.keystrokes import get_keystroke_data
from utils.messages import Page, Message, Field
from utils.strings import get_flag_title, discord_date, username_with_flag, quote_display

info = {
    "name": "encounters",
    "aliases": ["en"],
    "description": "Displays a list of opponents faced in multiplayer matches\n"
                   "Enter a second username for head-to-head analysis",
    "parameters": "[username] [username2]",
}


class Encounters(Command):
    @commands.command(aliases=info["aliases"])
    async def encounters(self, ctx, username: Optional[str] = "me", username2: Optional[str] = None):
        profile = await self.get_profile(ctx, username)
        await self.import_user(ctx, profile)

        if username2:
            profile2 = await self.get_profile(ctx, username2)
            await self.import_user(ctx, profile2)
            await run_head_to_head(ctx, profile, profile2)
        else:
            await run(ctx, profile)


async def run(ctx: commands.Context, profile: dict):
    gamemode = ctx.flags.gamemode
    encounters = get_encounter_stats(profile["userId"], gamemode=gamemode)

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

    for i, en in enumerate(user_encounters[:10]):
        opponent = en["opponentUsername"]
        count = en["totalEncounters"]
        wins = en["wins"]
        losses = en["losses"]
        win_rate = wins / count

        description += (
            f"{i + 1}. **{opponent}** - {count:,} matches "
            f"({wins:,}W—{losses:,}L, {win_rate:.2%})\n"
        )

    page = Page(
        title="Multiplayer Encounters" + get_flag_title(ctx.flags),
        description=description,
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

    if not encounters:
        raise GeneralException(
            "No Encounters",
            f"No {gamemode or "multiplayer"} encounters found \n"
            f"between `{profile1["username"]}` and `{profile2["username"]}`"
        )

    total_encounters = len(encounters)
    description = (
        f"**Total Encounters:** {total_encounters}\n"
        f"**First Encounter:** {discord_date(encounters[0]["timestamp"], "R")}\n"
        f"**Lastest Encounter:** {discord_date(encounters[-1]["timestamp"], "R")}\n"
    )

    def build_field(profile):
        stats = profile["enStats"]

        biggest_win = stats["biggestWin"]
        if profile["userId"] == profile1["userId"]:
            wpm_delta = biggest_win["userWpm"] - biggest_win["opponentWpm"]
        else:
            wpm_delta = biggest_win["opponentWpm"] - biggest_win["userWpm"]
        if wpm_delta > 0:
            biggest_win_str = f"**Biggest Win:** +{wpm_delta:,.2f} WPM"
        else:
            biggest_win_str = f"**Closest Loss:** {wpm_delta:,.2f} WPM"

        return Field(
            title=username_with_flag(profile, link_user=False),
            content=(
                f"**Average Speed:** {stats["wpm"]:,.2f} WPM\n"
                f"**Raw Speed:** {stats["rawWpm"]:,.2f} WPM\n"
                f"**Accuracy:** {stats["accuracy"]:.2%}\n"
                f"**Average Placement:** {stats["placement"]:,.2f}\n"
                f"**Wins:** {stats["wins"]:,} "
                f"({stats["wins"] / total_encounters:.2%} Win Rate)\n"
                f"**Best Win Streak:** {stats["bestStreak"]}\n"
                f"{biggest_win_str}\n"
            ),
            inline=True,
        )

    closest_race = encounters[0]
    profile1["enStats"] = {
        "wpm": 0, "rawWpm": 0, "accuracy": 0, "placement": 0, "wins": 0,
        "bestStreak": 0, "currentStreak": 0, "biggestWin": encounters[0],
    }
    profile2["enStats"] = {
        "wpm": 0, "rawWpm": 0, "accuracy": 0, "placement": 0, "wins": 0,
        "bestStreak": 0, "currentStreak": 0, "biggestWin": encounters[0],
    }

    for en in encounters:
        stats1 = profile1["enStats"]
        stats2 = profile2["enStats"]

        stats1["wpm"] += en["userWpm"]
        stats1["rawWpm"] += en["userRawWpm"]
        stats1["accuracy"] += en["userAccuracy"]
        stats1["placement"] += en["userPlacement"]

        stats2["wpm"] += en["opponentWpm"]
        stats2["rawWpm"] += en["opponentRawWpm"]
        stats2["accuracy"] += en["opponentAccuracy"]
        stats2["placement"] += en["opponentPlacement"]

        wpm_delta = en["userWpm"] - en["opponentWpm"]

        biggest_win1 = stats1["biggestWin"]
        if wpm_delta > biggest_win1["userWpm"] - biggest_win1["opponentWpm"]:
            stats1["biggestWin"] = en

        biggest_win2 = stats2["biggestWin"]
        if -wpm_delta > biggest_win2["opponentWpm"] - biggest_win2["userWpm"]:
            stats2["biggestWin"] = en

        if abs(wpm_delta) < abs(closest_race["userWpm"] - closest_race["opponentWpm"]):
            closest_race = en

        winner, loser = profile1, profile2
        if en["opponentPlacement"] < en["userPlacement"]:
            winner, loser = loser, winner

        winner["enStats"]["wins"] += 1
        winner["enStats"]["currentStreak"] += 1
        winner["enStats"]["bestStreak"] = max(
            winner["enStats"]["currentStreak"],
            winner["enStats"]["bestStreak"]
        )
        loser["enStats"]["currentStreak"] = 0

    for key in ["wpm", "rawWpm", "accuracy", "placement"]:
        for profile in [profile1, profile2]:
            profile["enStats"][key] /= total_encounters

    pages = [Page(
        title="Multiplayer Encounters",
        description=description,
        fields=[
            build_field(profile1),
            build_field(profile2),
        ],
        button_name="Stats",
    )]

    async def build_race_data(match_data):
        races = await get_races(match_id=match_data["matchId"], get_keystrokes=True)

        race1 = next(race for race in races if race["userId"] == profile1["userId"])
        keystroke_data = get_keystroke_data(race1["keystrokeData"])
        race1 |= {
            "keystroke_wpm": keystroke_data.keystrokeWpm,
            "username": profile1["username"],
            "startTime": keystroke_data.wpmCharacterTimes[0],
            "wpm": match_data["userWpm"],
        }

        race2 = next(race for race in races if race["userId"] == profile2["userId"])
        keystroke_data = get_keystroke_data(race2["keystrokeData"])
        race2 |= {
            "keystroke_wpm": keystroke_data.keystrokeWpm,
            "username": profile2["username"],
            "startTime": keystroke_data.wpmCharacterTimes[0],
            "wpm": match_data["opponentWpm"],
        }

        return [race1, race2]

    def build_race_description(race_data, quote):
        race_data.sort(key=lambda x: -x["wpm"])
        rankings = ""

        for i, race in enumerate(race_data):
            rankings += (
                f"{i + 1}. **{race["username"]}** - {race["wpm"]:,.2f} WPM "
                f"({race["accuracy"]:.2%} Acc, {race["startTime"]:,.0f}ms Start)\n"
            )

        return (
            f"Completed {discord_date(race_data[0]["timestamp"], "R")}\n\n"
            f"{quote_display(quote, 1000, display_status=True)}\n"
            f"**Rankings:**\n"
            f"{rankings}"
        )

    biggest_win1 = profile1["enStats"]["biggestWin"]
    wpm_delta1 = biggest_win1["userWpm"] - biggest_win1["opponentWpm"]
    race_data1 = await build_race_data(biggest_win1)
    quote1 = get_quote(biggest_win1["quoteId"])

    if wpm_delta1 > 0:
        pages.append(Page(
            title=f"Biggest Win - {profile1['username']} (+{wpm_delta1:,.2f} WPM)",
            description=build_race_description(race_data1, quote1),
            button_name="Biggest Win (p1)",
            render=lambda: match_graph.render(
                race_data=race_data1,
                title=(
                    f"Match Graph - {profile1["username"]} - "
                    f"Race #{race_data1[0]["raceNumber"]:,}"
                ),
                theme=ctx.user["theme"],
                themed_line=0,
            )
        ))

    biggest_win2 = profile2["enStats"]["biggestWin"]
    wpm_delta2 = biggest_win2["opponentWpm"] - biggest_win2["userWpm"]
    race_data2 = await build_race_data(biggest_win2)
    quote2 = get_quote(biggest_win2["quoteId"])

    if wpm_delta2 > 0:
        pages.append(Page(
            title=f"Biggest Win - {profile2['username']} (+{wpm_delta2:,.2f} WPM)",
            description=build_race_description(race_data2, quote2),
            button_name="Biggest Win (p2)",
            render=lambda: match_graph.render(
                race_data=race_data2,
                title=(
                    f"Match Graph - {profile1["username"]} - "
                    f"Race #{race_data2[1]["raceNumber"]:,}"
                ),
                theme=ctx.user["theme"],
                themed_line=1,
            )
        ))

    wpm_delta_close = abs(closest_race["userWpm"] - closest_race["opponentWpm"])
    race_data_close = await build_race_data(closest_race)
    quote_close = get_quote(closest_race["quoteId"])

    pages.append(Page(
        title=f"Closest Race (+{wpm_delta_close:,.2f} WPM)",
        description=build_race_description(race_data_close, quote_close),
        button_name="Closest Race",
        render=lambda: match_graph.render(
            race_data=race_data_close,
            title=(
                f"Match Graph - {profile1["username"]} - "
                f"Race #{race_data_close[1 if wpm_delta_close < 0 else 0]["raceNumber"]:,}"
            ),
            theme=ctx.user["theme"],
            themed_line=1,
        )
    ))

    message = Message(ctx, pages=pages)
    return await message.send()
