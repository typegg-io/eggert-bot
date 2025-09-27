from discord.ext import commands

from api.quotes import get_quotes
from commands.base import Command
from utils import strings, urls
from utils.messages import Page, Message, paginate_data

info = {
    "name": "search",
    "aliases": ["qs", "lf"],
    "description": "Performs a case-insensitive search through quotes for matching results",
    "parameters": "<query>",
}


class Search(Command):
    @commands.command(aliases=info["aliases"])
    async def search(self, ctx, *args: str):
        await run(ctx, " ".join(args))


def entry_formatter(quote):
    text = quote["text"]
    return (
        f"[**{quote["source"]["title"]}**]({urls.race(quote["quoteId"])}) "
        f"| {quote["difficulty"]:.2f}★ | {len(text)}c | "
        f"{"Ranked" if quote["ranked"] else "Unranked"}\n"
        f"\"{strings.truncate_clean(text, 150)}\"\n\n"
    )


async def run(ctx: commands.Context, query: str):
    results = await get_quotes(
        search=query,
        per_page=100,
        min_length=len(query),
    )
    quotes = results["quotes"]
    total_results = results["totalCount"]

    query_string = f"**Query:** \"{strings.escape_formatting(query)}\""
    if not quotes:
        page = Page(description="No results found.\n" + query_string)
        message = Message(ctx, page)
        return await message.send()

    per_page = 5
    pages = paginate_data(quotes, entry_formatter, 20, per_page)
    for i, page in enumerate(pages):
        page_start = i * per_page + 1
        page_end = min((i + 1) * per_page, total_results)
        page.description = (
            f"Displaying **{page_start}-{page_end}** of **{total_results:,}** results\n\n"
            f"{page.description}"
        )

    message = Message(
        ctx,
        title="Quote Search",
        header=query_string,
        pages=pages,
    )

    await message.send()
