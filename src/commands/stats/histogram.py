from typing import Optional
from discord.ext import commands
from commands.base import Command
from database.typegg.users import get_quote_bests
from utils.messages import Page, Message
from utils.strings import get_argument
from graphs import histogram


metrics = ["pp", "wpm", "acc"]
info = {
    "name": "histogram",
    "aliases": ["hg", "hist"],
    "description": "Retruns a histogram of the current metric, the default metric is PP.",
    "parameters": f"<username> [{"|".join(metrics)}]",
    "author": 231721357484752896,
}


class Histogram(Command):
    @commands.command(aliases=info["aliases"])
    async def Histogram(self, ctx, username: str = "me", metric: Optional[str] = "pp"):
        username = self.get_username(ctx, username)
        metric = get_argument(metrics, metric, True)


        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)

        await run(ctx, profile, metric)


async def run(ctx: commands.Context, profile: dict, metric: str):
    match metric:
        case "acc":
            metric = "accuracy"

    quote_bests = get_quote_bests(profile["userId"])
    quote_bests_stats = list(map(lambda race: race[metric], quote_bests))
    username = profile["username"]

    page = Page(
        title="pp vs. Length Comparison",
        render=lambda: histogram.render(
            username,
            metric,
            quote_bests_stats,
            ctx.user["theme"],
        )
    )

    message = Message(
        ctx,
        page=page,
    )

    await message.send()
