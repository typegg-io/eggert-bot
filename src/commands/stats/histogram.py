from typing import Optional
from discord.ext import commands
from commands.base import Command
from database.typegg.users import get_quote_bests
from utils.messages import Page, Message, Field
from utils.strings import get_argument
import numpy as np
from graphs import histogram


metrics = ["pp", "wpm", "acc", "react", "recover"]
info = {
    "name": "histogram",
    "aliases": ["hg", "hist"],
    "description": "Retruns a histogram for solo and for multi in the current metric, the default metric is pp.",
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
    title = metric.capitalize()

    match metric:
        case "acc":
            metric = "accuracy"
            title = metric.capitalize()
        case "react":
            metric = "errorReactionTime"
            title = "Error Reaction Time" 
        case "recover":
            metric = "errorRecoveryTime"
            title = "Error Recovery Time" 

    quote_bests = get_quote_bests(profile["userId"])

    solo_stats = []
    multi_stats = []

    for race in quote_bests:
        if race["gamemode"] == "solo":
            solo_stats.append(race[metric])
        elif race["gamemode"] == "multiplayer":
            multi_stats.append(race[metric])
        else:
            raise ValueError(dict(race))

    display_solo_stats = solo_stats
    display_multi_stats = multi_stats

    if metric == "accuracy":
            display_solo_stats = np.array(display_solo_stats) * 100
            display_multi_stats = np.array(display_multi_stats) * 100

    username = profile["username"]

    fields = []

    def make_field(title: str, data: list[float]):
        content = (
            f"**Average** {np.average(data):.2f}\n"
                f"**Mean** {np.mean(data):.2f}\n"
                f"**Standard Deviation** {np.std(data):.2f}\n"
                f"**Quartiles** {" -> ".join(map(lambda q: f"{q:.2f}", np.quantile(data, [0.25, 0.75])))}\n"
        )

        return Field(title=title, content=content, inline=True)


    fields = [make_field("Solo", display_solo_stats), make_field("Multi", display_multi_stats)]

    page = Page(
        title=f"{title} Histogram",
        fields=fields,
        render=lambda: histogram.render(
            username,
            metric,
            solo_stats,
            multi_stats,
            ctx.user["theme"],
        )
    )

    message = Message(
        ctx,
        page=page,
    )

    await message.send()

