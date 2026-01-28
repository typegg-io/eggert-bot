from typing import Optional

from discord.ext import commands

from commands.base import Command
from database.typegg.match_results import get_encounter_stats, get_match_stats
from utils.errors import GeneralException
from utils.messages import Page, Message
from utils.strings import get_flag_title

info = {
    "name": "encounters",
    "aliases": ["en"],
    "description": "Displays a list of opponents faced in multiplayer matches.\n"
                   "Enter a second username for a head-to-head analysis.",
    "parameters": "[username] [username2]",
}


class Encounters(Command):
    @commands.command(aliases=info["aliases"])
    async def encounters(self, ctx, username: Optional[str] = "me", username2: Optional[str] = None):
        profile = await self.get_profile(ctx, username)
        await self.import_user(ctx, profile)
        await run(ctx, profile)


async def run(ctx: commands.Context, profile: dict):
    gamemode = ctx.flags.gamemode
    encounters = get_encounter_stats(profile["userId"], gamemode=gamemode)

    if not encounters:
        raise GeneralException(
            "No Encounters",
            f"User `{profile["username"]}` has no {gamemode or "multiplayer"} encounters."
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
