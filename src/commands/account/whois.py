import json

from discord.ext import commands

from commands.base import Command
from database.bot.users import get_user, get_user_by_user_id
from utils.errors import ProfileNotFound, GeneralException
from utils.messages import Page, Message
from utils.strings import discord_date, GG_PLUS_LINKED
from utils.urls import profile_url

info = {
    "name": "whois",
    "aliases": ["who"],
    "description": "Displays information about a TypeGG or Discord user.",
    "parameters": "[discord_id/typegg_username]",
    "examples": [
        "-whois eiko"
    ]
}

UnknownWhoIs = GeneralException(
    "Unknown User",
    "I've never seen this person in my life"
)


class WhoIs(Command):
    @commands.command(aliases=info["aliases"])
    async def whois(self, ctx, *args):
        if not args:
            user_string = str(ctx.author.id)
        else:
            user_string = " ".join(args)

        try:
            site_profile = await self.get_profile(ctx, user_string, races_required=False)
            bot_profile = get_user_by_user_id(site_profile["userId"])
            await run(ctx, bot_profile, site_profile)
        except ProfileNotFound:
            try:
                discord_user = await commands.UserConverter().convert(ctx, user_string)
                bot_profile = get_user(discord_user.id, auto_insert=False)

                if not bot_profile:
                    raise UnknownWhoIs

                if bot_profile["userId"]:
                    site_profile = await self.get_profile(ctx, bot_profile["userId"], races_required=False)
                    await run(ctx, bot_profile, site_profile)
                else:
                    await run(ctx, bot_profile)
            except commands.BadArgument:
                raise UnknownWhoIs


async def run(ctx: commands.Context, bot_profile: dict = None, site_profile: dict = None):
    description = ""

    if site_profile:
        if site_profile["globalRank"] == -1:
            rank_string = "Unranked"
        else:
            rank_string = f"#{site_profile["globalRank"]:,} :earth_americas:"
            country = site_profile["country"]
            country_rank = f" / #{site_profile["countryRank"]} :flag_{country.lower()}:" if country else ""
            rank_string += country_rank

        description += (
            f"### TypeGG: [{site_profile["username"]}]({profile_url(site_profile["username"])})"
            f"{" " + GG_PLUS_LINKED if site_profile["isGgPlus"] else ""}\n"
            f"**Rank:** {rank_string}\n"
            f"**Total pp:** {site_profile["stats"]["totalPp"]:,.0f} pp\n"
            f"**nWPM:** {site_profile["stats"]["nWpm"]:.2f}\n"
            f"**Races:** {site_profile["stats"]["races"]:,}\n"
            f"**Join Date:** {discord_date(site_profile["joinDate"], "D")}\n"
        )
    else:
        description += "### TypeGG: Account not linked\n"

    if bot_profile:
        commands_used = json.loads(bot_profile["commands"])["counts"]
        top_commands = sorted(commands_used.items(), key=lambda x: -x[1])
        total_commands = sum([c[1] for c in top_commands])
        top_commands_str = "".join([f"{i + 1}. {c[0]} ({c[1]:,})\n" for i, c in enumerate(top_commands[:3])])

        description += (
            f"### Discord: <@{bot_profile["discordId"]}>\n"
            f"First Command: {discord_date(bot_profile["joined"], "D")}\n"
            f"Commands Used: {total_commands:,}\n"
            f"{top_commands_str}"
        )
    else:
        description += "### Discord: Account not linked"

    message = Message(
        ctx, page=Page(
            title="Who Is",
            description=description,
        ),
        profile=site_profile,
    )

    return await message.send()
