from discord import File, Embed
from discord.ext import commands
import os

from api.comparegraph import fetch_comparison_data
from api.users import get_tgg_user
from utils import errors
from graphs.comparegraph import render

info = {
    "name": "comparegraph",
    "aliases": ["flaneur", "cg"],
    "description": "Displays histograms comparing two user's quote PB pp/WPM differences",
    "parameters": "username2 [username1] [-m|--metric <pp|wpm>]",
    "defaults": {
        "metric": "pp",
    },
    "usages": [
        "comparegraph username2",
        "comparegraph username2 username1",
        "comparegraph username2 -m wpm",
    ],
}

async def setup(bot: commands.Bot):
    await bot.add_cog(CompareGraph(bot))

class CompareGraph(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"], name="comparegraph")
    async def comparegraph(self, ctx, *args):
        username1 = (await get_tgg_user(ctx.author.id))['username']
        username2 = None
        metric = info["defaults"]["metric"]

        i = 0
        while i < len(args):
            arg = args[i]

            if arg in ["-m", "--metric"] and i + 1 < len(args):
                metric_value = args[i + 1].lower()
                if metric_value in ["pp", "wpm"]:
                    metric = metric_value
                else:
                    return await ctx.send(embed=errors.invalid_metric(metric_value))
                i += 2
                continue

            if not username2:
                username2 = arg
            elif username1 == ctx.author.name:
                username1 = username2
                username2 = arg

            i += 1

        if not username2:
            return await ctx.send(embed=errors.missing_arguments(info))

        if username1 == username2:
            return await ctx.send(embed=errors.same_username())

        await run(ctx, username1, username2, metric)

async def run(ctx: commands.Context, username1: str, username2: str, metric: str = "pp"):
    loading_embed = Embed(
        title="Text Best Comparison",
        description="Generating comparison data, please wait...",
        color=0x3498db
    )
    loading_msg = await ctx.send(embed=loading_embed)

    try:
        response = await fetch_comparison_data(username1, username2, metric)

        if not response or response.get("status") != 200:
            await loading_msg.delete()
            error_msg = "Unable to fetch comparison data."
            if response and "message" in response:
                error_msg = response["message"]
            return await ctx.send(embed=Embed(
                title="No Data Available",
                description=error_msg,
                color=errors.RED,
            ))

        comparison_data: dict = response.get("data", {}) # type: ignore

        DEFAULT_COLOR = 0x00B5E2

        first_user = comparison_data.get("firstUser", {})
        second_user = comparison_data.get("secondUser", {})

        second_user_histogram = comparison_data["histogram"]["secondUser"]
        second_user_has_positive = any(bucket["difference"] > 0 for bucket in second_user_histogram) if second_user_histogram else False

        description = ""
        if not second_user_has_positive:
            TROPHY_EMOJI = '\U0001F3C6'
            description = f"{TROPHY_EMOJI} **TOTAL DOMINATION** {TROPHY_EMOJI}"

        same_text = ""

        file_name = f"compare_{username1}_{username2}_{metric}.png"

        render("keegant", comparison_data, file_name)

        if first_user and second_user:
            texts1 = first_user.get("winCount", 0)
            gain1 = first_user.get("gain", 0)
            average_gain1 = first_user.get("averageGain", 0)
            biggest_gap1 = first_user.get("biggestGap", 0)

            biggest_gap_quote1 = first_user.get("biggestGapQuote", "")
            biggest_gap_self_wpm1 = first_user.get("biggestGapSelfWPM", 0)
            biggest_gap_other_wpm1 = first_user.get("biggestGapOtherWPM", 0)

            texts2 = second_user.get("winCount", 0)
            gain2 = second_user.get("gain", 0)
            average_gain2 = second_user.get("averageGain", 0)
            biggest_gap2 = second_user.get("biggestGap", 0)

            # Get the biggest gap quote details for user 2
            biggest_gap_quote2 = second_user.get("biggestGapQuote", "")
            biggest_gap_self_wpm2 = second_user.get("biggestGapSelfWPM", 0)
            biggest_gap_other_wpm2 = second_user.get("biggestGapOtherWPM", 0)

            if metric == "pp":
                format_value = lambda x: f"+{int(x):,}"
                format_comparison = lambda x: f"{int(x)}"
            else:
                format_value = lambda x: f"+{x:,.2f}"
                format_comparison = lambda x: f"{x:.2f}"

            gap_details1 = ""
            if biggest_gap_quote1:
                gap_details1 = f"({format_comparison(biggest_gap_self_wpm1)} {metric.upper()} vs. {format_comparison(biggest_gap_other_wpm1)} {metric.upper()})\n"

            gap_details2 = ""
            if biggest_gap_quote2:
                gap_details2 = f"({format_comparison(biggest_gap_self_wpm2)} {metric.upper()} vs. {format_comparison(biggest_gap_other_wpm2)} {metric.upper()})\n"

            stats1 = (
                f"**Texts:** +{texts1:,}\n"
                f"**Gain:** {format_value(gain1)} {metric.upper()}\n"
                f"**Average Gain:** {format_value(average_gain1)} {metric.upper()}\n"
                f"**Biggest Gap:** {format_value(biggest_gap1)} {metric.upper()}\n"
                f"{gap_details1}"
                f"{same_text}"
            )

            if not second_user_has_positive:
                gap2 = f"**Closest:** {format_value(second_user.get('minValue', 0))} {metric.upper()}"
            else:
                gap2 = f"**Biggest Gap:** {format_value(biggest_gap2)} {metric.upper()}\n{gap_details2}"

            stats2 = (
                f"**Texts:** +{texts2:,}\n"
                f"**Gain:** {format_value(gain2)} {metric.upper()}\n"
                f"**Average Gain:** {format_value(average_gain2)} {metric.upper()}\n"
                f"{gap2}\n"
                f"{same_text}"
            )

            embed = Embed(
                title="Text Best Comparison",
                description=description,
                color=DEFAULT_COLOR,
            )

            embed.add_field(name=first_user['username'], value=stats1, inline=True)
            embed.add_field(name=second_user['username'], value=stats2, inline=True)

            # Set the image to reference the attached file
            embed.set_image(url=f"attachment://{file_name}")

            file = File(file_name, filename=file_name)
            await loading_msg.delete()
            await ctx.send(embed=embed, file=file)

            os.remove(file_name)
        else:
            await loading_msg.delete()
            return await ctx.send(embed=Embed(
                title="No Data Available",
                description="Unable to fetch comparison data for both users.",
                color=errors.RED,
            ))
    except Exception as e:
        print(f"Error in run: {e}")
        await loading_msg.delete()
        return await ctx.send(embed=errors.unexpected_error())
