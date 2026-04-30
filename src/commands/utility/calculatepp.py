from discord.ext import commands

from api.quotes import calculate_metric
from bot_setup import BotContext
from commands.base import Command
from utils.errors import MissingArguments
from utils.messages import Page, Message
from utils.strings import quote_display
from utils.urls import race_url

info = {
    "name": "calculatepp",
    "aliases": ["calculatewpm", "calc", "qc", "calcpp", "ppcalc"],
    "description": "Calculate WPM or pp for a specific quote, given the opposite.",
    "parameters": "<quote_id> <value> [pp|wpm]",
    "examples": [
        "-calc piykyai_3408 200 wpm",
        "-calc piykyai_3408 500 pp",
    ],
    "plus": True,
}


class CalculatePp(Command):
    supported_flags = {"metric", "number", "quote_id"}

    @commands.command(aliases=info["aliases"])
    async def calculatepp(self, ctx: BotContext):
        self.check_gg_plus(ctx)

        if ctx.flags.number is None:
            raise MissingArguments

        if not ctx.flags.quote_id:
            raise MissingArguments

        quote = await self.get_quote(ctx, ctx.flags.quote_id, from_api=True)
        quote_id = quote["quoteId"]
        value = abs(ctx.flags.number)
        metric = ctx.flags.metric
        calculated_value = await calculate_metric(quote_id, value, metric)

        quote_description = quote_display(
            quote,
            display_author=True,
            display_status=True,
            display_racers_users=True,
            display_submitted_by=True,
            max_text_chars=1000,
        )

        labels = ["pp", "WPM"]
        description = (
            f"{quote_description}\n"
            f"```{ctx.flags.number:,.2f} {labels[metric == "wpm"]} = "
            f"{calculated_value[labels[metric == "pp"].lower()]:,.2f} "
            f"{labels[metric == "pp"]}```"
        )

        page = Page(
            title=f"Quote Calculator - {quote_id}",
            description=description,
        )

        message = Message(
            ctx,
            page=page,
            url=race_url(quote_id),
            thumbnail=quote["source"]["thumbnailUrl"],
        )

        await message.send()
