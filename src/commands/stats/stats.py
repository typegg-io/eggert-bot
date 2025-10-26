from typing import Optional

from discord.ext import commands

from commands.base import Command
from utils.messages import Page, Message, Field
from utils.strings import discord_date, format_duration
from utils.urls import profile_url

info = {
    "name": "stats",
    "aliases": ["s", "profile"],
    "description": "Displays stats about a TypeGG account",
    "parameters": "[username]",
}


class Stats(Command):
    @commands.command(aliases=info["aliases"])
    async def stats(self, ctx, username: Optional[str] = "me"):
        profile = await self.get_profile(ctx, username)
        await run(ctx, profile)


async def run(ctx: commands.Context, profile: dict):
    fields = [
        Field(
            title="Performance",
            content=(
                f"**Total:** {profile["stats"]["totalPp"]:,.0f} pp\n"
                f"**Best:** {profile["stats"]["bestPp"]["value"]:,.2f} pp\n"
                f"**nWPM:** {profile["stats"]["nWpm"]:.2f} ({profile["stats"]["accuracy"]:.2%} accuracy)\n"
                f"**Top Speed:** {profile["stats"]["bestWpm"]["value"]} WPM\n\n"
            )
        ),
        Field(
            title="Activity",
            content=(
                f"**Quotes:** {profile["stats"]["quotesTyped"]:,}\n"
                f"**Races:** {profile["stats"]["races"]:,}\n"
                f"**Solo:** {profile["stats"]["soloRaces"]:,} / "
                f"**Multiplayer:** {profile["stats"]["multiplayerRaces"]:,}\n"
                f"**Wins:** {profile["stats"]["wins"]:,} "
                f"({0 if profile["stats"]["multiplayerRaces"] == 0
                else profile["stats"]["wins"] / profile["stats"]["multiplayerRaces"]:.2%} win rate)\n"
                f"**Level:** {profile["stats"]["level"]:,.2f} "
                f"({profile["stats"]["experience"]:,.0f} XP)\n"
                f"**Play Time:** {format_duration(profile["stats"]["playTime"] / 1000)}"
            )
        ),
        Field(
            title="Daily Quote",
            content=(
                f"**Current Streak:** {profile["stats"]["dailyQuotes"]["streak"]}\n"
                f"**Best Streak:** {profile["stats"]["dailyQuotes"]["bestStreak"]}\n"
                f"**Completed:** {profile["stats"]["dailyQuotes"]["completed"]}"
            ),
        ),
        Field(
            title="About",
            content=(
                f"**Last Seen:** {discord_date(profile["lastSeen"])}\n"
                f"**Join Date:** {discord_date(profile["joinDate"])}\n"
                + (f"**Layout:** {profile["hardware"]["layout"]}\n" if profile["hardware"]["layout"] else "")
                + (f"**Keyboard:** {profile["hardware"]["keyboard"]}\n" if profile["hardware"]["keyboard"] else "")
                + (f"**Switches:** {profile["hardware"]["switches"]}\n" if profile["hardware"]["switches"] else "")
                + f"**Profile Views:** {profile["profileViews"]}"
            )
        )
    ]

    rank_string = "**Rank:** "
    global_rank = profile["globalRank"]
    if global_rank == -1:
        rank_string += "Unranked"
    else:
        rank_string += f"#{profile["globalRank"]:,} :earth_americas:"
        country = profile["country"]
        country_rank = f" / #{profile["countryRank"]} :flag_{country.lower()}:" if country else ""
        rank_string += country_rank

    page = Page(
        description=rank_string,
        fields=fields,
    )

    message = Message(
        ctx,
        page=page,
        url=profile_url(profile["username"]),
        profile=profile,
    )

    return await message.send()
