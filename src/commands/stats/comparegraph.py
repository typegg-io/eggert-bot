from typing import Optional

from discord.ext import commands

from commands.base import Command
from database.typegg.users import get_quote_bests
from graphs import compare
from utils.errors import same_username, invalid_argument, no_common_texts
from utils.messages import Page, Message, Field
from utils.strings import get_option

metrics = ["pp", "wpm"]
info = {
    "name": "comparegraph",
    "aliases": ["cg", "flaneur"],
    "description": "",
    "parameters": "<username1> [username2] [pp|wpm]",
}


class CompareGraph(Command):
    @commands.command(aliases=info["aliases"])
    async def comparegraph(self, ctx, username1: str, username2: Optional[str] = "me", metric: Optional[str] = "pp"):
        metric = get_option(metrics, metric)
        metric_override = get_option(metrics, username2)

        if metric_override:
            metric = metric_override
            username2 = "me"
        elif not metric:
            return await ctx.send(embed=invalid_argument(info))

        username1, username2 = self.get_usernames(ctx, username1, username2)
        if username1 == username2:
            return await ctx.send(embed=same_username())

        profile1 = await self.get_profile(ctx, username1, races_required=True)
        profile2 = await self.get_profile(ctx, username2, races_required=True)
        await self.import_user(ctx, profile1)
        await self.import_user(ctx, profile2)

        await run(ctx, profile1, profile2, metric)


async def run(ctx: commands.Context, profile1: dict, profile2: dict, metric: str):
    quote_bests1 = get_quote_bests(profile1["userId"], as_dictionary=True)
    quote_bests2 = get_quote_bests(profile2["userId"], as_dictionary=True)
    common_quotes = list(quote_bests1.keys() & quote_bests2.keys())
    if not common_quotes:
        return await ctx.send(embed=no_common_texts())

    differences = [
        quote_bests1[quote_id][metric] - quote_bests2[quote_id][metric]
        for quote_id in common_quotes
    ]

    gains1 = [diff for diff in differences if diff > 0]
    gains2 = [-diff for diff in differences if diff < 0]
    match = max((
        (common_quotes[i], quote_bests1[common_quotes[i]][metric])
        for i, diff in enumerate(differences)
        if diff == 0.0
    ), key=lambda x: x[1], default=None)

    def display_gain(value, decimals=2):
        gain = f"{value:,.{decimals}f}"
        if value >= 0:
            gain = "+" + gain

        return gain

    def make_field(username, country, quotes_greater, gain, average_gain, max_gap, metric1, metric2, metric):
        if metric == "wpm":
            metric = metric.upper()
        flag = "" if country == "" else f":flag_{country.lower()}: "

        content = (
            f"**Quotes:** {display_gain(quotes_greater, 0)}\n"
            f"**Gain:** {display_gain(gain)} {metric}\n"
            f"**Average Gain:** {display_gain(average_gain)} {metric}\n"
            f"**{"Biggest Gain" if max_gap > 0 else "Closest"}:** {display_gain(max_gap)} {metric}\n"
            f"{metric1:,.2f} {metric} vs. {metric2:,.2f} {metric}\n"
        )

        if match:
            content += f"{match[0]} - {match[1]:,.2f} {metric} :handshake:"

        return Field(
            title=flag + username,
            content=content,
            inline=True,
        )

    fields = []

    username1 = profile1["username"]
    country = profile1["country"]
    quotes_greater = len(gains1)
    gain = sum(gains1)
    average_gain = 0 if gain == 0 else gain / quotes_greater
    max_gap = -min(gains2) if gain == 0 else max(gains1)
    quote_id = common_quotes[differences.index(max_gap)]
    metric1 = quote_bests1[quote_id][metric]
    metric2 = quote_bests2[quote_id][metric]

    fields.append(
        make_field(
            username1, country, quotes_greater, gain, average_gain, max_gap, metric1, metric2, metric
        )
    )

    username2 = profile2["username"]
    country = profile2["country"]
    quotes_greater = len(gains2)
    gain = sum(gains2)
    average_gain = 0 if gain == 0 else gain / quotes_greater
    max_gap = -min(gains1) if gain == 0 else max(gains2)
    quote_id = common_quotes[differences.index(-max_gap)]
    metric1 = quote_bests2[quote_id][metric]
    metric2 = quote_bests1[quote_id][metric]

    fields.append(
        make_field(
            username2, country, quotes_greater, gain, average_gain, max_gap, metric1, metric2, metric
        )
    )

    page = Page(
        title="Quote Best Comparison",
        fields=fields,
        render=lambda: compare.render(
            username1,
            gains1,
            username2,
            gains2,
            metric,
            ctx.user["theme"],
        )
    )

    message = Message(
        ctx,
        page=page,
    )

    await message.send()
