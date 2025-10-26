from typing import List, Optional
from discord.ext import commands
from commands.base import Command
from database.typegg.users import get_quote_bests
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
        profiles = set()

        for username in {username, *other_users}:
            try:
                profile = await self.get_profile(ctx, username, races_required=True)
                await self.import_user(ctx, profile)

                profiles.add(profile)
            except (MissingUsername, NoRaces):
                pass

        profiles = list(profiles)

        if len(profiles) == 0:
            raise NoRaces

        await run(ctx, profiles)


async def run(ctx: commands.Context, profiles: List[dict]):
    page = Page(
        title="Top 250 quotes",
        render=lambda: top250.render(
            profiles,
            ctx.user["theme"]
        )
    )

    message = Message(
        ctx,
        page=page
    )

    await message.send()
