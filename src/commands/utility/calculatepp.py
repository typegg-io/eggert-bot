from typing import Optional

from discord.ext import commands

from api.quotes import calculate_metric
from commands.base import Command
from utils.messages import Page, Message
from utils.strings import get_argument, quote_display
from utils.urls import race_url

info = {
    "name": "calculatepp",
    "aliases": ["calculatewpm", "calc", "qc", "calcpp", "ppcalc"],
    "description": "Calculate WPM or pp for a specific quote, given the opposite.",
    "parameters": "<quote_id> <value> [pp|wpm]",
    "plus": True,
}


class CalculatePp(Command):
    @commands.command(aliases=info["aliases"])
    async def calculatepp(self, ctx, quote_id: str, value: float, metric: Optional[str] = "pp"):
        self.check_gg_plus(ctx)

        metrics = ["pp", "wpm"]
        metric = get_argument(metrics, metric)
        quote = await self.get_quote(ctx, quote_id, from_api=True)
        quote_id = quote["quoteId"]

        calculated_value = await calculate_metric(quote_id, value, metric)
        quote_description = quote_display(
            quote,
            display_author=True,
            display_status=True,
            display_racers_users=True,
            display_submitted_by=True,
            max_text_chars=1000,
        )

        labels = sorted(["pp", "WPM"], reverse=metric == "pp")
        input_label, output_label = labels

        page = Page(
            title=f"Quote Calculator - {quote_id}",
            description=(
                f"{quote_description}\n"
                f"```{value:,.2f} {input_label} = "
                f"{calculated_value[metrics[metric == "pp"]]:,.2f} {output_label}```"
            ),
        )

        message = Message(
            ctx,
            page=page,
            url=race_url(quote_id),
            thumbnail=quote["source"]["thumbnailUrl"],
        )

        await message.send()
