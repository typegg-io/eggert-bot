from typing import Optional

from discord.ext import commands

from commands.base import Command
from commands.stats.best import run, metrics
from utils.errors import invalid_argument

info = {
    "name": "worst",
    "aliases": ["bottom"],
    "description": "Displays a user's bottom 100 quotes\n"
                   "\\- `metric` defaults to pp",
    "parameters": "[username] [pp|wpm]",
}


class Worst(Command):
    @commands.command(aliases=info["aliases"])
    async def worst(self, ctx, username: Optional[str] = "me", metric: Optional[str] = "pp"):
        if metric not in metrics:
            return await ctx.send(embed=invalid_argument(metrics))

        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)
        await run(ctx, profile, metric)
