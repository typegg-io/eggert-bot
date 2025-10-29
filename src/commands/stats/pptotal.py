from typing import List, Optional
from database.typegg.races import get_races
from discord.ext import commands
from commands.base import Command
from graphs import pptotal
from utils.errors import MissingUsername, NoRaces
from utils.messages import Page, Message


max_users_shown = 5

info = {
    "name": "pptotal",
    "aliases": ["pt"],
    "description": "Displays the total pp progression over time. "
    f"This graph can be generated for multiple users up to {max_users_shown} users.",
    "parameters": f"[username1] [username2] ... [username{max_users_shown}]",
    "author": 231721357484752896,
}


class Pptotal(Command):
    @commands.command(aliases=info["aliases"])
    async def pptotal(self, ctx, username: Optional[str] = "me", *other_users: str):
        other_users = other_users[:max_users_shown - 1]
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
    profiles = [{
        "data": await get_races(profile["userId"], columns=["pp", "timestamp", "quoteId"], order_by="timestamp"),
        "username": profile["username"]
    } for profile in profiles]

    page = Page(
        title="Total pp progression",
        render=lambda: pptotal.render(
            username,
            profiles,
            ctx.user["theme"]
        )
    )

    message = Message(
        ctx,
        page=page
    )

    await message.send()

