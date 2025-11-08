from typing import List, Optional

from discord.ext import commands
from numpy import average

from commands.base import Command
from database.typegg.users import get_quote_bests
from graphs import top250 as top250_graph
from utils.errors import NoRankedRaces
from utils.messages import Page, Message
from utils.stats import calculate_total_pp

max_users_shown = 5

info = {
    "name": "top250",
    "aliases": ["250"],
    "description": "Displays the top 250 quotes ordered by pp from high to low.\n"
                   f"This graph can be generated for up to {max_users_shown} users.",
    "parameters": f"[username1] [username2] ... [username{max_users_shown}]",
    "author": 231721357484752896,
}


class Top250(Command):
    @commands.command(aliases=info["aliases"])
    async def top250(self, ctx, username: Optional[str] = "me", *other_users: str):
        other_users = other_users[:max_users_shown - 1]
        usernames = set(other_users)
        usernames.add(username)
        profiles = [await self.get_profile(ctx, username, races_required=True) for username in usernames]

        await run(ctx, profiles)


async def run(ctx: commands.Context, profiles: List[dict]):
    top_250s = []
    description = ""
    profiles.sort(key=lambda x: -x["stats"]["totalPp"])
    username = profiles[0]["username"]

    for profile in profiles:
        quote_bests = get_quote_bests(
            profile["userId"],
            columns=["pp"],
            order_by="pp",
            limit=250,
        )
        pp_values = [race["pp"] for race in quote_bests]

        if not pp_values:
            raise NoRankedRaces(username)

        top_250s.append({
            "username": profile["username"],
            "pp_values": pp_values,
        })

        if profile["userId"] == ctx.user["userId"]:
            username = profile["username"]

        description += (
            f"**{profile["username"]}:** "
            f"Total {calculate_total_pp(quote_bests):,.0f} pp | "
            f"Max: {max(pp_values):,.0f} | "
            f"Average: {average(pp_values):,.0f} | "
            f"Min: {min(pp_values):,.0f}\n"
        )

    page = Page(
        title="Top 250 Quotes",
        description=description,
        render=lambda: top250_graph.render(
            username,
            top_250s,
            ctx.user["theme"]
        )
    )

    message = Message(
        ctx,
        page=page
    )

    await message.send()
