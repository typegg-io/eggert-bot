from typing import List, Optional, List
from database.typegg.users import get_quote_bests
from discord.ext import commands
from commands.base import Command
from graphs import top250
from utils.errors import MissingUsername, NoRaces
from utils.messages import Page, Message


max_users_shown = 5

info = {
    "name": "top250",
    "aliases": ["250"],
    "description": "Displays the top 250 quotes according to pp in order from high to low.\n"
    f"This graph can be made for multiple users up to {max_users_shown} users",
    "parameters": f"[username1] [username2] ... [username{max_users_shown}]",
    "author": 231721357484752896,
}


class Top250(Command):
    @commands.command(aliases=info["aliases"])
    async def top250(self, ctx, username: Optional[str] = "me", *other_users: str):
        profiles = []
        name = ""
        is_first_iteration = True

        for username in {username, *other_users}:
            tmp, is_first_iteration = is_first_iteration, False

            try:
                profile = await self.get_profile(ctx, username, races_required=True)
                await self.import_user(ctx, profile)

                if tmp:
                    name = profile["username"]

                profiles.append(profile)
            except (MissingUsername, NoRaces):
                pass

        if len(profiles) == 0:
            raise NoRaces

        await run(ctx, profiles, name)


async def run(ctx: commands.Context, profiles: List[dict], username: str):
    top250s = [{
        "data": list(map(lambda data: data["pp"], get_quote_bests(profile["userId"], columns=["pp"], order_by="pp", limit=250))),
        "username": profile["username"]
    } for profile in profiles]

    page = Page(
        title="Top 250 quotes",
        render=lambda: top250.render(
            username,
            top250s,
            ctx.user["theme"]
        )
    )

    message = Message(
        ctx,
        page=page
    )

    await message.send()
